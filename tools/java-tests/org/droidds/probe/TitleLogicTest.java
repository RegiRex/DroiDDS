package org.droidds.probe;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;
import java.util.concurrent.CancellationException;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.stream.Stream;

/** CodexAstraUlt: Real filesystem transactions and actual input logic exercise
 * authored bytes only. Failures preserve prior files and never count as skips. */
public final class TitleLogicTest {
    private static final byte[] ABC = new byte[]{97, 98, 99};
    private static final String SHA = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";
    private static int checks;
    interface Operation { void run() throws Exception; }
    private static void check(boolean condition, String message) {
        checks++; if (!condition) throw new AssertionError(message);
    }
    private static void rejects(Operation operation) throws Exception {
        try { operation.run(); }
        catch (IOException | IllegalArgumentException | CancellationException expected) { checks++; return; }
        throw new AssertionError("Expected operation to reject");
    }
    private static File child(Path root, String name) throws IOException {
        return Files.createDirectory(root.resolve(name)).toFile();
    }
    private static void noStage(File root) throws IOException {
        try (Stream<Path> files = Files.list(root.toPath())) {
            check(files.noneMatch(file -> file.getFileName().toString().startsWith(".import-")), "owned partial import survived");
        }
    }
    private static File copy(File directory, byte[] bytes) throws IOException {
        return TitleImport.copy(new ByteArrayInputStream(bytes), directory, 3, SHA, () -> false, (a, b) -> { });
    }

    private static void importAndReuse(Path root) throws Exception {
        File directory = child(root, "valid");
        Path original = root.resolve("owner-original.bin"); Files.write(original, ABC);
        File target;
        try (InputStream source = Files.newInputStream(original)) {
            target = TitleImport.copy(source, directory, 3, SHA, () -> false, (done, total) -> {
                check(done == 3 && total == 3, "progress did not describe actual copied bytes");
            });
        }
        check(java.util.Arrays.equals(Files.readAllBytes(target.toPath()), ABC), "import contents");
        check(java.util.Arrays.equals(Files.readAllBytes(original), ABC), "original changed");
        long before = target.lastModified();
        InputStream unreadable = new InputStream() { @Override public int read() { throw new AssertionError("reused import read provider"); } };
        check(TitleImport.copy(unreadable, directory, 3, SHA, () -> false, (a, b) -> { }).equals(target), "reuse identity");
        check(target.lastModified() == before, "reuse rewrote original destination"); noStage(directory);
    }

    private static void rejectionAndCancellation(Path root) throws Exception {
        File directory = child(root, "rejected");
        Path unrelated = directory.toPath().resolve("foreign.part"); Files.write(unrelated, ABC);
        for (byte[] invalid : new byte[][]{new byte[]{97, 98}, new byte[]{97, 98, 99, 100}, new byte[]{98, 98, 99}}) {
            rejects(() -> copy(directory, invalid)); noStage(directory);
            check(java.util.Arrays.equals(Files.readAllBytes(unrelated), ABC), "foreign file changed");
            check(!TitleImport.destination(directory, SHA).exists(), "rejected import was published");
        }
        AtomicBoolean cancelled = new AtomicBoolean();
        rejects(() -> TitleImport.copy(new ByteArrayInputStream(ABC), directory, 3, SHA,
                cancelled::get, (done, total) -> cancelled.set(true)));
        noStage(directory); check(!TitleImport.destination(directory, SHA).exists(), "cancelled import published");
        InputStream failure = new InputStream() { @Override public int read() throws IOException { throw new IOException("authored stream failure"); } };
        rejects(() -> TitleImport.copy(failure, directory, 3, SHA, () -> false, (a, b) -> { }));
        noStage(directory);
        rejects(() -> TitleImport.identity(0, SHA));
        rejects(() -> TitleImport.identity(TitleImport.MAX_INPUT + 1, SHA));
        rejects(() -> TitleImport.identity(3, "../wrong"));
    }

