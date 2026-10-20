package org.droidds.probe;

import android.content.Context;
import android.content.pm.PackageInfo;
import android.net.Uri;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.os.Process;
import android.os.SystemClock;
import android.util.AtomicFile;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.lang.ref.WeakReference;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** CodexAstraUlt: One process-scoped worker serializes native runs and report IO.
 * It owns only application context and a weak UI observer, so backgrounding or
 * recreation cannot leak Activities or duplicate a run. Native hangs still need
 * the device runner's deadline; Java cannot safely terminate a native thread. */
final class ProbeController {
    interface Observer {
        void onProbeChanged(Snapshot snapshot);
    }

    // CodexAstraUlt: Immutable UI snapshots never expose the private report bytes.
    // The display is capped separately from the bounded, verified persisted JSON.
    static final class Snapshot {
        final boolean running;
        final String status;
        final String details;
        final boolean canExport;
        final String exportStatus;
        final boolean canHomebrew;

        Snapshot(boolean running, String status, String details) {
            this(running, status, details, false, "");
        }

        Snapshot(boolean running, String status, String details,
                 boolean canExport, String exportStatus) {
            this.running = running;
            this.status = status;
            this.details = details.length() <= 32768
                    ? details : details.substring(0, 32768) + "\n[Display truncated]";
            this.canExport = canExport;
            this.exportStatus = exportStatus;
            this.canHomebrew = !running && canExport;
        }
    }

    private static final int CPU_REPORT_LIMIT = 1024 * 1024;
    private static final int GRAPHICS_REPORT_LIMIT = 64 * 1024;
    // CodexAstraUlt: Bound the independent full-runtime evidence without changing
    // the one-file report policy or allowing arbitrary native output growth.
    private static final int RUNTIME_REPORT_LIMIT = 256 * 1024;
    // CodexAstraUlt: Automatic homebrew and manual observations remain separate,
    // bounded sections in the existing one-file report, never new log bundles.
    static final int HOMEBREW_REPORT_LIMIT = 256 * 1024;
    private static final int REPORT_LIMIT = CPU_REPORT_LIMIT + GRAPHICS_REPORT_LIMIT
            + RUNTIME_REPORT_LIMIT + 2 * HOMEBREW_REPORT_LIMIT + 16384;
    private static ProbeController instance;
    private final Context application;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final ExecutorService worker = Executors.newSingleThreadExecutor(runnable -> {
        Thread thread = new Thread(runnable, "droidds-probe");
        thread.setPriority(Thread.NORM_PRIORITY);
        return thread;
    });
    private WeakReference<Observer> observer = new WeakReference<>(null);
    private Snapshot snapshot = new Snapshot(false, "Ready", "");
    private boolean started;
    private boolean active;
    private String currentRunId;
    private String homebrewToken;
    private byte[] homebrewBase;
    private byte[] homebrewRunningReport;

    // CodexAstraUlt: These immutable byte arrays are the exact successfully
    // persisted content, not freshly serialized UI text. A picker pins one run;
    // a subsequent run cannot change what that selection would write.
    private byte[] latestReport;
    private byte[] selectedReport;
    private String exportToken;
    private boolean exportWriting;
    private String exportMessage = "";

    private ProbeController(Context application) {
        this.application = application;
    }

    static synchronized ProbeController get(Context context) {
        if (instance == null) {
            instance = new ProbeController(context.getApplicationContext());
        }
        return instance;
    }

    // CodexAstraUlt: These entry points and state are main-thread-only. Once the
    // process has launched a run, Activity recreation cannot launch it again.
    void startOnce(String requestId) {
        requireMainThread();
        if (!started) {
            started = true;
            start(requestId);
        }
    }

    void runAgain() {
        requireMainThread();
        // CodexAstraUlt: A lost/cancelled picker must not trap the core probe.
        // Invalidate its token before rerunning, so a late result cannot silently
        // export another run. A write already queued retains its selected bytes.
        if (!active && exportToken != null && !exportWriting) {
            cancelExport(exportToken, "Previous save cancelled by the new run.");
        }
        start(null);
    }

