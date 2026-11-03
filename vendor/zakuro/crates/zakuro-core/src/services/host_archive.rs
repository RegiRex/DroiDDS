//! writable archives, kept as directories on the host.

use std::io::{Read, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};

use zakuro_common::result::{errors, ResultCode};

/// how an archive was formatted, which is what GetFormatInfo reports.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct FormatInfo {
    pub total_size: u32,
    pub directories: u32,
    pub files: u32,
    pub duplicate_data: bool,
}

impl FormatInfo {
    fn encode(self) -> [u8; 16] {
        let mut out = [0u8; 16];
        out[0..4].copy_from_slice(&self.total_size.to_le_bytes());
        out[4..8].copy_from_slice(&self.directories.to_le_bytes());
        out[8..12].copy_from_slice(&self.files.to_le_bytes());
        out[12] = self.duplicate_data as u8;
        out
    }

    fn decode(data: &[u8]) -> Option<FormatInfo> {
        let word = |i: usize| Some(u32::from_le_bytes(data.get(i..i + 4)?.try_into().ok()?));
        Some(FormatInfo {
            total_size: word(0)?,
            directories: word(4)?,
            files: word(8)?,
            duplicate_data: *data.get(12)? != 0,
        })
    }
}

/// one entry of a directory listing.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct DirectoryEntry {
    pub name: String,
    pub is_directory: bool,
    pub size: u64,
}

/// a writable archive, a host directory standing in for one of the
/// console's save filesystems.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct HostArchive {
    root: PathBuf,
}

impl HostArchive {
    pub fn at(root: impl Into<PathBuf>) -> HostArchive {
        HostArchive { root: root.into() }
    }

    /// the running title's own save data.
    pub fn save_data(base: &Path, program_id: u64) -> HostArchive {
        HostArchive::at(base.join("savedata").join(format!("{program_id:016X}")))
    }

    /// extra data, which titles keep outside their save, caches, downloaded
    /// content, data shared between versions of a game.
    pub fn ext_data(base: &Path, id: u64, shared: bool) -> HostArchive {
        let dir = if shared { "extdata/shared" } else { "extdata" };
        HostArchive::at(base.join(dir).join(format!("{id:016X}")))
    }

    pub fn system_save_data(base: &Path, id: u64) -> HostArchive {
        HostArchive::at(base.join("nand/system-save").join(format!("{id:016X}")))
    }

    pub fn sdmc(base: &Path) -> HostArchive {
        HostArchive::at(base.join("sdmc"))
    }

    pub fn exists(&self) -> bool {
        self.root.is_dir()
    }

    // CodexAstraUlt: Commit selection is limited to files under this archive;
    // it never scans the SD card or synchronizes unrelated title storage.
    pub fn contains_file(&self, path: &Path) -> bool {
        path != self.root && path.starts_with(&self.root)
    }

    /// creates the archive empty, discarding anything already in it, both
    /// how a title makes its save the first time and how it wipes one.
    pub fn format(&self, info: FormatInfo) -> Result<(), ResultCode> {
        if self.root.exists() {
            std::fs::remove_dir_all(&self.root).map_err(io_error)?;
        }
        create_directories_synced(&self.root)?;
        std::fs::write(self.format_path(), info.encode()).map_err(io_error)?;
        // CodexAstraUlt: Formatting is explicitly destructive, but success
        // still includes syncing its touched metadata, not unrelated archives.
        flush_file(&self.format_path())?;
        sync_parent(&self.format_path())?;
        log::info!("fs: formatted {:?}", self.root);
        Ok(())
    }

    /// removes the archive entirely, so it reads as never created.
    pub fn delete(&self) -> Result<(), ResultCode> {
        if !self.exists() {
            return Err(errors::FS_NOT_FOUND_INVALID_STATE);
        }
        std::fs::remove_dir_all(&self.root).map_err(io_error)?;
        let _ = std::fs::remove_file(self.format_path());
        sync_parent(&self.root)
    }

    /// what the archive was formatted with, or None if it never was.
    pub fn format_info(&self) -> Option<FormatInfo> {
        if !self.exists() {
            return None;
        }
        let data = std::fs::read(self.format_path()).unwrap_or_default();
        Some(FormatInfo::decode(&data).unwrap_or_default())
    }

    fn format_path(&self) -> PathBuf {
        let mut name = self.root.clone().into_os_string();
        name.push(".format");
        PathBuf::from(name)
    }

