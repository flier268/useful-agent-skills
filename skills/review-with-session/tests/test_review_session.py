from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "review_session.py"


class ReviewSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.env = os.environ.copy()
        self.env["REVIEW_WITH_SESSION_ROOT"] = str(self.root / "state")
        self.git("init", "-b", "main")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test User")
        self.write("app.py", "value = 1\n")
        self.git("add", "app.py")
        self.git("commit", "-m", "initial")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.repo,
            text=True,
            capture_output=True,
            check=check,
        )

    def write(self, relative: str, text: str) -> None:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def cli(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            text=True,
            capture_output=True,
            env=self.env,
            check=check,
        )

    def init(self, *args: str) -> Path:
        result = self.cli("init", "--repo", str(self.repo), *args)
        values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
        return Path(values["SESSION_PATH"])

    def test_legacy_init_defaults_to_uncommitted(self) -> None:
        self.write("app.py", "value = 2\n")
        session = self.init("--scope", "legacy label")
        meta = json.loads((session / "session.json").read_text())
        self.assertEqual("change", meta["mode"])
        self.assertEqual("uncommitted", meta["kind"])
        self.assertEqual("legacy label", meta["scope_label"])

    def test_all_structured_scopes(self) -> None:
        self.write("app.py", "value = 2\n")
        uncommitted = self.init("--mode", "change", "--kind", "uncommitted", "--fresh")
        self.assertEqual("uncommitted", json.loads((uncommitted / "session.json").read_text())["kind"])

        self.git("add", "app.py")
        staged = self.init("--mode", "change", "--kind", "staged", "--fresh")
        self.assertEqual("staged", json.loads((staged / "session.json").read_text())["kind"])

        self.git("commit", "-m", "change")
        commit = self.git("rev-parse", "HEAD").stdout.strip()
        commit_session = self.init("--mode", "change", "--kind", "commit", "--commit", commit, "--fresh")
        self.assertEqual(commit, json.loads((commit_session / "session.json").read_text())["commit"])

        audit = self.init(
            "--mode", "audit", "--kind", "project", "--path", "app.py", "--security", "--fresh"
        )
        audit_meta = json.loads((audit / "session.json").read_text())
        self.assertTrue(audit_meta["security"])
        self.assertEqual(["app.py"], audit_meta["paths"])

    def test_branch_records_explicit_base_and_excludes_worktree(self) -> None:
        self.git("switch", "-c", "feature")
        self.write("app.py", "value = 2\n")
        self.git("add", "app.py")
        self.git("commit", "-m", "feature")
        self.write("worktree.py", "not_part_of_branch = True\n")
        session = self.init("--mode", "change", "--kind", "branch", "--base", "main", "--fresh")
        meta = json.loads((session / "session.json").read_text())
        self.assertEqual("main", meta["comparison_ref"])
        self.assertIn("app.py", meta["snapshot"]["files"])
        self.assertNotIn("worktree.py", meta["snapshot"]["files"])

    def test_branch_resolves_an_ahead_upstream(self) -> None:
        self.git("switch", "-c", "feature")
        self.git("switch", "main")
        self.write("base.py", "base = 1\n")
        self.git("add", "base.py")
        self.git("commit", "-m", "advance main")
        self.git("switch", "feature")
        self.git("branch", "--set-upstream-to=main")
        session = self.init("--mode", "change", "--kind", "branch", "--fresh")
        meta = json.loads((session / "session.json").read_text())
        self.assertEqual("main", meta["comparison_ref"])
        self.assertEqual(self.git("rev-parse", "main").stdout.strip(), meta["comparison_sha"])

    def test_same_file_edit_and_stage_transition_are_drift(self) -> None:
        self.write("app.py", "value = 2\n")
        session = self.init("--mode", "change", "--kind", "uncommitted", "--fresh")
        self.write("app.py", "value = 3\n")
        content = self.cli("status", str(session)).stdout
        self.assertIn("DRIFT_STATUS=drift", content)
        self.assertIn("CONTENT_CHANGED app.py", content)

        self.cli("refresh-snapshot", str(session))
        self.git("add", "app.py")
        staged = self.cli("status", str(session)).stdout
        self.assertIn("STAGE_CHANGED app.py", staged)

    def test_untracked_content_and_space_path_drift(self) -> None:
        self.write("space name.txt", "one\n")
        session = self.init("--mode", "change", "--kind", "uncommitted", "--fresh")
        self.write("space name.txt", "two\n")
        result = self.cli("status", str(session)).stdout
        self.assertIn("CONTENT_CHANGED space name.txt", result)

    def test_branch_head_drift(self) -> None:
        self.git("switch", "-c", "feature")
        self.write("app.py", "value = 2\n")
        self.git("add", "app.py")
        self.git("commit", "-m", "first")
        session = self.init("--mode", "change", "--kind", "branch", "--base", "main", "--fresh")
        self.write("more.py", "more = True\n")
        self.git("add", "more.py")
        self.git("commit", "-m", "second")
        result = self.cli("status", str(session)).stdout
        self.assertIn("DRIFT_STATUS=drift", result)
        self.assertIn("ADDED more.py", result)

    def test_exact_session_is_reused(self) -> None:
        self.write("app.py", "value = 2\n")
        first = self.cli("init", "--repo", str(self.repo))
        second = self.cli("init", "--repo", str(self.repo))
        self.assertIn("REUSED=false", first.stdout)
        self.assertIn("REUSED=true", second.stdout)

    def test_structured_finding_deduplicates_counts_and_closes_by_id(self) -> None:
        session = self.init("--fresh")
        args = (
            "add-finding", str(session), "--priority", "P2", "--title", "Reject bad input",
            "--path", "app.py", "--line", "1", "--body", "Bad input reaches the parser."
        )
        first = self.cli(*args)
        duplicate = self.cli(*args)
        self.assertIn("FINDING_ID=F-001", first.stdout)
        self.assertIn("DUPLICATE=F-001", duplicate.stdout)
        updated = self.cli(
            *args, "--id", "F-001", "--body", "Updated evidence reaches the parser."
        )
        self.assertIn("UPDATED_ID=F-001", updated.stdout)
        self.assertIn("Updated evidence", (session / "findings-open.md").read_text())
        summary = self.cli("summary", str(session)).stdout
        self.assertIn("OPEN_FINDINGS=1", summary)

        self.cli("close-finding", str(session), "--id", "F-001", "--resolution", "fixed")
        closed_summary = self.cli("summary", str(session)).stdout
        self.assertIn("OPEN_FINDINGS=0", closed_summary)
        self.assertIn("CLOSED_FINDINGS=1", closed_summary)
        second = self.cli(
            "add-finding", str(session), "--priority", "P3", "--title", "Remove dead branch",
            "--path", "app.py", "--line", "1", "--body", "The branch is unreachable."
        )
        self.assertIn("FINDING_ID=F-002", second.stdout)

    def test_next_returns_first_real_step(self) -> None:
        session = self.init("--fresh")
        self.assertEqual("", self.cli("next", str(session)).stdout.strip())
        self.cli("add-next", str(session), "--step", "Inspect parser callers")
        self.cli("add-next", str(session), "--step", "Inspect serializer callers")
        self.assertEqual("Inspect parser callers", self.cli("next", str(session)).stdout.strip())
        completed = self.cli("complete-next", str(session)).stdout
        self.assertIn("COMPLETED=Inspect parser callers", completed)
        self.assertEqual("Inspect serializer callers", self.cli("next", str(session)).stdout.strip())

    def test_refresh_preserves_snapshot_and_marks_revalidation(self) -> None:
        self.write("app.py", "value = 2\n")
        session = self.init("--fresh")
        self.cli("add-checked", str(session), "--path", "app.py", "--conclusion", "reviewed")
        self.write("app.py", "value = 3\n")
        refreshed = self.cli("refresh-snapshot", str(session)).stdout
        self.assertIn("INVALIDATED_PATHS=1", refreshed)
        history = list((session / "snapshot-history").glob("*.json"))
        self.assertEqual(1, len(history))
        checked = (session / "checked-paths.md").read_text()
        self.assertIn("Revalidation required", checked)
        self.assertIn("app.py", checked)
        rechecked = self.cli(
            "add-checked", str(session), "--path", "app.py", "--conclusion", "revalidated"
        ).stdout
        self.assertIn("REVALIDATED=true", rechecked)
        self.assertNotIn("Revalidation required", (session / "checked-paths.md").read_text())
        summary = self.cli("summary", str(session)).stdout
        self.assertIn("CHECKED_PATHS=1", summary)
        self.assertIn("LAST_MEANINGFUL_CHANGE=revalidated app.py", summary)

    def test_legacy_session_is_readable_and_status_is_unknown(self) -> None:
        legacy = self.root / "state" / "agent-review-with-session-legacy"
        legacy.mkdir(parents=True, mode=0o700)
        (legacy / "session.json").write_text(
            json.dumps({"session_name": "legacy", "repo_path": str(self.repo), "head": "abc"})
        )
        (legacy / "index.md").write_text(
            "# Review Session Index\n\n## Resume Here\n\n- Scope: old\n"
            "- Current focus: none\n- Next file to open: findings-open.md\n"
            "- Last meaningful change: old\n\n## Review Summary\n\n- Status: active\n"
            "- Open findings: 0\n- Closed findings: 0\n- Checked paths: 0\n"
        )
        for name, heading in (
            ("findings-open.md", "# Open Findings\n"),
            ("findings-closed.md", "# Closed Findings\n"),
            ("checked-paths.md", "# Checked Paths\n"),
            ("next-steps.md", "# Next Steps\n"),
        ):
            (legacy / name).write_text(heading, encoding="utf-8")
        resolved = self.cli("resolve", str(legacy)).stdout
        status = self.cli("status", str(legacy)).stdout
        self.assertIn("LEGACY=true", resolved)
        self.assertIn("DRIFT_STATUS=legacy-unknown", status)

    def test_project_path_ignores_commit_outside_scope(self) -> None:
        session = self.init("--mode", "audit", "--kind", "project", "--path", "app.py", "--fresh")
        self.write("outside.py", "outside = True\n")
        self.git("add", "outside.py")
        self.git("commit", "-m", "outside scope")
        status = self.cli("status", str(session)).stdout
        self.assertIn("DRIFT_STATUS=exact", status)

    def test_session_path_and_markdown_inputs_are_restricted(self) -> None:
        result = self.cli("summary", str(self.repo), check=False)
        self.assertEqual(1, result.returncode)
        self.assertIn("invalid session name", result.stderr)

        session = self.init("--fresh")
        injected = self.cli(
            "add-finding", str(session), "--priority", "P2", "--title", "Keep sections intact",
            "--path", "app.py", "--line", "1", "--body", "Body\n\n## Forged section"
        )
        self.assertEqual(0, injected.returncode)
        self.assertIn("\\## Forged section", (session / "findings-open.md").read_text())
        invalid = self.cli("add-next", str(session), "--step", "one\n- forged", check=False)
        self.assertEqual(1, invalid.returncode)

    def test_malformed_session_is_isolated_and_permissions_are_private(self) -> None:
        state = self.root / "state"
        malformed = state / "agent-review-with-session-malformed"
        malformed.mkdir(parents=True, mode=0o700)
        state.chmod(0o700)
        (malformed / "session.json").write_text("{bad json", encoding="utf-8")
        result = self.cli("list")
        self.assertEqual(0, result.returncode)
        session = self.init("--fresh")
        if os.name != "nt":
            self.assertEqual(0o700, session.stat().st_mode & 0o777)

    def test_untracked_symlink_hash_does_not_read_target(self) -> None:
        secret = self.root / "secret.txt"
        secret.write_text("private-content", encoding="utf-8")
        (self.repo / "link.txt").symlink_to(secret)
        session = self.init("--fresh")
        meta = json.loads((session / "session.json").read_text())
        observed = meta["snapshot"]["files"]["link.txt"]["content"]
        expected = hashlib.sha256(
            b"symlink\0" + str(secret).encode("utf-8")
        ).hexdigest()
        secret_hash = hashlib.sha256(b"private-content").hexdigest()
        self.assertEqual(expected, observed)
        self.assertNotEqual(secret_hash, observed)

    def test_literal_pathspec_control_output_and_file_mode_drift(self) -> None:
        magic = ":(top)victim"
        self.write(magic, "magic\n")
        self.write("victim", "ordinary\n")
        self.git("add", f":(literal){magic}", "victim")
        self.git("commit", "-m", "pathspec names")
        audit = self.init("--mode", "audit", "--kind", "project", "--path", magic, "--fresh")
        files = json.loads((audit / "session.json").read_text())["snapshot"]["files"]
        self.assertEqual([magic], list(files))

        control_name = "escape-\x1b-file"
        self.write(control_name, "one\n")
        session = self.init("--fresh")
        os.chmod(self.repo / control_name, 0o755)
        result = self.cli("status", str(session)).stdout
        self.assertIn("MODE_CHANGED", result)
        self.assertNotIn("\x1b", result)
        self.assertIn("\\x1b", result)
        checked = self.cli(
            "add-checked", str(session), "--path", "tick`and\nnewline", "--conclusion", "reviewed"
        )
        self.assertEqual(0, checked.returncode)

    def test_staged_mode_and_merge_commit_track_modes_and_scope(self) -> None:
        self.write("app.py", "value = 2\n")
        os.chmod(self.repo / "app.py", 0o755)
        self.git("add", "app.py")
        staged = self.init("--mode", "change", "--kind", "staged", "--fresh")
        self.git("update-index", "--chmod=-x", "app.py")
        status = self.cli("status", str(staged)).stdout
        self.assertIn("MODE_CHANGED app.py", status)
        snapshot = json.loads((staged / "session.json").read_text())["snapshot"]
        self.assertEqual([], snapshot["unstaged"])
        self.assertEqual([], snapshot["untracked"])

        self.git("reset", "--hard", "HEAD")
        self.git("switch", "-c", "side")
        self.write("side.py", "side = True\n")
        self.git("add", "side.py")
        self.git("commit", "-m", "side")
        self.git("switch", "main")
        self.write("main.py", "main = True\n")
        self.git("add", "main.py")
        self.git("commit", "-m", "main")
        self.git("merge", "--no-ff", "side", "-m", "merge")
        merge = self.git("rev-parse", "HEAD").stdout.strip()
        commit_session = self.init(
            "--mode", "change", "--kind", "commit", "--commit", merge, "--fresh"
        )
        commit_snapshot = json.loads((commit_session / "session.json").read_text())["snapshot"]
        self.assertIn("side.py", commit_snapshot["files"])
        self.assertEqual([], commit_snapshot["unstaged"])

    def test_session_root_is_not_repermissioned_or_created_in_repo(self) -> None:
        original_mode = Path("/tmp").stat().st_mode & 0o7777
        broad_env = self.env.copy()
        broad_env["REVIEW_WITH_SESSION_ROOT"] = "/tmp"
        broad = subprocess.run(
            [sys.executable, str(SCRIPT), "init", "--repo", str(self.repo)],
            text=True, capture_output=True, env=broad_env
        )
        self.assertEqual(1, broad.returncode)
        self.assertEqual(original_mode, Path("/tmp").stat().st_mode & 0o7777)

        inside = self.repo / ".review-state"
        inside_env = self.env.copy()
        inside_env["REVIEW_WITH_SESSION_ROOT"] = str(inside)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "init", "--repo", str(self.repo)],
            text=True, capture_output=True, env=inside_env
        )
        self.assertEqual(1, result.returncode)
        self.assertFalse(inside.exists())

        linked_target = self.repo / ".linked-review-state"
        linked_root = self.root / "linked-state"
        linked_root.symlink_to(linked_target, target_is_directory=True)
        linked_env = self.env.copy()
        linked_env["REVIEW_WITH_SESSION_ROOT"] = str(linked_root)
        linked = subprocess.run(
            [sys.executable, str(SCRIPT), "init", "--repo", str(self.repo)],
            text=True, capture_output=True, env=linked_env
        )
        self.assertEqual(1, linked.returncode)
        self.assertFalse(linked_target.exists())

    def test_non_git_directory_has_actionable_error(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        result = self.cli("init", "--repo", str(outside), check=False)
        self.assertEqual(1, result.returncode)
        self.assertIn("not a git repository", result.stderr)


if __name__ == "__main__":
    unittest.main()
