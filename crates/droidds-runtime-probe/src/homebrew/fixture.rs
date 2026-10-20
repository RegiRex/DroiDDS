//! CodexAstraUlt: Original ARM11 homebrew that consumes HID, draws both displays
//! through GSP/PICA, and programs a PCM voice through the runtime's DSP service.
//! No Nintendo firmware, retail instructions, graphics or sound are included.

use super::pica::{self, Panel};

pub const PROGRAM_ID: u64 = 0x0004_0000_0D5D_0006;
pub const IDENTITY: &str = "droidds-original-homebrew-v1";
pub const LIBRARY: &str = "libdroidds_fixture_homebrew.so";
pub const TEXT: u32 = 0x0010_0000;
pub const TEXT_BYTES: u32 = 0x2000;
pub const FALLBACK: u32 = TEXT + TEXT_BYTES - 16;
pub const RODATA: u32 = TEXT + TEXT_BYTES;
pub const RODATA_BYTES: u32 = 0x4000;
pub const DATA: u32 = RODATA + RODATA_BYTES;
pub const CHECKPOINT: u32 = 0x4453_4436;

// CodexAstraUlt: These offsets are the guest's observable state, never commands
// for the host to mutate. Input enters exclusively through the HID service.
pub const CHECKPOINT_OFFSET: u32 = 0;
pub const FRAME_SERIAL_OFFSET: u32 = 4;
pub const FALLBACK_COUNT_OFFSET: u32 = 8;
pub const BUTTONS_OFFSET: u32 = 12;
pub const TOUCH_X_OFFSET: u32 = 16;
pub const TOUCH_Y_OFFSET: u32 = 20;
pub const TOUCH_VALID_OFFSET: u32 = 24;
pub const TOP_X_OFFSET: u32 = 28;
pub const TOP_Y_OFFSET: u32 = 32;
pub const BOTTOM_X_OFFSET: u32 = 36;
pub const BOTTOM_Y_OFFSET: u32 = 40;
pub const TONE_RATE_OFFSET: u32 = 44;
pub const ERROR_STAGE_OFFSET: u32 = 48;
pub const EXIT_REQUESTED_OFFSET: u32 = 52;
pub const PROGRESS_STAGE_OFFSET: u32 = 56;
pub const DSP_ENABLED_OFFSET: u32 = 60;
pub const DSP_POSITION_OFFSET: u32 = 64;
pub const DSP_BUFFER_ID_OFFSET: u32 = 68;

// CodexAstraUlt: Firmware-format structures are discovered by the guest's DSP
// IPC. Only its original sample area and ordinary data workspace are fixed.
const HID: u32 = 0x1000_0000;
const PCM: u32 = 0x1ff0_1000;
const PIPE_REPLY: u32 = 0x100;
const VOICE_POINTER: u32 = 0x120;
const MIXER_POINTER: u32 = 0x124;
const COUNTER_POINTER: u32 = 0x128;
const STATUS_POINTER: u32 = 0x12c;
const PIPE_STATE: u32 = 0x180;
const TOP_TEMPLATE: u32 = RODATA + 0x100;
const BOTTOM_TEMPLATE: u32 = RODATA + 0x2100;

pub const PCM_AMPLITUDE: i16 = 4000;
pub const PCM_PERIOD_SAMPLES: usize = 80;
pub const PCM_BUFFER_SAMPLES: usize = 160;
pub const OUTPUT_AMPLITUDE: i16 = 2000;

// CodexAstraUlt: This tiny emitter uses only ARMv6 instructions. Constants use
// rotated byte immediates rather than a distant literal pool, keeping branch
// targets and immutable executable coverage explicit as the guest grows.
const EQ: u32 = 0;
const NE: u32 = 1;
const MI: u32 = 4;
const HI: u32 = 8;
const AL: u32 = 14;

struct Arm {
    words: Vec<u32>,
    errors: Vec<usize>,
}

impl Arm {
    fn new() -> Self {
        Self {
            words: Vec::new(),
            errors: Vec::new(),
        }
    }

    fn word(&mut self, value: u32) {
        self.words.push(value);
    }

    fn at(&self) -> usize {
        self.words.len()
    }

    fn constant(&mut self, register: u32, value: u32) {
        self.constant_if(AL, register, value);
    }

