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
        for (int expected : new int[]{1, 1, 1, 0}) {
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

    public static void main(String[] arguments) throws Exception {
        Path root = Files.createTempDirectory("droidds-title-java-").toRealPath();
        try {
            importAndReuse(root); rejectionAndCancellation(root); publicationRace(root); symlinksAndReports(root); inputEdgesAndAxes();
            delayedCallbacksAcrossPause();
            System.out.println("{\"schema\":1,\"kind\":\"droidds-java-title-logic\",\"status\":\"passed\",\"checks\":" + checks
                    + ",\"controls\":[\"verified_import_reuse_preservation\",\"rejection_cancel_io_cleanup\","
                    + "\"atomic_publication_races\",\"symlink_and_atomic_report_preservation\",\"input_edges_axes_release\","
                    + "\"pause_resume_retires_delayed_callbacks\"]}");
        } finally {
            // CodexAstraUlt: Remove only this test's uniquely created tree.
            try (Stream<Path> paths = Files.walk(root)) {
                for (Path path : (Iterable<Path>)paths.sorted(Comparator.reverseOrder())::iterator) Files.delete(path);
            }
        }
    }
}
