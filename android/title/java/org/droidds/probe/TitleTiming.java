package org.droidds.probe;

/** CodexAstraUlt: Fixed-size timing aggregates classify guest production and
 * host scheduling without a sampling thread or per-frame log. UI lifecycle
 * boundaries close active time immediately, even while the worker is in JNI. */
final class TitleTiming {
    private boolean foreground, userPaused, stopped = true, finished = true, running, active, frameActive;
    private long activeStarted, activeWall, activeEpochs, frameStarted, lastPcm;
    private long workerStarted, workerWall;
    private boolean hasPcm;
    private long nativeCalls, nativeTotal, nativeMaximum;
    private long audioCalls, audioTotal, audioMaximum;
    private long completedFrames, frameTotal, frameMaximum, abandonedFrames;
    private long callbacks, requestedDelay, latenessTotal, latenessMaximum;
    private long pcmSubmissions, pcmGapMaximum;

    // CodexAstraUlt: Start/reset runs on the UI owner before queueing open.
    // Later UI events therefore cannot be overwritten by delayed worker setup.
    synchronized void reset(boolean visible) {
        foreground = visible; userPaused = false; stopped = false; finished = false;
        running = false; active = false; frameActive = false; hasPcm = false;
        activeStarted = activeWall = activeEpochs = frameStarted = lastPcm = 0;
        workerStarted = workerWall = 0;
        nativeCalls = nativeTotal = nativeMaximum = 0;
        audioCalls = audioTotal = audioMaximum = 0;
        completedFrames = frameTotal = frameMaximum = abandonedFrames = 0;
        callbacks = requestedDelay = latenessTotal = latenessMaximum = 0;
        pcmSubmissions = pcmGapMaximum = 0;
    }

    synchronized void foreground(boolean visible, long now) {
        foreground = visible; updateActive(now);
    }

    synchronized void userPaused(boolean paused, long now) {
        userPaused = paused; updateActive(now);
    }

    synchronized void running(boolean value, long now) {
        if (value && finished) return;
        updateWorker(value, now); updateActive(now);
        if (!value) abandonFrame();
    }

    // CodexAstraUlt: A UI stop does not erase the worker's remaining in-flight
    // execution. Keep its full interval as the denominator for guest counters.
    synchronized void requestStop(long now) {
        stopped = true; updateActive(now);
    }

    synchronized void stop(long now) {
        stopped = true; finished = true; updateWorker(false, now); updateActive(now); abandonFrame();
    }

    private void updateWorker(boolean next, long now) {
        if (running == next) return;
        if (running) workerWall = add(workerWall, elapsed(workerStarted, now));
        else workerStarted = now;
        running = next;
    }

    private void updateActive(long now) {
        boolean next = foreground && !userPaused && !stopped && running;
        if (active == next) return;
        if (active) {
            activeWall = add(activeWall, elapsed(activeStarted, now));
            if (hasPcm) pcmGapMaximum = Math.max(pcmGapMaximum, elapsed(lastPcm, now));
        } else {
            activeStarted = now; activeEpochs = add(activeEpochs, 1);
        }
        active = next;
        // CodexAstraUlt: Background time and a resumed prefill must not become
        // a huge apparent producer gap. Measure only after actual guest PCM.
        hasPcm = false;
    }

    synchronized void nativeCall(long start, long end) {
        long duration = elapsed(start, end);
        nativeCalls = add(nativeCalls, 1); nativeTotal = add(nativeTotal, duration);
        nativeMaximum = Math.max(nativeMaximum, duration);
    }

    synchronized void audioSubmit(long start, long end, int frames, boolean acceptedForeground) {
        long duration = elapsed(start, end);
        audioCalls = add(audioCalls, 1); audioTotal = add(audioTotal, duration);
        audioMaximum = Math.max(audioMaximum, duration);
        if (active && acceptedForeground && frames > 0) {
            pcmSubmissions = add(pcmSubmissions, 1);
            if (hasPcm) pcmGapMaximum = Math.max(pcmGapMaximum, elapsed(lastPcm, end));
            lastPcm = end; hasPcm = true;
        }
    }

    // CodexAstraUlt: Only an accepted current-generation callback is observed.
    // Requested pacing sleep is not scheduler lateness; zero-delay yields still
    // expose executor wake latency without inheriting stale pause callbacks.
    synchronized void callback(long queuedAt, long delay, long now) {
        long requested = Math.max(0, delay);
        long waited = elapsed(queuedAt, now);
        long late = waited > requested ? waited - requested : 0;
        callbacks = add(callbacks, 1); requestedDelay = add(requestedDelay, requested);
        latenessTotal = add(latenessTotal, late);
        latenessMaximum = Math.max(latenessMaximum, late);
    }

    synchronized void beginFrame(long now) {
        abandonFrame(); frameStarted = now; frameActive = true;
    }

    synchronized void finishFrame(long now) {
        if (!frameActive) return;
        long duration = elapsed(frameStarted, now);
        completedFrames = add(completedFrames, 1); frameTotal = add(frameTotal, duration);
        frameMaximum = Math.max(frameMaximum, duration); frameActive = false;
    }

    private void abandonFrame() {
        if (frameActive) abandonedFrames = add(abandonedFrames, 1);
        frameActive = false;
    }

    // CodexAstraUlt: Diagnostics never fail gameplay on a reversed observation
    // timestamp or overflow after a very long session. No timestamps are exported.
    private static long elapsed(long before, long after) {
        return after >= before ? after - before : 0;
    }

    private static long add(long total, long amount) {
        return amount > Long.MAX_VALUE - total ? Long.MAX_VALUE : total + amount;
    }

    synchronized Snapshot snapshot(long now) {
        long wall = add(activeWall, active ? elapsed(activeStarted, now) : 0);
        long worker = add(workerWall, running ? elapsed(workerStarted, now) : 0);
        long gap = active && hasPcm ? Math.max(pcmGapMaximum, elapsed(lastPcm, now)) : pcmGapMaximum;
        return new Snapshot(this, wall, worker, gap);
    }

    // CodexAstraUlt: Allocate one immutable aggregate only when exporting a
    // starting/final report; the emulation loop itself creates no timing objects.
    static final class Snapshot {
        final long activeWall, workerWall, activeEpochs, nativeCalls, nativeTotal, nativeMaximum;
        final long audioCalls, audioTotal, audioMaximum, completedFrames, frameTotal, frameMaximum;
        final long abandonedFrames, callbacks, requestedDelay, latenessTotal, latenessMaximum;
        final long pcmSubmissions, pcmGapMaximum;

        private Snapshot(TitleTiming timing, long wall, long worker, long gap) {
            activeWall = wall; workerWall = worker; activeEpochs = timing.activeEpochs;
            nativeCalls = timing.nativeCalls; nativeTotal = timing.nativeTotal; nativeMaximum = timing.nativeMaximum;
            audioCalls = timing.audioCalls; audioTotal = timing.audioTotal; audioMaximum = timing.audioMaximum;
            completedFrames = timing.completedFrames; frameTotal = timing.frameTotal; frameMaximum = timing.frameMaximum;
            abandonedFrames = timing.abandonedFrames; callbacks = timing.callbacks; requestedDelay = timing.requestedDelay;
            latenessTotal = timing.latenessTotal; latenessMaximum = timing.latenessMaximum;
            pcmSubmissions = timing.pcmSubmissions; pcmGapMaximum = gap;
        }
    }
}