    private static void publicationRace(Path root) throws Exception {
        for (boolean matching : new boolean[]{false, true}) {
            File directory = child(root, "race-" + matching);
            Path target = TitleImport.destination(directory, SHA).toPath();
            byte[] raced = matching ? ABC : new byte[]{7, 8, 9};
            Operation operation = () -> TitleImport.copy(new ByteArrayInputStream(ABC), directory, 3, SHA,
                    () -> false, (done, total) -> {
                        try { Files.write(target, raced); }
                        catch (IOException failure) { throw new AssertionError(failure); }
                    });
            if (matching) operation.run(); else rejects(operation);
            check(java.util.Arrays.equals(Files.readAllBytes(target), raced), "publication overwrote a raced destination");
            noStage(directory);
        }
    }

    private static void symlinksAndReports(Path root) throws Exception {
        File directory = child(root, "links");
        Path original = root.resolve("protected-save.bin"); Files.write(original, ABC);
        Files.createSymbolicLink(TitleImport.destination(directory, SHA).toPath(), original);
        rejects(() -> copy(directory, ABC));
        Path alias = root.resolve("directory-alias"); Files.createSymbolicLink(alias, directory.toPath());
        rejects(() -> TitleImport.directory(alias.toFile()));
        File report = root.resolve("latest-title-report.json").toFile();
        TitleImport.report(report, "{\"status\":\"old\"}".getBytes(StandardCharsets.UTF_8));
        TitleImport.report(report, "{\"status\":\"new\"}".getBytes(StandardCharsets.UTF_8));
        check(new String(Files.readAllBytes(report.toPath()), StandardCharsets.UTF_8).contains("new"), "report replacement failed");
        byte[] before = Files.readAllBytes(report.toPath());
        rejects(() -> TitleImport.report(report, new byte[TitleImport.REPORT_LIMIT + 1]));
        check(java.util.Arrays.equals(before, Files.readAllBytes(report.toPath())), "oversized report changed previous report");
        Path link = root.resolve("report-link.json"); Files.createSymbolicLink(link, original);
        rejects(() -> TitleImport.report(link.toFile(), before));
        check(java.util.Arrays.equals(Files.readAllBytes(original), ABC), "save changed through link");
        try (Stream<Path> files = Files.list(root)) {
            check(files.noneMatch(file -> file.getFileName().toString().startsWith(".report-")), "partial report survived");
        }
    }

    private static void inputEdgesAndAxes() {
        TitleInput input = new TitleInput();
        TitleInput.Sample sample = new TitleInput.Sample(0, 0, 0, false, 0, 0, 0, 0);
        input.button(1, true, 0); input.button(1, true, 1); input.button(1, false, 0); input.button(1, false, 1);
        for (int expected : new int[]{1, 0}) {
            sample = input.next(sample); check(sample.buttons == expected, "source-separated button edge");
        }
        input.touch(999, -1, true); input.axes(0.3f, -0.4f, 0.5f, -0.6f);
        input.touch(12, 15, true); input.touch(12, 15, false);
        sample = input.next(sample); check(sample.touched && sample.x == 319 && sample.y == 0, "touch down edge");
        sample = input.next(sample); check(sample.touched && sample.x == 12 && sample.y == 15
                && sample.circleX == 0.3f && sample.cStickY == -0.6f, "movement coalescing lost held state");
        sample = input.next(sample); check(!sample.touched, "touch up edge");
        check(TitleInput.axis(Float.NaN, 0) == 0 && TitleInput.axis(Float.POSITIVE_INFINITY, 0) == 0, "nonfinite axis");
        check(TitleInput.axis(0.1f, 0.2f) == 0 && TitleInput.axis(-1, 0.2f) == -1
                && TitleInput.axis(1, 0.2f) == 1 && TitleInput.axis(10, 0) == 1, "deadzone/clamping");
        for (int i = 0; i < 200; i++) input.button(2, i % 2 == 0, 1);
        check(input.overflows() > 0, "input bound was not reached");
        input.release(); sample = input.next(sample);
        check(sample.buttons == 0 && !sample.touched && sample.circleX == 0 && sample.circleY == 0
                && sample.cStickX == 0 && sample.cStickY == 0, "pause/disconnect did not release controls");
    }

