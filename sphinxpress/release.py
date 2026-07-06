"""Release metadata helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

import tomllib

from .errors import ReleaseResolutionError
from .models import AppConfig, ProjectConfig, ReleaseMetadata


def resolve_release_metadata(
    config: AppConfig, project: ProjectConfig
) -> ReleaseMetadata:
    tag = resolve_release_tag(config, project)
    return ReleaseMetadata(tag=tag, url=build_release_url(config, project, tag))


def resolve_release_tag(config: AppConfig, project: ProjectConfig) -> str:
    strategy = project.release_strategy
    if strategy == "manual":
        if not project.release_tag:
            raise ReleaseResolutionError(
                f"Project '{project.name}' uses manual release metadata "
                f"but has no release_tag."
            )
        return project.release_tag
    if strategy == "git_tag":
        project_root = find_project_root(project)
        result = subprocess.run(
            [
                "git",
                "--no-pager",
                "-C",
                str(project_root),
                "describe",
                "--tags",
                "--abbrev=0",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            _git_out = (
                result.stderr.strip() or result.stdout.strip() or "git describe failed"
            )
            raise ReleaseResolutionError(
                f"Could not resolve git tag for project '{project.name}': {_git_out}"
            )
        return result.stdout.strip()
    if strategy == "pyproject":
        project_root = find_project_root(project)
        pyproject_path = project_root / "pyproject.toml"
        if not pyproject_path.exists():
            raise ReleaseResolutionError(
                f"Project '{project.name}' is missing "
                f"pyproject.toml at {pyproject_path}."
            )
        with pyproject_path.open("rb") as handle:
            data = tomllib.load(handle)
        version = data.get("project", {}).get("version")
        if not isinstance(version, str) or not version.strip():
            raise ReleaseResolutionError(
                f"Project '{project.name}' does not define "
                f"[project].version in {pyproject_path}."
            )
        prefix = config.release.tag_prefix
        return version if version.startswith(prefix) else f"{prefix}{version}"
    raise ReleaseResolutionError(
        f"Unsupported release strategy '{strategy}' for project '{project.name}'."
    )


def build_release_url(config: AppConfig, project: ProjectConfig, tag: str) -> str:
    return config.release.release_url_template.format(
        repo_url=project.repo_url, tag=tag
    )


def find_project_root(project: ProjectConfig) -> Path:
    for root in (project.docs_root, project.conf_dir):
        for candidate in [root, *root.parents]:
            if (candidate / "pyproject.toml").exists() or (candidate / ".git").exists():
                return candidate
    return project.docs_root.parent
