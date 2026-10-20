package org.droidds.probe;

import android.content.Context;
import android.media.AudioAttributes;
import android.media.AudioFormat;
import android.media.AudioTrack;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.lang.ref.WeakReference;
import java.nio.charset.StandardCharsets;
import java.util.ArrayDeque;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

/** CodexAstraUlt: One persistent worker owns the native interactive session.
 * Activity recreation only reattaches a weak observer; it cannot duplicate a
 * guest, retain an Activity, or run native work on Android's main thread. */
final class HomebrewController {
    interface Observer {
        void onHomebrewState(String state, boolean finished);
        void onHomebrewFrame(int[] top, int[] bottom, long guestSerial);
    }

    // CodexAstraUlt: Native-resolution buffers and a fixed input queue bound
    // memory independently of display size, frame count and repeated UI events.
    private static final int INPUT_LIMIT = 64;
    private static final long FRAME_NANOS = Math.round(4_481_136.0 / 268_111_856.0 * 1_000_000_000.0);
    private static final int MAX_CATCHUP_FRAMES = 4;
    private static final long MAX_FOREGROUND_MS = 120000L;
    private static HomebrewController instance;
    private final Context application;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final ScheduledExecutorService worker = Executors.newSingleThreadScheduledExecutor(r ->
            new Thread(r, "droidds-homebrew"));
    private WeakReference<Observer> observer = new WeakReference<>(null);
    private WeakReference<Observer> previousView = new WeakReference<>(null);
    private final Object inputLock = new Object();
    private final ArrayDeque<Input> inputs = new ArrayDeque<>();
    private final AtomicBoolean deliveryPending = new AtomicBoolean();
    private final AtomicLong presented = new AtomicLong();
    private final AtomicLong lifecycleGeneration = new AtomicLong();
    private final AtomicLong viewAttachments = new AtomicLong();
    private final AtomicLong viewReplacements = new AtomicLong();
    private final int[] top = new int[400 * 240];
    private final int[] bottom = new int[320 * 240];
    private final int[] displayedTop = new int[400 * 240];
    private final int[] displayedBottom = new int[320 * 240];
    private final short[] pcm = new short[4096 * 2];
    private final long[] metrics = new long[4];
    private volatile String sessionId;
    private volatile boolean foreground;
    private volatile boolean stopRequested;
    private volatile String heard = "not_confirmed";
    private volatile String seen = "not_confirmed";
    private String state = "Preparing original homebrew…";
    private boolean finished;
    private int buttons;
    private int physicalButtons;
    private int virtualButtons;
    private int otherButtons;
    private int hatButtons;
    private int touchX;
    private int touchY;
    private boolean touched;
    private long hardwareEvents;
    private long touchEvents;
    private long touchDownEvents;
    private long virtualEvents;
    private long inputOverflows;
    private long otherKeyEvents;
    private long topDrawn;
    private long bottomDrawn;
    private long lastPairDrawn;
    // CodexAstraUlt: Fields below are owned only by the dedicated worker.
    private long nativeToken;
    private Input currentInput = new Input(0, 0, 0, false);
    private boolean prepared;
    private boolean closing;
    private boolean paused = true;
    private long frameCount;
    private long foregroundMs;
    private long foregroundStarted;
    private long pauseCount;
    private long resumeCount;
    private long stepErrors;
    private long scheduleGeneration;
    private long foregroundFrameStarts;
    private long rejectedBackgroundStarts;
    private long inFlightCompletions;
    // CodexAstraUlt: Separate mapped touch edges from inputs actually submitted
    // to the native guest, and report bounded pacing aggregates without frame logs.
    private long validTouchInputFrames;
    private FramePacer pacer = new FramePacer(FRAME_NANOS, MAX_CATCHUP_FRAMES);
    private AudioSink audio;
    private String stopReason = "stop_button";

    private static final class Input {
        final int buttons;
        final int x;
        final int y;
        final boolean touched;
        Input(int buttons, int x, int y, boolean touched) {
            this.buttons = buttons;
            this.x = x;
            this.y = y;
            this.touched = touched;
        }
    }

