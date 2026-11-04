package org.droidds.probe;

/** CodexAstraUlt: A fixed stereo queue retains actual resampled guest PCM.
 * Drain old samples before accepting a new chunk to reclaim available platform
 * space before the new chunk can overflow. All writes remain nonblocking. */
final class TitlePcmQueue {
    interface Writer { int write(short[] samples, int offset, int count); }

    private final short[] samples;
    private final PcmResampler resampler;
    private final PcmResampler.Sink enqueue = this::enqueueFrame;
    private int read, count, highWater;
    private long resampledInput, converted, written, dropped, partialWrites, zeroWrites;

    TitlePcmQueue(double inputRate, int outputRate, int capacityFrames) {
        if (capacityFrames <= 0 || capacityFrames > 8192) {
            throw new IllegalArgumentException("Invalid bounded PCM capacity");
        }
        samples = new short[capacityFrames * 2];
        resampler = new PcmResampler(inputRate, outputRate);
    }

    void accept(short[] input, int frames, Writer writer) {
        if (input == null || frames < 0 || frames > input.length / 2 || writer == null) {
            throw new IllegalArgumentException("Invalid PCM queue input");
        }
        // CodexAstraUlt: The old enqueue-first order discarded incoming PCM
        // before reclaiming platform space. Preserve old/new ordering by
        // draining the existing queue first, then enqueueing and draining again.
        drain(writer);
        if (frames != 0) {
            resampler.accept(input, frames, enqueue);
            resampledInput += frames;
            drain(writer);
        }
    }

    private void drain(Writer writer) {
        // CodexAstraUlt: Two contiguous segments cover a wrapped queue. A
        // partial or zero write never spins or discards its unaccepted tail.
        for (int attempt = 0; attempt < 2 && count > 0; attempt++) {
            int requested = Math.min(count, samples.length - read);
            int accepted = writer.write(samples, read, requested);
            if (accepted < 0 || accepted > requested || (accepted & 1) != 0) {
                throw new IllegalStateException("Audio write failed");
            }
            if (accepted < requested) partialWrites++;
            if (accepted == 0) zeroWrites++;
            count -= accepted;
            read = (read + accepted) % samples.length;
            written += accepted / 2;
            if (accepted == 0) break;
        }
    }

    private void enqueueFrame(short left, short right) {
        converted++;
        if (count + 2 > samples.length) { dropped++; return; }
        int end = (read + count) % samples.length;
        samples[end] = left;
        samples[(end + 1) % samples.length] = right;
        count += 2;
        highWater = Math.max(highWater, count / 2);
    }

    // CodexAstraUlt: Pause discards only this queue and interpolation history;
    // cumulative loss/write counters survive for the final session report.
    int flush() {
        int frames = count / 2;
        read = 0; count = 0; resampler.reset();
        return frames;
    }

    long resampledInputFrames() { return resampledInput; }
    long convertedFrames() { return converted; }
    long writtenFrames() { return written; }
    long droppedFrames() { return dropped; }
    long partialWrites() { return partialWrites; }
    long zeroWrites() { return zeroWrites; }
    int queuedFrames() { return count / 2; }
    int highWaterFrames() { return highWater; }
    int capacityFrames() { return samples.length / 2; }
}
