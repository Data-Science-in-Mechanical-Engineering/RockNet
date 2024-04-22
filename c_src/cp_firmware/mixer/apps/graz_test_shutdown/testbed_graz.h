#ifndef TESTBED_GRAZ_H_
#define TESTBED_GRAZ_H_

#define TB_NUMPATTERN 1
#define TB_NUMNODES 48

typedef struct
{
	uint8_t traffic_pattern;             // 0:unused, 1:p2p, 2:p2mp, 3:mp2p, 4: mp2mp
	uint8_t source_id[TB_NUMNODES];      // Only source_id[0] is used for p2p/p2mp
	uint8_t destination_id[TB_NUMNODES]; // Only destination_id[0] is used for p2p/mp2p
	uint8_t msg_length;                  // Message length in bytes in/to EEPROM
	uint8_t msg_offsetH;                 // Message offset in bytes in EEPROM (high byte)
	uint8_t msg_offsetL;                 // Message offset in bytes in EEPROM (low byte)

	uint32_t periodicity;                // Period in ms (0 indicates aperiodic traffic)
	uint32_t aperiodic_upper_bound;      // Upper bound for aperiodic traffic in ms
	uint32_t aperiodic_lower_bound;      // Lower bound for aperiodic traffic in ms
	uint32_t delta;                      // The delay bound delta in ms
} pattern_t;

typedef struct
{
	uint8_t node_id;                     // ID of the current node
	pattern_t p[TB_NUMPATTERN];          // Up to TB_NUMPATTERN parallel configurations
} config_t;


// Helper functions to print the input parameters injected by the competition's testbed
// void
// print_testbed_pattern(pattern_t* p)
// {
// 	uint8_t i;
// 	PRINTF("    Traffic pattern: ");
// 	switch(p->traffic_pattern)
// 	{
// 		case 0: PRINTF("unused\n");
// 			break;
// 		case 1: PRINTF("P2P\n");
// 			break;
// 		case 2: PRINTF("P2MP\n");
// 			break;
// 		case 3: PRINTF("MP2P\n");
// 			break;
// 		case 4: PRINTF("MP2MP\n");
// 			break;
// 		default: PRINTF("Unknown\n");
// 	}
// 	if( (p->traffic_pattern>0) && (p->traffic_pattern <=4))
// 	{
// 		PRINTF("    Sources:\n");
// 		for(i=0;i<TB_NUMNODES;i++)
// 		{
// 			if(p->source_id[i]!=0)
// 			PRINTF("      %d: %d\n",i,p->source_id[i]);
// 		}
// 		PRINTF("    Destinations:\n");
// 		for(i=0;i<TB_NUMNODES;i++)
// 		{
// 			if(p->destination_id[i]!=0)
// 			PRINTF("      %d: %d\n",i,p->destination_id[i]);
// 		}
// 		if(p->periodicity==0)
// 		{
// 			PRINTF("    Aperiodic Upper: %lu\n",p->aperiodic_upper_bound);
// 			PRINTF("    Aperiodic Lower: %lu\n",p->aperiodic_lower_bound);
// 		}
// 		else
// 		{
// 			PRINTF("    Period: %lu\n",p->periodicity);
// 		}
//         PRINTF("    Delta: %lu\n",p->delta);
//
// 		PRINTF("    Message Length: %d\n",p->msg_length);
// 		PRINTF("    Message OffsetH: %d\n",p->msg_offsetH);
// 		PRINTF("    Message OffsetL: %d\n",p->msg_offsetL);
// 	}
// 	PRINTF("\n");
//
// }
//
// void
// print_testbed_config(config_t* cfg)
// {
// 	PRINTF("Testbed configuration:\n");
// 	PRINTF("Node ID: %d",cfg->node_id);
// 	uint8_t i;
// 	for(i=0;i<TB_NUMPATTERN;i++)
// 	{
// 	        PRINTF("  Pattern %d:\n",i);
// 		print_testbed_pattern(&(cfg->p[i]));
// 	}
// }

#endif // TESTBED_GRAZ_H_
