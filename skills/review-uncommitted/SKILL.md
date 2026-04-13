---
name: review-uncommitted
description: Review staged, unstaged, and untracked repository changes without restarting from zero each time. Use when the agent is asked to review uncommitted work, continue a previous review pass, or track multiple pending findings across several fix-and-review cycles by storing a resumable cache session under the temp directory returned by the session script.
---

# Review Uncommitted

Review uncommitted changes with a resumable cache session so later passes can continue from prior findings instead of rereading the whole worktree.

## Session Workflow

1. If the user does not provide a session name, create one with:
   `python3 scripts/review_session.py init --repo <repo-path>`
2. Tell the user the returned `SESSION_NAME` and `SESSION_PATH`.
3. Treat the session folder as the review cache for later passes.
4. If the user provides an existing session name, resolve it with:
   `python3 scripts/review_session.py resolve <session-name>`
5. Before resuming an older session, check for worktree drift with:
   `python3 scripts/review_session.py status <session-name>`

## Reading Order

Read the minimum possible cache content.

1. Read `<session>/index.md` first.
2. Open only the file named in `Next file to open`.
3. Read `<session>/checked-paths.md` only when you need to avoid re-reviewing the same path or symbol.
4. Read `<session>/findings-open.md` only when continuing an existing issue.
5. Read the current git diff or specific source files only for the area being reviewed now.

For the cache file layout, read `references/cache-layout.md`.

## Review Rules

- Review both staged and unstaged tracked changes plus untracked files unless the user narrows the scope.
- Record what was checked in `checked-paths.md` with short conclusions.
- Keep `index.md` short and current so it can bootstrap the next pass quickly.
- Put active findings in `findings-open.md`.
- Move closed or disproven findings to `findings-closed.md`.
- Keep `next-steps.md` focused on the highest-value unresolved review targets.
- When a finding points to repeated bad patterns, note the related locations in `checked-paths.md` or `findings-open.md` instead of rediscovering them later.

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
- If the worktree changed significantly, update the cache files instead of creating duplicate sessions unless the user explicitly wants a fresh review.
- If a new, unrelated feature branch or worktree appears, start a new session.
- If the cache no longer matches the repo state closely enough to be trustworthy, tell the user and start a new session.

## Output

After each review pass:

- report findings first
- report residual risk or unverified areas
- give the session name back to the user for the next pass
