#include "wireless_control.h"
#include "mixer_config.h"

unsigned int all_flags_in_agg(uint8_t *agg);

priority_t get_prio_from_agg(uint8_t *agg, uint8_t idx);

void set_prio_in_agg(uint8_t *agg, uint8_t idx, priority_t prio);

uint8_t get_node_from_agg(uint8_t *agg, uint8_t idx);

void set_node_in_agg(uint8_t *agg, uint8_t idx, uint8_t nodeID);

void set_flag_in_agg(uint8_t *agg, uint8_t logical_nodeID);

void merge_flags_from_aggs(uint8_t *dst, uint8_t *src);

void aggregate_M_C_highest(volatile uint8_t *agg_is_valid, uint8_t *agg_local, uint8_t *agg_rx);