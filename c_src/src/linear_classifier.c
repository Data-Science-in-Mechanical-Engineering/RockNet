#include "linear_classifier.h"
#include "rocket_config.h"
#include "conv.h"

#include <math.h>

static float weight[NUM_FEATURES] = {1e-6};
static float bias = 1.0;
static float m_t_bias = 0;
static float v_t_bias = 0;
static float d_bias = 0;
static float d_weight[NUM_FEATURES] = {0};
static float m_t_weight[NUM_FEATURES] = {0};
static float v_t_weight[NUM_FEATURES] = {0};
static float features[NUM_FEATURES];

#define BETA_1 (0.99f)
#define BETA_2 (0.999f)
#define EPSILON (1e-8)

#define LEARNING_RATE (1e-5)

#define BATCH_SIZE 1

float classify(float *in)
{
    float temp = 0;
    for (uint32_t i = 0; i < NUM_FEATURES; i++) {
        temp += in[i] / LENGTH_TIME_SERIES * weight[i];
    }

    return tanhf(temp + bias);
}

static int train_step(float *in, float out)
{
    conv_multiple(in, features, get_kernels(), NUM_KERNELS, get_dilations(), NUM_DILATIONS, get_biases(), NUM_BIASES_PER_KERNEL);

    float out_pred = classify(features);
    // printf("Features %f, %f, %f\n", features[0], features[1], features[2]);
    for (uint32_t i = 0; i < NUM_FEATURES; i++) {
        d_weight[i] -= (features[i] / LENGTH_TIME_SERIES * (out - out_pred) * (1 - out_pred*out_pred));
    }
    d_bias -= (out - out_pred) * (1 - out_pred*out_pred);
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
    const float gamma = 0.001;
    for (uint64_t epoch = 0; epoch < 100000; epoch++) {
        if (epoch % BATCH_SIZE == BATCH_SIZE - 1) {
            float beta_1_pow = powf(BETA_1, (int) (epoch / LENGTH_TIME_SERIES + 1));
            float beta_2_pow = powf(BETA_2, (int) (epoch / LENGTH_TIME_SERIES + 1));
            for (int i = 0; i < NUM_FEATURES; i++) {
                m_t_weight[i] = BETA_1 * m_t_weight[i] + (1 - BETA_1) * d_weight[i];
                v_t_weight[i] = BETA_2 * v_t_weight[i] + (1 - BETA_2) * d_weight[i] * d_weight[i];

                float mt_hat = m_t_weight[i] / (1 - beta_1_pow);
                float vt_hat = v_t_weight[i] / (1 - beta_2_pow);

                weight[i] -= LEARNING_RATE * mt_hat / (sqrtf(vt_hat) + EPSILON);
                d_weight[i] = 0;
            }
            m_t_bias = BETA_1 * m_t_bias + (1 - BETA_1) * d_bias;
            v_t_bias = BETA_2 * v_t_bias + (1 - BETA_2) * d_bias * d_bias;

            float mt_hat = m_t_bias / (1 - beta_1_pow);
            float vt_hat = v_t_bias / (1 - beta_2_pow);
            bias -= LEARNING_RATE * mt_hat / (sqrtf(vt_hat) + EPSILON);
            d_bias = 0;
            printf("Epoch: %u, Accuracy: %f \n", epoch, accuracy_filtered);
        }
        accuracy_filtered = gamma*train_step(get_timeseries()[epoch % NUM_TIMESERIES], get_labels()[epoch % NUM_TIMESERIES]) + (1 - gamma) * accuracy_filtered;
    }
}
