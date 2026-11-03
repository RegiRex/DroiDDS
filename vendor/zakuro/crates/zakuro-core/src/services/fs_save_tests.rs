//! CodexAstraUlt: Original host/IPC controls distinguish durable requested
//! operations from false success; no owner save or game input is used here.

use super::*;
use crate::memory::{MemoryRegion, MemoryState, Permission};
use std::sync::atomic::{AtomicU64, Ordering};

static NEXT: AtomicU64 = AtomicU64::new(0);
const BASE: u32 = 0x0010_0000;
const MAPPED: u32 = 0x0008_0000;

struct Scratch(PathBuf);
impl Scratch {
    fn new() -> Self {
        let time = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path = std::env::temp_dir().join(format!(
            "droidds-save-{}-{time}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        std::fs::create_dir(&path).unwrap();
        Self(path)
    }
}
impl Drop for Scratch {
    fn drop(&mut self) {
        std::fs::remove_dir_all(&self.0).unwrap();
    }
}

fn system() -> System {
    let mut system = System::new(crate::Config::default());
    let block = system
        .memory
        .phys
        .allocate(MemoryRegion::Application, MAPPED)
        .unwrap();
    system.memory.map(
        BASE,
        block.addr,
        MAPPED,
        Permission::RW,
        MemoryState::Private,
    );
    system
}

fn file(system: &mut System, path: PathBuf, access: u32, dirty: bool) -> u32 {
    system.services.fs.add_file(OpenFile {
        path: "original-save".into(),
        backing: FileBacking::Host(path),
        access,
        dirty,
    })
}

fn request(system: &mut System, command: u16, parameters: &[u32]) -> CommandBuffer {
    let buffer = CommandBuffer::new(BASE);
    for index in 0..16 {
        buffer.set(&mut system.memory, index, 0);
    }
    buffer.set(
        &mut system.memory,
        0,
        Header::new(command, parameters.len() as u32, 0).0,
    );
    for (index, value) in parameters.iter().enumerate() {
        buffer.set(&mut system.memory, index as u32 + 1, *value);
    }
    buffer
}

fn file_request(system: &mut System, id: u32, command: u16, parameters: &[u32]) -> u32 {
    let buffer = request(system, command, parameters);
    let header = buffer.header(&mut system.memory);
    assert!(file_command(system, &buffer, header, id));
    buffer.get(&mut system.memory, 1)
}

// CodexAstraUlt: A helper error cannot become zero bytes of apparent success;
// EOF and empty operations remain valid, and explicit flush supports write-only
// host files without requiring permission to read their contents.
#[test]
fn host_io_preserves_errors_eof_and_requested_flush() {
    let scratch = Scratch::new();
    let path = scratch.0.join("save.bin");
    std::fs::write(&path, b"original").unwrap();
    let mut bytes = [0u8; 16];
    assert_eq!(host_archive::read_at(&path, 8, &mut bytes), Ok(0));
    assert_eq!(host_archive::read_at(&path, 0, &mut []), Ok(0));
    assert_eq!(host_archive::write_at(&path, 0, &[], false), Ok(0));
    assert_eq!(host_archive::write_at(&path, 2, b"DATA", true), Ok(4));
    assert_eq!(std::fs::read(&path).unwrap(), b"orDATAal");
    let missing = scratch.0.join("missing");
    for candidate in [&missing, &scratch.0] {
        assert!(host_archive::read_at(candidate, 0, &mut bytes).is_err());
        assert!(host_archive::write_at(candidate, 0, b"no", true).is_err());
        assert!(host_archive::flush_file(candidate).is_err());
        assert!(host_archive::checked_size(candidate).is_err());
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o200)).unwrap();
        assert_eq!(host_archive::write_at(&path, 0, b"ok", true), Ok(2));
        assert_eq!(host_archive::flush_file(&path), Ok(()));
        std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o600)).unwrap();
    }
}

