package org.droidds.probe;

import android.media.AudioAttributes;
import android.media.AudioFormat;
import android.media.AudioTrack;
import org.json.JSONException;
import org.json.JSONObject;

/** CodexAstraUlt: Reuse tested PCM interpolation and startup policy. Audio
 * consumes actual guest samples on the owning worker with a fixed queue;
 * unavailable audio is reported without replacing guest execution or PCM. */
final class TitleAudio {
    private static final int RATE = 48000;
    private final TitlePcmQueue queue;
    private final AudioStartup startup = new AudioStartup(RATE / 20);
    private final double inputRate;
    private AudioTrack track;
    private long generated, discardedInput, flushed, underruns;
    private long trackWrittenStart, starts;
    private String error;
    // CodexAstraUlt: One reusable callback avoids allocating per-slice writers.
    private final TitlePcmQueue.Writer output = (samples, offset, count) ->
            track.write(samples, offset, count, AudioTrack.WRITE_NON_BLOCKING);

    TitleAudio(double rate) { inputRate = rate; queue = new TitlePcmQueue(rate, RATE, 8192); }

    void start() {
        if (track != null || error != null) return;
        trackWrittenStart = queue.writtenFrames(); startup.reset();
        try {
            int minimum = AudioTrack.getMinBufferSize(RATE, AudioFormat.CHANNEL_OUT_STEREO,
                    AudioFormat.ENCODING_PCM_16BIT);
            if (minimum <= 0 || minimum > 192000) throw new IllegalStateException("Audio buffer unavailable");
            track = new AudioTrack.Builder()
                    .setAudioAttributes(new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_GAME)
                            .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC).build())
                    .setAudioFormat(new AudioFormat.Builder().setSampleRate(RATE)
                            .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                            .setChannelMask(AudioFormat.CHANNEL_OUT_STEREO).build())
                    .setTransferMode(AudioTrack.MODE_STREAM)
                    .setBufferSizeInBytes(Math.max(minimum, RATE / 10 * 4)).build();
            if (track.getState() != AudioTrack.STATE_INITIALIZED || track.getBufferSizeInFrames() < RATE / 20) {
                throw new IllegalStateException("Audio initialization failed");
            }
        } catch (RuntimeException failure) { error = failure.getClass().getSimpleName(); pause(); }
    }

    void accept(short[] pcm, int frames, boolean foreground) {
        if (pcm == null || frames < 0 || frames > pcm.length / 2) throw new IllegalArgumentException("PCM frame count");
        generated += frames;
        if (!foreground || error != null || track == null) { discardedInput += frames; return; }
        long beforeInput = queue.resampledInputFrames();
        try {
            // CodexAstraUlt: Pre-drain preserves PCM under backpressure without
            // increasing queue capacity or replacing missing guest samples.
            long before = queue.writtenFrames();
            queue.accept(pcm, frames, output);
            startup.accepted((int)(queue.writtenFrames() - before));
            if (startup.ready()) { track.play(); startup.started(); starts++; }
            // CodexAstraUlt: Playback position is needed only when closing a
            // track; remove the unused per-slice platform query.
        } catch (RuntimeException failure) {
            // CodexAstraUlt: A failed pre-drain has not consumed this new guest
            // chunk. Keep that input explicitly discarded rather than losing it
            // between generated-input and converted-output accounting.
            discardedInput += frames - (queue.resampledInputFrames() - beforeInput);
            error = failure.getClass().getSimpleName(); pause();
        }
    }

    void pause() {
        startup.reset();
        flushed += queue.flush();
        if (track == null) return;
        // CodexAstraUlt: Detach ownership before platform cleanup so failures,
        // including release(), cannot leave a stale track or escape native
        // teardown. Each cleanup operation still gets its own attempt.
        AudioTrack closing = track;
        track = null;
        try {
            closing.pause();
        } catch (RuntimeException failure) { recordError(failure); }
        try {
            long played = Integer.toUnsignedLong(closing.getPlaybackHeadPosition());
            flushed += Math.max(0, queue.writtenFrames() - trackWrittenStart - played);
        } catch (RuntimeException failure) { recordError(failure); }
        try { underruns += closing.getUnderrunCount(); }
        catch (RuntimeException failure) { recordError(failure); }
        try { closing.flush(); }
        catch (RuntimeException failure) { recordError(failure); }
        try { closing.stop(); }
        catch (RuntimeException failure) { recordError(failure); }
        try { closing.release(); }
        catch (RuntimeException failure) { recordError(failure); }
    }

    private void recordError(RuntimeException failure) {
        if (error == null) error = failure.getClass().getSimpleName();
    }

    JSONObject report() throws JSONException {
        return new JSONObject().put("status", error == null ? "measured" : "failed")
                .put("error", error == null ? JSONObject.NULL : error)
                .put("guest_sample_rate", inputRate).put("output_sample_rate", RATE)
                .put("resampled_input_frames", queue.resampledInputFrames())
                .put("generated_frames", generated).put("converted_frames", queue.convertedFrames())
                .put("written_frames", queue.writtenFrames()).put("dropped_frames", queue.droppedFrames())
                .put("discarded_input_frames", discardedInput)
                .put("flushed_frames", flushed).put("underruns", underruns).put("playback_starts", starts)
                .put("queue_capacity_frames", queue.capacityFrames()).put("queued_frames", queue.queuedFrames())
                .put("queue_high_water_frames", queue.highWaterFrames())
                .put("partial_writes", queue.partialWrites()).put("zero_writes", queue.zeroWrites());
    }
}