    /// maps a path inside the archive to a host path, refusing anything
    /// that would step outside it.
    pub fn resolve(&self, path: &str) -> Result<PathBuf, ResultCode> {
        let mut host = self.root.clone();
        for part in path.split(['/', '\\']) {
            match part {
                "" | "." => {}
                ".." => return Err(errors::FS_INVALID_PATH),
                name => host.push(name),
            }
        }
        Ok(host)
    }

    fn parent_exists(host: &Path) -> bool {
        host.parent().is_some_and(Path::is_dir)
    }

    /// the host file behind path, created empty first if create is set
    /// and it does not exist yet.
    pub fn open_file(&self, path: &str, create: bool) -> Result<PathBuf, ResultCode> {
        let host = self.resolve(path)?;
        if host.is_file() {
            return Ok(host);
        }
        if host.is_dir() {
            return Err(errors::FS_UNEXPECTED_FILE_OR_DIRECTORY);
        }
        if !Self::parent_exists(&host) {
            return Err(errors::FS_PATH_NOT_FOUND);
        }
        if !create {
            return Err(errors::FS_FILE_NOT_FOUND);
        }
        let file = std::fs::File::create(&host).map_err(io_error)?;
        file.sync_all().map_err(io_error)?;
        sync_parent(&host)?;
        Ok(host)
    }

    pub fn create_file(&self, path: &str, size: u64) -> Result<(), ResultCode> {
        let host = self.resolve(path)?;
        if host.exists() {
            return Err(errors::FS_FILE_ALREADY_EXISTS);
        }
        if !Self::parent_exists(&host) {
            return Err(errors::FS_PATH_NOT_FOUND);
        }
        let file = std::fs::File::create(&host).map_err(io_error)?;
        file.set_len(size).map_err(io_error)?;
        file.sync_all().map_err(io_error)?;
        sync_parent(&host)
    }

    pub fn delete_file(&self, path: &str) -> Result<(), ResultCode> {
        let host = self.resolve(path)?;
        if !host.is_file() {
            return Err(errors::FS_FILE_NOT_FOUND);
        }
        std::fs::remove_file(&host).map_err(io_error)?;
        sync_parent(&host)
    }

    pub fn rename_file(&self, from: &str, to: &str) -> Result<(), ResultCode> {
        let (from, to) = (self.resolve(from)?, self.resolve(to)?);
        if !from.is_file() {
            return Err(errors::FS_FILE_NOT_FOUND);
        }
        if to.exists() {
            return Err(errors::FS_FILE_ALREADY_EXISTS);
        }
        std::fs::rename(&from, &to).map_err(io_error)?;
        sync_parent(&from)?;
        if from.parent() != to.parent() { sync_parent(&to)?; }
        Ok(())
    }

    pub fn create_directory(&self, path: &str) -> Result<(), ResultCode> {
        let host = self.resolve(path)?;
        if host.exists() {
            return Err(errors::FS_DIRECTORY_ALREADY_EXISTS);
        }
        if !Self::parent_exists(&host) {
            return Err(errors::FS_PATH_NOT_FOUND);
        }
        std::fs::create_dir(&host).map_err(io_error)?;
        std::fs::File::open(&host).and_then(|dir| dir.sync_all()).map_err(io_error)?;
        sync_parent(&host)
    }

    pub fn delete_directory(&self, path: &str, recursive: bool) -> Result<(), ResultCode> {
        let host = self.resolve(path)?;
        if !host.is_dir() || host == self.root {
            return Err(errors::FS_PATH_NOT_FOUND);
        }
        if recursive {
            std::fs::remove_dir_all(&host).map_err(io_error)?;
            return sync_parent(&host);
        }
        if std::fs::read_dir(&host).map_err(io_error)?.next().is_some() {
            return Err(errors::FS_DIRECTORY_NOT_EMPTY);
        }
        std::fs::remove_dir(&host).map_err(io_error)?;
        sync_parent(&host)
    }

    pub fn rename_directory(&self, from: &str, to: &str) -> Result<(), ResultCode> {
        let (from, to) = (self.resolve(from)?, self.resolve(to)?);
        if !from.is_dir() {
            return Err(errors::FS_PATH_NOT_FOUND);
        }
        if to.exists() {
            return Err(errors::FS_DIRECTORY_ALREADY_EXISTS);
        }
        std::fs::rename(&from, &to).map_err(io_error)?;
        sync_parent(&from)?;
        if from.parent() != to.parent() { sync_parent(&to)?; }
        Ok(())
    }

