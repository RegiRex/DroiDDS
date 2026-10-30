/* CodexAstraUlt: The title JNI bridge only transports bounded input, output and
 * ownership. Guest loading, execution and diagnostics belong to the runtime. */
#include <jni.h>
#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "title_api.h"

/* CodexAstraUlt: Per-worker fixed buffers avoid per-slice native allocations and
 * shared mutable pixels. The Rust session itself remains owned by this thread. */
static _Thread_local jint top_pixels[400U * 240U];
static _Thread_local jint bottom_pixels[320U * 240U];
static _Thread_local int16_t pcm_samples[DDS_TITLE_PCM_FRAMES * 2U];

static void title_error(JNIEnv *env, const char *message) {
    if ((*env)->ExceptionCheck(env)) return;
    jclass type = (*env)->FindClass(env, "java/lang/IllegalStateException");
    if (type != NULL) {
        (*env)->ThrowNew(env, type, message);
        (*env)->DeleteLocalRef(env, type);
    }
}

/* CodexAstraUlt: Copy ordinary UTF-8 JSON as bytes, never modified-UTF strings;
 * the Rust allocation is released even when Java allocation or copying fails. */
static jbyteArray title_json(JNIEnv *env, char *owned) {
    const size_t limit = 256U * 1024U;
    if (owned == NULL) {
        title_error(env, "Title runtime returned no report");
        return NULL;
    }
    const size_t length = strnlen(owned, limit + 1U);
    if (length == 0U || length > limit) {
        droidds_title_free(owned);
        title_error(env, "Title runtime report exceeds its bound");
        return NULL;
    }
    jbyteArray result = (*env)->NewByteArray(env, (jsize)length);
    if (result != NULL) {
        (*env)->SetByteArrayRegion(env, result, 0, (jsize)length, (const jbyte *)owned);
    }
    droidds_title_free(owned);
    return result;
}

