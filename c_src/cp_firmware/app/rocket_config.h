#ifndef ROCKET_CONFIG_H
#define ROCKET_CONFIG_H

#include <stdint.h>

#define LENGTH_TIME_SERIES (101)
#define NUM_KERNELS (84)
#define NUM_DILATIONS (4)
#define NUM_BIASES_PER_KERNEL (29)
#define NUM_FEATURES (NUM_KERNELS * NUM_DILATIONS * NUM_BIASES_PER_KERNEL)

#define NUM_TIMESERIES (1000)

#define MAX_FEATURES_PER_DEVICE (1972)

typedef int8_t time_series_type_t;

static uint16_t devices_kernels_idx[] = {0, 17, 34, 51, 68, 84,};

static uint16_t devices_num_features[] = {1972, 1972, 1972, 1972, 1856,};

void init_rocket();

const time_series_type_t const **get_timeseries();

const float *get_labels();

const uint16_t *get_kernels();

const uint32_t *get_dilations();

const float *get_quantiles();

float *get_biases();

#endif