    /// lists a directory, sorted by name so the order is stable.
    pub fn list(&self, path: &str) -> Result<Vec<DirectoryEntry>, ResultCode> {
        let host = self.resolve(path)?;
        if !host.is_dir() {
            return Err(errors::FS_PATH_NOT_FOUND);
        }
        let mut entries: Vec<DirectoryEntry> = std::fs::read_dir(host)
            .map_err(io_error)?
            .flatten()
            .filter_map(|entry| {
                let metadata = entry.metadata().ok()?;
                Some(DirectoryEntry {
                    name: entry.file_name().to_string_lossy().into_owned(),
                    is_directory: metadata.is_dir(),
                    size: if metadata.is_dir() { 0 } else { metadata.len() },
                })
            })
            .collect();
        entries.sort_by(|a, b| a.name.cmp(&b.name));
        Ok(entries)
    }
}

// CodexAstraUlt: Metadata operations synchronize only their affected parent
// directories. Ordinary buffered file writes do not call these helpers.
fn sync_parent(path: &Path) -> Result<(), ResultCode> {
    let parent = path.parent().ok_or(errors::FS_INVALID_PATH)?;
    let parent = if parent.as_os_str().is_empty() { Path::new(".") } else { parent };
    std::fs::File::open(parent).and_then(|dir| dir.sync_all()).map_err(io_error)
}

fn create_directories_synced(path: &Path) -> Result<(), ResultCode> {
    let mut missing = Vec::new();
    let mut next = path;
    while !next.exists() {
        missing.push(next);
        next = next.parent().ok_or(errors::FS_INVALID_PATH)?;
        if next.as_os_str().is_empty() { next = Path::new("."); }
    }
    std::fs::create_dir_all(path).map_err(io_error)?;
    for directory in missing.into_iter().rev() {
        std::fs::File::open(directory).and_then(|dir| dir.sync_all()).map_err(io_error)?;
        sync_parent(directory)?;
    }
    Ok(())
}

// CodexAstraUlt: Keep host I/O failures distinct from a legitimate EOF/empty
// write. The service must return an error instead of telling a game it saved.
pub fn open_read_at(path: &Path, offset: u64) -> Result<std::fs::File, ResultCode> {
    let mut file = std::fs::File::open(path).map_err(io_error)?;
    if !file.metadata().map_err(io_error)?.is_file() {
        return Err(errors::FS_UNEXPECTED_FILE_OR_DIRECTORY);
    }
    file.seek(SeekFrom::Start(offset)).map_err(io_error)?;
    Ok(file)
}

pub fn open_write_at(path: &Path, offset: u64) -> Result<std::fs::File, ResultCode> {
    let mut file = std::fs::OpenOptions::new().write(true).open(path).map_err(io_error)?;
    if !file.metadata().map_err(io_error)?.is_file() {
        return Err(errors::FS_UNEXPECTED_FILE_OR_DIRECTORY);
    }
    file.seek(SeekFrom::Start(offset)).map_err(io_error)?;
    Ok(file)
}

pub fn read_at(path: &Path, offset: u64, buffer: &mut [u8]) -> Result<usize, ResultCode> {
    let mut file = open_read_at(path, offset)?;
    let mut total = 0;
    while total < buffer.len() {
        match file.read(&mut buffer[total..]).map_err(io_error)? {
            0 => break,
            n => total += n,
        }
    }
    Ok(total)
}

// CodexAstraUlt: Ordinary writes remain buffered. A caller requests durability
// explicitly; close/commit use flush_file for the affected file only.
pub fn write_at(path: &Path, offset: u64, data: &[u8], flush: bool) -> Result<usize, ResultCode> {
    let mut file = open_write_at(path, offset)?;
    file.write_all(data).map_err(io_error)?;
    if flush {
        file.sync_all().map_err(io_error)?;
    }
    Ok(data.len())
}

pub fn flush_file(path: &Path) -> Result<(), ResultCode> {
    // CodexAstraUlt: Opening a directory can succeed on Linux; it is not an
    // acceptable replacement for the save file that the guest requested.
    // CodexAstraUlt: A successfully written file may be host-write-only. Prefer
    // its write descriptor; a host-read-only file can still flush a clean view.
    let file = match std::fs::OpenOptions::new().write(true).open(path) {
        Ok(file) => file,
        Err(error) if error.kind() == std::io::ErrorKind::PermissionDenied => std::fs::File::open(path).map_err(io_error)?,
        Err(error) => return Err(io_error(error)),
    };
    if !file.metadata().map_err(io_error)?.is_file() { return Err(errors::FS_UNEXPECTED_FILE_OR_DIRECTORY); }
    file.sync_all().map_err(io_error)
}

