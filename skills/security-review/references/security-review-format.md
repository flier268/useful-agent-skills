# Security Review Document Format

Use this format when creating or restructuring security review docs so a later reviewer can resume with minimal context.

## Preferred Layout

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

## Index Template

```md
# Security Review

Last updated: YYYY-MM-DD
Reviewer: <name>
Review target: <repo / feature / diff / subsystem>

## Review Scope

- In scope: <areas under review>
- Out of scope: <optional>
- Accepted risk / exceptions: <links if any>

Status legend:

- `safe-reviewed`: control exists and was spot-checked in code/tests during this review
- `unsafe-followup`: concrete weakness found and still needs remediation
- `partial-reviewed`: area was inspected but needs deeper review

## Resume Here

- Current focus: <single sentence>
- Next file to open: `<one detail file path>`
- Last meaningful change: <single sentence>

## Progress

- <short bullet>
- <short bullet>
- <short bullet>

## Summary Table

| Area | Status | Notes |
| --- | --- | --- |
| Auth CSRF enforcement | `safe-reviewed` | Checked middleware and resolver boundary; no bypass found in current pass |
| File upload validation | `unsafe-followup` | Missing server-side MIME/content validation on import path |
| Customer callback redirects | `partial-reviewed` | Basic path constraints checked; state-binding review still pending |

## Detailed Index

- [Safe-reviewed controls](./security-review/safe-reviewed-controls.md)
- [Unsafe follow-up findings](./security-review/unsafe-followup-findings.md)
- [Remediated findings](./security-review/remediated-findings.md)
- [Partial-reviewed notes](./security-review/partial-reviewed-notes.md)
- [Similar-pattern scan](./security-review/similar-pattern-scan.md)
- [Verification notes](./security-review/verification-notes.md)
- [Next-pass focus](./security-review/next-pass.md)
```

## Detail File Rules

- Keep the index to conclusions, routing, and current state.
- Put long reasoning, evidence, repro steps, and chronology in detail files.
- Update an existing entry when continuing the same finding instead of creating duplicates.
- Split by retrieval purpose, not by date.

## Detail File Templates

### `unsafe-followup-findings.md`

```md
# Unsafe Follow-up Findings

## <Finding title>

- Status: `unsafe-followup`
- Severity: <critical/high/medium/low>
- Area: <surface>
- Source: <review pass / diff / file>

### Why this matters

<impact and exploit path>

### Evidence

- <file reference>
- <file reference>

### Remediation direction

- <required fix direction>

### Related checks

- <similar path reviewed or still pending>
```

### `remediated-findings.md`

```md
# Remediated Findings

## <Finding title>

- Previous status: `unsafe-followup`
- Current status: `remediated`

### Original issue

<short summary>

### What changed

<short summary of fix>

### Verification

- <test or evidence>
```

### `partial-reviewed-notes.md`

```md
# Partial-reviewed Notes

## <Area title>

### Checked so far

- <checked item>

### Why incomplete

- <remaining gap>

### Next step

- <next concrete review action>
```

### `safe-reviewed-controls.md`

```md
# Safe-reviewed Controls

## <Control or surface>

- Status: `safe-reviewed`
- Reason: <why acceptable in current pass>
- Evidence: <short file/test references>
- Residual risk: <optional short note>
```

### `similar-pattern-scan.md`

```md
# Similar-pattern Scan

## <Pattern name>

- Triggered by: <finding or suspicion>
- Locations checked: <list>
- Result: <same issue found / not found / partially checked>
```

### `verification-notes.md`

```md
# Verification Notes

## <Topic>

- Command or method: <how verified>
- Result: <what passed or failed>
- Limitation: <what was not verified>
```

### `next-pass.md`

```md
# Next-pass Focus

- <next review target and why>
- <next review target and why>
```

## Minimal Reading Order

Use this order when resuming:

1. `docs/security-review.md`
2. The one detail file named in `Resume Here`
3. `verification-notes.md` only if test evidence matters to the current question
4. `similar-pattern-scan.md` only if the issue may recur elsewhere

Do not open every detail file just because it exists.
