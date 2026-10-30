#ifndef DROIDDS_TITLE_API_H
#define DROIDDS_TITLE_API_H

/* CodexAstraUlt: Persistent generic-title ABI. A token names one generation on
 * its creating worker, never a raw pointer. Every operation uses that worker. */
#include <stddef.h>
#include <stdint.h>

#define DDS_TITLE_TOP_BYTES (400U * 240U * 4U)
#define DDS_TITLE_BOTTOM_BYTES (320U * 240U * 4U)
#define DDS_TITLE_PCM_FRAMES 4096U
#define DDS_TITLE_METRICS 5U
#define DDS_TITLE_MANIFEST_BYTES (1024U * 1024U)
#define DDS_TITLE_READY_TOP 1U
#define DDS_TITLE_READY_BOTTOM 2U

/* CodexAstraUlt: u64 fields match Rust repr(C). PCM counts are stereo frames;
 * ready_mask describes independent optional screen updates, including no frame
 * on a cooperative yield. Cycles/frames are cumulative guest observations. */
typedef struct DdsTitleMetrics {
    uint64_t frames;
    uint64_t cycles;
    uint64_t pcm_frames;
    uint64_t exited;
    uint64_t ready_mask;
} DdsTitleMetrics;

/* CodexAstraUlt: Open consumes no caller buffer. It writes zero before work and
 * a unique token only after installation; the caller closes that token if JSON
 * transfer fails. Native/hardware are booleans. Free returned UTF-8 JSON with
 * droidds_title_free exactly once. Paths select input, installer libraries and
 * durable runtime storage; this API never clears the latter. */
char *droidds_title_open(const uint8_t *manifest, size_t manifest_bytes,
    const char *input, const char *native_directory, const char *data_directory,
    uint32_t native_mode, uint32_t hardware, uint64_t *opened_token);
char *droidds_title_report(uint64_t token);
void droidds_title_free(char *report);
int32_t droidds_title_pause(uint64_t token);
int32_t droidds_title_resume(uint64_t token);
int32_t droidds_title_close(uint64_t token);

/* CodexAstraUlt: 0 means a completed bounded slice, -2 a recoverable paused
 * rejection, and -1 failure. Shapes are checked before advancing or writing;
 * RGBA lengths are bytes and PCM lengths are individual interleaved i16 samples.
 * All output buffers are required, mutually disjoint and valid for this call.
 * Axes must be finite within [-1,1]; touched coordinates use guest pixels. */
int32_t droidds_title_slice(uint64_t token, uint32_t buttons,
    float circle_x, float circle_y, float c_stick_x, float c_stick_y,
    int32_t touch_x, int32_t touch_y, uint32_t touched,
    uint8_t *top_rgba, size_t top_bytes, uint8_t *bottom_rgba, size_t bottom_bytes,
    int16_t *pcm, size_t pcm_samples, DdsTitleMetrics *metrics);

#endif
