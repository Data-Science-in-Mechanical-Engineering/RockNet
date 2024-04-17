#ifndef ROCKET_CONFIG_H
#define ROCKET_CONFIG_H

#include <stdint.h>

#define LENGTH_TIME_SERIES (101)
#define NUM_KERNELS (84)
#define NUM_DILATIONS (4)
#define NUM_BIASES_PER_KERNEL (29)
#define NUM_FEATURES (NUM_KERNELS * NUM_DILATIONS * NUM_BIASES_PER_KERNEL)

#define NUM_TIMESERIES (1000)

#define MAX_FEATURES_PER_DEVICE (696)

#define NUM_CLASSES (10)

typedef int8_t time_series_type_t;

static uint16_t devices_kernels_idx[] = {0, 6, 12, 18, 24, 30, 36, 42, 48, 54, 59, 64, 69, 74, 79, 84,};

static uint16_t devices_num_features[] = {696, 696, 696, 696, 696, 696, 696, 696, 696, 580, 580, 580, 580, 580, 580,};

void init_rocket();

const time_series_type_t const **get_timeseries();

const float *get_labels();

const uint16_t *get_kernels();

const uint32_t *get_dilations();

const float *get_quantiles();

float *get_biases();

#endif