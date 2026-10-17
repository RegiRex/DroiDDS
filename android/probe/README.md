# Android CPU loader probe shell

<!-- CodexAstraUlt: Define the original Java/JNI boundary and evidence protocol
without treating a packaged APK as device execution or game compatibility. -->

This small platform-only Android shell runs DroidDS's original synthetic CPU
fixtures through packaged native libraries. It contains no renderer, title
loader, networking, external storage access or Google/vendor service dependency.
The application is deliberately debuggable and test-only so a local `adb` runner
can extract its one private result. It is not a consumer emulator release.

| Setting | Value |
| --- | --- |
| Application ID | `org.droidds.probe` |
| Launch component | `org.droidds.probe/.ProbeActivity` |
| Version | `0.0.2` / version code `2` |
| Android minimum / target | API 29 / 35 |
| Initial packaged ABI | `arm64-v8a` |
| Result | `files/latest-probe.json`, inside private app storage |

## Native interface

<!-- CodexAstraUlt: Standard installed-library extraction keeps native loading
inside Android's package paths instead of executing downloaded writable files. -->

The manifest explicitly enables native-library extraction. Java loads
`libdroidds_probe_jni.so` using `System.loadLibrary` and passes the installed
`ApplicationInfo.nativeLibraryDir` to its synchronous native method:

```java
private static native byte[] nativeRun(String libraryDirectory);
```

The JNI symbol is
`Java_org_droidds_probe_ProbeController_nativeRun`. Its bridge links
`libdroidds_android_probe.so` and calls:

```c
char *droidds_probe_run(const char *library_directory);
void droidds_probe_free(char *report);
```

Rust owns its returned, NUL-terminated UTF-8 JSON allocation. JNI copies at most
1 MiB into a Java byte array and releases every non-null returned allocation using
the matching Rust function, including invalid-size and allocation-failure paths.
JNI does not pass JSON through modified-UTF-8 `NewStringUTF`. Java rejects invalid
UTF-8 and requires an object with exact terminal `status` of `passed` or `failed`.
The Rust loader resolves `libdds_fixture_<fixture_name>.so` in the provided
installer-owned directory. The shell does not scan or accept external libraries.

## Run ownership and report protocol

<!-- CodexAstraUlt: Process ownership plus unique request IDs prevents duplicate
Activity runs and stale evidence without a continuous monitor or per-run bundles. -->

One process-scoped worker executes all native calls and file writes off the main
thread. Activity recreation/backgrounding observes the existing run through a weak
observer; it does not launch another run. The first launch starts one run, and the
button permits an explicit sequential rerun. A new process starts a new run.

An automation caller supplies a unique `request_id` String launch extra after
force-stopping the existing probe process. The shell echoes the exact token under
`android_shell.request_id`. A normal launcher invocation uses a generated UUID.
The runner must match its request token, the installed APK identity and all required
native fixture evidence; a passing status alone is not a complete qualification.

The native JSON remains at the report's top level. The shell adds:

```json
{
  "android_shell": {
    "schema_version": 1,
    "request_id": "unique-caller-token",
    "run_id": "generated-uuid",
    "started_at_epoch_ms": 0,
    "finished_at_epoch_ms": 0,
    "process_id": 0,
    "app_version_name": "0.0.2",
    "app_version_code": 2
  }
}
```

Times are integer Unix epoch milliseconds. `finished_at_epoch_ms` appears only in
terminal reports. Before any native library loading, the shell atomically replaces
the previous report with `status: "running"` and the current shell metadata.
Ordinary Java, loader, UTF-8 and JSON failures produce `status: "failed"` with an
`error` object containing `type` and bounded `message`. A failure to save is shown
as a failure, and obsolete result files are removed. Atomic writes are read back
and compared byte-for-byte before the UI can display success. Only one latest
report is retained, plus Android AtomicFile's transient replacement/recovery files.

A fatal native crash, process kill, allocation failure or hang may leave a running
marker or no completed report. Those outcomes are incomplete and cannot pass. The
external device runner owns the wall-clock deadline and can stop this diagnostic
process; the app does not attempt unsafe termination of a native worker thread.

## Validation scope

<!-- CodexAstraUlt: Static shell compilation is useful evidence but does not
claim Android lifecycle, Bionic loading or CPU execution passed on hardware. -->

The Java sources compile against SDK 35 using Java 8 language/API compatibility
and strict warnings. The bridge compiles with NDK 27.3.13750724 for AArch64/API 29
with `-std=c11 -Wall -Wextra -Werror`. These checks do not exercise Android
lifecycle, loading or fixture execution on a Thor. The repository's build and
device runners record those separate outcomes.
