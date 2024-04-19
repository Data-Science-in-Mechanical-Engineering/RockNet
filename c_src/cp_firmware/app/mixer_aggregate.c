#include "mixer_aggregate.h"
#include "rocket_mixer_config.h"

static uint8_t node_idx=-1u;

static uint8_t 

void init_agg(uint8_t id)
{
  // get node_idx
  for (node_idx = 0; node_idx < NUM_ELEMENTS(nodes); node_idx++) {
    if (id == nodes[node_idx]) {
      break;
    }
  }
}

unsigned int all_flags_in_agg(uint8_t *agg)
{
  
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