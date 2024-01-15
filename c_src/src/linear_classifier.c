#include "linear_classifier.h"
#include "rocket_config.h"
#include "conv.h"

#include <math.h>

//#define PARAMETERLESS

static float weight[NUM_FEATURES] = {0};
static float bias = 0.0;
static float m_t_bias = 0;
static float v_t_bias = 0;
static float d_bias = 0;
static float d_weight[NUM_FEATURES] = {0};
static float m_t_weight[NUM_FEATURES] = {0};
static float v_t_weight[NUM_FEATURES] = {0};
static float features[NUM_FEATURES];

static float l_i[NUM_FEATURES] = {0};
static float g_i[NUM_FEATURES] = {0};
static float reward[NUM_FEATURES] = {0};
static float sum_of_gradients[NUM_FEATURES] = {0}; 

static float l_i_bias = 0;
static float g_i_bias = 0;
static float reward_bias = 0;
static float sum_of_gradients_bias = 0; 

#define BETA_1 (0.99f)
#define BETA_2 (0.999f)
#define EPSILON (1e-8)

#define LEARNING_RATE (1e-4)

#define BATCH_SIZE 100

float classify(float *in)
{
    float temp = 0;
    for (uint32_t i = 0; i < NUM_FEATURES; i++) {
        temp += in[i] * weight[i];
    }

    #ifdef PARAMETERLESS
    return temp + bias;
    #else
    return tanhf(temp + bias);
    #endif
}

static float train_step(float *in, float out)
{
    conv_multiple(in, features, get_kernels(), NUM_KERNELS, get_dilations(), NUM_DILATIONS, get_biases(), NUM_BIASES_PER_KERNEL);

    float out_pred = classify(features);
    // printf("Features %f, %f, %f\n", features[100], features[1001], features[2000]);
    for (uint32_t i = 0; i < NUM_FEATURES; i++) {
        #ifdef PARAMETERLESS
        d_weight[i] -= features[i] * (out - out_pred);
        #else
        d_weight[i] -= (features[i] * (out - out_pred) * ((1 - out_pred*out_pred)));
        #endif
    }
    #ifdef PARAMETERLESS
    d_bias -= (out - out_pred);
    #else
    d_bias -= (out - out_pred) * (1 - out_pred*out_pred);
    #endif
    // printf("out: %f, out_pred: %f \n", out, out_pred);
    
    //return (out - out_pred) * (out - out_pred);

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

static void init_float_array(float *array, uint16_t length, float value)
{
    for (uint16_t i = 0; i < length; i++) {
        array[i] = value;
    }
}

static inline float float_abs(float f) 
{
    return f > 0 ? f : -f;
}

static inline float float_max(float f1, float f2) 
{
    return f1 > f2 ? f1 : f2;
}

void train()
{
    printf("Starting training\n");
    float accuracy_filtered = 0;
    const float gamma = 0.01;
    uint16_t count = 0;
    for (uint64_t epoch = 0; epoch < 100000; epoch++) {
        if (epoch % BATCH_SIZE == BATCH_SIZE - 1) {
            #ifdef PARAMETERLESS
            for (int i = 0; i < NUM_FEATURES; i++) {
                d_weight[i] = -d_weight[i];
                l_i[i] = float_max(l_i[i], float_abs(d_weight[i]));
                g_i[i] = g_i[i] + float_abs(d_weight[i]);
                reward[i] = float_max(reward[i] + weight[i]*d_weight[i], 0);
                sum_of_gradients[i] += d_weight[i];
                //printf("%f\n", d_weight[i]);
                weight[i] = sum_of_gradients[i] / (l_i[i]*float_max(g_i[i]+l_i[i], 100*l_i[i]) + 1e-7) * (l_i[i] + reward[i]);
                d_weight[i] = 0.0f;
                //printf("%f\n", sum_of_gradients[i]);
            }
            count += 1;

            d_bias = -d_bias;
            l_i_bias = float_max(l_i_bias, float_abs(d_bias));
            g_i_bias = g_i_bias + float_abs(d_bias);
            reward_bias = float_max(reward_bias + bias*d_bias, 0);
            sum_of_gradients_bias += d_bias;
            printf("%f\n", d_bias);
            bias = sum_of_gradients_bias / (l_i_bias*float_max(g_i_bias+l_i_bias, 100*l_i_bias) + 1e-7) * (l_i_bias + reward_bias);
            d_bias = 0.0f;


            #else
            float beta_1_pow = powf(BETA_1, (int) (epoch / LENGTH_TIME_SERIES + 1));
            float beta_2_pow = powf(BETA_2, (int) (epoch / LENGTH_TIME_SERIES + 1));
            for (int i = 0; i < NUM_FEATURES; i++) {
                m_t_weight[i] = BETA_1 * m_t_weight[i] + (1 - BETA_1) * d_weight[i];
                v_t_weight[i] = BETA_2 * v_t_weight[i] + (1 - BETA_2) * d_weight[i] * d_weight[i];

                float mt_hat = m_t_weight[i] / (1 - beta_1_pow);
                float vt_hat = v_t_weight[i] / (1 - beta_2_pow);

                weight[i] -= LEARNING_RATE * mt_hat / (sqrtf(vt_hat) + EPSILON);  //d_weight[i]; // 
                d_weight[i] = 0;
            }
            m_t_bias = BETA_1 * m_t_bias + (1 - BETA_1) * d_bias;
            v_t_bias = BETA_2 * v_t_bias + (1 - BETA_2) * d_bias * d_bias;

            float mt_hat = m_t_bias / (1 - beta_1_pow);
            float vt_hat = v_t_bias / (1 - beta_2_pow);
            bias -= LEARNING_RATE * mt_hat / (sqrtf(vt_hat) + EPSILON);
            d_bias = 0;
            #endif
            printf("Epoch: %u, Accuracy: %u\n", (uint32_t) epoch, (uint32_t) (accuracy_filtered*100));
        }
        accuracy_filtered = gamma*train_step(get_timeseries()[epoch % NUM_TIMESERIES], get_labels()[epoch % NUM_TIMESERIES]) + (1 - gamma) * accuracy_filtered;
    }
}