// CodexAstraUlt: Rights and dirty state survive the actual postcard encoding.
// An independently declared legacy layout cannot accidentally acquire write
// access merely because the new decoder now supports explicit permissions.
#[test]
fn saved_host_permissions_and_dirty_state_round_trip_without_legacy_write_grant() {
    #[derive(serde::Serialize)]
    #[allow(dead_code)]
    enum OldBacking {
        RomImage { image: u32, offset: u64, size: u64 },
        Host(PathBuf),
        Memory(Vec<u8>),
        Layered { layered: u32, image: u32 },
    }
    #[derive(serde::Serialize)]
    struct OldFile {
        path: String,
        backing: OldBacking,
    }
    let path = PathBuf::from("original-test-save.bin");
    let old = OldFile {
        path: "/save".into(),
        backing: OldBacking::Host(path.clone()),
    };
    let bytes = postcard::to_allocvec(&old).unwrap();
    let restored: SavedFile = postcard::from_bytes(&bytes).unwrap();
    let restored = restored.open((&[], &[])).unwrap();
    assert_eq!(restored.access, OPEN_READ);
    assert!(!restored.dirty);
    for access in [OPEN_READ, OPEN_WRITE, OPEN_READ | OPEN_WRITE] {
        for dirty in [false, true] {
            let original = OpenFile {
                path: "/save".into(),
                backing: FileBacking::Host(path.clone()),
                access,
                dirty,
            };
            let bytes = postcard::to_allocvec(&original.save((&[], &[])).unwrap()).unwrap();
            let saved: SavedFile = postcard::from_bytes(&bytes).unwrap();
            let restored = saved.open((&[], &[])).unwrap();
            assert_eq!((restored.access, restored.dirty), (access, dirty));
        }
    }
    for access in [0, OPEN_CREATE, u32::MAX] {
        let saved = SavedFile {
            path: "/save".into(),
            backing: SavedBacking::HostWithAccess {
                path: path.clone(),
                access,
                dirty: false,
            },
        };
        assert!(saved.open((&[], &[])).is_none());
    }
}

// CodexAstraUlt: One operation spans several staging chunks; exact byte output
// is independent of chunking. An invalid final source page must fail before any
// partial write, including when the first source byte is otherwise readable.
#[test]
fn chunked_save_round_trip_and_invalid_source_preserve_existing_file() {
    let scratch = Scratch::new();
    let path = scratch.0.join("save.bin");
    std::fs::write(&path, b"prefix").unwrap();
    let mut system = system();
    let id = file(&mut system, path.clone(), OPEN_READ | OPEN_WRITE, false);
    let data: Vec<_> = (0..IO_CHUNK * 2 + 17)
        .map(|index| (index % 251) as u8)
        .collect();
    system.memory.write_bytes(BASE + 0x1000, &data);
    assert_eq!(
        write_file(&mut system, id, 6, data.len() as u32, BASE + 0x1000, false),
        Ok(data.len() as u32)
    );
    assert!(system.services.fs.files[&id].dirty);
    assert_eq!(flush_file_id(&mut system, id, true), Ok(()));
    assert!(!system.services.fs.files[&id].dirty);
    assert_eq!(
        read_file(&mut system, id, 6, data.len() as u32, BASE + 0x40000),
        Ok(data.len() as u32)
    );
    let mut output = vec![0u8; data.len()];
    system.memory.read_bytes(BASE + 0x40000, &mut output);
    assert_eq!(output, data);
    let before = std::fs::read(&path).unwrap();
    for (source, size) in [(BASE + MAPPED - 1, 2), (u32::MAX, 2), (BASE, u32::MAX)] {
        assert_eq!(
            write_file(&mut system, id, 0, size, source, false),
            Err(errors::FS_INVALID_PATH)
        );
        assert_eq!(std::fs::read(&path).unwrap(), before);
        assert!(!system.services.fs.files[&id].dirty);
    }
    assert_eq!(system.memory.fault_observation().0, 0);
}

