---
name: fix-issues
description: Investigate reported bugs or failures by tracing root causes, searching for similar issues, proposing the fix, implementing it, and checking for regressions. Use when the agent is asked to diagnose problems, fix broken behavior, or ensure a patch does not introduce new issues.
---

# Fix Issues

Treat reported problems as debugging and remediation work, not as isolated symptoms.

## Workflow

1. Reproduce or inspect the failure carefully enough to identify the actual root cause.
2. Search for similar code paths, duplicated logic, or adjacent cases that may share the same defect.
3. Propose the smallest correct fix that addresses the cause rather than masking the symptom.
4. Implement the fix.
5. Add or update tests when the affected area is prone to regression, the bug is likely to recur, or the fix changes business-critical behavior, authorization, validation, data shaping, or shared logic.
6. Check for regressions with targeted tests, existing test suites, or other focused verification.
7. Call out remaining uncertainty when verification is incomplete.

## Working Rules

- Do not stop at a surface-level patch if the underlying cause is still present.
- When one issue reveals a reusable bad pattern, inspect related locations and fix or report them together.
- Prefer changes that reduce future recurrence, such as consolidating logic or tightening validation.
- Default to adding regression coverage for fragile paths, shared helpers, permission checks, validation paths, data transformations, and bug classes that have already repeated once.
- If a useful automated test is not added, explain why it was skipped and what verification was used instead.
- Ensure the final explanation covers root cause, fix, similar-instance review, and verification.

## Output

Summarize the root cause first, then the fix, then what was checked for similar issues and regressions.
