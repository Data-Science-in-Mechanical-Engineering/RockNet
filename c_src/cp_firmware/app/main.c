/***************************************************************************************************
 ***************************************************************************************************
 *
 *	Copyright (c) 2019, Networked Embedded Systems Lab, TU Dresden
 *	All rights reserved.
 *
 *	Redistribution and use in source and binary forms, with or without
 *	modification, are permitted provided that the following conditions are met:
 *		* Redistributions of source code must retain the above copyright
 *		  notice, this list of conditions and the following disclaimer.
 *		* Redistributions in binary form must reproduce the above copyright
 *		  notice, this list of conditions and the following disclaimer in the
 *		  documentation and/or other materials provided with the distribution.
 *		* Neither the name of the NES Lab or TU Dresden nor the
 *		  names of its contributors may be used to endorse or promote products
 *		  derived from this software without specific prior written permission.
 *
 *	THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
 *	ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 *	WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 *	DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY
 *	DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 *	(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 *	LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 *	ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 *	(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 *	SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 ***********************************************************************************************//**
 *
 *	@file					main.c
 *
 *	@brief					main entry point
 *
 *	@version				$Id$
 *	@date					TODO
 *
 *	@author					Fabian Mager
 *
 ***************************************************************************************************

 	@details

	TODO

 **************************************************************************************************/
//***** Trace Settings *****************************************************************************

#include "gpi/trace.h"

// message groups for TRACE messages (used in GPI_TRACE_MSG() calls)
// define groups appropriate for your needs, assign one bit per group
// values > GPI_TRACE_LOG_USER (i.e. upper bits) are reserved
#define TRACE_INFO		GPI_TRACE_MSG_TYPE_INFO

// select active message groups, i.e., the messages to be printed (others will be dropped)
#ifndef GPI_TRACE_BASE_SELECTION
	#define GPI_TRACE_BASE_SELECTION	GPI_TRACE_LOG_STANDARD | GPI_TRACE_LOG_PROGRAM_FLOW
#endif
GPI_TRACE_CONFIG(main, GPI_TRACE_BASE_SELECTION);

//**************************************************************************************************
//***** Includes ***********************************************************************************

#include "mixer/mixer.h"

#include "gpi/tools.h"
#include "gpi/platform.h"
#include "gpi/interrupts.h"
#include "gpi/clocks.h"
#include "gpi/olf.h"

#include "spi.h"
#include "internal_messages.h"
#include "cp_os.h"
#include "mixer_config.h"
#include "relay_os.h"

#include "conv.h"

#include "rocket_config.h"
#include "linear_classifier.h"

#include "rocket_os.h"

#include GPI_PLATFORM_PATH(radio.h)

#include <nrf.h>
#ifndef DISABLE_BOLT
	#include <bolt.h>
#endif

#include <stdio.h>
#include <inttypes.h>
#include <stdlib.h>
#include <string.h>

//**************************************************************************************************
//***** Profile Settings ***************************************************************************

#if WC_PROFILE_MAIN
	#include "gpi/profile.h"
	GPI_PROFILE_SETUP("main.c", 1000, 2);
	#define PROFILE_MAIN(...)				GPI_PROFILE(100, ## __VA_ARGS__)
	#define PROFILE_MAIN_P(priority, ...)	GPI_PROFILE(priority, ## __VA_ARGS__)
#else
	#define PROFILE_MAIN(...)		while (0)
	#define PROFILE_MAIN_P(...)		while (0)
#endif

//**************************************************************************************************
//***** Local Defines and Consts *******************************************************************

#ifndef WEAK_RELEASE_SLOT
	#warning WEAK_RELEASE_SLOT not defined, set it to MX_ROUND_LENGTH / 2
	#define WEAK_RELEASE_SLOT	MX_ROUND_LENGTH / 2
#endif

// important for the log parser
#define PRINT_HEADER()	printf("# ID:%u ", TOS_NODE_ID)

#define TALK_WITH_AP 1
#define USE_SPI 1  // if using spi, debug messages will be sent via UART. Otherwise UART is used as communication with AP

