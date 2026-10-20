//! CodexAstraUlt: Interactive original homebrew and its headless qualification.
//! Android presents guest pixels and PCM; it never substitutes a host scene.

pub mod fixture;
pub mod pica;
#[cfg(feature = "producer")]
pub mod producer;
mod session;

pub use session::Session;
pub use zakuro_core::services::hid::{InputState, PadState};
pub const AUDIO_SAMPLE_RATE: f64 = zakuro_core::AUDIO_SAMPLE_RATE;

use crate::require;
use pica::{Panel, VisualState};
use serde_json::{json, Value};
use std::{path::Path, time::Instant};

// CodexAstraUlt: One bounded transfer per emulated display interval. Buffers are
// actual scanout/PCM results and can be reused by a frontend after it copies them.
#[derive(Debug)]
pub struct Frame {
    pub top: Vec<u8>,
    pub bottom: Vec<u8>,
    pub pcm: Vec<[i16; 2]>,
    pub guest_serial: u32,
    pub frames: u64,
    pub exited: bool,
}

fn visual(input: InputState) -> [VisualState; 2] {
    let top = VisualState {
        x: if input.buttons.contains(PadState::RIGHT) {
            328
        } else if input.buttons.contains(PadState::LEFT) {
            40
        } else {
            184
        },
        y: if input.buttons.contains(PadState::DOWN) {
            184
        } else if input.buttons.contains(PadState::UP) {
            24
        } else {
            104
        },
        active: input.buttons.contains(PadState::A),
    };
    let bottom = match input.touch {
        Some((x, y)) => VisualState {
            x: (x as u32).saturating_sub(16).min(288),
            y: (y as u32).saturating_sub(16).min(208),
            active: true,
        },
        None => VisualState {
            x: 144,
            y: 104,
            active: false,
        },
    };
    [top, bottom]
}

// CodexAstraUlt: These literal sample/geometry oracles are independent of DSP
// parsing, mixing, PICA tiling and framebuffer decoding implementation helpers.
fn pixel_mismatches(actual: &[u8], expected: &[u8]) -> usize {
    if actual.len() != expected.len() {
        return expected.len() / 4;
    }
    actual
        .chunks_exact(4)
        .zip(expected.chunks_exact(4))
        .filter(|(a, b)| a != b)
        .count()
}

fn expected_sample(index: usize, fast: bool) -> [i16; 2] {
    let period = if fast { 20 } else { 40 };
    [if (index / period).is_multiple_of(2) {
        2000
    } else {
        -2000
    }; 2]
}

fn audio_mismatches(actual: &[[i16; 2]], fast: bool) -> usize {
    actual
        .iter()
        .enumerate()
        .filter(|(index, sample)| **sample != expected_sample(*index, fast))
        .count()
}

fn check_guest(guest: &Value, input: InputState) -> Result<(), String> {
    let [top, bottom] = visual(input);
    require(
        guest["checkpoint"] == fixture::CHECKPOINT
            && guest["serial"].as_u64().is_some_and(|n| n > 0)
            && guest["fallback_count"] == guest["serial"]
            && guest["service_error_stage"] == 0,
        format!("homebrew guest checkpoint, helper or service result differs: {guest}"),
    )?;
    let (x, y, valid) = input
        .touch
        .map_or((0, 0, 0), |(x, y)| (x as u32, y as u32, 1));
    require(
        guest["buttons"] == input.buttons.bits()
            && guest["touch_x"] == x
            && guest["touch_y"] == y
            && guest["touch_valid"] == valid,
        format!("homebrew guest did not consume requested HID sample: {guest}"),
    )?;
    require(
        guest["top_x"] == top.x
            && guest["top_y"] == top.y
            && guest["bottom_x"] == bottom.x
            && guest["bottom_y"] == bottom.y
            && guest["tone_rate_bits"]
                == if top.active {
                    2.0f32.to_bits()
                } else {
                    1.0f32.to_bits()
                },
        "homebrew guest visual/audio state differs from independent input rules",
    )
}

struct StageOutput {
    top: Vec<u8>,
    bottom: Vec<u8>,
    pcm: Vec<[i16; 2]>,
}

