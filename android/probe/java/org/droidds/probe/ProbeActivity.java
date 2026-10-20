package org.droidds.probe;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.graphics.Typeface;
import android.os.Bundle;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

/** CodexAstraUlt: A small platform-only UI for CPU loading and an offscreen
 * Vulkan draw. Recreation observes the current process run; neither a game
 * renderer nor a dependency-heavy frontend is needed for this diagnostic. */
public final class ProbeActivity extends Activity implements ProbeController.Observer {
    // CodexAstraUlt: Framework request codes have 16 usable bits. Never reuse a
    // code within this process: a late result from a cancelled selection must
    // not consume a newer selection's token. Exhaustion fails without wrapping.
    private static final int LAST_SAVE_REQUEST = 65535;
    private static int nextSaveRequest = 1;
    private static final String SAVE_TOKEN_STATE = "report_export_token";
    private static final String SAVE_REQUEST_STATE = "report_export_request";
    private static final String NEXT_REQUEST_STATE = "report_export_next_request";
    private ProbeController controller;
    private TextView status;
    private TextView details;
    private TextView exportStatus;
    private Button run;
    private Button save;
    private Button homebrew;
    private String exportToken;
    private int exportRequest = -1;

    @Override
    public void onCreate(Bundle state) {
        super.onCreate(state);
        controller = ProbeController.get(getApplicationContext());
        // CodexAstraUlt: Rotation preserves the exact current request/token
        // pair and advances the process counter beyond every saved allocation.
        // A newly created Activity cannot reset another Activity's counter.
        if (state != null) {
            int savedNext = state.getInt(NEXT_REQUEST_STATE, LAST_SAVE_REQUEST + 1);
            if (savedNext < 1 || savedNext > LAST_SAVE_REQUEST + 1) {
                savedNext = LAST_SAVE_REQUEST + 1;
            }
            nextSaveRequest = Math.max(nextSaveRequest, savedNext);
            int savedRequest = state.getInt(SAVE_REQUEST_STATE, -1);
            if (savedRequest >= 1 && savedRequest < savedNext) {
                exportRequest = savedRequest;
                exportToken = state.getString(SAVE_TOKEN_STATE);
            }
        }

        // CodexAstraUlt: A platform-only layout keeps this diagnostic APK free of
        // frontend libraries and makes its limited scope visible to the tester.
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        int padding = Math.round(20 * getResources().getDisplayMetrics().density);
        content.setPadding(padding, padding, padding, padding);
        TextView title = new TextView(this);
        // CodexAstraUlt: Name the correction visibly; the milestone remains
        // 0.0.6 while Android's increasing install code distinguishes reports.
        title.setText("DroidDS 0.0.6 · correction 2");
        title.setTextSize(24);
        content.addView(title);
        TextView scope = new TextView(this);
        // CodexAstraUlt: Describe the expanded diagnostic in terms useful to
        // the tester while preserving the separation from actual game support.
        scope.setText("Tests an original 3DS program through the loader, services and graphics runtime, "
                + "alongside CPU and GPU checks. Save the report even if a check fails. "
                + "This diagnostic does not load your games yet.");
        scope.setTextSize(16);
        content.addView(scope);
        status = new TextView(this);
        status.setTextSize(20);
        content.addView(status);
        run = new Button(this);
        run.setText("Run again");
        run.setOnClickListener(view -> controller.runAgain());
        content.addView(run);
        // CodexAstraUlt: The visible guest has its own lifecycle and manual
        // observations. It cannot overlap automated work or a pinned export.
        homebrew = new Button(this);
        homebrew.setText("Test original homebrew");
        homebrew.setEnabled(false);
        homebrew.setOnClickListener(view -> {
            String token = controller.beginHomebrew();
            if (token == null) return;
            try {
                startActivity(new Intent(this, HomebrewActivity.class).putExtra("session_id", token));
            } catch (ActivityNotFoundException | SecurityException failure) {
                HomebrewController.get(getApplicationContext()).stop(token, "activity_launch_failed");
            }
        });
        content.addView(homebrew);
        save = new Button(this);
        save.setText("Save report");
        save.setEnabled(false);
        save.setOnClickListener(view -> chooseReportDestination());
        content.addView(save);
        exportStatus = new TextView(this);
        content.addView(exportStatus);
        TextView storage = new TextView(this);
        storage.setText("The latest report is retained in private app storage. "
                + "Save report copies a completed result to a location you choose.");
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

    // CodexAstraUlt: The framework document picker grants only one selected URI.
    // Its older Activity result API avoids adding AndroidX just for exporting a
    // small report; suppress that specific SDK deprecation only at the call site.
    @SuppressWarnings("deprecation")
    private void chooseReportDestination() {
        String selectedToken = controller.beginExport();
        if (selectedToken == null) {
            return;
        }
        if (nextSaveRequest > LAST_SAVE_REQUEST) {
            controller.cancelExport(selectedToken,
                    "Report dialog limit reached. Restart the app or retrieve the report with ADB.");
            exportToken = null;
            exportRequest = -1;
            return;
        }
        exportToken = selectedToken;
        exportRequest = nextSaveRequest++;
        Intent destination = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        destination.addCategory(Intent.CATEGORY_OPENABLE);
        destination.setType("application/json");
        destination.putExtra(Intent.EXTRA_TITLE, "droidds-latest-probe.json");
        try {
            startActivityForResult(destination, exportRequest);
        } catch (ActivityNotFoundException | SecurityException failure) {
            // CodexAstraUlt: Stripped-down Android installations may omit or
            // restrict the picker. Keep the saved probe and Run again functional.
            controller.cancelExport(exportToken,
                    "Document saving is unavailable. The private report can still be retrieved with ADB.");
            exportToken = null;
            exportRequest = -1;
        }
    }

    // CodexAstraUlt: Only selection identity/counter metadata crosses Activity
    // recreation. The controller retains bounded bytes; no report is put into
    // a Bundle or Binder transaction. Process death expires the old selection.
    @Override
    protected void onSaveInstanceState(Bundle state) {
        state.putString(SAVE_TOKEN_STATE, exportToken);
        state.putInt(SAVE_REQUEST_STATE, exportRequest);
        state.putInt(NEXT_REQUEST_STATE, nextSaveRequest);
        super.onSaveInstanceState(state);
    }

    @Override
    @SuppressWarnings("deprecation")
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        // CodexAstraUlt: Ignore old picker results before reading or clearing
        // the current token. A rerun/new picker cannot retarget an old URI to a
        // newer report, even if the old result arrives after Activity rotation.
        if (exportToken == null || exportRequest < 1 || requestCode != exportRequest) {
            return;
        }
        String selectedToken = exportToken;
        exportToken = null;
        exportRequest = -1;
        if (resultCode == RESULT_OK && data != null && data.getData() != null) {
            controller.finishExport(selectedToken, data.getData());
        } else {
            // CodexAstraUlt: Cancelling the picker is normal and does not turn
            // a successful CPU/Vulkan probe into a failed diagnostic result.
            controller.cancelExport(selectedToken, "Save cancelled.");
        }
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
        // CodexAstraUlt: UI delivery occurs on Android's main thread. Native
        // execution, atomic report writes and document export stay on the worker.
        status.setText(snapshot.status);
        details.setText(snapshot.details);
        run.setEnabled(!snapshot.running);
        save.setEnabled(snapshot.canExport);
        homebrew.setEnabled(snapshot.canHomebrew);
        exportStatus.setText(snapshot.exportStatus);
    }
}
