# Dark Moon first guarded native comparison

<!-- CodexAstraUlt: Preserve the owner's first actual private native result,
without promoting mismatched checkpoint evidence to parity or game boot. -->
Reported 2026-10-29 (America/New_York), source `b61a986`. The owner reports
that the worker built and all 103 local checks passed. The one paired run ended
`compared / different`, with no admission or runtime blocker:

| Route | Generated native instructions | Interpreted instructions |
| --- | ---: | ---: |
| Native | 1,999,970 | 30 |
| Interpreter | 0 | 2,000,000 |

The first differing checkpoint is **100,000 guest cycles**, in `cpsr` and
`reschedule_pending`. All 5,800 prior files were preserved. The supplied summary
is `dark-moon-native-comparison-20261029-evidence-001/dark-moon-native-comparison-summary.md`.
The cloud session has the owner's summary, not the private library, raw reports,
hashes or actual differing flag values. The 103-check result is owner-reported;
it is distinct from the cloud suite counts.

## Investigation and next observation

<!-- CodexAstraUlt: Separate reproduced generic mechanisms from an attribution
that requires the owner's actual checkpoint values and follow-up evidence. -->
Two generic issues were reproduced with original inputs:

- The generation-3 compiler can omit changed registers/flags at a budget exit
  when its liveness analysis says the continuation will overwrite them. Raw
  architectural snapshots at those stops can differ. In an authored ADD/CMP
  loop, CPSR differs at 100,000 cycles and the recorded full active state agrees
  after the next CMP. This does not establish that Dark Moon's difference has
  the same cause, or that all omitted state is unobservable to other threads.
- Native dispatch could shift the periodic scheduling phase and leave a pending
  request after long single-thread work; the interpreter could observe sleeping
  threads/timers late. The shared scheduler correction addresses those behaviors
  without forcing empty native scheduling passes every 8192 cycles.

The [correction and original test evidence](../builds/0.0.7-native-boundaries.md)
also adds a separate bounded comparison after SVC dispatches, where generated
code synchronizes its changed locals. Both routes must have the same event
ordinal, actual cycle, SVC number/PC and originating guest thread. A matching
sample requires actual native work before that sample. Raw differences remain
reported; a later matching sample does not erase or explain them automatically.

The next local task is **one default comparison with the rebuilt host worker**,
using the same prepared title and completed library. Follow
[the native-run procedure](../PRIVATE_TITLE_NATIVE_RUN.md). Do not regenerate
title sources, recompile its objects or increase execution limits. Return both
raw and synchronized outcomes, exact CPU flag/PC values at the first raw
difference, and any additional differing fields. Missing synchronized boundaries
are inconclusive; they do not authorize a longer run.

This report establishes observed private native execution. Native parity,
interactive boot, audio/graphics correctness, Android packaging and Thor
performance remain unqualified.