#define DISABLE_BOLT

//**************************************************************************************************
//***** Local Typedefs and Class Declarations ******************************************************


//**************************************************************************************************
//***** Forward Declarations ***********************************************************************



//**************************************************************************************************
//***** Local (Static) Variables *******************************************************************

static uint8_t			node_id;
static uint32_t			round_;
static uint32_t			initiator_msg_decoded;
static uint32_t			control_msg_decoded;
static uint32_t			prio_msg_decoded;
static uint32_t			msgs_not_decoded;
static uint32_t			msgs_weak;
static uint32_t			msgs_weak_fake;

static uint8_t			rank;
static uint8_t			hash;
static uint8_t			slot_full_rank;
static uint32_t			radio_on_time;

static uint8_t			all_ranks[MX_GENERATION_SIZE - 1]; // subtract control msg
static uint8_t			all_versions[MX_GENERATION_SIZE - 1]; // subtract control msg
static uint8_t			all_priorities[MX_GENERATION_SIZE - 1]; // subtract control msg
static uint8_t			all_currTrigger[MX_GENERATION_SIZE - 1]; // subtract control msg
static uint8_t			all_slot_full_rank[MX_GENERATION_SIZE - 1]; // subtract control msg
static uint32_t			all_radio_on_time[MX_GENERATION_SIZE - 1]; // subtract control msg

//**************************************************************************************************
//***** Global Variables ***************************************************************************

// TOS_NODE_ID is a variable with very special handling: on FLOCKLAB and INDRIYA, its init value
// gets overridden with the id of the node in the testbed during device programming (by calling
// tos-set-symbol (a script) on the elf file). Thus, it is well suited as a node id variable.
// ATTENTION: it is important to have TOS_NODE_ID in .data (not in .bss), otherwise tos-set-symbol
// will not work
uint16_t __attribute__((section(".data")))	TOS_NODE_ID = 0;
#define THIS_NODE_ID 13

//**************************************************************************************************
//***** Global Functions ****************************************************************************

//**************************************************************************************************
//***** Local Functions ****************************************************************************

//**************************************************************************************************

//**************************************************************************************************

