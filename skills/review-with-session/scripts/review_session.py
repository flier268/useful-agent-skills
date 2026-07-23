#!/usr/bin/env python3
"""Create and maintain durable, resumable code-review sessions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import stat
import subprocess
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 2
SESSION_PREFIX = "agent-review-with-session-"
LEGACY_ROOT = Path(tempfile.gettempdir())

READABLE_FILES = {
    "index": "index.md",
    "findings-open": "findings-open.md",
    "findings-closed": "findings-closed.md",
    "checked-paths": "checked-paths.md",
    "next-steps": "next-steps.md",
    "worktree-status": "worktree-status.txt",
    "worktree-files": "worktree-files.json",
    "session": "session.json",
}
WRITABLE_FILES = {
    "findings-open": "findings-open.md",
    "findings-closed": "findings-closed.md",
    "checked-paths": "checked-paths.md",
    "next-steps": "next-steps.md",
}

INDEX_TEMPLATE = """# Review Session Index

Session: {session_name}
Repo: {repo_path}
Created: {created_at}
Head: {head}

## Resume Here

- Scope: {scope}
- Mode: {mode}
- Kind: {kind}
- Current focus: not set
- Next file to open: next-steps.md
- Last meaningful change: session created

## Snapshot

- Staged files: {staged_count}
- Unstaged files: {unstaged_count}
- Untracked files: {untracked_count}
- Fingerprint: {fingerprint}

## Review Summary

