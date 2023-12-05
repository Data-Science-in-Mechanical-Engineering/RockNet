#include "mixer_aggregate.h"

unsigned int all_flags_in_agg(uint8_t *agg)
{
	/*ASSERT_CT(NUM_PLANTS > 0, NUM_PLANTS_must_be_greater_0);
	unsigned int last_bucket = (NUM_PLANTS - 1) / 8;
	unsigned int remaining_flags = NUM_PLANTS % 8;

	uint8_t last_flags_mask = ~((1 << (8 - remaining_flags)) - 1);
	// When the last bucket is completely filled with flags we have no remaining flags, so the mask
	// has to cover the whole bucket.
	if (remaining_flags == 0) last_flags_mask = 0xFF;

	for (unsigned int i = 0; i <= last_bucket; i++)
	{
		if (i == last_bucket)
		{
			if ((agg[i] & last_flags_mask) != last_flags_mask) return 0;
		}
		else
		{
			if (agg[i] != 0xFF) return 0;
		}
	}*/

	return 1;
}

// idx is zero-based
priority_t get_prio_from_agg(uint8_t *agg, uint8_t idx)
{
	/*// Out of bounds access protection.
	if (idx >= CONTROL_MSGS_M_C) return 0;

	unsigned int bucket = (NUM_PLANTS + idx * PRIO_WIDTH) / 8;
	unsigned int offset = (NUM_PLANTS + idx * PRIO_WIDTH) % 8;

	// First case, priority is completely inside one bucket.
	if (offset + PRIO_WIDTH <= 8)
	{
		// Create masks for the first and last bits.
		uint8_t pre_mask = 0;
		uint8_t post_mask = 0;

		if (offset > 0)
		{
			pre_mask = ((1 << offset) - 1) << (8 - offset);
		}

		// if (offset + PRIO_WIDTH < 8)
		// {
			post_mask = (1 << (8 - offset - PRIO_WIDTH)) - 1;
		// }

		// Masked priority value eventually needs to be right shifted for the correct value.
		return (agg[bucket] & ~(pre_mask | post_mask)) >> (8 - offset - PRIO_WIDTH);
	}
	else
	{
		// Priority is composed of multiple parts (distributed over multiple buckets)
		priority_t p = 0;
		uint8_t pre_mask = 0;

		if (offset > 0)
		{
			pre_mask = ((1 << offset) - 1) << (8 - offset);
		}

		// First part of priority p.
		uint8_t remaining_bits = PRIO_WIDTH - (8 - offset);
		p = (agg[bucket] & ~pre_mask) << remaining_bits;

		uint8_t post_mask = (1 << (8 - remaining_bits)) - 1;
		p |= (agg[bucket + 1] & ~post_mask) >> (8 - remaining_bits);

		return p;
	}*/
        return 1;
}

//**************************************************************************************************

void set_prio_in_agg(uint8_t *agg, uint8_t idx, priority_t prio)
{
	/*// Out of bounds access protection.
	if (idx >= CONTROL_MSGS_M_C) return;

	unsigned int bucket = (NUM_PLANTS + idx * PRIO_WIDTH) / 8;
	unsigned int offset = (NUM_PLANTS + idx * PRIO_WIDTH) % 8;

	// First case, priority is completely inside one bucket.
	if (offset + PRIO_WIDTH <= 8)
	{
		uint8_t pre_mask = 0;
		uint8_t post_mask = 0;

		if (offset > 0)
		{
			pre_mask = ((1 << offset) - 1) << (8 - offset);
		}

		// if (offset + PRIO_WIDTH < 8)
		// {
			post_mask = (1 << (8 - offset - PRIO_WIDTH)) - 1;
		// }

		// Mask value region in agg[bucket].
		uint8_t v = agg[bucket] & (pre_mask | post_mask);
		agg[bucket] = v | (prio << (8 - offset - PRIO_WIDTH));

		return;
	}
	// Priority is distributed over multiple buckets.
	else
	{
		uint8_t pre_mask = 0;

		if (offset > 0)
		{
			pre_mask = ((1 << offset) - 1) << (8 - offset);
		}

		// Mask value region in agg[bucket].
		uint8_t v = agg[bucket] & pre_mask;

		uint8_t remaining_bits = PRIO_WIDTH - (8 - offset);
		agg[bucket] = v | (prio >> remaining_bits);

		uint8_t post_mask = (1 << (8 - remaining_bits)) - 1;
		v = agg[bucket + 1] & post_mask;
		agg[bucket + 1] = v | ((prio & ((1 << remaining_bits) - 1)) << (8 - remaining_bits));

		return;
	}*/
}