    void observe(Observer target) {
        requireMainThread();
        observer = new WeakReference<>(target);
        target.onProbeChanged(snapshot);
    }

    void removeObserver(Observer target) {
        requireMainThread();
        if (observer.get() == target) {
            observer.clear();
        }
    }

    // CodexAstraUlt: Reserve the latest completed run before opening a manual
    // session. Export/rerun cannot overlap; Activity rotation keeps this token.
    String beginHomebrew() {
        requireMainThread();
        if (active || latestReport == null || exportToken != null || currentRunId == null) {
            return null;
        }
        final String token = UUID.randomUUID().toString();
        final String runId = currentRunId;
        final byte[] base = latestReport;
        homebrewToken = token;
        homebrewBase = base;
        homebrewRunningReport = null;
        active = true;
        latestReport = null;
        HomebrewController.get(application).reserve(token);
        publish(new Snapshot(true, "Preparing original homebrew", snapshot.details));
        worker.execute(() -> {
            try {
                JSONObject report = parseReport(base, REPORT_LIMIT);
                JSONObject pending = new JSONObject();
                pending.put("schema", 1);
                pending.put("kind", "droidds-android-interactive-session");
                pending.put("status", "running");
                pending.put("session_id", token);
                pending.put("bound_run_id", runId);
                report.put("interactive_session", pending);
                byte[] written = persist(new AtomicFile(new File(application.getFilesDir(),
                        "latest-probe.json")), report);
                main.post(() -> {
                    if (token.equals(homebrewToken) && runId.equals(currentRunId)) {
                        homebrewRunningReport = written;
                        HomebrewController.get(application).startPrepared(token);
                    }
                });
            } catch (Exception failure) {
                main.post(() -> {
                    if (token.equals(homebrewToken) && runId.equals(currentRunId)) {
                        homebrewToken = null;
                        homebrewBase = null;
                        active = false;
                        latestReport = base;
                        HomebrewController.get(application).preparationFailed(token);
                        publish(new Snapshot(false, "Could not save the session marker. Try again.",
                                snapshot.details));
                    }
                });
            }
        });
        return token;
    }

    // CodexAstraUlt: Only this controller merges manual results into its captured
    // automated report. A stale session never supplies or replaces the base/run ID.
    void finishHomebrew(String token, byte[] nativeResult, JSONObject observations,
                        String outcome, Runnable saved) {
        requireMainThread();
        if (!token.equals(homebrewToken) || homebrewBase == null) return;
        final byte[] base = homebrewBase;
        final String runId = currentRunId;
        final byte[] fallback = homebrewRunningReport;
        worker.execute(() -> {
            byte[] persisted;
            Snapshot result;
            try {
                JSONObject report = parseReport(base, REPORT_LIMIT);
                JSONObject manual = new JSONObject();
                manual.put("schema", 1);
                manual.put("kind", "droidds-android-interactive-session");
                manual.put("status", outcome);
                manual.put("session_id", token);
                manual.put("bound_run_id", runId);
                try {
                    manual.put("native", parseReport(nativeResult, HOMEBREW_REPORT_LIMIT));
                } catch (Exception invalid) {
                    manual.put("status", "failed");
                    manual.put("native", new JSONObject().put("status", "failed")
                            .put("error", "Manual native report was missing or invalid"));
                }
                manual.put("android", observations);
                if (manual.toString().getBytes(StandardCharsets.UTF_8).length > HOMEBREW_REPORT_LIMIT) {
                    throw new IOException("Manual session evidence exceeds its bound");
                }
                report.put("interactive_session", manual);
                // CodexAstraUlt: Overall status continues to describe automated
                // checks. Manual observations cannot turn a failure into a pass.
                persisted = persist(new AtomicFile(new File(application.getFilesDir(),
                        "latest-probe.json")), report);
                result = new Snapshot(false, "Automated checks: " + report.optString("status")
                        + ". Manual session: " + manual.optString("status")
                        + ". Qualification pending review. Save report to share it.",
                        report.toString(2));
            } catch (Exception failed) {
                persisted = fallback;
                result = new Snapshot(false, "Session save failed; retained report is incomplete.",
                        "Automated results were retained. Repeat the homebrew test before qualification.");
            }
            final byte[] written = persisted;
            final Snapshot terminal = result;
            main.post(() -> {
                if (!token.equals(homebrewToken) || !runId.equals(currentRunId)) return;
                homebrewToken = null;
                homebrewBase = null;
                homebrewRunningReport = null;
                active = false;
                latestReport = written;
                publish(terminal);
                saved.run();
            });
        });
    }

