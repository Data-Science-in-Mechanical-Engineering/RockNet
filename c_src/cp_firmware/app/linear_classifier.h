#ifndef LINEAR_CLASSIFIER_H
#define LINEAR_CLASSIFIER_H

#include <stdint.h>
#include <stdio.h>
#include <math.h>

#include "rocket_config.h"

void classify_part(const time_series_type_t *in, float *out);

void update_weights(float *out_pred, uint8_t idx_class, uint32_t round_nmbr);

void init_linear_classifier();

#endif