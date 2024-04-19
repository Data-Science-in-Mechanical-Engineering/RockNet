#include "message_layer.h"
#include "mixer/mixer.h"
#include "gpi/tools.h"
#include "gpi/platform.h"
#include "gpi/interrupts.h"
#include "gpi/clocks.h"
#include "gpi/olf.h"
#include <stdint.h>
#include <string.h>
#include "internal_messages.h"

#include <math.h>

#ifndef MIN
#define MIN(X, Y) (((X) < (Y)) ? (X) : (Y))
#endif

void message_layer_init()
{
  uint16_t idx = 1;
  for (uint16_t i=0; i<NUM_ELEMENTS(message_assignment); i++) {
    message_assignment[i].mixer_assignment_start = idx;
    uint16_t num_mixer_messages = ceil((float) (message_assignment[i].size) / MX_PAYLOAD_SIZE - 1e-7);

    message_assignment[i].size_end = message_assignment[i].size - (num_mixer_messages-1)*MX_PAYLOAD_SIZE;
    idx += num_mixer_messages;  // the number of mixer messages is the rounded up number
    message_assignment[i].mixer_assignment_end = idx;
    printf("num_mixer_messages: %u\r\n", num_mixer_messages);
    printf("start: %u\r\n", message_assignment[i].mixer_assignment_start);
    printf("end: %u\r\n", message_assignment[i].mixer_assignment_end);
    printf("size_end: %u\r\n", message_assignment[i].size_end);
  }
  
  if (message_assignment[NUM_ELEMENTS(message_assignment)-1].mixer_assignment_end > MX_GENERATION_SIZE) {
    // something is wrong, blink slowly
    while(1) {
      NRF_P0->OUTCLR = BV(25);
      gpi_milli_sleep(2000);
      NRF_P0->OUTSET = BV(25);
      gpi_milli_sleep(2000);
    }
  }
}

uint8_t read_message_from_mixer(uint8_t mixer_idx, uint8_t *msg_p, uint16_t size)
{
  void *p = mixer_read(mixer_idx);

  // check if message was received. Return 0 if not.
  if (NULL == p) {
    return 0;
  } else if ((void*)-1 == p) {
    return 0;
  } 
  //printf("size: %u, %u\r\n", size, ((uint8_t *) p)[0]);
  memcpy((void *) msg_p, p, size);
  return 1;
}

static uint8_t get_assignment_idx(uint8_t id)
{
  uint8_t idx = 0;
  while (idx < NUM_ELEMENTS(message_assignment)) {
    if (id == message_assignment[idx].id) {
      return idx;
      break;
    }
    idx += 1;
  }
  return 255;
}

uint8_t message_layer_get_message(uint8_t id, uint8_t *msg)
{

  uint8_t idx = get_assignment_idx(id);
  if (idx == 255) {
    return 0;
  }
  for (uint16_t i = 0; i < message_assignment[idx].mixer_assignment_end - message_assignment[idx].mixer_assignment_start - 1; i++) {
    //printf("%u\r\n", i);
    uint8_t succ = read_message_from_mixer(i + message_assignment[idx].mixer_assignment_start, msg + i*MX_PAYLOAD_SIZE, MX_PAYLOAD_SIZE);
    if (!succ) {
      return 0;
    }
  }

  // the last piece is smaller than MX_PAYLOAD_SIZE and thus, we should only read this smaller piece, to not hurt any memory locations
  uint8_t succ = read_message_from_mixer(message_assignment[idx].mixer_assignment_end - 1, 
                          msg + (message_assignment[idx].size-message_assignment[idx].size_end), 
                          message_assignment[idx].size_end);
  if (!succ) {
      return 0;
  }
  return 1;
}

uint8_t message_layer_set_message(uint8_t id, uint8_t *message)
{
  uint8_t idx = get_assignment_idx(id);
  if (idx == 255) {
    return 0;
  }

  for (uint16_t i = 0; i < message_assignment[idx].mixer_assignment_end - message_assignment[idx].mixer_assignment_start; i++) {
    mixer_write(i + message_assignment[idx].mixer_assignment_start, message + i*MX_PAYLOAD_SIZE, MX_PAYLOAD_SIZE);
    //printf("%u, %u\r\n",(message + i*MX_PAYLOAD_SIZE)[0], i);
  }
  return 1;
}