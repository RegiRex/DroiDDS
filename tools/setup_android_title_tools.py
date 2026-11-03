#!/usr/bin/env python3
"""CodexAstraUlt: Provision the pinned Android build tools in one owned directory.

Official archives are verified before extraction. No system packages, existing
Rust installation, shell profile, game input or signing key is modified.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import selectors
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import uuid
import zipfile


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path(__file__).with_name("android_title_toolchains.json")
MIB = 1024 * 1024
TARGET = "aarch64-linux-android"
RUST = "1.95.0"
NDK = "27.3.13750724"
TOOLS = "35.0.0"
KIND = "droidds_owned_android_tools"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    """CodexAstraUlt: Hash large tool archives without loading them into memory."""
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def atomic_json(path, value):
    """CodexAstraUlt: Replace only the installer's own bounded metadata files."""
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_text(path, value):
    """CodexAstraUlt: Never publish a partly written shell environment or probe."""
    path = plain_path(path)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            stream.write(value)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def plain_path(path):
    """CodexAstraUlt: Owned output cannot follow a symlink into other data."""
    path = Path(os.path.abspath(path))
    require("\n" not in str(path) and "\r" not in str(path), "Tool paths cannot contain newlines")
    require(all(not parent.is_symlink() for parent in (path, *path.parents)), "Tool output path contains a symlink")
    return path


def outside_git(path):
    # CodexAstraUlt: Some cloud sandboxes expose empty protected .git mount
    # points; only real checkout metadata identifies a working tree.
    require(not any((parent / ".git").is_file() or (parent / ".git/HEAD").is_file()
                    for parent in (path, *path.parents)),
            "Choose a tool directory outside every Git checkout")


def validate_catalog(catalog):
    """CodexAstraUlt: Keep the installation surface limited to reviewed official archives."""
    names = {"ndk", "build_tools", "platform", "jdk", "rustc", "cargo", "rust_std_host", "rust_std_android"}
    require(isinstance(catalog, dict) and catalog.get("schema_version") == 1
            and isinstance(catalog.get("packages"), dict) and set(catalog["packages"]) == names,
            "Unsupported tool manifest")
    prefixes = ("https://dl.google.com/android/repository/", "https://static.rust-lang.org/dist/2026-04-16/",
                "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.20.1%2B1/")
    for package in catalog["packages"].values():
        require(isinstance(package, dict) and isinstance(package.get("url"), str)
                and package["url"].startswith(prefixes) and isinstance(package.get("sha256"), str)
                and re.fullmatch(r"[a-f0-9]{64}", package["sha256"])
                and type(package.get("maximum_bytes")) is int and 0 < package["maximum_bytes"] <= 1024 * MIB,
                "Invalid pinned tool archive")
        prefix = next(value for value in prefixes if package["url"].startswith(value))
        require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+-]*", package["url"][len(prefix):]) is not None,
                "Invalid official archive filename")
        require(isinstance(package.get("root"), str)
                and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+-]*", package["root"]) is not None,
                "Invalid tool archive root")


@contextmanager
def owned_root(path, manifest_hash):
    """CodexAstraUlt: Unknown existing folders are never adopted or overwritten."""
    path = plain_path(path)
    outside_git(path)
    if not path.exists():
        require(path.parent.is_dir(), "The tool directory's parent must exist")
        path.mkdir(mode=0o700)
        atomic_json(path / "setup-state.json", {"schema_version": 1, "kind": KIND,
                    "manifest_sha256": manifest_hash, "status": "created"})
    require(path.is_dir(), "Tool output is not a directory")
    marker = path / "setup-state.json"
    require(marker.is_file() and not marker.is_symlink() and marker.stat().st_size <= MIB,
            "Existing directory is not a recognized DroiDDS tool installation")
    state = json.loads(marker.read_text())
    require(state.get("kind") == KIND and state.get("schema_version") == 1
            and state.get("manifest_sha256") == manifest_hash,
            "Existing tool installation has a different owner/version manifest")
    lock = path / ".setup.lock"
    require(not lock.is_symlink(), "Setup lock is a symlink")
    with lock.open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Another setup is using this tool directory") from None
        for name in ("archives", "receipts", "logs", "cargo"):
            target = path / name
            require(not target.is_symlink(), "Owned tool subdirectory is a symlink")
            target.mkdir(exist_ok=True)
        yield path


def member_path(value):
    """CodexAstraUlt: Reject archive traversal and ambiguous platform separators."""
    path = PurePosixPath(value)
    require(value and not path.is_absolute() and ".." not in path.parts
            and "\\" not in value and "\0" not in value,
            "Unsafe archive member path")
    return path