    // CodexAstraUlt: Preparing the document picker performs no IO and copies no
    // large buffer on the UI thread. Ownership stays in this process controller.
    String beginExport() {
        requireMainThread();
        if (active || latestReport == null || exportToken != null) {
            return null;
        }
        selectedReport = latestReport;
        exportToken = UUID.randomUUID().toString();
        exportMessage = "Choose where to save this completed report.";
        publish(snapshot);
        return exportToken;
    }

    void cancelExport(String token, String message) {
        requireMainThread();
        if (token != null && token.equals(exportToken) && !exportWriting) {
            selectedReport = null;
            exportToken = null;
            exportMessage = message;
            publish(snapshot);
        }
    }

    void finishExport(String token, Uri destination) {
        requireMainThread();
        if (token == null || !token.equals(exportToken) || selectedReport == null) {
            exportMessage = "That report selection expired. Use Save report again.";
            publish(snapshot);
            return;
        }
        if (exportWriting) {
            return;
        }
        if (destination == null) {
            cancelExport(token, "Save cancelled.");
            return;
        }
        final byte[] bytes = selectedReport;
        exportWriting = true;
        exportMessage = "Saving report…";
        publish(snapshot);
        worker.execute(() -> {
            String outcome;
            // CodexAstraUlt: Android grants access only to the document the user
            // selected. No broad storage access, persistent URI grant, Activity
            // reference or secondary executor is needed for this bounded write.
            try (OutputStream output = application.getContentResolver()
                    .openOutputStream(destination, "wt")) {
                if (output == null) {
                    throw new IOException("The document provider returned no output stream");
                }
                if (bytes.length == 0 || bytes.length > REPORT_LIMIT) {
                    throw new IOException("The selected report exceeds its size bound");
                }
                output.write(bytes);
                output.flush();
                outcome = "Report saved to the selected document.";
            } catch (Exception failure) {
                outcome = "Could not save the report: " + failure.getClass().getSimpleName()
                        + ". You can retry Save report; probe results are retained.";
            }
            final String result = outcome;
            main.post(() -> {
                if (token.equals(exportToken)) {
                    selectedReport = null;
                    exportToken = null;
                    exportWriting = false;
                    exportMessage = result;
                    publish(snapshot);
                }
            });
        });
    }

    private void start(String requestedId) {
        if (active) {
            return;
        }
        active = true;
        latestReport = null;
        if (exportToken == null) {
            exportMessage = "";
        }
        String runId = UUID.randomUUID().toString();
        currentRunId = runId;
        String requestId = requestedId == null || requestedId.isEmpty() ? runId : requestedId;
        long startedAt = System.currentTimeMillis();
        long startedElapsed = SystemClock.elapsedRealtime();
        publish(new Snapshot(true, "Running CPU and Vulkan probes", "Run: " + runId));
        worker.execute(() -> execute(runId, requestId, startedAt, startedElapsed));
    }