pub fn size_of(path: &Path) -> u64 {
    std::fs::metadata(path).map_or(0, |m| m.len())
}

// CodexAstraUlt: Guest GetSize propagates failure; display-only legacy size
// observations may still use size_of's zero default.
pub fn checked_size(path: &Path) -> Result<u64, ResultCode> {
    let metadata = std::fs::metadata(path).map_err(io_error)?;
    if !metadata.is_file() { return Err(errors::FS_UNEXPECTED_FILE_OR_DIRECTORY); }
    Ok(metadata.len())
}

pub fn set_size(path: &Path, size: u64) -> Result<(), ResultCode> {
    std::fs::OpenOptions::new()
        .write(true)
        .open(path)
        .and_then(|file| file.set_len(size))
        .map_err(io_error)
}

pub(crate) fn io_error(error: std::io::Error) -> ResultCode {
    log::error!("fs: host filesystem error: {error}");
    // CodexAstraUlt: Preserve concrete known FS failures. Remaining host errors
    // still return a failure, without inventing a console-specific success.
    match error.kind() {
        std::io::ErrorKind::NotFound => errors::FS_FILE_NOT_FOUND,
        std::io::ErrorKind::IsADirectory | std::io::ErrorKind::NotADirectory => errors::FS_UNEXPECTED_FILE_OR_DIRECTORY,
        _ => errors::FS_NOT_IMPLEMENTED,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn scratch(name: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!("zakuro-archive-{name}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        dir
    }

    #[test]
    fn an_archive_that_was_never_formatted_does_not_exist() {
        let base = scratch("fresh");
        let archive = HostArchive::save_data(&base, 0x0004_0000_0011_C500);
        assert!(!archive.exists());
        assert_eq!(archive.format_info(), None);
    }

    #[test]
    fn format_records_its_parameters_and_empties_the_archive() {
        let base = scratch("format");
        let archive = HostArchive::save_data(&base, 1);
        let info = FormatInfo { total_size: 0x10_0000, directories: 4, files: 8, duplicate_data: true };
        archive.format(info).unwrap();
        archive.create_file("/main", 0x100).unwrap();
        assert_eq!(archive.format_info(), Some(info));

        archive.format(info).unwrap();
        assert_eq!(archive.open_file("/main", false), Err(errors::FS_FILE_NOT_FOUND));
        let _ = std::fs::remove_dir_all(base);
    }

    #[test]
    fn files_round_trip_through_the_host() {
        let base = scratch("files");
        let archive = HostArchive::ext_data(&base, 0x11C5, false);
        archive.format(FormatInfo::default()).unwrap();
        archive.create_directory("/dir").unwrap();
        archive.create_file("/dir/data.bin", 4).unwrap();
        assert_eq!(archive.create_file("/dir/data.bin", 4), Err(errors::FS_FILE_ALREADY_EXISTS));
        assert_eq!(archive.create_file("/missing/x", 4), Err(errors::FS_PATH_NOT_FOUND));

        let host = archive.open_file("/dir/data.bin", false).unwrap();
        assert_eq!(write_at(&host, 2, b"abcd", false), Ok(4));
        assert_eq!(size_of(&host), 6);
        let mut buffer = [0u8; 8];
        assert_eq!(read_at(&host, 0, &mut buffer), Ok(6));
        assert_eq!(&buffer[..6], b"\0\0abcd");

        let listing = archive.list("/dir").unwrap();
        assert_eq!(listing, vec![DirectoryEntry { name: "data.bin".into(), is_directory: false, size: 6 }]);
        assert_eq!(archive.delete_directory("/dir", false), Err(errors::FS_DIRECTORY_NOT_EMPTY));
        archive.delete_directory("/dir", true).unwrap();
        let _ = std::fs::remove_dir_all(base);
    }

    #[test]
    fn paths_cannot_escape_the_archive() {
        let archive = HostArchive::at("/tmp/zakuro-never-created");
        assert_eq!(archive.resolve("/../etc/passwd"), Err(errors::FS_INVALID_PATH));
    }
}
