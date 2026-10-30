package org.droidds.probe;

/** CodexAstraUlt: The separate title JNI library consumes installer-owned code
 * and fixed caller-owned buffers. Every token operation stays on one worker. */
final class TitleNative {
    private TitleNative() { }
    static void load() { System.loadLibrary("droidds_title_jni"); }
    static native byte[] open(byte[] manifest, String input, String libraries,
            String runtime, boolean nativeMode, long[] openedToken);
    static native int slice(long token, int buttons, float circleX, float circleY,
            float cStickX, float cStickY, int touchX, int touchY, boolean touched,
            int[] top, int[] bottom, short[] pcm, long[] metrics);
    static native void pause(long token, boolean paused);
    static native byte[] report(long token);
    static native void close(long token);
}
