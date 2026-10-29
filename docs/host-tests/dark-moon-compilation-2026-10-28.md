# Dark Moon host native compilation

<!-- CodexAstraUlt: Preserve the owner's partial compilation evidence separately
from cloud fixture validation and unperformed linking/native/device execution. -->
Reported by the owner on 2026-10-28 (America/New_York), from source `8e06139`.
The local summary is `dark-moon-compilation-summary.md` in compilation run-001.
The private report, generated sources, receipts and objects are not available
in this cloud checkout; the following is the owner's textual result.

- All **61 original-fixture checks** reportedly passed.
- One compilation batch reached its default **1800-second batch deadline**.
- **133 of 521 objects were validated; 388 remain.**
- No earlier compiler failure was reported. No linked library exists yet.
- Completed receipts and all previous outputs were preserved. No resume or
  limit increase occurred.

The 521-object total matches the reported 520 generated C files plus the
compiler's original identity-binding unit. The two generated headers are inputs
to compilation, not separate object jobs. About 25.5% of the object count is
complete; that fraction is not a time-to-completion estimate. Jobs run largest
source first, and compile cost varies with source structure and host load.

## Bounded continuation

<!-- CodexAstraUlt: Replace a manual report after every healthy deadline with a
finite sequence of verified resumes, preserving every per-batch resource cap. -->
Continue the existing output with `--resume`, the original successful preparation,
the same compiler selection and the same compilation tools. The six Python files
bound into the compilation contract are unchanged between `8e06139` and
`17f3cba`; the latter's encryption-admission fix does not change this compilation
recipe. A checkout update or preparation-worker rebuild is unnecessary for resume.

The next local task permits **up to three additional default 30-minute batches**,
serially, against the same compilation output. This allocates up to 90 additional
minutes of batch budgets; bounded verification/reporting can extend wall elapsed
time beyond those deadlines. It does not increase per-command CPU, wall, memory,
file-size or retained-directory allowances, change optimization, or add parallel
compiler jobs. Preserve previous attempts, incomplete files and receipts.

After each invocation, inspect its own new attempt report. Continue only when it
reports `status=incomplete`, `reason=batch_budget`, and strictly more validated
objects than at the start of that invocation, with the same preparation/contract
identity. All retained receipts must pass the coordinator's built-in verification;
file counts alone cannot authorize reuse. Stop on success, any other failure or
rejection, lost/changed identity, zero progress, interruption, or the third batch.
An interrupted unreceipted object may be recompiled after a healthy batch deadline;
an actual compiler failure must not be automatically retried.

No new C generation or unchanged fixture-test replay is needed. Run the existing
link/static audit when all objects become available. Do not load the library or
execute private native code; runtime binding and code freshness remain separate
gates. Return one consolidated summary in a new path while preserving run-001's
summary, listing each attempt's status/reason, reused/new/ready/remaining objects,
elapsed time and limits. Include the library identity and static audit if complete,
or the precise first blocker if stopped.

See [the compilation procedure](../PRIVATE_TITLE_COMPILATION.md) for the exact
resume command and artifact contract.
