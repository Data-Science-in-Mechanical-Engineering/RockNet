#ifndef UART_H
#define UART_H

#include <stdint.h>
#include <stddef.h>

void send_uart(uint8_t* message, uint16_t size);

uint8_t receive_uart(uint8_t* message, uint16_t message_size);



#endif