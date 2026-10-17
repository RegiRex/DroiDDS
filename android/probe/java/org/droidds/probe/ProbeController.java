package org.droidds.probe;

import android.content.Context;
import android.content.pm.PackageInfo;
import android.os.Handler;
import android.os.Looper;
import android.os.Process;
import android.util.AtomicFile;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.lang.ref.WeakReference;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** CodexAstraUlt: One process-scoped worker serializes native runs. It owns only
 * application context and a weak UI observer, so backgrounding/recreation does
 * not leak Activities or duplicate a run. A device-side watchdog handles native
 * hangs by stopping this process; Java never tries to terminate a native thread. */
final class ProbeController {
    interface Observer {
        void onProbeChanged(Snapshot snapshot);
    }

    // CodexAstraUlt: Immutable snapshots cross from worker to UI; raw JSON shown
    // onscreen is capped independently of the one bounded persisted report.
    static final class Snapshot {
        final boolean running;
        final String status;
        final String details;

        Snapshot(boolean running, String status, String details) {
            this.running = running;
            this.status = status;
            this.details = details.length() <= 32768
                    ? details : details.substring(0, 32768) + "\n[Display truncated]";
        }
    }

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

    private void start(String requestedId) {
        if (active) {
            return;
        }
        active = true;
        String runId = UUID.randomUUID().toString();
        String requestId = requestedId == null || requestedId.isEmpty() ? runId : requestedId;
        long startedAt = System.currentTimeMillis();
        publish(new Snapshot(true, "Running", "Run: " + runId));
        worker.execute(() -> execute(runId, requestId, startedAt));
    }

    private void execute(String runId, String requestId, long startedAt) {
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
            JSONObject report = parseReport(result);
            Object status = report.opt("status");
            if (!(status instanceof String)
                    || !("passed".equals(status) || "failed".equals(status))) {
                throw new IOException("Native report has no valid terminal status");
            }
            shell.put("finished_at_epoch_ms", System.currentTimeMillis());
            report.put("android_shell", shell);
            persist(reportFile, report);
            complete(new Snapshot(false, "passed".equals(status) ? "Passed" : "Failed",
                    report.toString(2)));
        } catch (Exception | LinkageError failure) {
            // CodexAstraUlt: Loader, UTF-8, JSON and file failures are structured
            // failures. Native process death cannot be caught here; the running
            // marker plus the device runner's deadline make it incomplete.
            try {
                shell.put("finished_at_epoch_ms", System.currentTimeMillis());
                JSONObject error = new JSONObject();
                error.put("type", failure.getClass().getName());
                String message = failure.getMessage();
                error.put("message", message == null ? "No error detail" : bounded(message, 8192));
                JSONObject failed = new JSONObject();
                failed.put("status", "failed");
                failed.put("error", error);
                failed.put("android_shell", shell);
                persist(reportFile, failed);
                complete(new Snapshot(false, "Failed", failed.toString(2)));
            } catch (Exception persistenceFailure) {
                // CodexAstraUlt: A report that cannot be safely replaced must
                // not be treated as a prior pass; clear it and expose failure.
                reportFile.delete();
                complete(new Snapshot(false, "Failed: report could not be saved",
                        failure.getClass().getName() + ": " + bounded(String.valueOf(failure.getMessage()), 8192)
                                + "\nReport error: " + persistenceFailure.getClass().getName()));
            }
        }
    }

    private static JSONObject parseReport(byte[] bytes)
            throws IOException, JSONException {
        // CodexAstraUlt: Reject malformed UTF-8 rather than replacing bytes and
        // silently changing the native evidence returned through JNI.
        if (bytes == null || bytes.length == 0 || bytes.length > 1024 * 1024) {
            throw new IOException("Native report is empty or exceeds 1 MiB");
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

    private static void persist(AtomicFile destination, JSONObject report) throws IOException {
        // CodexAstraUlt: AtomicFile retains at most one current report and its
        // transient write/recovery files; it avoids per-run bundles or timers.
        byte[] bytes = report.toString().getBytes(StandardCharsets.UTF_8);
        if (bytes.length > 1024 * 1024 + 16384) {
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
    }

    private void complete(Snapshot result) {
        main.post(() -> {
            active = false;
            publish(result);
        });
    }

    private void publish(Snapshot value) {
        requireMainThread();
        snapshot = value;
        Observer target = observer.get();
        if (target != null) {
            target.onProbeChanged(value);
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

    // CodexAstraUlt: This synchronous call runs only inside the single worker.
    // Rust returns UTF-8 bytes via a narrow C ABI; JNI copies and releases them.
    private static native byte[] nativeRun(String libraryDirectory);
}
