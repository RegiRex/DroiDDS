//! CodexAstraUlt: Original ARM guests exercise save-file IPC and session reopen.
//! Host reads are independent oracles; only explicit failure controls alter a
//! test-owned backing file after the guest has opened its real file session.

use super::*;

const PAYLOAD: &[u8; 12] = b"DDS1\x19\0\0\0\xaa\x55\x01\xfe";
const PATH_BYTES: &[u8] = b"/slot.bin\0";
const PATH_ADDRESS: u32 = fixture::RODATA + 0x40;
const PAYLOAD_ADDRESS: u32 = fixture::RODATA + 0x80;
const COMPLETE: u32 = 0x5341_5645;
const OPENED: u32 = 0x4f50_454e;

// CodexAstraUlt: This small assembler uses independently authored ARMv6 and
// public FS IPC layouts. Every unexpected SVC/result/data value reaches Break.
struct Guest {
    words: Vec<u32>,
    literals: Vec<(usize, u32)>,
    errors: Vec<usize>,
}

impl Guest {
    fn new() -> Self {
        Self {
            words: Vec::new(),
            literals: Vec::new(),
            errors: Vec::new(),
        }
    }
    fn word(&mut self, value: u32) {
        self.words.push(value);
    }
    fn constant(&mut self, register: u32, value: u32) {
        self.literals.push((self.words.len(), value));
        self.word(0xe59f_0000 | register << 12);
    }
    fn mov(&mut self, destination: u32, source: u32) {
        self.word(0xe1a0_0000 | destination << 12 | source);
    }
    fn store(&mut self, register: u32, base: u32, offset: u32) {
        self.word(0xe580_0000 | base << 16 | register << 12 | offset);
    }
    fn load(&mut self, register: u32, base: u32, offset: u32) {
        self.word(0xe590_0000 | base << 16 | register << 12 | offset);
    }
    fn expect(&mut self, register: u32, value: u32) {
        self.constant(12, value);
        self.word(0xe150_000c | register << 16);
        self.errors.push(self.words.len());
        self.word(0x1a00_0000);
    }
    fn nonzero(&mut self, register: u32) {
        self.word(0xe350_0000 | register << 16);
        self.errors.push(self.words.len());
        self.word(0x0a00_0000);
    }
    fn ipc(&mut self, index: u32, value: u32) {
        self.constant(0, value);
        self.store(0, 10, index * 4);
    }
    fn arguments(&mut self, command: u32, values: &[u32]) {
        self.ipc(0, command);
        for (i, value) in values.iter().enumerate() {
            self.ipc(i as u32 + 1, *value);
        }
    }
    fn svc(&mut self, number: u32) {
        self.word(0xef00_0000 | number);
        if number != 3 {
            self.expect(0, 0);
        }
    }
    fn send(&mut self, handle: u32, success: bool) {
        self.mov(0, handle);
        self.svc(0x32);
        self.load(0, 10, 4);
        self.store(0, 11, 8);
        if success {
            self.expect(0, 0);
        } else {
            self.nonzero(0);
        }
    }
    fn connect(&mut self) {
        self.constant(11, fixture::DATA);
        self.constant(1, fixture::RODATA);
        self.svc(0x2d);
        self.mov(8, 1);
        self.word(0xee1d_af70); // MRC p15,0,r10,c13,c0,3: actual guest TLS.
        self.word(0xe28a_a080);
        self.arguments(0x0001_0000, &[]);
        self.send(8, true);
        self.arguments(
            0x0005_0100,
            &[
                u32::from_le_bytes(*b"fs:U"),
                u32::from_le_bytes(*b"SER\0"),
                7,
                0,
            ],
        );
        self.send(8, true);
        self.load(9, 10, 12);
        self.arguments(0x0801_0000, &[]);
        self.send(9, true);
    }
    fn open_archive(&mut self, success: bool) {
        self.arguments(0x080c_00c2, &[4, 1, 1, 0x4002, PAYLOAD_ADDRESS + 12]);
        self.send(9, success);
        if success {
            self.load(6, 10, 8);
            self.load(7, 10, 12);
        }
    }
    fn archive_handle(&mut self, index: u32) {
        self.store(6, 10, index * 4);
        self.store(7, 10, index * 4 + 4);
    }
    fn open_file(&mut self, flags: u32) {
        self.arguments(
            0x0802_01c2,
            &[
                0,
                0,
                0,
                3,
                PATH_BYTES.len() as u32,
                flags,
                0,
                (PATH_BYTES.len() as u32) << 14 | 2,
                PATH_ADDRESS,
            ],
        );
        self.archive_handle(2);
        self.send(9, true);
        self.load(5, 10, 12);
    }
    fn close(&mut self, success: bool) {
        self.arguments(0x0808_0000, &[]);
        self.send(5, success);
        self.mov(0, 5);
        self.svc(0x23);
        self.arguments(0x080e_0080, &[0, 0]);
        self.archive_handle(1);
        self.send(9, true);
        self.constant(0, COMPLETE);
        self.store(0, 11, 0);
        self.svc(3);
    }
    fn finish(mut self) -> Vec<u8> {
        let failed = self.words.len();
        self.word(0xef00_003c);
        self.word(0xeaff_fffe);
        for at in self.errors {
            self.words[at] |= ((failed as i32 - at as i32 - 2) as u32) & 0x00ff_ffff;
        }
        for (at, value) in self.literals {
            let offset = (self.words.len() - at - 2) * 4;
            assert!(offset < 4096);
            self.words[at] |= offset as u32;
            self.words.push(value);
        }
        assert!(self.words.len() * 4 <= 4096);
        self.words.into_iter().flat_map(u32::to_le_bytes).collect()
    }
}