// CodexAstraUlt: Core IPC controls verify access failures, missing metadata and
// zero/EOF reads independently of the authored CPU integration test.
#[test]
fn file_ipc_access_size_and_empty_reads_report_real_results() {
    let scratch = Scratch::new();
    let path = scratch.0.join("save.bin");
    std::fs::write(&path, b"original").unwrap();
    let mut system = system();
    let read = file(&mut system, path.clone(), OPEN_READ, false);
    let write = file(&mut system, path.clone(), OPEN_WRITE, false);
    system.memory.write_bytes(BASE + 0x1000, b"NEW");
    assert_eq!(
        file_request(
            &mut system,
            read,
            0x0803,
            &[0, 0, 3, 0, 0x3a, BASE + 0x1000]
        ),
        INVALID_OPEN_FLAGS.0
    );
    assert_eq!(
        file_request(&mut system, write, 0x0802, &[0, 0, 3, 0x3c, BASE + 0x2000]),
        INVALID_OPEN_FLAGS.0
    );
    assert_eq!(
        file_request(&mut system, read, 0x0805, &[1, 0]),
        INVALID_OPEN_FLAGS.0
    );
    assert_eq!(std::fs::read(&path).unwrap(), b"original");
    for (offset, size) in [(8, 3), (0, 0)] {
        assert_eq!(
            file_request(
                &mut system,
                read,
                0x0802,
                &[offset, 0, size, (size << 4) | 0xc, BASE + 0x2000]
            ),
            0
        );
        assert_eq!(CommandBuffer::new(BASE).get(&mut system.memory, 2), 0);
    }
    std::fs::remove_file(&path).unwrap();
    std::fs::create_dir(&path).unwrap();
    assert_eq!(
        file_request(&mut system, read, 0x0804, &[]),
        errors::FS_UNEXPECTED_FILE_OR_DIRECTORY.0
    );
    assert_eq!(
        file_request(&mut system, write, 0x0805, &[1, 0]),
        errors::FS_UNEXPECTED_FILE_OR_DIRECTORY.0
    );
    assert!(system.services.fs.files[&write].dirty);
}

// CodexAstraUlt: The unrelated archive deliberately contains a broken dirty
// backing. Committing this archive must not touch it; failed Close keeps its
// file record so a later repair/retry can synchronize successfully.
#[test]
fn commit_targets_one_archive_and_failed_close_retains_dirty_file() {
    let scratch = Scratch::new();
    let selected = HostArchive::at(scratch.0.join("selected"));
    let unrelated = HostArchive::at(scratch.0.join("unrelated"));
    for archive in [&selected, &unrelated] {
        archive.format(FormatInfo::default()).unwrap();
        archive.create_file("save", 1).unwrap();
    }
    let good = selected.resolve("save").unwrap();
    let bad = unrelated.resolve("save").unwrap();
    let mut system = system();
    let good_id = file(&mut system, good, OPEN_READ | OPEN_WRITE, true);
    let bad_id = file(&mut system, bad.clone(), OPEN_READ | OPEN_WRITE, true);
    std::fs::remove_file(&bad).unwrap();
    std::fs::create_dir(&bad).unwrap();
    let archive = system.services.fs.add_archive(OpenArchive {
        id: ARCHIVE_SAVEDATA,
        ncch_path: None,
        host: Some(selected),
    });
    for (handle, action, expected) in [
        (archive + 100, 0, errors::FS_ARCHIVE_NOT_MOUNTED.0),
        (archive, 1, errors::FS_NOT_IMPLEMENTED.0),
        (archive, 0, 0),
    ] {
        let buffer = request(
            &mut system,
            0x080d,
            &[
                handle as u32,
                (handle >> 32) as u32,
                action,
                0,
                0,
                0,
                0,
                0,
                0,
            ],
        );
        assert!(user_command(
            &mut system,
            &buffer,
            Header::new(0x080d, 5, 4)
        ));
        assert_eq!(buffer.get(&mut system.memory, 1), expected);
    }
    assert!(!system.services.fs.files[&good_id].dirty);
    assert!(system.services.fs.files[&bad_id].dirty);
    assert_eq!(
        file_request(&mut system, bad_id, 0x0808, &[]),
        errors::FS_UNEXPECTED_FILE_OR_DIRECTORY.0
    );
    assert!(system.services.fs.files[&bad_id].dirty);
    std::fs::remove_dir(&bad).unwrap();
    std::fs::write(&bad, b"repaired").unwrap();
    assert_eq!(file_request(&mut system, bad_id, 0x0808, &[]), 0);
    assert!(!system.services.fs.files.contains_key(&bad_id));
}
