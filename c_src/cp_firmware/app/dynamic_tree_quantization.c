#include <stdint.h>
#include <math.h>

#include "dynamic_tree_quantization.h"

static float quantized_values[256];

static int compare_float(const void* a, const void* b) 
{
     
      if (*(float*) a > *(float*)b) {
        return 1;
      }
      return -1;
}


void init_dynamic_tree_quantization()
{
    for (uint16_t q = 0; q < 256; q++) {
        float sign = 1;
        if (q >> 7 == 1) {
            sign = -1;
        }
        uint8_t exponent = 0;
        uint8_t mask = 1 << 6;
        while ((q & mask) == 0 && exponent < 7) {
            exponent++;
            mask >>= 1;
        }
        float scaling = powf(10, -exponent);
        float mantissa = ((q & ((int) roundf(powf(2, (6 - exponent))) - 1))) / (powf(2, (6 - exponent)) - 1 + 1e-7);
        quantized_values[255 - q] = sign * mantissa * scaling;
    }

    // Sort the array using qsort
    qsort(quantized_values, 256, sizeof(float), compare_float);
    
    for (uint16_t i = 0; i < 256; i++) {
        printf("%d\n", (int) (quantized_values[i] * 10000));
    }

}


// find the closest quantized value to the input value using bijnary search.
static uint8_t minimize_binary_search(float value)
{
    uint16_t lower = 0;
    uint16_t upper = 255;
    uint16_t mid = 0;
    while (lower < upper - 1) {
        mid = (lower + upper) / 2;
        if (quantized_values[mid] < value) {
            lower = mid;
        } else {
            upper = mid;
        }
    }
    return quantized_values[upper] - value < value - quantized_values[lower] ? upper : lower;
}

void dynamic_tree_quantization(const float *input, uint8_t *output, uint16_t length)
{
    for (uint16_t i = 0; i < length; i++) {
        float v = input[i];
        output[i] = minimize_binary_search(input[i]);
    }
}

void dynamic_tree_dequantization(const uint8_t *input, float *output, uint16_t length)
{
    for (uint16_t i = 0; i < length; i++) {
        output[i] = quantized_values[input[i]];
    }
}