    // CodexAstraUlt: Reproduce an old delayed frame firing after resume. Only
    // the new chain may advance the guest, including after a second restart.
    private static void delayedCallbacksAcrossPause() {
        TitleLoop loop = new TitleLoop();
        long delayed = loop.resume();
        check(loop.accepts(delayed) && !loop.synchronize(0), "initial callback rejected");
        // CodexAstraUlt: A queued lifecycle update may see the UI active again;
        // its observed pause epoch must still retire the abandoned old chain.
        check(loop.synchronize(1) && !loop.accepts(delayed), "rapid pause/resume boundary was lost");
        long resumed = loop.resume();
        int slices = 0;
        for (long queued : new long[]{resumed, delayed, resumed, delayed}) {
            if (loop.accepts(queued)) slices++;
        }
        check(slices == 2 && !loop.synchronize(1) && loop.accepts(resumed), "delayed callback created a second active work chain");
        loop.pause();
        check(!loop.accepts(resumed), "stopped callback survived");
        loop.synchronize(2);
        long replacement = loop.resume();
        check(loop.accepts(replacement) && !loop.accepts(resumed) && !loop.accepts(delayed)
                && !loop.synchronize(2), "restart reused an old work chain");
    }

    // CodexAstraUlt: Actual production input dequeue holds both short button
    // and touch presses across arbitrary cooperative yields within one frame.
    private static void inputEdgesAcrossYieldedSlices() {
        TitleInput input = new TitleInput();
        TitleInput.Sample sample = new TitleInput.Sample(0, 0, 0, false, 0, 0, 0, 0);
        input.button(1, true, 1); input.button(1, false, 1);
        sample = input.next(sample, 17);
        check(sample.buttons == 1, "press missing at first guest frame");
        for (int i = 0; i < 8; i++) sample = input.next(sample, 17);
        check(sample.buttons == 1, "cooperative yield consumed queued release");
        sample = input.next(sample, 18);
        check(sample.buttons == 0, "next guest frame did not receive release");
        input.touch(7, 9, true); input.touch(7, 9, false);
        sample = input.next(sample, 19);
        check(sample.touched && sample.x == 7 && sample.y == 9, "touch press missing");
        for (int i = 0; i < 8; i++) sample = input.next(sample, 19);
        check(sample.touched, "cooperative yield consumed touch release");
        sample = input.next(sample, 20);
        check(!sample.touched, "next guest frame did not receive touch release");
        input.button(2, true, 1); sample = input.next(sample, 21);
        check(sample.buttons == 2, "held control missing before pause");
        input.release(); sample = input.next(sample, 21);
        check(sample.buttons == 0 && !sample.touched, "pause release waited for another frame");
        input.release(); sample = input.next(sample, 0);
        check(sample.buttons == 0, "new session inherited old frame latch");
    }

    // CodexAstraUlt: A real event's hat and analog state must arrive together,
    // with no intermediate left+right/up+down state or duplicate-owner delay.
    private static void atomicJoystickFrames() {
        TitleInput input = new TitleInput();
        TitleInput.Sample sample = new TitleInput.Sample(0, 0, 0, false, 0, 0, 0, 0);
        input.motion(0x50, 1, 1, 0.2f, 0.3f);
        input.motion(0xa0, -1, -1, -0.4f, -0.5f);
        sample = input.next(sample, 0);
        check(sample.buttons == 0x50 && sample.circleX == 1 && sample.circleY == 1
                && sample.cStickX == 0.2f && sample.cStickY == 0.3f, "first joystick state split");
        sample = input.next(sample, 1);
        check(sample.buttons == 0xa0 && sample.circleX == -1 && sample.circleY == -1
                && sample.cStickX == -0.4f && sample.cStickY == -0.5f, "diagonal reversal split");
        input.motion(0xa0, -1, -1, -0.4f, -0.5f);
        input.motion(0, 0, 0, 0, 0);
        sample = input.next(sample, 2);
        check(sample.buttons == 0 && sample.circleX == 0 && sample.cStickX == 0,
                "duplicate joystick event delayed neutral state");
        input.button(1, true, 0); input.button(1, true, 1); input.button(1, false, 0);
        sample = input.next(sample, 3);
        check(sample.buttons == 1, "second source did not retain held button");
        input.button(1, false, 1);
        sample = input.next(sample, 4);
        check(sample.buttons == 0, "duplicate source delayed final release");
    }

