package org.droidds.probe;

import android.app.Activity;
import android.graphics.Typeface;
import android.os.Bundle;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

/** CodexAstraUlt: Original, deliberately small UI for the Android CPU loader
 * proof. Activity recreation observes the existing process run rather than
 * starting competing native executions or retaining an obsolete Activity. */
public final class ProbeActivity extends Activity implements ProbeController.Observer {
    private ProbeController controller;
    private TextView status;
    private TextView details;
    private Button run;

    @Override
    public void onCreate(Bundle state) {
        super.onCreate(state);
        controller = ProbeController.get(getApplicationContext());

        // CodexAstraUlt: A platform-only layout keeps this diagnostic APK free of
        // frontend libraries and makes its limited scope visible to the tester.
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        int padding = Math.round(20 * getResources().getDisplayMetrics().density);
        content.setPadding(padding, padding, padding, padding);
        TextView title = new TextView(this);
        title.setText("DroidDS Android probe");
        title.setTextSize(24);
        content.addView(title);
        TextView scope = new TextView(this);
        scope.setText("Synthetic CPU and native-library loading test. "
                + "This probe does not run games or render graphics.");
        scope.setTextSize(16);
        content.addView(scope);
        status = new TextView(this);
        status.setTextSize(20);
        content.addView(status);
        run = new Button(this);
        run.setText("Run again");
        run.setOnClickListener(view -> controller.runAgain());
        content.addView(run);
        TextView storage = new TextView(this);
        storage.setText("Only the latest report is retained in private app storage "
                + "as files/latest-probe.json.");
        content.addView(storage);
        details = new TextView(this);
        details.setTextIsSelectable(true);
        details.setTypeface(Typeface.MONOSPACE);
        details.setTextSize(12);
        content.addView(details);
        ScrollView scroll = new ScrollView(this);
        // CodexAstraUlt: Keep the diagnostic text clear of system bars when a
        // target-35 device applies edge-to-edge window behavior.
        scroll.setFitsSystemWindows(true);
        scroll.addView(content);
        setContentView(scroll);

        // CodexAstraUlt: An adb caller can supply a unique request token and
        // reject an earlier run's report. Normal launches receive a fresh UUID.
        controller.startOnce(getIntent().getStringExtra("request_id"));
    }

    @Override
    protected void onStart() {
        super.onStart();
        controller.observe(this);
    }

    @Override
    protected void onStop() {
        controller.removeObserver(this);
        super.onStop();
    }

    @Override
    public void onProbeChanged(ProbeController.Snapshot snapshot) {
        // CodexAstraUlt: All observer delivery occurs on Android's main thread;
        // native execution and atomic report writes remain on the worker.
        status.setText(snapshot.status);
        details.setText(snapshot.details);
        run.setEnabled(!snapshot.running);
    }
}