    private HomebrewController(Context context) {
        application = context.getApplicationContext();
    }

    static synchronized HomebrewController get(Context context) {
        if (instance == null) instance = new HomebrewController(context);
        return instance;
    }

    // CodexAstraUlt: Reservation is main-thread-only and precedes persistence of
    // the running marker; native creation waits for startPrepared afterwards.
    void reserve(String id) {
        sessionId = id;
        foreground = false;
        stopRequested = false;
        heard = "not_confirmed";
        seen = "not_confirmed";
        finished = false;
        state = "Preparing original homebrew…";
        deliveryPending.set(false);
        presented.set(0);
        viewAttachments.set(0);
        viewReplacements.set(0);
        previousView.clear();
        topDrawn = 0;
        bottomDrawn = 0;
        lastPairDrawn = 0;
        synchronized (inputLock) {
            inputs.clear();
            buttons = 0;
            physicalButtons = 0;
            virtualButtons = 0;
            otherButtons = 0;
            hatButtons = 0;
            touched = false;
            touchX = 0;
            touchY = 0;
            hardwareEvents = 0;
            touchEvents = 0;
            touchDownEvents = 0;
            virtualEvents = 0;
            inputOverflows = 0;
            otherKeyEvents = 0;
        }
        worker.execute(() -> {
            nativeToken = 0;
            prepared = false;
            closing = false;
            paused = true;
            frameCount = 0;
            foregroundMs = 0;
            foregroundStarted = 0;
            pauseCount = 0;
            resumeCount = 0;
            stepErrors = 0;
            foregroundFrameStarts = 0;
            rejectedBackgroundStarts = 0;
            inFlightCompletions = 0;
            validTouchInputFrames = 0;
            pacer = new FramePacer(FRAME_NANOS, MAX_CATCHUP_FRAMES);
            scheduleGeneration++;
            audio = null;
            stopReason = "stop_button";
            currentInput = new Input(0, 0, 0, false);
        });
    }

    boolean matches(String id) {
        return id != null && id.equals(sessionId) && !finished;
    }

    void observe(String id, Observer target) {
        if (!matches(id)) {
            target.onHomebrewState("This session expired. Start a new session from the report screen.", true);
            return;
        }
        observer = new WeakReference<>(target);
        if (previousView.get() != target) {
            if (viewAttachments.getAndIncrement() != 0) viewReplacements.incrementAndGet();
            previousView = new WeakReference<>(target);
        }
        target.onHomebrewState(state, finished);
    }

    void removeObserver(Observer target) {
        if (observer.get() == target) observer.clear();
    }

    void preparationFailed(String id) {
        if (!id.equals(sessionId)) return;
        finished = true;
        state = "Session could not start because its report could not be saved.";
        notifyObserver();
    }

    void startPrepared(String id) {
        if (!id.equals(sessionId) || finished) return;
        worker.execute(() -> {
            if (!id.equals(sessionId) || closing) return;
            prepared = true;
            if (stopRequested) {
                finishWorker(id, "interrupted");
                return;
            }
            try {
                System.loadLibrary("droidds_probe_jni");
                // CodexAstraUlt: Ownership reaches a preallocated output before
                // JSON parsing can allocate or throw. Finally also runs on Error,
                // so failed setup cannot strand the native session/global lock.
                final long[] openingToken = new long[1];
                boolean setupComplete = false;
                try {
                    byte[] openedBytes = nativeOpen(application.getApplicationInfo().nativeLibraryDir,
                            new File(application.getCacheDir(), "homebrew-session").getAbsolutePath(),
                            openingToken);
                    nativeToken = openingToken[0];
                    JSONObject opened = ProbeController.parseReport(openedBytes,
                            ProbeController.HOMEBREW_REPORT_LIMIT);
                    if (!"opened".equals(opened.optString("status"))) {
                        throw new IllegalStateException("Original guest could not open: " + opened.optString("error"));
                    }
                    double sampleRate = opened.getDouble("sample_rate");
                    if (nativeToken <= 0 || nativeToken != opened.getLong("token")
                            || !Double.isFinite(sampleRate) || sampleRate < 32000 || sampleRate > 33000) {
                        throw new IllegalStateException("Original guest returned an invalid session identity/rate");
                    }
                    audio = new AudioSink(sampleRate);
                    nativePause(nativeToken, true);
                    postState(id, "Use the controls and lower display. Stop and save when finished.", false);
                    updateForegroundWorker(id, foreground);
                    setupComplete = true;
                } finally {
                    if (!setupComplete) {
                        long openedToken = openingToken[0];
                        openingToken[0] = 0;
                        nativeToken = 0;
                        try {
                            if (openedToken != 0) nativeClose(openedToken);
                        } finally {
                            if (audio != null) audio.pause();
                        }
                    }
                }
            } catch (Exception | LinkageError failure) {
                stepErrors++;
                stopReason = "open_failed:" + failure.getClass().getSimpleName();
                finishWorker(id, "failed");
            }
        });
    }