def unpack(archive, destination, expected_root):
    """CodexAstraUlt: Only regular files, directories and confined links enter staging."""
    destination.mkdir()
    seen = set()
    total = 0
    if zipfile.is_zipfile(archive):
        links = []
        with zipfile.ZipFile(archive) as source:
            entries = source.infolist()
            require(len(entries) <= 100_000, "Archive entry count exceeds bound")
            for item in entries:
                relative = member_path(item.filename)
                require(relative.parts[0] == expected_root and str(relative) not in seen,
                        "Archive root or duplicate member differs")
                seen.add(str(relative))
                total += item.file_size
                require(total <= 4 * 1024 * MIB, "Expanded archive exceeds bound")
                target = destination.joinpath(*relative.parts)
                mode = item.external_attr >> 16
                kind = stat.S_IFMT(mode)
                require(kind in (0, stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK), "Archive contains a special file")
                if item.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                elif kind == stat.S_IFLNK:
                    require(item.file_size <= 4096, "Archive symlink target exceeds bound")
                    links.append((target, source.read(item).decode("utf-8")))
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with source.open(item) as incoming, target.open("xb") as outgoing:
                        shutil.copyfileobj(incoming, outgoing, MIB)
                    target.chmod((mode & 0o777) or 0o644)
            # CodexAstraUlt: Links are created last, so no extraction can write
            # through a link; each final chain must still stay in this archive root.
            for target, link in links:
                require(not Path(link).is_absolute(), "Absolute archive symlink")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(link)
            for target, _ in links:
                require(target.resolve().is_relative_to(destination / expected_root), "Archive link escapes its root")
    else:
        with tarfile.open(archive) as source:
            entries = source.getmembers()
            require(len(entries) <= 100_000, "Archive entry count exceeds bound")
            for item in entries:
                relative = member_path(item.name)
                require(relative.parts[0] == expected_root and str(relative) not in seen,
                        "Archive root or duplicate member differs")
                seen.add(str(relative))
                require(item.isfile() or item.isdir() or item.issym() or item.islnk(), "Archive contains a special file")
                total += item.size
                require(total <= 4 * 1024 * MIB, "Expanded archive exceeds bound")
            source.extractall(destination, members=entries, filter="data")
    result = destination / expected_root
    require(result.is_dir() and not result.is_symlink(), "Expected archive root is absent")
    # CodexAstraUlt: Tar's data filter confines links to staging; impose the
    # tighter single-component root too, before any installer binary is executed.
    for path in result.rglob("*"):
        if path.is_symlink():
            require(path.resolve().is_relative_to(result), "Archive link escapes its component")
    return result


def inventory(root):
    """CodexAstraUlt: Reuse verifies installed bytes and modes, not just a marker."""
    rows = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            require(path.resolve().is_relative_to(root), "Installed component link escapes its root")
            rows.append({"path": relative, "link": os.readlink(path)})
        elif path.is_file():
            rows.append({"path": relative, "bytes": path.stat().st_size,
                         "mode": stat.S_IMODE(path.stat().st_mode), "sha256": digest(path)})
        else:
            require(path.is_dir(), "Installed component contains a special file")
    require(rows, "Installed component is empty")
    return rows


def acquire(package, root, cache, offline):
    """CodexAstraUlt: Public downloads retain TLS/proxy policy and require pinned SHA-256."""
    name = package["url"].rsplit("/", 1)[-1]
    member_path(name)
    destination = root / "archives" / name
    for candidate in (destination, cache / name if cache else None):
        if candidate is not None and candidate.exists():
            require(candidate.is_file() and not candidate.is_symlink(), "Archive cache entry is not a plain file")
            require(candidate.stat().st_size <= package["maximum_bytes"], "Cached archive exceeds size bound")
            require(digest(candidate) == package["sha256"], "Cached archive checksum mismatch: " + name)
            return candidate
    require(not offline, "Required archive is not cached: " + name)
    print("Download " + name, flush=True)
    partial = destination.with_name(name + "." + uuid.uuid4().hex + ".partial")
    started = time.monotonic()
    try:
        request = urllib.request.Request(package["url"], headers={"User-Agent": "DroiDDS-tool-setup/1"})
        with urllib.request.urlopen(request, timeout=60) as response, partial.open("xb") as stream:
            size = 0
            while chunk := response.read(MIB):
                size += len(chunk)
                require(size <= package["maximum_bytes"] and time.monotonic() - started <= 1800,
                        "Archive download exceeds its size/time bound")
                stream.write(chunk)
        require(digest(partial) == package["sha256"], "Downloaded archive checksum mismatch: " + name)
        os.replace(partial, destination)
    finally:
        if partial.exists():
            partial.unlink()
    return destination


