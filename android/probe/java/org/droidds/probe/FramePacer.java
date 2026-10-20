package org.droidds.probe;

/** CodexAstraUlt: Anchor guest frames to monotonic deadlines so executor wake
 * latency does not accumulate into slower emulation and audio starvation.
 * Overload discards only wall-clock debt; every requested guest frame still runs. */
final class FramePacer {
    private final long interval;
    private final long maximumDebt;
    private long deadline;
    private long started;
    private boolean active;
    private boolean ready;
    private long epochs;
    private long frames;
    private long lateFrames;
    private long totalLateness;
    private long maximumLateness;
    private long maximumWork;
    private long resets;

    FramePacer(long intervalNanos, int catchupFrames) {
        if (intervalNanos <= 0 || catchupFrames <= 0
                || intervalNanos > Long.MAX_VALUE / catchupFrames) {
            throw new IllegalArgumentException("Invalid frame pacing bound");
        }
        interval = intervalNanos;
        maximumDebt = intervalNanos * catchupFrames;
    }

    // CodexAstraUlt: Resuming starts a new timeline; time spent in background
    // must never become catch-up work or survive as an active frame measurement.
    void resume(long now) {
        deadline = now;
        active = false;
        ready = true;
        epochs++;
    }

    void begin(long now) {
        if (!ready || active) throw new IllegalStateException("Invalid frame pacing start");
        long late = Math.max(0, now - deadline);
        if (late != 0) lateFrames++;
        totalLateness += late;
        maximumLateness = Math.max(maximumLateness, late);
        started = now;
        active = true;
        frames++;
    }

    long finish(long now) {
        if (!active || now < started) throw new IllegalStateException("Invalid frame pacing finish");
        maximumWork = Math.max(maximumWork, now - started);
        active = false;
        deadline += interval;
        if (now - deadline > maximumDebt) {
            // CodexAstraUlt: A long stall cannot trigger an unbounded burst.
            // Re-anchor the next start now, without dropping guest work/PCM or
            // adding another idle period while the audio queue may be starving.
            deadline = now;
            resets++;
        }
        return Math.max(0, deadline - now);
    }

    long epochs() { return epochs; }
    long frames() { return frames; }
    long lateFrames() { return lateFrames; }
    long totalLateness() { return totalLateness; }
    long maximumLateness() { return maximumLateness; }
    long maximumWork() { return maximumWork; }
    long resets() { return resets; }
}
