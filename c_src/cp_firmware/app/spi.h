#ifndef SPI_H
#define SPI_H

#include <stdint.h>

#define SPI_WAIT_TIME 2 // time in us to wait after spi transmission such that AP can process it.

void init_spi();

void spi_send(uint8_t *data_p, uint8_t *rx_data_p, uint16_t size);

void spi_rx(uint8_t *rx_data_p, uint16_t size);

void spi_tx(uint8_t *tx_data_p, uint16_t size);

#endif