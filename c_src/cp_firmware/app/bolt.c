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
 *	@file					bolt.c
 *
 *	@brief					Bolt processor interconnect interface
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
GPI_TRACE_CONFIG(bolt, GPI_TRACE_BASE_SELECTION);

//**************************************************************************************************
//**** Includes ************************************************************************************

#include "bolt.h"
#include "gpi/clocks.h"
#include "gpi/platform.h"
#include "gpi/tools.h"

#include <nrf.h>

//**************************************************************************************************
//***** Local Defines and Consts *******************************************************************



//**************************************************************************************************
//***** Local Typedefs and Class Declarations ******************************************************

typedef enum
{
	BOLT_STATE_IDLE		= 0,
	BOLT_STATE_READ		= 1,
	BOLT_STATE_WRITE	= 2,
	BOLT_STATE_INVALID	= 3,
	BOLT_NUM_OF_STATES	= 4
} bolt_state_t;

typedef enum
{
	BOLT_OP_READ		= 0,
	BOLT_OP_WRITE		= 1,
	BOLT_NUM_OF_OPS		= 2
} bolt_op_mode_t;

typedef struct __attribute__((packed))
{
	uint16_t 	len;
	uint8_t 	data[BOLT_MAX_MSG_LEN - 2];
} bolt_spi_pkt_t;

//**************************************************************************************************
//***** Forward Declarations ***********************************************************************



//**************************************************************************************************
//***** Local (Static) Variables *******************************************************************

static volatile bolt_state_t bolt_state = BOLT_STATE_INVALID;
// EasyDMA requires that there is a valid TXD.PTR and RXD.PTR to data RAM for each transfer.
// TODO: __attribute__((section(".data"))) superflous?
static bolt_spi_pkt_t rx_buffer;
static bolt_spi_pkt_t tx_buffer;

//**************************************************************************************************
//***** Global Variables ***************************************************************************



//**************************************************************************************************
//***** Local Functions ****************************************************************************

uint8_t bolt_acquire(bolt_op_mode_t mode)
{
	if ((NRF_P0->OUT & BV(BOLT_CONF_REQ_PIN)) || BOLT_ACK_STATUS)
	{
		GPI_TRACE_MSG(TRACE_INFO, "Bolt request failed (REQ or ACK still high)");
		return 1;
	}

	if (BOLT_STATE_IDLE != bolt_state)
	{
		GPI_TRACE_MSG(TRACE_INFO, "Bolt not in idle state, operation skipped");
		return 2;
	}

	// Read mode: set BOLT_CONF_MODE_PIN low.
	if (BOLT_OP_READ == mode)
	{
		if (!BOLT_DATA_AVAILABLE)
		{
			GPI_TRACE_MSG(TRACE_INFO, "Bolt no data available");
			return 3;
		}
		NRF_P0->OUTCLR = BV(BOLT_CONF_MODE_PIN);
		GPI_TRACE_MSG(TRACE_INFO, "Bolt requesting read access");
	}
	// Write mode: set BOLT_CONF_MODE_PIN high.
	else
	{
		NRF_P0->OUTSET = BV(BOLT_CONF_MODE_PIN);
		GPI_TRACE_MSG(TRACE_INFO, "Bolt requesting write access");
	}

	// Set request line high and wait for rising edge on the ACK line (max 100us).
	// TODO: is 100us a safe bound or could we lower this? Interrupts can
	// cause this to be longer than 100us.
	NRF_P0->OUTSET = BV(BOLT_CONF_REQ_PIN);
	uint8_t cnt = 0;
	do
	{
		gpi_micro_sleep(10);
		cnt++;
	}
	while(!BOLT_ACK_STATUS && cnt < 10);

	if (!BOLT_ACK_STATUS)
	{
		// ACK is still low -> failed.
		bolt_state = BOLT_STATE_IDLE;
		NRF_P0->OUTCLR = BV(BOLT_CONF_REQ_PIN);
		GPI_TRACE_MSG(TRACE_INFO, "Bolt access denied");
		return 4;
	}

	// Update state
	bolt_state = (mode == BOLT_OP_READ) ? BOLT_STATE_READ : BOLT_STATE_WRITE;

	// Enable SPI module.
	NRF_SPIM0->ENABLE = BV_BY_NAME(SPIM_ENABLE_ENABLE, Enabled);

	return 0;
}

