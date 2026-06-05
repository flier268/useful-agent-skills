#!/usr/bin/env python3
"""
Create and inspect resumable review sessions for uncommitted worktree reviews.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


SESSION_PREFIX = 'agent-review-with-session-'
DEFAULT_ROOT = Path(tempfile.gettempdir())

READABLE_FILES = {
    'index': 'index.md',
    'findings-open': 'findings-open.md',
    'findings-closed': 'findings-closed.md',
    'checked-paths': 'checked-paths.md',
    'next-steps': 'next-steps.md',
    'worktree-status': 'worktree-status.txt',
    'worktree-files': 'worktree-files.json',
    'session': 'session.json',
}

WRITABLE_FILES = {
    'findings-open': 'findings-open.md',
    'findings-closed': 'findings-closed.md',
    'checked-paths': 'checked-paths.md',
    'next-steps': 'next-steps.md',
}

INDEX_TEMPLATE = """# Review Session Index

Session: {session_name}
Repo: {repo_path}
Created: {created_from}
Head: {head}

## Resume Here

- Scope: {scope}
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


def parse_index_fields(index_text: str) -> dict[str, str]:
    patterns = {
        'scope': r'- Scope:\s*(.+)',
        'current_focus': r'- Current focus:\s*(.+)',
        'next_file_to_open': r'- Next file to open:\s*(.+)',
        'last_meaningful_change': r'- Last meaningful change:\s*(.+)',
        'staged_files': r'- Staged files:\s*(.+)',
        'unstaged_files': r'- Unstaged files:\s*(.+)',
        'untracked_files': r'- Untracked files:\s*(.+)',
        'status': r'- Status:\s*(.+)',
        'open_findings': r'- Open findings:\s*(.+)',
        'closed_findings': r'- Closed findings:\s*(.+)',
        'checked_paths': r'- Checked paths:\s*(.+)',
    }
    result: dict[str, str] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, index_text)
        result[key] = match.group(1).strip() if match else ''
    return result


def command_init(repo: Path, scope: str) -> int:
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
            scope=scope,
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


def command_list_sessions() -> int:
    sessions = sorted(DEFAULT_ROOT.glob(f'{SESSION_PREFIX}*'), key=lambda path: path.stat().st_mtime, reverse=True)
    for session_dir in sessions:
        if not session_dir.is_dir():
            continue
        meta_path = session_dir / 'session.json'
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        index_fields = parse_index_fields((session_dir / 'index.md').read_text(encoding='utf-8'))
        print(
            '\t'.join(
                [
                    session_dir.name,
                    str(session_dir),
                    meta.get('repo_path', ''),
                    index_fields.get('scope', ''),
                    index_fields.get('status', ''),
                    index_fields.get('current_focus', ''),
                ]
            )
        )
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


def command_show(session: str, name: str) -> int:
    session_dir = resolve_session(session)
    if name not in READABLE_FILES:
        choices = ', '.join(sorted(READABLE_FILES))
        raise ValueError(f'unknown session file key: {name}. use one of: {choices}')
    path = session_dir / READABLE_FILES[name]
    print(path.read_text(encoding='utf-8'), end='')
    return 0


def command_summary(session: str) -> int:
    session_dir = resolve_session(session)
    meta = json.loads((session_dir / 'session.json').read_text(encoding='utf-8'))
    index_fields = parse_index_fields((session_dir / 'index.md').read_text(encoding='utf-8'))
    print(f'SESSION_NAME={session_dir.name}')
    print(f'SESSION_PATH={session_dir}')
    print(f'REPO={meta["repo_path"]}')
    print(f'HEAD={meta["head"]}')
    print(f'SCOPE={index_fields["scope"]}')
    print(f'CURRENT_FOCUS={index_fields["current_focus"]}')
    print(f'NEXT_FILE_TO_OPEN={index_fields["next_file_to_open"]}')
    print(f'LAST_MEANINGFUL_CHANGE={index_fields["last_meaningful_change"]}')
    print(f'STAGED_FILES={index_fields["staged_files"]}')
    print(f'UNSTAGED_FILES={index_fields["unstaged_files"]}')
    print(f'UNTRACKED_FILES={index_fields["untracked_files"]}')
    print(f'STATUS={index_fields["status"]}')
    print(f'OPEN_FINDINGS={index_fields["open_findings"]}')
    print(f'CLOSED_FINDINGS={index_fields["closed_findings"]}')
    print(f'CHECKED_PATHS={index_fields["checked_paths"]}')
    return 0


