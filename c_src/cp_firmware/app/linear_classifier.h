#ifndef LINEAR_CLASSIFIER_H
#define LINEAR_CLASSIFIER_H

#include <stdint.h>
#include <stdio.h>
#include <math.h>

#include "rocket_config.h"

float classify_part(const time_series_type_t *in);

void update_weights(float out_pred, float out, uint32_t round_nmbr);

#endif