    // CodexAstraUlt: Model an actual in-flight native call across background,
    // resume, explicit pause and final teardown. Only the playing foreground
    // intervals contribute active wall time; full call cost remains observable.
    private static void timingAcrossLifecycle() {
        TitleTiming timing = new TitleTiming();
        timing.reset(true);
        check(timing.snapshot(1000).activeWall == 0, "opening counted as active emulation");
        timing.running(true, 1000); timing.beginFrame(1000);
        timing.foreground(false, 1010);
        timing.nativeCall(1001, 1020);
        timing.running(false, 1020);
        TitleTiming.Snapshot paused = timing.snapshot(5000);
        check(paused.activeWall == 10 && paused.activeEpochs == 1,
                "in-flight completion or background idle extended active time");
        check(paused.workerWall == 20,
                "worker denominator omitted guest execution after the UI background boundary");
        check(paused.nativeCalls == 1 && paused.nativeTotal == 19 && paused.nativeMaximum == 19,
                "native timing hid the in-flight lifecycle tail");
        check(paused.completedFrames == 0 && paused.abandonedFrames == 1,
                "abandoned partial frame became completed work");
        timing.foreground(true, 5000);
        check(timing.snapshot(5100).activeWall == 10, "foreground resumed timing before owner execution");
        timing.running(true, 5100); timing.beginFrame(5100); timing.finishFrame(5115);
        timing.userPaused(true, 5120); timing.running(false, 5150);
        check(timing.snapshot(8000).activeWall == 30, "user pause included worker retirement delay");
        timing.userPaused(false, 8000); timing.running(true, 8100); timing.beginFrame(8100);
        timing.requestStop(8130);
        check(timing.snapshot(8135).activeWall == 60 && timing.snapshot(8135).workerWall == 105,
                "requested stop erased the in-flight worker tail");
        timing.stop(8140); timing.running(true, 8200); timing.stop(9000);
        TitleTiming.Snapshot stopped = timing.snapshot(1000000);
        check(stopped.activeWall == 60 && stopped.activeEpochs == 3,
                "teardown or a stale running update reopened stopped timing");
        check(stopped.workerWall == 110,
                "worker-run denominator included paused idle/teardown or lost an in-flight tail");
        check(stopped.completedFrames == 1 && stopped.frameTotal == 15 && stopped.frameMaximum == 15
                && stopped.abandonedFrames == 2, "completed and abandoned frame accounting differs");
        timing.reset(false); timing.running(true, 1000000);
        TitleTiming.Snapshot replacement = timing.snapshot(2000000);
        check(replacement.activeWall == 0 && replacement.activeEpochs == 0 && replacement.nativeCalls == 0
                && replacement.completedFrames == 0 && replacement.abandonedFrames == 0,
                "new background session inherited old timing or work counters");
    }

    // CodexAstraUlt: Intended sleep, executor lateness and missing guest PCM
    // are different evidence. Empty slices, inactive submissions and pause time
    // must not masquerade as audio production or a long active PCM gap.
    private static void timingOfSchedulingAndPcm() {
        TitleTiming timing = new TitleTiming(); timing.reset(true); timing.running(true, 0);
        timing.callback(0, 10, 10); timing.callback(10, 10, 25); timing.callback(25, 0, 28);
        timing.audioSubmit(28, 30, 0, true);
        check(timing.snapshot(500).pcmGapMaximum == 0, "startup silence before any PCM counted as a delivery gap");
        timing.audioSubmit(501, 503, 160, true);
        timing.audioSubmit(510, 511, 0, true);
        timing.audioSubmit(523, 526, 160, true);
        check(timing.snapshot(530).pcmSubmissions == 2 && timing.snapshot(530).pcmGapMaximum == 23,
                "empty slice reset an actual PCM producer gap");
        timing.foreground(false, 550);
        timing.audioSubmit(600, 610, 160, false);
        TitleTiming.Snapshot gap = timing.snapshot(5000);
        check(gap.pcmSubmissions == 2 && gap.pcmGapMaximum == 24,
                "paused audio or background duration extended the active PCM gap");
        check(gap.callbacks == 3 && gap.requestedDelay == 20 && gap.latenessTotal == 8 && gap.latenessMaximum == 5,
                "requested pacing sleep was classified as executor lateness");
        check(gap.audioCalls == 5 && gap.audioTotal == 18 && gap.audioMaximum == 10,
                "audio submit wall cost omitted an inactive completion");
        timing.foreground(true, 5000); timing.audioSubmit(5010, 5012, 160, true); timing.stop(5014);
        check(timing.snapshot(9000).pcmSubmissions == 3 && timing.snapshot(9000).pcmGapMaximum == 24,
                "resume included background time in PCM spacing");
        check(timing.snapshot(9000).activeWall == 564, "active intervals do not match the modeled foreground route");
    }

