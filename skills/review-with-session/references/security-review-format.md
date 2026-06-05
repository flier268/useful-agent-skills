# Security Review Document Format

Use this format when creating or restructuring security review docs so a later reviewer can resume with minimal context.

## Preferred Layout

```text
<session>/
  index.md
  findings-open.md
  findings-closed.md
  checked-paths.md
  next-steps.md
```

## File Use

- `index.md`: review scope, current focus, next file, last meaningful change, current counts, short summary.
- `findings-open.md`: active security findings. Keep one section per finding.
- `findings-closed.md`: fixed, disproven, or accepted findings.
- `checked-paths.md`: checked paths, safe controls, repeated-pattern scans, and short verification notes.
- `next-steps.md`: unfinished security areas and next checks.

## Scope Binding

Security review keeps the chosen base scope.

- On uncommitted review, inspect staged, unstaged, and untracked changes.
- On staged review, inspect staged changes only.
- On branch review, inspect the branch diff only.
- On whole project review, inspect the requested project area in the current repository.

Record that base scope in `index.md`.
Keep the next file and current focus in that same file.

## Finding Format

```md
## <Finding title>

- Status: `unsafe-followup` or `partial-reviewed`
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

Move closed items to `findings-closed.md`.

## Checked Path Format

```md
- Path or control: <file / symbol / boundary>
- Status: `safe-reviewed` or `partial-reviewed`
- Scope: <uncommitted / staged / branch / whole project>
- <checked item>
- Evidence: <short file/test references>
- Residual risk: <optional short note>
```

Put repeated-pattern checks and command results here when they are short.
Put the next unfinished security checks in `next-steps.md`.

## Minimal Reading Order

Use this order when resuming:

1. Run `resolve`.
2. Read the short state through `summary`.
3. Read the next target through `next`.
4. Read the diff or source files for the chosen scope.
5. Read `checked-paths.md` through `show` only if the issue may recur elsewhere.

Do not open every detail file just because it exists.
