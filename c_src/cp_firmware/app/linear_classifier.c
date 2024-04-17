#include "linear_classifier.h"
#include "rocket_config.h"
#include "conv.h"

#include <math.h>

#define PARAMETERLESS

static float weight[MAX_FEATURES_PER_DEVICE] = {0};
static float bias = 0.0;

static float d_bias = 0;
static float d_weight[MAX_FEATURES_PER_DEVICE] = {0};
static float features[MAX_FEATURES_PER_DEVICE];

#ifndef PARAMETERLESS
static float m_t_bias = 0;
static float v_t_bias = 0;
static float m_t_weight[MAX_FEATURES_PER_DEVICE] = {0};
static float v_t_weight[MAX_FEATURES_PER_DEVICE] = {0};

#define BETA_1 (0.99f)
#define BETA_2 (0.999f)
#define EPSILON (1e-8)

#define LEARNING_RATE (1e-4)
#else
static float l_i[MAX_FEATURES_PER_DEVICE] = {0};
static float g_i[MAX_FEATURES_PER_DEVICE] = {0};
static float reward[MAX_FEATURES_PER_DEVICE] = {0};
static float sum_of_gradients[MAX_FEATURES_PER_DEVICE] = {0}; 

static float l_i_bias = 0;
static float g_i_bias = 0;
static float reward_bias = 0;
static float sum_of_gradients_bias = 0; 
#endif

#define BATCH_SIZE 100

static float accuracy_filtered = 0;
static const float gamma = 0.01;

extern uint16_t __attribute__((section(".data")))	TOS_NODE_ID;

float classify_part(const time_series_type_t *in)
{
    // this is different than the central implementation. here we calculate the features assigned to our device.
    conv_multiple(in, features, get_kernels(), NUM_KERNELS, get_dilations(), NUM_DILATIONS, get_biases(), NUM_BIASES_PER_KERNEL);

    float temp = 0;
    for (uint32_t i = 0; i < devices_num_features[TOS_NODE_ID-1]; i++) {
        temp += features[i] * weight[i];
    }
    return temp + bias;
}

static float train_step(float out_pred, float out)
{
    out_pred = out_pred;
    for (uint32_t i = 0; i < devices_num_features[TOS_NODE_ID-1]; i++) {
        d_weight[i] -= features[i] * (out - out_pred);
    }
    d_bias -= (out - out_pred);

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

static inline float float_abs(float f) 
{
    return f > 0 ? f : -f;
}

static inline float float_max(float f1, float f2) 
{
    return f1 > f2 ? f1 : f2;
}

void update_weights(float out_pred, float out, uint32_t round_nmbr)
{
    accuracy_filtered = gamma*train_step(out_pred, out) + (1 - gamma) * accuracy_filtered;
    if (round_nmbr % BATCH_SIZE == BATCH_SIZE - 1) {

    #ifndef PARAMETERLESS
        float beta_1_pow = powf(BETA_1, (int) (round_nmbr / LENGTH_TIME_SERIES + 1));
        float beta_2_pow = powf(BETA_2, (int) (round_nmbr / LENGTH_TIME_SERIES + 1));
   #endif
        
        for (int i = 0; i < devices_num_features[TOS_NODE_ID-1]; i++) {

            #ifndef PARAMETERLESS
            m_t_weight[i] = BETA_1 * m_t_weight[i] + (1 - BETA_1) * d_weight[i];
            v_t_weight[i] = BETA_2 * v_t_weight[i] + (1 - BETA_2) * d_weight[i] * d_weight[i];

            float mt_hat = m_t_weight[i] / (1 - beta_1_pow);
            float vt_hat = v_t_weight[i] / (1 - beta_2_pow);

            weight[i] -= LEARNING_RATE * mt_hat / (sqrtf(vt_hat) + EPSILON);  //d_weight[i]; // 
            #else
            d_weight[i] = -d_weight[i];
            l_i[i] = float_max(l_i[i], float_abs(d_weight[i]));
            g_i[i] = g_i[i] + float_abs(d_weight[i]);
            reward[i] = float_max(reward[i] + weight[i]*d_weight[i], 0);
            sum_of_gradients[i] += d_weight[i];
            //printf("%f\n", d_weight[i]);
            weight[i] = sum_of_gradients[i] / (l_i[i]*float_max(g_i[i]+l_i[i], 100*l_i[i]) + 1e-7) * (l_i[i] + reward[i]);  
            #endif

            d_weight[i] = 0;
        }
        #ifndef PARAMETERLESS
        m_t_bias = BETA_1 * m_t_bias + (1 - BETA_1) * d_bias;
        v_t_bias = BETA_2 * v_t_bias + (1 - BETA_2) * d_bias * d_bias;

        float mt_hat = m_t_bias / (1 - beta_1_pow);
        float vt_hat = v_t_bias / (1 - beta_2_pow);
        bias -= LEARNING_RATE * mt_hat / (sqrtf(vt_hat) + EPSILON);

        #else
        d_bias = -d_bias;
        l_i_bias = float_max(l_i_bias, float_abs(d_bias));
        g_i_bias = g_i_bias + float_abs(d_bias);
        reward_bias = float_max(reward_bias + bias*d_bias, 0);
        sum_of_gradients_bias += d_bias;
        bias = sum_of_gradients_bias / (l_i_bias*float_max(g_i_bias+l_i_bias, 100*l_i_bias) + 1e-7) * (l_i_bias + reward_bias);
        d_bias = 0.0f;
        #endif
        d_bias = 0;
        if (TOS_NODE_ID != 1) {
          bias = 0;
        }

        printf("Epoch: %u, Accuracy: %u\n", (uint32_t) round_nmbr, (uint32_t) (accuracy_filtered*100));
    }
}