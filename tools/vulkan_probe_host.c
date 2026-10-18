/* CodexAstraUlt: Execute the identical offscreen probe on a host Vulkan driver.
 * Python validates actual readback evidence; a successful process exit is not a pass. */
#include "vulkan_probe.h"
#include <stdio.h>

int main(void) {
    char report[65536];
    const int length = dds_vk_probe_run(report, sizeof(report));
    if (length <= 0 || (size_t)length >= sizeof(report)) {
        return 2;
    }
    if (fwrite(report, 1, (size_t)length, stdout) != (size_t)length) {
        return 3;
    }
    return putchar('\n') == EOF ? 3 : 0;
}
