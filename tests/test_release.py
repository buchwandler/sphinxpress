from __future__ import annotations

import subprocess

from conftest import copy_fixture, write_config

from sphinxpress.config import load_config
from sphinxpress.release import build_release_url, resolve_release_tag


def test_release_manual(tmp_path, minimal_project_root):
    config_path = write_config(
        tmp_path,
        projects=[
            {
                "name": "booktx",
                "docs_root": str(minimal_project_root / "docs"),
                "release_tag": "v0.4.0",
            }
        ],
    )
    config = load_config(config_path)

    assert resolve_release_tag(config, config.projects[0]) == "v0.4.0"


def test_release_git_tag(tmp_path):
    project_root = copy_fixture(tmp_path)
    subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=project_root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=project_root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "add", "."], cwd=project_root, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=project_root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "tag", "v0.4.1"], cwd=project_root, check=True, capture_output=True
    )
    config_path = write_config(
        tmp_path,
        projects=[
            {
                "name": "booktx",
                "docs_root": str(project_root / "docs"),
                "release_strategy": "git_tag",
            }
        ],
    )
    config = load_config(config_path)

    assert resolve_release_tag(config, config.projects[0]) == "v0.4.1"


def test_release_pyproject_version(tmp_path):
    project_root = copy_fixture(tmp_path)
    (project_root / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.7.0"\n',
        encoding="utf-8",
    )
    config_path = write_config(
        tmp_path,
        projects=[
            {
                "name": "booktx",
                "docs_root": str(project_root / "docs"),
                "release_strategy": "pyproject",
            }
        ],
    )
    config = load_config(config_path)

    assert resolve_release_tag(config, config.projects[0]) == "v0.7.0"


def test_release_url_template(tmp_path, minimal_project_root):
    config_path = write_config(
        tmp_path,
        projects=[
            {
                "name": "booktx",
                "docs_root": str(minimal_project_root / "docs"),
                "release_tag": "v0.4.0",
            }
        ],
    )
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            'release_url_template = "{repo_url}/releases/tag/{tag}"',
            'release_url_template = "{repo_url}/archive/{tag}.zip"',
        ),
        encoding="utf-8",
    )
    config = load_config(config_path)

    assert (
        build_release_url(config, config.projects[0], "v0.4.0")
        == "https://example.com/booktx/archive/v0.4.0.zip"
    )
