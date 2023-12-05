#include "gpi/trace.h"
#define PRINT_INFO		UINT32_C(0x00000001)
GPI_TRACE_CONFIG(main, GPI_TRACE_LOG_ALL);

//**************************************************************************************************

#include <stdio.h>
#include "gpi/platform.h"
#include "gpi/interrupts.h"
#include "gpi/clocks.h"
#include "gpi/tools.h"


// ASSERT_CT_STATIC(sizeof(unsigned int) == sizeof(uint32_t), int_types_do_not_match);
ASSERT_CT_STATIC(sizeof(unsigned int) == sizeof(uint16_t), int_types_do_not_match);


int main()
{
	gpi_platform_init();
	gpi_int_enable();

	printf("\nSystem initialized\n");

	ASSERT_CT(sizeof(Gpi_Slow_Tick_Extended) == sizeof(uint32_t),
			  Gpi_Slow_Tick_Extended_has_wrong_size);

	if (ASSERT_CT_EVAL(sizeof(uint16_t) == sizeof(unsigned int)))
	{
		GPI_TRACE_MSG(PRINT_INFO, "The dead path...");
	}
	else
	{
		GPI_TRACE_MSG(PRINT_INFO, "The only path...");
	}

	return 0;
}