    // CodexAstraUlt: The volatile foreground guard stops new work immediately;
    // the queued transition flushes audio and pauses Rust on its owning thread.
    void setForeground(String id, boolean value) {
        if (!matches(id)) return;
        foreground = value;
        if (!value) {
            lifecycleGeneration.incrementAndGet();
            clearInput();
        }
        worker.execute(() -> updateForegroundWorker(id, value));
    }

    private void updateForegroundWorker(String id, boolean requested) {
        if (!id.equals(sessionId) || closing || !prepared || nativeToken == 0) return;
        if (stopRequested) {
            finishWorker(id, "completed");
            return;
        }
        try {
            if (requested && foreground && paused) {
                nativePause(nativeToken, false);
                paused = false;
                resumeCount++;
                foregroundStarted = SystemClock.elapsedRealtime();
                audio.start();
                pacer.resume(SystemClock.elapsedRealtimeNanos());
                final long generation = ++scheduleGeneration;
                worker.execute(() -> step(id, generation));
            } else if (!requested && !paused) {
                scheduleGeneration++;
                paused = true;
                foregroundMs += SystemClock.elapsedRealtime() - foregroundStarted;
                foregroundStarted = 0;
                pauseCount++;
                nativePause(nativeToken, true);
                audio.pause();
                currentInput = new Input(0, 0, 0, false);
            }
        } catch (Exception | LinkageError failure) {
            stepErrors++;
            stopReason = "lifecycle_failed:" + failure.getClass().getSimpleName();
            finishWorker(id, "failed");
        }
    }

    private void step(String id, long generation) {
        if (!id.equals(sessionId) || generation != scheduleGeneration || closing || paused || !foreground) return;
        if (stopRequested) {
            finishWorker(id, "completed");
            return;
        }
        long start = SystemClock.elapsedRealtimeNanos();
        try {
            synchronized (inputLock) {
                if (!inputs.isEmpty()) currentInput = inputs.removeFirst();
            }
            if (!foreground) {
                rejectedBackgroundStarts++;
                return;
            }
            final long lifecycle = lifecycleGeneration.get();
            pacer.begin(start);
            foregroundFrameStarts++;
            if (currentInput.touched) validTouchInputFrames++;
            int result = nativeFrame(nativeToken, currentInput.buttons, currentInput.x, currentInput.y,
                    currentInput.touched, top, bottom, pcm, metrics);
            // CodexAstraUlt: A paused native session is a recoverable lifecycle
            // rejection, never evidence of a corrupt guest or a reason to spin.
            if (result == -2) {
                updateForegroundWorker(id, false);
                if (foreground) updateForegroundWorker(id, true);
                return;
            }
            frameCount++;
            boolean crossedPause = lifecycleGeneration.get() != lifecycle;
            if (crossedPause) inFlightCompletions++;
            // CodexAstraUlt: An already executing native frame may finish after
            // onPause, but its output is never newly presented/played in background.
            audio.accept(pcm, (int)metrics[2], foreground && !crossedPause);
            if (foreground && !crossedPause) {
                queuePresentation(id, frameCount, lifecycle);
            }
            // CodexAstraUlt: Replace relative per-frame waiting, which added
            // every executor wake delay to guest time, with bounded absolute
            // deadlines. Catch-up runs the full guest frame and all its draws.
            long delay = pacer.finish(SystemClock.elapsedRealtimeNanos());
            long elapsed = foregroundMs + SystemClock.elapsedRealtime() - foregroundStarted;
            if (metrics[3] != 0 || frameCount >= 6000 || elapsed >= MAX_FOREGROUND_MS) {
                stopReason = metrics[3] != 0 ? "guest_exited" : "session_limit";
                finishWorker(id, "completed");
            } else if (foreground && !stopRequested) {
                worker.schedule(() -> step(id, generation), delay, TimeUnit.NANOSECONDS);
            }
        } catch (Exception | LinkageError failure) {
            stepErrors++;
            stopReason = "step_failed:" + failure.getClass().getSimpleName();
            finishWorker(id, "failed");
        }
    }