    fn constant_if(&mut self, condition: u32, register: u32, value: u32) {
        let mut first = true;
        for byte in 0..4 {
            let part = (value >> (byte * 8)) & 255;
            if part == 0 && (value != 0 || byte != 0) {
                continue;
            }
            let rotate = if byte == 0 { 0 } else { 16 - byte * 4 };
            let operation = if first {
                0x03a0_0000
            } else {
                0x0380_0000 | register << 16
            };
            self.word(condition << 28 | operation | register << 12 | rotate << 8 | part);
            first = false;
        }
    }

    fn mov(&mut self, destination: u32, source: u32) {
        self.word(0xe1a0_0000 | destination << 12 | source);
    }

    fn load(&mut self, register: u32, base: u32, offset: u32) {
        assert!(offset < 4096);
        self.word(0xe590_0000 | base << 16 | register << 12 | offset);
    }

    fn store(&mut self, register: u32, base: u32, offset: u32) {
        assert!(offset < 4096);
        self.word(0xe580_0000 | base << 16 | register << 12 | offset);
    }

    fn half(&mut self, load: bool, register: u32, base: u32, offset: u32) {
        assert!(offset < 256);
        self.word(
            0xe1c0_00b0
                | u32::from(load) << 20
                | base << 16
                | register << 12
                | (offset & 0xf0) << 4
                | (offset & 15),
        );
    }

    fn write(&mut self, base: u32, offset: u32, value: u32) {
        self.constant(0, value);
        self.store(0, base, offset);
    }

    fn stage(&mut self, stage: u32) {
        self.write(11, PROGRESS_STAGE_OFFSET, stage);
    }

    fn branch(&mut self, condition: u32) -> usize {
        let at = self.at();
        self.word(condition << 28 | 0x0a00_0000);
        at
    }

    fn resolve(&mut self, branch: usize, target: usize) {
        let distance = target as i32 - branch as i32 - 2;
        self.words[branch] |= distance as u32 & 0x00ff_ffff;
    }

    fn back(&mut self, condition: u32, target: usize) {
        let at = self.branch(condition);
        self.resolve(at, target);
    }

    fn check_zero(&mut self, register: u32) {
        self.word(0xe350_0000 | register << 16);
        let at = self.branch(NE);
        self.errors.push(at);
    }

    fn svc(&mut self, number: u32) {
        self.word(0xef00_0000 | number);
        if number != 3 {
            self.check_zero(0);
        }
    }

    fn ipc(&mut self, index: u32, value: u32) {
        self.write(10, index * 4, value);
    }

    fn send(&mut self, handle: u32) {
        self.mov(0, handle);
        self.svc(0x32);
        self.load(0, 10, 4);
        self.check_zero(0);
    }

    fn service(&mut self, name: &[u8; 8], length: u32, register: u32) {
        self.ipc(0, 0x0005_0100);
        self.ipc(1, u32::from_le_bytes(name[..4].try_into().unwrap()));
        self.ipc(2, u32::from_le_bytes(name[4..].try_into().unwrap()));
        self.ipc(3, length);
        self.ipc(4, 0);
        self.send(8);
        self.load(register, 10, 12);
    }

    fn copy(&mut self, source: u32, destination: u32, length: usize) {
        assert_eq!(length % 4, 0);
        self.constant(0, source);
        self.constant(1, destination);
        self.constant(2, length as u32 / 4);
        let start = self.at();
        self.word(0xe490_3004); // CodexAstraUlt: LDR/STR postincrement copy guest data.
        self.word(0xe481_3004);
        self.word(0xe252_2001);
        self.back(NE, start);
    }

    fn fill(&mut self, address: u32, words: u32, value: u32) {
        self.constant(0, address);
        self.constant(1, value);
        self.constant(2, words);
        let start = self.at();
        self.word(0xe480_1004);
        self.word(0xe252_2001);
        self.back(NE, start);
    }

    fn finish(mut self) -> Vec<u8> {
        // CodexAstraUlt: Service failures publish the responsible stage before
        // the real guest Break syscall; progress alone is never an error.
        let failed = self.at();
        self.load(0, 11, PROGRESS_STAGE_OFFSET);
        self.store(0, 11, ERROR_STAGE_OFFSET);
        self.word(0xef00_003c);
        self.word(0xeaff_fffe);
        for at in self.errors.clone() {
            self.resolve(at, failed);
        }
        assert!(self.words.len() * 4 < (FALLBACK - TEXT) as usize);
        self.words.into_iter().flat_map(u32::to_le_bytes).collect()
    }
}

