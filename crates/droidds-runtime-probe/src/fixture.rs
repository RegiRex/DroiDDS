//! CodexAstraUlt: An original ARM/NCCH/PICA program, made from public instruction
//! and register formats. No guest bytes or artwork originate in a retail title.

use zakuro_gpu::registers::*;

pub const PROGRAM_ID: u64 = 0x0004_0000_0D5D_0005;
pub const TEXT: u32 = 0x0010_0000;
pub const RODATA: u32 = 0x0010_1000;
pub const DATA: u32 = 0x0010_2000;
pub const FALLBACK: u32 = TEXT + 0x800;
pub const COLOR: u32 = 0x1f00_0000;
pub const COMMANDS: u32 = 0x1f00_1000;
pub const CHECKPOINT: u32 = 0x4453_4435;
pub const LIBRARY: &str = "libdroidds_fixture_runtime.so";
pub const IDENTITY: &str = "droidds-original-pica-ipc-v1";
pub const WIDTH: u32 = 8;

// CodexAstraUlt: Literal loads keep this ARM11 program within ARMv6; the helper
// at TEXT+0x800 is deliberately absent from the emitted native source segment.
struct Arm {
    words: Vec<u32>,
    literals: Vec<(usize, u32)>,
    errors: Vec<usize>,
}

