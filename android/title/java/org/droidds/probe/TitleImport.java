package org.droidds.probe;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.FileAlreadyExistsException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.concurrent.CancellationException;
import java.util.function.BooleanSupplier;

/** CodexAstraUlt: Import is a bounded immutable-copy transaction. Only the
 * unique staging file created by this invocation may be deleted on failure.
 * This plain Java layer is exercised on the host without Android mocks. */
final class TitleImport {
    static final long MAX_INPUT = 8L * 1024 * 1024 * 1024;
    static final int REPORT_LIMIT = 256 * 1024;
    private static final long SPACE_RESERVE = 16L * 1024 * 1024;
    interface Progress { void copied(long bytes, long total); }

    private TitleImport() { }

    static File directory(File directory) throws IOException {
        Path path = directory.toPath();
        if (Files.isSymbolicLink(path)) throw new IOException("Storage directory is a symbolic link");
        Files.createDirectories(path);
        if (!Files.isDirectory(path, LinkOption.NOFOLLOW_LINKS)
                || !directory.getAbsoluteFile().equals(directory.getCanonicalFile())) {
            throw new IOException("Storage directory is not an ordinary private directory");
        }
        return directory;
    }

    static void identity(long bytes, String sha256) {
        if (bytes <= 0 || bytes > MAX_INPUT || sha256 == null || !sha256.matches("[0-9a-f]{64}")) {
            throw new IllegalArgumentException("Unsupported game identity");
        }
    }

    static File destination(File directory, String sha256) {
        identity(1, sha256);
        return new File(directory, sha256 + ".bin");
    }

    private static MessageDigest digest() {
        try { return MessageDigest.getInstance("SHA-256"); }
        catch (NoSuchAlgorithmException impossible) { throw new AssertionError(impossible); }
    }

    private static void cancelled(BooleanSupplier cancel) {
        if (cancel.getAsBoolean()) throw new CancellationException("Import cancelled");
    }

    private static String hex(byte[] bytes) {
        char[] alphabet = "0123456789abcdef".toCharArray();
        char[] out = new char[bytes.length * 2];
        for (int i = 0; i < bytes.length; i++) {
            out[i * 2] = alphabet[(bytes[i] & 255) >>> 4];
            out[i * 2 + 1] = alphabet[bytes[i] & 15];
        }
        return new String(out);
    }

    static boolean verify(File file, long bytes, String sha256, BooleanSupplier cancel) throws IOException {
        identity(bytes, sha256);
        Path path = file.toPath();
        if (!Files.exists(path, LinkOption.NOFOLLOW_LINKS)) return false;
        if (!Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS) || Files.size(path) != bytes) {
            throw new IOException("An existing imported file does not match this build");
        }
        MessageDigest digest = digest();
        byte[] buffer = new byte[64 * 1024];
        long total = 0;
        try (InputStream source = new FileInputStream(file)) {
            while (true) {
                cancelled(cancel);
                int count = source.read(buffer);
                if (count < 0) break;
                if (count == 0) continue;
                total += count;
                if (total > bytes) throw new IOException("Imported file changed during verification");
                digest.update(buffer, 0, count);
            }
        }
        cancelled(cancel);
        if (total != bytes || !hex(digest.digest()).equals(sha256)) {
            throw new IOException("An existing imported file does not match this build");
        }
        return true;
    }

    static File copy(InputStream source, File directory, long bytes, String sha256,
            BooleanSupplier cancel, Progress progress) throws IOException {
        identity(bytes, sha256);
        directory(directory);
        cancelled(cancel);
        File target = destination(directory, sha256);
        if (verify(target, bytes, sha256, cancel)) return target;
        if (directory.getUsableSpace() < bytes + SPACE_RESERVE) {
            throw new IOException("Not enough free space to import this game");
        }
        Path stage = Files.createTempFile(directory.toPath(), ".import-", ".part");
        try {
            MessageDigest digest = digest();
            byte[] buffer = new byte[64 * 1024];
            long total = 0;
            try (FileOutputStream output = new FileOutputStream(stage.toFile())) {
                while (true) {
                    cancelled(cancel);
                    int count = source.read(buffer);
                    if (count < 0) break;
                    if (count == 0) continue;
                    total += count;
                    if (total > bytes) throw new IOException("Selected file is larger than this build expects");
                    digest.update(buffer, 0, count);
                    output.write(buffer, 0, count);
                    progress.copied(total, bytes);
                }
                cancelled(cancel);
                if (total != bytes || !hex(digest.digest()).equals(sha256)) {
                    throw new IOException("Selected game does not match this build");
                }
                output.getFD().sync();
            }
            // CodexAstraUlt: link() publishes a complete same-filesystem file
            // atomically and cannot replace an existing destination. Unlike an
            // atomic rename, its no-replace semantics hold even during a race.
            if (!stage.toFile().setWritable(false, false)) throw new IOException("Cannot protect imported file");
            cancelled(cancel);
            try { Files.createLink(target.toPath(), stage); }
            catch (FileAlreadyExistsException raced) {
                if (!verify(target, bytes, sha256, cancel)) throw raced;
            }
            return target;
        } finally {
            Files.deleteIfExists(stage);
        }
    }

    // CodexAstraUlt: One diagnostic file is replaced only after a complete,
    // synced, bounded write. Imported games and runtime saves are never touched.
    static void report(File target, byte[] bytes) throws IOException {
        if (bytes == null || bytes.length == 0 || bytes.length > REPORT_LIMIT) {
            throw new IOException("Diagnostic report exceeds its bound");
        }
        directory(target.getParentFile());
        if (Files.exists(target.toPath(), LinkOption.NOFOLLOW_LINKS)
                && !Files.isRegularFile(target.toPath(), LinkOption.NOFOLLOW_LINKS)) {
            throw new IOException("Report destination is not an ordinary file");
        }
        Path stage = Files.createTempFile(target.getParentFile().toPath(), ".report-", ".part");
        try {
            try (FileOutputStream output = new FileOutputStream(stage.toFile())) {
                output.write(bytes);
                output.getFD().sync();
            }
            Files.move(stage, target.toPath(), StandardCopyOption.ATOMIC_MOVE,
                    StandardCopyOption.REPLACE_EXISTING);
        } finally { Files.deleteIfExists(stage); }
    }
}