// CodexAstraUlt: Set up actual srv/HID sessions and map the returned kernel
// shared-memory handle. The host never writes the guest's input result fields.
fn initialize_services(arm: &mut Arm) {
    arm.constant(11, DATA);
    arm.constant(7, 0);
    arm.stage(1);
    arm.constant(1, RODATA);
    arm.svc(0x2d);
    arm.mov(8, 1);
    arm.word(0xee1d_af70); // CodexAstraUlt: Read real thread TLS via MRC.
    arm.word(0xe28a_a080);
    arm.ipc(0, 0x0001_0000);
    arm.send(8);
    arm.service(b"gsp::Gpu", 8, 9);
    arm.stage(2);
    arm.service(b"hid:USER", 8, 6);
    arm.ipc(0, 0x000a_0000);
    arm.send(6);
    arm.load(0, 10, 12);
    arm.constant(1, HID);
    arm.constant(2, 1);
    arm.constant(3, 1);
    arm.svc(0x1f);
    arm.constant(4, HID);
    arm.stage(3);
    arm.service(b"dsp::DSP", 8, 5);
}

// CodexAstraUlt: Use DSP's service-discovered addresses and HLE PCM voice path,
// without uploading or pretending to execute proprietary firmware. ARM guest
// instructions synthesize the original square-wave samples in mapped DSP RAM.
fn initialize_audio(arm: &mut Arm) {
    for quarter in 0..4 {
        let sample = if quarter % 2 == 0 {
            PCM_AMPLITUDE
        } else {
            -PCM_AMPLITUDE
        } as u16 as u32;
        arm.fill(PCM + quarter * 80, 20, sample | sample << 16);
    }
    arm.write(11, PIPE_STATE, 0);
    arm.ipc(0, 0x000d_0082);
    arm.ipc(1, 2);
    arm.ipc(2, 1);
    arm.ipc(3, 0x4002);
    arm.ipc(4, DATA + PIPE_STATE);
    arm.send(5);
    arm.write(10, 0x100, (32 << 14) | 2);
    arm.write(10, 0x104, DATA + PIPE_REPLY);
    arm.ipc(0, 0x000e_00c0);
    arm.ipc(1, 2);
    arm.ipc(2, 0);
    arm.ipc(3, 32);
    arm.send(5);
    arm.load(0, 10, 8);
    arm.word(0xe240_0020);
    arm.check_zero(0);
    arm.constant(6, DATA + PIPE_REPLY);
    arm.half(true, 0, 6, 0);
    arm.word(0xe240_000f);
    arm.check_zero(0);
    for (index, destination) in [
        (0, COUNTER_POINTER),
        (1, VOICE_POINTER),
        (2, STATUS_POINTER),
        (4, MIXER_POINTER),
    ] {
        arm.ipc(0, 0x000c_0040);
        arm.constant(6, DATA + PIPE_REPLY);
        arm.half(true, 0, 6, 2 + index * 2);
        arm.store(0, 10, 4);
        arm.send(5);
        arm.load(0, 10, 8);
        arm.store(0, 11, destination);
    }
    arm.load(6, 11, COUNTER_POINTER);
    arm.constant(0, 1);
    arm.half(false, 0, 6, 0);
    arm.constant(1, 0x20000);
    arm.word(0xe086_6001);
    arm.constant(0, 0);
    arm.half(false, 0, 6, 0);

    // CodexAstraUlt: DSP32 address/count fields store the high halfword first;
    // float and dirty fields use ordinary ARM little-endian words.
    arm.load(6, 11, VOICE_POINTER);
    arm.write(6, 0x04, 1.0f32.to_bits());
    arm.write(6, 0x08, 1.0f32.to_bits());
    arm.write(6, 0x34, 1.0f32.to_bits());
    arm.write(6, 0x38, 2);
    arm.write(6, 0xa0, 1);
    arm.write(6, 0xac, PCM.rotate_left(16));
    arm.write(6, 0xb0, (PCM_BUFFER_SAMPLES as u32).rotate_left(16));
    arm.write(6, 0xb4, 5);
    arm.write(6, 0xbc, 2);
    arm.write(6, 0, 0x6207_0000);
    arm.load(6, 11, MIXER_POINTER);
    arm.write(6, 4, 0.5f32.to_bits());
    arm.write(6, 0x14, 1 << 16);
    arm.write(6, 0, 0x0401_0000);
    arm.write(11, TONE_RATE_OFFSET, 1.0f32.to_bits());
}