    private void execute(String runId, String requestId, long startedAt, long startedElapsed) {
        AtomicFile reportFile = new AtomicFile(new File(application.getFilesDir(), "latest-probe.json"));
        JSONObject shell = new JSONObject();
        try {
            shell.put("schema_version", 1);
            shell.put("run_id", runId);
            shell.put("request_id", requestId);
            shell.put("started_at_epoch_ms", startedAt);
            shell.put("process_id", Process.myPid());
            PackageInfo packageInfo = application.getPackageManager()
                    .getPackageInfo(application.getPackageName(), 0);
            shell.put("app_version_name", packageInfo.versionName);
            shell.put("app_version_code", packageInfo.getLongVersionCode());
            // CodexAstraUlt: Record model/OS context, never a hardware serial or
            // advertising identifier. Monotonic duration covers the whole probe;
            // it is not a CPU benchmark or an estimate of game performance.
            shell.put("manufacturer", bounded(Build.MANUFACTURER, 256));
            shell.put("model", bounded(Build.MODEL, 256));
            shell.put("android_api", Build.VERSION.SDK_INT);
            shell.put("android_release", bounded(Build.VERSION.RELEASE, 256));

            // CodexAstraUlt: Replace any old passing report BEFORE entering
            // native code. An abort/hang leaves a running marker, never success.
            JSONObject running = new JSONObject();
            running.put("status", "running");
            running.put("android_shell", shell);
            try {
                persist(reportFile, running);
            } catch (IOException failure) {
                reportFile.delete();
                throw failure;
            }

            System.loadLibrary("droidds_probe_jni");
            byte[] result = nativeRun(application.getApplicationInfo().nativeLibraryDir);
            JSONObject report = parseReport(result, CPU_REPORT_LIMIT);
            Object cpuStatus = report.opt("status");
            if (!(cpuStatus instanceof String)
                    || !("passed".equals(cpuStatus) || "failed".equals(cpuStatus))) {
                throw new IOException("CPU report has no valid terminal status");
            }
            // CodexAstraUlt: Preserve the existing CPU evidence and explicitly
            // qualify graphics separately. Missing Vulkan cannot become a pass;
            // this synthetic draw is not a PICA renderer or a game execution.
            report.put("cpu_status", cpuStatus);
            JSONObject graphics;
            try {
                graphics = parseReport(nativeVulkan(), GRAPHICS_REPORT_LIMIT);
                Object graphicsStatus = graphics.opt("status");
                if (!(graphicsStatus instanceof String)
                        || !("passed".equals(graphicsStatus) || "failed".equals(graphicsStatus)
                        || "unavailable".equals(graphicsStatus))) {
                    throw new IOException("Vulkan report has no valid terminal status");
                }
            } catch (Exception | LinkageError failure) {
                graphics = new JSONObject();
                graphics.put("status", "failed");
                graphics.put("error", errorDetails(failure));
            }
            report.put("graphics_probe", graphics);
            // CodexAstraUlt: Preserve completed stages in the same atomic report
            // before the larger runtime call. Native process death leaves useful
            // partial evidence with a running status, never a stale success.
            report.put("status", "running");
            report.put("android_shell", shell);
            JSONObject runtimeRunning = new JSONObject();
            runtimeRunning.put("status", "running");
            report.put("runtime_probe", runtimeRunning);
            persist(reportFile, report);
            // CodexAstraUlt: The real loader/service/PICA fixture has its own
            // result. Preserve prior CPU/GPU evidence even if its Java/native
            // boundary fails; only the dedicated cache subdirectory is passed.
            JSONObject runtime;
            try {
                File scratch = new File(application.getCacheDir(), "runtime-probe");
                runtime = parseReport(nativeRuntime(application.getApplicationInfo().nativeLibraryDir,
                        scratch.getAbsolutePath()), RUNTIME_REPORT_LIMIT);
                Object runtimeStatus = runtime.opt("status");
                if (!(runtimeStatus instanceof String)
                        || !("passed".equals(runtimeStatus) || "failed".equals(runtimeStatus))) {
                    throw new IOException("Runtime report has no valid terminal status");
                }
            } catch (Exception | LinkageError failure) {
                runtime = new JSONObject();
                runtime.put("status", "failed");
                runtime.put("error", errorDetails(failure));
            }
            report.put("runtime_probe", runtime);
            // CodexAstraUlt: Qualify the original interactive guest automatically
            // before offering a manual session. A crash preserves earlier stages.
            JSONObject homebrew = new JSONObject().put("status", "running");
            report.put("interactive_probe", homebrew);
            persist(reportFile, report);
            try {
                File scratch = new File(application.getCacheDir(), "homebrew-probe");
                homebrew = parseReport(nativeHomebrewProbe(
                        application.getApplicationInfo().nativeLibraryDir, scratch.getAbsolutePath()),
                        HOMEBREW_REPORT_LIMIT);
                String state = homebrew.optString("status", "");
                if (!("passed".equals(state) || "failed".equals(state))) {
                    throw new IOException("Homebrew report has no valid terminal status");
                }
            } catch (Exception | LinkageError failure) {
                homebrew = new JSONObject().put("status", "failed")
                        .put("error", errorDetails(failure));
            }
            report.put("interactive_probe", homebrew);
            // CodexAstraUlt: The platform baseline alone cannot satisfy 0.0.5. A
            // missing renderer section stays a failed, exportable diagnostic.
            JSONObject renderer = graphics.optJSONObject("renderer_probe");
            String rendererStatus = renderer == null ? "not reported"
                    : renderer.optString("status", "not reported");
            boolean passed = "passed".equals(cpuStatus)
                    && "passed".equals(graphics.optString("status"))
                    && graphics.optInt("schema", -1) == 2
                    && "passed".equals(rendererStatus)
                    && "passed".equals(runtime.optString("status"))
                    && "passed".equals(homebrew.optString("status"));
            report.put("status", passed ? "passed" : "failed");
            finishShell(shell, startedElapsed);
            report.put("android_shell", shell);
            byte[] persisted = persist(reportFile, report);
            // CodexAstraUlt: A missing renderer capability is useful diagnostic
            // evidence. Show it distinctly while retaining the complete report
            // and requiring actual renderer success for an overall pass.
            String summary = "CPU: " + cpuStatus + " · Vulkan: " + graphics.optString("status")
                    + " · Renderer checks: " + rendererStatus
                    + " · 3DS runtime: " + runtime.optString("status")
                    + " · Homebrew checks: " + homebrew.optString("status");
            String outcome = passed ? "Automated checks passed — test homebrew next. " : "Checks did not pass — ";
            complete(new Snapshot(false, outcome + summary,
                    report.toString(2)), persisted);
        } catch (Exception | LinkageError failure) {
            // CodexAstraUlt: Loader, UTF-8, JSON and file failures are structured
            // failures. Native process death cannot be caught here; the running
            // marker plus the device runner's deadline make it incomplete.
            try {
                finishShell(shell, startedElapsed);
                JSONObject failed = new JSONObject();
                failed.put("status", "failed");
                failed.put("error", errorDetails(failure));
                failed.put("android_shell", shell);
                byte[] persisted = persist(reportFile, failed);
                complete(new Snapshot(false, "Failed", failed.toString(2)), persisted);
            } catch (Exception persistenceFailure) {
                // CodexAstraUlt: A report that cannot be safely replaced must
                // not be treated as a prior pass; clear it and expose failure.
                reportFile.delete();
                complete(new Snapshot(false, "Failed: report could not be saved",
                        failure.getClass().getName() + ": " + bounded(String.valueOf(failure.getMessage()), 8192)
                                + "\nReport error: " + persistenceFailure.getClass().getName()), null);
            }
        }
    }

