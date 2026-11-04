package org.droidds.probe;

import android.media.AudioTrack;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import org.json.JSONObject;

/** CodexAstraUlt: Exercise actual queue/adapter code with ordered authored PCM
 * and a controlled nonblocking sink; no device performance claim is made. */
public final class TitleAudioTest {
    private static final double GUEST_RATE = 32728.498046875;
    private static int checks;

    private static void check(boolean condition, String message) {
        checks++;
        if (!condition) throw new AssertionError(message);
    }

    private static void rejects(Runnable action, String message) {
        boolean failed = false;
        try { action.run(); }
        catch (IllegalArgumentException | IllegalStateException expected) { failed = true; }
        check(failed, message);
    }

    // CodexAstraUlt: A deterministic stereo ramp makes stale/reordered samples
    // visible, including both sides of a circular-buffer wrap.
    private static short[] ramp(int start, int frames) {
        short[] result = new short[frames * 2];
        for (int i = 0; i < frames; i++) {
            result[i * 2] = (short)((start + i) * 3 - 17000);
            result[i * 2 + 1] = (short)(16000 - (start + i) * 2);
        }
        return result;
    }

    private static final class Sink implements TitlePcmQueue.Writer {
        final List<Short> output = new ArrayList<>();
        int available, maximum = Integer.MAX_VALUE, calls;
        Sink(int frames) { available = frames; }
        public int write(short[] samples, int offset, int count) {
            calls++;
            int accepted = Math.min(Math.min(count / 2, available), maximum);
            for (int i = 0; i < accepted * 2; i++) output.add(samples[offset + i]);
            available -= accepted;
            return accepted * 2;
        }
    }

    private static List<Short> reference(short[] input, double rate) {
        List<Short> output = new ArrayList<>();
        new PcmResampler(rate, 48000).accept(input, input.length / 2,
                (left, right) -> { output.add(left); output.add(right); });
        return output;
    }

    private static void backpressure() {
        TitlePcmQueue queue = new TitlePcmQueue(GUEST_RATE, 48000, 8192);
        Sink sink = new Sink(4800);
        // CodexAstraUlt: Two maximum legal guest chunks leave old PCM pending
        // while the platform is full. It then consumes 4800 frames before the
        // third <=4096-frame chunk arrives: pre-drain must make room first.
        queue.accept(ramp(0, 4096), 4096, sink);
        check(queue.droppedFrames() == 0 && queue.queuedFrames() > 0, "Initial queue differs");
        queue.accept(ramp(4096, 4096), 4096, sink);
        check(queue.droppedFrames() == 0 && queue.queuedFrames() > 7000, "Backpressure setup differs");
        sink.available = 4800;
        queue.accept(ramp(8192, 3000), 3000, sink);
        check(queue.droppedFrames() == 0,
                "Avoidable overflow with free platform capacity: " + queue.droppedFrames());
        sink.available = 20000;
        queue.accept(new short[0], 0, sink);
        List<Short> expected = reference(ramp(0, 11192), GUEST_RATE);
        check(sink.output.equals(expected), "PCM changed or reordered across queue wrap");
        check(queue.queuedFrames() == 0 && queue.writtenFrames() == expected.size() / 2, "Drain accounting differs");
        check(queue.convertedFrames() == queue.writtenFrames(), "Accepted PCM was lost");
        check(queue.highWaterFrames() <= 8192 && queue.capacityFrames() == 8192, "Queue grew");
    }

    private static void boundedWrites() {
        TitlePcmQueue queue = new TitlePcmQueue(48000, 48000, 8);
        Sink sink = new Sink(100);
        sink.maximum = 2;
        queue.accept(ramp(0, 6), 6, sink);
        check(queue.queuedFrames() == 2 && sink.calls == 2, "Partial writes lost a tail or spun");
        int previous = sink.calls;
        sink.maximum = 0;
        queue.accept(ramp(6, 4), 4, sink);
        check(sink.calls - previous == 2 && queue.queuedFrames() == 6, "Zero writes spun or dropped PCM");
        previous = sink.calls;
        queue.accept(new short[0], 0, sink);
        check(sink.calls - previous == 1 && queue.queuedFrames() == 6, "Empty chunk doubled a blocked drain");
        sink.maximum = 2;
        queue.accept(new short[0], 0, sink);
        sink.maximum = 100;
        queue.accept(new short[0], 0, sink);
        check(sink.output.equals(reference(ramp(0, 10), 48000)), "Partial/zero-write sequence differs");
        check(queue.queuedFrames() == 0 && queue.droppedFrames() == 0, "Valid tails were lost");
        check(queue.partialWrites() > 0 && queue.zeroWrites() == 3, "Write counters differ");

        TitlePcmQueue blocked = new TitlePcmQueue(48000, 48000, 8);
        Sink full = new Sink(0);
        blocked.accept(ramp(0, 12), 12, full);
        check(blocked.queuedFrames() == 8 && blocked.droppedFrames() == 4, "Real overflow was hidden");
        check(blocked.convertedFrames() == blocked.queuedFrames() + blocked.droppedFrames(), "Overflow accounting differs");
    }

