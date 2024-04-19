#include "cp_os.h"
#include "spi.h" 
#include "mixer/mixer.h"
#include "mixer_aggregate.h"
#include "gpi/trace.h"
#include "gpi/tools.h"
#include "gpi/platform.h"
#include "gpi/interrupts.h"
#include "gpi/clocks.h"
#include "gpi/olf.h"
#include "message_layer.h"
#include <string.h>

static uint8_t node_id;
static uint32_t round_nr;
static uint8_t agg_input[AGGREGATE_SIZE];
static Gpi_Hybrid_Tick t_ref;
static uint8_t TOS_NODE_ID;

static uint8_t (*communication_finished_callback)(ap_message_t*, uint16_t);
static uint16_t (*communication_starts_callback)(ap_message_t**);

static ap_message_t dummy_message;

void init_cp_os(uint8_t (*communication_finished_callback_p)(ap_message_t*, uint16_t), 
                uint16_t (*communication_starts_callback_p)(ap_message_t**),
                uint8_t id)
{
  communication_finished_callback = communication_finished_callback_p;
  communication_starts_callback = communication_starts_callback_p;
  TOS_NODE_ID = id;

  for (node_id = 0; node_id < NUM_ELEMENTS(nodes); ++node_id) {
    if (nodes[node_id] == TOS_NODE_ID)
            break;
  }

  init_agg(id);
}
            

void run()
{
  ap_message_t ap_pkt;
  message_layer_init();
  printf("Messagelayer init\r\n");

  round_nr = 1;
  // t_ref for first round is now (-> start as soon as possible)
  t_ref = gpi_tick_hybrid();
  run_normal_operation();
}


