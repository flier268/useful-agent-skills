# Cache Layout

The review session cache lives in a random folder under the temp directory chosen by the skill helper script, with a name like `agent-review-with-session-abc123`.

Run the helper script from its skill path, not from the reviewed repository:

```sh
python3 <this-skill-dir>/scripts/review_session.py <command>
```

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

1. Run `python3 <this-skill-dir>/scripts/review_session.py resolve <session>`.
2. Run `python3 <this-skill-dir>/scripts/review_session.py summary <session>`.
3. Run `python3 <this-skill-dir>/scripts/review_session.py next <session>`.
4. Run `python3 <this-skill-dir>/scripts/review_session.py show <session> checked-paths` only when you need to avoid re-reviewing the same area.
5. Run `python3 <this-skill-dir>/scripts/review_session.py show <session> findings-open` when continuing an existing issue.
6. Run `python3 <this-skill-dir>/scripts/review_session.py status <session>` if the worktree may have changed since the cache was created.

Do not load every cache file by default.

## Security Review Note

For security review, keep using this cache.
Use the same file names as normal review.
Keep `index.md` as the short pointer to the current scope, focus, and next file.
The chosen scope still applies.
`staged` review still reads staged changes only.
`branch` review still reads the branch diff only.
`whole project` review still reads the requested project area.
