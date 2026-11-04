package android.media;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** CodexAstraUlt: Deterministic bounded platform sink for JVM tests. It models
 * capacity and explicit failure injection, never Android timing or a driver. */
public final class AudioTrack {
    public static final int MODE_STREAM = 1, STATE_INITIALIZED = 1, WRITE_NON_BLOCKING = 1;
    public static AudioTrack latest;
    public final List<String> calls = new ArrayList<>();
    public final Set<String> failures = new HashSet<>();
    public int releaseCalls, playCalls, written, played, underruns;
    public boolean playing;
    private final int capacity;
    private int available;

    private AudioTrack(int frames) { capacity = frames; available = frames; latest = this; }

    public static int getMinBufferSize(int rate, int channels, int encoding) { return 19200; }
    public int getState() { return STATE_INITIALIZED; }
    public int getBufferSizeInFrames() { return capacity; }

    private void called(String operation) {
        calls.add(operation);
        if (failures.contains(operation)) throw new IllegalStateException("Injected " + operation);
    }

    public int write(short[] samples, int offset, int count, int mode) {
        called("write");
        if (mode != WRITE_NON_BLOCKING || offset < 0 || count < 0 || offset + count > samples.length) {
            throw new AssertionError("Invalid platform write");
        }
        int accepted = Math.min(count / 2, available);
        written += accepted; available -= accepted;
        return accepted * 2;
    }

    public void consume(int frames) {
        if (!playing) return;
        int consumed = Math.min(frames, capacity - available);
        available += consumed; played += consumed;
    }

    public void play() { called("play"); playCalls++; playing = true; }
    public void pause() { called("pause"); playing = false; }
    public int getPlaybackHeadPosition() { called("head"); return played; }
    public int getUnderrunCount() { called("underruns"); return underruns; }
    public void flush() { called("flush"); available = capacity; }
    public void stop() { called("stop"); playing = false; }
    public void release() { releaseCalls++; called("release"); }

    public static final class Builder {
        private int bytes;
        public Builder setAudioAttributes(AudioAttributes value) { return this; }
        public Builder setAudioFormat(AudioFormat value) { return this; }
        public Builder setTransferMode(int value) { return this; }
        public Builder setBufferSizeInBytes(int value) { bytes = value; return this; }
        public AudioTrack build() { return new AudioTrack(bytes / 4); }
    }
}