    private static void invalidWrites() {
        for (int invalid : new int[] {-1, 1, 100}) {
            TitlePcmQueue queue = new TitlePcmQueue(48000, 48000, 8);
            rejects(() -> queue.accept(ramp(0, 4), 4, (samples, offset, count) -> invalid),
                    "Invalid write result accepted");
            check(queue.writtenFrames() == 0 && queue.queuedFrames() == 4, "Invalid result advanced queue");
            Sink sink = new Sink(8);
            queue.accept(new short[0], 0, sink);
            check(sink.output.equals(reference(ramp(0, 4), 48000)), "Rejected write changed actual PCM");
        }
        TitlePcmQueue queue = new TitlePcmQueue(48000, 48000, 8);
        queue.accept(ramp(0, 6), 6, new Sink(0));
        final int[] attempts = {0};
        rejects(() -> queue.accept(new short[0], 0, (samples, offset, count) -> ++attempts[0] == 1 ? 4 : -1),
                "Partial success then platform failure accepted");
        check(queue.writtenFrames() == 2 && queue.queuedFrames() == 4, "Successful prefix was forgotten");
        long before = queue.convertedFrames();
        Sink unused = new Sink(8);
        rejects(() -> queue.accept(null, 0, unused), "Null input accepted");
        rejects(() -> queue.accept(ramp(0, 1), -1, unused), "Negative input accepted");
        rejects(() -> queue.accept(ramp(0, 1), 2, unused), "Oversize input accepted");
        rejects(() -> queue.accept(ramp(0, 1), 1, null), "Null writer accepted");
        check(unused.calls == 0 && queue.convertedFrames() == before && queue.queuedFrames() == 4,
                "Invalid input drained or advanced state");
    }

    private static void lifecycle() throws Exception {
        TitleAudio audio = new TitleAudio(GUEST_RATE);
        audio.start();
        AudioTrack first = AudioTrack.latest;
        check(first.playCalls == 0, "Empty audio track started");
        audio.accept(ramp(0, 1000), 1000, true);
        check(first.playCalls == 0, "Insufficient accepted prefill started audio");
        audio.accept(ramp(1000, 1000), 1000, true);
        check(first.playCalls == 1, "Accepted prefill did not start audio once");
        first.consume(1000); first.underruns = 7;
        audio.pause();
        JSONObject paused = audio.report();
        check(first.releaseCalls == 1 && first.calls.indexOf("pause") < first.calls.indexOf("head"),
                "Playback was not paused before its final head snapshot");
        check(paused.getLong("underruns") == 7, "Track underruns were not retained");
        check(paused.getLong("flushed_frames") == paused.getLong("written_frames") - 1000,
                "Unplayed platform PCM was miscounted");
        check(paused.getLong("queued_frames") == 0, "Pause retained queued PCM");
        audio.pause();
        check(first.releaseCalls == 1 && audio.report().getLong("underruns") == 7, "Pause double-counted a released track");
        audio.accept(ramp(2000, 10), 10, false);
        check(audio.report().getLong("discarded_input_frames") == 10, "Background input was not separated");
        audio.start();
        AudioTrack second = AudioTrack.latest;
        check(second != first && second.playCalls == 0, "Resume reused a released/playing track");
        audio.accept(ramp(3000, 1000), 1000, true);
        check(second.playCalls == 0, "Resume inherited old prefill");
        audio.accept(ramp(4000, 1000), 1000, true);
        check(second.playCalls == 1, "Resume failed to start after fresh prefill");
        second.underruns = 3;
        audio.pause();
        check(audio.report().getLong("underruns") == 10 && audio.report().getLong("playback_starts") == 2,
                "Per-track totals were lost on resume");
        check("measured".equals(audio.report().getString("status")), "Valid lifecycle reported failure");

        // CodexAstraUlt: The real adapter also traverses the production queue's
        // backpressure correction; the fake sink does not pre-drain for it.
        TitleAudio pressured = new TitleAudio(GUEST_RATE);
        pressured.start();
        AudioTrack hardware = AudioTrack.latest;
        pressured.accept(ramp(0, 4096), 4096, true);
        pressured.accept(ramp(4096, 4096), 4096, true);
        hardware.consume(4800);
        pressured.accept(ramp(8192, 3000), 3000, true);
        check(pressured.report().getLong("dropped_frames") == 0, "Adapter still enqueued before draining");
        pressured.pause();
    }

