#ifndef ROCKET_CONFIG_H
#define ROCKET_CONFIG_H

#include <stdint.h>
#include "gpi/tools.h"

#define MINIMUM(a,b) \
   ({ __typeof__ (a) _a = (a); \
       __typeof__ (b) _b = (b); \
     _a < _b ? _a : _b; })

#define LENGTH_TIME_SERIES (136)
#define NUM_KERNELS (84)
#define NUM_DILATIONS (5)
#define NUM_BIASES_PER_KERNEL (23)
#define NUM_FEATURES (NUM_KERNELS * NUM_DILATIONS * NUM_BIASES_PER_KERNEL)

#define NUM_TRAINING_TIMESERIES (23)
#define NUM_EVALUATION_TIMESERIES (50)

#define MAX_FEATURES_PER_DEVICE (4830)

typedef int8_t time_series_type_t;

static uint16_t devices_kernels_idx[] = {0, 42, 84,};

static uint16_t devices_num_features[] = {4830, 4830,};

#define DEVICE_NUM_FEATURES (devices_num_features[TOS_NODE_ID-1])

#define NUM_CLASSES (2)

#define BATCH_SIZE MINIMUM(128, NUM_TRAINING_TIMESERIES)

void init_rocket();

const time_series_type_t const **get_training_timeseries();

const uint8_t *get_training_labels();

const time_series_type_t const **get_evaluation_timeseries();

const uint8_t *get_evaluation_labels();

const uint16_t *get_kernels();

const uint32_t *get_dilations();

const float *get_quantiles();

float *get_biases();

#endif