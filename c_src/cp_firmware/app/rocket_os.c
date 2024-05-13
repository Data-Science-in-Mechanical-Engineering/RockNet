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

static uint32_t round_nmbr = -1lu;

static uint16_t rx_time_series_last_round;
static time_series_type_t timeseries[LENGTH_TIME_SERIES];
static uint8_t label = 0;

static float linear_classification_part[NUM_CLASSES] = {0};

static ap_message_t message;
static ap_message_t ts_message;

static uint8_t rocket_node_idx = 0;


static training_state_t training_state = IDLE;
static uint32_t batch_time = 0;
static float evaluation_accuracy = 0;
 static float num_summands_evaluation_accuracy = 0;

static uint32_t current_training_ts_idx = 0;
static uint32_t current_evaluation_ts_idx = 0;


static uint8_t communication_finished_callback(ap_message_t *data, uint16_t size)
{
  float cummulative[NUM_CLASSES] = {0};
  time_series_type_t timeseries[LENGTH_TIME_SERIES];
  uint16_t time_series_data_idx = 0xFFFF;

  // parse messages
  for (uint16_t i = 0; i < size; i++) {
    if (data[i].header.type == TYPE_METADATA) {
      round_nmbr = data[i].metadata_message.round_nmbr;
    } else {
      if (data[i].header.type == TYPE_CLASSIFICATION) {
        for (uint8_t j = 0; j < NUM_CLASSES; j++) {
          cummulative[j] += data[i].classification_message.classification[j];
        }
      } else {
        if (data[i].header.type == TYPE_TIME_SERIES) {
          time_series_data_idx = i;
        }
      }
    }
  }

  // calculate current batch_time and state out of round_nmbr
  // sync to current round
  if (training_state == IDLE && round_nmbr != -1lu) {
    uint32_t current_time = round_nmbr % (NUM_TRAINING_TIMESERIES + NUM_EVALUATION_TIMESERIES);

    if (current_time < NUM_EVALUATION_TIMESERIES) {
      current_evaluation_ts_idx = current_time+2;
      current_training_ts_idx = 0;
      training_state = EVALUATION;
    } else {
      current_training_ts_idx = current_time - NUM_EVALUATION_TIMESERIES+2;
      current_evaluation_ts_idx = 0;
      training_state = TRAINING;
    }
  }
  //printf("%lu\r\n", round_nmbr);
  //printf(":%lu\r\n", current_training_ts_idx);
  //printf(":%lu\r\n", current_evaluation_ts_idx);

  uint8_t updated_gradients = 0;
  
  switch (training_state) {
    case TRAINING:
      { 
        if (rx_time_series_last_round) {
          calculate_and_accumulate_gradient(cummulative, label);
          if (batch_time > BATCH_SIZE - 1) {
            batch_time = 0;
            update_weights();
            updated_gradients = 1;
            printf("Gradient update\r\n");
          }
        }

        batch_time++;

        // we have a 2 round delay, i.e., in the last 2 rounds of the training, we need to already send the evaluation datas.
        if (current_training_ts_idx == NUM_TRAINING_TIMESERIES-1) {
          current_evaluation_ts_idx = 0;
        }
        if (current_training_ts_idx == NUM_TRAINING_TIMESERIES) {
          current_evaluation_ts_idx = 1;
          training_state = EVALUATION;
          if (!updated_gradients) {
            update_weights();
            printf("Gradient update\r\n");
          }
        }
        current_training_ts_idx++;
      }
      break;
    case EVALUATION:
      {
        if (rx_time_series_last_round) {
          // calculated correct label?
          uint8_t pred_idx = get_max_idx(cummulative, NUM_CLASSES);
          batch_time = 0;
          if (pred_idx == label) {
            evaluation_accuracy++;
          }
          num_summands_evaluation_accuracy++;
        }

        
        if (current_evaluation_ts_idx == NUM_EVALUATION_TIMESERIES-1) {
          current_training_ts_idx = 0;
        }
        if (current_evaluation_ts_idx == NUM_EVALUATION_TIMESERIES) {
          current_training_ts_idx = 1;
 
          current_evaluation_ts_idx = 0;
          current_training_ts_idx = 0;
          training_state = TRAINING;

          printf("Accuracy: %u\r\n", (uint16_t) (1000 * evaluation_accuracy/num_summands_evaluation_accuracy));

          evaluation_accuracy = 0;
          num_summands_evaluation_accuracy = 0;
        } 
        current_evaluation_ts_idx++;
      }
      break;
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
    classify_part(timeseries, linear_classification_part);

  } else {
    rx_time_series_last_round = 0;
  }
  return 0;
} 
                
static uint16_t communication_starts_callback(ap_message_t **data)
{
  // write timeseries in tx_message
  data[0] = &message;
  for (uint8_t i = 0; i < NUM_CLASSES; i++) {
    data[0]->classification_message.classification[i] = linear_classification_part[i];
  }
  // write timeseries in tx_message
  if (rocket_node_idx == 0) {
    data[1] = &ts_message;
    const time_series_type_t *ts;
    uint8_t label = 0; 
    // determine, if to send training or evaluation data
    switch (training_state) {
      case TRAINING:
        {
          // 2 round before siwtching to the evaluation, we already need to send evaluation timeseries, as we have a delay.
          // (the gradients, we calculate for the next times are the gradients for the timeseries, we currently received)
          if (current_training_ts_idx <  NUM_TRAINING_TIMESERIES) {
            ts = get_training_timeseries()[current_training_ts_idx];
            label = get_training_labels()[current_training_ts_idx];
          } else {
            ts = get_evaluation_timeseries()[current_evaluation_ts_idx];
            label = get_evaluation_labels()[current_evaluation_ts_idx];
          }

          data[1]->time_series_message.training = 1;

        }
        break;
      case EVALUATION:
        {
          // 1 round before siwtching to the training, we already need to send training timeseries, as we have a delay.
          if (current_evaluation_ts_idx <  NUM_EVALUATION_TIMESERIES) {
            ts = get_evaluation_timeseries()[current_evaluation_ts_idx];
            label = get_evaluation_labels()[current_evaluation_ts_idx];
          } else {
            printf("%u\n", current_training_ts_idx);
            ts = get_training_timeseries()[current_training_ts_idx];
            label = get_training_labels()[current_training_ts_idx];
          }
        }
        break;
      case IDLE:
        return 1;
    }
    for (uint16_t j = 0; j < LENGTH_TIME_SERIES; j++) {
      data[1]->time_series_message.data[j] = ts[j];
    }
    data[1]->time_series_message.label = label;

    return 2;
  }
  return 1;
}

void run_rocket_os(uint8_t id)
{ 
  printf("Init device %u started\n", id);

  rocket_node_idx = get_rocket_node_idx(id);

  training_state = IDLE;

  message.header.id = id;
  message.header.type = TYPE_CLASSIFICATION;

  ts_message.header.id = 254;
  ts_message.header.type = TYPE_TIME_SERIES;

  init_linear_classifier(id);

  init_cp_os(&communication_finished_callback, &communication_starts_callback, id);
  
  printf("Init device %u finished\n", id);
  run();
}