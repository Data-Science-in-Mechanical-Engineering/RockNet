#ifndef ROCKET_CONFIG_H
#define ROCKET_CONFIG_H

#include <stdint.h>

#define LENGTH_TIME_SERIES (136)
#define NUM_KERNELS (84)
#define NUM_DILATIONS (5)
#define NUM_BIASES_PER_KERNEL (23)
#define NUM_FEATURES (NUM_KERNELS * NUM_DILATIONS * NUM_BIASES_PER_KERNEL)

#define NUM_TIMESERIES (23)

#define MAX_FEATURES_PER_DEVICE ()

typedef  time_series_type_t;

#define DEVICE_NUM_FEATURES (NUM_FEATURES)

#define MAX_FEATURES_PER_DEVICE (NUM_FEATURES)

#define NUM_CLASSES (2)

void init_rocket();

const time_series_type_t const **get_timeseries();

const uint8_t *get_labels();

const uint16_t *get_kernels();

const uint32_t *get_dilations();

const float *get_quantiles();

float *get_biases();

#endif