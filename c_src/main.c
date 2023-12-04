#include <stdio.h>
#include <stdlib.h>
#include "conv.h"

#include "rocket_config.h"
#include "linear_classifier.h"

int main()
{
    init_rocket();

    train();
}