// print results for the log parser
static void print_results(uint8_t log_id)
{
	unsigned int	slot, slot_min, i;

	#if WC_PROFILE_MAIN
		Gpi_Profile_Ticket	ticket;
		const char			*module_name;
		uint16_t			line;
		uint32_t			timestamp;
		memset(&ticket, 0, sizeof(ticket));

		while (gpi_profile_read(&ticket, &module_name, &line, &timestamp))
		{
			printf("profile %s %4" PRIu16 ": %" PRIu32 "\n", module_name, line, timestamp);
		}
	#endif

	// stats
	// mixer_print_statistics();

	// #define PRINT(n) printf(#n ": %" PRIu16 "\n", mixer_statistics()->n)
	// PRINT(num_sent);
	// PRINT(num_received);
	// PRINT(num_resync);
	// PRINT(num_rx_timeout);
	// // PRINT(slot_full_rank);
	// PRINT(slot_off);
	// #undef PRINT

	// #define PRINT(n) printf(#n ": %luus\n", (unsigned long)gpi_tick_hybrid_to_us(mixer_statistics()->n))
	// PRINT(radio_on_time);
	// #undef PRINT

	slot_full_rank = mixer_statistics()->slot_full_rank;
	radio_on_time = gpi_tick_hybrid_to_us(mixer_statistics()->radio_on_time);

	for (i = 0; i < MX_GENERATION_SIZE; i++)
	{
		if (mixer_stat_slot(i) >= 0) ++rank;
	}
#if USE_SPI 
	PRINT_HEADER();    
        printf("round=%" PRIu32 " rank=%" PRIu8 " initDec=%" PRIu32 " ctrlDec=%" PRIu32
		   " priDec=%" PRIu32 " notDec=%" PRIu32 " weak=%" PRIu32 " weakF=%" PRIu32 "\n",
		   round_, rank, initiator_msg_decoded, control_msg_decoded, prio_msg_decoded,
		   msgs_not_decoded, msgs_weak, msgs_weak_fake);
#endif
	// PRINT_HEADER();
	// printf("aggregate: %02" PRIx8 " %02" PRIx8 " %02" PRIx8 " (n1=%" PRIu8 " p1=%" PRIu8 " n2=%" PRIu8 " p2=%" PRIu8 ")\n", agg[0], agg[1], agg[2] & 0xF0, GET_NODE1(agg), GET_PRIO1(agg), GET_NODE2(agg), GET_PRIO2(agg));

	// PRINT_HEADER();
	// printf("prios=[");
	// for (i = 0; i < (MX_GENERATION_SIZE - 1); i++)
	// {
	// 	printf("%" PRIu8 ";", all_priorities[i]);
	// }
	// printf("]\n");
	memset(all_priorities, 0, sizeof(all_priorities));

	// PRINT_HEADER();
	// printf("curTrigger=[");
	// for (i = 0; i < (MX_GENERATION_SIZE - 1); i++)
	// {
	// 	printf("%" PRIu8 ";", all_currTrigger[i]);
	// }
	// printf("]\n");
	memset(all_currTrigger, 0, sizeof(all_currTrigger));

	// PRINT_HEADER();
	// printf("rank=[");
	// for (i = 0; i < (MX_GENERATION_SIZE - 1); i++)
	// {
	// 	printf("%" PRIu8 ";", all_ranks[i]);
	// }
	// printf("]\n");
	memset(all_ranks, 0, sizeof(all_ranks));

	// PRINT_HEADER();
	// printf("full_rank=[");
	// for (i = 0; i < (MX_GENERATION_SIZE - 1); i++)
	// {
	// 	printf("%" PRIu8 ";", all_slot_full_rank[i]);
	// }
	// printf("]\n");
	memset(all_slot_full_rank, 0, sizeof(all_slot_full_rank));

	// PRINT_HEADER();
	// printf("radio=[");
	// for (i = 0; i < (MX_GENERATION_SIZE - 1); i++)
	// {
	// 	printf("%" PRIu32 ";", all_radio_on_time[i]);
	// }
	// printf("]\n");
	memset(all_radio_on_time, 0, sizeof(all_radio_on_time));

	uint8_t version = all_versions[0];
	for (i = 1; i < (MX_GENERATION_SIZE - 1); i++)
	{
		if (version != all_versions[i]) {
                  #if USE_SPI   
			printf("version mismatch (i=%u)\n", i);
                  #endif
                 }
	}

	// PRINT_HEADER();
	// printf("version=[");
	// for (i = 0; i < (MX_GENERATION_SIZE - 1); i++)
	// {
	// 	printf("%" PRIu8 ";", all_versions[i]);
	// }
	// printf("]\n");





	// PRINT_HEADER();
	// printf("rank_up_slot=[");
	// for (slot_min = 0; 1; )
	// {
	// 	slot = -1u;
	// 	for (i = 0; i < MX_GENERATION_SIZE; ++i)
	// 	{
	// 		if (mixer_stat_slot(i) < slot_min)
	// 			continue;

	// 		if (slot > (uint16_t)mixer_stat_slot(i))
	// 			slot = mixer_stat_slot(i);
	// 	}

	// 	if (-1u == slot)
	// 		break;

	// 	for (i = 0; i < MX_GENERATION_SIZE; ++i)
	// 	{
	// 		if (mixer_stat_slot(i) == slot)
	// 			printf("%u;", slot);
	// 	}

	// 	slot_min = slot + 1;
	// }
	// printf("]\n");

	// PRINT_HEADER();
	// printf("rank_up_row=[");
	// for (slot_min = 0; 1; )
	// {
	// 	slot = -1u;
	// 	for (i = 0; i < MX_GENERATION_SIZE; ++i)
	// 	{
	// 		if (mixer_stat_slot(i) < slot_min)
	// 			continue;

	// 		if (slot > (uint16_t)mixer_stat_slot(i))
	// 			slot = mixer_stat_slot(i);
	// 	}

	// 	if (-1u == slot)
	// 		break;

	// 	for (i = 0; i < MX_GENERATION_SIZE; ++i)
	// 	{
	// 		if (mixer_stat_slot(i) == slot)
	// 			printf("%u;", i);
	// 	}

	// 	slot_min = slot + 1;
	// }
	// printf("]\n");
}

