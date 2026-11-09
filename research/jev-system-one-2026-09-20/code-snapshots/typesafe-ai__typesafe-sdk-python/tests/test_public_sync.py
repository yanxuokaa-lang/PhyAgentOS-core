"""Test snapshot filtering and release retries."""

import base64
import importlib
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / ".github/scripts"
INCLUDES = "pyproject.toml\nsrc/\ndocs/changelog.md\n.github/workflows/publish.yml\n"

pytestmark = pytest.mark.skipif(
    not (SCRIPTS / "sync_public.py").is_file(), reason="Public sync tooling is only available in the dev repository"
)


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(  # noqa: S603 - Explicit Git arguments in disposable fixtures.
        ["git", *args],  # noqa: S607 - Git is supplied by CI.
        cwd=repo,
        text=True,
        stderr=subprocess.PIPE,
    ).strip()


def write(repo: Path, path: str, content: str) -> None:
    file = repo / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content)


def commit(repo: Path, message: str = "private work") -> None:
    git(repo, "add", ".")
    git(repo, "commit", "--allow-empty", "-qm", message)


def set_version(repo: Path, version: str) -> None:
    write(repo, "pyproject.toml", f'[project]\nname = "typesafe-sdk"\nversion = "{version}"\n')
    write(repo, "docs/changelog.md", f"## v{version} (2026-09-11)\n\nReviewed release notes.\n")


def run_script(source: Path, script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - Repository-owned script with explicit fixture paths.
        [sys.executable, str(SCRIPTS / script), *args],
        cwd=source,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "UV_NO_CACHE": "1"},
        timeout=30,
    )


@pytest.fixture
def repos(tmp_path: Path) -> tuple[Path, Path, Path]:
    source, destination, remote = tmp_path / "dev", tmp_path / "public", tmp_path / "remote.git"
    for repo in [source, destination]:
        repo.mkdir()
        git(repo, "init", "-q", "--initial-branch=main")
        git(repo, "config", "user.name", "Test")
        git(repo, "config", "user.email", "test@example.com")
        git(repo, "config", "commit.gpgsign", "false")
    git(tmp_path, "init", "--bare", "--initial-branch=main", str(remote))
    git(destination, "remote", "add", "origin", str(remote))
    set_version(source, "42.0.0")
    write(source, ".releaseinclude", INCLUDES)
    write(source, "src/typesafe_sdk/__init__.py", "# public source\n")
    write(source, ".github/workflows/publish.yml", "name: Publish\n")
    write(source, ".github/workflows/CI.yml", "private CI\n")
    write(source, ".dagger/private.py", "private infrastructure\n")
    write(source, "RELEASING.md", "private instructions\n")
    commit(source)
    commit(source, "more private history")
    return source, destination, remote


def sync(source: Path, destination: Path, tag: str = "v42.0.0") -> subprocess.CompletedProcess[str]:
    return run_script(source, "sync_public.py", str(destination), tag, "--dry-run")


