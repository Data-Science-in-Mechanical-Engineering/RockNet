#include "cp_os.h"
#include "uart.h"
#include "internal_messages.h"
#include "gpi/tools.h"
#include "gpi/platform.h"
#include "gpi/interrupts.h"
#include "gpi/clocks.h"
#include "gpi/olf.h"
#include "cp_os.h"
#include "rocket_os.h"
#include "linear_classifier.h"
#include <stdint.h>

static ap_com_handle hap_com;

static uint32_t round_nmbr = 0;

static uint16_t rx_time_series_last_round;
static float timeseries[LENGTH_TIME_SERIES];
static float label = 0;

static float linear_classification_part = 0;

static ap_message_t message;

extern uint16_t __attribute__((section(".data"))) TOS_NODE_ID;

static void rx_wait_uart()
{
  // do not waitfor rx
}

static void tx_wait_uart()
{
  
}

static uint16_t receive_data_from_AP(ap_message_t **data)
{
  return 0;
}

static void send_data_to_AP(ap_message_t *data, uint16_t size)
{
}

static uint8_t communication_finished_callback(ap_message_t *data, uint16_t size)
{
  float cummulative = 0;
  float timeseries[LENGTH_TIME_SERIES];
  uint16_t time_series_data_idx = 0xFFFF;

  // parse messages
  for (uint16_t i = 0; i < size; i++) {
    if (data[i].header.type == TYPE_METADATA) {
      round_nmbr = data[i].metadata_message.round_nmbr;
    } else {
      if (data[i].header.type == TYPE_CLASSIFICATION) {
        cummulative += data[i].classification_message.classification;
        //printf("Cummulative: %d\n", (int32_t) (cummulative*10000));
      } else {
        if (data[i].header.type == TYPE_TIME_SERIES) {
          cummulative += data[i].time_series_message.classification;
          //printf("Cummulative: %u\n", (uint32_t) (cummulative*10000));
          time_series_data_idx = i;
        }
      }
    }
  }

  if (rx_time_series_last_round) {
    //printf("Cummulative: %d\n", (int32_t) (cummulative*10000));
    update_weights(cummulative, label, round_nmbr);
  }

  
  linear_classification_part = 0;

  // received time series.
  if (time_series_data_idx != 0xFFFF) {
    rx_time_series_last_round = 1;
    for (uint16_t j = 0; j < LENGTH_TIME_SERIES; j++) {
      timeseries[j] = data[time_series_data_idx].time_series_message.data[j];
    }

    label = data[time_series_data_idx].time_series_message.label;

    // calculate part of linear classification
    linear_classification_part = classify_part(timeseries);

  } else {
    rx_time_series_last_round = 0;
  }

} 
                
static uint16_t communication_starts_callback(ap_message_t **data)
{
  // write timeseries in tx_message
  data[0] = &message;
  if (TOS_NODE_ID == 1) {
    float **tsp = get_timeseries();
    for (uint16_t j = 0; j < LENGTH_TIME_SERIES; j++) {
      data[0]->time_series_message.data[j] = tsp[round_nmbr % NUM_TIMESERIES][j];
    }

    data[0]->header.id = TOS_NODE_ID;
    data[0]->header.type = TYPE_TIME_SERIES;
    data[0]->time_series_message.classification = linear_classification_part;
    data[0]->time_series_message.label = get_labels()[round_nmbr % NUM_TIMESERIES];
  } else {
    data[0]->header.id = TOS_NODE_ID;
    data[0]->header.type = TYPE_CLASSIFICATION;
    data[0]->classification_message.classification = linear_classification_part;
  }
  return 1;
}

void run_rocket_os(uint8_t id)
{ 
  printf("Init device %u started\n", TOS_NODE_ID);

  init_ap_com(&hap_com, &send_uart, &receive_uart, &rx_wait_uart, &tx_wait_uart);
  init_cp_os(&receive_data_from_AP, &send_data_to_AP, &communication_finished_callback, &communication_starts_callback, id);
  
  printf("Init device %u finished\n", TOS_NODE_ID);
  run();
}