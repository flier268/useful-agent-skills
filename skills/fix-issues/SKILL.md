---
name: fix-issues
description: Diagnose reported bugs or failures, reproduce or trace the root cause, fix it with focused regression coverage, and verify related paths. Use when the agent is asked to fix broken behavior, investigate failures, or guard against recurring issues.
---

# Fix Issues

Treat bugs as root-cause work, not symptom cleanup.

## Workflow

1. Reproduce the failure or inspect enough evidence to identify the actual cause.
2. If the user gives explicit reproduction steps, work in TDD mode: add a failing test that captures those steps before changing production code, then make it pass.
3. Search nearby and duplicated code for the same defect pattern.
4. Apply the smallest correct fix that removes the cause.
5. Add or update regression coverage for fragile, shared, security-sensitive, validation, or data-shaping behavior.
6. Run targeted verification and note any uncertainty that remains.

## Working Rules

- Do not stop at a surface-level patch if the underlying cause is still present.
- Prefer fixes that reduce recurrence without broad refactors.
- If a useful automated test is skipped, explain why and state the manual or targeted check used instead.

## Output

Summarize root cause, fix, similar-instance review, and verification.
