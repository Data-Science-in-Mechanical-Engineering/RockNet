#ifndef ROCKET_CONFIG_H
#define ROCKET_CONFIG_H

#include <stdint.h>

#define LENGTH_TIME_SERIES (101)
#define NUM_KERNELS (84)
#define NUM_DILATIONS (4)
#define NUM_BIASES_PER_KERNEL (29)
#define NUM_FEATURES (NUM_KERNELS * NUM_DILATIONS * NUM_BIASES_PER_KERNEL)

#define NUM_TIMESERIES (1000)

void init_rocket();

float **get_timeseries();

float *get_labels();

uint16_t *get_kernels();

uint32_t *get_dilations();

float *get_quantiles();

float *get_biases();

#endif