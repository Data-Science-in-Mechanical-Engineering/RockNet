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

static const uint8_t nodes[] = {1, 1};
static const uint8_t dnni_nodes[] = {1};

static message_assignment_t message_assignment[] = {
	{.id=1, .size=414}};
#define MX_PAYLOAD_SIZE 83
#define MX_ROUND_LENGTH 150
#define MX_SLOT_LENGTH GPI_TICK_US_TO_HYBRID2(1019)
#define ROUND_LENGTH_MS                 248
#define MX_GENERATION_SIZE 6

#endif /* INC_DNNI_CONFIG_H */