    // CodexAstraUlt: One pending delivery owns its pixel arrays until main has
    // copied them into Bitmaps. Slow UI work cannot accumulate frame objects.
    private void queuePresentation(String id, long serial, long lifecycle) {
        if (!deliveryPending.compareAndSet(false, true)) return;
        System.arraycopy(top, 0, displayedTop, 0, top.length);
        System.arraycopy(bottom, 0, displayedBottom, 0, bottom.length);
        main.post(() -> {
            try {
                if (id.equals(sessionId) && foreground && !finished
                        && lifecycle == lifecycleGeneration.get()) {
                    Observer target = observer.get();
                    if (target != null) {
                        target.onHomebrewFrame(displayedTop, displayedBottom, serial);
                    }
                }
            } finally {
                if (id.equals(sessionId)) deliveryPending.set(false);
            }
        });
    }

    // CodexAstraUlt: Count a frame only after both actual Canvas views draw its
    // copied pixels, not when invalidate() merely queues future rendering.
    void canvasDrawn(String id, boolean upper, long sequence) {
        if (!matches(id) || !foreground || sequence <= 0) return;
        if (upper) topDrawn = sequence; else bottomDrawn = sequence;
        if (topDrawn == bottomDrawn && topDrawn > lastPairDrawn) {
            lastPairDrawn = topDrawn;
            presented.incrementAndGet();
        }
    }

    void button(int mask, boolean down, int source) {
        if (!foreground || stopRequested) return;
        synchronized (inputLock) {
            int old = source == 1 ? physicalButtons : source == 3 ? hatButtons
                    : source == 0 ? virtualButtons : otherButtons;
            int next = down ? old | mask : old & ~mask;
            if (next == old) return;
            if (source == 1) physicalButtons = next;
            else if (source == 3) hatButtons = next;
            else if (source == 0) virtualButtons = next;
            else otherButtons = next;
            buttons = physicalButtons | virtualButtons | otherButtons | hatButtons;
            if (source == 1 || source == 3) hardwareEvents++;
            else if (source == 0) virtualEvents++;
            else otherKeyEvents++;
            enqueueInput(false);
        }
    }

    void touch(int x, int y, boolean down) {
        if (!foreground || stopRequested) return;
        synchronized (inputLock) {
            if (down && !touched) touchDownEvents++;
            touched = down;
            touchX = Math.max(0, Math.min(319, x));
            touchY = Math.max(0, Math.min(239, y));
            touchEvents++;
            enqueueInput(true);
        }
    }

    private void enqueueInput(boolean movingTouch) {
        // CodexAstraUlt: Coalesce only consecutive held-touch positions. Button
        // changes and touch down/up edges remain ordered, avoiding drag backlog.
        Input last = inputs.peekLast();
        if (movingTouch && last != null && touched && last.touched && last.buttons == buttons) {
            inputs.removeLast();
        }
        if (inputs.size() >= INPUT_LIMIT) {
            inputOverflows++;
            inputs.clear();
        }
        inputs.addLast(new Input(buttons, touchX, touchY, touched));
    }