def run(root, name, command, environment, timeout=120):
    """CodexAstraUlt: Bounded owned processes retain local logs and never prompt for credentials."""
    log = root / "logs" / (name + "-" + uuid.uuid4().hex + ".log")
    with log.open("xb") as stream:
        process = subprocess.Popen([str(part) for part in command], env=environment,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
        deadline = time.monotonic() + timeout
        size = 0
        try:
            # CodexAstraUlt: Drain through a capped pipe instead of discovering
            # an oversized log only after a failed process has filled storage.
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while selector.get_map():
                    remaining = deadline - time.monotonic()
                    require(remaining > 0, name + " exceeded its time bound")
                    for key, _ in selector.select(min(remaining, 0.5)):
                        chunk = os.read(key.fd, 64 * 1024)
                        if not chunk:
                            selector.unregister(key.fileobj)
                            break
                        require(size + len(chunk) <= 32 * MIB, name + " output exceeds bound")
                        stream.write(chunk)
                        size += len(chunk)
            result = process.wait(timeout=max(0.01, deadline - time.monotonic()))
        except BaseException as error:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=5)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
            raise RuntimeError(name + " stopped: " + str(error) + "; see " + str(log)) from None
        finally:
            process.stdout.close()
    require(result == 0, name + " failed; see " + str(log))
    require(log.stat().st_size <= 32 * MIB, name + " output exceeds bound")
    return log.read_text(errors="replace")


def component(root, name, destination, packages, catalog, args, installer=None):
    """CodexAstraUlt: Publish a complete validated component atomically; reuse is read-only."""
    destination = plain_path(destination)
    receipt = plain_path(root / "receipts" / (name + ".json"))
    wanted = {key: catalog[key]["sha256"] for key in packages}
    if destination.exists():
        require(destination.is_dir() and not destination.is_symlink() and receipt.is_file()
                and not receipt.is_symlink(), "Existing component has no valid receipt: " + name)
        record = json.loads(receipt.read_text())
        require(record.get("archives") == wanted and record.get("files") == inventory(destination),
                "Installed component changed: " + name)
        print("Reuse " + name, flush=True)
        return
    if receipt.exists():
        require(receipt.is_file() and json.loads(receipt.read_text()).get("archives") == wanted,
                "Interrupted component receipt differs: " + name)
    staging = Path(tempfile.mkdtemp(prefix=".stage-" + name + "-", dir=root))
    try:
        extracted = []
        for index, key in enumerate(packages):
            package = catalog[key]
            archive = acquire(package, root, args.archive_cache, args.offline)
            extracted.append(unpack(archive, staging / str(index), package["root"]))
        if installer:
            ready = installer(staging, extracted)
        else:
            require(len(extracted) == 1, "Component archive count differs")
            ready = extracted[0]
        files = inventory(ready)
        destination.parent.mkdir(parents=True, exist_ok=True)
        require(not destination.exists(), "Component appeared during setup")
        # CodexAstraUlt: Publish the receipt first; interruption before rename
        # can retry, while every published component already has its receipt.
        atomic_json(receipt, {"schema_version": 1, "archives": wanted, "files": files})
        os.rename(ready, destination)
        print("Installed " + name, flush=True)
    finally:
        shutil.rmtree(staging)


def environment(root, sdk, java):
    """CodexAstraUlt: Every writable compiler/cache location belongs to this setup."""
    value = dict(os.environ)
    value.update(CARGO_HOME=str(root / "cargo"), RUSTUP_HOME=str(root / "unused-rustup"),
                 RUSTC=str(root / "rust/bin/rustc"), JAVA_HOME=str(java),
                 ANDROID_HOME=str(sdk), ANDROID_SDK_ROOT=str(sdk),
                 GIT_TERMINAL_PROMPT="0", CARGO_NET_GIT_FETCH_WITH_CLI="true")
    value["PATH"] = str(root / "rust/bin") + os.pathsep + str(java / "bin") + os.pathsep + value.get("PATH", "")
    value.pop("RUSTUP_TOOLCHAIN", None)
    value.pop("CARGO_ENCODED_RUSTFLAGS", None)
    value.pop("RUSTFLAGS", None)
    return value


