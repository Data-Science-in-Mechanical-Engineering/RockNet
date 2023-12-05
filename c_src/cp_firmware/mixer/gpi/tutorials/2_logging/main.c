#include "gpi/trace.h"
#define PRINT_INFO		UINT32_C(0x00000001)
#define PRINT_WHILE		UINT32_C(0x00000002)
// GPI_TRACE_CONFIG(main, PRINT_WHILE);
// GPI_TRACE_CONFIG(main, GPI_TRACE_LOG_USER);
// GPI_TRACE_CONFIG(main, GPI_TRACE_LOG_PROGRAM_FLOW | GPI_TRACE_LOG_USER);
GPI_TRACE_CONFIG(main, GPI_TRACE_LOG_ALL);

//**************************************************************************************************

#include <stdio.h>
#include "gpi/platform.h"
#include "gpi/interrupts.h"
#include "gpi/clocks.h"


unsigned int function_B()
{
	static unsigned int retCode = 0;
	GPI_TRACE_FUNCTION();
	GPI_TRACE_MSG(PRINT_INFO, "Don't call me again!");
	GPI_TRACE_RETURN(++retCode);
}


void function_A()
{
	GPI_TRACE_FUNCTION();
	GPI_TRACE_MSG(PRINT_INFO, "I am going to call function_B");
	function_B();
	GPI_TRACE_RETURN();
}


int main()
{
	gpi_platform_init();
	gpi_int_enable();

	printf("\nSystem initialized\n");

	uint16_t counter = 0;
	while (counter < 5)
	{
		GPI_TRACE_MSG(PRINT_WHILE, "while loop iteration %u", ++counter);
		function_A();
		gpi_milli_sleep(5000);
	}

	return 0;
}
