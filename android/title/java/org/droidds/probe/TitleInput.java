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
        enqueue(new Sample(sources[0] | sources[1] | sources[2], latest.x, latest.y,
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

    synchronized void release() {
        queue.clear();
        for (int i = 0; i < sources.length; i++) sources[i] = 0;
        enqueue(new Sample(0, 0, 0, false, 0, 0, 0, 0), false);
    }

    synchronized long overflows() { return overflows; }
}
