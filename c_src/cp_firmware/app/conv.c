#include "conv.h"
#include "rocket_config.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#define min(a,b) \
    ({ typeof (a) _a = (a); \
    typeof (b) _b = (b); \
    _a < _b ? _a : _b; })

  
extern uint16_t __attribute__((section(".data"))) TOS_NODE_ID;

static void mult_timeseries(const time_series_type_t *in, float *out, time_series_type_t scalar)
{
    for (uint32_t i = 0; i < LENGTH_TIME_SERIES; i++) {
        out[i] = scalar * in[i];
    }
}

void mult_1(const time_series_type_t *in, float *out)
{
    mult_timeseries(in, out, (time_series_type_t) -1);
}

void mult3(const time_series_type_t *in, float *out)
{
    mult_timeseries(in, out, (time_series_type_t) 3);
}


/**
 * convolution of timeseries with -1, as describes in section 3.2.3 of mini rocket paper
*/
void conv_1(const float *in_1, float *out, uint32_t dilation)
{
    for (uint32_t i = 0; i < LENGTH_TIME_SERIES; i++) {
        out[i] = 0;
        for (uint8_t j = 0; j < 9; j++) {
            const uint32_t in_index = i - 4 * dilation + j*dilation;
            
            // padding
            if (in_index < 0 || in_index >= LENGTH_TIME_SERIES) {
                continue;
            }

            out[i] += in_1[in_index];
        }
    }
}

/**
 * convolution of timeseries with 3, as described in section 3.2.3 of mini rocket paper
 * @param kernel a bit array, containint 0, if the kernel is -1 and 1 if the kernel is 2, e.g. 100101000 = [2, -1, -1, 2, -1, 2, -1, -1, -1]
*/
void conv3(const float *in3, float *out, uint16_t kernel, uint32_t dilation)
{
    for (uint32_t i = 0; i < LENGTH_TIME_SERIES; i++) {
        out[i] = 0;
        for (uint8_t j = 0; j < 9; j++) {
            if (kernel & (1 << j)) {
                const uint32_t in_index = i - 4 * dilation + j*dilation;
                
                // padding
                if (in_index < 0 || in_index >= LENGTH_TIME_SERIES) {
                    continue;
                }

                out[i] += in3[in_index];
            }
        }
    }
}

void add_timeseries(const float *in1, const float *in2, time_series_type_t *out)
{
    for (uint32_t i = 0; i < LENGTH_TIME_SERIES; i++) {
        out[i] = in1[i] + in2[i];
    }
}

static int cmpfunc (const void * a, const void * b) {
   return ( *(float*)a > *(float*)b );
}

void calc_bias(const time_series_type_t *in, float *bias, uint16_t *kernels, uint32_t number_kernels_total, uint32_t *dilations, uint32_t number_dilations, float *quantiles, uint32_t biases_per_kernel)
{
    mult_1(in, timeseries_1);
    mult3(in, timeseries3);

    uint32_t bias_idx = 0;
    uint32_t quantiles_idx = 0;
    for (uint32_t dilation_idx = 0; dilation_idx < number_dilations; dilation_idx++) {

        conv_1(timeseries_1, conv_timeseries_1, dilations[dilation_idx]);

        quantiles_idx += biases_per_kernel * devices_kernels_idx[TOS_NODE_ID-1];
        for (uint32_t kernel_idx = devices_kernels_idx[TOS_NODE_ID-1]; kernel_idx < devices_kernels_idx[TOS_NODE_ID]; kernel_idx++) {

            conv3(timeseries3, conv_timeseries3, kernels[kernel_idx], dilations[dilation_idx]);

            // to addition in place to save memory
            add_timeseries(conv_timeseries_1, conv_timeseries3, conv_timeseries3);

            qsort(conv_timeseries3, LENGTH_TIME_SERIES, sizeof(float), cmpfunc);

            /*for (int i = 0; i < LENGTH_TIME_SERIES; i++) {
              printf("%d\n", (int32_t) (conv_timeseries3[i]*1000));
            }*/

            for (uint32_t i = 0; i < biases_per_kernel; i++) {
                bias[bias_idx] = conv_timeseries3[(int) min((LENGTH_TIME_SERIES * quantiles[quantiles_idx]), LENGTH_TIME_SERIES-1)];
                //printf("%u: %u, %d\n", quantiles_idx, kernels[kernel_idx], (int32_t) (bias[bias_idx]*1000));
                bias_idx++;
                quantiles_idx++;
            }
        }
        quantiles_idx += biases_per_kernel * (number_kernels_total - devices_kernels_idx[TOS_NODE_ID]);
    }
}


void conv_multiple(const time_series_type_t *in, float *features, uint16_t *kernels, uint32_t number_kernels, uint32_t *dilations, uint32_t number_dilations, float *biases, uint32_t number_biases_per_kernel)
{
    mult_1(in, timeseries_1);
    mult3(in, timeseries3);

    uint32_t feature_idx = 0;
    for (uint32_t dilation_idx = 0; dilation_idx < number_dilations; dilation_idx++) {

        conv_1(timeseries_1, conv_timeseries_1, dilations[dilation_idx]);


        for (uint32_t kernel_idx = devices_kernels_idx[TOS_NODE_ID-1]; kernel_idx < devices_kernels_idx[TOS_NODE_ID]; kernel_idx++) {

            conv3(timeseries3, conv_timeseries3, kernels[kernel_idx], dilations[dilation_idx]);

            // to addition in place to save memory
            add_timeseries(conv_timeseries_1, conv_timeseries3, conv_timeseries3);

            for (uint32_t bias_idx = 0; bias_idx < number_biases_per_kernel; bias_idx++) {
                features[feature_idx] = 0;

                for (uint32_t i = 0; i < LENGTH_TIME_SERIES; i++) {
                    if (conv_timeseries3[i] > biases[feature_idx]) {
                        features[feature_idx]++;
                    }
                }
                features[feature_idx] /= LENGTH_TIME_SERIES;
                feature_idx++;
            }
        }
    }
}
