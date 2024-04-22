#include <stdio.h>
#include "gpi/platform.h"
#include "gpi/clocks.h"

int main()
{
	gpi_platform_init();

	printf("\nLED there be light...\n");

	int c = 5;
	while (c--)
	{
		gpi_led_toggle(GPI_LED_3);
		gpi_milli_sleep(1000);
	}

	printf("Going to bed\n");
	gpi_sleep();

	return 0;
}
