---
name: security-review
description: Review code, diffs, or features for concrete security risks and maintain concise security review docs. Use when the user asks for a security review, continuation of a finding, or updates to `docs/security-review.md` and `docs/security-review/`.
---

# Security Review

Perform focused security review and keep docs easy to resume.

## Documentation Contract

- Use `docs/security-review.md` as the canonical review index.
- Use `docs/security-review/` for detailed findings, evidence, and follow-ups.
- Keep the index short enough to resume without opening every detail file.
- For an exact markdown template, read `references/security-review-format.md`.

## Index Structure

Keep the index to these sections:

1. Title and metadata: review title, `Last updated`, `Reviewer`, optional `Review target`
2. Review scope
3. Resume here
4. Progress: 3-8 short bullets
5. Summary table: `Area`, `Status`, `Notes`
6. Detailed index: links to focused detail files

## Detail File Split

- `safe-reviewed-controls.md`: controls that were checked and found acceptable
- `unsafe-followup-findings.md`: concrete weaknesses that still need remediation
- `remediated-findings.md`: findings that were fixed during the review or already resolved
- `partial-reviewed-notes.md`: areas inspected but not yet reviewed deeply enough
- `similar-pattern-scan.md`: related code paths checked because a finding suggested a repeated pattern
- `verification-notes.md`: tests, repro steps, verification evidence, and what remains unverified
- `next-pass.md`: the queued follow-up items for the next review pass

Add another detail file only when it has a distinct retrieval purpose. Do not create one file per day or thought stream.

## Workflow

1. Read only the index file first: `docs/security-review.md`.
2. Use the progress bullets, summary table, and detailed index to decide whether more context is needed.
3. Read a detail file only when continuing or verifying that specific area.
4. Review the code, diff, or feature for concrete risks, missing protections, and verification gaps.
5. Keep long reasoning and evidence in the matching detail file, not the index.

## Continuation Rules

When resuming, load context in this order:

1. Index file
2. The specific detail file linked from the relevant row or progress bullet
3. Verification notes only if the current question depends on test evidence
4. Similar-pattern scan only if the same bug class may recur

## Writing Rules

- Keep the index readable in one pass.
- Keep table notes to conclusions, not full reasoning.
- Update existing entries when continuing the same finding instead of creating duplicates.
- Prefer stable section names so later reviewers can jump directly to the right file.

## Review Standard

- Prefer concrete findings over broad advice.
- Call out impact, exploit path, affected surface, and missing validation or authorization checks.
- Check for similar issues in related code when a pattern is found.

## Output

Report findings first, ordered by severity, with file references when available.
If no findings are discovered, state that explicitly and mention residual risk or testing gaps.
