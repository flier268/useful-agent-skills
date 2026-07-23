# Session CLI

Run:

```sh
python3 <skill-dir>/scripts/review_session.py <command>
```

## Initialize

```sh
review_session.py init --repo PATH --mode change --kind uncommitted
review_session.py init --repo PATH --mode change --kind staged
review_session.py init --repo PATH --mode change --kind branch [--base REF]
review_session.py init --repo PATH --mode change --kind commit --commit SHA
review_session.py init --repo PATH --mode audit --kind project [--path PATH ...] [--security]
```

Use `--scope TEXT` as a human-readable label.
Use `--fresh` to bypass exact-session reuse.

Legacy `init --repo PATH --scope TEXT` remains valid.
It creates an uncommitted change session.

## Resume

```sh
review_session.py list [--repo PATH] [--status active] [--mode MODE] [--kind KIND]
review_session.py resolve SESSION
review_session.py summary SESSION
review_session.py status SESSION
review_session.py next SESSION
review_session.py show SESSION FILE_KEY
```

Readable keys are `index`, `findings-open`, `findings-closed`, `checked-paths`,
`next-steps`, `worktree-status`, `worktree-files`, and `session`.

`status` returns `exact`, `drift`, or `legacy-unknown`.
It reports content, stage, executable-mode, added, and removed path drift separately.

## Record

```sh
review_session.py add-finding SESSION \
  --priority P2 \
  --title "Imperative title" \
  --path path/to/file.py \
  --line 42 \
  --body "Trigger, wrong behavior, and impact." \
  [--evidence TEXT] \
  [--trust-boundary TEXT] \
  [--remediation TEXT]

review_session.py close-finding SESSION --id F-001 \
  [--resolution TEXT] [--verification TEXT]

review_session.py add-checked SESSION --path PATH --conclusion TEXT
review_session.py add-next SESSION --step TEXT
review_session.py complete-next SESSION
review_session.py clear-next SESSION
review_session.py refresh-snapshot SESSION
```

Repeat `add-finding` with `--id F-001` to replace an open finding after revalidation.
`add-finding --title --body` remains available for legacy callers.
`close-finding --title` remains available for legacy callers.

General compatibility commands remain available:
`update-index`, `append`, `replace`, `clear-open-findings`, and `sync-index`.
Use them only when a structured command cannot express the update.
