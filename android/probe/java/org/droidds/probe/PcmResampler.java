package org.droidds.probe;

/** CodexAstraUlt: Pure streaming stereo interpolation, independent of Android.
 * State survives chunk boundaries; reset discards history at a paused/flush boundary. */
final class PcmResampler {
    interface Sink { void frame(short left, short right); }
    private final double step;
    private long inputs;
    private long outputs;
    private double next;
    private short left;
    private short right;

    PcmResampler(double inputRate, int outputRate) {
        if (!Double.isFinite(inputRate) || inputRate <= 0 || outputRate <= 0
                || inputRate / outputRate < 0.125 || inputRate / outputRate > 8) {
            throw new IllegalArgumentException("Unsupported bounded PCM rate ratio");
        }
        step = inputRate / outputRate;
    }

    void accept(short[] samples, int frames, Sink sink) {
        if (samples == null || frames < 0 || frames > samples.length / 2 || sink == null) {
            throw new IllegalArgumentException("Invalid stereo PCM input");
        }
        for (int i = 0; i < frames; ++i) {
            short currentLeft = samples[i * 2];
            short currentRight = samples[i * 2 + 1];
            long index = inputs++;
            if (index == 0) { left = currentLeft; right = currentRight; }
            while (next <= index) {
                double fraction = index == 0 ? 1 : Math.max(0, Math.min(1, next - (index - 1)));
                sink.frame((short)Math.round(left + (currentLeft - left) * fraction),
                        (short)Math.round(right + (currentRight - right) * fraction));
                outputs++;
                next += step;
            }
            left = currentLeft;
            right = currentRight;
        }
    }

    void reset() { inputs = 0; outputs = 0; next = 0; left = 0; right = 0; }
    long inputFrames() { return inputs; }
    long outputFrames() { return outputs; }
}
