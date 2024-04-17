#include "linear_classifier.h"
#include "rocket_config.h"
#include "conv.h"

#include <math.h>

static float weight[NUM_CLASSES * MAX_FEATURES_PER_DEVICE] = {0};
static float bias[NUM_CLASSES] = {0};
static float m_t_bias[NUM_CLASSES] = 0;
static float v_t_bias[NUM_CLASSES] = 0;
static float d_bias[NUM_CLASSES] = 0;
static float d_weight[MAX_FEATURES_PER_DEVICE] = {0};
static float m_t_weight[NUM_CLASSES * MAX_FEATURES_PER_DEVICE] = {0};
static float v_t_weight[NUM_CLASSES * MAX_FEATURES_PER_DEVICE] = {0};
static float features[NUM_CLASSES * MAX_FEATURES_PER_DEVICE];

static float out_exp[NUM_CLASSES];

#define BETA_1 (0.99f)
#define BETA_2 (0.999f)
#define EPSILON (1e-8)

#define LEARNING_RATE (1e-4)

#define BATCH_SIZE 100

static float accuracy_filtered = 0;
static const float gamma = 0.01;

extern uint16_t __attribute__((section(".data")))	TOS_NODE_ID;

static uint32_t t=0;

float classify_part(const time_series_type_t *in)
{
    // this is different than the central implementation. here we calculate the features assigned to our device.
    conv_multiple(in, features, get_kernels(), NUM_KERNELS, get_dilations(), NUM_DILATIONS, get_biases(), NUM_BIASES_PER_KERNEL);

    float temp = 0;
    for (uint32_t i = 0; i < devices_num_features[TOS_NODE_ID-1]; i++) {
        temp += features[i] * weight[i];
    }
    // we also do not use tanh, we do this after a mixer round
    return temp + bias;
}

static void calculate_exp(float *in, float *out uint16_t length)
{
  for (uint16_t i = 0; i < length; i++) {
    out[i] = expf(in[i]);
  }
}

static float calculate_sum(float *in, uint16_t length) 
{
  float result = 0;
  for (uint16_t i = 0; i < length; i++) {
    result += in[i];
  }
  
}

static uint8_t get_max_idx(float *in, uint8_t length) {
{
    uint8_t best_idx = 0;
    float best_val = in[0];
    for (uint8_t i = 1; i < length; i++) {
      if (best_val < in[i]) {
        best_val = in[i];
        best_idx = i;
      }
    }
    return best_idx;
}

static uint8_t train_step(float *out_pred, uint8_t idx_class)
{
    out_pred = tanh(out_pred);
    
    // first calculate the exponential of the output and the sum, needed for softmax
    calculate_exp(out_pred, out_exp, NUM_CLASSES);

    float sum_exp = calculate_sum(out_exp, NUM_CLASSES);
    float sum_exp_square_inv = 1/(sum_exp * sum_exp);

    float temp;

    for (uint32_t row_weight = 0; row_weight < NUM_CLASSES; row_weight++) {
      for (uint32_t col_weight = 0; col_weight < devices_num_features[TOS_NODE_ID-1]; col_weight++) {
          
          // standard formula for derivative of cross entropy + softmax
          temp -= out_exp[idx_class]*out_exp[row_weight] * features[col_weight] * sum_exp_square_inv;

          // if we are in the row of the current class in the dataset, add something
          if (row_weight == idx_class) {
            temp += out_exp[row_weight] * features[col_weight] * sum_exp * sum_exp_square_inv;
          }

          d_weight[row_weight*NUM_CLASSES + col_weight] -= temp * sum_exp / out_exp[idx_class];
      }   
    }

    // calculate if prediction is correct
    return get_max_idx(out_exp, NUM_CLASSES) == idx_class;
}

void update_weights(float *out_pred, uint8_t idx_class, uint32_t round_nmbr)
{
    accuracy_filtered = gamma*train_step(out_pred, idx_class) + (1 - gamma) * accuracy_filtered;
    if (round_nmbr % BATCH_SIZE == BATCH_SIZE - 1) {
        float beta_1_pow = powf(BETA_1, t);
        float beta_2_pow = powf(BETA_2, t);
        for (uint32_t row_weight = 0; row_weight < NUM_CLASSES; row_weight++) {
          for (uint32_t col_weight = 0; col_weight < devices_num_features[TOS_NODE_ID-1]; col_weight++) {
              uint32_t i = row_weight*NUM_CLASSES + col_weight;
              m_t_weight[i] = BETA_1 * m_t_weight[i] + (1 - BETA_1) * d_weight[i];
              v_t_weight[i] = BETA_2 * v_t_weight[i] + (1 - BETA_2) * d_weight[i] * d_weight[i];

              float mt_hat = m_t_weight[i] / (1 - beta_1_pow);
              float vt_hat = v_t_weight[i] / (1 - beta_2_pow);

              weight[i] -= LEARNING_RATE * mt_hat / (sqrtf(vt_hat) + EPSILON);  //d_weight[i]; // 
              d_weight[i] = 0;
          }
        }
        m_t_bias = BETA_1 * m_t_bias + (1 - BETA_1) * d_bias;
        v_t_bias = BETA_2 * v_t_bias + (1 - BETA_2) * d_bias * d_bias;

        float mt_hat = m_t_bias / (1 - beta_1_pow);
        float vt_hat = v_t_bias / (1 - beta_2_pow);
        bias -= LEARNING_RATE * mt_hat / (sqrtf(vt_hat) + EPSILON);
        d_bias = 0;
        if (TOS_NODE_ID != 1) {
          bias = 0;
        }
        t++;
        printf("Epoch: %u, Accuracy: %u\n", (uint32_t) round_nmbr, (uint32_t) (accuracy_filtered*100));
    }
}