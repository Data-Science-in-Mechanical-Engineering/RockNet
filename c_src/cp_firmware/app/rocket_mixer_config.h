#ifndef INC_DNNI_CONFIG_H
#define INC_DNNI_CONFIG_H

typedef struct message_assignment_t_tag 
{ 
	uint8_t id;   // id of message slot 
	uint16_t size;  // slot size in byte 
	uint16_t mixer_assignment_start;  // the index in mixer, the message starts 
	uint16_t mixer_assignment_end;   // the index in mixer the message ends (not including this index)
	uint16_t size_end; // the size of the piece of the message in the mixer message at index mixer_assignment_end-1 
} message_assignment_t;

static const uint8_t nodes[] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 15};
static const uint8_t dnni_nodes[] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15};

static message_assignment_t message_assignment[] = {
	{.id=254, .size=107},
 	{.id=1, .size=10},
 	{.id=2, .size=10},
 	{.id=3, .size=10},
 	{.id=4, .size=10},
 	{.id=5, .size=10},
 	{.id=6, .size=10},
 	{.id=7, .size=10},
 	{.id=8, .size=10},
 	{.id=9, .size=10},
 	{.id=10, .size=10},
 	{.id=11, .size=10},
 	{.id=12, .size=10},
 	{.id=13, .size=10},
 	{.id=14, .size=10},
 	{.id=15, .size=10}};
#define MX_PAYLOAD_SIZE 54
#define MX_ROUND_LENGTH 150
#define MX_SLOT_LENGTH GPI_TICK_US_TO_HYBRID2(1367)
#define ROUND_LENGTH_MS                 ((150*MX_SLOT_LENGTH / (GPI_HYBRID_CLOCK_RATE / 1000000)) / 1000 + 38)
#define MX_GENERATION_SIZE 18

#endif /* INC_DNNI_CONFIG_H */
