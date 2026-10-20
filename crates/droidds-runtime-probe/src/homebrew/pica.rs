//! CodexAstraUlt: Original native-resolution PICA drawings for the interactive
//! guest. The guest owns list submission, display transfer and buffer swapping;
//! the independent oracle below never reads these commands or GPU memory.

use zakuro_gpu::registers::*;

// CodexAstraUlt: Four fixed, disjoint VRAM slots bound this fixture's render
// targets. Each 0x80000-byte slot fits the larger 240*400*4-byte top image;
// commands live after all four, never inside a framebuffer as in the tiny .5
// fixture. These are guest virtual addresses, not host pointers.
pub const TOP_COLOR: u32 = 0x1f00_0000;
pub const BOTTOM_COLOR: u32 = 0x1f08_0000;
pub const TOP_SCANOUT: u32 = 0x1f10_0000;
pub const BOTTOM_SCANOUT: u32 = 0x1f18_0000;
pub const TOP_COMMANDS: u32 = 0x1f20_0000;
pub const BOTTOM_COMMANDS: u32 = 0x1f20_2000;
pub const MARKER_SIZE: u32 = 32;
pub const COMMAND_CAPACITY: usize = 0x2000;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Panel {
    Top,
    Bottom,
}

impl Panel {
    pub const fn width(self) -> u32 {
        match self {
            Self::Top => 400,
            Self::Bottom => 320,
        }
    }

    pub const fn height(self) -> u32 {
        240
    }
}

// CodexAstraUlt: Upright marker coordinates come from guest-observed HID state.
// They are deliberately distinct from rotated PICA viewport coordinates.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct VisualState {
    pub x: u32,
    pub y: u32,
    pub active: bool,
}

pub struct Template {
    pub bytes: Vec<u8>,
    /// Byte offset of the marker's viewport value, not its register header.
    pub viewport_offset: u32,
    /// Three packed color words for each of the marker's three vertices.
    pub color_offsets: [u32; 9],
}

// CodexAstraUlt: All generated inputs are exactly representable integers or
// half-integers. This packs PICA float24 without depending on the renderer's
// decoder, preserving an independently specified public fixture.
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

pub fn color_words(active: bool, panel: Panel) -> [u32; 3] {
    vector(match (panel, active) {
        (Panel::Top, false) => [1.0, 0.0, 0.0, 1.0],
        (Panel::Top, true) => [0.0, 1.0, 0.0, 1.0],
        (Panel::Bottom, false) => [1.0, 1.0, 0.0, 1.0],
        (Panel::Bottom, true) => [0.0, 1.0, 1.0, 1.0],
    })
}

// CodexAstraUlt: LCD scanout is column-major, with each column bottom first.
// A rectangle upright at (x,y) therefore has PICA viewport origin
// (240-y-height, panel_width-x-width); the display transfer needs no flip.
pub fn viewport_xy(panel: Panel, x: u32, y: u32) -> u32 {
    assert!(x <= panel.width() - MARKER_SIZE && y <= 240 - MARKER_SIZE);
    (240 - y - MARKER_SIZE) | ((panel.width() - x - MARKER_SIZE) << 16)
}

struct Commands {
    words: Vec<u32>,
    draw: u32,
}

impl Commands {
    fn write(&mut self, register: usize, value: u32) -> u32 {
        let offset = (self.words.len() * 4) as u32;
        self.words.extend([value, register as u32 | 0xf0000]);
        offset
    }

    // CodexAstraUlt: One oversized triangle clipped by an integer viewport
    // fills exactly the requested rectangle. Every draw supplies all positions
    // and colors; no stale fixed attribute or previous frame supplies content.
    fn rectangle(&mut self, panel: Panel, area: [u32; 4], color: [u32; 3]) -> (u32, [u32; 9]) {
        let [x, y, width, height] = area;
        assert!(width > 0 && height > 0 && x + width <= panel.width() && y + height <= 240);
        self.write(REG_VIEWPORT_WIDTH, float24(height as f32 / 2.0));
        self.write(REG_VIEWPORT_HEIGHT, float24(width as f32 / 2.0));
        let viewport = self.write(
            REG_VIEWPORT_XY,
            (240 - y - height) | ((panel.width() - x - width) << 16),
        );
        self.write(REG_FIXED_ATTRIBUTE_INDEX, 15);
        let mut colors = [0; 9];
        for (vertex, position) in [
            [-1.0, -1.0, -0.5, 1.0],
            [3.0, -1.0, -0.5, 1.0],
            [-1.0, 3.0, -0.5, 1.0],
        ]
        .into_iter()
        .enumerate()
        {
            for (word, value) in vector(position).into_iter().enumerate() {
                self.write(REG_FIXED_ATTRIBUTE_DATA + word, value);
            }
            for (word, value) in color.into_iter().enumerate() {
                colors[vertex * 3 + word] = self.write(REG_FIXED_ATTRIBUTE_DATA + word, value);
            }
        }
        self.draw += 1;
        self.write(0x245, self.draw);
        (viewport, colors)
    }
}

