/* CodexAstraUlt: Bounded JNI transport for the original interactive guest.
 * Guest execution owns the pixels/PCM; this bridge only converts/copies them. */
#include <jni.h>
#include <stdint.h>
#include <string.h>
#include "homebrew_api.h"

extern void droidds_probe_free(char *report);

/* CodexAstraUlt: One fixed workspace per calling worker avoids per-frame native
 * allocations and shared mutable buffers across threads. Never retain JNI borrows. */
static _Thread_local jint top_pixels[400U * 240U];
static _Thread_local jint bottom_pixels[320U * 240U];
static _Thread_local int16_t pcm_samples[DDS_HOMEBREW_PCM_FRAMES * 2U];

static void homebrew_error(JNIEnv *env, const char *message) {
    jclass type = (*env)->FindClass(env, "java/lang/IllegalStateException");
    if (type != NULL) {
        (*env)->ThrowNew(env, type, message);
        (*env)->DeleteLocalRef(env, type);
    }
}

/* CodexAstraUlt: All JSON stays ordinary UTF-8 and is released by its allocator,
 * including JNI allocation/copy failures. No report is passed to NewStringUTF. */
static jbyteArray homebrew_json(JNIEnv *env, char *owned) {
    const size_t limit = 256U * 1024U;
    if (owned == NULL) {
        homebrew_error(env, "Interactive runtime returned no report");
        return NULL;
    }
    const size_t length = strnlen(owned, limit + 1U);
    if (length == 0U || length > limit) {
        droidds_probe_free(owned);
        homebrew_error(env, "Interactive runtime report exceeds its bound");
        return NULL;
    }
    jbyteArray result = (*env)->NewByteArray(env, (jsize)length);
    if (result != NULL) {
        (*env)->SetByteArrayRegion(env, result, 0, (jsize)length, (const jbyte *)owned);
    }
    droidds_probe_free(owned);
    return result;
}

static jbyteArray homebrew_paths(JNIEnv *env, jstring libraries, jstring scratch,
                                 char *(*operation)(const char *, const char *)) {
    if (libraries == NULL || scratch == NULL) {
        homebrew_error(env, "Android did not provide interactive runtime paths");
        return NULL;
    }
    const char *library_path = (*env)->GetStringUTFChars(env, libraries, NULL);
    if (library_path == NULL) return NULL;
    const char *scratch_path = (*env)->GetStringUTFChars(env, scratch, NULL);
    if (scratch_path == NULL) {
        (*env)->ReleaseStringUTFChars(env, libraries, library_path);
        return NULL;
    }
    char *result = operation(library_path, scratch_path);
    (*env)->ReleaseStringUTFChars(env, scratch, scratch_path);
    (*env)->ReleaseStringUTFChars(env, libraries, library_path);
    return homebrew_json(env, result);
}

JNIEXPORT jbyteArray JNICALL
Java_org_droidds_probe_ProbeController_nativeHomebrewProbe(JNIEnv *env, jclass owner,
                                                         jstring libraries, jstring scratch) {
    (void)owner;
    return homebrew_paths(env, libraries, scratch, droidds_homebrew_probe);
}

JNIEXPORT jbyteArray JNICALL
Java_org_droidds_probe_HomebrewController_nativeOpen(JNIEnv *env, jclass owner,
    jstring libraries, jstring scratch, jlongArray opening_token) {
    (void)owner;
    if (libraries == NULL || scratch == NULL || opening_token == NULL
            || (*env)->GetArrayLength(env, opening_token) != 1) {
        homebrew_error(env, "Android did not provide interactive runtime paths/token output");
        return NULL;
    }
    const jlong zero = 0;
    (*env)->SetLongArrayRegion(env, opening_token, 0, 1, &zero);
    if ((*env)->ExceptionCheck(env)) return NULL;
    const char *library_path = (*env)->GetStringUTFChars(env, libraries, NULL);
    if (library_path == NULL) return NULL;
    const char *scratch_path = (*env)->GetStringUTFChars(env, scratch, NULL);
    if (scratch_path == NULL) {
        (*env)->ReleaseStringUTFChars(env, libraries, library_path);
        return NULL;
    }
    /* CodexAstraUlt: Java allocates its token output before native creation and
     * takes ownership before JSON parsing. JNI retains ownership until both
     * transfers succeed, including allocation/copy failures with exceptions. */
    uint64_t opened_token = 0;
    char *owned = droidds_homebrew_open(library_path, scratch_path, &opened_token);
    (*env)->ReleaseStringUTFChars(env, scratch, scratch_path);
    (*env)->ReleaseStringUTFChars(env, libraries, library_path);
    jbyteArray result = homebrew_json(env, owned);
    if (result != NULL && !(*env)->ExceptionCheck(env)) {
        const jlong token = (jlong)opened_token;
        (*env)->SetLongArrayRegion(env, opening_token, 0, 1, &token);
    }
    if (result == NULL || (*env)->ExceptionCheck(env)) {
        if (opened_token != 0) droidds_homebrew_close(opened_token);
        /* CodexAstraUlt: Revoke even a partially transferred token without
         * replacing the original allocation/copy exception with cleanup work. */
        jthrowable pending = (*env)->ExceptionOccurred(env);
        if (pending != NULL) (*env)->ExceptionClear(env);
        (*env)->SetLongArrayRegion(env, opening_token, 0, 1, &zero);
        if (pending != NULL) {
            if ((*env)->ExceptionCheck(env)) (*env)->ExceptionClear(env);
            (*env)->Throw(env, pending);
            (*env)->DeleteLocalRef(env, pending);
        }
        return NULL;
    }
    return result;
}

