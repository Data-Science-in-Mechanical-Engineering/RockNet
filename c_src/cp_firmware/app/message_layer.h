#ifndef MESSAGE_LAYER_H
#define MESSAGE_LAYER_H

#include "mixer_config.h"

/**
  initializes the message layer
 */
void message_layer_init();

/**
 * gets the message from layer with id. 
 * @param id id of message
 * @param msg pointer to write message into. Caution, the pointer has to point to a space, which is as big as specified in message_assignment
 * @returns 0, if message was not received, 1,if message was receives
 */
uint8_t message_layer_get_message(uint8_t id, uint8_t *msg);

/**
 * sets the message from id to layer. 
 * @param id id of message
 * @param msg pointer of message.
 */
uint8_t message_layer_set_message(uint8_t id, uint8_t *message);

/**
 * @param mixer_idx index of mixer message
 * @param msg_p pointer to message
 * @param size size in byte to read
 * @returns 0, if message was not received
 */
uint8_t read_message_from_mixer(uint8_t mixer_idx, uint8_t *msg_p, uint16_t size);

#endif