- Status: active
- Open findings: 0
- Closed findings: 0
- Checked paths: 0
"""

FINDINGS_OPEN_TEMPLATE = "# Open Findings\n"
FINDINGS_CLOSED_TEMPLATE = "# Closed Findings\n"
CHECKED_PATHS_TEMPLATE = "# Checked Paths\n"
NEXT_STEPS_TEMPLATE = "# Next Steps\n"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_root() -> Path:
    override = os.environ.get("REVIEW_WITH_SESSION_ROOT")
    if override:
        return Path(os.path.abspath(Path(override).expanduser()))
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        return Path(base) / "review-with-session" if base else Path.home() / "AppData/Local/review-with-session"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/review-with-session"
    state_home = os.environ.get("XDG_STATE_HOME")
    return Path(state_home) / "review-with-session" if state_home else Path.home() / ".local/state/review-with-session"


def ensure_root() -> Path:
    root = default_root()
    existed = root.exists()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        metadata = root.stat()
        if metadata.st_uid != os.getuid():
            raise ValueError(f"session root is owned by another user: {root}")
        if existed and stat.S_IMODE(metadata.st_mode) & 0o077:
            raise ValueError(f"session root permissions are too broad: {root}")
    return root


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path: Path, value: Any) -> None:
    atomic_write(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def run_git_bytes(repo: Path, args: list[str]) -> bytes:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, check=False)
    if result.returncode != 0:
        error = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(error or f'git {" ".join(args)} failed')
    return result.stdout


def run_git(repo: Path, args: list[str]) -> str:
    return run_git_bytes(repo, args).decode("utf-8", "surrogateescape")


def git_paths(repo: Path, args: list[str]) -> list[str]:
    normalized = list(args)
    if "--" in normalized:
        normalized.insert(normalized.index("--"), "-z")
    else:
        normalized.append("-z")
    raw = run_git_bytes(repo, normalized)
    return [value.decode("utf-8", "surrogateescape") for value in raw.split(b"\0") if value]


def validate_repo(repo: Path) -> Path:
    repo = repo.resolve()
    root = Path(run_git(repo, ["rev-parse", "--show-toplevel"]).strip()).resolve()
    return root


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def single_line(value: str, field: str, *, reject_backtick: bool = False) -> str:
    if any(unicodedata.category(character) == "Cc" for character in value):
        raise ValueError(f"{field} cannot contain control characters")
    if reject_backtick and "`" in value:
        raise ValueError(f"{field} cannot contain backticks")
    return value


def markdown_body(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    safe = "".join(
        character
        if character in {"\n", "\t"} or unicodedata.category(character) != "Cc"
        else f"\\x{ord(character):02x}"
        for character in normalized
    )
    return re.sub(r"^##(\s+)", r"\\##\1", safe, flags=re.MULTILINE)


def inline_path(value: str) -> str:
    encoded = terminal_value(value).replace("`", r"\x60")
    return encoded.replace("\\", "\\\\")


def terminal_value(value: str) -> str:
    return "".join(
        character if unicodedata.category(character) != "Cc" else f"\\x{ord(character):02x}"
        for character in value
    )


def literal_pathspecs(paths: list[str]) -> list[str]:
    return [f":(literal){path}" for path in paths]


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode):
        return sha256_bytes(b"symlink\0" + os.readlink(path).encode("utf-8", "surrogateescape"))
    if not stat.S_ISREG(metadata.st_mode):
        return f"non-regular:{stat.S_IFMT(metadata.st_mode):o}"
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as handle:
        opened = os.fstat(handle.fileno())
        if not stat.S_ISREG(opened.st_mode):
            raise ValueError(f"refusing to hash non-regular file: {path}")
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def worktree_entry(repo: Path, relative: str) -> dict[str, str]:
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError(f"unsafe repository path: {relative}")
    path = repo / relative_path
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return {"content": "missing", "mode": "missing"}
    return {
        "content": file_sha(path),
        "mode": (
            "120000"
            if stat.S_ISLNK(metadata.st_mode)
            else ("100755" if metadata.st_mode & stat.S_IXUSR else "100644")
            if stat.S_ISREG(metadata.st_mode)
            else f"special:{stat.S_IFMT(metadata.st_mode):o}"
        ),
    }


def git_object_sha(repo: Path, ref: str, path: str) -> str:
    result = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=repo, capture_output=True, check=False)
    return sha256_bytes(result.stdout) if result.returncode == 0 else "missing"


def git_mode(repo: Path, ref: str, path: str) -> str:
    if ref == ":":
        output = run_git(repo, ["ls-files", "--stage", "--", f":(literal){path}"])
    else:
        output = run_git(repo, ["ls-tree", ref, "--", f":(literal){path}"])
    return output.split(maxsplit=1)[0] if output.strip() else "missing"


def commit_parent(repo: Path, commit: str) -> str | None:
    parts = run_git(repo, ["rev-list", "--parents", "-n", "1", commit]).split()
    return parts[1] if len(parts) > 1 else None


def existing_ref(repo: Path, ref: str) -> bool:
    result = subprocess.run(["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], cwd=repo)
    return result.returncode == 0


def resolve_branch_base(repo: Path, explicit: str | None) -> tuple[str, str]:
    if explicit:
        if not existing_ref(repo, explicit):
            raise ValueError(f"base ref not found: {explicit}")
        return explicit, run_git(repo, ["rev-parse", f"{explicit}^{{commit}}"]).strip()
    upstream = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if upstream.returncode == 0:
        candidate = upstream.stdout.strip()
        ahead = int(run_git(repo, ["rev-list", "--count", f"HEAD..{candidate}"]).strip())
        if ahead > 0:
            return candidate, run_git(repo, ["rev-parse", f"{candidate}^{{commit}}"]).strip()
    for candidate in ("main", "master"):
        if existing_ref(repo, candidate):
            return candidate, run_git(repo, ["rev-parse", f"{candidate}^{{commit}}"]).strip()
    raise ValueError("cannot resolve branch base; pass --base")


def scope_signature(meta: dict[str, Any]) -> str:
    fields = {
        "repo_path": meta["repo_path"],
        "mode": meta["mode"],
        "kind": meta["kind"],
        "security": bool(meta.get("security")),
        "paths": meta.get("paths", []),
        "base_ref": meta.get("base_ref"),
        "comparison_ref": meta.get("comparison_ref"),
        "commit": meta.get("commit"),
    }
    return sha256_bytes(json.dumps(fields, sort_keys=True).encode())


def changed_sets(repo: Path, paths: list[str]) -> tuple[list[str], list[str], list[str]]:
    suffix = ["--", *literal_pathspecs(paths)] if paths else []
    staged = git_paths(repo, ["diff", "--cached", "--name-only", *suffix])
    unstaged = git_paths(repo, ["diff", "--name-only", *suffix])
    untracked_args = ["ls-files", "--others", "--exclude-standard"]
    if paths:
        untracked_args.extend(["--", *literal_pathspecs(paths)])
    untracked = git_paths(repo, untracked_args)
    return sorted(set(staged)), sorted(set(unstaged)), sorted(set(untracked))


def target_files(repo: Path, meta: dict[str, Any], head: str) -> dict[str, dict[str, str]]:
    kind = meta["kind"]
    paths = list(meta.get("paths", []))
    staged, unstaged, untracked = changed_sets(repo, paths)
    result: dict[str, dict[str, str]] = {}
    if kind == "uncommitted":
        for path in sorted(set(staged + unstaged + untracked)):
            states = []
            if path in staged:
                states.append("staged")
            if path in unstaged:
                states.append("unstaged")
            if path in untracked:
                states.append("untracked")
            result[path] = {
                "state": "+".join(states),
                **worktree_entry(repo, path),
            }
    elif kind == "project":
        tracked_args = ["ls-files"]
        if paths:
            tracked_args.extend(["--", *literal_pathspecs(paths)])
        tracked = git_paths(repo, tracked_args)
        for path in sorted(set(tracked + untracked)):
            states = []
            if path in staged:
                states.append("staged")
            if path in unstaged:
                states.append("unstaged")
            if path in untracked:
                states.append("untracked")
            result[path] = {
                "state": "+".join(states) or "tracked",
                **worktree_entry(repo, path),
            }
    elif kind == "staged":
        for path in staged:
            result[path] = {
                "state": "staged",
                "content": git_object_sha(repo, "", path),
                "mode": git_mode(repo, ":", path),
            }
    elif kind == "branch":
        merge_base = meta["merge_base"]
        names = git_paths(repo, ["diff", "--name-only", f"{merge_base}..{head}", "--"])
        for path in sorted(set(names)):
            result[path] = {
                "state": "branch",
                "content": git_object_sha(repo, head, path),
                "mode": git_mode(repo, head, path),
            }
    elif kind == "commit":
        commit = meta["commit"]
        parent = commit_parent(repo, commit)
        names = (
            git_paths(repo, ["diff", "--name-only", f"{parent}..{commit}", "--"])
            if parent
            else git_paths(repo, ["diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit, "--"])
        )
        for path in sorted(set(names)):
            result[path] = {
                "state": "commit",
                "content": git_object_sha(repo, commit, path),
                "mode": git_mode(repo, commit, path),
            }
    return result


def build_snapshot(repo: Path, meta: dict[str, Any]) -> dict[str, Any]:
    head = run_git(repo, ["rev-parse", "HEAD"]).strip()
    kind = meta["kind"]
    paths = list(meta.get("paths", []))
    suffix = ["--", *literal_pathspecs(paths)] if paths else []
    staged, unstaged, untracked = changed_sets(repo, paths)
    if kind == "uncommitted":
        target = run_git_bytes(repo, ["diff", "--binary", "HEAD", *suffix])
    elif kind == "staged":
        target = run_git_bytes(repo, ["diff", "--cached", "--binary", *suffix])
    elif kind == "branch":
        comparison_ref = meta["comparison_ref"]
        comparison_sha = run_git(repo, ["rev-parse", f"{comparison_ref}^{{commit}}"]).strip()
        merge_base = run_git(repo, ["merge-base", head, comparison_sha]).strip()
        meta["comparison_sha"] = comparison_sha
        meta["merge_base"] = merge_base
        target = run_git_bytes(repo, ["diff", "--binary", f"{merge_base}..{head}", "--"])
    elif kind == "commit":
        commit = run_git(repo, ["rev-parse", f'{meta["commit"]}^{{commit}}']).strip()
        meta["commit"] = commit
        parent = commit_parent(repo, commit)
        target = (
            run_git_bytes(repo, ["diff", "--binary", f"{parent}..{commit}", "--"])
            if parent
            else run_git_bytes(repo, ["show", "--format=", "--binary", "--root", commit])
        )
    elif kind == "project":
        baseline = (
            run_git_bytes(repo, ["ls-tree", "-r", "HEAD", "--", *literal_pathspecs(paths)])
            if paths
            else run_git_bytes(repo, ["rev-parse", "HEAD^{tree}"])
        )
        target = baseline + b"\0" + run_git_bytes(repo, ["diff", "--binary", "HEAD", *suffix])
    else:
        raise ValueError(f"unsupported scope kind: {kind}")
    files = target_files(repo, meta, head)
    if kind in {"branch", "commit"}:
        staged, unstaged, untracked = [], [], []
    elif kind == "staged":
        unstaged, untracked = [], []
    material = {
        "head": head if kind in {"uncommitted", "branch"} or (kind == "project" and not paths) else None,
        "merge_base": meta.get("merge_base"),
        "target_sha": sha256_bytes(target),
        "files": files,
    }
    fingerprint = sha256_bytes(json.dumps(material, sort_keys=True).encode())
    return {
        "captured_at": now_iso(),
        "head": head,
        "merge_base": meta.get("merge_base"),
        "fingerprint": fingerprint,
        "target_sha": material["target_sha"],
        "files": files,
        "staged": staged,
        "unstaged": unstaged,
        "untracked": untracked,
        "status_text": run_git(repo, ["status", "--short"]),
    }


def session_roots() -> list[Path]:
    roots = [default_root(), LEGACY_ROOT]
    return list(dict.fromkeys(Path(os.path.abspath(path)) for path in roots))


def safe_session_dir(path: Path) -> Path:
    candidate = Path(os.path.abspath(path))
    if candidate.name == "" or not candidate.name.startswith(SESSION_PREFIX):
        raise ValueError(f"invalid session name: {candidate.name}")
    if candidate.parent not in session_roots():
        raise ValueError(f"session is outside an allowed root: {candidate}")
    metadata = candidate.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise ValueError(f"session is not a real directory: {candidate}")
    if os.name != "nt":
        if metadata.st_uid != os.getuid():
            raise ValueError(f"session is owned by another user: {candidate}")
        if stat.S_IMODE(metadata.st_mode) & 0o077:
            raise ValueError(f"session permissions are too broad: {candidate}")
    meta_path = candidate / "session.json"
    meta_stat = meta_path.lstat()
    if stat.S_ISLNK(meta_stat.st_mode) or not stat.S_ISREG(meta_stat.st_mode):
        raise ValueError(f"invalid session metadata file: {meta_path}")
    for required in ("index.md", "findings-open.md", "findings-closed.md", "checked-paths.md", "next-steps.md"):
        required_path = candidate / required
        required_stat = required_path.lstat()
        if stat.S_ISLNK(required_stat.st_mode) or not stat.S_ISREG(required_stat.st_mode):
            raise ValueError(f"invalid session file: {required_path}")
    return candidate


def resolve_session(session: str) -> Path:
    candidate = Path(session)
    if candidate.exists():
        return safe_session_dir(candidate)
    for root in session_roots():
        fallback = root / session
        if fallback.exists():
            return safe_session_dir(fallback)
    raise FileNotFoundError(f"session not found: {session}")


def load_meta(session_dir: Path) -> dict[str, Any]:
    meta_path = session_dir / "session.json"
    if meta_path.stat().st_size > 1024 * 1024:
        raise ValueError(f"session metadata is too large: {meta_path}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if not isinstance(meta, dict) or not isinstance(meta.get("repo_path"), str):
        raise ValueError(f"invalid session metadata: {meta_path}")
    if "schema_version" not in meta:
        meta["schema_version"] = 1
        meta["legacy"] = True
    return meta


def parse_index_fields(text: str) -> dict[str, str]:
    labels = [
        "Scope", "Mode", "Kind", "Current focus", "Next file to open",
        "Last meaningful change", "Staged files", "Unstaged files",
        "Untracked files", "Fingerprint", "Status", "Open findings",
        "Closed findings", "Checked paths",
    ]
    return {
        label.lower().replace(" ", "_"): (
            match.group(1).strip() if (match := re.search(rf"^- {re.escape(label)}:\s*(.*)$", text, re.MULTILINE)) else ""
        )
        for label in labels
    }


def replace_index_field(text: str, label: str, value: str, section: str = "## Resume Here") -> str:
    pattern = rf"^- {re.escape(label)}:\s*.*$"
    replacement = f"- {label}: {value}"
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count:
        return updated
    marker = section + "\n\n"
    if marker not in text:
        raise ValueError(f"index section not found: {section}")
    return text.replace(marker, marker + replacement + "\n", 1)


def split_sections(text: str) -> tuple[str, list[tuple[str, str]]]:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", text, re.MULTILINE))
    if not matches:
        return text.rstrip() + "\n", []
    prefix = text[:matches[0].start()].rstrip() + "\n"
    sections = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((match.group(1).strip(), text[match.start():end].strip() + "\n"))
    return prefix, sections


def count_sections(path: Path) -> int:
    _, sections = split_sections(path.read_text(encoding="utf-8"))
    return sum(title != "Usage" for title, _ in sections)


def count_checked(path: Path) -> int:
    paths = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if match := re.match(r"^- `(.+?)`:", line):
            paths.add(match.group(1))
    return len(paths)


def sync_index(session_dir: Path) -> None:
    path = session_dir / "index.md"
    text = path.read_text(encoding="utf-8")
    values = {
        "Open findings": str(count_sections(session_dir / "findings-open.md")),
        "Closed findings": str(count_sections(session_dir / "findings-closed.md")),
        "Checked paths": str(count_checked(session_dir / "checked-paths.md")),
    }
    for label, value in values.items():
        text = replace_index_field(text, label, value, "## Review Summary")
    atomic_write(path, text)


def append_file(path: Path, text: str) -> None:
    current = path.read_text(encoding="utf-8")
    separator = "\n" if current.endswith("\n") else "\n\n"
    atomic_write(path, current.rstrip() + separator + "\n" + text.strip() + "\n")


def all_sessions() -> list[Path]:
    found: dict[str, Path] = {}
    for root in session_roots():
        if not root.exists():
            continue
        for path in root.glob(f"{SESSION_PREFIX}*"):
            try:
                safe = safe_session_dir(path)
                load_meta(safe)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            found[str(safe)] = safe
    return sorted(found.values(), key=lambda path: path.stat().st_mtime, reverse=True)


def make_meta(args: argparse.Namespace, repo: Path) -> dict[str, Any]:
    mode = args.mode or ("audit" if args.kind == "project" else "change")
    kind = args.kind or ("project" if mode == "audit" else "uncommitted")
    if mode == "audit" and kind != "project":
        raise ValueError("audit mode requires --kind project")
    if mode == "change" and kind == "project":
        raise ValueError("project scope requires --mode audit")
    if args.security and mode != "audit":
        raise ValueError("--security requires audit mode")
    meta: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "repo_path": str(repo),
        "mode": mode,
        "kind": kind,
        "security": bool(args.security),
        "paths": args.paths or [],
        "scope_label": single_line(args.scope, "scope") if args.scope else f"{mode}:{kind}",
        "base_ref": args.base,
        "commit": args.commit,
        "status": "active",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    if kind == "branch":
        comparison_ref, comparison_sha = resolve_branch_base(repo, args.base)
        meta["comparison_ref"] = comparison_ref
        meta["comparison_sha"] = comparison_sha
        meta["merge_base"] = run_git(repo, ["merge-base", "HEAD", comparison_sha]).strip()
    if kind == "commit":
        if not args.commit:
            raise ValueError("commit scope requires --commit")
        meta["commit"] = run_git(repo, ["rev-parse", f"{args.commit}^{{commit}}"]).strip()
    return meta


def reusable_session(meta: dict[str, Any], fingerprint: str) -> Path | None:
    signature = scope_signature(meta)
    for path in all_sessions():
        existing = load_meta(path)
        if existing.get("schema_version") != SCHEMA_VERSION or existing.get("status", "active") != "active":
            continue
        if existing.get("scope_signature") != signature:
            continue
        if existing.get("snapshot", {}).get("fingerprint") == fingerprint:
            return path
    return None


def command_init(args: argparse.Namespace) -> int:
    repo = validate_repo(Path(args.repo))
    meta = make_meta(args, repo)
    snapshot = build_snapshot(repo, meta)
    meta["scope_signature"] = scope_signature(meta)
    meta["snapshot"] = snapshot
    if not args.fresh and (reused := reusable_session(meta, snapshot["fingerprint"])):
        print(f"SESSION_NAME={terminal_value(reused.name)}")
        print(f"SESSION_ROOT={terminal_value(str(reused.parent))}")
        print(f"SESSION_PATH={terminal_value(str(reused))}")
        print("REUSED=true")
        return 0
    root = default_root()
    resolved_root = root.resolve(strict=False)
    resolved_repo = repo.resolve()
    if resolved_root == resolved_repo or resolved_repo in resolved_root.parents:
        raise ValueError("session root cannot be inside the reviewed repository")
    root = ensure_root()
    final_name = f"{SESSION_PREFIX}{secrets.token_hex(6)}"
    while (root / final_name).exists():
        final_name = f"{SESSION_PREFIX}{secrets.token_hex(6)}"
    session_dir = Path(tempfile.mkdtemp(prefix=".review-session-build-", dir=root))
    if os.name != "nt":
        session_dir.chmod(0o700)
    meta["session_name"] = final_name
    write_json(session_dir / "session.json", meta)
    atomic_write(
        session_dir / "index.md",
        INDEX_TEMPLATE.format(
            session_name=final_name,
            repo_path=repo,
            created_at=meta["created_at"],
            head=snapshot["head"],
            scope=meta["scope_label"],
            mode=meta["mode"],
            kind=meta["kind"],
            staged_count=len(snapshot["staged"]),
            unstaged_count=len(snapshot["unstaged"]),
            untracked_count=len(snapshot["untracked"]),
            fingerprint=snapshot["fingerprint"],
        ),
    )
    atomic_write(session_dir / "findings-open.md", FINDINGS_OPEN_TEMPLATE)
    atomic_write(session_dir / "findings-closed.md", FINDINGS_CLOSED_TEMPLATE)
    atomic_write(session_dir / "checked-paths.md", CHECKED_PATHS_TEMPLATE)
    initial_targets = list(snapshot["files"])
    if not initial_targets and meta["kind"] == "project":
        initial_targets = meta["paths"] or ["Inspect repository entry points and architecture boundaries"]
    next_text = NEXT_STEPS_TEMPLATE
    if initial_targets:
        next_text += "\n" + "\n".join(f"- Inspect `{inline_path(target)}`" for target in initial_targets) + "\n"
    atomic_write(session_dir / "next-steps.md", next_text)
    atomic_write(session_dir / "worktree-status.txt", snapshot["status_text"])
    write_json(
        session_dir / "worktree-files.json",
        {key: snapshot[key] for key in ("staged", "unstaged", "untracked", "files", "fingerprint")},
    )
    final_dir = root / final_name
    os.replace(session_dir, final_dir)
    session_dir = final_dir
    print(f"SESSION_NAME={terminal_value(session_dir.name)}")
    print(f"SESSION_ROOT={terminal_value(str(root))}")
    print(f"SESSION_PATH={terminal_value(str(session_dir))}")
    print("REUSED=false")
    return 0


def command_resolve(session: str) -> int:
    path = resolve_session(session)
    meta = load_meta(path)
    print(f"SESSION_NAME={terminal_value(path.name)}")
    print(f"SESSION_ROOT={terminal_value(str(path.parent))}")
    print(f"SESSION_PATH={terminal_value(str(path))}")
    print(f"SCHEMA_VERSION={meta.get('schema_version')}")
    print(f"LEGACY={str(bool(meta.get('legacy'))).lower()}")
    return 0


def command_list(args: argparse.Namespace) -> int:
    repo_filter = str(Path(args.repo).resolve()) if args.repo else None
    for path in all_sessions():
        meta = load_meta(path)
        fields = parse_index_fields((path / "index.md").read_text(encoding="utf-8"))
        if repo_filter and meta.get("repo_path") != repo_filter:
            continue
        if args.status and fields.get("status", meta.get("status", "active")) != args.status:
            continue
        if args.mode and meta.get("mode") != args.mode:
            continue
        if args.kind and meta.get("kind") != args.kind:
            continue
        print("\t".join(terminal_value(str(value)) for value in [
            path.name, str(path), meta.get("repo_path", ""), meta.get("mode", "legacy"),
            meta.get("kind", "legacy"), fields.get("status", "active"), fields.get("current_focus", ""),
        ]))
    return 0


def compare_snapshots(original: dict[str, Any], current: dict[str, Any]) -> dict[str, list[str]]:
    old_files = original.get("files", {})
    new_files = current.get("files", {})
    old_names, new_names = set(old_files), set(new_files)
    shared = old_names & new_names
    return {
        "added": sorted(new_names - old_names),
        "removed": sorted(old_names - new_names),
        "content_changed": sorted(path for path in shared if old_files[path].get("content") != new_files[path].get("content")),
        "stage_changed": sorted(path for path in shared if old_files[path].get("state") != new_files[path].get("state")),
        "mode_changed": sorted(path for path in shared if old_files[path].get("mode") != new_files[path].get("mode")),
    }


def command_status(session: str) -> int:
    session_dir = resolve_session(session)
    meta = load_meta(session_dir)
    print(f"SESSION_NAME={terminal_value(session_dir.name)}")
    if meta.get("schema_version") != SCHEMA_VERSION:
        print("DRIFT_STATUS=legacy-unknown")
        return 0
    repo = validate_repo(Path(meta["repo_path"]))
    working_meta = dict(meta)
    current = build_snapshot(repo, working_meta)
    original = meta["snapshot"]
    drift = compare_snapshots(original, current)
    exact = original.get("fingerprint") == current.get("fingerprint")
    print(f"DRIFT_STATUS={'exact' if exact else 'drift'}")
    print(f"ORIGINAL_HEAD={original.get('head', '')}")
    print(f"CURRENT_HEAD={current.get('head', '')}")
    for label, key in [
        ("ADDED_FILES", "added"), ("REMOVED_FILES", "removed"),
        ("CONTENT_CHANGED_FILES", "content_changed"), ("STAGE_CHANGED_FILES", "stage_changed"),
        ("MODE_CHANGED_FILES", "mode_changed"),
    ]:
        print(f"{label}={len(drift[key])}")
        for path in drift[key]:
            print(f"{key.upper()} {terminal_value(path)}")
    return 0


def command_show(session: str, name: str) -> int:
    if name not in READABLE_FILES:
        raise ValueError(f"unknown session file key: {name}")
    print((resolve_session(session) / READABLE_FILES[name]).read_text(encoding="utf-8"), end="")
    return 0


def command_summary(session: str) -> int:
    session_dir = resolve_session(session)
    meta = load_meta(session_dir)
    fields = parse_index_fields((session_dir / "index.md").read_text(encoding="utf-8"))
    values = {
        "SESSION_NAME": session_dir.name,
        "SESSION_PATH": session_dir,
        "REPO": meta.get("repo_path", ""),
        "SCHEMA_VERSION": meta.get("schema_version", 1),
        "MODE": meta.get("mode", "legacy"),
        "KIND": meta.get("kind", "legacy"),
        "SECURITY": str(bool(meta.get("security"))).lower(),
        **{key.upper(): value for key, value in fields.items()},
    }
    for key, value in values.items():
        print(f"{key}={terminal_value(str(value))}")
    return 0


def command_next(session: str) -> int:
    session_dir = resolve_session(session)
    text = (session_dir / "next-steps.md").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("- ") and line not in {
            "- Add the next highest-value review targets here.",
            "- Update `index.md` so `Next file to open` points to the most relevant file.",
        }:
            print(line[2:].strip())
            return 0
    fields = parse_index_fields((session_dir / "index.md").read_text(encoding="utf-8"))
    focus = fields.get("current_focus", "")
    print("" if focus in {"", "not set"} else terminal_value(focus))
    return 0


def remove_next_step(session_dir: Path, expected: str | None = None) -> str | None:
    path = session_dir / "next-steps.md"
    lines = path.read_text(encoding="utf-8").splitlines()
    removed = None
    updated = []
    for line in lines:
        if removed is None and line.startswith("- "):
            step = line[2:].strip()
            if expected is None or step == expected:
                removed = step
                continue
        updated.append(line)
    if removed is not None:
        atomic_write(path, "\n".join(updated).rstrip() + "\n")
    return removed


def command_complete_next(session: str) -> int:
    session_dir = resolve_session(session)
    completed = remove_next_step(session_dir)
    print(f"COMPLETED={terminal_value(completed or '')}")
    return 0


def text_from_arg(text: str | None, text_file: str | None) -> str:
    if text is not None and text_file is not None:
        raise ValueError("use only one text source")
    if text is not None:
        return text
    if text_file == "-":
        return sys.stdin.read()
    if text_file:
        return Path(text_file).read_text(encoding="utf-8")
    raise ValueError("missing text")


def command_update_index(args: argparse.Namespace) -> int:
    session_dir = resolve_session(args.session)
    path = session_dir / "index.md"
    text = path.read_text(encoding="utf-8")
    updates = {
        "Scope": args.scope, "Current focus": args.current_focus,
        "Next file to open": args.next_file_to_open,
        "Last meaningful change": args.last_meaningful_change, "Status": args.status,
        "Open findings": args.open_findings, "Closed findings": args.closed_findings,
        "Checked paths": args.checked_paths,
    }
    changed = False
    for label, value in updates.items():
        if value is not None:
            value = single_line(value, label)
            section = "## Review Summary" if label in {"Status", "Open findings", "Closed findings", "Checked paths"} else "## Resume Here"
            text = replace_index_field(text, label, value, section)
            changed = True
    if not changed:
        raise ValueError("no update fields provided")
    atomic_write(path, text)
    if args.status:
        meta = load_meta(session_dir)
        meta["status"] = args.status
        meta["updated_at"] = now_iso()
        write_json(session_dir / "session.json", meta)
    print(f"UPDATED={path}")
    return 0


def session_file(session_dir: Path, name: str) -> Path:
    if name not in WRITABLE_FILES:
        raise ValueError(f"unknown writable session file key: {name}")
    return session_dir / WRITABLE_FILES[name]


def command_append_replace(args: argparse.Namespace, replace: bool) -> int:
    session_dir = resolve_session(args.session)
    path = session_file(session_dir, args.name)
    value = text_from_arg(args.text, args.text_file)
    atomic_write(path, value.rstrip() + "\n") if replace else append_file(path, value)
    sync_index(session_dir)
    print(f"UPDATED={path}")
    return 0


def finding_headers(path: Path) -> list[tuple[str, str]]:
    _, sections = split_sections(path.read_text(encoding="utf-8"))
    return sections


def command_add_finding(args: argparse.Namespace) -> int:
    session_dir = resolve_session(args.session)
    path = session_dir / "findings-open.md"
    body = markdown_body(text_from_arg(args.body, args.body_file))
    title_value = single_line(args.title, "title")
    prefix, sections = split_sections(path.read_text(encoding="utf-8"))
    if args.priority or args.path or args.line is not None:
        if not (args.priority and args.path and args.line is not None):
            raise ValueError("structured finding requires --priority, --path, and --line")
        path_value = inline_path(args.path)
        signature = f"[{args.priority}] {title_value} — {path_value}:{args.line}"
        if args.finding_id and not re.fullmatch(r"F-\d+", args.finding_id):
            raise ValueError("finding id must use F-NNN form")
        for title, _ in sections:
            if re.sub(r"^F-\d+\s+", "", title) == signature and not title.startswith(f"{args.finding_id} "):
                print(f"DUPLICATE={title.split()[0]}")
                return 0
        if args.finding_id:
            if not any(title.startswith(f"{args.finding_id} ") for title, _ in sections):
                raise ValueError(f"open finding not found: {args.finding_id}")
            finding_id = args.finding_id
        else:
            all_sections = sections + finding_headers(session_dir / "findings-closed.md")
            numbers = [int(match.group(1)) for title, _ in all_sections if (match := re.match(r"F-(\d+)", title))]
            finding_id = f"F-{max(numbers, default=0) + 1:03d}"
        title = f"{finding_id} {signature}"
        extras = []
        if args.evidence:
            extras.append(f"### Evidence\n\n{markdown_body(args.evidence)}")
        if args.trust_boundary:
            extras.append(f"### Trust boundary\n\n{markdown_body(args.trust_boundary)}")
        if args.remediation:
            extras.append(f"### Remediation\n\n{markdown_body(args.remediation)}")
        section = f"## {title}\n\n{body.strip()}"
        if extras:
            section += "\n\n" + "\n\n".join(extras)
        if args.finding_id:
            rewritten = []
            for existing_title, existing_section in sections:
                rewritten.append(section if existing_title.startswith(f"{finding_id} ") else existing_section.rstrip())
            atomic_write(path, prefix.rstrip() + "\n\n" + "\n\n".join(rewritten) + "\n")
        else:
            append_file(path, section)
        sync_index(session_dir)
        print(f"{'UPDATED_ID' if args.finding_id else 'FINDING_ID'}={finding_id}")
    else:
        append_file(path, f"## {title_value.strip()}\n\n{body.strip()}")
        sync_index(session_dir)
        print("FINDING_ID=legacy")
    return 0


def command_close_finding(args: argparse.Namespace) -> int:
    if not args.finding_id and not args.title:
        raise ValueError("use --id or --title")
    if args.finding_id:
        single_line(args.finding_id, "finding id")
    if args.title:
        single_line(args.title, "title")
    session_dir = resolve_session(args.session)
    open_path = session_dir / "findings-open.md"
    prefix, sections = split_sections(open_path.read_text(encoding="utf-8"))
    selected = None
    remaining = []
    for title, section in sections:
        matches = title.startswith(f"{args.finding_id} ") if args.finding_id else title == args.title
        if selected is None and matches:
            selected = section
        else:
            remaining.append(section)
    if selected is None:
        raise ValueError("open finding not found")
    notes = []
    if args.resolution:
        notes.append(f"- Resolution: {single_line(args.resolution, 'resolution')}")
    if args.verification:
        notes.append(f"- Verification: {single_line(args.verification, 'verification')}")
    closed = selected.rstrip() + (("\n\n" + "\n".join(notes)) if notes else "")
    append_file(session_dir / "findings-closed.md", closed)
    if not args.keep_open:
        atomic_write(open_path, prefix.rstrip() + "\n" + ("\n" + "\n\n".join(item.rstrip() for item in remaining) + "\n" if remaining else ""))
    sync_index(session_dir)
    print(f"UPDATED={session_dir}")
    return 0


def command_add_checked(args: argparse.Namespace) -> int:
    session_dir = resolve_session(args.session)
    meta = load_meta(session_dir)
    fingerprint = meta.get("snapshot", {}).get("fingerprint", "legacy")
    checked_path = session_dir / "checked-paths.md"
    path_value = inline_path(args.path)
    conclusion = single_line(args.conclusion, "conclusion")
    replacement = f"- `{path_value}`: {conclusion} [fingerprint: {fingerprint}]"
    lines = checked_path.read_text(encoding="utf-8").splitlines()
    updated: list[str] = []
    replaced = False
    revalidated = False
    for line in lines:
        if re.match(rf"^- `{re.escape(path_value)}`:", line):
            if not replaced:
                updated.append(replacement)
                replaced = True
            continue
        if line.startswith("- Revalidation required:"):
            pending = re.findall(r"`([^`]+)`", line)
            if path_value in pending:
                pending = [path for path in pending if path != path_value]
                revalidated = True
                if pending:
                    updated.append("- Revalidation required: " + ", ".join(f"`{path}`" for path in pending))
                continue
        updated.append(line)
    if not replaced:
        if updated and updated[-1] != "":
            updated.append("")
        updated.append(replacement)
    atomic_write(checked_path, "\n".join(updated).rstrip() + "\n")
    if revalidated:
        index_path = session_dir / "index.md"
        index_text = index_path.read_text(encoding="utf-8")
        index_text = replace_index_field(
            index_text,
            "Last meaningful change",
            f"revalidated {path_value}",
            "## Resume Here",
        )
        atomic_write(index_path, index_text)
    remove_next_step(session_dir, f"Inspect `{path_value}`")
    sync_index(session_dir)
    print(f"UPDATED={checked_path}")
    print(f"REVALIDATED={str(revalidated).lower()}")
    return 0


def command_add_next(args: argparse.Namespace) -> int:
    session_dir = resolve_session(args.session)
    append_file(session_dir / "next-steps.md", f"- {single_line(args.step, 'step')}")
    print(f"UPDATED={session_dir / 'next-steps.md'}")
    return 0


def command_refresh(session: str) -> int:
    session_dir = resolve_session(session)
    meta = load_meta(session_dir)
    if meta.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("legacy session cannot refresh structured snapshot")
    repo = validate_repo(Path(meta["repo_path"]))
    current = build_snapshot(repo, meta)
    original = meta["snapshot"]
    drift = compare_snapshots(original, current)
    history = session_dir / "snapshot-history"
    history.mkdir(exist_ok=True)
    write_json(history / f'{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")}.json', original)
    invalidated = sorted(set(sum(drift.values(), [])))
    if invalidated:
        append_file(
            session_dir / "checked-paths.md",
            "- Revalidation required: " + ", ".join(f"`{inline_path(path)}`" for path in invalidated),
        )
    meta["snapshot"] = current
    meta["updated_at"] = now_iso()
    write_json(session_dir / "session.json", meta)
    atomic_write(session_dir / "worktree-status.txt", current["status_text"])
    write_json(
        session_dir / "worktree-files.json",
        {key: current[key] for key in ("staged", "unstaged", "untracked", "files", "fingerprint")},
    )
    index_path = session_dir / "index.md"
    text = index_path.read_text(encoding="utf-8")
    for label, value in {
        "Staged files": len(current["staged"]), "Unstaged files": len(current["unstaged"]),
        "Untracked files": len(current["untracked"]), "Fingerprint": current["fingerprint"],
        "Last meaningful change": "snapshot refreshed; changed paths require revalidation",
    }.items():
        section = "## Snapshot" if label != "Last meaningful change" else "## Resume Here"
        text = replace_index_field(text, label, str(value), section)
    atomic_write(index_path, text)
    sync_index(session_dir)
    print(f"UPDATED={session_dir}")
    print(f"INVALIDATED_PATHS={len(invalidated)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--repo", default=".")
    init.add_argument("--scope")
    init.add_argument("--mode", choices=["change", "audit"])
    init.add_argument("--kind", choices=["uncommitted", "staged", "branch", "commit", "project"])
    init.add_argument("--base")
    init.add_argument("--commit")
    init.add_argument("--path", dest="paths", action="append")
    init.add_argument("--security", action="store_true")
    init.add_argument("--fresh", action="store_true")
    listing = sub.add_parser("list")
    listing.add_argument("--repo")
    listing.add_argument("--status")
    listing.add_argument("--mode", choices=["change", "audit"])
    listing.add_argument("--kind")
    for command in ("resolve", "status", "summary", "next", "complete-next", "refresh-snapshot", "sync-index", "clear-open-findings", "clear-next"):
        item = sub.add_parser(command)
        item.add_argument("session")
    show = sub.add_parser("show")
    show.add_argument("session")
    show.add_argument("name")
    update = sub.add_parser("update-index")
    update.add_argument("session")
    for option in ("scope", "current-focus", "next-file-to-open", "last-meaningful-change", "status", "open-findings", "closed-findings", "checked-paths"):
        update.add_argument(f"--{option}")
    for command in ("append", "replace"):
        item = sub.add_parser(command)
        item.add_argument("session")
        item.add_argument("name")
        item.add_argument("--text")
        item.add_argument("--text-file")
    finding = sub.add_parser("add-finding")
    finding.add_argument("session")
    finding.add_argument("--title", required=True)
    finding.add_argument("--body")
    finding.add_argument("--body-file")
    finding.add_argument("--priority", choices=["P0", "P1", "P2", "P3"])
    finding.add_argument("--path")
    finding.add_argument("--line", type=int)
    finding.add_argument("--evidence")
    finding.add_argument("--trust-boundary")
    finding.add_argument("--remediation")
    finding.add_argument("--id", dest="finding_id")
    close = sub.add_parser("close-finding")
    close.add_argument("session")
    close.add_argument("--id", dest="finding_id")
    close.add_argument("--title")
    close.add_argument("--resolution")
    close.add_argument("--verification")
    close.add_argument("--keep-open", action="store_true")
    checked = sub.add_parser("add-checked")
    checked.add_argument("session")
    checked.add_argument("--path", required=True)
    checked.add_argument("--conclusion", required=True)
    next_item = sub.add_parser("add-next")
    next_item.add_argument("session")
    next_item.add_argument("--step", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "init":
            return command_init(args)
        if args.command == "list":
            return command_list(args)
        if args.command == "resolve":
            return command_resolve(args.session)
        if args.command == "status":
            return command_status(args.session)
        if args.command == "show":
            return command_show(args.session, args.name)
        if args.command == "summary":
            return command_summary(args.session)
        if args.command == "next":
            return command_next(args.session)
        if args.command == "complete-next":
            return command_complete_next(args.session)
        if args.command == "update-index":
            return command_update_index(args)
        if args.command in {"append", "replace"}:
            return command_append_replace(args, args.command == "replace")
        if args.command == "add-finding":
            return command_add_finding(args)
        if args.command == "close-finding":
            return command_close_finding(args)
        if args.command == "add-checked":
            return command_add_checked(args)
        if args.command == "add-next":
            return command_add_next(args)
        if args.command == "refresh-snapshot":
            return command_refresh(args.session)
        session_dir = resolve_session(args.session)
        if args.command == "sync-index":
            sync_index(session_dir)
        elif args.command == "clear-open-findings":
            atomic_write(session_dir / "findings-open.md", FINDINGS_OPEN_TEMPLATE)
            sync_index(session_dir)
        elif args.command == "clear-next":
            atomic_write(session_dir / "next-steps.md", NEXT_STEPS_TEMPLATE)
        print(f"UPDATED={session_dir}")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