/* CodexAstraUlt: Explicit RGBA-byte to ARGB-integer conversion avoids relying
 * on the native byte order of Android's Bitmap storage. This does not draw. */
static void pack_argb(jint *pixels, size_t count) {
    uint8_t *bytes = (uint8_t *)pixels;
    for (size_t i = 0; i < count; ++i) {
        const size_t p = i * 4U;
        const uint32_t value = ((uint32_t)bytes[p + 3U] << 24U)
            | ((uint32_t)bytes[p] << 16U) | ((uint32_t)bytes[p + 1U] << 8U)
            | (uint32_t)bytes[p + 2U];
        pixels[i] = (jint)value;
    }
}

JNIEXPORT jint JNICALL
Java_org_droidds_probe_HomebrewController_nativeFrame(JNIEnv *env, jclass owner,
    jlong token, jint buttons, jint x, jint y, jboolean touched,
    jintArray top, jintArray bottom, jshortArray audio, jlongArray values) {
    (void)owner;
    if (token <= 0 || top == NULL || bottom == NULL || audio == NULL || values == NULL
            || (*env)->GetArrayLength(env, top) != 400 * 240
            || (*env)->GetArrayLength(env, bottom) != 320 * 240
            || (*env)->GetArrayLength(env, audio) != (jsize)(DDS_HOMEBREW_PCM_FRAMES * 2U)
            || (*env)->GetArrayLength(env, values) != (jsize)DDS_HOMEBREW_METRICS
            || ((uint32_t)buttons & ~0xCFFFU) != 0U
            || (touched && (x < 0 || x >= 320 || y < 0 || y >= 240))) {
        homebrew_error(env, "Invalid interactive frame token, input or buffer capacity");
        return -1;
    }
    DdsHomebrewMetrics metrics = {0};
    const int32_t result = droidds_homebrew_frame((uint64_t)token, (uint32_t)buttons,
        x, y, touched ? 1U : 0U, (uint8_t *)top_pixels, sizeof(top_pixels),
        (uint8_t *)bottom_pixels, sizeof(bottom_pixels), pcm_samples,
        DDS_HOMEBREW_PCM_FRAMES * 2U, &metrics);
    if (result == -2) return -2;
    if (result != 0 || metrics.pcm_frames > DDS_HOMEBREW_PCM_FRAMES
            || metrics.frame_index > INT64_MAX || metrics.guest_serial > UINT32_MAX
            || metrics.exited > 1U) {
        homebrew_error(env, "Interactive guest step failed or returned invalid frame metrics");
        return -1;
    }
    pack_argb(top_pixels, 400U * 240U);
    pack_argb(bottom_pixels, 320U * 240U);
    (*env)->SetIntArrayRegion(env, top, 0, 400 * 240, top_pixels);
    if ((*env)->ExceptionCheck(env)) return -1;
    (*env)->SetIntArrayRegion(env, bottom, 0, 320 * 240, bottom_pixels);
    if ((*env)->ExceptionCheck(env)) return -1;
    (*env)->SetShortArrayRegion(env, audio, 0, (jsize)(metrics.pcm_frames * 2U), pcm_samples);
    if ((*env)->ExceptionCheck(env)) return -1;
    const jlong measured[DDS_HOMEBREW_METRICS] = {(jlong)metrics.frame_index,
        (jlong)metrics.guest_serial, (jlong)metrics.pcm_frames, (jlong)metrics.exited};
    (*env)->SetLongArrayRegion(env, values, 0, (jsize)DDS_HOMEBREW_METRICS, measured);
    return 0;
}

JNIEXPORT void JNICALL
Java_org_droidds_probe_HomebrewController_nativePause(JNIEnv *env, jclass owner,
                                                     jlong token, jboolean paused) {
    (void)owner;
    if (token <= 0 || droidds_homebrew_pause((uint64_t)token, paused ? 1U : 0U) != 0) {
        homebrew_error(env, "Interactive session pause or resume failed");
    }
}

JNIEXPORT jbyteArray JNICALL
Java_org_droidds_probe_HomebrewController_nativeReport(JNIEnv *env, jclass owner, jlong token) {
    (void)owner;
    if (token <= 0) {
        homebrew_error(env, "Interactive session token is invalid");
        return NULL;
    }
    return homebrew_json(env, droidds_homebrew_report((uint64_t)token));
}

JNIEXPORT void JNICALL
Java_org_droidds_probe_HomebrewController_nativeClose(JNIEnv *env, jclass owner, jlong token) {
    (void)env;
    (void)owner;
    if (token > 0) droidds_homebrew_close((uint64_t)token);
}
