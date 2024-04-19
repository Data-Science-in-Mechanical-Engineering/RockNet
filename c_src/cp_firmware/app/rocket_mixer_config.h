#ifndef INC_DNNI_CONFIG_H
#define INC_DNNI_CONFIG_H

#include <stdint.h>

typedef struct message_assignment_t_tag
{
	uint8_t id;   // id of message slot
	uint16_t size;  // slot size in byte
	uint16_t mixer_assignment_start;  // the index in mixer, the message starts
	uint16_t mixer_assignment_end;   // the index in mixer the message ends (not including this index)
	uint16_t size_end; // the size of the piece of the message in the mixer message at index mixer_assignment_end-1
} message_assignment_t;

static const uint8_t nodes[] = {  1,  2,  3, };
static const uint8_t rocket_nodes[] = {  1,  2, };

static message_assignment_t message_assignment[] = {
 {.id=254, .size=140},
 {.id=1, .size=10},
 {.id=2, .size=10},
 };

#define MX_PAYLOAD_SIZE 100
#define MX_ROUND_LENGTH 150
#define MX_SLOT_LENGTH GPI_TICK_US_TO_HYBRID2(665)
#define ROUND_LENGTH_MS            ((150*MX_SLOT_LENGTH / (GPI_HYBRID_CLOCK_RATE / 1000000)) / 1000 + 300)
#define MX_GENERATION_SIZE 5

#define AGGREGATE_FLAGS_SIZE (0)
#define AGGREGATE_CONTENT_SIZE (0)

typedef struct __attribute__((packed)) aggregate_field_t_tag
{
	uint8_t flags[AGGREGATE_FLAGS_SIZE];
	float class_values[AGGREGATE_CONTENT_SIZE];
} aggregate_field_t;

#define AGGREGATE_SIZE (sizeof(aggregate_field_t))

uint8_t get_rocket_node_idx(uint8_t id);

#endif /* INC_DNNI_CONFIG_H */