ASSERT_CT_STATIC(PRIO_WIDTH <= 8, set_prio_in_agg_needs_to_implement_support_for_priority_widths_greater_8_bit);

//**************************************************************************************************

// idx is zero-based
uint8_t get_node_from_agg(uint8_t *agg, uint8_t idx)
{
        /*
	// Out of bounds access protection.
	if (idx >= CONTROL_MSGS_M_C) return 0;

	unsigned int bucket = (NUM_PLANTS + CONTROL_MSGS_M_C * PRIO_WIDTH + idx * NODE_ID_WIDTH) / 8;
	unsigned int offset = (NUM_PLANTS + CONTROL_MSGS_M_C * PRIO_WIDTH + idx * NODE_ID_WIDTH) % 8;

	// First case, node ID is completely inside one bucket.
	if (offset + NODE_ID_WIDTH <= 8)
	{
		// Create masks for the first and last bits.
		uint8_t pre_mask = 0;
		uint8_t post_mask = 0;

		if (offset > 0)
		{
			pre_mask = ((1 << offset) - 1) << (8 - offset);
		}

		// if (offset + NODE_ID_WIDTH < 8)
		// {
			post_mask = (1 << (8 - offset - NODE_ID_WIDTH)) - 1;
		// }

		// Masked node ID eventually needs to be right shifted for the correct value.
		return (agg[bucket] & ~(pre_mask | post_mask)) >> (8 - offset - NODE_ID_WIDTH);
	}
	else
	{
		// Node ID is composed of multiple parts (distributed over multiple buckets).
		uint8_t n = 0;
		uint8_t pre_mask = 0;

		if (offset > 0)
		{
			pre_mask = ((1 << offset) - 1) << (8 - offset);
		}

		uint8_t remaining_bits = NODE_ID_WIDTH - (8 - offset);
		n = (agg[bucket] & ~pre_mask) << remaining_bits;

		uint8_t post_mask = (1 << (8 - remaining_bits)) - 1;
		n |= (agg[bucket + 1] & ~post_mask) >> (8 - remaining_bits);

		return n;
	}*/
        return 0;
}

//**************************************************************************************************

// Here, nodeID is used as value and NOT as index. Use the same nodeID as in the AP code.
void set_node_in_agg(uint8_t *agg, uint8_t idx, uint8_t nodeID)
{
	/*// Out of bounds access protection.
	if (idx >= CONTROL_MSGS_M_C) return;

	unsigned int bucket = (NUM_PLANTS + CONTROL_MSGS_M_C * PRIO_WIDTH + idx * NODE_ID_WIDTH) / 8;
	unsigned int offset = (NUM_PLANTS + CONTROL_MSGS_M_C * PRIO_WIDTH + idx * NODE_ID_WIDTH) % 8;

	// First case, priority is completely inside one bucket.
	if (offset + NODE_ID_WIDTH <= 8)
	{
		uint8_t pre_mask = 0;
		uint8_t post_mask = 0;

		if (offset > 0)
		{
			pre_mask = ((1 << offset) - 1) << (8 - offset);
		}

		// if (offset + NODE_ID_WIDTH < 8)
		// {
			post_mask = (1 << (8 - offset - NODE_ID_WIDTH)) - 1;
		// }

		// Mask value region in agg[bucket].
		uint8_t v = agg[bucket] & (pre_mask | post_mask);
		agg[bucket] = v | (nodeID << (8 - offset - NODE_ID_WIDTH));

		return;
	}
	// Node ID is distributed over multiple buckets.
	else
	{
		uint8_t pre_mask = 0;

		if (offset > 0)
		{
			pre_mask = ((1 << offset) - 1) << (8 - offset);
		}

		// Mask value region in agg[bucket].
		uint8_t v = agg[bucket] & pre_mask;

		uint8_t remaining_bits = NODE_ID_WIDTH - (8 - offset);
		agg[bucket] = v | (nodeID >> remaining_bits);

		uint8_t post_mask = (1 << (8 - remaining_bits)) - 1;
		v = agg[bucket + 1] & post_mask;
		agg[bucket + 1] = v | ((nodeID & ((1 << remaining_bits) - 1)) << (8 - remaining_bits));

		return;
	}
        */
}

//**************************************************************************************************

