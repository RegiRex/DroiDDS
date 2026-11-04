package android.media;

/** CodexAstraUlt: Test-only format builder for the actual title audio adapter. */
public final class AudioFormat {
    public static final int CHANNEL_OUT_STEREO = 12, ENCODING_PCM_16BIT = 2;
    public static final class Builder {
        public Builder setSampleRate(int value) { return this; }
        public Builder setEncoding(int value) { return this; }
        public Builder setChannelMask(int value) { return this; }
        public AudioFormat build() { return new AudioFormat(); }
    }
}
