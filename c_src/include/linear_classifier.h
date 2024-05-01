#ifndef LINEAR_CLASSIFIER_H
#define LINEAR_CLASSIFIER_H

#include <stdint.h>
#include <stdio.h>
#include <math.h>

#include "rocket_config.h"

void classify_part(const time_series_type_t *in, float *out);

uint8_t get_max_idx(float *in, uint8_t length);

uint8_t calculate_and_accumulate_gradient(float *out_pred, uint8_t idx_class);

void update_weights();

void init_linear_classifier(uint8_t id);

#endif