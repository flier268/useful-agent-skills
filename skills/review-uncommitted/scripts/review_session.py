#!/usr/bin/env python3
"""
Create and inspect resumable review sessions for uncommitted worktree reviews.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


SESSION_PREFIX = 'codex-review-uncommitted-'
DEFAULT_ROOT = Path(tempfile.gettempdir())

INDEX_TEMPLATE = """# Review Session Index

Session: {session_name}
Repo: {repo_path}
Created: {created_from}
Head: {head}

## Resume Here

- Current focus: not set
- Next file to open: findings-open.md
- Last meaningful change: session created

## Snapshot

- Staged files: {staged_count}
- Unstaged files: {unstaged_count}
- Untracked files: {untracked_count}

## Review Summary

- Status: active
- Open findings: 0
- Closed findings: 0
- Checked paths: 0

## Files

- findings-open.md
- findings-closed.md
- checked-paths.md
- next-steps.md
- worktree-status.txt
- worktree-files.json
"""

FINDINGS_OPEN_TEMPLATE = """# Open Findings

## Usage

- Add one section per active finding.
- Keep the first line of each section as the concise conclusion.
- Move resolved items to `findings-closed.md` instead of leaving stale text here.
"""

FINDINGS_CLOSED_TEMPLATE = """# Closed Findings

## Usage

- Move findings here once they are fixed, disproven, or accepted as non-issues.
- Keep a short note about why the finding was closed.
"""

CHECKED_PATHS_TEMPLATE = """# Checked Paths

## Usage

- Record paths or symbols already reviewed so later passes do not restart from zero.
- For each item, note the conclusion and whether another pass is needed.
"""

NEXT_STEPS_TEMPLATE = """# Next Steps

- Add the next highest-value review targets here.
- Update `index.md` so `Next file to open` points to the most relevant file.
"""


def run_git(repo: Path, args: list[str]) -> str:
    result = subprocess.run(
        ['git', *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f'git {" ".join(args)} failed')
    return result.stdout


def collect_snapshot(repo: Path) -> dict:
    head = run_git(repo, ['rev-parse', 'HEAD']).strip()
    status_text = run_git(repo, ['status', '--short'])
    staged = run_git(repo, ['diff', '--cached', '--name-only']).splitlines()
    unstaged = run_git(repo, ['diff', '--name-only']).splitlines()
    untracked = run_git(repo, ['ls-files', '--others', '--exclude-standard']).splitlines()
    return {
        'head': head,
        'status_text': status_text,
        'staged': [x for x in staged if x],
        'unstaged': [x for x in unstaged if x],
        'untracked': [x for x in untracked if x],
    }


def resolve_session(session: str) -> Path:
    candidate = Path(session)
    if candidate.exists():
        return candidate.resolve()
    fallback = DEFAULT_ROOT / session
    if fallback.exists():
        return fallback.resolve()
    raise FileNotFoundError(f'session not found: {session}')


def command_init(repo: Path) -> int:
    repo = repo.resolve()
    snapshot = collect_snapshot(repo)
    session_dir = Path(tempfile.mkdtemp(prefix=SESSION_PREFIX, dir=DEFAULT_ROOT))
    session_name = session_dir.name

    meta = {
        'session_name': session_name,
        'repo_path': str(repo),
        'head': snapshot['head'],
    }

    (session_dir / 'session.json').write_text(
        json.dumps(meta, indent=2) + '\n',
        encoding='utf-8',
    )
    (session_dir / 'index.md').write_text(
        INDEX_TEMPLATE.format(
            session_name=session_name,
            repo_path=repo,
            created_from=snapshot['head'],
            head=snapshot['head'],
            staged_count=len(snapshot['staged']),
            unstaged_count=len(snapshot['unstaged']),
            untracked_count=len(snapshot['untracked']),
        ),
        encoding='utf-8',
    )
    (session_dir / 'findings-open.md').write_text(FINDINGS_OPEN_TEMPLATE, encoding='utf-8')
    (session_dir / 'findings-closed.md').write_text(FINDINGS_CLOSED_TEMPLATE, encoding='utf-8')
    (session_dir / 'checked-paths.md').write_text(CHECKED_PATHS_TEMPLATE, encoding='utf-8')
    (session_dir / 'next-steps.md').write_text(NEXT_STEPS_TEMPLATE, encoding='utf-8')
    (session_dir / 'worktree-status.txt').write_text(snapshot['status_text'], encoding='utf-8')
    (session_dir / 'worktree-files.json').write_text(
        json.dumps(
            {
                'staged': snapshot['staged'],
                'unstaged': snapshot['unstaged'],
                'untracked': snapshot['untracked'],
            },
            indent=2,
        )
        + '\n',
        encoding='utf-8',
    )

    print(f'SESSION_NAME={session_name}')
    print(f'SESSION_ROOT={DEFAULT_ROOT}')
    print(f'SESSION_PATH={session_dir}')
    return 0


def command_resolve(session: str) -> int:
    session_dir = resolve_session(session)
    print(f'SESSION_NAME={session_dir.name}')
    print(f'SESSION_ROOT={DEFAULT_ROOT}')
    print(f'SESSION_PATH={session_dir}')
    for name in [
        'index.md',
        'findings-open.md',
        'findings-closed.md',
        'checked-paths.md',
        'next-steps.md',
    ]:
        print(str(session_dir / name))
    return 0


def command_status(session: str) -> int:
    session_dir = resolve_session(session)
    meta = json.loads((session_dir / 'session.json').read_text(encoding='utf-8'))
    repo = Path(meta['repo_path'])
    current = collect_snapshot(repo)
    original = json.loads((session_dir / 'worktree-files.json').read_text(encoding='utf-8'))

    original_set = set(original.get('staged', [])) | set(original.get('unstaged', [])) | set(
        original.get('untracked', [])
    )
    current_set = set(current['staged']) | set(current['unstaged']) | set(current['untracked'])

    added = sorted(current_set - original_set)
    removed = sorted(original_set - current_set)

    print(f'SESSION_NAME={session_dir.name}')
    print(f'REPO={repo}')
    print(f'ORIGINAL_HEAD={meta["head"]}')
    print(f'CURRENT_HEAD={current["head"]}')
    print(f'CURRENT_CHANGED_FILES={len(current_set)}')
    print(f'ADDED_FILES={len(added)}')
    for path in added:
        print(f'+ {path}')
    print(f'REMOVED_FILES={len(removed)}')
    for path in removed:
        print(f'- {path}')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)

    init_parser = subparsers.add_parser('init')
    init_parser.add_argument('--repo', default='.', help='Repository path')

    resolve_parser = subparsers.add_parser('resolve')
    resolve_parser.add_argument('session', help='Session name or path')

    status_parser = subparsers.add_parser('status')
    status_parser.add_argument('session', help='Session name or path')

    args = parser.parse_args()

    try:
        if args.command == 'init':
            return command_init(Path(args.repo))
        if args.command == 'resolve':
            return command_resolve(args.session)
        if args.command == 'status':
            return command_status(args.session)
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1

    return 1


if __name__ == '__main__':
    raise SystemExit(main())