impl Arm {
    fn new() -> Self {
        Self {
            words: Vec::new(),
            literals: Vec::new(),
            errors: Vec::new(),
        }
    }
    fn word(&mut self, word: u32) {
        self.words.push(word);
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
    fn ipc(&mut self, index: u32, value: u32) {
        self.constant(0, value);
        self.store(0, 10, index * 4);
    }
    fn check_zero(&mut self, register: u32) {
        self.word(0xe350_0000 | register << 16);
        self.errors.push(self.words.len());
        self.word(0x1a00_0000);
    }
    fn svc(&mut self, number: u32) {
        self.word(0xef00_0000 | number);
        if number != 3 {
            self.check_zero(0);
        }
    }
    fn send(&mut self, handle: u32) {
        self.mov(0, handle);
        self.svc(0x32);
        self.load(0, 10, 4);
        self.check_zero(0);
    }
    fn get_service(&mut self, name: &[u8; 8], length: u32, handle: u32) {
        self.ipc(0, 0x0005_0100);
        self.ipc(1, u32::from_le_bytes(name[..4].try_into().unwrap()));
        self.ipc(2, u32::from_le_bytes(name[4..].try_into().unwrap()));
        self.ipc(3, length);
        self.ipc(4, 0);
        self.send(8);
        self.load(handle, 10, 12);
    }
    fn finish(mut self) -> Vec<u8> {
        let failed = self.words.len();
        self.word(0xef00_003c); // CodexAstraUlt: Fail visibly via svcBreak.
        self.word(0xeaff_fffe);
        for at in self.errors {
            self.words[at] |= ((failed as i32 - at as i32 - 2) as u32) & 0x00ff_ffff;
        }
        for (at, value) in self.literals {
            let offset = (self.words.len() - at - 2) * 4;
            assert!(offset < 0x1000);
            self.words[at] |= offset as u32;
            self.words.push(value);
        }
        assert!(self.words.len() * 4 < 0x800);
        self.words.into_iter().flat_map(u32::to_le_bytes).collect()
    }
}

// CodexAstraUlt: Exactly representable float24 inputs and opaque primary colors
// give a hand-derived pixel oracle, independent of both renderer implementations.
fn float24(value: f32) -> u32 {
    if value == 0.0 {
        return 0;
    }
    let bits = value.to_bits();
    (bits & 0x8000_0000) >> 8 | ((((bits >> 23) & 255) + 63 - 127) << 16) | ((bits >> 7) & 65535)
}

fn vector(value: [f32; 4]) -> [u32; 3] {
    let [x, y, z, w] = value.map(float24);
    [
        (w << 8) | (z >> 16),
        ((z & 65535) << 16) | (y >> 8),
        ((y & 255) << 24) | x,
    ]
}

pub fn pica_commands() -> Vec<u8> {
    let mut words = Vec::new();
    let mut write = |register: usize, value: u32| words.extend([value, register as u32 | 0xf0000]);
    write(REG_VS_BLOCK + SHADER_PROGRAM_INDEX, 0);
    for word in [0x13 << 26, (0x13 << 26) | (1 << 21) | (1 << 12), 0x22 << 26] {
        write(REG_VS_BLOCK + SHADER_PROGRAM_DATA, word);
    }
    write(REG_VS_BLOCK + SHADER_DESCRIPTOR_INDEX, 0);
    write(
        REG_VS_BLOCK + SHADER_DESCRIPTOR_DATA,
        0xf | (0b00_01_10_11 << 5) | (0b00_01_10_11 << 14),
    );
    write(REG_SHADER_OUTPUT_TOTAL, 2);
    write(REG_SHADER_OUTPUT_MAP, 0x0302_0100);
    write(REG_SHADER_OUTPUT_MAP + 1, 0x0b0a_0908);
    write(REG_VS_INPUT_REGISTER_MAP_LOW, 0x10);
    write(REG_VS_ATTRIBUTE_COUNT, 1);
    write(REG_VS_BLOCK + SHADER_INPUT_CONFIG, 1);
    write(REG_VS_BLOCK + SHADER_OUTPUT_MASK, 3);
    write(REG_VIEWPORT_WIDTH, float24(4.0));
    write(REG_VIEWPORT_HEIGHT, float24(4.0));
    write(REG_COLOR_BUFFER_ADDRESS, 0x1800_0000 >> 3);
    write(REG_COLOR_BUFFER_FORMAT, 4);
    write(REG_FRAMEBUFFER_DIMENSIONS, 8 | (7 << 12));
    write(REG_COLOR_BUFFER_WRITE, 0xf);
    write(REG_DEPTH_COLOR_MASK, 0xf << 8);
    write(REG_LOGIC_OP, 3);
    // CodexAstraUlt: First cover the target red, then its upper-right quarter
    // green. Both axes are asymmetric so a vertical flip cannot self-qualify.
    for (pass, color) in [[1.0, 0.0, 0.0, 1.0], [0.0, 1.0, 0.0, 1.0]]
        .into_iter()
        .enumerate()
    {
        if pass == 1 {
            write(REG_VIEWPORT_WIDTH, float24(2.0));
            write(REG_VIEWPORT_HEIGHT, float24(2.0));
            write(REG_VIEWPORT_XY, 4 | (4 << 16));
        }
        write(REG_FIXED_ATTRIBUTE_INDEX, 15);
        for position in [
            [-1.0, -1.0, -0.5, 1.0],
            [3.0, -1.0, -0.5, 1.0],
            [-1.0, 3.0, -0.5, 1.0],
        ] {
            for attribute in [position, color] {
                for (i, word) in vector(attribute).into_iter().enumerate() {
                    write(REG_FIXED_ATTRIBUTE_DATA + i, word);
                }
            }
        }
        write(0x245, pass as u32 + 1);
    }
    words.into_iter().flat_map(u32::to_le_bytes).collect()
}

pub fn native_text() -> Vec<u8> {
    let commands = pica_commands();
    let mut arm = Arm::new();
    arm.constant(11, DATA);
    // CodexAstraUlt: A normally clear flag enables the native RX-store control.
    arm.load(0, 11, 16);
    arm.word(0xe350_0000);
    arm.constant(1, TEXT);
    arm.constant(2, 0);
    arm.word(0x1581_2000);
    arm.constant(7, 0);
    arm.constant(6, FALLBACK);
    arm.word(0xe12f_ff36); // CodexAstraUlt: BLX r6 crosses into an absent native entry.
    arm.store(7, 11, 4);
    arm.constant(1, RODATA);
    arm.svc(0x2d);
    arm.mov(8, 1);
    arm.word(0xee1d_af70); // CodexAstraUlt: MRC p15,0,r10,c13,c0,3 reads the real thread TLS.
    arm.word(0xe28a_a080);
    arm.ipc(0, 0x0001_0000);
    arm.send(8);
    arm.get_service(b"cfg:u\0\0\0", 5, 9);
    arm.ipc(0, 0x0005_0000);
    arm.send(9);
    arm.load(0, 10, 8);
    arm.store(0, 11, 8);
    arm.get_service(b"gsp::Gpu", 8, 9);
    // CodexAstraUlt: The guest copies its original command list into mapped VRAM;
    // the host never submits a replacement list or draws the expected picture.
    arm.constant(0, RODATA + 0x100);
    arm.constant(1, COMMANDS);
    arm.constant(2, commands.len() as u32 / 4);
    let start = arm.words.len();
    arm.word(0xe490_3004);
    arm.word(0xe481_3004);
    arm.word(0xe252_2001);
    let at = arm.words.len();
    arm.word(0x1a00_0000 | ((start as i32 - at as i32 - 2) as u32 & 0x00ff_ffff));
    arm.ipc(0, 0x0006_0080);
    arm.ipc(1, COMMANDS);
    arm.ipc(2, commands.len() as u32);
    arm.send(9);
    arm.constant(0, CHECKPOINT);
    arm.store(0, 11, 0);
    arm.svc(3);
    arm.finish()
}

// CodexAstraUlt: Each image has one executable page, one immutable data page and
// one writable result page. All NCCH and ExHeader fields are original fixtures.
pub fn image(old_mode: u8, new_mode: u8, new_platform: bool) -> Vec<u8> {
    let native = native_text();
    let mut code = vec![0u8; 0x3000];
    code[..native.len()].copy_from_slice(&native);
    code[0x800..0x808].copy_from_slice(
        &[0xe287_7001u32, 0xe12f_ff1e]
            .into_iter()
            .flat_map(u32::to_le_bytes)
            .collect::<Vec<_>>(),
    );
    code[0x1000..0x1005].copy_from_slice(b"srv:\0");
    let commands = pica_commands();
    assert!(commands.len() <= 0xf00);
    code[0x1100..0x1100 + commands.len()].copy_from_slice(&commands);
    let mut out = vec![0u8; 0x800];
    out[0x100..0x104].copy_from_slice(b"NCCH");
    out[0x118..0x120].copy_from_slice(&PROGRAM_ID.to_le_bytes());
    out[0x18c] = if new_platform { 2 } else { 1 };
    out[0x18f] = 4;
    out[0x1a0..0x1a4].copy_from_slice(&3u32.to_le_bytes());
    for (at, address) in [(0x210, TEXT), (0x220, RODATA), (0x230, DATA)] {
        out[at..at + 12].copy_from_slice(
            &[address, 1, 0x1000]
                .into_iter()
                .flat_map(u32::to_le_bytes)
                .collect::<Vec<_>>(),
        );
    }
    out[0x21c..0x220].copy_from_slice(&0x1000u32.to_le_bytes());
    out[0x40c] = if new_platform { 3 } else { 0 };
    out[0x40d] = new_mode;
    out[0x40e] = old_mode << 4;
    out[0x40f] = 0x30;
    out[0x600..0x605].copy_from_slice(b".code");
    out[0x60c..0x610].copy_from_slice(&(code.len() as u32).to_le_bytes());
    out.extend(code);
    out
}

pub fn expected_pixels() -> Vec<[u8; 4]> {
    (0..64)
        .map(|i| {
            if i % 8 >= 4 && i / 8 < 4 {
                [0, 255, 0, 255]
            } else {
                [255, 0, 0, 255]
            }
        })
        .collect()
}
