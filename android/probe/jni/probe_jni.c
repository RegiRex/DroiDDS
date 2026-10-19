/* CodexAstraUlt: JNI marshals the installed library directory and bounded UTF-8
 * reports. Rust owns CPU execution; the separate C Vulkan helper owns its draw. */
#include <jni.h>
#include <stddef.h>
#include <stdlib.h>

#include "vulkan_probe.h"
#include <string.h>

extern char *droidds_probe_run(const char *library_directory);
extern void droidds_probe_free(char *report);
/* CodexAstraUlt: The runtime uses the same owning Rust allocator/free contract. */
extern char *droidds_runtime_run(const char *library_directory, const char *scratch_directory);

/* CodexAstraUlt: Error messages here are ASCII; report text is returned as bytes,
 * never passed through JNI's incompatible modified-UTF-8 NewStringUTF API. */
static void throw_state(JNIEnv *env, const char *message) {
    jclass error_class = (*env)->FindClass(env, "java/lang/IllegalStateException");
    if (error_class != NULL) {
        (*env)->ThrowNew(env, error_class, message);
        (*env)->DeleteLocalRef(env, error_class);
    }
}

/* CodexAstraUlt: Centralize bounded UTF-8 copying and matching Rust release for
 * both CPU and runtime results, including all JNI allocation failures. */
static jbyteArray copy_owned_report(JNIEnv *env, char *report, size_t report_limit) {
    if (report == NULL) {
        throw_state(env, "Native probe returned no report");
        return NULL;
    }

    /* CodexAstraUlt: Match every non-null Rust allocation with its Rust release,
     * including invalid reports or JNI allocation failures. Bound persisted evidence. */
    const size_t report_length = strnlen(report, report_limit + 1U);
    if (report_length == 0U || report_length > report_limit) {
        droidds_probe_free(report);
        throw_state(env, "Native probe report is empty or exceeds its byte limit");
        return NULL;
    }
    jbyteArray result = (*env)->NewByteArray(env, (jsize)report_length);
    if (result != NULL) {
        (*env)->SetByteArrayRegion(env, result, 0, (jsize)report_length,
                                  (const jbyte *)report);
    }
    droidds_probe_free(report);
    return result;
}

JNIEXPORT jbyteArray JNICALL
Java_org_droidds_probe_ProbeController_nativeRun(JNIEnv *env, jclass controller,
                                                jstring library_directory) {
    (void)controller;
    if (library_directory == NULL) {
        throw_state(env, "Android did not provide its native library directory");
        return NULL;
    }

    /* CodexAstraUlt: Android's installer owns this ASCII package-library path.
     * Release its JNI borrow immediately after the synchronous Rust call. */
    const char *directory = (*env)->GetStringUTFChars(env, library_directory, NULL);
    if (directory == NULL) {
        return NULL;
    }
    char *report = droidds_probe_run(directory);
    (*env)->ReleaseStringUTFChars(env, library_directory, directory);
    return copy_owned_report(env, report, 1024U * 1024U);
}

/* CodexAstraUlt: Keep Vulkan discovery/drawing on the same Java worker. Its C
 * helper writes only into this bounded allocation; JNI owns and frees that
 * allocation on every exit, including pending Java allocation/copy exceptions. */
JNIEXPORT jbyteArray JNICALL
Java_org_droidds_probe_ProbeController_nativeVulkan(JNIEnv *env, jclass controller) {
    (void)controller;
    const size_t report_limit = 64U * 1024U;
    char *report = malloc(report_limit);
    if (report == NULL) {
        throw_state(env, "Could not allocate the Vulkan report buffer");
        return NULL;
    }
    const int length = dds_vk_probe_run(report, report_limit);
    if (length <= 0 || (size_t)length > report_limit) {
        free(report);
        throw_state(env, "Vulkan report is empty or exceeds 64 KiB");
        return NULL;
    }
    jbyteArray result = (*env)->NewByteArray(env, (jsize)length);
    if (result != NULL) {
        /* CodexAstraUlt: JSON is ordinary UTF-8, never JNI modified UTF-8. */
        (*env)->SetByteArrayRegion(env, result, 0, (jsize)length,
                                  (const jbyte *)report);
    }
    free(report);
    return result;
}

/* CodexAstraUlt: Use a dedicated app-private scratch path for original fixture
 * files. Both borrowed paths are released before copying the owned JSON result. */
JNIEXPORT jbyteArray JNICALL
Java_org_droidds_probe_ProbeController_nativeRuntime(JNIEnv *env, jclass controller,
                                                    jstring library_directory,
                                                    jstring scratch_directory) {
    (void)controller;
    if (library_directory == NULL || scratch_directory == NULL) {
        throw_state(env, "Android did not provide runtime paths");
        return NULL;
    }
    const char *libraries = (*env)->GetStringUTFChars(env, library_directory, NULL);
    if (libraries == NULL) return NULL;
    const char *scratch = (*env)->GetStringUTFChars(env, scratch_directory, NULL);
    if (scratch == NULL) {
        (*env)->ReleaseStringUTFChars(env, library_directory, libraries);
        return NULL;
    }
    char *report = droidds_runtime_run(libraries, scratch);
    (*env)->ReleaseStringUTFChars(env, scratch_directory, scratch);
    (*env)->ReleaseStringUTFChars(env, library_directory, libraries);
    return copy_owned_report(env, report, 256U * 1024U);
}
