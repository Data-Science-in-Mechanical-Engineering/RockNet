#include "wireless_control.h"
#include "mixer_config.h"

void init_agg(uint8_t id);

unsigned int all_flags_in_agg(uint8_t *agg);

void aggregate_M_C_highest(volatile uint8_t *agg_is_valid, uint8_t *agg_local, uint8_t *agg_rx);