def verify_tools(root, sdk, java, env):
    """CodexAstraUlt: Exercise actual binaries and the Android standard library."""
    for relative in (f"ndk/{NDK}/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android29-clang",
                     f"ndk/{NDK}/shader-tools/linux-x86_64/glslc", f"ndk/{NDK}/shader-tools/linux-x86_64/spirv-val",
                     f"build-tools/{TOOLS}/aapt2", f"build-tools/{TOOLS}/d8",
                     f"build-tools/{TOOLS}/zipalign", f"build-tools/{TOOLS}/apksigner",
                     "platforms/android-35/android.jar"):
        require((sdk / relative).is_file(), "Missing Android tool: " + relative)
    properties = (sdk / "ndk" / NDK / "source.properties").read_text()
    require(re.search(r"^Pkg.Revision\s*=\s*27\.3\.13750724\s*$", properties, re.M), "Wrong NDK revision")
    properties = (sdk / "build-tools" / TOOLS / "source.properties").read_text()
    require(re.search(r"^Pkg.Revision\s*=\s*35\.0\.0\s*$", properties, re.M), "Wrong build-tools revision")
    properties = (sdk / "platforms/android-35/source.properties").read_text()
    require(re.search(r"^AndroidVersion.ApiLevel\s*=\s*35\s*$", properties, re.M), "Wrong Android platform")
    versions = {}
    versions["rustc"] = run(root, "rust-version", [env["RUSTC"], "--version"], env).strip()
    require(versions["rustc"].startswith("rustc 1.95.0 "), "Wrong Rust version")
    versions["cargo"] = run(root, "cargo-version", [root / "rust/bin/cargo", "--version"], env).strip()
    versions["javac"] = run(root, "java-version", [java / "bin/javac", "-version"], env).strip()
    require(versions["javac"].startswith("javac 17."), "JDK 17 is required")
    library = Path(run(root, "android-stdlib", [env["RUSTC"], "--print", "target-libdir", "--target", TARGET], env).strip())
    require(library.is_dir() and any(library.glob("libstd-*.rlib")), "Rust Android standard library is missing")
    versions["clang"] = run(root, "clang-version", [sdk / f"ndk/{NDK}/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android29-clang", "--version"], env).splitlines()[0]
    for name, relative, option in (("aapt2", f"build-tools/{TOOLS}/aapt2", "version"),
                                  ("d8", f"build-tools/{TOOLS}/d8", "--version"),
                                  ("apksigner", f"build-tools/{TOOLS}/apksigner", "version"),
                                  ("glslc", f"ndk/{NDK}/shader-tools/linux-x86_64/glslc", "--version"),
                                  ("spirv-val", f"ndk/{NDK}/shader-tools/linux-x86_64/spirv-val", "--version")):
        versions[name] = run(root, name + "-version", [sdk / relative, option], env).splitlines()[0]
    # CodexAstraUlt: Link a tiny authored Android library to exercise the Rust
    # target, NDK linker and system stubs without running any game or device.
    probe = plain_path(root / "target-check.rs")
    library_output = plain_path(root / "target-check.so")
    atomic_text(probe, "// CodexAstraUlt: Original Android toolchain installation check.\n#[no_mangle]\npub extern \"C\" fn droidds_setup_check() -> usize { std::mem::size_of::<usize>() }\n")
    linker = sdk / f"ndk/{NDK}/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android29-clang"
    run(root, "android-rust-check", [env["RUSTC"], "--crate-name", "droidds_setup_check", "--crate-type", "cdylib",
        "--target", TARGET, "-C", "linker=" + str(linker), probe, "-o", library_output], env)
    header = library_output.read_bytes()[:20]
    require(header[:6] == b"\x7fELF\x02\x01" and header[18:20] == b"\xb7\x00", "Android link did not produce AArch64 ELF")
    return versions


def write_environment(root, sdk, java):
    """CodexAstraUlt: Sourcing this explicit file affects only the calling shell."""
    values = {"DROIDDS_SDK": sdk, "DROIDDS_JAVA": java, "ANDROID_HOME": sdk, "ANDROID_SDK_ROOT": sdk,
              "JAVA_HOME": java, "CARGO_HOME": root / "cargo", "RUSTUP_HOME": root / "unused-rustup",
              "RUSTC": root / "rust/bin/rustc"}
    lines = ["# CodexAstraUlt: Project-local build tools; no shell profile was changed."]
    lines += ["export " + key + "=" + shlex.quote(str(value)) for key, value in values.items()]
    lines += ["export PATH=" + shlex.quote(str(root / "rust/bin") + ":" + str(java / "bin")) + ':"$PATH"',
              "unset RUSTUP_TOOLCHAIN CARGO_ENCODED_RUSTFLAGS RUSTFLAGS",
              "export GIT_TERMINAL_PROMPT=0 CARGO_NET_GIT_FETCH_WITH_CLI=true", ""]
    atomic_text(root / "env.sh", "\n".join(lines))