void run_rounds(uint8_t (*communication_finished_callback)(ap_message_t*, uint16_t), uint16_t (*communication_starts_callback)(ap_message_t**))
{
  init_message_t init_pkt = {.round = 0};
  // init buffer, which saves messages, which are received
  ap_message_t mixer_messages_received[NUM_ELEMENTS(message_assignment) + 1]; //+1, because the las entry is the init_pkt
  // if 1, message is valid, if 0, message is not valid (was not received)
  uint8_t mixer_messages_received_valid[MX_GENERATION_SIZE-1];

  uint16_t messages_received_idx = 0;

  Gpi_Hybrid_Tick ticks_start;
  for (; 1; round_nr++) {

    // init mixer
    mixer_init(node_id);
    mixer_set_weak_release_slot(WEAK_RELEASE_SLOT);
    mixer_set_weak_return_msg((void*)-1);
    // init aggregate callback (not important if we do not use aggregates, which we currently not do)
    mixer_init_agg(&aggregate_M_C_highest);
    // reset aggregate
    memset(agg_input, 0, AGGREGATE_SIZE);

    // Initiator sends initiator packet. Currently it only holds the round number
    if (MX_INITIATOR_ID == TOS_NODE_ID)
    {
      init_pkt.round = round_nr;
                           
      // NOTE: we specified that the control packet uses index 0 and data packets use
      // indexes > 0. 

      mixer_write(0, &init_pkt, sizeof(init_message_t));
    }
    
    // wait before calling callback to give application processor enough time for computation
    //while (gpi_tick_compare_hybrid(gpi_tick_hybrid(), READ_AND_ARM_OFFSET(t_ref, ROUND_PERIOD)) < 0);
    //CLR_COM_GPIO1();

    // e.g. READ data from application processor (or do something else)
    ap_message_t *tx_messages[NUM_ELEMENTS(message_assignment)];
    uint16_t size_tx_messages = communication_starts_callback(tx_messages);
    
    // write aggregate (currently not used)
    //set_flag_in_agg(agg_input, plant_idx);
    //set_node_in_agg(agg_input, 0, TOS_NODE_ID);
    //set_prio_in_agg(agg_input, 0, 1);
    mixer_write_agg(agg_input);
    // write into mixer
    for (uint16_t tx_message_idx = 0; tx_message_idx < size_tx_messages; tx_message_idx++) {
      // when the agent does not want to send anything, it sends a TYPE_DUMMY
      if (tx_messages[tx_message_idx]->header.type != TYPE_DUMMY) {
        // the id of the message in the message layer is written in the header.
        message_layer_set_message(tx_messages[tx_message_idx]->header.id, (uint8_t *) tx_messages[tx_message_idx]);
      }
    }

    // arm mixer
    // start first round with infinite scan
    // -> nodes join next available round, does not require simultaneous boot-up
    //mixer_write_agg(agg_input);
    mixer_arm(((MX_INITIATOR_ID == TOS_NODE_ID) ? MX_ARM_INITIATOR : 0) | ((1 == round_nr) ? MX_ARM_INFINITE_SCAN : 0));
    
    // inference has ended. Toggle line (we measure inference + copying of data as inference time)
    CLR_COM_LED();
    ticks_start = gpi_tick_hybrid() - ticks_start;
    ticks_start = gpi_tick_hybrid_to_us(ticks_start);
    
    if (TOS_NODE_ID != 1) {
      //printf("i: %u\n", ticks_start);
      //printf("m: %u\n", messages_received_idx - 1);
      //printf("%u\r\n", ROUND_LENGTH_MS);
    }

    // toggle pin
    gpi_milli_sleep(1);
    SET_COM_LED();


    // poll such that mixer round starts at the correct time.
    // delay initiator a bit
    // -> increase probability that all nodes are ready when initiator starts the round
    // -> avoid problems in view of limited t_ref accuracy
    if (MX_INITIATOR_ID == TOS_NODE_ID)
    {
      while (gpi_tick_compare_hybrid(gpi_tick_hybrid(), MIXER_OFFSET(t_ref, ROUND_PERIOD) + MIXER_INITIATOR_DELAY) < 0);
    }
    else
    {
      while (gpi_tick_compare_hybrid(gpi_tick_hybrid(), MIXER_OFFSET(t_ref, ROUND_PERIOD)) < 0);
    }
    CLR_COM_GPIO1();      
    // ATTENTION: don't delay after the polling loop (-> print before)
    CLR_COM_LED();
    ticks_start = gpi_tick_hybrid();
    t_ref = mixer_start();

    // sometimes communication ends a bit earlier, when agent has received everything and its neightbours too.
    while (gpi_tick_compare_hybrid(gpi_tick_hybrid(), SYNC_OFFSET(t_ref)) < 0);
    ticks_start = gpi_tick_hybrid() - ticks_start;
    ticks_start = gpi_tick_hybrid_to_us(ticks_start);
    if (TOS_NODE_ID != 1) {
      //printf("c: %u\n", ticks_start);
    }
    ticks_start = gpi_tick_hybrid();
    SET_COM_LED();

      
    // Just for Debug
    SET_COM_GPIO1();

    // read received data
    uint32_t msgs_not_decoded = 0;
    uint32_t msgs_weak = 0;
    uint32_t control_msg_decoded = 0;
    messages_received_idx = 0;
    for (uint16_t i = 0; i < NUM_ELEMENTS(message_assignment); i++) {
      // write data in array, when message was received
      messages_received_idx += message_layer_get_message(message_assignment[i].id, (uint8_t *) &mixer_messages_received[messages_received_idx]);
    }
        
    // mixer_print_statistics();

    // synchronize to the initiator node
    init_message_t init_message;
    uint8_t succ = read_message_from_mixer(0, (uint8_t *) &init_message, sizeof(init_message_t));
    if (succ) {
      if (1 == round_nr) {
        round_nr = init_message.round;
      // resynchronize when round number does not match
      } else if (init_message.round != round_nr) {
        round_nr = 0;	// increments to 1 with next round loop iteration
      }
    }

    #if DEVICE_ID == 1
    // printf("%u/%u\n", messages_received_idx, NUM_ELEMENTS(message_assignment));
    for (uint8_t i = 0; i < messages_received_idx; i++) {
      //printf("%u\n", mixer_messages_received[i].header.id);
    }
    #endif

    // write round in metadata message, which will be sent to AP, such that AP knows what time it is.
    mixer_messages_received[messages_received_idx].metadata_message.header.type = TYPE_METADATA;
    mixer_messages_received[messages_received_idx].metadata_message.header.id = TOS_NODE_ID;
    mixer_messages_received[messages_received_idx].metadata_message.round_nmbr = round_nr;
    messages_received_idx += 1; // local or initiator message?

    // process received data (e.g. send it to AP) and finish, if the callback says so.
    if (communication_finished_callback(mixer_messages_received, messages_received_idx)) {
      break;
    }
  }
}

static uint16_t wait_for_agents_com_starts_callback(ap_message_t **message)
{
  // This TYPE_CP_ACK message is never TXed to the AP!!
  // It is required to put this into the Mixer TX/RX buffer anyway, such that the node advertises itself to the network!
  dummy_message.header.type = TYPE_CP_ACK;
  dummy_message.header.id = TOS_NODE_ID;
  message[0] = &dummy_message;
  //NRF_P0->OUTSET = BV(25);
  return 1;
}

static uint8_t wait_for_agents_com_finished_callback(ap_message_t *received_messages, uint16_t size) // received_messages unnecessary
{
  /*uint16_t num_messages_received = 0;
  for (uint16_t i = 0; i<NUM_ELEMENTS(message_assignment)+1; i++) {
    if (messages_received_valid[i] == 1) {
      num_messages_received++;
    }
  }*/
  if (size == ((uint16_t) NUM_ELEMENTS(message_assignment))+1) { // + 1 because of local message or initiator?
    return 1;
  }
  return 0;
}

void wait_for_other_agents()
{   
  run_rounds(&wait_for_agents_com_finished_callback, &wait_for_agents_com_starts_callback);
}


/**
 * run in normal operation
 */
void run_normal_operation()
{
  run_rounds(communication_finished_callback, communication_starts_callback);
}