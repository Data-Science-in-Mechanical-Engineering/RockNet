#ifndef LINEAR_CLASSIFIER_H
#define LINEAR_CLASSIFIER_H

#include <stdint.h>
#include <stdio.h>
#include <math.h>

float classify_part(float *in);

void update_weights(float out_pred, float out);

#endif