// CodexAstraUlt: The writer formats only a new test-owned archive. Reader and
// failure guests reuse the same program identity and storage without formatting.
#[derive(Clone, Copy)]
enum Operation {
    Write,
    Read,
    LinkedRead,
    ReadOnlyWrite,
    WriteOnlyRead,
    BackingWrite,
    BackingRead,
    BackingFlush,
}

fn image(operation: Operation) -> Vec<u8> {
    let mut guest = Guest::new();
    guest.connect();
    if matches!(operation, Operation::Write) {
        guest.open_archive(false);
        guest.arguments(0x080f_0180, &[64, 4, 4, 1, 1, 0]);
        guest.send(9, true);
    }
    guest.open_archive(true);
    if matches!(operation, Operation::Write) {
        guest.arguments(
            0x0808_0202,
            &[
                0,
                0,
                0,
                3,
                PATH_BYTES.len() as u32,
                0,
                PAYLOAD.len() as u32,
                0,
                (PATH_BYTES.len() as u32) << 14 | 2,
                PATH_ADDRESS,
            ],
        );
        guest.archive_handle(2);
        guest.send(9, true);
    }
    let flags = match operation {
        Operation::Read | Operation::LinkedRead | Operation::ReadOnlyWrite => 1,
        Operation::WriteOnlyRead => 2,
        _ => 3,
    };
    guest.open_file(flags);
    if matches!(operation, Operation::LinkedRead) {
        // CodexAstraUlt: The remaining file session must remain usable after
        // the original session closes; a duplicate handle is not the same IPC
        // object as OpenLinkFile's independently closable file session.
        guest.arguments(0x080c_0000, &[]);
        guest.send(5, true);
        guest.load(4, 10, 12);
        guest.arguments(0x0808_0000, &[]);
        guest.send(5, true);
        guest.mov(0, 5);
        guest.svc(0x23);
        guest.mov(5, 4);
    }
    if matches!(
        operation,
        Operation::BackingWrite | Operation::BackingRead | Operation::BackingFlush
    ) {
        // CodexAstraUlt: A real guest sleep gives the test one explicit fault-
        // injection boundary after opening, without touching guest registers.
        guest.constant(0, OPENED);
        guest.store(0, 11, 4);
        guest.constant(0, 100_000_000);
        guest.constant(1, 0);
        guest.svc(0x0a);
    }
    match operation {
        Operation::Write | Operation::ReadOnlyWrite | Operation::BackingWrite => {
            guest.arguments(
                0x0803_0102,
                &[
                    0,
                    0,
                    PAYLOAD.len() as u32,
                    1,
                    (PAYLOAD.len() as u32) << 4 | 0xa,
                    PAYLOAD_ADDRESS,
                ],
            );
            guest.send(5, matches!(operation, Operation::Write));
            if matches!(operation, Operation::Write) {
                guest.load(0, 10, 8);
                guest.expect(0, PAYLOAD.len() as u32);
                guest.arguments(0x0809_0000, &[]);
                guest.send(5, true);
                guest.arguments(0x080d_0144, &[0, 0, 0, 0, 0, 0xa, 0, 0xc, 0]);
                guest.archive_handle(1);
                guest.send(9, true);
            }
        }
        Operation::Read
        | Operation::LinkedRead
        | Operation::WriteOnlyRead
        | Operation::BackingRead => {
            guest.arguments(
                0x0802_00c2,
                &[
                    0,
                    0,
                    PAYLOAD.len() as u32,
                    (PAYLOAD.len() as u32) << 4 | 0xc,
                    fixture::DATA + 0x20,
                ],
            );
            guest.send(
                5,
                matches!(operation, Operation::Read | Operation::LinkedRead),
            );
            if matches!(operation, Operation::Read | Operation::LinkedRead) {
                guest.load(0, 10, 8);
                guest.expect(0, PAYLOAD.len() as u32);
                for (i, word) in PAYLOAD.chunks_exact(4).enumerate() {
                    guest.load(0, 11, 0x20 + 4 * i as u32);
                    guest.expect(0, u32::from_le_bytes(word.try_into().unwrap()));
                }
            }
        }
        Operation::BackingFlush => {
            guest.arguments(0x0809_0000, &[]);
            guest.send(5, false);
        }
    }
    // CodexAstraUlt: A failed attempted write keeps dirty state so Close cannot
    // falsely promise that an unflushable backing has become durable.
    guest.close(!matches!(operation, Operation::BackingWrite));
    let program = guest.finish();
    let mut image = fixture::image(0, 0, false);
    image[0x800..0x1800].fill(0);
    image[0x800..0x800 + program.len()].copy_from_slice(&program);
    image[0x1840..0x1840 + PATH_BYTES.len()].copy_from_slice(PATH_BYTES);
    image[0x1880..0x1880 + PAYLOAD.len()].copy_from_slice(PAYLOAD);
    if matches!(operation, Operation::ReadOnlyWrite) {
        image[0x1880..0x1884].copy_from_slice(b"FAIL");
    }
    image[0x1880 + PAYLOAD.len()] = 0;
    image
}

