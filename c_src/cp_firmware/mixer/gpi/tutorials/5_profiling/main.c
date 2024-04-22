#include "gpi/trace.h"
#define PRINT_INFO		UINT32_C(0x00000001)
GPI_TRACE_CONFIG(main, GPI_TRACE_LOG_ALL);

//**************************************************************************************************

#include "gpi/profile.h"
GPI_PROFILE_SETUP("main.c", 100, 1);

//**************************************************************************************************

#include <stdio.h>
#include "gpi/platform.h"
#include "gpi/interrupts.h"
#include "gpi/clocks.h"


void function_A(void)
{
	GPI_TRACE_FUNCTION();
	GPI_PROFILE(1, "function_A() entry");

	gpi_milli_sleep(567);

	GPI_PROFILE(1, "function_A() return");
	GPI_TRACE_RETURN();
}


int main()
{
	gpi_platform_init();
	gpi_int_enable();

	#if GPI_ARCH_IS_DEVICE(nRF52840)
		// Profiling uses SysTick timer on nRF platform.
		SysTick->LOAD  = -1u;
		SysTick->VAL   = 0;
		SysTick->CTRL  = SysTick_CTRL_CLKSOURCE_Msk | SysTick_CTRL_ENABLE_Msk;
	#endif

	printf("\nSystem initialized\n");

	Gpi_Profile_Ticket	ticket;
	const char			*module_name;
	uint16_t			line;
	uint32_t			timestamp;
	memset(&ticket, 0, sizeof(ticket));

	int counter = 5;
	while(counter--)
	{
		function_A();

		while (gpi_profile_read(&ticket, &module_name, &line, &timestamp))
		{
			printf("profile %s %4" PRIu16 ": %" PRIu32 "\n", module_name, line, timestamp);
		}
	}

	return 0;
}
