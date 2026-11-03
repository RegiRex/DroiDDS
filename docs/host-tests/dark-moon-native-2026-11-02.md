# Dark Moon corrected-scheduler native comparison

<!-- CodexAstraUlt: Preserve the owner's follow-up exactly, including raw
differences and missing boundaries, without inventing a new cloud private run. -->
Reported **2026-11-02** (America/New_York), source `857ff47`. The owner reports
an offline/locked worker rebuild, **57 targeted checks passed**, and exactly one
default paired comparison with the retained title preparation and Linux library.
No title regeneration or recompilation occurred; **5,843 prior files remained
unchanged**. Both routes stopped at the cycle budget.

| Route | Generated native instructions | Interpreted instructions |
| --- | ---: | ---: |
| Native | 1,999,970 | 30 |
| Interpreter | 0 | 2,000,000 |

The raw result remains **different**: CPSR differs at 100,000 and 2,000,000
cycles. At the first difference:

| Field | Interpreter | Native |
| --- | --- | --- |
| CPSR | `0x8000001F` | `0x0000001F` |
| `registers[15]` | `0x00100030` | `0x00100030` |
| `reschedule_pending` | `false` | `false` |

The supplied first checkpoint differs only in the negative-condition flag among
these fields. The earlier reported scheduler-pending mismatch is absent here.
The summary does not supply the second checkpoint's exact flag values.

The supplemental synchronized comparison **matches at cycle 303,222**. Samples
for the 500,000, 1,000,000 and 2,000,000 thresholds are absent on both routes.
No longer run is inferred or requested to fill these missing samples.

## Interpretation

<!-- CodexAstraUlt: A fully saved sampled match is useful bounded evidence;
it cannot retroactively qualify arbitrary snapshots or every thread state. -->
This is consistent with the [scheduler correction and fully saved SVC
observations](../builds/0.0.7-native-boundaries.md). The generation-3 compiler's
known omission of dead flags at a budget return can explain raw observation
differences in authored fixtures. This summary alone does not prove that it
explains Dark Moon's flags, or that every relevant native/interpreter state is
equivalent. The raw `different` result remains part of the evidence.

The cloud session has the owner's summary, not the full private reports,
worker/input/library hashes or generated code. The reported synchronized match
is accepted as owner-supplied evidence, not independently revalidated raw event
identity/counter data. It does not establish interactive boot, graphics/audio
correctness or Thor performance.

The previously requested `857ff47` comparison is now performed. Its changes
are already included in the public Android preview and current main. No new
production correction or repeated unchanged private trace is justified by this
summary. Cloud follow-up adds original generated-code coverage for live
condition flags across budget preemption and a real thread switch. The next
private task uses the [Android build and device procedure](../ANDROID_TITLE_BUILD.md)
with the retained prepared C and a separate ARM64 compilation; the successful
521-object Linux build remains untouched.
