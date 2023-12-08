#ifndef CONV_H
#define CONV_H

#include <stdint.h>

#include "rocket_config.h"

static float timeseries_1[LENGTH_TIME_SERIES];
static float timeseries3[LENGTH_TIME_SERIES];

static float conv_timeseries_1[LENGTH_TIME_SERIES];
static float conv_timeseries3[LENGTH_TIME_SERIES];


void mult_1(const time_series_type_t *in, float *out);

void mult3(const time_series_type_t *in, float *out);

void conv_1(const float *in_1, float *out, uint32_t dilation);

void conv3(const float *in3, float *out, uint16_t kernel, uint32_t dilation);

void add_timeseries(const float *in1, const float *in2, time_series_type_t *out);

void calc_bias(const time_series_type_t *in, float *bias, uint16_t *kernels, uint32_t number_kernels, uint32_t *dilations, uint32_t number_dilations, float *quantiles, uint32_t biases_per_kernel);

void conv_multiple(const time_series_type_t *in, float *features, uint16_t *kernels, uint32_t number_kernels, uint32_t *dilations, uint32_t number_dilations, float *biases, uint32_t number_biases);


#endif