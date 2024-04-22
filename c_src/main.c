#include <stdio.h>
#include <stdlib.h>
#include "conv.h"

#include "rocket_config.h"
#include "linear_classifier.h"

int main()
{
    init_rocket();

    for (int i = 0; i < NUM_FEATURES; i++) {
        printf("%f\n", get_biases()[i]);
    }

    init_linear_classifier();
    train();
}