@pytest.fixture
def signer(repos: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Emulate GitHub's Git object API in the bare remote; use real Git for fetch/push."""
    _, destination, remote = repos
    monkeypatch.syspath_prepend(str(SCRIPTS))
    module = importlib.import_module("sync_public")

    def blob(content: bytes) -> str:
        return (
            subprocess.check_output(
                ["git", "hash-object", "-w", "--stdin"],  # noqa: S607 - Git is supplied by CI.
                input=content,
                cwd=remote,
            )
            .decode()
            .strip()
        )

    def api(endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        if endpoint == "blobs":
            assert payload["encoding"] == "base64"
            return {"sha": blob(base64.b64decode(payload["content"]))}
        if endpoint == "trees":
            git(remote, "read-tree", "--empty")
            for entry in payload["tree"]:
                sha = blob(entry["content"].encode("utf-8")) if "content" in entry else entry["sha"]
                git(remote, "update-index", "--add", "--cacheinfo", entry["mode"], sha, entry["path"])
            return {"sha": git(remote, "write-tree")}
        assert endpoint == "commits"
        # GitHub only signs when author, committer, and signature are omitted.
        assert set(payload) == {"message", "tree", "parents"}
        # The API creates the release commit directly, without an interim local commit.
        head = module.Repo(destination).head
        assert (head.commit.hexsha if head.is_valid() else None) == (payload["parents"][0] if payload["parents"] else None)
        parents = [arg for parent in payload["parents"] for arg in ["-p", parent]]
        sha = git(
            remote,
            "-c",
            "user.name=release-app[bot]",
            "-c",
            "user.email=release-app[bot]@users.noreply.github.com",
            "commit-tree",
            payload["tree"],
            *parents,
            "-m",
            payload["message"],
        )
        return {"sha": sha, "verification": {"verified": True, "reason": "valid"}}

    monkeypatch.setattr(module, "api", api)
    return module


@pytest.mark.parametrize("with_history", [False, True])
def test_sign_snapshot_and_push(repos: tuple[Path, Path, Path], signer: ModuleType, with_history: bool) -> None:
    source, destination, remote = repos
    if with_history:
        write(destination, "obsolete.txt", "delete me")
        commit(destination, "public history")
        git(destination, "push", "origin", "main")
    write(source, "src/run.sh", "#!/bin/sh\necho 'héllo'\n")
    (source / "src/run.sh").chmod(0o755)
    (source / "src/image.bin").write_bytes(b"\x00\xff\x80\r\n")
    commit(source)
    parent = git(destination, "rev-parse", "HEAD") if with_history else ""
    remote_refs = git(remote, "show-ref", "--head") if with_history else ""

    assert signer.sync_public(source, destination, "v42.0.0", dry_run=False)

    signed = git(destination, "rev-parse", "HEAD")
    assert git(destination, "log", "-1", "--format=%P") == parent
    assert git(destination, "rev-list", "--count", "HEAD") == ("2" if with_history else "1")
    assert git(destination, "log", "-1", "--format=%s") == "Release v42.0.0"
    assert (destination / "src/run.sh").read_text() == "#!/bin/sh\necho 'héllo'\n"
    assert (destination / "src/run.sh").stat().st_mode & 0o777 == 0o755
    assert (destination / "src/image.bin").read_bytes() == b"\x00\xff\x80\r\n"
    assert not (destination / "obsolete.txt").exists()
    assert not (destination / ".dagger").exists()
    assert git(destination, "rev-parse", "v42.0.0") == signed
    assert git(destination, "status", "--porcelain") == ""
    assert git(remote, "for-each-ref", "--format=%(refname)") == ("refs/heads/main" if with_history else "")
    if with_history:
        assert git(remote, "show-ref", "--head") == remote_refs
    result = run_script(source, "push_public.py", str(destination), "v42.0.0")
    assert result.returncode == 0, result.stderr
    assert git(remote, "rev-parse", "main") == signed
    assert git(remote, "rev-parse", "v42.0.0") == signed
    assert not signer.sync_public(source, destination, "v42.0.0", dry_run=False)
    assert git(destination, "rev-parse", "v42.0.0") == signed


@pytest.mark.parametrize("failure", ["tree", "signature"])
def test_signing_failure_keeps_refs(
    repos: tuple[Path, Path, Path],
    signer: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    source, destination, remote = repos
    commit(destination, "public history")
    git(destination, "push", "origin", "main")
    original = git(destination, "show-ref", "--head")
    remote_refs = git(remote, "show-ref", "--head")
    create_object = signer.api

    def fail(endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        result = create_object(endpoint, payload)
        if endpoint == "trees" and failure == "tree":
            result["sha"] = "0" * 40
        if endpoint == "commits":
            result["verification"] = {"verified": False, "reason": "unsigned"}
        return result

    monkeypatch.setattr(signer, "api", fail)
    with pytest.raises(ValueError, match=r"does not match|did not verify"):
        signer.sync_public(source, destination, "v42.0.0", dry_run=False)
    assert git(destination, "show-ref", "--head") == original
    assert git(remote, "show-ref", "--head") == remote_refs


def test_dry_run_skips_github(repos: tuple[Path, Path, Path], signer: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    source, destination, remote = repos

    def fail(endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        pytest.fail("Dry runs must not call the GitHub API")

    monkeypatch.setattr(signer, "api", fail)
    assert signer.sync_public(source, destination, "v42.0.0", dry_run=True)
    assert git(destination, "log", "-1", "--format=%s") == "Release v42.0.0"
    assert git(remote, "for-each-ref", "--format=%(refname)") == ""


def test_snapshot_and_push_retries(repos: tuple[Path, Path, Path]) -> None:
    source, destination, remote = repos
    # Export the committed version despite local edits.
    write(source, "src/untracked.py", "private draft")
    write(source, "src/typesafe_sdk/__init__.py", "uncommitted edits")
    set_version(source, "99.0.0")
    result = sync(source, destination)
    assert result.returncode == 0, result.stderr
    assert git(destination, "rev-list", "--count", "HEAD") == "1"
    assert git(destination, "log", "-1", "--format=%s") == "Release v42.0.0"
    assert (destination / "src/typesafe_sdk/__init__.py").read_text() == "# public source\n"
    assert not any(
        (destination / path).exists() for path in [".dagger", "RELEASING.md", ".releaseinclude", "src/untracked.py", ".github/workflows/CI.yml"]
    )
    head = git(destination, "rev-parse", "HEAD")
    assert git(destination, "rev-parse", "v42.0.0") == head
    assert sync(source, destination).returncode == 0
    dry_run = run_script(source, "push_public.py", str(destination), "v42.0.0", "--dry-run")
    assert dry_run.returncode == 0, dry_run.stderr
    assert git(remote, "for-each-ref", "--format=%(refname)") == ""
    for _ in range(2):
        pushed = run_script(source, "push_public.py", str(destination), "v42.0.0")
        assert pushed.returncode == 0, pushed.stderr
    assert git(remote, "rev-parse", "main") == head
    assert git(remote, "rev-parse", "v42.0.0") == head
    assert git(remote, "branch", "--list") == "* main"


def test_existing_history_deletions_and_immutable_tags(repos: tuple[Path, Path, Path]) -> None:
    source, destination, _ = repos
    write(destination, "old-private-config", "previously committed infrastructure")
    commit(destination, "existing destination history")
    assert sync(source, destination).returncode == 0
    assert not (destination / "old-private-config").exists()
    released = git(destination, "rev-parse", "HEAD")
    assert git(destination, "rev-list", "--count", "HEAD") == "2"
    write(source, "src/added.py", "new public code")
    commit(source)
    result = sync(source, destination)
    assert result.returncode != 0
    assert "different contents" in result.stderr
    assert git(destination, "rev-parse", "v42.0.0") == released
    set_version(source, "42.0.2")
    commit(source)
    assert sync(source, destination, "v42.0.2").returncode == 0
    newest = git(destination, "rev-parse", "main")
    set_version(source, "42.0.1")
    commit(source)
    result = sync(source, destination, "v42.0.1")
    assert result.returncode != 0
    assert "Refusing" in result.stderr
    git(source, "checkout", "HEAD~3")
    assert sync(source, destination).returncode == 0
    assert git(destination, "rev-parse", "main") == newest


@pytest.mark.parametrize("include", ["../private", ".git/config", "src/*", ".releaseinclude", "/src", "missing-file"])
def test_invalid_includes(repos: tuple[Path, Path, Path], include: str) -> None:
    source, destination, _ = repos
    write(source, ".releaseinclude", INCLUDES + include + "\n")
    commit(source)
    result = sync(source, destination)
    assert result.returncode != 0
    assert "Invalid public include" in result.stderr or "matches no committed files" in result.stderr
    assert git(destination, "tag", "--list") == ""


def test_unsafe_snapshots(repos: tuple[Path, Path, Path]) -> None:
    source, destination, _ = repos
    (source / "src/link").symlink_to("../RELEASING.md")
    commit(source)
    result = sync(source, destination)
    assert result.returncode != 0
    assert "Unsupported public file mode" in result.stderr
    write(destination, "keep.txt", "local work")
    result = sync(source, destination)
    assert result.returncode != 0
    assert "must be clean" in result.stderr
    assert (destination / "keep.txt").read_text() == "local work"


def test_version_mismatch(repos: tuple[Path, Path, Path]) -> None:
    source, destination, _ = repos
    result = sync(source, destination, "v42.0.1")
    assert result.returncode != 0
    assert "does not match package version" in result.stderr


def test_atomic_push_rejects_concurrent_update(repos: tuple[Path, Path, Path], signer: ModuleType) -> None:
    source, destination, remote = repos
    assert sync(source, destination).returncode == 0
    assert run_script(source, "push_public.py", str(destination), "v42.0.0").returncode == 0
    set_version(source, "42.0.1")
    commit(source)
    assert signer.sync_public(source, destination, "v42.0.1", dry_run=False)
    # Simulate a concurrent update to public main.
    competitor = source.parent / "competitor"
    git(source.parent, "clone", str(remote), str(competitor))
    git(competitor, "config", "user.name", "Test")
    git(competitor, "config", "user.email", "test@example.com")
    git(competitor, "config", "commit.gpgsign", "false")
    commit(competitor, "concurrent main change")
    git(competitor, "push", "origin", "main")
    result = run_script(source, "push_public.py", str(destination), "v42.0.1")
    assert result.returncode != 0
    assert git(remote, "tag", "--list") == "v42.0.0"
    assert git(remote, "rev-parse", "main") == git(competitor, "rev-parse", "HEAD")


def test_release_contributors(repos: tuple[Path, Path, Path], signer: ModuleType) -> None:
    source, destination, _ = repos
    write(source, "src/feature.py", "# Alice's contribution\n")
    git(source, "add", ".")
    git(
        source,
        "-c",
        "user.name=Alice",
        "-c",
        "user.email=alice@example.com",
        "commit",
        "-qm",
        "Private implementation details\n\nCo-authored-by: Bob <bob@example.com>\nCo-authored-by: Bob <bob@example.com>",
    )
    git(source, "-c", "user.name=Bob", "-c", "user.email=bob@example.com", "commit", "--allow-empty", "-qm", "More private work")

    assert signer.sync_public(source, destination, "v42.0.0", dry_run=False)
    assert git(destination, "log", "-1", "--format=%B").splitlines() == [
        "Release v42.0.0",
        "",
        "Co-authored-by: Alice <alice@example.com>",
        "Co-authored-by: Bob <bob@example.com>",
        "Co-authored-by: Test <test@example.com>",
    ]
    git(source, "tag", "v42.0.0")
    set_version(source, "42.0.1")
    git(source, "add", ".")
    git(
        source,
        "-c",
        "user.name=Carol",
        "-c",
        "user.email=carol@example.com",
        "commit",
        "-qm",
        "Next release\n\nCo-authored-by: Alice <alice@example.com>",
    )
    assert signer.sync_public(source, destination, "v42.0.1", dry_run=False)
    assert git(destination, "log", "-1", "--format=%B").splitlines() == [
        "Release v42.0.1",
        "",
        "Co-authored-by: Alice <alice@example.com>",
        "Co-authored-by: Carol <carol@example.com>",
    ]
