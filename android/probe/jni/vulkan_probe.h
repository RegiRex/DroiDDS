/* CodexAstraUlt: Original bounded graphics probe boundary. This executes only
 * synthetic offscreen draws; it is not a PICA renderer or game benchmark. */
#ifndef DROIDDS_VULKAN_PROBE_H
#define DROIDDS_VULKAN_PROBE_H

#include <stddef.h>

/* CodexAstraUlt: A positive return is the UTF-8 JSON length excluding its written
 * NUL terminator. A negative return means serialization/capacity failure. Driver
 * hangs require an external process deadline; this function is not a watchdog. */
int dds_vk_probe_run(char *json, size_t capacity);

#endif
