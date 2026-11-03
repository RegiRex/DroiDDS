package org.droidds.probe;

import java.util.ArrayDeque;

/** CodexAstraUlt: Preserve button/touch edges in a bounded queue, coalesce
 * movement only, and release every input on pause or controller removal. */
final class TitleInput {
    static final int LIMIT = 64;
    static final class Sample {
        final int buttons, x, y;
        final float circleX, circleY, cStickX, cStickY;
        final boolean touched;
        Sample(int buttons, int x, int y, boolean touched, float cx, float cy, float sx, float sy) {
            this.buttons = buttons; this.x = x; this.y = y; this.touched = touched;
            circleX = cx; circleY = cy; cStickX = sx; cStickY = sy;
        }
    }
    private final ArrayDeque<Sample> queue = new ArrayDeque<>();
    private final int[] sources = new int[3];
    private Sample latest = new Sample(0, 0, 0, false, 0, 0, 0, 0);
    private boolean lastMovement;
    private long overflows;
    // CodexAstraUlt: A cooperative yield is not a new guest input interval.
    // Keep each queued edge until the preceding guest frame has completed.
    private long sampledFrame = Long.MIN_VALUE;

    static float axis(float value, float flat) {
        if (!Float.isFinite(value) || !Float.isFinite(flat)) return 0;
        float deadzone = Math.max(0, Math.min(0.95f, flat));
        float absolute = Math.min(1, Math.abs(value));
        return absolute <= deadzone ? 0 : Math.copySign((absolute - deadzone) / (1 - deadzone), value);
    }

    synchronized void button(int bit, boolean down, int source) {
        if (source < 0 || source >= sources.length) throw new IllegalArgumentException("Input source");
        int next = down ? sources[source] | bit : sources[source] & ~bit;
        if (next == sources[source]) return;
        sources[source] = next;
        // CodexAstraUlt: Two Android sources holding the same guest button
        // do not create extra frame-long edges; retain ownership until both up.
        int combined = sources[0] | sources[1] | sources[2];
        if (combined == latest.buttons) return;
        enqueue(new Sample(combined, latest.x, latest.y,
                latest.touched, latest.circleX, latest.circleY, latest.cStickX, latest.cStickY), false);
    }

    synchronized void touch(int x, int y, boolean down) {
        enqueue(new Sample(latest.buttons, Math.max(0, Math.min(319, x)),
                Math.max(0, Math.min(239, y)), down, latest.circleX, latest.circleY,
                latest.cStickX, latest.cStickY), down && latest.touched);
    }

    synchronized void axes(float cx, float cy, float sx, float sy) {
        enqueue(new Sample(latest.buttons, latest.x, latest.y, latest.touched,
                axis(cx, 0), axis(cy, 0), axis(sx, 0), axis(sy, 0)), true);
    }

    // CodexAstraUlt: One joystick event is one complete hat/axis observation.
    // Separate direction updates could expose opposite buttons together and
    // spread a diagonal change across several guest frames.
    synchronized void motion(int hat, float cx, float cy, float sx, float sy) {
        if ((hat & ~0xf0) != 0) throw new IllegalArgumentException("Hat buttons");
        sources[2] = hat;
        int combined = sources[0] | sources[1] | sources[2];
        float x = axis(cx, 0), y = axis(cy, 0), rx = axis(sx, 0), ry = axis(sy, 0);
        if (combined == latest.buttons && x == latest.circleX && y == latest.circleY
                && rx == latest.cStickX && ry == latest.cStickY) return;
        enqueue(new Sample(combined, latest.x, latest.y, latest.touched, x, y, rx, ry),
                combined == latest.buttons);
    }

    private void enqueue(Sample value, boolean movement) {
        if (movement && lastMovement && !queue.isEmpty()) queue.removeLast();
        if (queue.size() == LIMIT) { queue.clear(); overflows++; }
        queue.addLast(value); latest = value; lastMovement = movement;
    }

    synchronized Sample next(Sample previous) {
        if (queue.isEmpty()) return previous;
        Sample sample = queue.removeFirst();
        if (queue.isEmpty()) lastMovement = false;
        return sample;
    }

    synchronized Sample next(Sample previous, long frame) {
        if (frame < 0) throw new IllegalArgumentException("Guest frame");
        if (sampledFrame == frame) return previous;
        sampledFrame = frame;
        return next(previous);
    }

    synchronized void release() {
        queue.clear();
        sampledFrame = Long.MIN_VALUE;
        for (int i = 0; i < sources.length; i++) sources[i] = 0;
        enqueue(new Sample(0, 0, 0, false, 0, 0, 0, 0), false);
    }

    synchronized long overflows() { return overflows; }
}
