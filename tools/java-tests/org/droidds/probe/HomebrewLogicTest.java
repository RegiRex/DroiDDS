package org.droidds.probe;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** CodexAstraUlt: Execute real frontend math on a host JVM. These independent
 * waveform/geometry oracles do not pretend to exercise Android playback or Views. */
public final class HomebrewLogicTest {
    private static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }

    private static List<Short> convert(PcmResampler resampler, short[] input, int chunk) {
        List<Short> result = new ArrayList<>();
        PcmResampler.Sink sink = (left, right) -> { result.add(left); result.add(right); };
        for (int frame = 0; frame < input.length / 2; frame += chunk) {
            int stop = Math.min(frame + chunk, input.length / 2);
            short[] part = Arrays.copyOfRange(input, frame * 2, stop * 2);
            resampler.accept(part, stop - frame, sink);
        }
        return result;
    }

    private static short[] ramp(int frames) {
        short[] result = new short[frames * 2];
        for (int i = 0; i < frames; i++) {
            result[i * 2] = (short)(i * 20 - 10000);
            result[i * 2 + 1] = (short)(10000 - i * 20);
        }
        return result;
    }

    private static void waveformOracle() {
        // CodexAstraUlt: A linear signal remains linear after interpolation;
        // expected samples come from absolute signal time, not adapter state.
        final double rate = 32728.498046875;
        final int frames = 1001;
        PcmResampler resampler = new PcmResampler(rate, 48000);
        List<Short> result = convert(resampler, ramp(frames), frames);
        int expected = (int)Math.floor((frames - 1) * 48000 / rate) + 1;
        check(result.size() == expected * 2, "Resampled duration differs from source time");
        check(resampler.inputFrames() == frames && resampler.outputFrames() == expected,
                "Actual rate counters disagree");
        for (int i = 0; i < expected; i++) {
            double at = i * rate / 48000;
            check(Math.abs(result.get(i * 2) - Math.round(-10000 + at * 20)) <= 1,
                    "Left-channel linear signal differs");
            check(Math.abs(result.get(i * 2 + 1) - Math.round(10000 - at * 20)) <= 1,
                    "Right-channel linear signal differs");
        }
    }

    private static void streamingAndReset() {
        short[] input = ramp(1001);
        List<Short> whole = convert(new PcmResampler(32728.498046875, 48000), input, 1001);
        for (int chunk : new int[] {1, 7, 160, 480, 640}) {
            PcmResampler resampler = new PcmResampler(32728.498046875, 48000);
            check(whole.equals(convert(resampler, input, chunk)), "Chunk boundary changed PCM");
            resampler.reset();
            check(resampler.inputFrames() == 0 && resampler.outputFrames() == 0, "Pause reset retained counters");
            check(whole.equals(convert(resampler, input, 53)), "Pause reset retained stale waveform history");
        }
    }

    private static void clippingAndInvalidInput() {
        List<Short> result = convert(new PcmResampler(6000, 48000),
                new short[] {Short.MIN_VALUE, Short.MAX_VALUE, Short.MAX_VALUE, Short.MIN_VALUE}, 1);
        check(result.size() == 18, "Eight-times interpolation rate differs");
        check(result.get(0) == Short.MIN_VALUE && result.get(1) == Short.MAX_VALUE,
                "Full-scale initial sample changed");
        check(result.get(16) == Short.MAX_VALUE && result.get(17) == Short.MIN_VALUE,
                "Full-scale final sample wrapped");
        for (double rate : new double[] {Double.NaN, Double.POSITIVE_INFINITY, 0, -1, 1}) {
            boolean rejected = false;
            try { new PcmResampler(rate, 48000); } catch (IllegalArgumentException expected) { rejected = true; }
            check(rejected, "Unsupported rate accepted");
        }
        PcmResampler resampler = new PcmResampler(32728.498046875, 48000);
        boolean rejected = false;
        try { resampler.accept(new short[2], 2, (left, right) -> {}); }
        catch (IllegalArgumentException expected) { rejected = true; }
        check(rejected && resampler.inputFrames() == 0 && resampler.outputFrames() == 0,
                "Invalid buffer consumed samples");
    }

    private static void letterboxOracle() {
        ScreenGeometry.Fit fit = ScreenGeometry.fit(600, 600, 320, 240);
        check(fit.left == 0 && fit.top == 75 && fit.width == 600 && fit.height == 450,
                "Bottom-screen aspect ratio or letterbox differs");
        check(Arrays.equals(fit.touch(0, 75), new int[] {0, 0}), "Origin mapping differs");
        check(Arrays.equals(fit.touch(300, 300), new int[] {160, 120}), "Center mapping differs");
        check(Arrays.equals(fit.touch(599.9f, 524.9f), new int[] {319, 239}), "Last pixel differs");
        for (float[] point : new float[][] {{-1, 75}, {600, 75}, {0, 74.9f}, {0, 525},
                {Float.NaN, 300}, {300, Float.POSITIVE_INFINITY}}) {
            check(fit.touch(point[0], point[1]) == null, "Letterbox/nonfinite touch entered guest screen");
        }
        check(ScreenGeometry.fit(0, 600, 320, 240).touch(0, 300) == null, "Empty view accepted touch");
        ScreenGeometry.Fit landscape = ScreenGeometry.fit(800, 300, 320, 240);
        check(Arrays.equals(landscape.touch(400, 150), new int[] {160, 120}),
                "Rotation/resize changed guest center mapping");
    }

    private static void deadlineOracle() {
        // CodexAstraUlt: An independent absolute timeline injects a different
        // wake delay on each frame. Relative-delay scheduling would accumulate
        // those delays and fail this duration check even with short frame work.
        final long period = 1000000L;
        FramePacer pacer = new FramePacer(period, 4);
        pacer.resume(0);
        long now = 0;
        for (int i = 0; i < 1000; i++) {
            pacer.begin(now);
            long finished = now + period / 5;
            long delay = pacer.finish(finished);
            check(finished + delay == (i + 1) * period, "Scheduler jitter accumulated into guest slowdown");
            now = finished + delay + (i % 7) * 1000;
        }
        check(pacer.frames() == 1000 && pacer.resets() == 0 && pacer.lateFrames() > 0,
                "Normal jitter changed frame count or reset the clock");
        check(pacer.maximumLateness() == 6000 && pacer.maximumWork() == period / 5,
                "Measured wake lateness/work differs from injected timing");

        // CodexAstraUlt: Modest stalls catch up with real frames; a long stall
        // abandons bounded wall-clock debt without inventing completed frames.
        FramePacer loaded = new FramePacer(period, 4);
        loaded.resume(0);
        loaded.begin(0);
        check(loaded.finish(2 * period) == 0 && loaded.resets() == 0,
                "Short overload did not allow bounded catch-up");
        loaded.begin(2 * period);
        check(loaded.finish(2 * period + period / 5) == 0, "Catch-up inserted a relative wait");
        loaded.begin(2 * period + period / 5);
        check(loaded.finish(2 * period + 2 * period / 5) == 3 * period / 5,
                "Catch-up did not return to the original timeline");
        loaded.begin(3 * period);
        check(loaded.finish(20 * period) == 0 && loaded.resets() == 1 && loaded.frames() == 4,
                "Long overload accumulated unbounded debt or skipped guest frames");
        loaded.begin(20 * period);
        check(loaded.finish(20 * period + period / 5) == period * 4 / 5 && loaded.resets() == 1,
                "Overload reset added idle time or retained the old catch-up debt");
    }

    private static void pacingResumeOracle() {
        // CodexAstraUlt: A background interval must not generate frame debt.
        FramePacer pacer = new FramePacer(1000, 4);
        pacer.resume(100);
        pacer.begin(100);
        check(pacer.finish(300) == 800, "Initial pacing differs");
        pacer.resume(1000000000);
        pacer.begin(1000000000);
        check(pacer.finish(1000000200) == 800 && pacer.resets() == 0 && pacer.epochs() == 2,
                "Paused wall time leaked into the resumed timeline");
        check(pacer.frames() == 2 && pacer.maximumLateness() == 0,
                "Resume invented catch-up frames or lateness");
    }

    private static void prefillOracle() {
        // CodexAstraUlt: Model platform partial writes, including a full queue
        // accepting zero bytes. Only accepted guest samples may start playback.
        AudioStartup startup = new AudioStartup(2400);
        check(!startup.ready() && !startup.playing(), "Empty track was ready to play");
        boolean rejected = false;
        try { startup.started(); } catch (IllegalStateException expected) { rejected = true; }
        check(rejected, "Empty playback was allowed");
        for (int accepted : new int[] {800, 0, 400, 1199}) startup.accepted(accepted);
        check(!startup.ready() && startup.prefillFrames() == 2399, "Partial writes invented prefill");
        startup.accepted(1);
        check(startup.ready(), "Accepted threshold did not permit playback");
        startup.started();
        startup.accepted(10000);
        check(startup.playing() && !startup.ready() && startup.prefillFrames() == 2400,
                "Started track was counted again or prefill changed");
        startup.reset();
        startup.accepted(800);
        check(!startup.ready() && !startup.playing() && startup.prefillFrames() == 800,
                "Pause retained prefill from the released platform queue");
        startup.reset(); // CodexAstraUlt: Pause during prefill also clears ownership.
        startup.accepted(3200);
        check(startup.ready() && startup.prefillFrames() == 3200, "Whole guest frame crossing threshold was lost");
    }

    public static void main(String[] args) {
        waveformOracle();
        streamingAndReset();
        clippingAndInvalidInput();
        letterboxOracle();
        deadlineOracle();
        pacingResumeOracle();
        prefillOracle();
        System.out.println("{\"schema\":1,\"kind\":\"droidds-java-homebrew-logic\",\"status\":\"passed\","
                + "\"controls\":[\"time_based_pcm_oracle\",\"chunk_and_pause_continuity\","
                + "\"full_scale_and_invalid_pcm\",\"letterbox_touch_and_resize\","
                + "\"absolute_deadline_jitter_and_overload\",\"pause_resets_frame_timeline\","
                + "\"guest_pcm_prefill_and_partial_writes\"]}");
    }
    private HomebrewLogicTest() {}
}
