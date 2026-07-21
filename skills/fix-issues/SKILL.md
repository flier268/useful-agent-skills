---
name: fix-issues
description: Diagnose and repair broken software behavior by tracing the causal chain, restoring the violated contract or invariant, checking related paths, adding regression coverage, and verifying the result. Use for bug fixes, regressions, incorrect edge cases, and failures that may otherwise invite a local workaround.
---

# Fix Issues

Restore correct behavior at the level that owns it.

## Workflow

1. Define the observed failure, expected behavior, user impact, and violated contract or invariant.
2. Reproduce the failure or gather enough evidence to explain it.
3. Trace the causal chain from trigger to failure. Distinguish the trigger, failure mechanism, actionable root cause, and contributing design gaps.
4. Locate the component that owns the broken invariant. Inspect callers, boundaries, shared abstractions, and duplicated implementations for the same defect pattern.
5. Choose the smallest complete repair that restores the invariant across affected paths. Change the source of truth or owning abstraction when a local patch would preserve the underlying defect.
6. For a reproducible defect, add a failing regression test before changing production code when practical. Cover the invariant and important neighboring cases rather than only the reported input.
7. Implement the repair. Refactor only the structure required to make the correction coherent and durable.
8. Verify the original failure, related paths, and relevant test suites. Record remaining uncertainty or risk.

## Working Rules

- Do not equate fewer changed lines with a better fix.
- Do not hide a defect with a guard, fallback, retry, default value, or swallowed error unless the underlying cause is outside the repair boundary. Document that boundary when this exception applies.
- Do not expand into unrelated cleanup. Broaden the change only when the violated invariant spans multiple components.
- If an automated regression test is impractical, explain why and state the substitute verification.

## Output

Report the causal chain, repair boundary, restored behavior, related-instance review, verification, and remaining risk.
