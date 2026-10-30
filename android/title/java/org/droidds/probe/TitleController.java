package org.droidds.probe;

import android.content.Context;
import android.content.res.AssetFileDescriptor;
import android.net.Uri;
import android.os.CancellationSignal;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.lang.ref.WeakReference;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.CancellationException;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

/** CodexAstraUlt: Import, native ownership and audio run off the UI thread.
 * Activity replacement reattaches to the same controller; private saves and
 * imports survive stop, error and process restart without automatic deletion. */
final class TitleController {
    interface Observer {
        void state(Snapshot snapshot);
        void reset();
        void pixels(int[] top, int[] bottom, int mask, long sequence);
    }
    static final class Snapshot {
        final String message;
        final boolean busy, running, importing, paused, canImport, canPlay, canExport, included;
        Snapshot(String message, boolean busy, boolean running, boolean importing,
                boolean paused, boolean canImport, boolean canPlay, boolean canExport, boolean included) {
            this.message = message; this.busy = busy; this.running = running;
            this.importing = importing; this.paused = paused; this.canImport = canImport; this.canPlay = canPlay;
            this.canExport = canExport; this.included = included;
        }
    }
    private static final long FRAME_NANOS = Math.round(4_481_136.0 / 268_111_856.0 * 1_000_000_000.0);
    private static TitleController instance;
    private final Context application;
    private final File privateRoot, imports, runtime, reportFile;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final ScheduledExecutorService worker = Executors.newSingleThreadScheduledExecutor(
            task -> new Thread(task, "droidds-title"));
    private final TitleInput input = new TitleInput();
    private final TitleLoop loop = new TitleLoop();
    private final AtomicLong generation = new AtomicLong();
    private final AtomicLong lifecycle = new AtomicLong();
    private final AtomicBoolean deliveryPending = new AtomicBoolean();
    private final AtomicBoolean progressPending = new AtomicBoolean();
    private final Object presentationLock = new Object();
    private WeakReference<Observer> observer = new WeakReference<>(null);
    // CodexAstraUlt: These UI fields change only on Android's main thread.
    private String message = "Preparing…";
    private boolean busy = true, running, importing, included, configured;
    private File imported;
    private byte[] manifest;
    private long expectedBytes;
    private String expectedHash;
    private volatile boolean foreground, userPaused, stopRequested;
    private volatile int importPercent;
    private volatile AtomicBoolean importCancel;
    private volatile CancellationSignal importSignal;
    private volatile InputStream importStream;
    // CodexAstraUlt: Only the native worker accesses the following session data.
    private long token, frames, slices, cycles, presented, nextStatus, inputOverflowStart;
    private int pendingPlanes, cachedPlanes;
    private boolean paused = true, closing, frameInProgress, nativeMode;
    private TitleAudio audio;
    private FramePacer pacer;
    private TitleInput.Sample currentInput = new TitleInput.Sample(0, 0, 0, false, 0, 0, 0, 0);
    private final int[] top = new int[400 * 240], bottom = new int[320 * 240];
    private final int[] displayedTop = new int[400 * 240], displayedBottom = new int[320 * 240];
    private final short[] pcm = new short[8192];
    private final long[] metrics = new long[5];

    private TitleController(Context context) throws IOException {
        application = context.getApplicationContext();
        // CodexAstraUlt: Android may expose its own private directory through a
        // platform symlink; resolve that trusted root before checking children.
        privateRoot = application.getFilesDir().getCanonicalFile();
        imports = new File(privateRoot, "imports"); runtime = new File(privateRoot, "runtime");
        reportFile = new File(privateRoot, "latest-title-report.json");
        worker.execute(this::configure);
    }

    static synchronized TitleController get(Context context) throws IOException {
        if (instance == null) instance = new TitleController(context);
        return instance;
    }

