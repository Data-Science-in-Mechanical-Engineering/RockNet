#include "cp_os.h"
#include "uart.h"
#include "internal_messages.h"
#include "gpi/tools.h"
#include "gpi/platform.h"
#include "gpi/interrupts.h"
#include "gpi/clocks.h"
#include "gpi/olf.h"
#include "cp_os.h"
#include <stdint.h>


static uint8_t communication_finished_callback(ap_message_t *data, uint16_t size)
{
  return 0;
} 
                
static uint16_t communication_starts_callback(ap_message_t **data)
{
  return 0;
}

void run_relay_os(uint8_t id)
{ 
  init_cp_os(&communication_finished_callback, &communication_starts_callback, id);
  run();
}