    // CodexAstraUlt: A recreated UI must display the admitted route rather than
    // stale defaults, while idle selections remain editable for the next run.
    private static void vertexPolicyAcrossViewReplacement() throws Exception {
        TitleLaunchOptions defaults = TitleLaunchOptions.restored(0, TitleLaunchOptions.AUTOMATIC);
        check(defaults.nativeMode && defaults.vertexPolicyName().equals("automatic"), "default renderer policy changed");
        for (boolean nativeRoute : new boolean[]{false, true}) {
            for (int choice = TitleLaunchOptions.AUTOMATIC; choice <= TitleLaunchOptions.GPU; choice++) {
                TitleLaunchOptions options = new TitleLaunchOptions(nativeRoute, choice);
                check(options.nativeMode == nativeRoute && options.vertexPolicy == choice
                        && options.vertexPolicyName().equals(new String[]{"automatic", "cpu", "gpu"}[choice]),
                        "vertex selection altered guest CPU mode or report identity");
            }
        }
        for (int invalid : new int[]{Integer.MIN_VALUE, -1, 3, Integer.MAX_VALUE}) {
            rejects(() -> new TitleLaunchOptions(true, invalid));
            check(TitleLaunchOptions.restored(1, invalid).vertexPolicy == TitleLaunchOptions.AUTOMATIC,
                    "invalid saved selector enabled a forced renderer path");
        }
        TitleLaunchOptions activeGpu = new TitleLaunchOptions(true, TitleLaunchOptions.GPU);
        check(activeGpu.displayed(true, 1, TitleLaunchOptions.CPU) == activeGpu,
                "stale Activity state changed a live native/GPU selection");
        check(activeGpu.displayed(true, -1, -1) == activeGpu,
                "missing recreated widgets replaced the active session's selection");
        TitleLaunchOptions activeCpu = new TitleLaunchOptions(false, TitleLaunchOptions.CPU);
        check(activeCpu.displayed(true, 0, TitleLaunchOptions.AUTOMATIC) == activeCpu,
                "Activity defaults hid a live interpreter/CPU selection");
        TitleLaunchOptions next = activeGpu.displayed(false, 1, TitleLaunchOptions.CPU);
        check(!next.nativeMode && next.vertexPolicy == TitleLaunchOptions.CPU,
                "idle selection could not prepare a different next session");
        check(activeGpu.nativeMode && activeGpu.vertexPolicy == TitleLaunchOptions.GPU,
                "next-session UI state mutated the prior admitted selection");
        check(TitleLaunchOptions.restored(99, TitleLaunchOptions.GPU).nativeMode,
                "invalid saved CPU route changed the default execution mode");
    }

    public static void main(String[] arguments) throws Exception {
        Path root = Files.createTempDirectory("droidds-title-java-").toRealPath();
        try {
            importAndReuse(root); rejectionAndCancellation(root); publicationRace(root); symlinksAndReports(root); inputEdgesAndAxes();
            delayedCallbacksAcrossPause();
            inputEdgesAcrossYieldedSlices();
            atomicJoystickFrames();
            timingAcrossLifecycle(); timingOfSchedulingAndPcm();
            vertexPolicyAcrossViewReplacement();
            System.out.println("{\"schema\":1,\"kind\":\"droidds-java-title-logic\",\"status\":\"passed\",\"checks\":" + checks
                    + ",\"controls\":[\"verified_import_reuse_preservation\",\"rejection_cancel_io_cleanup\","
                    + "\"atomic_publication_races\",\"symlink_and_atomic_report_preservation\",\"input_edges_axes_release\","
                    + "\"pause_resume_retires_delayed_callbacks\",\"active_timing_and_delivery_gap_accounting\","
                    + "\"vertex_policy_validation_and_session_latching\"]}");
        } finally {
            // CodexAstraUlt: Remove only this test's uniquely created tree.
            try (Stream<Path> paths = Files.walk(root)) {
                for (Path path : (Iterable<Path>)paths.sorted(Comparator.reverseOrder())::iterator) Files.delete(path);
            }
        }
    }
}