    private static void cleanupFailures() throws Exception {
        for (String operation : Arrays.asList("pause", "head", "underruns", "flush", "stop", "release")) {
            TitleAudio audio = new TitleAudio(GUEST_RATE);
            audio.start();
            AudioTrack track = AudioTrack.latest;
            track.failures.add(operation);
            audio.pause();
            check(track.releaseCalls == 1, "Cleanup failure skipped release: " + operation);
            check(track.calls.containsAll(Arrays.asList("pause", "head", "underruns", "flush", "stop", "release")),
                    "Cleanup failure skipped later operations: " + operation);
            check("failed".equals(audio.report().getString("status")), "Cleanup failure was hidden: " + operation);
            audio.pause(); audio.start();
            check(track.releaseCalls == 1 && AudioTrack.latest == track, "Failed track was released twice or replaced silently");
        }
        TitleAudio failedWrite = new TitleAudio(GUEST_RATE);
        failedWrite.start();
        AudioTrack broken = AudioTrack.latest;
        broken.failures.add("write"); broken.failures.add("release");
        failedWrite.accept(ramp(0, 100), 100, true);
        check(broken.releaseCalls == 1 && "failed".equals(failedWrite.report().getString("status")),
                "Write/release failure escaped or lost ownership cleanup");
        check(failedWrite.report().getLong("written_frames") == 0
                && failedWrite.report().getLong("flushed_frames") == failedWrite.report().getLong("converted_frames"),
                "Failed write claimed accepted PCM");

        // CodexAstraUlt: The new pre-drain can fail before consuming the new
        // chunk. Its guest frames must be explicitly discarded, while earlier
        // accepted output and queued PCM retain their original accounting.
        TitleAudio failedPreDrain = new TitleAudio(GUEST_RATE);
        failedPreDrain.start();
        AudioTrack blocked = AudioTrack.latest;
        failedPreDrain.accept(ramp(0, 4096), 4096, true);
        failedPreDrain.accept(ramp(4096, 4096), 4096, true);
        long priorConverted = failedPreDrain.report().getLong("converted_frames");
        long priorWritten = failedPreDrain.report().getLong("written_frames");
        blocked.failures.add("write");
        failedPreDrain.accept(ramp(8192, 500), 500, true);
        JSONObject stopped = failedPreDrain.report();
        check(stopped.getLong("discarded_input_frames") == 500, "Failed pre-drain lost incoming guest accounting");
        check(stopped.getLong("resampled_input_frames") == 8192
                && stopped.getLong("generated_frames") == 8692, "Failed pre-drain claimed resampling");
        check(stopped.getLong("converted_frames") == priorConverted
                && stopped.getLong("written_frames") == priorWritten, "Failed pre-drain altered prior PCM totals");
        check(stopped.getLong("flushed_frames") == priorConverted && blocked.releaseCalls == 1,
                "Failed pre-drain did not retain and flush original queued PCM exactly once");
    }

    public static void main(String[] args) throws Exception {
        backpressure(); boundedWrites(); invalidWrites(); lifecycle(); cleanupFailures();
        System.out.println("{\"schema\":1,\"kind\":\"droidds-java-title-audio\",\"status\":\"passed\",\"checks\":"
                + checks + ",\"controls\":[\"backpressure_preserves_pcm_order\",\"bounded_partial_zero_write_queue\","
                + "\"invalid_writes_preserve_accounting\",\"startup_pause_resume_preserves_ownership\","
                + "\"cleanup_failures_release_once\"]}");
    }
}