// CodexAstraUlt: Reopen the same app-private data directory while independently
// admitting each original executable; original inputs remain immutable.
fn open(fixture: &Fixture, data: &std::path::Path, native: bool) -> Session {
    Session::open(OpenOptions {
        manifest_json: &serde_json::to_vec(&fixture.manifest).unwrap(),
        input: &fixture.input,
        native_directory: &fixture.native,
        data_directory: data,
        native,
        hardware: false,
    })
    .unwrap()
}

fn complete(session: &mut Session) {
    for _ in 0..32 {
        if session.system.exited {
            break;
        }
        session
            .slice(InputState::default())
            .unwrap_or_else(|error| {
                panic!(
                    "{error}, last IPC result {:#010x}: {}",
                    session.system.memory.read32(fixture::DATA + 8),
                    session.report()
                )
            });
    }
    assert!(session.system.exited, "{}", session.report());
    assert_eq!(session.system.memory.read32(fixture::DATA), COMPLETE);
    assert!(session.report()["first_blocker"].is_null());
    assert_eq!(session.report()["memory_faults"]["distinct_pages"], 0);
    assert_eq!(session.report()["unsupported_services"], 0);
    assert_eq!(session.report()["unsupported_svcs"], 0);
    if session.native {
        assert!(session.report()["native_instructions"].as_u64().unwrap() > 0);
    }
}

fn saved_file(fixture: &Fixture) -> PathBuf {
    fixture
        .data
        .join("user")
        .join("savedata")
        .join(format!("{:016X}", fixture::PROGRAM_ID))
        .join("slot.bin")
}

