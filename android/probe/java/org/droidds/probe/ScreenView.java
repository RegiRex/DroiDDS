package org.droidds.probe;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.view.MotionEvent;
import android.view.View;

/** CodexAstraUlt: Display only the runtime's guest framebuffer. Canvas scales
 * a copied Bitmap; no host-generated triangle or decoration substitutes for it. */
final class ScreenView extends View {
    interface Touch { void update(int x, int y, boolean down); }
    interface Presented { void drawn(long sequence); }
    private final int guestWidth;
    private final int guestHeight;
    private final Bitmap bitmap;
    private final Paint paint = new Paint();
    private final Touch touch;
    private final Presented presented;
    private long sequence;
    private int pointer = -1;

    ScreenView(Context context, int width, int height, Touch target, Presented drawn) {
        super(context);
        guestWidth = width;
        guestHeight = height;
        bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
        touch = target;
        presented = drawn;
        setContentDescription(target == null ? "Guest top display" : "Guest lower touch display");
        setClickable(target != null);
    }

    void pixels(int[] values, long frameSequence) {
        if (values.length != guestWidth * guestHeight) throw new IllegalArgumentException("Wrong framebuffer size");
        bitmap.setPixels(values, 0, guestWidth, 0, 0, guestWidth, guestHeight);
        sequence = frameSequence;
        invalidate();
    }

    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        ScreenGeometry.Fit fit = ScreenGeometry.fit(getWidth(), getHeight(), guestWidth, guestHeight);
        canvas.drawColor(Color.BLACK);
        if (fit.width <= 0 || fit.height <= 0) return;
        canvas.drawBitmap(bitmap, null, new RectF(fit.left, fit.top, fit.left + fit.width,
                fit.top + fit.height), paint);
        if (sequence > 0 && presented != null) presented.drawn(sequence);
    }

    @Override public boolean onTouchEvent(MotionEvent event) {
        if (touch == null) return false;
        int action = event.getActionMasked();
        if (action == MotionEvent.ACTION_DOWN) pointer = event.getPointerId(0);
        if (pointer < 0) return false;
        int index = event.findPointerIndex(pointer);
        boolean up = action == MotionEvent.ACTION_UP || action == MotionEvent.ACTION_CANCEL
                || (action == MotionEvent.ACTION_POINTER_UP
                    && event.getPointerId(event.getActionIndex()) == pointer);
        if (up || index < 0) {
            touch.update(0, 0, false);
            pointer = -1;
            if (action == MotionEvent.ACTION_UP) performClick();
            return true;
        }
        int[] mapped = ScreenGeometry.fit(getWidth(), getHeight(), guestWidth, guestHeight)
                .touch(event.getX(index), event.getY(index));
        touch.update(mapped == null ? 0 : mapped[0], mapped == null ? 0 : mapped[1], mapped != null);
        return true;
    }

    @Override public boolean performClick() { super.performClick(); return true; }
}
