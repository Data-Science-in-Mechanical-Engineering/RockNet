/***************************************************************************************************
 ***************************************************************************************************
 *
 *	Copyright (c) 2022-, Institute for Data Science in Mechanical Engineering, RWTH Aachen
 *	All rights reserved.
 *
 *	Redistribution and use in source and binary forms, with or without
 *	modification, are permitted provided that the following conditions are met:
 *		* Redistributions of source code must retain the above copyright
 *		  notice, this list of conditions and the following disclaimer.
 *		* Redistributions in binary form must reproduce the above copyright
 *		  notice, this list of conditions and the following disclaimer in the
 *		  documentation and/or other materials provided with the distribution.
 *		* Neither the name of the DSME or RWTH nor the
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
 *	@file					cp_os.h
 *
 *	@brief					defines the functions and makros needed to run the communication processor
 *
 *	@version				$Id$
 *	@date					TODO
 *
 *	@author					Alexander Graefe
 *
 ***************************************************************************************************

 	@details

	

 **************************************************************************************************/

#ifndef CP_OS_H
#define CP_OS_H

#include "spi.h"
#include "internal_messages.h"
#include "mixer_config.h"
#include "wireless_control.h"
#include <stdint.h>

/**
 * inits the communication processor.
 * @param receive_data_from_AP function which reads data from AP and writes it into the pointer.#
 * @param send_data_to_AP function which sends data to AP. The first parameter is the list of data. The second parameter is the length of the data.
 * @param communication_finished_callback is called after communication is finished. Use this to preprocess data and send it to agent.
 *                                        The first parameter is a list of all messages. The second parameter is a list, which specifies
 *                                        if the message at the same index in the first parameter was received succesfully. (Do not use
 *                                        use message if 0). If communication_finished_callback returns a value unequal to zero,
 *                                        run_normal_operation will terminate.
 * @param communication_starts_callback   is called before communication starts. Use this to read data from AP. Wirte the data into the
 *                                        first parameter. Returns the size of messages to send.
 * @param id id of CP
 */
void init_cp_os(uint8_t (*communication_finished_callback)(ap_message_t*, uint16_t), 
                uint16_t (*communication_starts_callback)(ap_message_t**),
                uint8_t id);

/**
 * runs the communication processor. Call this method to run the communication including search for AP and other CPs
 */
void run();

/**
 * waits until the CP has connection to the AP
 * @param the function writes the data it receives from the agent into this.
 */
void wait_for_AP(ap_message_t *AP_pkt);

/**
 * waits until it has connectionn to other agents
 * 
 */
void wait_for_other_agents();


/**
 * run in normal operation.
 */
void run_normal_operation();

#endif
