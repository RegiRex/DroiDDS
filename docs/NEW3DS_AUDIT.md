# New 3DS integration audit for 0.0.4

<!-- CodexAstraUlt: Turn the preliminary Xenoblade memory concern into pinned,
reproducible findings without claiming a title or Android runtime was executed. -->

Reviewed **2026-10-19**. **The unmodified selected runtime needs fixes before we can qualify
New 3DS titles.** A synthetic host harness reproduced incorrect New 3DS header
decoding and demonstrated that selecting expanded physical RAM does not expand
the application allocation. These are integration blockers, not evidence that
Xenoblade was run or that a particular game crashed. **0.0.4 does not yet include
the full loader, HLE kernel or these fixes in its Android APK.**

<!-- CodexAstraUlt: Preserve the upstream audit while recording corrected
device layouts separately from unperformed New 3DS retail-title execution. -->
**Current integration update:** the published
[0.0.5 prerelease](https://github.com/RegiRex/DroidDS/releases/tag/v0.0.5-probe.1)
includes the parser, resolved memory, configuration and commitment corrections
below, with real loader/kernel regressions. All required host/CI gates pass in
[run 39341905818](https://github.com/RegiRex/DroidDS/actions/runs/39341905818),
and public downloads are verified; see the
[build record](builds/0.0.5-runtime-integration.md) and
[0.0.5 integration corrections](#005-integration-corrections).
The [owner's 0.0.5 Thor report](device-tests/0.0.5-thor-runtime.md) now passes five
actual loader/memory cases, including New 3DS legacy-64, 124 and 178 MiB modes.
Xenoblade has not been run. The original audit still describes the unchanged
upstream revision. Version 0.0.6 implements original interactive homebrew and
retains these regressions; local/main/tag CI gates and independent public-download
verification pass. The prerelease is published; manual-device qualification
remains pending.

The existing New 3DS model selection, 256 MiB physical RAM, model-reporting
services and extra input service provide useful foundations. We should correct
and test that implementation, rather than replace it or globally triple its
clock constant.

## Exact sources and method

<!-- CodexAstraUlt: Attribute format evidence separately from executed runtime
code. The independent sources are read for layout facts, not imported. -->

| Source | Revision and role |
| --- | --- |
| Zakuro | [`412900a5a020301da15c1cc382585e05a489a535`](https://github.com/fearkov/zakuro/tree/412900a5a020301da15c1cc382585e05a489a535), the selected runtime pin; actual Rust parser/allocator compiled and executed |
| Project_CTR | [`d52c2b0e788c2d085763d7c5dcc4b2edd9ffb7d8`](https://github.com/3DSGuy/Project_CTR/tree/d52c2b0e788c2d085763d7c5dcc4b2edd9ffb7d8); independent public extended-header layout and makerom serialization definitions, read only |
| Uberhar | [`c1516360bc49ab2aa49825632cfd87e31157fb47`](https://github.com/RegiRex/uberhar/tree/c1516360bc49ab2aa49825632cfd87e31157fb47); existing Citra/Azahar-derived layout and region tables, read only, no code copied |

[`tools/audit_new3ds.py`](../tools/audit_new3ds.py) compiles the **unchanged**
Zakuro `ncch.rs`, `reader.rs` and `physical.rs` with Rust `#[path]` modules.
It executes the exact `app_bytes` assignment extracted from the pinned loader.
The thin original harness supplies only reader error types and the actual NCSD
media-unit constant, plus existing host-built `serde`/`zakuro-common` artifacts.
The surrounding title loader, model selection, kernel, services and graphics
are **not** executed. No additional dependency enters the Android APK.

The tool verifies the checkout revision, compares every included source file
with its Git blob, records source/artifact SHA-256 values, uses bounded compiler
and process deadlines, and writes to a new output directory. Its successful
status is **`findings_reproduced`**, not emulator compatibility `passed`.

After the normal host foundation build, reproduce with:

```bash
python3 tools/audit_new3ds.py \
  --zakuro /path/to/pinned/zakuro-checkout \
  --deps target/release/deps \
  --output out/new3ds-audit
```

Executed in the prepared cloud workspace with Rust **1.95.0**, using the selected
Zakuro checkout and `target/release/deps`. The recorded local run was
`out/new3ds-004-audit-1/report.json`: compilation with warnings denied succeeded;
**12 original synthetic cases completed**, six exposing parser mismatches.
Every case actually allocated its application region, rejected an additional
4 KiB page, freed the allocation, and observed the free count restored. This is
a bounded allocator test, not sustained leak/fragmentation qualification.

## Confirmed parser and memory findings

<!-- CodexAstraUlt: Distinguish executed findings from source-only consequences,
and preserve enough exact input/output detail to construct real regressions. -->

**N3DS-001: extended-header fields use the wrong bytes/nibble.**
[Zakuro's parser](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-fs/src/ncch.rs#L250)
reads New 3DS memory mode from the upper nibble of offset `0x20C`, and CPU/L2
flags from `0x20D`. Independent
[makerom definitions](https://github.com/3DSGuy/Project_CTR/blob/d52c2b0e788c2d085763d7c5dcc4b2edd9ffb7d8/makerom/src/exheader.h#L158),
[its writer](https://github.com/3DSGuy/Project_CTR/blob/d52c2b0e788c2d085763d7c5dcc4b2edd9ffb7d8/makerom/src/exheader.c#L307),
and the
[Citra-derived header](https://github.com/RegiRex/uberhar/blob/c1516360bc49ab2aa49825632cfd87e31157fb47/src/core/file_sys/ncch_container.h#L169)
place **L2 at `0x20C` bit 0, CPU speed at `0x20C` bit 1, and memory mode in
`0x20D` bits 0–3**. Original inputs at those offsets reproduce the discrepancy:

| Input New mode / CPU-L2 flags | Expected mode / CPU speed / L2 | Actual pinned parser |
| --- | --- | --- |
| `1 / 0` — 124 MiB, ordinary clock, no L2 | `1 / 0 / false` | `0 / 0 / true` |
| `1 / 3` — 124 MiB, fast clock and L2 | `1 / 1 / true` | `0 / 0 / true` |
| `2 / 0` — 178 MiB, ordinary clock, no L2 | `2 / 0 / false` | `0 / 1 / false` |
| `2 / 3` — 178 MiB, fast clock and L2 | `2 / 1 / true` | `0 / 1 / false` |
| `0 / 1` — legacy memory, L2 only | `0 / 0 / true` | `0 / 0 / false` |
| `0 / 2` — legacy memory, fast clock only | `0 / 1 / false` | `0 / 0 / false` |

**N3DS-002: application memory ignores New 3DS mode.** The
[loader assignment](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-core/src/loader.rs#L74)
uses only `exheader.system_mode.application_memory()`. A scoped search through
all pinned `crates/` found `n3ds_system_mode`, `n3ds_cpu_speed` and
`enable_l2_cache` only in their field declarations and parser initializers.
Even correcting N3DS-001 alone therefore cannot change allocation.

The executable harness supplies `new3ds=true` to the actual allocator and
observes **256 MiB total FCRAM but only 64 MiB application**, for both the 124 MiB
and 178 MiB synthetic requests with Old mode 0. An extra application page fails
after 64 MiB has been allocated, despite ample memory in other regions. Old modes
0/2/3/4/5 still produce their existing 64/96/80/72/32 MiB application sizes.

**N3DS-003: region splits require a complete layout, not just a larger app size.**
The [physical allocator](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-core/src/memory/physical.rs#L35)
assigns up to 32 MiB to System and the remainder to Base. This disagrees with the
read-only [Citra-derived region table](https://github.com/RegiRex/uberhar/blob/c1516360bc49ab2aa49825632cfd87e31157fb47/src/core/hle/kernel/memory.cpp#L28):

| Mode | Table reference: Application / System / Base (MiB) | Pinned allocator observation (MiB) |
| --- | --- | --- |
| Old production | `64 / 44 / 20` | `64 / 32 / 32` |
| Old mode 2 | `96 / 12 / 20` | `96 / 32 / 0` |
| New production | `124 / 100 / 32` | `64 / 32 / 160` for the original 124 MiB request |
| New development 1 | `178 / 46 / 32` | `64 / 32 / 160` for the original 178 MiB request |

Treat that region table as an implementation reference requiring independent
hardware/documentation corroboration and regression tests, not hardware measured
by this audit. In particular, the observed **zero Base region in Old mode 2** is
relevant because services allocate Base memory. Increasing application size in
isolation would leave the other region boundaries incorrect.

**N3DS-004: the reported memory-mode selector is initialized before its source.**
Source inspection finds
[`map_special_pages`](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-core/src/loader.rs#L279)
reading `system.title` to obtain the mode, but `System::new` initializes that field
to `None`, and `load` sets it only at the end, after mapping the configuration
page. The mode therefore defaults to zero on that path. Additionally,
`SystemMode` has implicit enum discriminants 0/1/2/3/4, whereas encoded Old mode
values are 0/2/3/4/5; using `as u32` would still misreport non-production modes
after moving title assignment. Pass an explicit resolved memory configuration
to the mapper and use an explicit raw-mode conversion. This finding is source
analysis; the narrow harness does not execute the configuration-page mapper.

## Scheduling, time and services

<!-- CodexAstraUlt: Avoid treating host core count or a clock multiplier as New
3DS compatibility; identify observable contracts and tests for integration. -->

The runtime already has these useful pieces:

- [Loader/model selection](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-core/src/loader.rs#L82)
  enables New 3DS for NCCH platform 2 and supports an explicit configuration.
  The shared hardware page distinguishes the selected model.
- [APT model/platform queries](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-core/src/services/apt.rs#L478)
  and [CFG model queries](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-core/src/services/cfg.rs#L61)
  already return New 3DS values.
- [`ir:rst`](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-core/src/services/ir_rst.rs#L1)
  implements C-stick/ZL/ZR shared memory and timed updates. Existence is not proof
  that the future Android frontend maps those controls correctly.

The following are **source-level integration risks**, not measured performance
regressions or a demand to introduce host-thread parallelism immediately:

- [`System`](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-core/src/lib.rs#L158)
  has one active CPU context, with saved thread contexts selected by a
  [single scheduler](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-core/src/kernel/mod.rs#L255).
  `processor_id` is stored at thread creation but no scheduling consumer was
  found; `GetCurrentProcessorNumber` returns zero. Test affinity, runnable-thread
  progress, synchronization, TLS and native/fallback transitions before claiming
  expanded guest-core behavior. Serial host scheduling can be intentional, but
  guest-visible results and forward progress still need qualification.
- Parsed CPU-speed/L2 fields have no consumers. APT CPU-time-limit requests are
  stored and read back, without a scheduler consumer found in the same search.
  Separate capability reporting, per-thread CPU accounting and guest timing.
  Do not promise a speedup by flipping these fields.
- [`CPU_CLOCK_HZ`](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-core/src/kernel/thread.rs#L12)
  is shared by tick/time conversions, timeouts, input/camera polling and audio
  sample rate. Frame/audio cadence also has separate constants. Multiplying it
  globally could alter clocks/audio/timeouts without implementing New 3DS CPU
  scheduling. Preserve the guest system-tick domain and validate any execution
  rate conversion with monotonic-clock, timer, vblank and audio tests.
- [`System::new`](https://github.com/fearkov/zakuro/blob/412900a5a020301da15c1cc382585e05a489a535/crates/zakuro-core/src/lib.rs#L254)
  allocates default physical memory; the loader immediately replaces it with a
  second allocation. Resolve layout before construction to avoid redundant
  initialization. Peak resident-memory cost has not been measured, and this is
  not evidence of a persistent memory leak.

## Original 0.0.5 integration gates

<!-- CodexAstraUlt: Define a small dependency-ordered fix set and regressions,
instead of silently modifying a shared Cargo cache or marking Xenoblade ready. -->

<!-- CodexAstraUlt: Keep the original audit plan while distinguishing the shipped
parser/layout/loader corrections from still-open scheduling and private-title work. -->
The list below preserves the audit's original work plan. Steps 1–3 now have the
implemented corrections and passing host regressions described in the correction
record; active New modes 3–15 are explicitly rejected. Broader scheduling/time/
service work and the private Xenoblade baseline in steps 4–5 remain open.

1. **Parser correction:** apply a reviewed patch in DroidDS's selected runtime
   source, leaving the shared Cargo cache untouched. Decode the independent
   byte/nibble layout; preserve raw values and explicitly handle unsupported
   modes. Add actual-parser fixtures for both CPU-speed bits, L2, modes 0/1/2,
   reserved bits, truncation, and all supported Old modes. Investigate mode 3
   separately: the inspected references differ on its status.
2. **One resolved memory configuration:** resolve model, title memory request,
   physical region layout, application commit limit and guest-reported values
   before creating `System`. Keep New 3DS legacy applications' compatibility
   limits distinct from total physical RAM. Reject unsupported requests clearly;
   do not silently clamp or present a different mode.
3. **Real loader and kernel tests:** use an original executable fixture through
   the complete loader. Assert configuration-page mode/region fields, resource
   limit queries, heap/linear-heap addresses, region non-overlap and allocation
   boundary behavior. Require Base allocations for a service and Old mode 2 to
   succeed where appropriate; validate free/reuse and failure recovery. Include
   both sides of the existing firmware-dependent linear-heap boundary.
4. **Scheduling/time/service tests:** prove forward progress with different
   processor/affinity requests, cross-thread synchronization and AOT/interpreter
   exits. Check model queries and `ir:rst` lifecycle. Preserve stable timeouts,
   audio and vblank under the selected execution-rate policy. Record unsupported
   service calls with bounded summaries, not continuous per-instruction logs.
5. **Private Xenoblade baseline:** once its actual header and owned dump are
   available locally, record the exact request and effective memory/model, then
   attempt the private host boot and fixed checkpoint. A title-specific request
   must come from that input; this audit does not assume Xenoblade uses mode 1
   or mode 2. Keep Dark Moon and Sonic Old-mode regressions alongside it.

None of these findings requires copying Citra/Azahar/Uberhar implementation into
DroidDS. Retain upstream attribution and inspect licenses if that decision
changes. A source patch must be pinned, tested and reported as such before a
future build claims the memory issue is fixed.

## 0.0.5 integration corrections

<!-- CodexAstraUlt: Record implemented changes and actual regressions separately
from the unchanged historical harness and from unperformed retail/device tests. -->

The maintained source is now under `vendor/zakuro`, with the original revision,
file hashes and MIT notice retained. Cargo's shared upstream checkout remains
unchanged. The following corrections ship in 0.0.5:

| Finding | Actual integration change |
| --- | --- |
| N3DS-001 | `ExHeader::parse` reads CPU/L2 from `0x20C` bits 1/0 and New mode from `0x20D` bits 0–3. Old modes retain explicit raw values; unknown modes cannot silently become production mode. |
| N3DS-002/003 | `MemoryLayout::resolve` determines complete physical regions and a separate application commitment limit before `System` construction. Top-down code/heap and bottom-up linear allocations share that cap. |
| N3DS-004 | The resolved raw mode and effective application commitment feed the actual configuration mapper directly, without reading the not-yet-installed title or casting enum ordinals. |
| Redundant initialization | The title loader constructs RAM and its page tables once with the resolved layout, rather than allocating defaults and immediately replacing them. This is not a measured game speedup or leak fix. |
| New-capacity address safety | Private allocations respect the 128 MiB virtual heap, stack and existing mappings. Old-firmware linear allocations stay inside their 128 MiB window even with 178 MiB physical application capacity; newer firmware uses its separate 256 MiB window. |
| Restore compatibility | Allocator geometry/quota and page-map preflight run before saved RAM replaces live RAM. Same-size incompatible states are rejected without changing the tested RAM sentinel, mapping, CPU value or commitment accounting. |

The implementation's supported application configurations are:

| Selected model / request | Config mode | Physical Application / System / Base (MiB) | Application commitment/report (MiB) |
| --- | ---: | --- | ---: |
| Old mode 0 | 0 | 64 / 44 / 20 | 64 |
| Old mode 2 | 2 | 96 / 12 / 20 | 96 |
| Old mode 3 | 3 | 80 / 28 / 20 | 80 |
| Old mode 4 | 4 | 72 / 36 / 20 | 72 |
| Old mode 5 | 5 | 32 / 76 / 20 | 32 |
| New legacy, Old mode 0 | 6 | 124 / 100 / 32 | 64 |
| New legacy, Old mode 2 | 6 | 124 / 100 / 32 | 96 |
| New legacy, Old mode 3 | 6 | 124 / 100 / 32 | 80 |
| New mode 1 | 6 | 124 / 100 / 32 | 124 |
| New mode 2 | 7 | 178 / 46 / 32 | 178 |

The legacy distinction is deliberate. Independent read-only corroboration comes
from [Luma3DS PM launch code](https://github.com/LumaTeam/Luma3DS/blob/e2778a45/sysmodules/pm/source/launch.c#L230)
and its [resource-limit setter](https://github.com/LumaTeam/Luma3DS/blob/e2778a45/sysmodules/pm/source/reslimit.c#L293).
The setter explicitly places the same limit in the high 32 bits for the kernel's
`APPMEMALLOC` field. Consequently, a New legacy configuration page's reported
application/system/base values do not sum to all 256 MiB of physical FCRAM.
This is implementation-reference corroboration, not a new hardware measurement;
no Luma/Citra implementation was copied into the Rust changes.

New legacy requests for Old modes 4/5 are explicitly unsupported: the inspected
PM reference assigns them zero application commitment, so the implementation does not
invent a working 72/32 MiB legacy mode. Unknown Old modes and active New modes
3–15 also fail clearly before allocation. Old hardware can still run the Old
request of an enhanced, non-exclusive title; a New-only NCCH selects the New
model. CPU speed/L2 parsing does not multiply the global tick clock or establish
expanded scheduling behavior.

### Executed regression boundary

<!-- CodexAstraUlt: Name the actual production-path tests and independent input
contracts so a parser-only check cannot be mistaken for loader qualification. -->

[`droidds_memory_layout.rs`](../vendor/zakuro/crates/zakuro-core/tests/droidds_memory_layout.rs)
constructs original NCCH bytes with independent expected values and executes the
actual loader and guest interpreter. Its host regressions check all supported
configurations, guest exit, raw config values and selected model, resource-limit SVCs,
heap/linear placement on both sides of the firmware boundary, and real HID
service allocation from Base. Allocation exhaustion, recovery, reuse, invalid
modes, overflow/overlap, linear-alias rejection and incompatible saved-state
nonmutation are exercised. The parser separately tests CPU/L2 combinations,
reserved bits, Old raw modes and truncation. These host regressions pass.

Reproduce with the root locked workspace:

```bash
cargo test --locked -p zakuro-fs -p zakuro-core --lib -- --test-threads=1
cargo test --locked -p zakuro-core --test droidds_memory_layout -- --test-threads=1
```

The integrated runtime report also executes original New/Old NCCH variants and
checks actual memory boundaries and guest completion. The owner's 0.0.5 Android
report passes all five cases, including the New 3DS legacy distinction between
124 MiB physical application memory and a 64 MiB commitment limit. Boundary
rejection, free/recovery, Base allocation and guest exit pass. These tests establish
the corrected bounded contracts,
not broad state-file hardening, long-run fragmentation/leak freedom, full
multi-core scheduling, CRO lifecycle or Xenoblade boot. No private retail inputs
are available in this environment; all primary-title baselines remain open.
<!-- CodexAstraUlt: Carry the proven memory subset into interactive work without
using one original HID/DSP guest to close scheduler or retail compatibility. -->
The next step is 0.0.6 visible original guest and lifecycle qualification, with
all existing layout regressions retained. Its HID and DSP HLE interactions and
audio-rate conversion are bounded fixture work, not proof of New 3DS timing,
DSP firmware compatibility or Xenoblade audio. Automatic output must be followed
by the Thor manual screen/input/audio/lifecycle gate before 0.0.7 promotion.