fn run_case(
    native_dir: &Path,
    scratch: &Path,
    name: &str,
    native: bool,
    hardware: bool,
) -> Result<(Value, Vec<StageOutput>), String> {
    let mut session = Session::create(native_dir, scratch, native, hardware)?;
    let mut stages = Vec::new();
    let mut outputs = Vec::new();
    let mut lifecycle = json!({"pause_rejected_frame":false,"pause_no_progress":false,"resume_progress":false,"guest_exit":false});
    let result = (|| -> Result<(), String> {
        for (stage, input) in [
            ("idle", InputState::default()),
            (
                "buttons",
                InputState {
                    buttons: PadState::A | PadState::RIGHT | PadState::UP,
                    ..InputState::default()
                },
            ),
            (
                "touch",
                InputState {
                    touch: Some((247, 181)),
                    ..InputState::default()
                },
            ),
            ("release", InputState::default()),
        ] {
            let mut last = None;
            // CodexAstraUlt: Four real display intervals settle DSP gain/rate
            // changes; no samples or images are synthesized during this wait.
            for _ in 0..4 {
                last = Some(session.frame(input)?);
            }
            let frame = last.unwrap();
            let guest = session.guest();
            check_guest(&guest, input)?;
            let [top, bottom] = visual(input);
            let top_errors = pixel_mismatches(&frame.top, &pica::expected_pixels(Panel::Top, top));
            let bottom_errors =
                pixel_mismatches(&frame.bottom, &pica::expected_pixels(Panel::Bottom, bottom));
            let audio_errors = audio_mismatches(&frame.pcm, top.active);
            let differing = |actual: &[u8], expected: Vec<u8>| -> Vec<Value> {
                actual.chunks_exact(4).zip(expected.chunks_exact(4)).enumerate()
                .filter(|(_, (a,b))|a!=b).take(4).map(|(index,(actual,expected))|json!({"index":index,"actual":actual,"expected":expected})).collect()
            };
            stages.push(json!({"name":stage,"guest":guest,"frames":frame.frames,
                "top":{"width":400,"height":240,"pixels_checked":96000,"mismatched_pixels":top_errors,
                    "first_mismatches":differing(&frame.top,pica::expected_pixels(Panel::Top,top))},
                "bottom":{"width":320,"height":240,"pixels_checked":76800,"mismatched_pixels":bottom_errors,
                    "first_mismatches":differing(&frame.bottom,pica::expected_pixels(Panel::Bottom,bottom))},
                "audio":{"samples_checked":frame.pcm.len(),"mismatched_samples":audio_errors,"channels":2,
                    "rate_multiplier":if top.active{2}else{1},"first_samples":frame.pcm.iter().take(4).collect::<Vec<_>>()},
                "status":if top_errors==0 && bottom_errors==0 && audio_errors==0 && !frame.pcm.is_empty() && frame.pcm.len().is_multiple_of(160){"passed"}else{"failed"}}));
            require(
                top_errors == 0 && bottom_errors == 0,
                format!(
                    "{name}/{stage}: actual scanout pixels differ ({top_errors}/{bottom_errors})"
                ),
            )?;
            require(
                !frame.pcm.is_empty() && frame.pcm.len().is_multiple_of(160) && audio_errors == 0,
                format!(
                    "{name}/{stage}: actual DSP samples differ ({audio_errors}/{})",
                    frame.pcm.len()
                ),
            )?;
            outputs.push(StageOutput {
                top: frame.top,
                bottom: frame.bottom,
                pcm: frame.pcm,
            });
        }
        let before = session.report();
        session.pause();
        session.pause();
        let rejection = session
            .frame(InputState::default())
            .err()
            .ok_or("paused homebrew accepted execution")?;
        let after = session.report();
        let stopped = before["cycles"] == after["cycles"]
            && before["steps"] == after["steps"]
            && before["guest"] == after["guest"];
        require(
            stopped && rejection.contains("paused") && after["pause_count"] == 1,
            "homebrew pause changed guest state or duplicated transition",
        )?;
        lifecycle["pause_rejected_frame"] = json!(true);
        lifecycle["pause_no_progress"] = json!(true);
        session.resume();
        session.resume();
        session.frame(InputState::default())?;
        let resumed = session.report();
        require(
            resumed["cycles"].as_u64() > before["cycles"].as_u64() && resumed["resume_count"] == 1,
            "homebrew resume did not progress exactly once",
        )?;
        lifecycle["resume_progress"] = json!(true);
        let exit = InputState {
            buttons: PadState::SELECT | PadState::START,
            ..InputState::default()
        };
        let mut exited = false;
        for _ in 0..4 {
            if session.frame(exit)?.exited {
                exited = true;
                break;
            }
        }
        let report = session.report();
        require(
            exited && report["guest"]["exit_requested"] == 1 && report["dsp_running"] == false,
            "homebrew did not exit through its own DSP shutdown and SVC",
        )?;
        lifecycle["guest_exit"] = json!(true);
        // CodexAstraUlt: Fixed sleeps advance emulated time independently of
        // instructions. These exact measured counts reject skipped guest work
        // or compiler-budget drift while keeping host elapsed time separate.
        require(
            report["cycles"] == 80_442_631u64
                && report["frames"] == 17
                && report["frames_delivered"] == 18
                && report["guest"]["serial"] == 18
                && report["guest"]["fallback_count"] == 18
                && report["pcm_samples"] == 9760
                && report["pcm_nonzero_samples"] == 9600
                && report["pcm_peak"] == 2000
                && report["command_lists"] == 36
                && report["draw_calls"] == 108
                && report["vertices_drawn"] == 324
                && report["interpreted_instructions"] == if native { 36 } else { 9073 }
                && report["recompiled_instructions"] == if native { 9037 } else { 0 }
                && report["steps"] == if native { 19851 } else { 28728 },
            format!("{name}: exact guest scheduling, CPU or output totals differ"),
        )?;
        require(
            report["services_seen"] == json!(["dsp::DSP", "gsp::Gpu", "hid:USER"]),
            "homebrew required service route differs",
        )?;
        if native {
            require(
                report["recompiled_instructions"]
                    .as_u64()
                    .is_some_and(|n| n > 0)
                    && report["interpreted_instructions"]
                        .as_u64()
                        .is_some_and(|n| n > 0)
                    && report["native_fallback_instructions"] == 0,
                "homebrew native/interpreter route proof differs",
            )?;
        } else {
            require(
                report["recompiled_instructions"] == 0,
                "interpreter homebrew ran native code",
            )?;
        }
        if hardware {
            require(
                report["hardware"]["recorded_draws"]
                    .as_u64()
                    .is_some_and(|n| n > 0)
                    && report["hardware"]["submissions"]
                        .as_u64()
                        .is_some_and(|n| n > 0),
                "homebrew did not submit hardware draws",
            )?;
        }
        Ok(())
    })();
    let error = result.err();
    Ok((
        json!({"name":name,"status":if error.is_none(){"passed"}else{"failed"},"error":error,
        "stages":stages,"lifecycle":lifecycle,"session":session.report()}),
        outputs,
    ))
}

