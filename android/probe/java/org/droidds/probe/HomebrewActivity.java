package org.droidds.probe;

import android.app.Activity;
import android.hardware.input.InputManager;
import android.os.Bundle;
import android.view.InputDevice;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.LinearLayout;
import android.widget.TextView;

/** CodexAstraUlt: Manual presentation/input/audio observations for the original
 * guest. Both guest screens share this Android display; no second physical
 * display or retail-game compatibility is implied. */
public final class HomebrewActivity extends Activity implements HomebrewController.Observer,
        InputManager.InputDeviceListener {
    private HomebrewController controller;
    private String sessionId;
    private TextView status;
    private ScreenView top;
    private ScreenView bottom;
    private InputManager inputManager;

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        controller = HomebrewController.get(getApplicationContext());
        sessionId = getIntent().getStringExtra("session_id");
        if (!controller.matches(sessionId)) { finish(); return; }
        inputManager = (InputManager)getSystemService(INPUT_SERVICE);
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setFitsSystemWindows(true);
        int padding = Math.round(8 * getResources().getDisplayMetrics().density);
        content.setPadding(padding, padding, padding, padding);
        TextView help = new TextView(this);
        help.setText("Original homebrew: use your D-pad and A button, then touch the lower screen. "
                + "Listen for its tone. Briefly switch apps and return to test pause/resume.");
        content.addView(help);
        status = new TextView(this);
        content.addView(status);
        LinearLayout screens = new LinearLayout(this);
        screens.setOrientation(LinearLayout.VERTICAL);
        top = new ScreenView(this, 400, 240, null,
                sequence -> controller.canvasDrawn(sessionId, true, sequence));
        bottom = new ScreenView(this, 320, 240, (x, y, down) -> controller.touch(x, y, down),
                sequence -> controller.canvasDrawn(sessionId, false, sequence));
        screens.addView(top, new LinearLayout.LayoutParams(-1, 0, 1));
        screens.addView(bottom, new LinearLayout.LayoutParams(-1, 0, 1));
        content.addView(screens, new LinearLayout.LayoutParams(-1, 0, 1));
        // CodexAstraUlt: Touch buttons are a useful fallback but are counted
        // separately; they cannot qualify physical-controller input.
        LinearLayout controls = new LinearLayout(this);
        addControl(controls, "←", 1 << 5);
        addControl(controls, "↑", 1 << 6);
        addControl(controls, "↓", 1 << 7);
        addControl(controls, "→", 1 << 4);
        addControl(controls, "A", 1);
        addControl(controls, "B", 1 << 1);
        content.addView(controls);
        CheckBox display = new CheckBox(this);
        display.setText("I can see both guest screens");
        display.setChecked(controller.displayConfirmed());
        display.setOnCheckedChangeListener((button, checked) -> controller.confirmDisplay(checked));
        content.addView(display);
        CheckBox sound = new CheckBox(this);
        sound.setText("I heard the guest's tone");
        sound.setChecked(controller.audioConfirmed());
        sound.setOnCheckedChangeListener((button, checked) -> controller.confirmAudio(checked));
        content.addView(sound);
        Button stop = new Button(this);
        stop.setText("Stop and save session");
        stop.setOnClickListener(view -> controller.stop(sessionId, "stop_button"));
        content.addView(stop);
        setContentView(content);
    }

    private void addControl(LinearLayout row, String label, int mask) {
        Button button = new Button(this);
        button.setText(label);
        button.setMinWidth(0);
        button.setMinimumWidth(0);
        button.setOnTouchListener((view, event) -> {
            int action = event.getActionMasked();
            if (action == MotionEvent.ACTION_DOWN) controller.button(mask, true, 0);
            if (action == MotionEvent.ACTION_UP || action == MotionEvent.ACTION_CANCEL) {
                controller.button(mask, false, 0);
                if (action == MotionEvent.ACTION_UP) view.performClick();
            }
            return true;
        });
        row.addView(button, new LinearLayout.LayoutParams(0, -2, 1));
    }

    @Override protected void onStart() {
        super.onStart();
        if (controller != null) controller.observe(sessionId, this);
    }

    @Override protected void onResume() {
        super.onResume();
        if (controller != null) controller.setForeground(sessionId, true);
        if (inputManager != null) inputManager.registerInputDeviceListener(this, null);
    }

    @Override protected void onPause() {
        if (controller != null) controller.setForeground(sessionId, false);
        if (inputManager != null) inputManager.unregisterInputDeviceListener(this);
        super.onPause();
    }

    @Override protected void onStop() {
        if (controller != null) controller.removeObserver(this);
        super.onStop();
    }

    @Override public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (!hasFocus && controller != null) controller.releaseInputs();
    }

    // CodexAstraUlt: This Activity uses the framework's legacy back hook, with
    // predictive callbacks disabled in its manifest. Back saves/closes on the
    // owning worker before finishing; it never abandons a live native session.
    @Override @SuppressWarnings("deprecation") public void onBackPressed() {
        if (controller != null) controller.stop(sessionId, "back_button");
        else finish();
    }

    @Override public boolean dispatchKeyEvent(KeyEvent event) {
        int bit = keyBit(event.getKeyCode());
        if (bit != 0 && controller != null
                && (event.getAction() == KeyEvent.ACTION_DOWN || event.getAction() == KeyEvent.ACTION_UP)) {
            InputDevice device = event.getDevice();
            boolean gamepad = device != null && !device.isVirtual()
                    && ((device.getSources() & InputDevice.SOURCE_GAMEPAD) == InputDevice.SOURCE_GAMEPAD
                        || (device.getSources() & InputDevice.SOURCE_JOYSTICK) == InputDevice.SOURCE_JOYSTICK);
            controller.button(bit, event.getAction() == KeyEvent.ACTION_DOWN, gamepad ? 1 : 2);
            return true;
        }
        return super.dispatchKeyEvent(event);
    }

    private static int keyBit(int code) {
        switch (code) {
            case KeyEvent.KEYCODE_BUTTON_A: return 1;
            case KeyEvent.KEYCODE_BUTTON_B: return 1 << 1;
            case KeyEvent.KEYCODE_BUTTON_SELECT: return 1 << 2;
            case KeyEvent.KEYCODE_BUTTON_START: return 1 << 3;
            case KeyEvent.KEYCODE_DPAD_RIGHT: return 1 << 4;
            case KeyEvent.KEYCODE_DPAD_LEFT: return 1 << 5;
            case KeyEvent.KEYCODE_DPAD_UP: return 1 << 6;
            case KeyEvent.KEYCODE_DPAD_DOWN: return 1 << 7;
            case KeyEvent.KEYCODE_BUTTON_R1: return 1 << 8;
            case KeyEvent.KEYCODE_BUTTON_L1: return 1 << 9;
            case KeyEvent.KEYCODE_BUTTON_X: return 1 << 10;
            case KeyEvent.KEYCODE_BUTTON_Y: return 1 << 11;
            case KeyEvent.KEYCODE_BUTTON_L2: return 1 << 14;
            case KeyEvent.KEYCODE_BUTTON_R2: return 1 << 15;
            default: return 0;
        }
    }

    @Override public boolean onGenericMotionEvent(MotionEvent event) {
        InputDevice device = event.getDevice();
        if (controller != null && device != null && !device.isVirtual()
                && (event.getSource() & InputDevice.SOURCE_JOYSTICK) == InputDevice.SOURCE_JOYSTICK) {
            float x = event.getAxisValue(MotionEvent.AXIS_HAT_X);
            float y = event.getAxisValue(MotionEvent.AXIS_HAT_Y);
            if (Float.isFinite(x) && Float.isFinite(y)) {
                controller.button(1 << 5, x < -0.5f, 3);
                controller.button(1 << 4, x > 0.5f, 3);
                controller.button(1 << 6, y < -0.5f, 3);
                controller.button(1 << 7, y > 0.5f, 3);
            }
            return true;
        }
        return super.onGenericMotionEvent(event);
    }

    @Override public void onInputDeviceAdded(int deviceId) { /* CodexAstraUlt: No held input to restore. */ }
    @Override public void onInputDeviceChanged(int deviceId) { controller.releaseInputs(); }
    @Override public void onInputDeviceRemoved(int deviceId) { controller.releaseInputs(); }

    @Override public void onHomebrewState(String message, boolean terminal) {
        if (status != null) status.setText(message);
        if (terminal) finish();
    }

    @Override public void onHomebrewFrame(int[] upper, int[] lower, long serial) {
        top.pixels(upper, serial);
        bottom.pixels(lower, serial);
    }
}