    // CodexAstraUlt: Share bounded structured error handling without letting
    // driver/load failures erase already completed CPU evidence.
    private static JSONObject errorDetails(Throwable failure) throws JSONException {
        JSONObject error = new JSONObject();
        error.put("type", failure.getClass().getName());
        String message = failure.getMessage();
        error.put("message", message == null ? "No error detail" : bounded(message, 8192));
        return error;
    }

    private static void finishShell(JSONObject shell, long startedElapsed) throws JSONException {
        shell.put("finished_at_epoch_ms", System.currentTimeMillis());
        shell.put("elapsed_realtime_ms", SystemClock.elapsedRealtime() - startedElapsed);
    }

    static JSONObject parseReport(byte[] bytes, int limit)
            throws IOException, JSONException {
        // CodexAstraUlt: Reject malformed UTF-8 rather than replacing bytes and
        // silently changing the native evidence returned through JNI.
        if (bytes == null || bytes.length == 0 || bytes.length > limit) {
            throw new IOException("Native report is empty or exceeds its size bound");
        }
        try {
            String text = StandardCharsets.UTF_8.newDecoder()
                    .onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT)
                    .decode(ByteBuffer.wrap(bytes)).toString();
            return new JSONObject(text);
        } catch (CharacterCodingException invalidUtf8) {
            throw new IOException("Native report is not valid UTF-8", invalidUtf8);
        }
    }

    private static byte[] persist(AtomicFile destination, JSONObject report) throws IOException {
        // CodexAstraUlt: AtomicFile retains at most one current report and its
        // transient write/recovery files; it avoids per-run bundles or timers.
        byte[] bytes = report.toString().getBytes(StandardCharsets.UTF_8);
        if (bytes.length > REPORT_LIMIT) {
            throw new IOException("Combined probe report exceeds its size bound");
        }
        FileOutputStream stream = null;
        try {
            stream = destination.startWrite();
            stream.write(bytes);
            destination.finishWrite(stream);
            stream = null;
            // CodexAstraUlt: AtomicFile logs some finalization failures instead
            // of throwing. Read back exact bytes before publishing a pass so a
            // failed rename cannot silently preserve a previous passing record.
            try (FileInputStream input = destination.openRead()) {
                ByteArrayOutputStream actual = new ByteArrayOutputStream(bytes.length);
                byte[] buffer = new byte[4096];
                int count;
                while ((count = input.read(buffer)) != -1) {
                    if (actual.size() + count > bytes.length) {
                        throw new IOException("Stored report differs from the current run");
                    }
                    actual.write(buffer, 0, count);
                }
                if (!Arrays.equals(actual.toByteArray(), bytes)) {
                    throw new IOException("Stored report differs from the current run");
                }
            }
        } catch (IOException failure) {
            if (stream != null) {
                destination.failWrite(stream);
            }
            throw failure;
        }
        return bytes;
    }

    private void complete(Snapshot result, byte[] persisted) {
        main.post(() -> {
            active = false;
            latestReport = persisted;
            publish(result);
        });
    }

    private void publish(Snapshot value) {
        requireMainThread();
        snapshot = new Snapshot(value.running, value.status, value.details,
                !active && latestReport != null && exportToken == null, exportMessage);
        Observer target = observer.get();
        if (target != null) {
            target.onProbeChanged(snapshot);
        }
    }

    private static String bounded(String value, int limit) {
        return value.length() <= limit ? value : value.substring(0, limit);
    }

    private static void requireMainThread() {
        if (Looper.myLooper() != Looper.getMainLooper()) {
            throw new IllegalStateException("Probe UI state must be accessed on the main thread");
        }
    }

    // CodexAstraUlt: All three synchronous calls run only inside the single worker.
    // Native code returns bounded UTF-8 bytes; JNI copies and releases buffers.
    private static native byte[] nativeRun(String libraryDirectory);
    // CodexAstraUlt: Run only the packaged original guest in private scratch space.
    private static native byte[] nativeRuntime(String libraryDirectory, String scratchDirectory);
    private static native byte[] nativeVulkan();
    // CodexAstraUlt: The scripted guest suite is independent of manual Android observations.
    private static native byte[] nativeHomebrewProbe(String libraryDirectory, String scratchDirectory);
}
