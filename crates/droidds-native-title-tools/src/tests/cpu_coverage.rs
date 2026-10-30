//! CodexAstraUlt: Original ARM/Thumb and finite-VFP guests exercise the complete
//! generated-library worker route with independent instruction/state oracles.

use super::*;

// CodexAstraUlt: Both routes consume identical immutable title bytes and fresh
// runtime directories. The generated code is compiled, sealed and truly loaded;
// neither mock ABI entries nor a substituted interpreter route qualify these.
fn run_pair(image: Vec<u8>) -> [Value; 2] {
    let fixture = Fixture::from_image(image);
    let original = fs::read(&fixture.input).unwrap();
    let file = fixture.prepared_native_library();
    let library = SealedFile::open(file.as_raw_fd(), request::LIBRARY_LIMIT, None).unwrap();
    let reports = ["interpreter", "native"].map(|route| {
        let mut request = fixture.typed();
        request.route = route.into();
        request.limits.max_steps = 500_000;
        request.limits.max_cycles = 2_000_000;
        let mut report = envelope(Some(&request));
        execute(
            &request,
            &library,
            &fixture.bundle,
            &fixture.root.join(route),
            &mut report,
            Instant::now(),
            |_| {},
        )
        .unwrap();
        assert_eq!(report["status"], "guest_exited", "{report:#}");
        assert_eq!(report["library_loaded"], route == "native");
        assert_eq!(report["runtime_binding_enforced"], true);
        assert_eq!(
            report["synchronized_checkpoints"].as_array().unwrap().len(),
            1
        );
        report
    });
    assert_eq!(fs::read(&fixture.input).unwrap(), original);
    assert_eq!(
        reports[0]["observed"]["state"],
        reports[1]["observed"]["state"]
    );
    assert_eq!(
        reports[0]["synchronized_checkpoints"][0]["boundary"],
        reports[1]["synchronized_checkpoints"][0]["boundary"]
    );
    assert_eq!(
        reports[0]["synchronized_checkpoints"][0]["state"],
        reports[1]["synchronized_checkpoints"][0]["state"]
    );
    let native = &reports[1]["synchronized_checkpoints"][0]["instructions"];
    assert!(
        native["recompiled"]
            .as_u64()
            .unwrap()
            .checked_sub(native["callback_interpreted"].as_u64().unwrap())
            .expect("callback instructions cannot exceed compiled dispatch work")
            > 100_000
    );
    reports
}

// CodexAstraUlt: The forced 100000-cycle checkpoint can finish a partial block
// in the outer interpreter. Count exact guest work across both routes without
// mistaking that supported fallback for either missing work or native coverage.
fn assert_native_work(report: &Value, total: u64, before_svc: u64, callbacks: u64) {
    let observed = &report["observed"];
    assert_eq!(
        observed["recompiled_instructions"].as_u64().unwrap()
            + observed["interpreted_instructions"].as_u64().unwrap(),
        total
    );
    assert_eq!(observed["native_callback_fallback_instructions"], callbacks);
    let sample = &report["synchronized_checkpoints"][0]["instructions"];
    assert_eq!(
        sample["recompiled"].as_u64().unwrap() + sample["interpreted"].as_u64().unwrap(),
        before_svc
    );
    assert_eq!(sample["callback_interpreted"], callbacks);
}

// CodexAstraUlt: Direct BLX enters a discovered Thumb function, whose bounded
// loop reaches a Thumb SVC before BX returns to ARM. Literal/branch offsets and
// cycle counts are specified from the authored instruction sequence, not copied
// from an interpreter or the generator's analysis.
#[test]
fn generated_thumb_svc_and_arm_return_preserve_mode_flags_and_identity() {
    let _serial = SERIAL.lock().unwrap();
    let mut image = fixture::image(0, 0, false);
    for (index, word) in [
        0xfa00_0006u32, // BLX TEXT+32; LR=TEXT+4.
        0xe3a0_407a,    // MOV r4,#0x7a after the Thumb return.
        0xef00_0003,    // ExitProcess from ARM.
    ]
    .into_iter()
    .enumerate()
    {
        image[0x800 + 4 * index..0x804 + 4 * index].copy_from_slice(&word.to_le_bytes());
    }
    for (index, halfword) in [
        0x2200u16, // MOVS r2,#0.
        0x4b03,    // LDR r3,[aligned PC+12] -> literal at TEXT+48.
        0x3201,    // ADDS r2,#1.
        0x429a,    // CMP r2,r3.
        0xd1fc,    // BNE TEXT+36; three instructions per iteration.
        0xdf28,    // GetSystemTick from Thumb; HLE adds 150 cycles.
        0x4770,    // BX LR -> ARM TEXT+4.
    ]
    .into_iter()
    .enumerate()
    {
        image[0x820 + 2 * index..0x822 + 2 * index].copy_from_slice(&halfword.to_le_bytes());
    }
    image[0x830..0x834].copy_from_slice(&40_000u32.to_le_bytes());
    let reports = run_pair(image);
    for report in &reports {
        let sample = &report["synchronized_checkpoints"][0];
        assert_eq!(sample["boundary"]["ordinal"], 1);
        assert_eq!(sample["boundary"]["cycle"], 120_154);
        assert_eq!(sample["boundary"]["number"], 0x28);
        assert_eq!(sample["boundary"]["svc_pc"], fixture::TEXT + 42);
        assert_eq!(sample["boundary"]["thread_guest_id"], 0);
        assert_eq!(sample["state"]["cpsr"], 0x6000_003fu32);
        assert_eq!(sample["state"]["registers"][2], 40_000);
        assert_eq!(sample["state"]["registers"][3], 40_000);
        assert_eq!(sample["state"]["registers"][14], fixture::TEXT + 4);
        assert_eq!(sample["state"]["registers"][15], fixture::TEXT + 44);
        assert_eq!(report["observed"]["cycles"], 120_157);
        assert_eq!(report["observed"]["state"]["cpsr"], 0x6000_001fu32);
        assert_eq!(report["observed"]["state"]["registers"][4], 0x7a);
        assert_eq!(
            report["observed"]["state"]["registers"][15],
            fixture::TEXT + 12
        );
    }
    assert_eq!(reports[0]["observed"]["interpreted_instructions"], 120_007);
    assert_native_work(&reports[1], 120_007, 120_004, 0);
}