    private void clearInput() {
        synchronized (inputLock) {
            inputs.clear();
            buttons = 0;
            physicalButtons = 0;
            virtualButtons = 0;
            otherButtons = 0;
            hatButtons = 0;
            touched = false;
            inputs.addLast(new Input(0, 0, 0, false));
        }
    }

    void releaseInputs() { clearInput(); }
    boolean displayConfirmed() { return "yes".equals(seen); }
    boolean audioConfirmed() { return "yes".equals(heard); }
    void confirmDisplay(boolean value) { seen = value ? "yes" : "no"; }
    void confirmAudio(boolean value) { heard = value ? "yes" : "no"; }

    void stop(String id, String reason) {
        if (!matches(id)) return;
        stopRequested = true;
        foreground = false;
        clearInput();
        postState(id, "Stopping and saving session…", false);
        worker.execute(() -> {
            if (!id.equals(sessionId) || closing) return;
            stopReason = reason;
            if (prepared) finishWorker(id, nativeToken == 0 ? "interrupted" : "completed");
        });
    }

    private void finishWorker(String id, String outcome) {
        if (closing || !id.equals(sessionId)) return;
        closing = true;
        foreground = false;
        if (!paused && foregroundStarted != 0) {
            foregroundMs += SystemClock.elapsedRealtime() - foregroundStarted;
            foregroundStarted = 0;
        }
        paused = true;
        byte[] report = "{\"status\":\"interrupted\",\"error\":\"Session never opened\"}"
                .getBytes(StandardCharsets.UTF_8);
        try {
            if (nativeToken != 0) report = nativeReport(nativeToken);
        } catch (Exception | LinkageError failure) {
            outcome = "failed";
            stepErrors++;
        } finally {
            if (nativeToken != 0) {
                try { nativeClose(nativeToken); }
                catch (LinkageError failure) { outcome = "failed"; }
                nativeToken = 0;
            }
            if (audio != null) audio.pause();
        }
        JSONObject observations = new JSONObject();
        try {
            observations.put("diagnostics_schema", 2);
            observations.put("presentation", "android-canvas-rgba-readback");
            observations.put("top_width", 400);
            observations.put("top_height", 240);
            observations.put("bottom_width", 320);
            observations.put("bottom_height", 240);
            observations.put("frames_received", frameCount);
            observations.put("presented_frames", presented.get());
            observations.put("view_attachments", viewAttachments.get());
            observations.put("view_replacements", viewReplacements.get());
            observations.put("duration_foreground_ms", foregroundMs);
            observations.put("pause_count", pauseCount);
            observations.put("resume_count", resumeCount);
            observations.put("foreground_frame_starts", foregroundFrameStarts);
            observations.put("background_frame_start_rejections", rejectedBackgroundStarts);
            observations.put("in_flight_frames_completed_after_pause", inFlightCompletions);
            observations.put("native_step_errors", stepErrors);
            observations.put("stop_reason", stopReason);
            // CodexAstraUlt: These counters distinguish UI mapping from native
            // input submission, and expose pacing drift without per-frame data.
            observations.put("valid_touch_input_frames", validTouchInputFrames);
            JSONObject pacing = new JSONObject();
            pacing.put("policy", "absolute-deadline-bounded-catchup");
            pacing.put("interval_ns", FRAME_NANOS);
            pacing.put("max_catchup_frames", MAX_CATCHUP_FRAMES);
            pacing.put("epochs", pacer.epochs());
            pacing.put("frame_starts", pacer.frames());
            pacing.put("late_frame_starts", pacer.lateFrames());
            pacing.put("lateness_ns_total", pacer.totalLateness());
            pacing.put("lateness_ns_max", pacer.maximumLateness());
            pacing.put("frame_work_ns_max", pacer.maximumWork());
            pacing.put("deadline_resets", pacer.resets());
            observations.put("pacing", pacing);
            observations.put("display_seen_by_user", seen);
            observations.put("heard_by_user", heard);
            synchronized (inputLock) {
                observations.put("hardware_button_events", hardwareEvents);
                observations.put("touch_events", touchEvents);
                observations.put("touch_down_events", touchDownEvents);
                observations.put("virtual_button_events", virtualEvents);
                observations.put("other_key_events", otherKeyEvents);
                observations.put("input_queue_overflows", inputOverflows);
            }
            observations.put("audio", audio == null ? new JSONObject().put("status", "not_started") : audio.report());
            if (audio != null && audio.failed()) outcome = "failed";
        } catch (JSONException invalid) {
            outcome = "failed";
        }
        final byte[] nativeResult = report;
        final String finalOutcome = outcome;
        main.post(() -> ProbeController.get(application).finishHomebrew(id, nativeResult,
                observations, finalOutcome, () -> postState(id, "Session saved. Return to Save report.", true)));
    }

