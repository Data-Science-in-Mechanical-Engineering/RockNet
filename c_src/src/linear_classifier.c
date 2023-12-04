#include "linear_classifier.h"
#include "rocket_config.h"
#include "conv.h"

#include <math.h>

static float weight[NUM_FEATURES] = {1e-6};
static float bias = 0;
static float d_bias = 0;
static float d_weight[NUM_FEATURES] = {0};
static float features[NUM_FEATURES];

#define LEARNING_RATE (1e-9)

float classify(float *in)
{
    float temp = 0;
    for (uint32_t i = 0; i < NUM_FEATURES; i++) {
        temp += in[i] * weight[i];
    }

    return tanhf(temp + bias);
}

static int train_step(float *in, float out)
{
    conv_multiple(in, features, get_kernels(), NUM_KERNELS, get_dilations() ,NUM_DILATIONS, get_biases(), NUM_BIASES_PER_KERNEL);

    float out_pred = classify(features);
    for (uint32_t i = 0; i < NUM_FEATURES; i++) {
        d_weight[i] += LEARNING_RATE * (features[i] * (out - out_pred) * (1 - out_pred*out_pred));
    }
    d_bias += LEARNING_RATE * (out - out_pred) * (1 - out_pred*out_pred);
    //printf("out: %f, out_pred: %f\n", out, out_pred);
    
    if (out < 0 && out_pred < 0) {
        return 1;
    } 
    if (out > 0 && out_pred > 0) {
        return 1;
    } 
    else {
        return 0;
    }
}

void train()
{
    printf("Starting training\n");
    float accuracy_filtered = 0;
    const float gamma = 0.01;
    for (uint64_t epoch = 0; epoch < 100000; epoch++) {
        if (epoch % 100 == 99) {
            for (int i = 0; i < NUM_FEATURES; i++) {
                weight[i] += d_weight[i];
                d_weight[i] = 0;
            }
            bias += d_bias;
            d_bias = 0;
            printf("%f\n", accuracy_filtered);
        }
        accuracy_filtered = gamma*train_step(get_timeseries()[epoch % NUM_TIMESERIES], get_labels()[epoch % NUM_TIMESERIES]) + (1 - gamma) * accuracy_filtered;
    }
}
