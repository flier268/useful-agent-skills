# Session Storage

Session state is stored outside the reviewed repository.

- Linux: `$XDG_STATE_HOME/review-with-session`
- Linux fallback: `~/.local/state/review-with-session`
- macOS: `~/Library/Application Support/review-with-session`
- Windows: `%LOCALAPPDATA%\review-with-session`
- Override: `REVIEW_WITH_SESSION_ROOT`

The helper also searches the system temporary directory for legacy sessions.
Unix session directories use mode `0700`.
An existing custom root must already be private to the current user.
The helper never changes permissions on an existing root.
The session root cannot be inside the reviewed repository.

## Files

- `session.json`: structured scope, target refs, fingerprint, and current snapshot.
- `index.md`: short human-readable resume summary.
- `findings-open.md`: active findings.
- `findings-closed.md`: resolved, disproven, or accepted findings.
- `checked-paths.md`: completed areas and their snapshot fingerprints.
- `next-steps.md`: ordered unfinished targets.
- `worktree-status.txt`: current Git status snapshot.
- `worktree-files.json`: current changed-file and fingerprint details.
- `snapshot-history/`: snapshots preserved by `refresh-snapshot`.

Schema version 2 sessions have a structured review target.
Sessions without `schema_version` are legacy sessions.
Legacy sessions remain readable.
Their drift result is `legacy-unknown`.

Do not edit session files directly.
Use the helper so updates remain atomic and counts stay synchronized.