// CodexAstraUlt: Sample the real HID rings, retain exact observations, and derive
// bounded upright marker positions in guest code. Both axes are independently
// controllable and touch is centered/clamped inside the lower display.
fn sample_input(arm: &mut Arm) -> usize {
    arm.stage(5);
    arm.load(6, 4, 0x1c);
    arm.store(6, 11, BUTTONS_OFFSET);
    arm.word(0xe206_000c);
    arm.word(0xe350_000c);
    let exit = arm.branch(EQ);
    arm.constant(0, 184);
    arm.word(0xe316_0020);
    arm.constant_if(NE, 0, 40);
    arm.word(0xe316_0010);
    arm.constant_if(NE, 0, 328);
    arm.store(0, 11, TOP_X_OFFSET);
    arm.constant(0, 104);
    arm.word(0xe316_0040);
    arm.constant_if(NE, 0, 24);
    arm.word(0xe316_0080);
    arm.constant_if(NE, 0, 184);
    arm.store(0, 11, TOP_Y_OFFSET);
    arm.load(0, 4, 0xb8);
    arm.word(0xe084_1180); // CodexAstraUlt: r1 = HID + ring index * 8.
    arm.load(0, 1, 0xc8);
    arm.word(0xe1a0_2800);
    arm.word(0xe1a0_2822);
    arm.store(2, 11, TOUCH_X_OFFSET);
    arm.word(0xe1a0_3820);
    arm.store(3, 11, TOUCH_Y_OFFSET);
    arm.load(6, 1, 0xcc);
    arm.store(6, 11, TOUCH_VALID_OFFSET);
    arm.word(0xe252_2010);
    arm.constant_if(MI, 2, 0);
    arm.constant(0, 288);
    arm.word(0xe152_0000);
    arm.word(0x81a0_2000);
    arm.word(0xe253_3010);
    arm.constant_if(MI, 3, 0);
    arm.word(0xe353_00d0);
    arm.constant_if(HI, 3, 208);
    arm.word(0xe356_0000);
    arm.constant_if(EQ, 2, 144);
    arm.constant_if(EQ, 3, 104);
    arm.store(2, 11, BOTTOM_X_OFFSET);
    arm.store(3, 11, BOTTOM_Y_OFFSET);
    exit
}

// CodexAstraUlt: A changes the guest's DSP voice rate, rather than asking the
// native frontend to synthesize a different beep. Preserve other voice state.
fn update_audio(arm: &mut Arm) {
    arm.stage(6);
    arm.load(6, 11, BUTTONS_OFFSET);
    arm.constant(0, 1.0f32.to_bits());
    arm.word(0xe316_0001);
    arm.constant_if(NE, 0, 2.0f32.to_bits());
    arm.load(1, 11, TONE_RATE_OFFSET);
    arm.word(0xe150_0001);
    let unchanged = arm.branch(EQ);
    arm.store(0, 11, TONE_RATE_OFFSET);
    arm.load(6, 11, VOICE_POINTER);
    arm.store(0, 6, 0x34);
    arm.write(6, 0, 1 << 18);
    arm.resolve(unchanged, arm.at());
    arm.load(6, 11, STATUS_POINTER);
    arm.constant(0, 0x20000);
    arm.word(0xe086_6000);
    arm.word(0xe5d6_0000);
    arm.store(0, 11, DSP_ENABLED_OFFSET);
    arm.load(0, 6, 4);
    arm.word(0xe1a0_0860); // CodexAstraUlt: ROR16 decodes a DSP32 status value.
    arm.store(0, 11, DSP_POSITION_OFFSET);
    arm.half(true, 0, 6, 8);
    arm.store(0, 11, DSP_BUFFER_ID_OFFSET);
}

