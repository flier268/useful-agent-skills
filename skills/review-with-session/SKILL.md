---
name: review-with-session
description: Perform read-only, defect-first code review with a durable resumable session. Use for uncommitted, staged, branch, commit, whole-project, or security review when the agent must cover the complete scope, record every actionable finding, and resume without repeating checked work.
---

# Review With Session

Review the requested target without modifying it.
Write only to the session state.
Do not edit reviewed files, commit, push, post comments, or delegate the review.

Read the applicable `AGENTS.md` before inspecting code.
Read [references/session-cli.md](references/session-cli.md) when creating, resuming, or updating a session.
Read [references/security-review-format.md](references/security-review-format.md) for security audits.

## Choose The Mode

Use `change` mode for `uncommitted`, `staged`, `branch`, and `commit`.
Use `audit` mode for `project`.
Add `--security` only to an audit session.

When no scope is named, use `change:uncommitted`.

- `uncommitted`: inspect staged, unstaged, and untracked changes.
- `staged`: inspect only the index diff and staged new files.
- `branch`: inspect merge base through `HEAD`; exclude uncommitted changes.
- `commit`: inspect exactly the named commit.
- `project`: inspect the requested paths, or the whole repository when no path is named.

For branch scope, honor an explicit base.
Otherwise use a suitable upstream that is ahead of `HEAD`.
Otherwise use local `main`, then local `master`.
Ask for a base only when none can be resolved.

## Start Or Resume

Initialize through the helper.
The helper reuses an active session only when its structured scope and fingerprint match.
Use `--fresh` only when the user requests a separate pass.

On resume:

1. Run `resolve`.
2. Run `summary`.
3. Run `status`.
4. Stop trusting affected checked paths when status reports drift.
5. Run `next`.
6. Read only the session details needed for the next target.

Create a new session when repo, mode, kind, comparison target, commit, path scope, or security mode differs.
Do not retarget a structured session by editing its display label.

## Review Contract

Inspect the complete target and enough surrounding code to understand every changed or audited path.
Continue after finding the first issue.
Check relevant tests and call sites before recording a finding.

Record a finding only when all conditions apply:

- The issue meaningfully affects correctness, security, performance, or maintainability.
- The issue is discrete and actionable.
- The affected scenario or call path is demonstrated by the code.
- The author would probably fix it after learning about it.
- A change finding was introduced or materially worsened by the reviewed change.
- An audit finding exists in reachable code inside the requested project scope.

Do not report speculation, intentional behavior changes, unrelated pre-existing problems in change mode, or style preferences.
Report cleanup only when it prevents a concrete issue or removes materially harmful dead behavior.
Report missing tests only when they leave a demonstrated behavior or regression unprotected.

For change mode, cite the smallest useful line range that overlaps the reviewed change.
For audit mode, cite the smallest useful line range containing the defect.

## Record Progress

Use structured `add-finding` arguments for every new finding.
Use one stable finding ID per issue.
Update an existing issue instead of creating a duplicate.
Use `add-checked` after completing a path, symbol, or call chain.
Use `add-next` for the highest-value unfinished target.
Checkpoint after a meaningful review area and before pausing.
Let the helper update counts and metadata.

When drift appears, revalidate findings and checked paths that overlap changed files.
Run `refresh-snapshot` only after recording the drift decision.
The helper preserves the previous snapshot and marks affected paths for revalidation.

## Finding Format

Use priorities consistently:

- `P0`: universal release blocker or critical failure.
- `P1`: urgent defect that should be fixed next.
- `P2`: ordinary defect that should be fixed.
- `P3`: low-impact issue that is still worth fixing.

Use an imperative title.
Explain the triggering scenario, wrong behavior, impact, and confirming evidence in one short paragraph.
Add trust-boundary and remediation fields only when useful for a security finding.

## Output

Present all open findings first in priority order.
Do not cap or sample findings.
Say `No findings.` when no issue qualifies.
Then give a brief overall assessment.
Mention material test gaps and residual risks.
State whether the selected scope was fully reviewed.
Name every remaining area when coverage is incomplete.
End with the session name for the next pass.