// CodexAstraUlt: A native callback must preserve live carry for the following
// ADC, and conditional execution must consume the resulting flags correctly.
// Exactly representable VFP operands give independent bitwise arithmetic and
// conversion oracles; this is deliberately not broad floating-point conformance.
#[test]
fn generated_callback_preserves_live_carry_and_finite_vfp_state_at_svc() {
    let _serial = SERIAL.lock().unwrap();
    let mut image = fixture::image(0, 0, false);
    let words = [
        0xe59f_7054u32, // LDR r7,[pc,#84] -> 40000 at word 23.
        0xe3a0_6000,    // MOV r6,#0.
        0xe286_6001,    // ADD r6,r6,#1.
        0xe156_0007,    // CMP r6,r7.
        0x1aff_fffc,    // BNE word 2; three instructions per iteration.
        0xe3e0_0000,    // MVN r0,#0 -> ffffffff.
        0xe290_1001,    // ADDS r1,r0,#1 -> 0, C=1 and Z=1.
        0xeef8_5a10,    // VMRS r5,FPEXC uses actual callback interpretation.
        0xe2a1_2005,    // ADC r2,r1,#5 -> 6, requiring carry across callback.
        0xe1b0_3fa0,    // LSRS r3,r0,#31 -> 1, C=1.
        0xe352_0006,    // CMP r2,#6 -> Z=1,C=1.
        0x03a0_8055,    // MOVEQ r8,#0x55 executes.
        0x13a0_80aa,    // MOVNE r8,#0xaa must not execute.
        0xe59f_0024,    // LDR r0,[pc,#36] -> IEEE 1.5 at word 24.
        0xee00_0a10,    // VMOV s0,r0.
        0xe59f_1020,    // LDR r1,[pc,#32] -> IEEE 2.0 at word 25.
        0xee00_1a90,    // VMOV s1,r1.
        0xee30_1a20,    // VADD.F32 s2,s0,s1 -> 3.5.
        0xee61_1a20,    // VMUL.F32 s3,s2,s1 -> 7.0.
        0xeebd_2ae1,    // VCVT.S32.F32 s4,s3 -> integer 7.
        0xee12_9a10,    // VMOV r9,s4.
        0xef00_0028,    // GetSystemTick.
        0xef00_0003,    // ExitProcess.
        40_000,
        0x3fc0_0000,
        0x4000_0000,
    ];
    for (index, word) in words.into_iter().enumerate() {
        image[0x800 + 4 * index..0x804 + 4 * index].copy_from_slice(&word.to_le_bytes());
    }
    let reports = run_pair(image);
    for report in &reports {
        let sample = &report["synchronized_checkpoints"][0];
        assert_eq!(sample["boundary"]["ordinal"], 1);
        assert_eq!(sample["boundary"]["cycle"], 120_169);
        assert_eq!(sample["boundary"]["number"], 0x28);
        assert_eq!(sample["boundary"]["svc_pc"], fixture::TEXT + 84);
        assert_eq!(sample["state"]["cpsr"], 0x6000_001fu32);
        for (register, expected) in [
            (2, 6),
            (3, 1),
            (5, 0x4000_0000),
            (6, 40_000),
            (7, 40_000),
            (8, 0x55),
            (9, 7),
        ] {
            assert_eq!(sample["state"]["registers"][register], expected);
        }
        for (register, expected) in [0x3fc0_0000u32, 0x4000_0000, 0x4060_0000, 0x40e0_0000, 7]
            .into_iter()
            .enumerate()
        {
            assert_eq!(sample["state"]["vfp_registers"][register], expected);
        }
        assert_eq!(sample["state"]["fpscr"], 0);
        assert_eq!(sample["state"]["fpexc"], 0x4000_0000);
        assert_eq!(report["observed"]["cycles"], 120_170);
    }
    assert_eq!(reports[0]["observed"]["interpreted_instructions"], 120_020);
    assert_native_work(&reports[1], 120_020, 120_019, 1);
}