def command_next(session: str) -> int:
    session_dir = resolve_session(session)
    index_fields = parse_index_fields((session_dir / 'index.md').read_text(encoding='utf-8'))
    print(index_fields['next_file_to_open'])
    return 0


def text_from_arg(text: str | None, text_file: str | None) -> str:
    if text is not None and text_file is not None:
        raise ValueError('use only one of --text or --text-file')
    if text is not None:
        return text
    if text_file is None:
        raise ValueError('missing text; use --text or --text-file')
    if text_file == '-':
        return sys.stdin.read()
    return Path(text_file).read_text(encoding='utf-8')


def replace_index_line(text: str, label: str, value: str) -> str:
    pattern = rf'^- {re.escape(label)}:\s*.*$'
    replacement = f'- {label}: {value}'
    next_text, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f'index field not found: {label}')
    return next_text


def replace_or_insert_index_line(text: str, label: str, value: str, after_label: str | None = None) -> str:
    pattern = rf'^- {re.escape(label)}:\s*.*$'
    replacement = f'- {label}: {value}'
    next_text, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count == 1:
        return next_text
    if after_label is not None:
        after_pattern = rf'^- {re.escape(after_label)}:\s*.*$'
        match = re.search(after_pattern, text, flags=re.MULTILINE)
        if match:
            return text[: match.end()] + '\n' + replacement + text[match.end():]
    marker = '## Resume Here\n\n'
    if marker in text:
        return text.replace(marker, marker + replacement + '\n', 1)
    raise ValueError(f'index field not found: {label}')


def command_update_index(
    session: str,
    scope: str | None,
    current_focus: str | None,
    next_file_to_open: str | None,
    last_meaningful_change: str | None,
    status: str | None,
    open_findings: str | None,
    closed_findings: str | None,
    checked_paths: str | None,
) -> int:
    session_dir = resolve_session(session)
    path = session_dir / 'index.md'
    text = path.read_text(encoding='utf-8')
    updates = [
        ('Scope', scope),
        ('Current focus', current_focus),
        ('Next file to open', next_file_to_open),
        ('Last meaningful change', last_meaningful_change),
        ('Status', status),
        ('Open findings', open_findings),
        ('Closed findings', closed_findings),
        ('Checked paths', checked_paths),
    ]
    changed = False
    for label, value in updates:
        if value is not None:
            if label == 'Scope':
                text = replace_or_insert_index_line(text, label, value)
            else:
                text = replace_index_line(text, label, value)
            changed = True
    if not changed:
        raise ValueError('no update fields provided')
    path.write_text(text, encoding='utf-8')
    print(f'UPDATED={path}')
    return 0


def session_file_path(session_dir: Path, name: str) -> Path:
    if name not in WRITABLE_FILES:
        choices = ', '.join(sorted(WRITABLE_FILES))
        raise ValueError(f'unknown writable session file key: {name}. use one of: {choices}')
    return session_dir / WRITABLE_FILES[name]


def command_append(session: str, name: str, text: str) -> int:
    session_dir = resolve_session(session)
    path = session_file_path(session_dir, name)
    current = path.read_text(encoding='utf-8')
    separator = '\n\n' if current and not current.endswith('\n\n') else ''
    path.write_text(current + separator + text.rstrip() + '\n', encoding='utf-8')
    print(f'UPDATED={path}')
    return 0


def command_replace(session: str, name: str, text: str) -> int:
    session_dir = resolve_session(session)
    path = session_file_path(session_dir, name)
    path.write_text(text.rstrip() + '\n', encoding='utf-8')
    print(f'UPDATED={path}')
    return 0


def command_clear_open_findings(session: str) -> int:
    session_dir = resolve_session(session)
    path = session_dir / 'findings-open.md'
    path.write_text(FINDINGS_OPEN_TEMPLATE, encoding='utf-8')
    print(f'UPDATED={path}')
    return 0


def markdown_section(title: str, body: str) -> str:
    return f'## {title.strip()}\n\n{body.strip()}\n'


def command_add_finding(session: str, title: str, body: str) -> int:
    return command_append(session, 'findings-open', markdown_section(title, body))


def command_add_checked(session: str, path_value: str, conclusion: str) -> int:
    return command_append(session, 'checked-paths', f'- `{path_value}`: {conclusion}')


def command_add_next(session: str, step: str) -> int:
    return command_append(session, 'next-steps', f'- {step}')


def split_markdown_sections(text: str) -> tuple[str, list[tuple[str, str]]]:
    matches = list(re.finditer(r'^##\s+(.+?)\s*$', text, flags=re.MULTILINE))
    if not matches:
        return text, []
    prefix = text[: matches[0].start()].rstrip() + '\n'
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((match.group(1).strip(), text[match.start():end].strip() + '\n'))
    return prefix, sections


