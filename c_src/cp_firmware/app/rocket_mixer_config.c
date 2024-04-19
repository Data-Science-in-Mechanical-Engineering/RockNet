#include "rocket_mixer_config.h"

#include "gpi/tools.h"

uint8_t get_rocket_node_idx(uint8_t id) 
{
  uint8_t i;
  for (i = 0; i < NUM_ELEMENTS(rocket_nodes); i++) {
    if (rocket_nodes[i] == id) {
      return i;
    }
  }
  return 255;
}