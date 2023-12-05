#ifndef __WIRELESS_CONTROL_H__
#define __WIRELESS_CONTROL_H__

// #include "mixer/mixer.h"
#include "gpi/tools.h"
#include "gpi/clocks.h"
#include "mixer_config.h"

#define TURN_OFF_AGG

#ifndef TURN_OFF_AGG
#define CONTROL_MSGS_M_C					2
#define PRIO_WIDTH							8
#define NODE_ID_WIDTH						5
#define AGGREGATE_CONTAINS_ALL_PRIORITIES	0
#else
#define CONTROL_MSGS_M_C					0
#define PRIO_WIDTH							0
#define NODE_ID_WIDTH						0
#define AGGREGATE_CONTAINS_ALL_PRIORITIES	0
#endif

#ifndef TURN_OFF_AGG
ASSERT_CT_STATIC(NUM_PLANTS <= ((1 << NODE_ID_WIDTH) - 1), NODE_ID_WIDTH_cannot_support_all_nodes);
ASSERT_CT_STATIC(NODE_ID_WIDTH <= 8, NODE_ID_WIDTH_greater_8_is_not_implemented);
#endif

#ifndef TURN_OFF_AGG
#define AGGREGATE_SIZE_M_C_PRIORITIES	((NUM_PLANTS + CONTROL_MSGS_M_C * PRIO_WIDTH + CONTROL_MSGS_M_C * NODE_ID_WIDTH + 7) / 8)
#define AGGREGATE_SIZE_ALL_PRIORITIES	((NUM_PLANTS * PRIO_WIDTH + 7) / 8)
#else
#define AGGREGATE_SIZE_M_C_PRIORITIES	0
#define AGGREGATE_SIZE_ALL_PRIORITIES	0
#endif

#if AGGREGATE_CONTAINS_ALL_PRIORITIES == 1
	#error "NOT IMPLEMENTED"
	#define AGGREGATE_SIZE	AGGREGATE_SIZE_ALL_PRIORITIES
#else
	#define AGGREGATE_SIZE	AGGREGATE_SIZE_M_C_PRIORITIES
#endif

typedef uint8_t priority_t;
ASSERT_CT_STATIC(PRIO_WIDTH <= (sizeof(priority_t) * 8), prob_info_t_needs_to_implement_support_for_priority_widths_greater_8_bit);



// The Bolt durations contain besides the actual SPI data transfer
// also the code around such as memcpy, mixer_write etc.
// measured: <274us for generation size 3 (1 control, 2 data packets)
#define BOLT_WRITE_DURATION		(MX_GENERATION_SIZE * GPI_TICK_US_TO_HYBRID2(200))

// duration the CP needs to read data from AP.
#define AP_READ_DURATION		(GPI_TICK_MS_TO_HYBRID2(20))

// measured: <6us
#define MIXER_ARM_DURATION		(GPI_TICK_US_TO_HYBRID2(10))

#define MIXER_INITIATOR_DELAY	(3 * MX_SLOT_LENGTH)

// After calling mixer_start, the actual first transmission
// (starting point for the deadline calculation) is a bit delayed.
// measured: ~47us
#define MIXER_FIRST_TX_DELAY	(GPI_TICK_US_TO_HYBRID2(47))

#define MIXER_DURATION			(MIXER_FIRST_TX_DELAY + (MX_ROUND_LENGTH * MX_SLOT_LENGTH))

// Safety buffer after Mixer to compensate potential inaccuracies at the end of a Mixer round.
#define MIXER_DEADLINE_BUFFER	(5 * MX_SLOT_LENGTH)

// offsets are time deltas with respect to t_ref (end of Mixer round) for certain events
#define SYNC_LINE_OFFSET(ref)		((ref) + MIXER_DEADLINE_BUFFER \
										   + BOLT_WRITE_DURATION)

#define SYNC_OFFSET(ref)		((ref))

// depends on the actual communication period p
#define MIXER_OFFSET(ref, p)		((ref) + (p) \
										   - MIXER_DURATION \
										   - MIXER_INITIATOR_DELAY \
										   + MX_SLOT_LENGTH) // TODO: unclear why

#define READ_AND_ARM_OFFSET(ref, p)	(MIXER_OFFSET(ref, p) - MIXER_ARM_DURATION \
														  - AP_READ_DURATION)


#define BOLT_PKT_INFO_SIZE	offsetof(bolt_pkt_t, payload_start)
#define LEN_BOLT_CONTROL	(BOLT_PKT_INFO_SIZE + sizeof(control_pkt_t))
#define LEN_BOLT_DATA		(BOLT_PKT_INFO_SIZE + sizeof(data_pkt_t))
#define LEN_BOLT_DATA_PROB	(BOLT_PKT_INFO_SIZE + sizeof(data_prob_pkt_t))
#define LEN_BOLT_PRIO_DATA	(BOLT_PKT_INFO_SIZE + sizeof(uint8_t)*(MX_GENERATION_SIZE - 1))
#define LEN_BOLT_PRINT		(BOLT_PKT_INFO_SIZE + sizeof(stats_pkt_t))
#define LEN_BOLT_INIT		(BOLT_PKT_INFO_SIZE + sizeof(init_pkt_t))
#define LEN_BOLT_DATA_FAKE	(BOLT_PKT_INFO_SIZE + sizeof(data_pkt_t))
#define LEN_BOLT_AGG_DATA	(BOLT_PKT_INFO_SIZE + sizeof(agg_pkt_t))

//**************************************************************************************************

// ATTENTION: Do not change this since the same AP code is used for periodic and predictive control.
enum bolt_pkt_type
{
	BOLT_CONTROL,
	BOLT_DATA,
	BOLT_DATA_PROB,
	BOLT_PRINT,
	BOLT_INIT,
	BOLT_DATA_FAKE,
	BOLT_AGG_DATA,
        BOLT_PRIO
};

//**************************************************************************************************

#endif // __WIRELESS_CONTROL_H__