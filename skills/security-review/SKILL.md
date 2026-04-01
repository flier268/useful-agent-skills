---
name: security-review
description: Review code, diffs, or features for security risks and maintain structured security review documents. Use when Codex is asked to do a security review, continue an existing finding, update `docs/security-review.md`, or write detailed findings under `docs/security-review/` without expanding every security document by default.
---

# Security Review

Perform a focused security review while keeping the security documentation structured and non-duplicative.

## Documentation Contract

Use one index file plus focused detail files.

- Use `docs/security-review.md` as the canonical review index.
- Use `docs/security-review/` as the detail directory.
- Keep the index short enough that a reviewer can reload context quickly and continue a previous pass without opening every detail file.
- For an exact markdown template, read `references/security-review-format.md`.

## Index Structure

Keep the index limited to these sections, in this order:

1. Title and metadata
   - Review title
   - `Last updated`
   - `Reviewer`
   - Optional `Review target`
2. Review scope
   - What code, feature, diff, or subsystem is in scope
   - Link to accepted-risk or exception documents if they exist
   - Short status legend for labels such as `safe-reviewed`, `unsafe-followup`, and `partial-reviewed`
3. Resume here
   - `Current focus`
   - `Next file to open`
   - `Last meaningful change`
3. Progress
   - 3-8 short bullets covering the current overall state, newly closed findings, and any active open risk
4. Summary table
   - Columns: `Area`, `Status`, `Notes`
   - One row per reviewed surface or control family
   - `Notes` must stay compact and point to the core conclusion only
5. Detailed index
   - Link to each detail file under `docs/security-review/`
   - Give each file a narrow purpose

## Detail File Split

Split detail files by review outcome or review function, not by long chronological notes.

- `safe-reviewed-controls.md`: controls that were checked and found acceptable
- `unsafe-followup-findings.md`: concrete weaknesses that still need remediation
- `remediated-findings.md`: findings that were fixed during the review or already resolved
- `partial-reviewed-notes.md`: areas inspected but not yet reviewed deeply enough
- `similar-pattern-scan.md`: related code paths checked because a finding suggested a repeated pattern
- `verification-notes.md`: tests, repro steps, verification evidence, and what remains unverified
- `next-pass.md`: the queued follow-up items for the next review pass

If a repo needs additional files, add them only when they represent a distinct retrieval purpose. Do not create one file per day or one file per thought stream.

Prefer this directory layout:

```text
docs/
  security-review.md
  security-review/
    unsafe-followup-findings.md
    remediated-findings.md
    partial-reviewed-notes.md
    safe-reviewed-controls.md
    similar-pattern-scan.md
    verification-notes.md
    next-pass.md
```

## What Each Detail File Should Contain

- `safe-reviewed-controls.md`
  - One compact entry per control or surface
  - Why it is considered safe enough for the current pass
  - Key file references only
- `unsafe-followup-findings.md`
  - One entry per open finding
  - Include severity, impact, exploit path, affected surface, and required remediation direction
- `remediated-findings.md`
  - Original issue summary
  - What changed
  - What evidence shows it is now remediated
- `partial-reviewed-notes.md`
  - What was checked
  - Why the review is incomplete
  - What must be checked next
- `similar-pattern-scan.md`
  - The triggering pattern
  - Which similar locations were reviewed
  - Whether the same issue was found elsewhere
- `verification-notes.md`
  - Commands, tests, manual checks, and limits of verification
- `next-pass.md`
  - A short queue of the next review targets with why they matter

## Workflow

1. Read only the index file first: `docs/security-review.md`.
2. Use the progress bullets, summary table, and detailed index to decide whether more context is needed.
3. Do not expand all files under `docs/security-review/` by default.
4. Read a detail file under `docs/security-review/` only when one of these is true:
   - Continue the same finding.
   - Update the same section.
   - Resolve an apparent conflict or inconsistency.
   - Validate the evidence behind a summary-table conclusion.
   - Resume a previous review pass that explicitly points to that file.
5. Review the code, diff, or feature and identify concrete security findings, risks, missing protections, or verification gaps.
6. When updating docs, keep the index limited to summary, status, compact table notes, and links.
7. Write detailed analysis only in the matching detail file.

## Continuation Rules

When resuming an earlier review, load context in this order:

1. Index file
2. The specific detail file linked from the relevant row or progress bullet
3. Verification notes only if the current question depends on test evidence
4. Similar-pattern scan only if the same bug class may recur

Do not reread unrelated detail files just because they exist.

## Writing Rules

- Keep the index readable in one pass.
- Keep each table note to the conclusion, not the full reasoning.
- Put long reasoning, evidence, and chronology in detail files.
- Update existing entries when continuing the same finding instead of creating duplicates.
- Prefer stable section names so later reviewers can jump directly to the right file.

## Review Standard

- Prefer concrete findings over broad advice.
- Call out impact, exploit path, affected surface, and missing validation or authorization checks.
- Check for similar issues in related code when a pattern is found.
- Avoid repeating long detail text in both the index and the detail file.

## Output

Report findings first, ordered by severity, with file references when available.
If no findings are discovered, state that explicitly and mention residual risk or testing gaps.