//**************************************************************************************************

void bolt_release(void)
{
	// Note: In bolt_read and bolt_write we wait for the transfer to finish and the peripheral to be
	// stopped so that we can safely disable it here.
	NRF_SPIM0->ENABLE = BV_BY_NAME(SPIM_ENABLE_ENABLE, Disabled);
	// Set REQ low.
	NRF_P0->OUTCLR = BV(BOLT_CONF_REQ_PIN);
	// Wait for ACK to go down.
	while (BOLT_ACK_STATUS) ;
	bolt_state = BOLT_STATE_IDLE;
	GPI_TRACE_MSG(TRACE_INFO, "Bolt back in idle state");
}

//**************************************************************************************************
//***** Global Functions ***************************************************************************

uint8_t bolt_init(void)
{
	// Disable SPI module before configuration.
	NRF_SPIM0->ENABLE = BV_BY_NAME(SPIM_ENABLE_ENABLE, Disabled);

	// P0.14: GPIO, used as COM_SCK
	NRF_P0->PIN_CNF[14] =
		BV_BY_NAME(GPIO_PIN_CNF_DIR, Output)		|
		BV_BY_NAME(GPIO_PIN_CNF_INPUT, Disconnect)	|
		BV_BY_NAME(GPIO_PIN_CNF_PULL, Disabled)		|
		BV_BY_NAME(GPIO_PIN_CNF_DRIVE, S0S1)		|
		BV_BY_NAME(GPIO_PIN_CNF_SENSE, Disabled);

	// P0.15: GPIO, used as COM_MISO
	NRF_P0->PIN_CNF[15] =
		BV_BY_NAME(GPIO_PIN_CNF_DIR, Input)			|
		BV_BY_NAME(GPIO_PIN_CNF_INPUT, Connect)		|
		BV_BY_NAME(GPIO_PIN_CNF_PULL, Disabled)		| // see DPP2_user_guide
		// BV_BY_NAME(GPIO_PIN_CNF_PULL, Pulldown)		|
		BV_BY_NAME(GPIO_PIN_CNF_SENSE, Disabled);

	// P0.16: GPIO, used as COM_MOSI
	NRF_P0->PIN_CNF[16] =
		BV_BY_NAME(GPIO_PIN_CNF_DIR, Output)		|
		BV_BY_NAME(GPIO_PIN_CNF_INPUT, Disconnect)	|
		BV_BY_NAME(GPIO_PIN_CNF_PULL, Disabled)		|
		BV_BY_NAME(GPIO_PIN_CNF_DRIVE, S0S1)		|
		BV_BY_NAME(GPIO_PIN_CNF_SENSE, Disabled);
	NRF_P0->OUTCLR = BV(16);

	NRF_SPIM0->PSEL.SCK =
		BV_BY_VALUE(SPIM_PSEL_SCK_PORT, 0)	|
		BV_BY_VALUE(SPIM_PSEL_SCK_PIN, 14)	|
		BV_BY_NAME(SPIM_PSEL_SCK_CONNECT, Connected);

	NRF_SPIM0->PSEL.MISO =
		BV_BY_VALUE(SPIM_PSEL_MISO_PORT, 0)	|
		BV_BY_VALUE(SPIM_PSEL_MISO_PIN, 15)	|
		BV_BY_NAME(SPIM_PSEL_MISO_CONNECT, Connected);

	NRF_SPIM0->PSEL.MOSI =
		BV_BY_VALUE(SPIM_PSEL_MOSI_PORT, 0)	|
		BV_BY_VALUE(SPIM_PSEL_MOSI_PIN, 16)	|
		BV_BY_NAME(SPIM_PSEL_MOSI_CONNECT, Connected);

	// Chip select line is not needed because Bolt uses specific GPIO lines.
	NRF_SPIM0->PSEL.CSN = BV_BY_NAME(SPIM_PSEL_CSN_CONNECT, Disconnected);
	NRF_SPIM0->PSELDCX = BV_BY_NAME(SPIM_PSELDCX_CONNECT, Disconnected);

	// Bolt supports SPI master with up to 4MHz (= 4Mbps) clock speed.
	NRF_SPIM0->FREQUENCY = BV_BY_NAME(SPIM_FREQUENCY_FREQUENCY, M4);

	NRF_SPIM0->CONFIG =
		BV_BY_NAME(SPIM_CONFIG_CPHA, Leading)	|
		BV_BY_NAME(SPIM_CONFIG_CPOL, ActiveHigh)	|
		BV_BY_NAME(SPIM_CONFIG_ORDER, MsbFirst);

	NRF_SPIM0->ORC = 0;

	// Enable the SPI module only when needed (bolt_acquire).
	// NRF_SPIM0->ENABLE = BV_BY_NAME(SPIM_ENABLE_ENABLE, Enabled);

	bolt_state = BOLT_STATE_IDLE;

	if(bolt_status() != 0) {
		GPI_TRACE_MSG(TRACE_INFO, "Bolt not accessible, init failed");
		bolt_state = BOLT_STATE_INVALID;
		return 1;
	}

	GPI_TRACE_MSG(TRACE_INFO, "Bolt initialized with message size %u", BOLT_MAX_MSG_LEN);
	return 0;
}

