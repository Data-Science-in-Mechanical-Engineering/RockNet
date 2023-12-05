#include "uart.h"

#include "messages.h"
#include "messages.c"

#include "mixer/mixer.h"

#include "gpi/tools.h"
#include "gpi/platform.h"
#include "gpi/interrupts.h"
#include "gpi/clocks.h"
#include "gpi/olf.h"

#include "stdint.h"

void send_uart(uint8_t *message, uint16_t size){

        //uint8_t eol = '\n';
        //uint8_t buf[size + sizeof(eol)];
        //uint8_t buf[size];

        //memcpy(&buf, message, size);
        //buf[size] = eol;

        // flush data buffer (for DMA access)
	REORDER_BARRIER();

	// setup DMA
	NRF_UARTE0->TXD.PTR = (uintptr_t)message;
	NRF_UARTE0->TXD.MAXCNT = size;

	// flush data buffer writes from CPU pipeline
	// NOTE: This is not really necessary here because it has been done implicitly for sure
	// due to the short pipeline length of the Cortex-M4. We do it anyway to keep the code clean.
	__DMB();

	// start TX
	NRF_UARTE0->EVENTS_ENDTX = 0;
	NRF_UARTE0->TASKS_STARTTX = 1;

	// wait until buf can be released
	// NOTE: ENDTX implies TXSTARTED, i.e., TXD.PTR and TXD.MAXCNT are released too
	while (!(NRF_UARTE0->EVENTS_ENDTX));
}

uint8_t receive_uart(uint8_t *message, uint16_t message_size){  //make adaptable for different message sizes

        uint32_t timeout_ms = 200;
        const uint16_t TICKS_PER_MS = GPI_FAST_CLOCK_RATE / 1000u;
	
        Gpi_Fast_Tick_Native tick;

	ASSERT_CT(GPI_FAST_CLOCK_RATE == TICKS_PER_MS * 1000u, GPI_FAST_CLOCK_RATE_unsupported);
	ASSERT_CT(sizeof(tick) >= sizeof(uint32_t));

	// ensure that ms * TICKS_PER_MS < INT32_MAX (signed)
	ASSERT_CT(TICKS_PER_MS < 0x8000);

	tick = gpi_tick_fast_native();

	tick += (Gpi_Fast_Tick_Native)timeout_ms * TICKS_PER_MS;
       
        NRF_UARTE0->RXD.PTR = (uintptr_t) message;
	NRF_UARTE0->RXD.MAXCNT = message_size;

	NRF_UARTE0->EVENTS_ENDRX = 0;
	NRF_UARTE0->TASKS_STARTRX = 1;

        
	while (!(NRF_UARTE0->EVENTS_ENDRX) && (gpi_tick_compare_fast_native(gpi_tick_fast_native(), tick) <= 0));

	if (NRF_UARTE0->EVENTS_ENDRX){
          return 1;
        }
        else{
          return 0;
        }  
}