def command_close_finding(
    session: str,
    title: str,
    resolution: str | None,
    verification: str | None,
    keep_open: bool,
) -> int:
    session_dir = resolve_session(session)
    open_path = session_dir / 'findings-open.md'
    closed_path = session_dir / 'findings-closed.md'
    prefix, sections = split_markdown_sections(open_path.read_text(encoding='utf-8'))
    selected: tuple[str, str] | None = None
    remaining: list[tuple[str, str]] = []
    for section_title, section_text in sections:
        if selected is None and section_title == title:
            selected = (section_title, section_text)
        else:
            remaining.append((section_title, section_text))
    if selected is None:
        raise ValueError(f'open finding not found: {title}')

    note_lines = []
    if resolution:
        note_lines.append(f'- Resolution: {resolution}')
    if verification:
        note_lines.append(f'- Verification: {verification}')
    closed_text = selected[1].rstrip()
    if note_lines:
        closed_text += '\n\n' + '\n'.join(note_lines)
    command_append(session, 'findings-closed', closed_text)

    if not keep_open:
        next_open = prefix.rstrip() + '\n'
        if remaining:
            next_open += '\n' + '\n'.join(section_text.rstrip() for _, section_text in remaining) + '\n'
        open_path.write_text(next_open, encoding='utf-8')
        print(f'UPDATED={open_path}')
    return 0


def command_refresh_snapshot(session: str) -> int:
    session_dir = resolve_session(session)
    meta_path = session_dir / 'session.json'
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    repo = Path(meta['repo_path'])
    snapshot = collect_snapshot(repo)
    meta['head'] = snapshot['head']
    meta_path.write_text(json.dumps(meta, indent=2) + '\n', encoding='utf-8')
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
    index_path = session_dir / 'index.md'
    index_text = index_path.read_text(encoding='utf-8')
    index_text = replace_index_line(index_text, 'Staged files', str(len(snapshot['staged'])))
    index_text = replace_index_line(index_text, 'Unstaged files', str(len(snapshot['unstaged'])))
    index_text = replace_index_line(index_text, 'Untracked files', str(len(snapshot['untracked'])))
    index_path.write_text(index_text, encoding='utf-8')
    print(f'UPDATED={session_dir}')
    return 0


def count_markdown_sections(path: Path) -> int:
    _, sections = split_markdown_sections(path.read_text(encoding='utf-8'))
    return sum(1 for title, _ in sections if title != 'Usage')


def count_checked_paths(path: Path) -> int:
    count = 0
    for line in path.read_text(encoding='utf-8').splitlines():
        stripped = line.strip()
        if not stripped.startswith('- '):
            continue
        if stripped.startswith('- Record ') or stripped.startswith('- For each '):
            continue
        count += 1
    return count