// CodexAstraUlt: Shared host/Android automation compares actual routes; audible
// playback, physical controls and Android surface lifecycle remain device gates.
pub fn run_probe(native_directory: &Path, scratch: &Path) -> Value {
    let started = Instant::now();
    let mut report = json!({"schema":1,"kind":"droidds-homebrew-probe","fixture":fixture::IDENTITY,
        "status":"failed","error":null,"audio_sample_rate":AUDIO_SAMPLE_RATE,
        "presentation":"rgba_readback","cases":[],"route_comparisons":0,"controls":[],
        "limitations":["Original immutable single-thread NCCH only; no retail title, CRO or multithreaded guest qualification.",
            "Automatic readback and PCM checks do not establish physical display, audible playback or Android surface lifecycle.",
            "DSP high-level PCM voice/mixer protocol only; no Nintendo firmware, DSP instruction set, AAC or ADPCM qualification.",
            "Native-resolution fixture; no handheld game-speed, high-resolution or sustained-memory qualification."]});
    let result = (|| -> Result<(), String> {
        let mut reference: Option<Vec<StageOutput>> = None;
        for (name, native, hardware) in [
            ("interpreter_software", false, false),
            ("native_software", true, false),
            ("native_vulkan", true, true),
        ] {
            let (case, outputs) = run_case(native_directory, scratch, name, native, hardware)?;
            let failed = case["error"].as_str().map(str::to_owned);
            report["cases"].as_array_mut().unwrap().push(case);
            if let Some(error) = failed {
                return Err(error);
            }
            if let Some(expected) = &reference {
                require(
                    outputs.len() == expected.len()
                        && outputs
                            .iter()
                            .zip(expected)
                            .all(|(a, b)| a.top == b.top && a.bottom == b.bottom && a.pcm == b.pcm),
                    format!("{name}: rendered/audio output differs from interpreter reference"),
                )?;
                report["route_comparisons"] =
                    json!(report["route_comparisons"].as_u64().unwrap() + 1);
            } else {
                reference = Some(outputs);
            }
        }
        let reference = reference.unwrap();
        let mut pixel = reference[0].top.clone();
        pixel[17] ^= 1;
        require(
            pixel_mismatches(&pixel, &reference[0].top) == 1,
            "homebrew pixel corruption accepted",
        )?;
        let mut audio = reference[0].pcm.clone();
        audio[0][0] ^= 1;
        require(
            audio_mismatches(&audio, false) == 1,
            "homebrew audio corruption accepted",
        )?;
        let mut budget = Session::create(native_directory, scratch, false, false)?;
        require(
            budget.report()["cycles"] == 0 && budget.report()["guest"]["serial"] == 0,
            "homebrew recreated guest did not start clean",
        )?;
        let rejected = budget.budget_control()?;
        let rejected_steps = budget.report()["steps"].clone();
        drop(budget);
        let mut changed = Session::create(native_directory, scratch, true, false)?;
        let code_rejection = changed.changed_code_control()?;
        report["controls"] = json!([
            {"name":"pixel_mutation_rejected","status":"passed","mismatches":1},
            {"name":"audio_mutation_rejected","status":"passed","mismatches":1},
            {"name":"frame_budget_rejected","status":"passed","rejection":rejected,"steps":rejected_steps},
            {"name":"recreate_starts_clean","status":"passed","initial_cycles":0,"initial_guest_serial":0},
            {"name":"changed_code_before_dispatch_rejected","status":"passed","rejection":code_rejection,
                "steps":changed.report()["steps"],"cycles":changed.report()["cycles"],
                "native_instructions":changed.report()["recompiled_instructions"],"interpreted_instructions":changed.report()["interpreted_instructions"]}]);
        report["status"] = json!("passed");
        Ok(())
    })();
    if let Err(error) = result {
        report["error"] = json!(error);
    }
    report["elapsed_ms"] = json!(started.elapsed().as_millis());
    report
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn independent_audio_oracle_rejects_channel_phase_and_rate_errors() {
        let mut pcm = (0..160)
            .map(|i| expected_sample(i, false))
            .collect::<Vec<_>>();
        assert_eq!(audio_mismatches(&pcm, false), 0);
        assert!(audio_mismatches(&pcm, true) > 0);
        pcm[40][1] ^= 1;
        assert_eq!(audio_mismatches(&pcm, false), 1);
        pcm.rotate_left(1);
        assert!(audio_mismatches(&pcm, false) > 1);
    }
    #[test]
    fn input_oracle_clamps_touch_and_has_explicit_direction_precedence() {
        let states = visual(InputState {
            buttons: PadState::LEFT | PadState::RIGHT | PadState::UP | PadState::DOWN | PadState::A,
            touch: Some((319, 239)),
            ..InputState::default()
        });
        assert_eq!(
            states[0],
            VisualState {
                x: 328,
                y: 184,
                active: true
            }
        );
        assert_eq!(
            states[1],
            VisualState {
                x: 288,
                y: 208,
                active: true
            }
        );
        assert_eq!(
            visual(InputState {
                touch: Some((0, 0)),
                ..InputState::default()
            })[1],
            VisualState {
                x: 0,
                y: 0,
                active: true
            }
        );
    }
}
