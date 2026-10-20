package org.droidds.probe;

/** CodexAstraUlt: Start playback only after actual guest PCM has been accepted
 * by the platform queue. Generated, rejected or merely converted samples cannot
 * satisfy prefill; every pause starts a fresh queue and a fresh qualification. */
final class AudioStartup {
    private final int target;
    private long accepted;
    private boolean playing;

    AudioStartup(int targetFrames) {
        if (targetFrames <= 0) throw new IllegalArgumentException("Invalid audio prefill");
        target = targetFrames;
    }

    void reset() {
        accepted = 0;
        playing = false;
    }

    void accepted(int frames) {
        if (frames < 0) throw new IllegalArgumentException("Negative accepted PCM");
        if (!playing) accepted += frames;
    }

    boolean ready() { return !playing && accepted >= target; }
    boolean playing() { return playing; }
    long prefillFrames() { return accepted; }

    void started() {
        if (!ready()) throw new IllegalStateException("Audio playback started before prefill");
        playing = true;
    }
}
