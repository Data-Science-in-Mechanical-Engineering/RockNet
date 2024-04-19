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
#include "rocket_config.h"
#include <stdint.h>

static uint32_t round_nmbr = 0;

static uint16_t rx_time_series_last_round;
static time_series_type_t timeseries[LENGTH_TIME_SERIES];
static uint8_t label = 0;

static float linear_classification_part[NUM_CLASSES] = {0};

static ap_message_t message;
static ap_message_t ts_message;

extern uint16_t __attribute__((section(".data"))) TOS_NODE_ID;


static uint8_t communication_finished_callback(ap_message_t *data, uint16_t size)
{
  float cummulative[NUM_CLASSES] = {0};
  time_series_type_t timeseries[LENGTH_TIME_SERIES];
  uint16_t time_series_data_idx = 0xFFFF;

  // printf("size %u\r\n", size);

  // parse messages
  for (uint16_t i = 0; i < size; i++) {
    if (data[i].header.type == TYPE_METADATA) {
      round_nmbr = data[i].metadata_message.round_nmbr;
    } else {
      if (data[i].header.type == TYPE_CLASSIFICATION) {
        for (uint8_t j = 0; j < NUM_CLASSES; j++) {
          //printf("rx: %d\r\n", (int) (data[i].classification_message.classification[j] * 100));
          cummulative[j] += data[i].classification_message.classification[j];
        }
        //printf("-------------\r\n");
        // printf("Cummulative: %d, %d, %d, %d\n", (int32_t) (cummulative[0]*10000), (int32_t) (cummulative[1]*10000), (int32_t) (cummulative[2]*10000), (int32_t) (cummulative[3]*10000));
      } else {
        if (data[i].header.type == TYPE_TIME_SERIES) {
          time_series_data_idx = i;
        }
      }
    }
  }
  if (time_series_data_idx != 0xFFFF) {
      //printf("label rx %u, %u\r\n", data[time_series_data_idx].time_series_message.label, time_series_data_idx);
  }
  if (rx_time_series_last_round) {
    //printf("Cummulative: %d\n", (int32_t) (cummulative*10000));
    update_weights(cummulative, label, round_nmbr);
  }

  // init as zero, so it is zero in case, we have not received the timeseries.
  for (uint8_t i = 0; i < NUM_CLASSES; i++) {
    linear_classification_part[i] = 0;
  }

  // received time series.
  if (time_series_data_idx != 0xFFFF) {
    rx_time_series_last_round = 1;
    for (uint16_t j = 0; j < LENGTH_TIME_SERIES; j++) {
      timeseries[j] = data[time_series_data_idx].time_series_message.data[j];
    }

    label = data[time_series_data_idx].time_series_message.label;

    // calculate part of linear classification
    //printf("-------------------------");
    classify_part(timeseries, linear_classification_part);

  } else {
    rx_time_series_last_round = 0;
    //printf("ggggggggggggggg");
  }
  // printf("---------\r\n");
  return 0;
} 
                
static uint16_t communication_starts_callback(ap_message_t **data)
{
  // write timeseries in tx_message
  data[0] = &message;
  for (uint8_t i = 0; i < NUM_CLASSES; i++) {
    data[0]->classification_message.classification[i] = linear_classification_part[i];
    //printf("lc tx: %d\r\n", (int) (linear_classification_part[i] * 100));
  }
  //printf("--------\r\n");
  // write timeseries in tx_message
  if (TOS_NODE_ID == 1) {
    data[1] = &ts_message;
    const time_series_type_t const **tsp = get_timeseries();
    for (uint16_t j = 0; j < LENGTH_TIME_SERIES; j++) {
      data[1]->time_series_message.data[j] = tsp[round_nmbr % NUM_TIMESERIES][j];
    }
    data[1]->time_series_message.label = get_labels()[round_nmbr % NUM_TIMESERIES];
    return 2;
  }
  return 1;
}

void run_rocket_os(uint8_t id)
{ 
  printf("Init device %u started\n", TOS_NODE_ID);

  message.header.id = TOS_NODE_ID;
  message.header.type = TYPE_CLASSIFICATION;

  ts_message.header.id = 254;
  ts_message.header.type = TYPE_TIME_SERIES;

  init_linear_classifier();

  init_cp_os(&communication_finished_callback, &communication_starts_callback, id);
  
  printf("Init device %u finished\n", TOS_NODE_ID);
  run();
}