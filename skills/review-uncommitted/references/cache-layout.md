# Cache Layout

The review session cache lives in a random folder under the temp directory chosen by `scripts/review_session.py`, with a name like `codex-review-uncommitted-abc123`.

## Files

- `index.md`: minimal resume file; read this first on every continuation
- `findings-open.md`: active findings still under review
- `findings-closed.md`: findings closed as fixed, disproven, or accepted
- `checked-paths.md`: files, symbols, or areas already reviewed with concise conclusions
- `next-steps.md`: queued follow-up targets for the next pass
- `worktree-status.txt`: raw `git status --short` snapshot from session creation
- `worktree-files.json`: staged, unstaged, and untracked file lists from session creation
- `session.json`: metadata for resolving the session and checking drift

## Minimal Reading Order

1. Read `index.md`.
2. Open the one file named in `Next file to open`.
3. Read `checked-paths.md` only when you need to avoid re-reviewing the same area.
4. Read `findings-open.md` when continuing an existing issue.
5. Run `scripts/review_session.py status <session>` if the worktree may have changed since the cache was created.

Do not load every cache file by default.
