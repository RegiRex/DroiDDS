/* CodexAstraUlt: Internal original capability/representative-pipeline probe.
 * Its tiny synthetic paths do not implement or qualify full PICA semantics. */
#ifndef DROIDDS_VULKAN_RENDERER_H
#define DROIDDS_VULKAN_RENDERER_H
#include <stddef.h>
#include <stdint.h>
#include <vulkan/vulkan.h>

/* CodexAstraUlt: Always serialize bounded evidence, including unsupported
 * capabilities. Only actual successful readbacks set passed to one. */
int dds_renderer_probe_run(VkInstance instance, VkPhysicalDevice physical,
                          uint32_t instance_api, char *json, size_t capacity,
                          int *passed);
#endif
