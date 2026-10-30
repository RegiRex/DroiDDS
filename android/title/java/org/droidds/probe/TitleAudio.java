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
    private final short[] queue = new short[8192 * 2];
    private final PcmResampler resampler;
    private final AudioStartup startup = new AudioStartup(RATE / 20);
    private final double inputRate;
    private AudioTrack track;
    private int read, count;
    private long generated, converted, written, dropped, discardedInput, flushed, underruns;
    private long trackWritten, trackPlayed, starts;
    private String error;
    private final PcmResampler.Sink enqueue = this::enqueueFrame;

    TitleAudio(double rate) { inputRate = rate; resampler = new PcmResampler(rate, RATE); }

    void start() {
        if (track != null || error != null) return;
        trackWritten = 0; trackPlayed = 0; startup.reset();
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
        if (frames < 0 || frames > pcm.length / 2) throw new IllegalArgumentException("PCM frame count");
        generated += frames;
        if (!foreground || error != null || track == null) { discardedInput += frames; return; }
        resampler.accept(pcm, frames, enqueue);
        try {
            for (int attempt = 0; attempt < 2 && count > 0; attempt++) {
                int requested = Math.min(count, queue.length - read);
                int accepted = track.write(queue, read, requested, AudioTrack.WRITE_NON_BLOCKING);
                if (accepted < 0 || accepted > requested || accepted % 2 != 0) {
                    throw new IllegalStateException("Audio write failed");
                }
                count -= accepted; read = (read + accepted) % queue.length;
                written += accepted / 2; trackWritten += accepted / 2;
                startup.accepted(accepted / 2);
                if (accepted == 0) break;
            }
            if (startup.ready()) { track.play(); startup.started(); starts++; }
            trackPlayed = Integer.toUnsignedLong(track.getPlaybackHeadPosition());
        } catch (RuntimeException failure) { error = failure.getClass().getSimpleName(); pause(); }
    }

    private void enqueueFrame(short left, short right) {
        converted++;
        if (count + 2 > queue.length) { dropped++; return; }
        int end = (read + count) % queue.length;
        queue[end] = left; queue[(end + 1) % queue.length] = right; count += 2;
    }

    void pause() {
        resampler.reset(); startup.reset();
        flushed += count / 2; count = 0; read = 0;
        if (track == null) return;
        try {
            trackPlayed = Integer.toUnsignedLong(track.getPlaybackHeadPosition());
            flushed += Math.max(0, trackWritten - trackPlayed);
            underruns += track.getUnderrunCount();
            track.pause(); track.flush(); track.stop();
        } catch (RuntimeException failure) { error = failure.getClass().getSimpleName(); }
        finally { track.release(); track = null; }
    }

    JSONObject report() throws JSONException {
        return new JSONObject().put("status", error == null ? "measured" : "failed")
                .put("error", error == null ? JSONObject.NULL : error)
                .put("guest_sample_rate", inputRate).put("output_sample_rate", RATE)
                .put("generated_frames", generated).put("converted_frames", converted)
                .put("written_frames", written).put("dropped_frames", dropped)
                .put("discarded_input_frames", discardedInput)
                .put("flushed_frames", flushed).put("underruns", underruns).put("playback_starts", starts);
    }
}
