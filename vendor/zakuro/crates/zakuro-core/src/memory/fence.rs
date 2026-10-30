//! CodexAstraUlt: Optional Linux/Android backing owns whole 4 KiB host pages so
//! read-only guest code never shares a protected page with allocator metadata.

use std::ops::{Deref, DerefMut};

// CodexAstraUlt: Ordinary frontends retain their existing heap allocation.
// Only an explicitly admitted pre-execution session creates a private mapping.
// CodexAstraUlt: Bionic exposes the same mmap/mprotect ownership operations;
// Android still rejects unsupported host page sizes before moving live memory.
pub struct FcramBacking(Backing);

enum Backing {
    Heap(Box<[u8]>),
    #[cfg(any(target_os = "linux", target_os = "android"))]
    Mapped(Mapped),
}

#[cfg(any(target_os = "linux", target_os = "android"))]
struct Mapped {
    pointer: std::ptr::NonNull<u8>,
    bytes: usize,
}

// SAFETY: Mapped exclusively owns its mapping; access is mediated by borrowed
// slices exactly as for the default Box. No background thread mutates it.
#[cfg(any(target_os = "linux", target_os = "android"))]
unsafe impl Send for Mapped {}
#[cfg(any(target_os = "linux", target_os = "android"))]
unsafe impl Sync for Mapped {}

#[cfg(any(target_os = "linux", target_os = "android"))]
impl Drop for Mapped {
    fn drop(&mut self) {
        // SAFETY: This is the exact live anonymous mapping we own. munmap does
        // not write to its read-only pages or invoke the heap allocator on them.
        unsafe { libc::munmap(self.pointer.as_ptr().cast(), self.bytes) };
    }
}

impl FcramBacking {
    pub(super) fn new(bytes: usize) -> Self {
        Self(Backing::Heap(vec![0; bytes].into_boxed_slice()))
    }

    // CodexAstraUlt: Keep an unsuccessful alignment/protection attempt separate
    // from live memory. The caller swaps/rebases only after this copy succeeds.
    pub(super) fn fenced_copy(&self, offset: usize, bytes: usize) -> Result<Self, String> {
        #[cfg(any(target_os = "linux", target_os = "android"))]
        {
            // SAFETY: sysconf has no pointer arguments and cannot mutate RAM.
            if unsafe { libc::sysconf(libc::_SC_PAGESIZE) } != 4096 {
                return Err("native_base_code_fence_requires_linux_or_android_4k_pages".into());
            }
            if self.is_empty() || self.len() % 4096 != 0 || offset % 4096 != 0 ||
                bytes == 0 || bytes % 4096 != 0 || offset.checked_add(bytes).is_none_or(|end| end > self.len()) {
                return Err("native_base_code_fence_invalid_host_range".into());
            }
            // SAFETY: Anonymous mmap allocates independent writable pages; no
            // pointer from the live memory map is passed to the operating system.
            let pointer = unsafe { libc::mmap(std::ptr::null_mut(), self.len(),
                libc::PROT_READ | libc::PROT_WRITE, libc::MAP_PRIVATE | libc::MAP_ANONYMOUS, -1, 0) };
            if pointer == libc::MAP_FAILED {
                return Err("native_base_code_fence_allocation_failed".into());
            }
            let Some(pointer) = std::ptr::NonNull::new(pointer.cast::<u8>()) else {
                // CodexAstraUlt: A successful address-zero mapping still needs
                // release even though Rust cannot represent it as a live slice.
                // SAFETY: mmap returned this exact allocation, not MAP_FAILED.
                unsafe { libc::munmap(pointer, self.len()) };
                return Err("native_base_code_fence_null_mapping".into());
            };
            let mapping = Mapped { pointer, bytes: self.len() };
            // SAFETY: The source is live, the new mapping has exactly its size,
            // and the two allocations cannot overlap.
            unsafe { std::ptr::copy_nonoverlapping(self.as_ptr(), pointer.as_ptr(), self.len()) };
            // SAFETY: Both ends are host-page aligned and inside our allocation.
            if unsafe { libc::mprotect(pointer.as_ptr().add(offset).cast(), bytes, libc::PROT_READ) } != 0 {
                return Err("native_base_code_fence_protection_failed".into());
            }
            Ok(Self(Backing::Mapped(mapping)))
        }
        #[cfg(not(any(target_os = "linux", target_os = "android")))]
        {
            let _ = (offset, bytes);
            Err("native_base_code_fence_requires_linux_or_android_4k_pages".into())
        }
    }

    pub(super) fn is_fenced_mapping(&self) -> bool {
        match &self.0 {
            Backing::Heap(_) => false,
            #[cfg(any(target_os = "linux", target_os = "android"))]
            Backing::Mapped(_) => true,
        }
    }
}

// CodexAstraUlt: Preserve slice-based physical-memory and save-state callers;
// writes to protected bytes intentionally terminate the isolated diagnostic.
impl Deref for FcramBacking {
    type Target = [u8];
    fn deref(&self) -> &[u8] {
        match &self.0 {
            Backing::Heap(bytes) => bytes,
            #[cfg(any(target_os = "linux", target_os = "android"))]
            Backing::Mapped(mapping) => {
                // SAFETY: The mapping remains readable until its owner drops.
                unsafe { std::slice::from_raw_parts(mapping.pointer.as_ptr(), mapping.bytes) }
            }
        }
    }
}

impl DerefMut for FcramBacking {
    fn deref_mut(&mut self) -> &mut [u8] {
        match &mut self.0 {
            Backing::Heap(bytes) => bytes,
            #[cfg(any(target_os = "linux", target_os = "android"))]
            Backing::Mapped(mapping) => {
                // SAFETY: &mut self gives unique access to the owned mapping.
                // Its diagnostic read-only fence remains enforced by Linux.
                unsafe { std::slice::from_raw_parts_mut(mapping.pointer.as_ptr(), mapping.bytes) }
            }
        }
    }
}

impl AsRef<[u8]> for FcramBacking {
    fn as_ref(&self) -> &[u8] { self }
}

impl AsMut<[u8]> for FcramBacking {
    fn as_mut(&mut self) -> &mut [u8] { self }
}