//**************************************************************************************************

// ATTENTION: Parameter buffer must be bigger or equal to BOLT_MAX_MSG_LEN!
uint16_t bolt_read(void *buffer)
{
	if (!buffer)
	{
		GPI_TRACE_MSG(TRACE_INFO, "Bolt invalid parameter");
		return 0;
	}

	if (bolt_acquire(BOLT_OP_READ) != 0) return 0;

	GPI_TRACE_MSG(TRACE_INFO, "Bolt starting data transfer");

	// NOTE: It remains unclear from the documentation if RXD.PTR and TXD.PTR have to be set before
	// every transfer. To be on the safe side, we do.
	NRF_SPIM0->TXD.PTR = (uintptr_t)&tx_buffer;
	NRF_SPIM0->TXD.MAXCNT = sizeof(tx_buffer);
	NRF_SPIM0->RXD.PTR = (uintptr_t)&rx_buffer;
	NRF_SPIM0->RXD.MAXCNT = sizeof(rx_buffer);

	NRF_SPIM0->TASKS_START = 1;

	// Bolt indicates the end of the transfer by lowering the ACK line.
	while (BOLT_ACK_STATUS) ;

	if (!NRF_SPIM0->EVENTS_END)
	{
		// Master is still in the transaction (BOLT_MAX_MSG_LEN not reached) but Bolt has already
		// signaled the end of the transaction (ACK line low). At this point we can safely stop the
		// transaction.
		NRF_SPIM0->TASKS_STOP = 1;
		while (!NRF_SPIM0->EVENTS_STOPPED) ;
		NRF_SPIM0->EVENTS_STOPPED = 0;
	}

	// When the master has stopped the ENDRX, ENDTX and END events are generated automatically.
	// However, the manual does not specify the delay so to be safe we wait for the END event.
	while (!NRF_SPIM0->EVENTS_END);
	// Events must be reset manually.
	NRF_SPIM0->EVENTS_ENDRX = 0;
	NRF_SPIM0->EVENTS_ENDTX = 0;
	NRF_SPIM0->EVENTS_END = 0;

	// When reading data from Bolt, we stop the transfer as soon as Bolt lowers the ACK line. By
	// doing so we potentially receive superflous bytes at the end. To hide this behavior from the
	// application and return the correct number of bytes, we include the length in the first two
	// bytes before the transfer and strip them afterwards.
	memcpy(buffer, rx_buffer.data, rx_buffer.len);

	GPI_TRACE_MSG(TRACE_INFO, "Bolt %" PRIu32 " bytes received (actual len = %" PRIu16 ")",
		NRF_SPIM0->RXD.AMOUNT, rx_buffer.len);

	bolt_release();

	return rx_buffer.len;
}

