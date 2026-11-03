//! CodexAstraUlt: Original guest input crosses real HID IPC, CPU polling and
//! cooperative yields. No private title or host-only input mock qualifies it.

use super::*;

fn buttons(session: &mut Session) -> u32 {
    session
        .system
        .memory
        .read32(homebrew::fixture::DATA + homebrew::fixture::BUTTONS_OFFSET)
}

// CodexAstraUlt: Holding A when HID first becomes available changes the guest's
// pitch before DSP consumes its initialization. The guest must preserve those
// pending configuration flags so both CPU routes still produce actual audio.
#[test]
fn original_guest_held_startup_input_preserves_pending_audio_initialization() {
    let _serial = SERIAL.lock().unwrap();
    let fixture = Fixture::new(homebrew::fixture::image(), true);
    let pressed = InputState {
        buttons: PadState::A,
        ..InputState::default()
    };
    let mut observations = Vec::new();
    for native in [false, true] {
        let mut session = fixture.open(native).unwrap();
        for _ in 0..4096 {
            session.advance(pressed, 1, Duration::from_secs(1)).unwrap();
            if session
                .system
                .memory
                .read32(homebrew::fixture::DATA + homebrew::fixture::FRAME_SERIAL_OFFSET)
                > 0
            {
                break;
            }
        }
        assert_eq!(session.system.frames, 0);
        assert_eq!(
            session
                .system
                .memory
                .read32(homebrew::fixture::DATA + homebrew::fixture::FRAME_SERIAL_OFFSET,),
            1
        );
        // CodexAstraUlt: The authored guest stores the service-returned voice
        // pointer in its workspace; this observes its writes without supplying
        // or repairing any DSP state from the host test.
        let voice = session
            .system
            .memory
            .read32(homebrew::fixture::DATA + 0x120);
        let dirty = session.system.memory.read32(voice);
        let frame = four_frames(&mut session, pressed);
        let enabled = session
            .system
            .memory
            .read32(homebrew::fixture::DATA + homebrew::fixture::DSP_ENABLED_OFFSET);
        eprintln!(
            "startup audio native={native}: pending_dirty={dirty:#010x}, enabled={enabled}, pcm_frames={}, nonzero_frames={}",
            frame.pcm.len(),
            frame.pcm.iter().filter(|sample| **sample != [0, 0]).count()
        );
        observations.push((native, dirty, enabled, frame.pcm));
        drop(session);
        fixture.preserved();
    }
    for (native, dirty, enabled, pcm) in observations {
        assert_eq!(dirty & 0x6207_0000, 0x6207_0000, "native={native}");
        assert_eq!(enabled, 1, "native={native}");
        tone(&pcm, 20);
    }
}

#[test]
fn hid_resource_creation_samples_once_and_yields_do_not_erase_press_edges() {
    let _serial = SERIAL.lock().unwrap();
    let fixture = Fixture::new(homebrew::fixture::image(), true);
    let pressed = InputState {
        buttons: PadState::A,
        touch: Some((47, 81)),
        ..InputState::default()
    };
    for native in [false, true] {
        let mut session = fixture.open(native).unwrap();
        // CodexAstraUlt: Execute actual guest GetIPCHandles. The first sample
        // must exist on return from the creating dispatch, before another slice.
        for _ in 0..2048 {
            session.advance(pressed, 1, Duration::from_secs(1)).unwrap();
            if session.system.services.hid.shared_memory_paddr != 0 {
                break;
            }
        }
        let frame = session.system.frames;
        assert_ne!(session.system.services.hid.shared_memory_paddr, 0);
        assert_eq!(session.system.services.hid.pad_index, 1);
        assert_eq!(session.system.services.hid.touch_index, 1);
        assert_eq!(session.system.services.hid.previous, PadState::A);
        let cycle = session.system.cpu.cycles;
        for _ in 0..8 {
            // CodexAstraUlt: A caller presenting the later release during a
            // yield cannot replace the input already latched for this frame.
            let slice = session
                .advance(InputState::default(), 1, Duration::from_secs(1))
                .unwrap();
            assert_eq!(slice.frames, frame);
            assert!(slice.top.is_none() && slice.bottom.is_none());
            assert_eq!(session.system.services.hid.pad_index, 1);
            assert_eq!(session.system.services.hid.touch_index, 1);
            assert_eq!(session.system.services.hid.input, pressed);
            assert_eq!(session.system.services.hid.previous, PadState::A);
        }
        assert!(session.system.cpu.cycles > cycle);
        // CodexAstraUlt: Explicit pause remains an immediate release boundary,
        // even though no guest frame has completed since the press.
        let cycle = session.system.cpu.cycles;
        session.pause();
        assert_eq!(session.system.services.hid.previous, PadState::empty());
        assert_eq!(session.system.services.hid.input, InputState::default());
        assert_eq!(session.system.cpu.cycles, cycle);
        session.resume();
        session
            .advance(InputState::default(), 1, Duration::from_secs(1))
            .unwrap();
        assert_eq!(session.system.services.hid.previous, PadState::empty());
        drop(session);
        fixture.preserved();
    }
}

