#ifndef DYNAMIC_TREE_QUANTIZATION_H
#define DYNAMIC_TREE_QUANTIZATION_H

#include <stdint.h>

void init_dynamic_tree_quantization();

void dynamic_tree_quantization(const float *input, uint8_t *output, uint16_t length);

void dynamic_tree_dequantization(const uint8_t *input, float *output, uint16_t length);

#endif // DYNAMIC_TREE_QUANTIZATION_H