#include "spi.h"

#include "mixer/mixer.h"

#include "gpi/tools.h"
#include "gpi/platform.h"
#include "gpi/interrupts.h"
#include "gpi/clocks.h"
#include "gpi/olf.h"

static uint8_t dummy[1024];

void init_spi()
{


        // P0.013 GPIO / SPI CS
	NRF_P0->PIN_CNF[13] =
		BV_BY_NAME(GPIO_PIN_CNF_DIR, Output)		|
		BV_BY_NAME(GPIO_PIN_CNF_INPUT, Disconnect)	|
		BV_BY_NAME(GPIO_PIN_CNF_PULL, Disabled)		|
		BV_BY_NAME(GPIO_PIN_CNF_DRIVE, S0S1)		|
		BV_BY_NAME(GPIO_PIN_CNF_SENSE, Disabled);
	NRF_P0->OUTCLR = BV(13);

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
  NRF_SPIM0->ENABLE = BV_BY_NAME(SPIM_ENABLE_ENABLE, Enabled);


}

void spi_send(uint8_t *data_p, uint8_t *rx_data_p, uint16_t size)
{
  // cs used otherwise
  //NRF_P0->OUTCLR = BV(13); // pin doesnt have to be toggled anymore!
  // NOTE: It remains unclear from the documentation if RXD.PTR and TXD.PTR have to be set before
  // every transfer. To be on the safe side, we do.
  NRF_SPIM0->TXD.PTR = (uintptr_t) data_p;
  NRF_SPIM0->TXD.MAXCNT = size;
  NRF_SPIM0->RXD.PTR = (uintptr_t) rx_data_p;
  NRF_SPIM0->RXD.MAXCNT = size;

  NRF_SPIM0->TASKS_START = 1;
  // When the master has stopped the ENDRX, ENDTX and END events are generated automatically.
  // However, the manual does not specify the delay so to be safe we wait for the END event.
  while (!NRF_SPIM0->EVENTS_END);
  // Events must be reset manually.
  NRF_SPIM0->EVENTS_ENDRX = 0;
  NRF_SPIM0->EVENTS_ENDTX = 0;
  NRF_SPIM0->EVENTS_END = 0;
  //NRF_P0->OUTSET = BV(13);
}


void spi_rx(uint8_t *rx_data_p, uint16_t size)
{
  printf("spi_rx %u, %u\r\n", rx_data_p, size);
  spi_send(dummy, rx_data_p, size);
}

void spi_tx(uint8_t *tx_data_p, uint16_t size)
{
  spi_send(tx_data_p, dummy, size);
}