// CodexAstraUlt: A guest-created save must survive teardown and two admitted
// reopen sessions, with exact file bytes and guest-side comparisons on both CPUs.
#[test]
fn guest_save_write_commit_and_reopen_read_match_on_both_cpu_routes() {
    let _serial = SERIAL.lock().unwrap();
    for native in [false, true] {
        let writer = Fixture::new(image(Operation::Write), native);
        let mut session = writer.open(native).unwrap();
        complete(&mut session);
        drop(session);
        assert_eq!(fs::read(saved_file(&writer)).unwrap(), PAYLOAD);
        let reader = Fixture::new(image(Operation::Read), native);
        for _ in 0..2 {
            let mut session = open(&reader, &writer.data, native);
            session.pause();
            session.resume();
            complete(&mut session);
            let mut actual = [0u8; 12];
            session
                .system
                .memory
                .read_bytes(fixture::DATA + 0x20, &mut actual);
            assert_eq!(&actual, PAYLOAD);
        }
        assert_eq!(fs::read(saved_file(&writer)).unwrap(), PAYLOAD);
        writer.preserved();
        reader.preserved();
    }
}

// CodexAstraUlt: Rights failures cannot alter a save or expose file bytes through
// a write-only session; the original guest asserts the IPC error itself.
#[test]
fn guest_file_access_modes_reject_opposite_operation_without_changing_save() {
    let _serial = SERIAL.lock().unwrap();
    for native in [false, true] {
        let writer = Fixture::new(image(Operation::Write), native);
        complete(&mut writer.open(native).unwrap());
        for operation in [Operation::ReadOnlyWrite, Operation::WriteOnlyRead] {
            let client = Fixture::new(image(operation), native);
            let mut session = open(&client, &writer.data, native);
            complete(&mut session);
            if matches!(operation, Operation::WriteOnlyRead) {
                let mut unread = [0u8; 12];
                session
                    .system
                    .memory
                    .read_bytes(fixture::DATA + 0x20, &mut unread);
                assert_eq!(unread, [0; 12]);
            }
            assert_eq!(fs::read(saved_file(&writer)).unwrap(), PAYLOAD);
            client.preserved();
        }
        writer.preserved();
    }
}

// CodexAstraUlt: A guest link is its own live file session, not a second name
// for a service record that disappears when the original closes.
#[test]
fn guest_link_file_survives_original_file_session_close() {
    let _serial = SERIAL.lock().unwrap();
    for native in [false, true] {
        let writer = Fixture::new(image(Operation::Write), native);
        complete(&mut writer.open(native).unwrap());
        let reader = Fixture::new(image(Operation::LinkedRead), native);
        complete(&mut open(&reader, &writer.data, native));
        assert_eq!(fs::read(saved_file(&writer)).unwrap(), PAYLOAD);
        writer.preserved();
        reader.preserved();
    }
}

// CodexAstraUlt: Make a real host operation fail after a successful guest open,
// so an unconditional success reply cannot pass as persistence or durability.
#[test]
fn guest_read_write_and_flush_failures_are_not_reported_as_success() {
    let _serial = SERIAL.lock().unwrap();
    for native in [false, true] {
        for operation in [
            Operation::BackingWrite,
            Operation::BackingRead,
            Operation::BackingFlush,
        ] {
            let writer = Fixture::new(image(Operation::Write), native);
            complete(&mut writer.open(native).unwrap());
            let client = Fixture::new(image(operation), native);
            let mut session = open(&client, &writer.data, native);
            for _ in 0..16 {
                if session.system.memory.read32(fixture::DATA + 4) == OPENED {
                    break;
                }
                session.slice(InputState::default()).unwrap();
            }
            assert_eq!(session.system.memory.read32(fixture::DATA + 4), OPENED);
            assert!(!session.system.exited);
            // CodexAstraUlt: Only this freshly authored test save is replaced;
            // no user input, title snapshot or existing save is fault-injected.
            let backing = saved_file(&writer);
            fs::remove_file(&backing).unwrap();
            fs::create_dir(&backing).unwrap();
            complete(&mut session);
            assert!(backing.is_dir());
            writer.preserved();
            client.preserved();
        }
    }
}
