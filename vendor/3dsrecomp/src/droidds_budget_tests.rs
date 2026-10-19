//! CodexAstraUlt: Native execution regressions for conditional-branch budget
//! accounting. The hand-counted original loops contain no memory or retail data.

use crate::{codegen, compile::Compiler, discover, image::Segment};
use std::{fs, process::Command};

fn executes_with_exact_budget(thumb: bool) {
    // CodexAstraUlt: MOV counter,3; loop: SUBS counter,1; BNE loop;
    // MOV result,42; SVC42. Both encodings execute exactly nine instructions.
    let bytes: Vec<u8> = if thumb {
        [0x2003u16, 0x3801, 0xd1fd, 0x212a, 0xdf2a]
            .into_iter().flat_map(u16::to_le_bytes).collect()
    } else {
        [0xe3a0_0003u32, 0xe250_0001, 0x1aff_fffd, 0xe3a0_102a, 0xef00_002a]
            .into_iter().flat_map(u32::to_le_bytes).collect()
    };
    let program = discover::Program {
        text: Segment { base: 0x0010_0000, bytes },
        seeds: vec![(0x0010_0000 | u32::from(thumb), discover::Source::Entry)],
        slots: Some(Default::default()),
    };
    let analysis = discover::analyze(&program);
    let unit = codegen::Unit { module: None, program: &program, analysis: &analysis };
    let directory = std::env::temp_dir().join(format!("droidds-budget-{}-{}-{}",
        std::process::id(), u8::from(thumb),
        std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()));
    fs::create_dir(&directory).unwrap();
    let mut sources = Vec::new();
    for (name, content) in codegen::generate(&[unit], &[]) {
        fs::write(directory.join(&name),content).unwrap();
        if name.ends_with(".c") { sources.push(name); }
    }
    let entry = if thumb { "t_00100000" } else { "f_00100000" };
    // CodexAstraUlt: Run with sufficient budget, then stop on a loop boundary
    // after exactly five instructions and resume. Exit codes expose which
    // register, stop reason or accounting assertion failed in the native code.
    let harness = r#"
#include "recomp.h"
extern void @ENTRY@(Context *);
int main(void) {
    Context state = {0};
    state.thumb = @THUMB@;
    state.r[15] = 0x00100000u;
    state.budget = 64;
    @ENTRY@(&state);
    if (state.r[0] != 0 || state.r[1] != 42) return 1;
    if (state.exit != EXIT_SVC || state.svc != 42) return 2;
    if (state.budget != 55) return 3;
    Context sliced = {0};
    sliced.thumb = @THUMB@;
    sliced.r[15] = 0x00100000u;
    sliced.budget = 5;
    @ENTRY@(&sliced);
    if (sliced.exit != EXIT_BUDGET || sliced.budget != 0) return 4;
    if (sliced.r[0] != 1 || sliced.r[1] != 0) return 5;
    if (sliced.r[15] != 0x00100000u + @STRIDE@) return 6;
    sliced.budget = 64;
    sliced.exit = EXIT_NONE;
    @ENTRY@(&sliced);
    if (sliced.r[0] != 0 || sliced.r[1] != 42) return 7;
    if (sliced.exit != EXIT_SVC || sliced.svc != 42) return 8;
    if (sliced.budget != 60) return 9;
    return 0;
}
"#.replace("@ENTRY@",entry).replace("@THUMB@",if thumb {"1"} else {"0"})
        .replace("@STRIDE@",if thumb {"2"} else {"4"});
    fs::write(directory.join("budget-main.c"),harness).unwrap();
    sources.push("budget-main.c".into());
    let compiler = Compiler::find().expect("a host C compiler is required for native budget regression tests");
    let built = Command::new(&compiler.program).args(&compiler.leading)
        .args(["-O2","-ffp-contract=off","-fno-math-errno","-I."])
        .args(sources).args(["-lm","-o","budget-test"])
        .current_dir(&directory).output().unwrap();
    assert!(built.status.success(),"native budget fixture compilation failed: {}",String::from_utf8_lossy(&built.stderr));
    let executed = Command::new(directory.join("budget-test")).output().unwrap();
    assert!(executed.status.success(),"{} native budget regression exited {:?}; retained fixture {}",if thumb {"Thumb"}else{"ARM"},executed.status.code(),directory.display());
    fs::remove_dir_all(directory).unwrap();
}

#[test]
fn arm_conditional_backedge_preserves_exact_budget_and_resume() { executes_with_exact_budget(false); }

#[test]
fn thumb_conditional_backedge_preserves_exact_budget_and_resume() { executes_with_exact_budget(true); }