// CodexAstraUlt: Guest patches only its writable PICA data. GSP submits actual
// PICA draws, tiled-to-linear display transfer and framebuffer swap per panel.
fn draw_panel(arm: &mut Arm, panel: Panel) {
    let top = matches!(panel, Panel::Top);
    arm.stage(if top { 7 } else { 8 });
    let template = pica::template(panel);
    let (commands, color, scanout, x, y) = if top {
        (
            pica::TOP_COMMANDS,
            pica::TOP_COLOR,
            pica::TOP_SCANOUT,
            TOP_X_OFFSET,
            TOP_Y_OFFSET,
        )
    } else {
        (
            pica::BOTTOM_COMMANDS,
            pica::BOTTOM_COLOR,
            pica::BOTTOM_SCANOUT,
            BOTTOM_X_OFFSET,
            BOTTOM_Y_OFFSET,
        )
    };
    arm.load(0, 11, x);
    arm.load(1, 11, y);
    arm.word(0xe261_20d0); // CodexAstraUlt: Native X = 208 - upright Y.
    arm.constant(3, panel.width() - pica::MARKER_SIZE);
    arm.word(0xe043_3000);
    arm.word(0xe182_2803); // CodexAstraUlt: Native Y in high half of viewport XY.
    arm.constant(6, commands + template.viewport_offset);
    arm.store(2, 6, 0);
    arm.load(
        6,
        11,
        if top {
            BUTTONS_OFFSET
        } else {
            TOUCH_VALID_OFFSET
        },
    );
    arm.word(if top { 0xe316_0001 } else { 0xe356_0000 });
    let normal = pica::color_words(false, panel);
    let active = pica::color_words(true, panel);
    for vertex in 0..3 {
        for component in 0..3 {
            arm.constant(0, normal[component]);
            arm.constant_if(NE, 0, active[component]);
            arm.constant(1, commands + template.color_offsets[vertex * 3 + component]);
            arm.store(0, 1, 0);
        }
    }
    arm.ipc(0, 0x0006_0080);
    arm.ipc(1, commands);
    arm.ipc(2, template.bytes.len() as u32);
    arm.send(9);
    arm.ipc(0, 0x000d_0140);
    arm.ipc(1, color);
    arm.ipc(2, scanout);
    arm.ipc(3, 240 | panel.width() << 16);
    arm.ipc(4, 240 | panel.width() << 16);
    arm.ipc(5, 0);
    arm.send(9);
    arm.ipc(0, 0x0005_01c0);
    arm.ipc(1, u32::from(!top));
    arm.ipc(2, 0);
    arm.ipc(3, scanout);
    arm.ipc(4, scanout);
    arm.ipc(5, 960);
    arm.ipc(6, 0);
    arm.ipc(7, 0);
    arm.send(9);
}

pub fn native_text() -> Vec<u8> {
    let mut arm = Arm::new();
    initialize_services(&mut arm);
    initialize_audio(&mut arm);
    arm.stage(4);
    arm.copy(
        TOP_TEMPLATE,
        pica::TOP_COMMANDS,
        pica::template(Panel::Top).bytes.len(),
    );
    arm.copy(
        BOTTOM_TEMPLATE,
        pica::BOTTOM_COMMANDS,
        pica::template(Panel::Bottom).bytes.len(),
    );
    arm.ipc(0, 0x000b_0040);
    arm.ipc(1, 0);
    arm.send(9);

    let frame = arm.at();
    let exit = sample_input(&mut arm);
    update_audio(&mut arm);
    draw_panel(&mut arm, Panel::Top);
    draw_panel(&mut arm, Panel::Bottom);
    arm.constant(6, FALLBACK);
    arm.word(0xe12f_ff36);
    arm.store(7, 11, FALLBACK_COUNT_OFFSET);
    arm.load(0, 11, FRAME_SERIAL_OFFSET);
    arm.word(0xe280_0001);
    arm.store(0, 11, FRAME_SERIAL_OFFSET);
    arm.write(11, CHECKPOINT_OFFSET, CHECKPOINT);
    arm.constant(0, 16_666_667);
    arm.constant(1, 0);
    arm.svc(0x0a);
    arm.back(AL, frame);

    // CodexAstraUlt: SELECT+START performs a guest DSP shutdown and ordinary
    // process exit. It does not clear saves or replace the native activity.
    arm.resolve(exit, arm.at());
    arm.stage(9);
    arm.write(11, EXIT_REQUESTED_OFFSET, 1);
    arm.write(11, PIPE_STATE, 1);
    arm.ipc(0, 0x000d_0082);
    arm.ipc(1, 2);
    arm.ipc(2, 1);
    arm.ipc(3, 0x4002);
    arm.ipc(4, DATA + PIPE_STATE);
    arm.send(5);
    arm.svc(3);
    arm.finish()
}