    private static byte[] read(InputStream source, int limit) throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192];
        int count;
        while ((count = source.read(buffer)) != -1) {
            if (count == 0) continue;
            if (output.size() > limit - count) throw new IOException("File exceeds its supported size");
            output.write(buffer, 0, count);
        }
        return output.toByteArray();
    }

    private static JSONObject json(byte[] bytes) throws JSONException {
        if (bytes == null || bytes.length == 0 || bytes.length > TitleImport.REPORT_LIMIT) {
            throw new JSONException("Missing or oversized native report");
        }
        return new JSONObject(new String(bytes, StandardCharsets.UTF_8));
    }

    private void configure() {
        try {
            final byte[] loaded;
            try (InputStream source = application.getAssets().open("title-manifest.json")) {
                loaded = read(source, 1024 * 1024);
            }
            JSONObject value = new JSONObject(new String(loaded, StandardCharsets.UTF_8));
            if (!"droidds_android_title".equals(value.getString("kind")) || value.getInt("schema_version") != 1) {
                throw new IOException("Unsupported packaged title manifest");
            }
            String program = value.getString("program_id");
            if (!program.matches("[0-9a-f]{16}")
                    || !application.getPackageName().equals("org.droidds.title.t" + program)) {
                throw new IOException("Package does not match its title identity");
            }
            JSONObject expected = value.getJSONObject("input");
            Object length = expected.get("bytes");
            if (!(length instanceof Long) && !(length instanceof Integer)) throw new IOException("Invalid input length");
            final long bytes = ((Number)length).longValue();
            final String hash = expected.getString("sha256");
            TitleImport.identity(bytes, hash);
            TitleImport.directory(imports); TitleImport.directory(runtime);
            File candidate = TitleImport.destination(imports, hash);
            final File existing = TitleImport.verify(candidate, bytes, hash, () -> false) ? candidate : null;
            boolean hasIncluded = false;
            for (String asset : application.getAssets().list("")) {
                if ("original-title.cxi".equals(asset)) hasIncluded = true;
            }
            final boolean includedAsset = hasIncluded;
            main.post(() -> {
                manifest = loaded; expectedBytes = bytes; expectedHash = hash;
                imported = existing; configured = true; included = includedAsset; busy = false;
                message = existing == null ? "Import the game file for this build." : "Ready to play.";
                notifyObserver();
            });
        } catch (Exception failure) {
            try {
                TitleImport.report(reportFile, new JSONObject().put("schema_version", 1)
                        .put("kind", "droidds_android_title_session").put("status", "failed")
                        .put("stage", "configuration").put("error", safeMessage(failure))
                        .toString().getBytes(StandardCharsets.UTF_8));
            } catch (Exception unavailable) { /* CodexAstraUlt: Preserve the original preparation failure. */ }
            main.post(() -> { busy = false; message = "This build could not prepare its game storage."; notifyObserver(); });
        }
    }

    void observe(Observer target) {
        observer = new WeakReference<>(target); notifyObserver();
        target.reset();
        // CodexAstraUlt: A recreated paused view can display the last real
        // guest planes without advancing the guest or inventing a new frame.
        synchronized (presentationLock) {
            if (cachedPlanes != 0) target.pixels(displayedTop, displayedBottom, cachedPlanes, Math.max(1, presented));
        }
    }
    void removeObserver(Observer target) { if (observer.get() == target) observer.clear(); }
    private void notifyObserver() {
        Observer target = observer.get();
        if (target != null) target.state(new Snapshot(message, busy, running, importing, userPaused,
                configured && !busy, configured && imported != null && !busy, reportFile.isFile() && !busy, included));
    }

    // CodexAstraUlt: Both included original fixtures and picker documents use
    // the exact same private-copy transaction; asset origin grants no bypass.
    void importGame(Uri uri, boolean useIncluded) {
        if (!configured || busy || (useIncluded && !included) || (!useIncluded && uri == null)) return;
        final long id = generation.incrementAndGet();
        busy = true; importing = true; message = "Importing game…"; notifyObserver();
        final AtomicBoolean cancel = new AtomicBoolean();
        final CancellationSignal signal = new CancellationSignal();
        importCancel = cancel; importSignal = signal;
        worker.execute(() -> {
            File result = null;
            String outcome;
            try {
                InputStream opened;
                if (useIncluded) opened = application.getAssets().open("original-title.cxi");
                else {
                    AssetFileDescriptor descriptor = application.getContentResolver().openAssetFileDescriptor(uri, "r", signal);
                    if (descriptor == null) throw new IOException("Document could not open");
                    try { opened = descriptor.createInputStream(); }
                    catch (IOException failure) { descriptor.close(); throw failure; }
                }
                importStream = opened;
                try (InputStream source = opened) {
                    result = TitleImport.copy(source, imports, expectedBytes, expectedHash, cancel::get, (done, total) -> {
                        importPercent = (int)(done * 100 / total);
                        if (progressPending.compareAndSet(false, true)) main.post(() -> {
                            try {
                                if (generation.get() == id && importing) { message = "Importing game… " + importPercent + "%"; notifyObserver(); }
                            } finally { progressPending.set(false); }
                        });
                    });
                }
                outcome = "Ready to play.";
            } catch (CancellationException failure) { outcome = "Import cancelled.";
            } catch (Exception failure) { outcome = cancel.get() ? "Import cancelled." : "Import failed: " + safeMessage(failure);
            } finally { importStream = null; importCancel = null; importSignal = null; }
            final File copied = result; final String text = outcome;
            main.post(() -> {
                if (generation.get() != id) return;
                if (copied != null) imported = copied;
                busy = false; importing = false; message = text; notifyObserver();
            });
        });
    }

    void cancelImport() {
        AtomicBoolean cancel = importCancel;
        if (cancel == null || !cancel.compareAndSet(false, true)) return;
        message = "Cancelling import…"; notifyObserver();
        final CancellationSignal signal = importSignal;
        final InputStream source = importStream;
        // CodexAstraUlt: Provider cancellation/close can block; one helper for
        // this explicitly cancelled transaction keeps Android's UI responsive.
        new Thread(() -> {
            if (signal != null) signal.cancel();
            if (source != null) try { source.close(); } catch (IOException ignored) { }
        }, "droidds-import-cancel").start();
    }

    void start(boolean useNative) {
        if (!configured || imported == null || busy) return;
        final long id = generation.incrementAndGet();
        final String inputPath = imported.getAbsolutePath();
        busy = true; running = true; userPaused = false; stopRequested = false;
        // CodexAstraUlt: Retire the preceding session's visible image before
        // startup; this UI reset is never counted as new guest output.
        synchronized (presentationLock) { cachedPlanes = 0; }
        Observer target = observer.get();
        if (target != null) target.reset();
        input.release(); message = "Starting game…"; deliveryPending.set(false); notifyObserver();
        worker.execute(() -> {
            loop.pause();
            token = 0; closing = false; paused = true; frameInProgress = false;
            frames = 0; cycles = 0; slices = 0; presented = 0; nextStatus = 0;
            inputOverflowStart = input.overflows();
            pendingPlanes = 0;
            synchronized (presentationLock) { cachedPlanes = 0; }
            audio = null; nativeMode = useNative; pacer = new FramePacer(FRAME_NANOS, 4);
            currentInput = new TitleInput.Sample(0, 0, 0, false, 0, 0, 0, 0);
            final long[] opening = new long[1];
            try {
                writeReport("starting", null, null);
                TitleNative.load();
                JSONObject opened = json(TitleNative.open(manifest, inputPath,
                        new File(application.getApplicationInfo().nativeLibraryDir).getCanonicalPath(),
                        runtime.getAbsolutePath(), useNative, opening));
                token = opening[0];
                if (!"opened".equals(opened.optString("status")) || token <= 0 || token != opened.getLong("token")) {
                    throw new IOException(opened.optString("error", "Game did not open"));
                }
                double rate = opened.getDouble("sample_rate");
                if (!Double.isFinite(rate) || rate < 32000 || rate > 33000) throw new IOException("Unsupported game audio rate");
                audio = new TitleAudio(rate);
                TitleNative.pause(token, true);
                if (stopRequested) finish(id, "stopped", null);
                else updateLifecycle(id);
            } catch (Exception | LinkageError failure) {
                if (token == 0) token = opening[0];
                finish(id, "failed", safeMessage(failure));
            }
        });
    }

    void foreground(boolean active) {
        foreground = active;
        if (!active) { lifecycle.incrementAndGet(); input.release(); }
        final long id = generation.get();
        worker.execute(() -> updateLifecycle(id));
    }

    void pauseOrResume() {
        if (!running) return;
        userPaused = !userPaused; lifecycle.incrementAndGet(); input.release(); notifyObserver();
        final long id = generation.get(); worker.execute(() -> updateLifecycle(id));
    }

    private void updateLifecycle(long id) {
        if (generation.get() != id || closing || token == 0) return;
        if (stopRequested) { finish(id, "stopped", null); return; }
        final boolean boundary = loop.synchronize(lifecycle.get());
        boolean shouldPause = !foreground || userPaused;
        try {
            if ((shouldPause || boundary) && !paused) {
                loop.pause();
                TitleNative.pause(token, true); paused = true; frameInProgress = false;
                if (audio != null) audio.pause();
            }
            if (!shouldPause && paused) {
                TitleNative.pause(token, false); paused = false;
                currentInput = new TitleInput.Sample(0, 0, 0, false, 0, 0, 0, 0);
                audio.start(); pacer.resume(SystemClock.elapsedRealtimeNanos()); frameInProgress = false;
                final long ticket = loop.resume();
                worker.execute(() -> step(id, ticket));
            }
            postMessage(id, userPaused ? "Paused." : frames == 0 ? "Starting game…" : "Running.");
        } catch (Exception | LinkageError failure) { finish(id, "failed", safeMessage(failure)); }
    }

    // CodexAstraUlt: Yielded slices keep progressing without declaring a slow
    // startup to be a bad frame. Only actual completed frames affect pacing;
    // only ready image planes update the UI, and PCM is drained on every slice.
    private void step(long id, long ticket) {
        if (generation.get() != id || !loop.accepts(ticket) || closing || paused || token == 0) return;
        if (!foreground || userPaused) { updateLifecycle(id); return; }
        if (stopRequested) { finish(id, "stopped", null); return; }
        try {
            currentInput = input.next(currentInput);
            long beforeLifecycle = lifecycle.get();
            long start = SystemClock.elapsedRealtimeNanos();
            if (!frameInProgress) { pacer.begin(start); frameInProgress = true; }
            int result = TitleNative.slice(token, currentInput.buttons, currentInput.circleX, currentInput.circleY,
                    currentInput.cStickX, currentInput.cStickY, currentInput.x, currentInput.y, currentInput.touched,
                    top, bottom, pcm, metrics);
            if (result == -2) { loop.pause(); paused = true; frameInProgress = false; audio.pause(); updateLifecycle(id); return; }
            if (result != 0 || metrics[2] < 0 || metrics[2] > 4096 || metrics[4] < 0 || metrics[4] > 3
                    || metrics[0] < frames || metrics[1] < cycles || metrics[3] < 0 || metrics[3] > 1) {
                throw new IOException("Game returned invalid slice data");
            }
            slices++; cycles = metrics[1];
            boolean active = foreground && !userPaused && lifecycle.get() == beforeLifecycle && !stopRequested;
            audio.accept(pcm, (int)metrics[2], active);
            // CodexAstraUlt: Retain a newly ready plane across a pause that
            // arrives during this slice, even if the guest later stays still.
            pendingPlanes |= (int)metrics[4];
            if (active && pendingPlanes != 0) present(id, 0, beforeLifecycle);
            long delay = 0;
            if (metrics[0] > frames) {
                frames = metrics[0]; delay = pacer.finish(SystemClock.elapsedRealtimeNanos()); frameInProgress = false;
            }
            if (metrics[3] != 0) { finish(id, "guest_exited", null); return; }
            if (stopRequested) { finish(id, "stopped", null); return; }
            long now = SystemClock.elapsedRealtime();
            if (now >= nextStatus) { nextStatus = now + 1000; postMessage(id, frames == 0 ? "Starting game…" : "Running."); }
            if (active) worker.schedule(() -> step(id, ticket), delay, TimeUnit.NANOSECONDS);
            else {
                // CodexAstraUlt: A pause/resume pair can both arrive during one
                // slice. Force that missed pause boundary before consulting the
                // latest foreground state, so the work loop cannot become idle.
                loop.pause(); TitleNative.pause(token, true); paused = true; frameInProgress = false;
                audio.pause(); updateLifecycle(id);
            }
        } catch (Exception | LinkageError failure) { finish(id, "failed", safeMessage(failure)); }
    }

    private void present(long id, int mask, long epoch) {
        pendingPlanes |= mask;
        if (!deliveryPending.compareAndSet(false, true)) return;
        final int deliveredPlanes = pendingPlanes;
        pendingPlanes = 0;
        final long sequence;
        synchronized (presentationLock) {
            if ((deliveredPlanes & 1) != 0) System.arraycopy(top, 0, displayedTop, 0, top.length);
            if ((deliveredPlanes & 2) != 0) System.arraycopy(bottom, 0, displayedBottom, 0, bottom.length);
            cachedPlanes |= deliveredPlanes;
            sequence = ++presented;
        }
        main.post(() -> {
            try {
                if (generation.get() == id && foreground && !userPaused && !stopRequested && lifecycle.get() == epoch) {
                    Observer target = observer.get();
                    if (target != null) synchronized (presentationLock) {
                        target.pixels(displayedTop, displayedBottom, deliveredPlanes, sequence);
                    }
                }
            } finally { if (generation.get() == id) deliveryPending.set(false); }
        });
    }

    void stop() {
        if (!running) return;
        stopRequested = true; lifecycle.incrementAndGet(); input.release();
        message = "Stopping…"; notifyObserver();
        final long id = generation.get(); worker.execute(() -> { if (generation.get() == id && token != 0) finish(id, "stopped", null); });
    }

    private void finish(long id, String outcome, String error) {
        if (generation.get() != id || closing) return;
        loop.pause(); closing = true; paused = true; frameInProgress = false;
        JSONObject nativeReport = null;
        try { if (token != 0) nativeReport = json(TitleNative.report(token)); }
        catch (Exception | LinkageError failure) { outcome = "failed"; if (error == null) error = safeMessage(failure); }
        finally {
            if (token != 0) {
                try { TitleNative.close(token); }
                catch (Exception | LinkageError failure) { outcome = "failed"; if (error == null) error = safeMessage(failure); }
                token = 0;
            }
            if (audio != null) audio.pause();
        }
        boolean saved = true;
        try { writeReport(outcome, error, nativeReport); }
        catch (Exception failure) { saved = false; }
        final String state = !saved ? "Game stopped; its report could not be saved."
                : "failed".equals(outcome) ? "Game stopped with an error. Save the report for details."
                : "guest_exited".equals(outcome) ? "Game closed." : "Stopped.";
        main.post(() -> { if (generation.get() == id) { running = false; busy = false; message = state; notifyObserver(); } });
    }

    private void writeReport(String outcome, String error, JSONObject nativeReport) throws IOException, JSONException {
        JSONObject report = new JSONObject().put("schema_version", 1).put("kind", "droidds_android_title_session")
                .put("status", outcome).put("route", nativeMode ? "native" : "interpreter")
                .put("input_sha256", expectedHash).put("slices", slices).put("frames", frames).put("cycles", cycles)
                .put("presentation", "android-canvas-readback").put("image_deliveries", presented)
                .put("input_queue_overflows", Math.max(0, input.overflows() - inputOverflowStart))
                .put("error", error == null ? JSONObject.NULL : error)
                .put("runtime", nativeReport == null ? JSONObject.NULL : nativeReport)
                .put("audio", audio == null ? JSONObject.NULL : audio.report());
        TitleImport.report(reportFile, report.toString().getBytes(StandardCharsets.UTF_8));
    }

    void exportReport(Uri destination) {
        if (busy || destination == null || !reportFile.isFile()) return;
        busy = true; message = "Saving report…"; notifyObserver();
        worker.execute(() -> {
            String result;
            try {
                final byte[] bytes;
                try (InputStream source = new FileInputStream(reportFile)) { bytes = read(source, TitleImport.REPORT_LIMIT); }
                try (OutputStream output = application.getContentResolver().openOutputStream(destination, "wt")) {
                    if (output == null) throw new IOException("Report destination unavailable");
                    output.write(bytes); output.flush();
                }
                result = "Report saved.";
            } catch (Exception failure) { result = "Could not save the report to that location."; }
            final String text = result;
            main.post(() -> { busy = false; message = text; notifyObserver(); });
        });
    }

    private void postMessage(long id, String text) {
        main.post(() -> { if (generation.get() == id && running) { message = text; notifyObserver(); } });
    }
    private static String safeMessage(Throwable failure) {
        String text = failure.getMessage();
        if (text == null || text.isEmpty()) text = failure.getClass().getSimpleName();
        return text.substring(0, Math.min(512, text.length()));
    }
    void button(int bit, boolean down, int source) { if (foreground && running && !userPaused && !stopRequested) input.button(bit, down, source); }
    void touch(int x, int y, boolean down) { if (foreground && running && !userPaused && !stopRequested) input.touch(x, y, down); }
    void axes(float cx, float cy, float sx, float sy) { if (foreground && running && !userPaused && !stopRequested) input.axes(cx, cy, sx, sy); }
    void releaseInputs() { input.release(); }
}
