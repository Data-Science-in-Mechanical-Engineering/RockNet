#include "gpi/trace.h"
#define PRINT_INFO		UINT32_C(0x00000001)
GPI_TRACE_CONFIG(main, GPI_TRACE_LOG_ALL);

//**************************************************************************************************

#include <stdio.h>
#include "gpi/platform.h"
#include "gpi/interrupts.h"
#include "gpi/clocks.h"


int main()
{
	gpi_platform_init();
	gpi_int_enable();

	printf("\nSystem initialized\n");

	uint16_t counter = 5;
	while (counter--)
	{
		Gpi_Fast_Tick_Native start, end;

		start = gpi_tick_fast_native();
		GPI_TRACE_MSG(PRINT_INFO, "executing GPI_TRACE_MSG");
		end = gpi_tick_fast_native();
		GPI_TRACE_MSG(PRINT_INFO, "GPI_TRACE_MSG execution time = %" PRIu32 " us",
					  gpi_tick_fast_to_us(end - start));

		start = gpi_tick_fast_native();
		GPI_TRACE_MSG_FAST(PRINT_INFO, "executing GPI_TRACE_MSG_FAST");
		end = gpi_tick_fast_native();
		GPI_TRACE_MSG(PRINT_INFO, "GPI_TRACE_MSG_FAST execution time = %" PRIu32 " us",
					  gpi_tick_fast_to_us(end - start));

		gpi_milli_sleep(5000);
	}

	return 0;
}
