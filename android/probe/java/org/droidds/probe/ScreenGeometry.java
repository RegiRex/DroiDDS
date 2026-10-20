package org.droidds.probe;

/** CodexAstraUlt: Pure letterbox geometry used by drawing and touch mapping, so
 * border/outside behavior can be tested without pretending to run Android. */
final class ScreenGeometry {
    static final class Fit {
        final float left;
        final float top;
        final float width;
        final float height;
        final int guestWidth;
        final int guestHeight;
        Fit(float left, float top, float width, float height, int guestWidth, int guestHeight) {
            this.left = left; this.top = top; this.width = width; this.height = height;
            this.guestWidth = guestWidth; this.guestHeight = guestHeight;
        }
        int[] touch(float x, float y) {
            if (!Float.isFinite(x) || !Float.isFinite(y) || width <= 0 || height <= 0
                    || x < left || y < top || x >= left + width || y >= top + height) return null;
            return new int[] {Math.min(guestWidth - 1, (int)((x - left) * guestWidth / width)),
                    Math.min(guestHeight - 1, (int)((y - top) * guestHeight / height))};
        }
    }
    static Fit fit(int width, int height, int guestWidth, int guestHeight) {
        if (width < 0 || height < 0 || guestWidth <= 0 || guestHeight <= 0) {
            throw new IllegalArgumentException("Invalid screen geometry");
        }
        float scale = Math.min((float)width / guestWidth, (float)height / guestHeight);
        float w = guestWidth * scale, h = guestHeight * scale;
        return new Fit((width - w) / 2, (height - h) / 2, w, h, guestWidth, guestHeight);
    }
    private ScreenGeometry() {}
}