    private void postState(String id, String message, boolean terminal) {
        main.post(() -> {
            if (!id.equals(sessionId)) return;
            state = message;
            finished = terminal;
            notifyObserver();
        });
    }

    private void notifyObserver() {
        Observer target = observer.get();
        if (target != null) target.onHomebrewState(state, finished);
    }

    /** CodexAstraUlt: Stateful linear interpolation converts only guest PCM to
     * 48 kHz. A fixed stereo ring and nonblocking writes bound audio latency and
     * memory; overflow/flush/underrun counters remain visible in the report. */
    private static final class AudioSink {
        private static final int OUTPUT_RATE = 48000;
        private static final int PREFILL_FRAMES = OUTPUT_RATE / 20;
        private final double inputRate;
        private final short[] queue = new short[8192 * 2];
        private AudioTrack track;
        private int read;
        private int count;
        private long generated;
        private long converted;
        private long written;
        private long played;
        private long dropped;
        private long flushed;
        private long partial;
        private long underruns;
        private long trackWritten;
        private long trackPlayed;
        private final AudioStartup startup = new AudioStartup(PREFILL_FRAMES);
        private long trackPreparations;
        private long playbackStarts;
        private long prefillFrames;
        private int highWater;
        private final PcmResampler resampler;
        private final PcmResampler.Sink enqueue = this::enqueueFrame;
        private long resamplerResets;
        private long discardedInput;
        private String error;

        AudioSink(double rate) {
            inputRate = rate;
            resampler = new PcmResampler(rate, OUTPUT_RATE);
        }

