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
 *	@file					bolt.h
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

#ifndef __GPI_ARM_nRF_DPP2_COM_BOLT_H__
#define __GPI_ARM_nRF_DPP2_COM_BOLT_H__

//**************************************************************************************************
//***** Includes ***********************************************************************************

#include <stdint.h>

//**************************************************************************************************
//***** Global (Public) Defines and Consts *********************************************************

#define BOLT_CONF_TIMEREQ_PIN		2
#define BOLT_CONF_ACK_PIN			17
#define BOLT_CONF_MODE_PIN			19
#define BOLT_CONF_IND_PIN			20
#define BOLT_CONF_REQ_PIN			21

#ifndef BOLT_MAX_MSG_LEN
	#define BOLT_MAX_MSG_LEN		64
#endif // BOLT_MAX_MSG_LEN

#define BOLT_DATA_AVAILABLE			(NRF_P0->IN & BV(BOLT_CONF_IND_PIN))
#define BOLT_ACK_STATUS				(NRF_P0->IN & BV(BOLT_CONF_ACK_PIN))

//**************************************************************************************************
//***** Local (Private) Defines and Consts *********************************************************



//**************************************************************************************************
//***** Forward Class and Struct Declarations ******************************************************



//**************************************************************************************************
//***** Global Typedefs and Class Declarations *****************************************************



//**************************************************************************************************
//***** Global Variables ***************************************************************************



//**************************************************************************************************
//***** Prototypes of Global Functions *************************************************************

#ifdef __cplusplus
	extern "C" {
#endif

 // @brief initializes all required GPIO pins and peripherals for Bolt
 // @return 0 if successful (= Bolt accessible), 1 otherwise
uint8_t		bolt_init(void);

// @return 0 if BOLT is active/ready (= responds to a write request) and 1 otherwise
uint8_t		bolt_status(void);

// @brief flush the BOLT queue (drop all messages)
void		bolt_flush(void);

// @brief read a message from Bolt
// @param[out] buffer	the output buffer to hold the received data, must be at least
//					BOLT_CONF_MAX_MSG_LEN long
uint16_t	bolt_read(void *buffer);

// @brief read a message from Bolt
// @param[in] data		the data to send to Bolt
// @param[in] len		the number of bytes to write
// @return 0 if successful, 1 otherwise
uint8_t		bolt_write(const void *data, uint16_t len);

#ifdef __cplusplus
	}
#endif

//**************************************************************************************************
//***** Implementations of Inline Functions ********************************************************



//**************************************************************************************************
//**************************************************************************************************

#endif // __GPI_ARM_nRF_DPP2_COM_BOLT_H__
