---
name: review-uncommitted
description: Review staged, unstaged, and untracked repository changes with a resumable cache session. Use when the user asks to review uncommitted work, continue a prior review pass, or track findings across fix-and-review cycles.
---

# Review Uncommitted

Review uncommitted changes without restarting from zero.

## Script Path

Resolve helper scripts relative to this skill directory, not the repository being reviewed.

- Current script: `/home/kumei/.codex/skills/review-uncommitted/scripts/review_session.py`
- Portable form: `<this-skill-dir>/scripts/review_session.py`

## Session Workflow

1. If the user does not provide a session name, create one with:
   `python3 /home/kumei/.codex/skills/review-uncommitted/scripts/review_session.py init --repo <repo-path>`
2. Tell the user the returned `SESSION_NAME` and `SESSION_PATH`.
3. If the user provides an existing session name, resolve it with:
   `python3 /home/kumei/.codex/skills/review-uncommitted/scripts/review_session.py resolve <session-name>`
4. Before resuming an older session, check for worktree drift with:
   `python3 /home/kumei/.codex/skills/review-uncommitted/scripts/review_session.py status <session-name>`

## Reading Order

1. Read `<session>/index.md` first.
2. Open only the file named in `Next file to open`.
3. Read `<session>/checked-paths.md` only when you need to avoid re-reviewing the same path or symbol.
4. Read `<session>/findings-open.md` only when continuing an existing issue.
5. Read the current git diff or specific source files only for the area being reviewed now.

For the cache file layout, read `references/cache-layout.md`.

## Review Rules

- Review both staged and unstaged tracked changes plus untracked files unless the user narrows the scope.
- Record checked areas and short conclusions in `checked-paths.md`.
- Keep `index.md` short and current.
- Put active findings in `findings-open.md`; move resolved or disproven findings to `findings-closed.md`.
- Keep `next-steps.md` focused on the highest-value remaining targets.

## Index Requirements

Keep `<session>/index.md` limited to:

- current focus
- next file to open
- last meaningful change
- current worktree snapshot counts
- short review summary

Do not turn `index.md` into a full log.

## Continuation Rules

- Reuse the existing session whenever the user wants another review pass on the same ongoing work.
- If the worktree changed, update the cache instead of creating a duplicate session unless a fresh review is needed.
- If the repo, branch, or task is unrelated to the session, start a new session.
- If the cache no longer matches the repo state closely enough to be trustworthy, tell the user and start a new session.

## Output

Report findings first, then residual risk or unverified areas, then the session name for the next pass.