void init_spi(); // unnecessary?

//**************************************************************************************************

static void initialization(void)
{
	gpi_platform_init(); // Initialise Generic Platform Interface (GPI)
        gpi_int_enable(); // Enable interrupts
        init_spi(); // Initialise SPI communication to AP

	// Start random number generator (RNG) now so that we definitely have some random value as a seed later in the initialization.
	NRF_RNG->INTENCLR = BV_BY_NAME(RNG_INTENCLR_VALRDY, Clear);
	NRF_RNG->CONFIG = BV_BY_NAME(RNG_CONFIG_DERCEN, Enabled);
	NRF_RNG->TASKS_START = 1;

	// enable SysTick timer if needed
	//#if MX_VERBOSE_PROFILE
		SysTick->LOAD  = -1u;
		SysTick->VAL   = 0;
		SysTick->CTRL  = SysTick_CTRL_CLKSOURCE_Msk | SysTick_CTRL_ENABLE_Msk;
	//#endif

	// init RF transceiver
	gpi_radio_init(MX_PHY_MODE);
	gpi_radio_set_tx_power(gpi_radio_dbm_to_power_level(MX_TX_PWR_DBM));
	switch (MX_PHY_MODE)
	{
		case BLE_1M:
		case BLE_2M:
		case BLE_125k:
		case BLE_500k:
			gpi_radio_set_channel(39);
			gpi_radio_ble_set_access_address(~0x8E89BED6);
			break;

		case IEEE_802_15_4:
			gpi_radio_set_channel(26);
			break;

		default:
                  #if USE_SPI   
			printf("ERROR: MX_PHY_MODE is invalid!\n");
			assert(0);
                  #endif
                  break;
	}
        #if USE_SPI   
	printf("Hardware initialized. Compiled at __DATE__ __TIME__ = " __DATE__ " " __TIME__ "\n");
        #endif

	/*
	* Pearson hashing (from Wikipedia)
	*
	* Pearson hashing is a hash function designed for fast execution on processors with 8-bit registers.
	* Given an input consisting of any number of bytes, it produces as output a single byte that is strongly
	* dependent on every byte of the input. Its implementation requires only a few instructions, plus a
	* 256-byte lookup table containing a permutation of the values 0 through 255.
	*/

	// T table for Pearson hashing from RFC 3074.
	uint8_t T[256] = {
		251, 175, 119, 215, 81, 14, 79, 191, 103, 49, 181, 143, 186, 157,  0,
		232, 31, 32, 55, 60, 152, 58, 17, 237, 174, 70, 160, 144, 220, 90, 57,
		223, 59,  3, 18, 140, 111, 166, 203, 196, 134, 243, 124, 95, 222, 179,
		197, 65, 180, 48, 36, 15, 107, 46, 233, 130, 165, 30, 123, 161, 209, 23,
		97, 16, 40, 91, 219, 61, 100, 10, 210, 109, 250, 127, 22, 138, 29, 108,
		244, 67, 207,  9, 178, 204, 74, 98, 126, 249, 167, 116, 34, 77, 193,
		200, 121,  5, 20, 113, 71, 35, 128, 13, 182, 94, 25, 226, 227, 199, 75,
		27, 41, 245, 230, 224, 43, 225, 177, 26, 155, 150, 212, 142, 218, 115,
		241, 73, 88, 105, 39, 114, 62, 255, 192, 201, 145, 214, 168, 158, 221,
		148, 154, 122, 12, 84, 82, 163, 44, 139, 228, 236, 205, 242, 217, 11,
		187, 146, 159, 64, 86, 239, 195, 42, 106, 198, 118, 112, 184, 172, 87,
		2, 173, 117, 176, 229, 247, 253, 137, 185, 99, 164, 102, 147, 45, 66,
		231, 52, 141, 211, 194, 206, 246, 238, 56, 110, 78, 248, 63, 240, 189,
		93, 92, 51, 53, 183, 19, 171, 72, 50, 33, 104, 101, 69, 8, 252, 83, 120,
		76, 135, 85, 54, 202, 125, 188, 213, 96, 235, 136, 208, 162, 129, 190,
		132, 156, 38, 47, 1, 7, 254, 24, 4, 216, 131, 89, 21, 28, 133, 37, 153,
		149, 80, 170, 68, 6, 169, 234, 151
	};

	// Pearsong hashing algorithm as described in RFC 3074.
	// -> http://www.apps.ietf.org/rfc/rfc3074.html
	char *key = __TIME__;
	hash = 8; // length of __TIME__ string
	for (uint8_t i = 8; i > 0;) hash = T[hash ^ key[--i]];
        
        #if USE_SPI   
	printf("version hash = %" PRIu8 "\n", hash);
        #endif

	// get TOS_NODE_ID
	// if not set by programming toolchain on testbed
	if (0 == TOS_NODE_ID)
	{
		uint16_t	data[2];

		// read from nRF UICR area
		gpi_nrf_uicr_read(&data, 0, sizeof(data));

		// check signature
		if (0x55AA == data[0])
		{
			GPI_TRACE_MSG(TRACE_INFO, "non-volatile config is valid");
			TOS_NODE_ID = data[1];
		}
		else GPI_TRACE_MSG(TRACE_INFO, "non-volatile config is invalid");

		// if signature is invalid
		while (0 == TOS_NODE_ID)
		{
                          #ifndef THIS_NODE_ID
                          printf("TOS_NODE_ID not set. enter value: ");

                          // read from console
                          // scanf("%u", &TOS_NODE_ID);
                          char s[8];
                          TOS_NODE_ID = atoi(getsn(s, sizeof(s)));

                          printf("\nTOS_NODE_ID set to %u\n", TOS_NODE_ID);

                          // until input value is valid
                          if (0 == TOS_NODE_ID)
                                  continue;
                          #else
                          TOS_NODE_ID = THIS_NODE_ID;
                          #endif

                          // store new value in UICR area

			data[0] = 0x55AA;
			data[1] = TOS_NODE_ID;

			gpi_nrf_uicr_erase();
			gpi_nrf_uicr_write(0, &data, sizeof(data));

			// ATTENTION: Writing to UICR requires NVMC->CONFIG.WEN to be set which in turn
			// invalidates the instruction cache (permanently). Besides that, UICR updates take
			// effect only after reset (spec. 4413_417 v1.0 4.3.3 page 24). Therefore we do a soft
			// reset after the write procedure.
                        #if USE_SPI   
			printf("Restarting system...\n");
                        #endif
			gpi_milli_sleep(100);		// safety margin (e.g. to empty UART Tx FIFO)
			NVIC_SystemReset();

			break;
		}
	}
        #if USE_SPI   
	printf("starting node %u ...\n", TOS_NODE_ID);
        #endif
	// Stop RNG because we only need one random number as seed.
	NRF_RNG->TASKS_STOP = 1;
	uint8_t rng_value = BV_BY_VALUE(RNG_VALUE_VALUE, NRF_RNG->VALUE);
	uint32_t rng_seed = rng_value * gpi_mulu_16x16(TOS_NODE_ID, gpi_tick_fast_native());
	#if USE_SPI   
        printf("random seed for Mixer is %" PRIu32"\n", rng_seed);
        #endif
	// init RNG with randomized seed
	mixer_rand_seed(rng_seed);

	// translate TOS_NODE_ID to logical node id used with mixer
	for (node_id = 0; node_id < NUM_ELEMENTS(nodes); ++node_id)
	{
		if (nodes[node_id] == TOS_NODE_ID)
			break;
	}
	if (node_id >= NUM_ELEMENTS(nodes))
	{
          #if USE_SPI   
		printf("!!! PANIC: node mapping not found for node %u !!!\n", TOS_NODE_ID);
          #endif
		//while (1);
	}
        #if USE_SPI   
	printf("mapped physical node %u to logical id %u\n", TOS_NODE_ID, node_id);
        #endif

	Gpi_Hybrid_Tick app_time = ROUND_PERIOD - MIXER_INITIATOR_DELAY - MIXER_DURATION -
							   MIXER_DEADLINE_BUFFER - BOLT_WRITE_DURATION - MIXER_ARM_DURATION -
							   AP_READ_DURATION +
							   MX_SLOT_LENGTH; // TODO: unclear (refers to MIXER_OFFSET)
	#if USE_SPI   
        printf("AP has a time window of %" PRIu32 " us for calculation and writing to Bolt.\n", gpi_tick_hybrid_to_us(app_time));

        #endif
	mixer_print_config();
        
}





