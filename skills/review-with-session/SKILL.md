---
name: review-with-session
description: Review code with a resumable session for uncommitted, staged, branch, whole-project, or security review.
---

# Review With Session

Use one resumable session for review work.

## When To Use

- uncommitted changes
- staged changes only
- one branch or branch diff
- whole project review
- security review on any of the scopes above

## Helper

Run `python3 <this-skill-dir>/scripts/review_session.py <command>` from this skill directory.
Read `references/cache-layout.md` for cache files.
Read `references/security-review-format.md` for security review files.

## Pick Scope

- No scope named: review staged, unstaged, and untracked changes.
- Staged review: inspect `git diff --cached` and staged new files only.
- Branch review: inspect the diff from merge base to branch tip.
- Whole project review: inspect the requested project area in the current repository.
- Security review: keep the requested scope, keep the same files to inspect, and write security notes in the same session files.

Security review does not replace `staged`, `branch`, or `whole project` review.
It adds security checks on top of the chosen scope.

If branch review does not name a base branch:

1. Use the branch upstream if it exists.
2. Else use `main` if present.
3. Else use `master` if present.
4. Else ask the user which base branch to compare.

## Session

1. If the user does not provide a session name, create one with:
   `python3 <this-skill-dir>/scripts/review_session.py init --repo <repo-path>`
2. Tell the user the returned `SESSION_NAME` and `SESSION_PATH`.
3. If the user provides an existing session name, resolve it with:
   `python3 <this-skill-dir>/scripts/review_session.py resolve <session-name>`
4. Before resuming an older session, check for worktree drift with:
   `python3 <this-skill-dir>/scripts/review_session.py status <session-name>`
5. Read session summary through:
   `python3 <this-skill-dir>/scripts/review_session.py summary <session-name>`
6. Read session files through:
   `python3 <this-skill-dir>/scripts/review_session.py show <session-name> <file-key>`
7. Read only the next target through:
   `python3 <this-skill-dir>/scripts/review_session.py next <session-name>`
8. Record the review scope in the session index.

## Read In Order

1. Run `resolve` first.
2. Read the short state through `summary`.
3. Read only the next target through `next`.
4. Read `checked-paths.md` through `show` only when you need to avoid re-reviewing the same path or symbol.
5. Read `findings-open.md` through `show` only when continuing an existing issue.
6. Run `status` only when the worktree may have changed since the cache was created.
7. Read the current diff or source files for the chosen scope only.

## Keep Updated

- Record checked areas and short conclusions in `checked-paths.md`.
- Keep `index.md` short and current.
- Put active findings in `findings-open.md`; move resolved or disproven findings to `findings-closed.md`.
- Keep `next-steps.md` focused on the highest-value remaining targets.
- Keep `<session>/index.md` limited to review scope, current focus, next file to open, last meaningful change, current worktree snapshot counts, and a short review summary.

For security review:

- Write security progress into `index.md`, `findings-open.md`, `findings-closed.md`, `checked-paths.md`, and `next-steps.md`.
- Keep the same file names as other review scopes.
- Update existing findings instead of creating duplicates.
- Check trust boundaries, input handling, auth, permissions, secret handling, file access, network exposure, and repeated patterns in similar code.

## Security Flow

1. Keep the normal session files.
2. Treat `index.md` as the main resume file for security work too.
3. Keep the current focus and next file in the same `index.md`.
4. Keep using the same scope rules for `uncommitted`, `staged`, `branch`, or `whole project`.
5. Follow the detail-file layout in `references/security-review-format.md`.
6. Put findings in `findings-open.md` and `findings-closed.md`.
7. Put repeated-pattern checks and verification notes in `checked-paths.md` and `next-steps.md` when needed.
8. Report security findings from the same session files before any general review notes.

## Continue Or Restart

- Reuse the existing session whenever the user wants another review pass on the same ongoing work.
- If the worktree changed, update the cache instead of creating a duplicate session unless a fresh review is needed.
- If the repo, branch, scope, or task is unrelated to the session, start a new session.
- If the cache no longer matches the repo state closely enough to be trustworthy, tell the user and start a new session.

## Output

- Report findings first.
- Then report residual risk or unverified areas.
- Then report the session name for the next pass.
