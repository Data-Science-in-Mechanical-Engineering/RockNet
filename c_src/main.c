#include <stdio.h>
#include <stdlib.h>
#include "conv.h"

#include "rocket_config.h"
#include "linear_classifier.h"

static float cummulative[NUM_CLASSES];

void train()
{
    printf("Starting training\n");
    float accuracy_filtered = 0;
    const float gamma = 0.01;
    for (uint64_t epoch = 0; epoch < 100000; epoch++) {
        for (uint32_t batch_idx = 0; batch_idx < NUM_TRAINING_TIMESERIES; batch_idx++) {
            classify_part(get_training_timeseries()[batch_idx], cummulative);
            calculate_and_accumulate_gradient(cummulative, get_training_labels()[batch_idx]);

            if (batch_idx % BATCH_SIZE == BATCH_SIZE-1) {
                update_weights();
                printf("----------");
            }
        }
        update_weights();
        float acc = 0;
        for (uint32_t batch_idx = 0; batch_idx < NUM_EVALUATION_TIMESERIES; batch_idx++) {
            classify_part(get_evaluation_timeseries()[batch_idx], cummulative);

            for (uint8_t i = 0; i < NUM_CLASSES; i++) {
                //printf("%f, ", cummulative[i]);
            }

            uint8_t pred_idx = get_max_idx(cummulative, NUM_CLASSES);
            //printf("%u\r\n", pred_idx);

            if (pred_idx == get_evaluation_labels()[batch_idx]) {
                acc++;
            }
        }

        printf("Epoch: %lu Accuracy %f\r\n", epoch, acc / NUM_EVALUATION_TIMESERIES * 100);
    }
}

int main()
{
    init_rocket();

    for (int i = 0; i < NUM_FEATURES; i++) {
        printf("%f\n", get_biases()[i]);
    }

    init_linear_classifier(0);
    train();
}