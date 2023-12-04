#include <stdio.h>
#include "conv.h"

static float in_timeseries[LENGTH_TIME_SERIES] = {1.0, 2.0, -3.0};
static uint16_t kernels[3] = {0b111000000, 0b111000000, 0b111000000};
static uint32_t dilations[2] = {1, 2};
static float biases[2] = {-1.0, 1.0};

int main()
{
    float features[12] = {0};
    conv_multiple(in_timeseries, features, kernels, 3, dilations, 2, biases, 2);

    for (int i = 0; i < 12; i++) {
        printf("%f\n", features[i]);
    }
    return 0;
}