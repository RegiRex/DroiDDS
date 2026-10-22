# Laptop setup and eventual cleanup

<!-- CodexAstraUlt: Persist the owner's 2026-10-22 request for selective cleanup
after testing, without treating that request as permission to remove tools now. -->
The owner wants exact commands to remove development additions when this work is
finished, while preserving software and data that were already on the Nobara
laptop. Prepare those commands from the actual local inventory; do not remove
anything automatically or during ongoing testing. Install another tool only
when a concrete build or diagnostic requires it. The current host baseline
already runs, so a longer bounded run does not require another tool installation.

<!-- CodexAstraUlt: Distinguish requested installation from measured ownership;
the cloud session has not inspected the laptop's package or Rust history. -->
The setup instructions requested `git`, `gcc`, `curl` and `python3` through DNF,
Rustup if missing, Rust 1.95.0 with rustfmt/clippy, locked Cargo dependencies and
a release worker build. This list does not prove that every package was newly
installed. No pre-install inventory was captured by that procedure. The owner
reports substantial additions; exact package changes and sizes remain for local
inspection. Toolchains, dependency caches and build artifacts can occupy
substantial disk space. Their presence alone does not show that background work
is running; these setup instructions did not configure a background service.

## Record before further changes

<!-- CodexAstraUlt: Recover a selective cleanup record without guessing which
preexisting packages or shared development tools belong to DroidDS. -->
Local Codex should keep a cleanup inventory outside Git, using read-only checks:

- Find the actual setup transaction with `dnf history list`, then inspect its
  ID using `dnf history info`. Record newly installed packages separately from
  already present packages and upgrades; retain relevant setup console output.
- Record the Rustup installation, toolchain list and actual Cargo/Rustup storage
  locations. Use the earlier setup/session evidence to determine whether Rustup
  and Rust 1.95.0 were newly added. Current presence or timestamps alone do not
  establish that they were absent before setup. Preserve anything of uncertain
  ownership and check whether another project now needs a newly added tool.
- Record the exact checkout, effective Cargo build-output directory, shared
  dependency caches and their sizes. A configured target directory may be
  outside the checkout or shared, so do not infer its ownership from its name.
- Record each private baseline directory and distinguish its full `input.*`
  game snapshot from small reports. Keep the original game, saves, source
  changes, signing material and diagnostic summaries outside the removal list.

## Prepare cleanup when finished

<!-- CodexAstraUlt: Require concrete, reviewed removal scope instead of a broad
undo that can remove system tools, other projects' caches or private originals. -->
Provide the owner with exact paths/package names, estimated recoverable space,
and separate commands for each verified category. Start with disposable,
exclusively owned build output and redundant staged game copies, retaining the
reports and original input. Preserve any run still needed to reproduce a result.

Remove a Rust toolchain only when it was added for this work and is no longer
needed. Full Rustup removal is appropriate only if the entire installation was
new for this task and has no other users/projects. Shared Cargo caches must not
be deleted wholesale. Package removals need the actual DNF history and a reviewed
transaction preview showing their dependency effects; retain uncertain items.

Do not prescribe blanket removal of `git gcc curl python3`, blind DNF history
undo/autoremove, or recursive deletion of shared Cargo/Rustup directories. Those
operations are not equivalent to undoing only this project's additions. No final
removal command is established until local evidence identifies its exact scope.