#[test]
fn original_guest_consumes_press_and_release_across_many_yielded_slices() {
    let _serial = SERIAL.lock().unwrap();
    let fixture = Fixture::new(homebrew::fixture::image(), true);
    for native in [false, true] {
        let mut session = fixture.open(native).unwrap();
        four_frames(&mut session, InputState::default());
        assert_eq!(buttons(&mut session), 0);
        let frame = session.system.frames;
        let pressed = InputState {
            buttons: PadState::A,
            touch: Some((247, 181)),
            ..InputState::default()
        };
        session.advance(pressed, 1, Duration::from_secs(1)).unwrap();
        assert_eq!(session.system.frames, frame);
        let index = session.system.services.hid.pad_index;
        let mut observed_press = buttons(&mut session) == PadState::A.bits();
        let mut yielded = 0;
        // CodexAstraUlt: The real original ARM guest, not the test, writes its
        // consumed buttons/touch into DATA. Early release arguments model the
        // old per-slice caller and must not erase the frame's latched press.
        for _ in 0..8192 {
            if session.system.frames != frame {
                break;
            }
            let slice = session
                .advance(InputState::default(), 1, Duration::from_secs(1))
                .unwrap();
            if slice.frames == frame {
                yielded += 1;
                assert_eq!(session.system.services.hid.pad_index, index);
            }
            observed_press |= buttons(&mut session) == PadState::A.bits();
        }
        assert!(yielded > 1, "route native={native}");
        assert!(
            observed_press,
            "guest never consumed press: native={native}"
        );
        assert_eq!(session.system.frames, frame + 1);
        assert_eq!(
            session
                .system
                .memory
                .read32(homebrew::fixture::DATA + homebrew::fixture::TOUCH_X_OFFSET),
            247
        );
        let mut observed_release = false;
        for _ in 0..8192 {
            session
                .advance(InputState::default(), 1, Duration::from_secs(1))
                .unwrap();
            if buttons(&mut session) == 0 {
                observed_release = true;
                break;
            }
        }
        assert!(
            observed_release,
            "guest never consumed release: native={native}"
        );
        if native {
            assert!(session.report()["native_instructions"].as_u64().unwrap() > 0);
        }
        drop(session);
        fixture.preserved();
    }
}

// CodexAstraUlt: Reapply the former per-slice HID publication to the actual
// original interpreter guest as a negative control. A press followed by a
// release before its polling instruction disappears, even though the guest
// advances normally. The corrected path above must consume both transitions.
#[test]
fn former_per_slice_publication_reproduces_a_missed_guest_press() {
    let _serial = SERIAL.lock().unwrap();
    let fixture = Fixture::new(homebrew::fixture::image(), false);
    let mut session = fixture.open(false).unwrap();
    four_frames(&mut session, InputState::default());
    let frame = session.system.frames;
    let pressed = InputState {
        buttons: PadState::A,
        ..InputState::default()
    };
    session.advance(pressed, 1, Duration::from_secs(1)).unwrap();
    assert_eq!(session.system.frames, frame);
    let mut observed_press = buttons(&mut session) == PadState::A.bits();
    let mut extra_samples = 0;
    for _ in 0..8192 {
        if session.system.frames != frame {
            break;
        }
        // CodexAstraUlt: These are precisely the superseded operations, kept
        // only in this control; no production bypass or alternate mode exists.
        session.system.set_input(InputState::default());
        hid::update(&mut session.system, InputState::default());
        extra_samples += 1;
        session
            .advance(InputState::default(), 1, Duration::from_secs(1))
            .unwrap();
        observed_press |= buttons(&mut session) == PadState::A.bits();
    }
    assert_eq!(session.system.frames, frame + 1);
    assert!(extra_samples > 8);
    assert!(
        !observed_press,
        "legacy control unexpectedly consumed short press"
    );
    fixture.preserved();
}
