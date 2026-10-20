#ifndef DROIDDS_HOMEBREW_API_H
#define DROIDDS_HOMEBREW_API_H

/* CodexAstraUlt: Fixed, original-homebrew ABI shared by Rust and JNI. Tokens
 * select a generation-checked session on its owning worker, never a raw pointer. */
#include <stddef.h>
#include <stdint.h>

#define DDS_HOMEBREW_TOP_BYTES (400U * 240U * 4U)
#define DDS_HOMEBREW_BOTTOM_BYTES (320U * 240U * 4U)
#define DDS_HOMEBREW_PCM_FRAMES 4096U
#define DDS_HOMEBREW_METRICS 4U

/* CodexAstraUlt: All fields are uint64_t, preserving an unambiguous repr(C)
 * layout. PCM counts are stereo frames; buffers contain interleaved i16 samples. */
typedef struct DdsHomebrewMetrics {
    uint64_t frame_index;
    uint64_t guest_serial;
    uint64_t pcm_frames;
    uint64_t exited;
} DdsHomebrewMetrics;

/* CodexAstraUlt: JSON allocations use droidds_probe_free. Open returns a positive
 * signed-64-bit-compatible token in JSON; failure has no usable token. */
/* CodexAstraUlt: Open writes zero before work and its newly created token on
 * success, so JNI can close that exact session if Java result allocation fails. */
char *droidds_homebrew_open(const char *library_directory, const char *scratch_directory,
                          uint64_t *opened_token);
char *droidds_homebrew_probe(const char *library_directory, const char *scratch_directory);
char *droidds_homebrew_report(uint64_t token);
void droidds_homebrew_close(uint64_t token);
int32_t droidds_homebrew_pause(uint64_t token, uint32_t paused);

/* CodexAstraUlt: Zero means success, -2 is a recoverable paused-session rejection,
 * and other negative values are failed session steps requiring report/close.
 * Lengths are bytes for RGBA and individual i16 samples for PCM. Rust never
 * retains these borrows; frame() validates capacities before writing output. */
int32_t droidds_homebrew_frame(uint64_t token, uint32_t buttons,
    int32_t touch_x, int32_t touch_y, uint32_t touched,
    uint8_t *top_rgba, size_t top_bytes, uint8_t *bottom_rgba, size_t bottom_bytes,
    int16_t *pcm, size_t pcm_samples, DdsHomebrewMetrics *metrics);

#endif