JNIEXPORT jbyteArray JNICALL
Java_org_droidds_probe_TitleNative_open(JNIEnv *env, jclass owner,
    jbyteArray manifest, jstring input, jstring libraries, jstring runtime,
    jboolean native_mode, jlongArray opening_token) {
    (void)owner;
    if (opening_token == NULL || (*env)->GetArrayLength(env, opening_token) != 1) {
        title_error(env, "Title open requires a token output");
        return NULL;
    }
    const jlong zero = 0;
    (*env)->SetLongArrayRegion(env, opening_token, 0, 1, &zero);
    if ((*env)->ExceptionCheck(env)) return NULL;
    if (manifest == NULL || input == NULL || libraries == NULL || runtime == NULL) {
        title_error(env, "Title manifest and runtime paths are required");
        return NULL;
    }
    const jsize length = (*env)->GetArrayLength(env, manifest);
    if (length <= 0 || (uint32_t)length > DDS_TITLE_MANIFEST_BYTES) {
        title_error(env, "Title manifest exceeds its bound");
        return NULL;
    }
    /* CodexAstraUlt: Admission can hash a large input. Copy this bounded asset
     * before calling Rust instead of pinning a Java array through that work. */
    uint8_t *manifest_copy = malloc((size_t)length);
    if (manifest_copy == NULL) {
        title_error(env, "Cannot allocate title manifest transfer");
        return NULL;
    }
    (*env)->GetByteArrayRegion(env, manifest, 0, length, (jbyte *)manifest_copy);
    if ((*env)->ExceptionCheck(env)) { free(manifest_copy); return NULL; }
    const char *input_path = (*env)->GetStringUTFChars(env, input, NULL);
    if (input_path == NULL) { free(manifest_copy); return NULL; }
    const char *library_path = (*env)->GetStringUTFChars(env, libraries, NULL);
    if (library_path == NULL) {
        (*env)->ReleaseStringUTFChars(env, input, input_path);
        free(manifest_copy);
        return NULL;
    }
    const char *runtime_path = (*env)->GetStringUTFChars(env, runtime, NULL);
    if (runtime_path == NULL) {
        (*env)->ReleaseStringUTFChars(env, libraries, library_path);
        (*env)->ReleaseStringUTFChars(env, input, input_path);
        free(manifest_copy);
        return NULL;
    }
    /* CodexAstraUlt: Hardware rendering is an explicit Android requirement;
     * interpreter selection changes only the CPU route, not Vulkan admission. */
    uint64_t opened_token = 0;
    char *owned = droidds_title_open(manifest_copy, (size_t)length, input_path,
        library_path, runtime_path, native_mode ? 1U : 0U, 1U, &opened_token);
    (*env)->ReleaseStringUTFChars(env, runtime, runtime_path);
    (*env)->ReleaseStringUTFChars(env, libraries, library_path);
    (*env)->ReleaseStringUTFChars(env, input, input_path);
    free(manifest_copy);
    jbyteArray result = title_json(env, owned);
    if (result != NULL && !(*env)->ExceptionCheck(env)) {
        const jlong token = (jlong)opened_token;
        (*env)->SetLongArrayRegion(env, opening_token, 0, 1, &token);
    }
    /* CodexAstraUlt: JNI owns a new session until both outputs transfer. Revoke
     * a partially written token while retaining the original Java exception. */
    if (result == NULL || (*env)->ExceptionCheck(env)) {
        if (opened_token != 0) (void)droidds_title_close(opened_token);
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

/* CodexAstraUlt: Byte-order-independent RGBA to Android ARGB conversion does
 * not render guest pixels or alter buffers without a ready flag. */
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
Java_org_droidds_probe_TitleNative_slice(JNIEnv *env, jclass owner,
    jlong token, jint buttons, jfloat circle_x, jfloat circle_y,
    jfloat c_stick_x, jfloat c_stick_y, jint x, jint y, jboolean touched,
    jintArray top, jintArray bottom, jshortArray audio, jlongArray values) {
    (void)owner;
    if (token <= 0 || top == NULL || bottom == NULL || audio == NULL || values == NULL
            || (*env)->GetArrayLength(env, top) != 400 * 240
            || (*env)->GetArrayLength(env, bottom) != 320 * 240
            || (*env)->GetArrayLength(env, audio) != (jsize)(DDS_TITLE_PCM_FRAMES * 2U)
            || (*env)->GetArrayLength(env, values) != (jsize)DDS_TITLE_METRICS
            || ((uint32_t)buttons & ~0xFF00CFFFU) != 0U
            || !isfinite(circle_x) || !isfinite(circle_y) || !isfinite(c_stick_x) || !isfinite(c_stick_y)
            || fabsf(circle_x) > 1.0f || fabsf(circle_y) > 1.0f
            || fabsf(c_stick_x) > 1.0f || fabsf(c_stick_y) > 1.0f
            || (touched && (x < 0 || x >= 320 || y < 0 || y >= 240))) {
        title_error(env, "Invalid title token, input or buffer capacity");
        return -1;
    }
    DdsTitleMetrics metrics = {0};
    const int32_t result = droidds_title_slice((uint64_t)token, (uint32_t)buttons,
        circle_x, circle_y, c_stick_x, c_stick_y, x, y, touched ? 1U : 0U,
        (uint8_t *)top_pixels, sizeof(top_pixels), (uint8_t *)bottom_pixels,
        sizeof(bottom_pixels), pcm_samples, DDS_TITLE_PCM_FRAMES * 2U, &metrics);
    if (result == -2) return -2;
    if (result != 0 || metrics.frames > INT64_MAX || metrics.cycles > INT64_MAX
            || metrics.pcm_frames > DDS_TITLE_PCM_FRAMES || metrics.exited > 1U
            || metrics.ready_mask > (DDS_TITLE_READY_TOP | DDS_TITLE_READY_BOTTOM)) {
        title_error(env, "Title slice failed or returned invalid metrics");
        return -1;
    }
    if ((metrics.ready_mask & DDS_TITLE_READY_TOP) != 0U) {
        pack_argb(top_pixels, 400U * 240U);
        (*env)->SetIntArrayRegion(env, top, 0, 400 * 240, top_pixels);
        if ((*env)->ExceptionCheck(env)) return -1;
    }
    if ((metrics.ready_mask & DDS_TITLE_READY_BOTTOM) != 0U) {
        pack_argb(bottom_pixels, 320U * 240U);
        (*env)->SetIntArrayRegion(env, bottom, 0, 320 * 240, bottom_pixels);
        if ((*env)->ExceptionCheck(env)) return -1;
    }
    (*env)->SetShortArrayRegion(env, audio, 0, (jsize)(metrics.pcm_frames * 2U), pcm_samples);
    if ((*env)->ExceptionCheck(env)) return -1;
    const jlong measured[DDS_TITLE_METRICS] = {(jlong)metrics.frames,
        (jlong)metrics.cycles, (jlong)metrics.pcm_frames, (jlong)metrics.exited,
        (jlong)metrics.ready_mask};
    (*env)->SetLongArrayRegion(env, values, 0, (jsize)DDS_TITLE_METRICS, measured);
    return (*env)->ExceptionCheck(env) ? -1 : 0;
}

JNIEXPORT void JNICALL
Java_org_droidds_probe_TitleNative_pause(JNIEnv *env, jclass owner, jlong token, jboolean paused) {
    (void)owner;
    if (token <= 0 || (paused ? droidds_title_pause((uint64_t)token)
                              : droidds_title_resume((uint64_t)token)) != 0) {
        title_error(env, "Title pause or resume failed");
    }
}

JNIEXPORT jbyteArray JNICALL
Java_org_droidds_probe_TitleNative_report(JNIEnv *env, jclass owner, jlong token) {
    (void)owner;
    if (token <= 0) {
        title_error(env, "Title token is invalid");
        return NULL;
    }
    return title_json(env, droidds_title_report((uint64_t)token));
}

JNIEXPORT void JNICALL
Java_org_droidds_probe_TitleNative_close(JNIEnv *env, jclass owner, jlong token) {
    (void)owner;
    if (token > 0 && droidds_title_close((uint64_t)token) != 0) {
        title_error(env, "Title close used a stale token or wrong worker");
    }
}