// CodexAstraUlt: The actual loader receives an original NCCH with two RX pages,
// four immutable data pages and one writable page. Deliberate fallback remains
// outside native_text while inside the fully guarded executable mapping.
pub fn image() -> Vec<u8> {
    let native = native_text();
    let mut code = vec![0u8; (TEXT_BYTES + RODATA_BYTES + 0x1000) as usize];
    code[..native.len()].copy_from_slice(&native);
    let helper: Vec<u8> = [0xe287_7001u32, 0xe12f_ff1e]
        .into_iter()
        .flat_map(u32::to_le_bytes)
        .collect();
    let helper_at = (FALLBACK - TEXT) as usize;
    code[helper_at..helper_at + helper.len()].copy_from_slice(&helper);
    let ro_at = TEXT_BYTES as usize;
    code[ro_at..ro_at + 5].copy_from_slice(b"srv:\0");
    for (panel, address) in [(Panel::Top, TOP_TEMPLATE), (Panel::Bottom, BOTTOM_TEMPLATE)] {
        let template = pica::template(panel);
        assert!(template.bytes.len() <= 0x1f00);
        let at = (address - TEXT) as usize;
        code[at..at + template.bytes.len()].copy_from_slice(&template.bytes);
    }
    let mut out = vec![0u8; 0x800];
    out[0x100..0x104].copy_from_slice(b"NCCH");
    out[0x118..0x120].copy_from_slice(&PROGRAM_ID.to_le_bytes());
    out[0x18c] = 1;
    out[0x18f] = 4;
    out[0x1a0..0x1a4].copy_from_slice(&3u32.to_le_bytes());
    for (at, address, bytes) in [
        (0x210, TEXT, TEXT_BYTES),
        (0x220, RODATA, RODATA_BYTES),
        (0x230, DATA, 0x1000),
    ] {
        let entry: Vec<u8> = [address, bytes / 0x1000, bytes]
            .into_iter()
            .flat_map(u32::to_le_bytes)
            .collect();
        out[at..at + 12].copy_from_slice(&entry);
    }
    out[0x21c..0x220].copy_from_slice(&0x1000u32.to_le_bytes());
    out[0x40f] = 0x30;
    out[0x600..0x605].copy_from_slice(b".code");
    out[0x60c..0x610].copy_from_slice(&(code.len() as u32).to_le_bytes());
    out.extend(code);
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::homebrew::{InputState, PadState, Session};
    use std::time::{SystemTime, UNIX_EPOCH};

    // CodexAstraUlt: Exercise real ARM conditional/clamping paths beyond the
    // public four-stage probe. Expected positions are literal boundary values;
    // exact displayed pixels still come through guest PICA and scanout.
    #[test]
    fn original_guest_consumes_touch_edges_and_opposite_direction_precedence() {
        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let directory = std::env::temp_dir().join(format!(
            "droidds-original-guest-edges-{}-{unique}",
            std::process::id()
        ));
        let mut session = Session::create(&std::env::temp_dir(), &directory, false, false).unwrap();
        for (buttons, touch, top, bottom) in [
            (PadState::LEFT | PadState::DOWN, (0, 0), (40, 184), (0, 0)),
            (
                PadState::LEFT | PadState::RIGHT | PadState::UP | PadState::DOWN,
                (319, 239),
                (328, 184),
                (288, 208),
            ),
            (PadState::empty(), (0, 239), (184, 104), (0, 208)),
            (PadState::empty(), (319, 0), (184, 104), (288, 0)),
        ] {
            let input = InputState {
                buttons,
                touch: Some(touch),
                ..InputState::default()
            };
            let mut latest = None;
            for _ in 0..4 {
                latest = Some(session.frame(input).unwrap());
            }
            let frame = latest.unwrap();
            let guest = session.guest();
            assert_eq!(guest["service_error_stage"], 0);
            assert_eq!(guest["buttons"], buttons.bits());
            assert_eq!(guest["touch_x"], touch.0);
            assert_eq!(guest["touch_y"], touch.1);
            assert_eq!(guest["touch_valid"], 1);
            assert_eq!(guest["top_x"], top.0);
            assert_eq!(guest["top_y"], top.1);
            assert_eq!(guest["bottom_x"], bottom.0);
            assert_eq!(guest["bottom_y"], bottom.1);
            assert_eq!(
                frame.top,
                pica::expected_pixels(
                    Panel::Top,
                    pica::VisualState {
                        x: top.0,
                        y: top.1,
                        active: false
                    }
                )
            );
            assert_eq!(
                frame.bottom,
                pica::expected_pixels(
                    Panel::Bottom,
                    pica::VisualState {
                        x: bottom.0,
                        y: bottom.1,
                        active: true
                    }
                )
            );
        }
        assert_eq!(session.report()["memory_faults"], 0);
        drop(session);
        std::fs::remove_dir_all(directory).unwrap();
    }
}