pub fn template(panel: Panel) -> Template {
    // CodexAstraUlt: Reuse only the publicly specified pass-through shader
    // shape qualified by .5. Each screen has 240 columns in tiled storage and
    // 400/320 rows; both extents are multiples of an 8x8 PICA tile.
    let mut commands = Commands {
        words: Vec::new(),
        draw: 0,
    };
    commands.write(REG_VS_BLOCK + SHADER_PROGRAM_INDEX, 0);
    for word in [0x13 << 26, (0x13 << 26) | (1 << 21) | (1 << 12), 0x22 << 26] {
        commands.write(REG_VS_BLOCK + SHADER_PROGRAM_DATA, word);
    }
    commands.write(REG_VS_BLOCK + SHADER_DESCRIPTOR_INDEX, 0);
    commands.write(
        REG_VS_BLOCK + SHADER_DESCRIPTOR_DATA,
        0xf | (0b00_01_10_11 << 5) | (0b00_01_10_11 << 14),
    );
    commands.write(REG_SHADER_OUTPUT_TOTAL, 2);
    commands.write(REG_SHADER_OUTPUT_MAP, 0x0302_0100);
    commands.write(REG_SHADER_OUTPUT_MAP + 1, 0x0b0a_0908);
    commands.write(REG_VS_INPUT_REGISTER_MAP_LOW, 0x10);
    commands.write(REG_VS_ATTRIBUTE_COUNT, 1);
    commands.write(REG_VS_BLOCK + SHADER_INPUT_CONFIG, 1);
    commands.write(REG_VS_BLOCK + SHADER_OUTPUT_MASK, 3);
    let target = match panel {
        Panel::Top => TOP_COLOR,
        Panel::Bottom => BOTTOM_COLOR,
    };
    commands.write(
        REG_COLOR_BUFFER_ADDRESS,
        (target - 0x1f00_0000 + 0x1800_0000) >> 3,
    );
    commands.write(REG_COLOR_BUFFER_FORMAT, 4);
    commands.write(
        REG_FRAMEBUFFER_DIMENSIONS,
        240 | ((panel.width() - 1) << 12),
    );
    commands.write(REG_COLOR_BUFFER_WRITE, 0xf);
    commands.write(REG_DEPTH_COLOR_MASK, 0xf << 8);
    commands.write(REG_LOGIC_OP, 3);

    // CodexAstraUlt: Distinct backgrounds and an asymmetric corner reveal
    // channel swaps, wrong screen selection and flips even before any input.
    let background = match panel {
        Panel::Top => [0.0, 0.0, 1.0, 1.0],
        Panel::Bottom => [0.0, 0.0, 0.0, 1.0],
    };
    commands.rectangle(panel, [0, 0, panel.width(), 240], vector(background));
    let (corner, color) = match panel {
        Panel::Top => ([8, 8, 24, 16], [1.0, 1.0, 1.0, 1.0]),
        Panel::Bottom => ([8, 8, 16, 24], [1.0, 0.0, 1.0, 1.0]),
    };
    commands.rectangle(panel, corner, vector(color));
    let (viewport_offset, color_offsets) = commands.rectangle(
        panel,
        [
            (panel.width() - MARKER_SIZE) / 2,
            104,
            MARKER_SIZE,
            MARKER_SIZE,
        ],
        color_words(false, panel),
    );
    let bytes: Vec<u8> = commands
        .words
        .into_iter()
        .flat_map(u32::to_le_bytes)
        .collect();
    assert!(bytes.len() <= COMMAND_CAPACITY);
    Template {
        bytes,
        viewport_offset,
        color_offsets,
    }
}

// CodexAstraUlt: This oracle describes the visible image directly in upright
// coordinates and literal RGBA bytes. It shares neither the command builder's
// viewport transform/float packing nor the production tiling/scanout decoder.
// Guest-observed coordinates are validated before indexing; no renderer output
// or generated command bytes are used to manufacture the expected result.
pub fn expected_pixels(panel: Panel, state: VisualState) -> Vec<u8> {
    let width = match panel {
        Panel::Top => 400,
        Panel::Bottom => 320,
    };
    assert!(state.x <= width - 32 && state.y <= 208);
    let mut pixels = Vec::with_capacity((width * 240 * 4) as usize);
    for y in 0..240 {
        for x in 0..width {
            let mut color = match panel {
                Panel::Top => [0, 0, 255, 255],
                Panel::Bottom => [0, 0, 0, 255],
            };
            match panel {
                Panel::Top if (8..32).contains(&x) && (8..24).contains(&y) => {
                    color = [255, 255, 255, 255];
                }
                Panel::Bottom if (8..24).contains(&x) && (8..32).contains(&y) => {
                    color = [255, 0, 255, 255];
                }
                _ => {}
            }
            if (state.x..state.x + 32).contains(&x) && (state.y..state.y + 32).contains(&y) {
                color = match (panel, state.active) {
                    (Panel::Top, false) => [255, 0, 0, 255],
                    (Panel::Top, true) => [0, 255, 0, 255],
                    (Panel::Bottom, false) => [255, 255, 0, 255],
                    (Panel::Bottom, true) => [0, 255, 255, 255],
                };
            }
            pixels.extend(color);
        }
    }
    pixels
}
