from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

import pytest

from sphinxpress.config import load_config
from sphinxpress.errors import ReleaseResolutionError
from sphinxpress.source_manager import resolve_site_targets


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _create_versioned_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "booktx"
    docs = repo / "docs"
    package = repo / "src" / "booktx"
    package.mkdir(parents=True)
    docs.mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "booktx"\nversion = "1.0.0"\n',
        encoding="utf-8",
    )
    (docs / "conf.py").write_text(
        "project = 'booktx'\nextensions = []\nroot_doc = 'index'\n",
        encoding="utf-8",
    )
    (docs / "index.rst").write_text("Release docs\n============\n", encoding="utf-8")
    (package / "__init__.py").write_text(
        "def version() -> str:\n    return 'release'\n"
    )
    _git(repo, "init")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "release")
    _git(repo, "tag", "v1.0.0")
    (docs / "index.rst").write_text("Main docs\n=========\n", encoding="utf-8")
    (package / "__init__.py").write_text("def version() -> str:\n    return 'main'\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "main")
    _git(repo, "branch", "-M", "main")
    return repo


def _write_versioned_config(
    tmp_path: Path,
    docs_root: Path,
    *,
    release_strategy: str = "git_tag",
    release_tag: str | None = None,
    main_ref: str = "main",
) -> Path:
    release_tag_line = f'release_tag = "{release_tag}"\n' if release_tag else ""
    config_path = tmp_path / "sphinxpress.toml"
    config_path.write_text(
        textwrap.dedent(
            f"""
            [site]
            root = "."
            base_url = "https://example.com"
            tools_dir = "tools"
            nav_data_dir = "_data/tool_nav"
            layout = "tool-doc"
            title = "Example Docs"

            [site.versioning]
            enabled = true
            default = "release"

            [[site.versioning.variants]]
            name = "release"
            label = "Latest release"
            source = "release"
            url_segment = ""

            [[site.versioning.variants]]
            name = "main"
            label = "Current main"
            source = "git_ref"
            ref = "{main_ref}"
            url_segment = "main"

            [book]
            title = "Example Book"
            author = "Test Author"
            language = "en"
            version = "0.1.0"
            copyright = "2026, Test Author"
            project_order = ["booktx"]
            docs_variant = "release"

            [pdf]
            builder = "latexpdf"
            output = "dist/example.pdf"

            [epub]
            builder = "epub"
            output = "dist/example.epub"

            [release]
            tag_prefix = "v"
            release_url_template = "{{repo_url}}/releases/tag/{{tag}}"

            [[projects]]
            name = "booktx"
            title = "booktx"
            docs_root = "{str(docs_root).replace(chr(92), "/")}"
            conf_dir = "{str(docs_root).replace(chr(92), "/")}"
            root_doc = "index"
            repo_url = "https://github.com/example/booktx"
            release_strategy = "{release_strategy}"
            {release_tag_line}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    return config_path


def test_source_manager_resolves_release_and_main_targets(tmp_path):
    repo = _create_versioned_repo(tmp_path)
    config = load_config(_write_versioned_config(tmp_path, repo / "docs"))

    targets = resolve_site_targets(config, config.projects)
    by_name = {target.variant.name: target for target in targets}

    assert set(by_name) == {"release", "main"}
    assert by_name["release"].resolved_ref == "v1.0.0"
    assert by_name["main"].resolved_ref == "main"
    assert by_name["release"].commit_sha != by_name["main"].commit_sha
    assert by_name["release"].source_root != by_name["main"].source_root
    assert "Release docs" in (by_name["release"].docs_root / "index.rst").read_text(
        encoding="utf-8"
    )
    assert "Main docs" in (by_name["main"].docs_root / "index.rst").read_text(
        encoding="utf-8"
    )
    assert _git(repo, "status", "--short") == ""


def test_source_manager_reuses_cached_worktree_for_same_commit(tmp_path):
    repo = _create_versioned_repo(tmp_path)
    config = load_config(_write_versioned_config(tmp_path, repo / "docs"))

    first = resolve_site_targets(config, config.projects)
    second = resolve_site_targets(config, config.projects)

    first_by_name = {target.variant.name: target for target in first}
    second_by_name = {target.variant.name: target for target in second}
    assert first_by_name["release"].source_root == second_by_name["release"].source_root
    assert first_by_name["main"].source_root == second_by_name["main"].source_root
    assert first_by_name["main"].commit_sha == second_by_name["main"].commit_sha


def test_source_manager_replaces_cached_worktree_when_ref_moves(tmp_path):
    repo = _create_versioned_repo(tmp_path)
    config = load_config(_write_versioned_config(tmp_path, repo / "docs"))

    first = {
        target.variant.name: target
        for target in resolve_site_targets(config, config.projects)
    }
    (repo / "docs" / "index.rst").write_text(
        "Updated main docs\n=================\n", encoding="utf-8"
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "update main")
    second = {
        target.variant.name: target
        for target in resolve_site_targets(config, config.projects)
    }

    assert first["main"].source_root == second["main"].source_root
    assert first["main"].commit_sha != second["main"].commit_sha
    assert "Updated main docs" in (second["main"].docs_root / "index.rst").read_text(
        encoding="utf-8"
    )


def test_source_manager_rejects_missing_git_ref(tmp_path):
    repo = _create_versioned_repo(tmp_path)
    config = load_config(
        _write_versioned_config(tmp_path, repo / "docs", main_ref="missing-branch")
    )

    with pytest.raises(
        ReleaseResolutionError,
        match="variant 'main'.*project 'booktx'",
    ):
        resolve_site_targets(config, config.projects)


def test_source_manager_rejects_docs_root_outside_repo(tmp_path, monkeypatch):
    repo = _create_versioned_repo(tmp_path)
    outside = tmp_path / "outside-docs"
    outside.mkdir()
    (outside / "index.rst").write_text("Outside docs\n============\n", encoding="utf-8")
    config_path = tmp_path / "sphinxpress.toml"
    config_path.write_text(
        textwrap.dedent(
            f"""
            [site]
            root = "."
            base_url = "https://example.com"
            tools_dir = "tools"
            nav_data_dir = "_data/tool_nav"
            layout = "tool-doc"
            title = "Example Docs"

            [site.versioning]
            enabled = true
            default = "release"

            [[site.versioning.variants]]
            name = "release"
            label = "Latest release"
            source = "release"
            url_segment = ""

            [book]
            title = "Example Book"
            author = "Test Author"
            language = "en"
            version = "0.1.0"
            copyright = "2026, Test Author"
            project_order = ["booktx"]
            docs_variant = "release"

            [pdf]
            builder = "latexpdf"
            output = "dist/example.pdf"

            [epub]
            builder = "epub"
            output = "dist/example.epub"

            [release]
            tag_prefix = "v"
            release_url_template = "{{repo_url}}/releases/tag/{{tag}}"

            [[projects]]
            name = "booktx"
            title = "booktx"
            docs_root = "{str(outside).replace(chr(92), "/")}"
            conf_dir = "{str(repo / "docs").replace(chr(92), "/")}"
            root_doc = "index"
            repo_url = "https://github.com/example/booktx"
            release_strategy = "git_tag"
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    config = load_config(config_path)
    monkeypatch.setattr(
        "sphinxpress.source_manager.find_project_root", lambda project: repo
    )

    with pytest.raises(
        ReleaseResolutionError, match="must stay within the project root"
    ):
        resolve_site_targets(config, config.projects)


def test_source_manager_rejects_missing_release_tag_without_fallback(tmp_path):
    repo = _create_versioned_repo(tmp_path)
    config = load_config(
        _write_versioned_config(
            tmp_path,
            repo / "docs",
            release_strategy="manual",
            release_tag="v9.9.9",
        )
    )

    with pytest.raises(
        ReleaseResolutionError,
        match="variant 'release'.*project 'booktx'",
    ):
        resolve_site_targets(config, config.projects)