        void start() {
            if (track != null || error != null) return;
            // CodexAstraUlt: A failed replacement track must not inherit the
            // released track's PCM totals and count those samples as flushed twice.
            trackWritten = 0;
            trackPlayed = 0;
            startup.reset();
            try {
                int minimum = AudioTrack.getMinBufferSize(OUTPUT_RATE,
                        AudioFormat.CHANNEL_OUT_STEREO, AudioFormat.ENCODING_PCM_16BIT);
                if (minimum <= 0 || minimum > 192000) throw new IllegalStateException("Audio buffer size unavailable");
                track = new AudioTrack.Builder()
                        .setAudioAttributes(new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_GAME)
                                .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC).build())
                        .setAudioFormat(new AudioFormat.Builder().setSampleRate(OUTPUT_RATE)
                                .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                                .setChannelMask(AudioFormat.CHANNEL_OUT_STEREO).build())
                        .setTransferMode(AudioTrack.MODE_STREAM)
                        .setBufferSizeInBytes(Math.max(minimum, OUTPUT_RATE / 10 * 4)).build();
                if (track.getState() != AudioTrack.STATE_INITIALIZED) throw new IllegalStateException("Audio initialization failed");
                if (track.getBufferSizeInFrames() < PREFILL_FRAMES) {
                    throw new IllegalStateException("Audio queue cannot hold startup prefill");
                }
                track.setVolume(0.2f);
                // CodexAstraUlt: The former empty play() call began starving
                // before the first guest frame. Prepare a paused track and start
                // it only after 50 ms of actual guest PCM has been accepted.
                trackPreparations++;
            } catch (Exception failure) {
                error = failure.getClass().getSimpleName();
                pause();
            }
        }

        void accept(short[] samples, int frames, boolean playbackAllowed) {
            generated += frames;
            if (error != null || !playbackAllowed) {
                discardedInput += frames;
                return;
            }
            resampler.accept(samples, frames, enqueue);
            if (track == null) return;
            try {
                for (int attempt = 0; attempt < 2 && count > 0; ++attempt) {
                    int requested = Math.min(count, queue.length - read);
                    int accepted = track.write(queue, read, requested, AudioTrack.WRITE_NON_BLOCKING);
                    if (accepted < 0 || accepted % 2 != 0 || accepted > requested) {
                        throw new IllegalStateException("Audio write failed");
                    }
                    if (accepted < requested) partial++;
                    count -= accepted;
                    read = (read + accepted) % queue.length;
                    written += accepted / 2;
                    trackWritten += accepted / 2;
                    startup.accepted(accepted / 2);
                    if (accepted == 0) break;
                }
                if (startup.ready()) {
                    track.play();
                    prefillFrames += startup.prefillFrames();
                    startup.started();
                    playbackStarts++;
                }
                trackPlayed = Integer.toUnsignedLong(track.getPlaybackHeadPosition());
            } catch (Exception failure) {
                error = failure.getClass().getSimpleName();
                pause();
            }
        }

        private void enqueueFrame(short left, short right) {
            converted++;
            if (count + 2 > queue.length) {
                dropped++;
                return;
            }
            int end = (read + count) % queue.length;
            queue[end] = left;
            queue[(end + 1) % queue.length] = right;
            count += 2;
            highWater = Math.max(highWater, count / 2);
        }

        void pause() {
            if (resampler.inputFrames() != 0) {
                resampler.reset();
                resamplerResets++;
            }
            flushed += count / 2;
            count = 0;
            read = 0;
            startup.reset();
            if (track == null) return;
            try {
                trackPlayed = Integer.toUnsignedLong(track.getPlaybackHeadPosition());
                played += trackPlayed;
                flushed += Math.max(0, trackWritten - trackPlayed);
                underruns += track.getUnderrunCount();
                track.pause();
                track.flush();
                track.stop();
            } catch (Exception failure) {
                error = failure.getClass().getSimpleName();
            } finally {
                track.release();
                track = null;
            }
        }

        boolean failed() { return error != null; }

        JSONObject report() throws JSONException {
            JSONObject value = new JSONObject();
            value.put("status", error == null ? "measured" : "failed");
            value.put("guest_sample_rate", inputRate);
            value.put("output_sample_rate", OUTPUT_RATE);
            value.put("resampler", "stateful-linear");
            value.put("generated_frames", generated);
            value.put("converted_frames", converted);
            value.put("written_frames", written);
            value.put("playback_head_frames", played);
            value.put("dropped_frames", dropped);
            value.put("flushed_frames", flushed);
            value.put("partial_writes", partial);
            value.put("underruns", underruns);
            value.put("queue_high_water_frames", highWater);
            value.put("resampler_resets", resamplerResets);
            value.put("discarded_input_frames", discardedInput);
            // CodexAstraUlt: Actual starts and accepted prefill remain observable;
            // a prepared or paused track alone is never evidence of playback.
            value.put("prefill_target_frames", PREFILL_FRAMES);
            value.put("track_preparations", trackPreparations);
            value.put("playback_starts", playbackStarts);
            value.put("prefill_frames_total", prefillFrames);
            if (error != null) value.put("error", error);
            return value;
        }
    }

    private static native byte[] nativeOpen(String libraries, String scratch, long[] openingToken);
    private static native int nativeFrame(long token, int buttons, int x, int y, boolean touched,
            int[] top, int[] bottom, short[] pcm, long[] metrics);
    private static native void nativePause(long token, boolean paused);
    private static native byte[] nativeReport(long token);
    private static native void nativeClose(long token);
}