//**************************************************************************************************

uint8_t bolt_write(const void *data, uint16_t len)
{
	if (!data)
	{
		GPI_TRACE_MSG(TRACE_INFO, "Bolt write with invalid data pointer");
		return 1;
	}

	// BOLT_MAX_MSG_LEN - 2 because we include the actual length (2 B) into the packet.
	if (!len || (len > (BOLT_MAX_MSG_LEN - 2)))
	{
		GPI_TRACE_MSG(TRACE_INFO, "Bolt write with invalid length (ensure len <= BOLT_MAX_MSG_LEN - 2)");
		return 2;
	}

	if (bolt_acquire(BOLT_OP_WRITE) != 0) return 3;

	// When reading data from Bolt, we stop the transfer as soon as Bolt lowers the ACK line. By
	// doing so we potentially receive superflous bytes at the end. To hide this behavior from the
	// application and return the correct number of bytes, we include the length in the first two
	// bytes before the transfer and strip them afterwards.
	// ((bolt_spi_packet*)tx_buffer)->len = len;
	// memcpy(((bolt_spi_packet*)tx_buffer)->data, data, len);
	tx_buffer.len = len;
	memcpy(tx_buffer.data, data, len);

	GPI_TRACE_MSG(TRACE_INFO, "Bolt starting data transfer");

	// NOTE: It remains unclear from the documentation if RXD.PTR and TXD.PTR have to be set before
	// every transfer. To be on the safe side, we do.
	NRF_SPIM0->TXD.PTR = (uintptr_t)&tx_buffer;
	NRF_SPIM0->TXD.MAXCNT = len + 2;
	NRF_SPIM0->RXD.PTR = (uintptr_t)&rx_buffer;
	NRF_SPIM0->RXD.MAXCNT = len + 2;

	NRF_SPIM0->TASKS_START = 1;
	// Wait for the end of the transfer (END event).
	while (!NRF_SPIM0->EVENTS_END)
	{
		if (!BOLT_ACK_STATUS)
		{
			// Some error occured and Bolt lowered the ACK line. The transfer can be aborted.
			NRF_SPIM0->TASKS_STOP = 1;
			while (!NRF_SPIM0->EVENTS_STOPPED) ;
			NRF_SPIM0->EVENTS_STOPPED = 0;
			// When the master has stopped the ENDRX, ENDTX and END events are generated
			// automatically. However, the manual does not specify the delay so to be safe we wait
			// for the END event.
			while (!NRF_SPIM0->EVENTS_END);
			NRF_SPIM0->EVENTS_ENDRX = 0;
			NRF_SPIM0->EVENTS_ENDTX = 0;
			NRF_SPIM0->EVENTS_END = 0;

			bolt_release();
			GPI_TRACE_MSG(TRACE_INFO, "Bolt transfer aborted");
			return 4;
		}
	}
	// Events must be reset manually.
	NRF_SPIM0->EVENTS_ENDRX = 0;
	NRF_SPIM0->EVENTS_ENDTX = 0;
	NRF_SPIM0->EVENTS_END = 0;

	GPI_TRACE_MSG(TRACE_INFO, "Bolt data written (TXD.AMOUNT %" PRIu32 " B)", NRF_SPIM0->TXD.AMOUNT);

	bolt_release();
	return 0;
}

//**************************************************************************************************
uint8_t bolt_status(void)
{
	if (bolt_acquire(BOLT_OP_WRITE) == 0)
	{
		bolt_release();
		return 0;
	}

	return 1;
}

//**************************************************************************************************

void bolt_flush(void)
{
	while (BOLT_DATA_AVAILABLE) bolt_read(&rx_buffer);
}

//**************************************************************************************************
//**************************************************************************************************