void set_flag_in_agg(uint8_t *agg, uint8_t logical_nodeID)
{
	/*
        // Out of bounds access protection.
	if (logical_nodeID >= NUM_PLANTS) return;

	agg[logical_nodeID / 8] |= (0x1 << (7 - (logical_nodeID % 8)));
        */
}

//**************************************************************************************************

void merge_flags_from_aggs(uint8_t *dst, uint8_t *src)
{
	/*
        ASSERT_CT(NUM_PLANTS > 0, NUM_PLANTS_must_be_greater_0);
	unsigned int last_bucket = (NUM_PLANTS - 1) / 8;
	unsigned int remaining_flags = NUM_PLANTS % 8;

	uint8_t last_flags_mask = ~((1 << (8 - remaining_flags)) - 1);
	// When the last bucket is completely filled with flags we have no remaining flags, so the mask
	// has to cover the whole bucket.
	if (remaining_flags == 0) last_flags_mask = 0xFF;

	for (unsigned int i = 0; i <= last_bucket; i++)
	{
		if (i == last_bucket)
		{
			dst[i] |= src[i] & last_flags_mask;
		}
		else
		{
			dst[i] |= src[i];
		}
	}
        */
}

//**************************************************************************************************

void aggregate_M_C_highest(volatile uint8_t *agg_is_valid, uint8_t *agg_local, uint8_t *agg_rx)
{
	/*
        priority_t top_prios[CONTROL_MSGS_M_C];
	uint8_t top_nodes[CONTROL_MSGS_M_C];
	memset(top_prios, 0, sizeof(priority_t) * CONTROL_MSGS_M_C);
	memset(top_nodes, 0, sizeof(uint8_t) * CONTROL_MSGS_M_C);

	unsigned int top_prios_idx = 0;
	// unsigned int top_nodes_idx = 0;
	unsigned int agg_local_idx = 0;
	unsigned int agg_rx_idx = 0;

	while (top_prios_idx < CONTROL_MSGS_M_C)
	{
		priority_t p1 = get_prio_from_agg(agg_local, agg_local_idx);
		priority_t p2 = get_prio_from_agg(agg_rx, agg_rx_idx);

		uint8_t n1 = get_node_from_agg(agg_local, agg_local_idx);
		uint8_t n2 = get_node_from_agg(agg_rx, agg_rx_idx);

		// skip for duplicates
		// for (unsigned int i = 0; i < top_nodes_idx; i++)
		for (unsigned int i = 0; i < top_prios_idx; i++)
		{
			if (n1 == top_nodes[i])
			{
				++agg_local_idx;
				n1 = get_node_from_agg(agg_local, agg_local_idx);
				p1 = get_prio_from_agg(agg_local, agg_local_idx);
			}

			if (n2 == top_nodes[i])
			{
				++agg_rx_idx;
				n2 = get_node_from_agg(agg_rx, agg_rx_idx);
				p2 = get_prio_from_agg(agg_rx, agg_rx_idx);
			}
		}

		if (p1 == p2)
		{
			if (n1 < n2)
			{
				top_prios[top_prios_idx] = p1;
				top_nodes[top_prios_idx] = n1;
				// top_nodes[top_nodes_idx] = n1;
				++top_prios_idx;
				++agg_local_idx;
				// ++top_nodes_idx;

			}
			else if (n1 > n2)
			{
				top_prios[top_prios_idx] = p2;
				top_nodes[top_prios_idx] = n2;
				++top_prios_idx;
				++agg_rx_idx;
			}
			// When n1 == n2, we can add either one.
			else
			{
				top_prios[top_prios_idx] = p1;
				top_nodes[top_prios_idx] = n1;
				++top_prios_idx;
				++agg_local_idx;
			}
		}
		else if (p1 > p2)
		{
			top_prios[top_prios_idx] = p1;
			top_nodes[top_prios_idx] = n1;
			++top_prios_idx;
			++agg_local_idx;
		}
		else // p1 < p2
		{
			top_prios[top_prios_idx] = p2;
			top_nodes[top_prios_idx] = n2;
			++top_prios_idx;
			++agg_rx_idx;
		}
	}

	// invalidate aggregate before modification
	*agg_is_valid = 0;

	merge_flags_from_aggs(agg_local, agg_rx);
	for (unsigned int i = 0; i < CONTROL_MSGS_M_C; i++)
	{
		set_prio_in_agg(agg_local, i, top_prios[i]);
		set_node_in_agg(agg_local, i, top_nodes[i]);
	}

	// activate aggregate after modification
	*agg_is_valid = 1;
        */
}