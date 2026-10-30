package org.droidds.probe;

import android.app.Activity;
import android.content.Intent;
import android.content.res.Configuration;
import android.hardware.input.InputManager;
import android.os.Bundle;
import android.view.InputDevice;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;

/** CodexAstraUlt: A real title frontend uses imported matching data, existing
 * guest screen widgets and device controls. It does not substitute a test scene
 * or treat app lifecycle events as new guest sessions. */
public final class TitleActivity extends Activity implements TitleController.Observer,
        InputManager.InputDeviceListener {
    private static final int PICK_GAME = 101, SAVE_REPORT = 102;
    private TitleController controller;
    private InputManager inputManager;
    private ScreenView top, bottom;
    private TextView status;
    private Button choose, included, play, pause, stop, cancel, save;
    private Spinner route;
    private boolean running, importing;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        try { controller = TitleController.get(getApplicationContext()); }
        catch (Exception failure) {
            TextView error = new TextView(this); error.setText("DroiDDS could not open its private storage.");
            setContentView(error); return;
        }
        inputManager = (InputManager)getSystemService(INPUT_SERVICE);
        boolean landscape = getResources().getConfiguration().orientation == Configuration.ORIENTATION_LANDSCAPE;
        LinearLayout root = new LinearLayout(this);
        root.setFitsSystemWindows(true);
        root.setOrientation(landscape ? LinearLayout.HORIZONTAL : LinearLayout.VERTICAL);
        int padding = Math.round(8 * getResources().getDisplayMetrics().density);
        root.setPadding(padding, padding, padding, padding);
        LinearLayout screens = new LinearLayout(this); screens.setOrientation(LinearLayout.VERTICAL);
        top = new ScreenView(this, 400, 240, null, null);
        bottom = new ScreenView(this, 320, 240, (x, y, down) -> controller.touch(x, y, down), null);
        // CodexAstraUlt: Both guest planes currently share one Android display;
        // touch coordinates retain the lower guest's native geometry.
        top.setContentDescription("3DS upper screen"); bottom.setContentDescription("3DS lower touch screen");
        screens.addView(top, new LinearLayout.LayoutParams(-1, 0, 1));
        screens.addView(bottom, new LinearLayout.LayoutParams(-1, 0, 1));
        root.addView(screens, landscape ? new LinearLayout.LayoutParams(0, -1, 3)
                : new LinearLayout.LayoutParams(-1, 0, 3));
        LinearLayout panel = new LinearLayout(this); panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(padding, padding, 0, 0);
        TextView title = new TextView(this); title.setText("DroiDDS"); title.setTextSize(22); panel.addView(title);
        status = new TextView(this); status.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        panel.addView(status);
        choose = action(panel, "Import game", () -> {
            Intent picker = new Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("*/*");
            try { startActivityForResult(picker, PICK_GAME); }
            catch (RuntimeException unavailable) { status.setText("No document picker is available on this device."); }
        });
        included = action(panel, "Load included test", () -> controller.importGame(null, true));
        cancel = action(panel, "Cancel import", () -> controller.cancelImport());
        route = new Spinner(this);
        ArrayAdapter<String> routes = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item,
                new String[]{"Native", "Interpreter"});
        routes.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        route.setAdapter(routes); route.setContentDescription("Execution mode");
        if (state != null) route.setSelection(state.getInt("route", 0) == 1 ? 1 : 0);
        panel.addView(route);
        play = action(panel, "Play", () -> controller.start(route.getSelectedItemPosition() == 0));
        LinearLayout session = new LinearLayout(this);
        pause = action(session, "Pause", () -> controller.pauseOrResume());
        stop = action(session, "Stop", () -> controller.stop()); panel.addView(session);
        // CodexAstraUlt: Physical controls provide both analog sticks; these
        // compact touch buttons retain essential input when no pad is attached.
        buttons(panel, new String[]{"L", "↑", "R"}, new int[]{1 << 9, 1 << 6, 1 << 8});
        buttons(panel, new String[]{"←", "↓", "→"}, new int[]{1 << 5, 1 << 7, 1 << 4});
        buttons(panel, new String[]{"X", "Y", "A", "B"}, new int[]{1 << 10, 1 << 11, 1, 1 << 1});
        buttons(panel, new String[]{"Select", "Start", "ZL", "ZR"}, new int[]{1 << 2, 1 << 3, 1 << 14, 1 << 15});
        save = action(panel, "Save report", () -> {
            Intent target = new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE)
                    .setType("application/json").putExtra(Intent.EXTRA_TITLE, "droidds-latest-title.json");
            try { startActivityForResult(target, SAVE_REPORT); }
            catch (RuntimeException unavailable) { status.setText("No document picker is available; the report remains saved in the app."); }
        });
        ScrollView scrolling = new ScrollView(this); scrolling.addView(panel);
        root.addView(scrolling, landscape ? new LinearLayout.LayoutParams(0, -1, 2)
                : new LinearLayout.LayoutParams(-1, 0, 2));
        setContentView(root);
    }

    private Button action(LinearLayout parent, String label, Runnable action) {
        Button button = new Button(this); button.setText(label); button.setOnClickListener(view -> action.run());
        parent.addView(button, parent.getOrientation() == LinearLayout.HORIZONTAL
                ? new LinearLayout.LayoutParams(0, -2, 1) : new LinearLayout.LayoutParams(-1, -2));
        return button;
    }

    private void buttons(LinearLayout parent, String[] labels, int[] bits) {
        LinearLayout row = new LinearLayout(this);
        for (int i = 0; i < labels.length; i++) {
            final int mask = bits[i];
            Button button = new Button(this); button.setText(labels[i]);
            button.setMinWidth(0); button.setMinimumWidth(0);
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
        parent.addView(row);
    }

    @Override protected void onStart() { super.onStart(); if (controller != null) controller.observe(this); }
    @Override protected void onResume() {
        super.onResume(); if (controller != null) controller.foreground(true);
        if (inputManager != null) inputManager.registerInputDeviceListener(this, null);
    }
    @Override protected void onPause() {
        if (controller != null) controller.foreground(false);
        if (inputManager != null) inputManager.unregisterInputDeviceListener(this);
        super.onPause();
    }
    @Override protected void onStop() { if (controller != null) controller.removeObserver(this); super.onStop(); }
    @Override public void onWindowFocusChanged(boolean focused) {
        super.onWindowFocusChanged(focused); if (!focused && controller != null) controller.releaseInputs();
    }
    @Override protected void onSaveInstanceState(Bundle state) {
        if (route != null) state.putInt("route", route.getSelectedItemPosition());
        super.onSaveInstanceState(state);
    }
    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (controller == null || result != RESULT_OK || data == null || data.getData() == null) return;
        if (request == PICK_GAME) controller.importGame(data.getData(), false);
        if (request == SAVE_REPORT) controller.exportReport(data.getData());
    }
    @Override @SuppressWarnings("deprecation") public void onBackPressed() {
        if (importing) controller.cancelImport();
        else if (running) controller.stop();
        else super.onBackPressed();
    }

    @Override public void state(TitleController.Snapshot state) {
        running = state.running; importing = state.importing;
        status.setText(state.message);
        choose.setEnabled(state.canImport); included.setVisibility(state.included ? View.VISIBLE : View.GONE);
        included.setEnabled(state.canImport); cancel.setVisibility(state.importing ? View.VISIBLE : View.GONE);
        play.setEnabled(state.canPlay); pause.setEnabled(state.running); stop.setEnabled(state.running);
        pause.setText(state.paused ? "Resume" : "Pause"); route.setEnabled(!state.busy); save.setEnabled(state.canExport);
    }
    // CodexAstraUlt: Hide old bitmaps between sessions; only a new guest plane
    // or the current session's retained plane makes that view visible again.
    @Override public void reset() { top.setVisibility(View.INVISIBLE); bottom.setVisibility(View.INVISIBLE); }
    @Override public void pixels(int[] upper, int[] lower, int mask, long sequence) {
        if ((mask & 1) != 0) { top.pixels(upper, sequence); top.setVisibility(View.VISIBLE); }
        if ((mask & 2) != 0) { bottom.pixels(lower, sequence); bottom.setVisibility(View.VISIBLE); }
    }

    static int button(int code) {
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
    @Override public boolean dispatchKeyEvent(KeyEvent event) {
        int bit = button(event.getKeyCode());
        if (bit != 0 && controller != null && running
                && (event.getAction() == KeyEvent.ACTION_DOWN || event.getAction() == KeyEvent.ACTION_UP)) {
            controller.button(bit, event.getAction() == KeyEvent.ACTION_DOWN, 1); return true;
        }
        return super.dispatchKeyEvent(event);
    }
    private static float axis(MotionEvent event, InputDevice device, int axis) {
        InputDevice.MotionRange range = device.getMotionRange(axis, event.getSource());
        return range == null ? 0 : TitleInput.axis(event.getAxisValue(axis), range.getFlat());
    }
    @Override public boolean onGenericMotionEvent(MotionEvent event) {
        InputDevice device = event.getDevice();
        if (controller == null || device == null || device.isVirtual() || !running
                || (event.getSource() & InputDevice.SOURCE_JOYSTICK) != InputDevice.SOURCE_JOYSTICK) {
            return super.onGenericMotionEvent(event);
        }
        float hx = axis(event, device, MotionEvent.AXIS_HAT_X), hy = axis(event, device, MotionEvent.AXIS_HAT_Y);
        controller.button(1 << 5, hx < -0.5f, 2); controller.button(1 << 4, hx > 0.5f, 2);
        controller.button(1 << 6, hy < -0.5f, 2); controller.button(1 << 7, hy > 0.5f, 2);
        int rightX = device.getMotionRange(MotionEvent.AXIS_Z, event.getSource()) != null ? MotionEvent.AXIS_Z : MotionEvent.AXIS_RX;
        int rightY = device.getMotionRange(MotionEvent.AXIS_RZ, event.getSource()) != null ? MotionEvent.AXIS_RZ : MotionEvent.AXIS_RY;
        controller.axes(axis(event, device, MotionEvent.AXIS_X), -axis(event, device, MotionEvent.AXIS_Y),
                axis(event, device, rightX), -axis(event, device, rightY));
        return true;
    }
    @Override public void onInputDeviceAdded(int id) { /* CodexAstraUlt: No old held state is restored. */ }
    @Override public void onInputDeviceChanged(int id) { if (controller != null) controller.releaseInputs(); }
    @Override public void onInputDeviceRemoved(int id) { if (controller != null) controller.releaseInputs(); }
}