def command_sync_index(session: str) -> int:
    session_dir = resolve_session(session)
    open_count = count_markdown_sections(session_dir / 'findings-open.md')
    closed_count = count_markdown_sections(session_dir / 'findings-closed.md')
    checked_count = count_checked_paths(session_dir / 'checked-paths.md')
    return command_update_index(
        session,
        scope=None,
        current_focus=None,
        next_file_to_open=None,
        last_meaningful_change=None,
        status=None,
        open_findings=str(open_count),
        closed_findings=str(closed_count),
        checked_paths=str(checked_count),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)

    init_parser = subparsers.add_parser('init')
    init_parser.add_argument('--repo', default='.', help='Repository path')
    init_parser.add_argument('--scope', default='uncommitted changes', help='Review scope label')

    subparsers.add_parser('list')

    resolve_parser = subparsers.add_parser('resolve')
    resolve_parser.add_argument('session', help='Session name or path')

    status_parser = subparsers.add_parser('status')
    status_parser.add_argument('session', help='Session name or path')

    show_parser = subparsers.add_parser('show')
    show_parser.add_argument('session', help='Session name or path')
    show_parser.add_argument('name', help='Session file key')

    summary_parser = subparsers.add_parser('summary')
    summary_parser.add_argument('session', help='Session name or path')

    next_parser = subparsers.add_parser('next')
    next_parser.add_argument('session', help='Session name or path')

    update_index_parser = subparsers.add_parser('update-index')
    update_index_parser.add_argument('session', help='Session name or path')
    update_index_parser.add_argument('--scope')
    update_index_parser.add_argument('--current-focus')
    update_index_parser.add_argument('--next-file-to-open')
    update_index_parser.add_argument('--last-meaningful-change')
    update_index_parser.add_argument('--status')
    update_index_parser.add_argument('--open-findings')
    update_index_parser.add_argument('--closed-findings')
    update_index_parser.add_argument('--checked-paths')

    append_parser = subparsers.add_parser('append')
    append_parser.add_argument('session', help='Session name or path')
    append_parser.add_argument('name', help='Writable session file key')
    append_parser.add_argument('--text', help='Text to append')
    append_parser.add_argument('--text-file', help='File to append, or - for stdin')

    replace_parser = subparsers.add_parser('replace')
    replace_parser.add_argument('session', help='Session name or path')
    replace_parser.add_argument('name', help='Writable session file key')
    replace_parser.add_argument('--text', help='Replacement text')
    replace_parser.add_argument('--text-file', help='Replacement text file, or - for stdin')

    clear_open_parser = subparsers.add_parser('clear-open-findings')
    clear_open_parser.add_argument('session', help='Session name or path')

    add_finding_parser = subparsers.add_parser('add-finding')
    add_finding_parser.add_argument('session', help='Session name or path')
    add_finding_parser.add_argument('--title', required=True)
    add_finding_parser.add_argument('--body', help='Finding body')
    add_finding_parser.add_argument('--body-file', help='Finding body file, or - for stdin')

    close_finding_parser = subparsers.add_parser('close-finding')
    close_finding_parser.add_argument('session', help='Session name or path')
    close_finding_parser.add_argument('--title', required=True)
    close_finding_parser.add_argument('--resolution')
    close_finding_parser.add_argument('--verification')
    close_finding_parser.add_argument('--keep-open', action='store_true')

    add_checked_parser = subparsers.add_parser('add-checked')
    add_checked_parser.add_argument('session', help='Session name or path')
    add_checked_parser.add_argument('--path', required=True)
    add_checked_parser.add_argument('--conclusion', required=True)

    add_next_parser = subparsers.add_parser('add-next')
    add_next_parser.add_argument('session', help='Session name or path')
    add_next_parser.add_argument('--step', required=True)

    clear_next_parser = subparsers.add_parser('clear-next')
    clear_next_parser.add_argument('session', help='Session name or path')

    refresh_parser = subparsers.add_parser('refresh-snapshot')
    refresh_parser.add_argument('session', help='Session name or path')

    sync_parser = subparsers.add_parser('sync-index')
    sync_parser.add_argument('session', help='Session name or path')

    args = parser.parse_args()

    try:
        if args.command == 'init':
            return command_init(Path(args.repo), args.scope)
        if args.command == 'list':
            return command_list_sessions()
        if args.command == 'resolve':
            return command_resolve(args.session)
        if args.command == 'status':
            return command_status(args.session)
        if args.command == 'show':
            return command_show(args.session, args.name)
        if args.command == 'summary':
            return command_summary(args.session)
        if args.command == 'next':
            return command_next(args.session)
        if args.command == 'update-index':
            return command_update_index(
                args.session,
                scope=args.scope,
                current_focus=args.current_focus,
                next_file_to_open=args.next_file_to_open,
                last_meaningful_change=args.last_meaningful_change,
                status=args.status,
                open_findings=args.open_findings,
                closed_findings=args.closed_findings,
                checked_paths=args.checked_paths,
            )
        if args.command == 'append':
            return command_append(args.session, args.name, text_from_arg(args.text, args.text_file))
        if args.command == 'replace':
            return command_replace(args.session, args.name, text_from_arg(args.text, args.text_file))
        if args.command == 'clear-open-findings':
            return command_clear_open_findings(args.session)
        if args.command == 'add-finding':
            return command_add_finding(args.session, args.title, text_from_arg(args.body, args.body_file))
        if args.command == 'close-finding':
            return command_close_finding(
                args.session,
                title=args.title,
                resolution=args.resolution,
                verification=args.verification,
                keep_open=args.keep_open,
            )
        if args.command == 'add-checked':
            return command_add_checked(args.session, args.path, args.conclusion)
        if args.command == 'add-next':
            return command_add_next(args.session, args.step)
        if args.command == 'clear-next':
            return command_replace(args.session, 'next-steps', NEXT_STEPS_TEMPLATE)
        if args.command == 'refresh-snapshot':
            return command_refresh_snapshot(args.session)
        if args.command == 'sync-index':
            return command_sync_index(args.session)
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1

    return 1


if __name__ == '__main__':
    raise SystemExit(main())