def setup(args):
    require(sys.version_info >= (3, 11), "Setup requires Python 3.11 or newer")
    require(platform.system() == "Linux" and platform.machine() == "x86_64", "Setup requires Linux x86-64")
    require(shutil.which("cc") and shutil.which("git") and shutil.which("sh"), "Existing cc, git and sh are required")
    repository = args.repository.resolve(strict=True)
    require((repository / "Cargo.lock").is_file() and (repository / "Cargo.toml").is_file(), "DroiDDS checkout is missing")
    catalog_bytes = MANIFEST.read_bytes()
    catalog = json.loads(catalog_bytes)
    validate_catalog(catalog)
    lock_before = digest(repository / "Cargo.lock")
    with owned_root(args.output, hashlib.sha256(catalog_bytes).hexdigest()) as root:
        report = {"schema_version": 1, "kind": KIND, "manifest_sha256": hashlib.sha256(catalog_bytes).hexdigest(),
                  "status": "installing", "cargo_lock_sha256": lock_before,
                  "system_packages_changed": False, "existing_rust_changed": False,
                  "game_execution_performed": False}
        try:
            require(shutil.disk_usage(root).free >= 6 * 1024 * MIB, "Setup needs at least 6 GiB free for extraction and dependencies")
            sdk = args.reuse_sdk.resolve(strict=True) if args.reuse_sdk else root / "sdk"
            java = args.reuse_java_home.resolve(strict=True) if args.reuse_java_home else root / "jdk"
            env = environment(root, sdk, java)
            packages = catalog["packages"]
            if not args.reuse_sdk:
                for name, relative in (("ndk", f"sdk/ndk/{NDK}"), ("build_tools", f"sdk/build-tools/{TOOLS}"),
                                       ("platform", "sdk/platforms/android-35")):
                    component(root, name, root / relative, [name], packages, args)
            if not args.reuse_java_home:
                component(root, "jdk", java, ["jdk"], packages, args)

            def rust_install(staging, extracted):
                prefix = staging / "installed"
                for index, package in enumerate(extracted):
                    run(root, "install-rust-" + str(index), ["sh", package / "install.sh",
                        "--prefix=" + str(prefix), "--disable-ldconfig"], env, timeout=300)
                return prefix

            component(root, "rust", root / "rust", ["rustc", "cargo", "rust_std_host", "rust_std_android"],
                      packages, args, rust_install)
            report["versions"] = verify_tools(root, sdk, java, env)
            print("Populate locked Cargo dependencies in the owned cache", flush=True)
            command = [root / "rust/bin/cargo", "fetch", "--locked", "--manifest-path", repository / "Cargo.toml"]
            if args.offline:
                command.append("--offline")
            run(root, "cargo-fetch", command, env, timeout=1800)
            run(root, "cargo-offline-check", [root / "rust/bin/cargo", "metadata", "--offline", "--locked",
                "--format-version", "1", "--manifest-path", repository / "Cargo.toml"], env, timeout=300)
            require(digest(repository / "Cargo.lock") == lock_before, "Cargo lock changed during setup")
            write_environment(root, sdk, java)
            report.update(status="ready", sdk=str(sdk), java_home=str(java), rust=str(root / "rust"),
                          cargo_home=str(root / "cargo"), environment=str(root / "env.sh"),
                          reused_sdk=bool(args.reuse_sdk), reused_java_home=bool(args.reuse_java_home))
        except BaseException as error:
            report.update(status="failed", error=type(error).__name__ + ": " + str(error))
            atomic_json(root / "setup-state.json", report)
            raise
        atomic_json(root / "setup-state.json", report)
        print(json.dumps({key: report[key] for key in ("status", "environment", "sdk", "java_home", "cargo_home")}, indent=2))
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repository", type=Path, default=ROOT)
    parser.add_argument("--archive-cache", type=Path)
    parser.add_argument("--reuse-sdk", type=Path)
    parser.add_argument("--reuse-java-home", type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    try:
        setup(args)
    except (Exception, KeyboardInterrupt) as error:
        print("Setup stopped: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