//**************************************************************************************************
//***** Global Functions ***************************************************************************

int main()
{
    /*gpi_platform_init(); // Initialise Generic Platform Interface (GPI)
    gpi_int_enable(); // Enable interrupts
    init_spi(); // Initialise SPI communication to AP */
    initialization(); // this contains gpi_platform_init, gpi_int_enable and init_spi
    
    printf("Hello There\r\n");

    init_rocket();
    //while(1){}

    /*float a[NUM_CLASSES];
    uint8_t label = 0;
    int current_ts_idx = 0;
    // central learning
    if (NUM_ELEMENTS(dnni_nodes) == 1) {
      for (uint32_t i = 0; i < 100000; i++) {
        current_ts_idx = i%NUM_TIMESERIES;
        label = get_labels()[current_ts_idx];
        classify_part(get_timeseries()[current_ts_idx], a);
        update_weights(a, label, i+2);
        //current_ts_idx = i%NUM_TIMESERIES;
        //label = get_labels()[i%NUM_TIMESERIES];
      }
    }*/

    //train();
    
    for (int i = 0; i < NUM_ELEMENTS(rocket_nodes); i++) {
      if (TOS_NODE_ID == rocket_nodes[i]) {

        /*while (TOS_NODE_ID != DEVICE_ID) {
          NRF_P0->OUTSET = BV(25);
          // Wait for AP to startup
          gpi_milli_sleep(2000);
          NRF_P0->OUTCLR = BV(25);
          gpi_milli_sleep(2000);
        }*/
        printf("Starting Rocket OS\r\n");
        run_rocket_os(TOS_NODE_ID);
      }
    }

    run_relay_os(TOS_NODE_ID);
    
    /*while (1)  {
      uint8_t *test[2];
      receive_data_from_cp(test);
      printf("test[0]: %u, %u\r\n", ((ap_message_t *) test[0])->header.id, ((ap_message_t *) test[0])->header.type);
      printf("test[1]: %u, %u\r\n", ((ap_message_t *) test[1])->header.id, ((ap_message_t *) test[1])->header.type);
      printf("test[1].data: %u, %u\r\n", (uint16_t) ((ap_message_t *) test[1])->data.data[0], (uint16_t) ((ap_message_t *) test[1])->data.data[1]);
      printf("Hallo\r\n");

        ap_message_t test2[2];
        printf("Hallo %u\r\n", sizeof(layer_data_t));
        test2[0].header.id = 10;
        test2[0].header.type = TYPE_AP_ACK;

        test2[1].header.id = 20;
        test2[1].header.type = TRANSFORM_TYPE(TYPE_LAYER_RESULT);
        test2[1].data.data[0] = 11;
        test2[1].data.data[1] = 25;
        send_data_to_cp(test2, 2);

        gpi_milli_sleep(1000);
    }
    init_cp_os(&receive_data_from_AP, &send_data_to_AP, &communication_finished_callback_temp,
                &communication_starts_callback_temp, TOS_NODE_ID);
    NRF_P0->OUTCLR = BV(25);
    // Wait for AP to startup
    gpi_milli_sleep(5000);
    run();*/
}

//**************************************************************************************************
//**************************************************************************************************
