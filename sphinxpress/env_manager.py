"""Managed Sphinx build environment support."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import venv
from pathlib import Path

from .models import AppConfig, ProjectConfig

_FINGERPRINT_FILE = ".sphinxpress-env.json"


def prepare_build_environment(config: AppConfig, projects: list[ProjectConfig]) -> str:
    """Return the Sphinx build command for this run."""
    env = config.build.env
    if not env.enabled:
        return config.build.sphinx_build

    env.path.mkdir(parents=True, exist_ok=True)
    venv.EnvBuilder(with_pip=True).create(env.path)
    python = _venv_executable(env.path, "python")
    fingerprint = _fingerprint(config, projects)
    fingerprint_path = env.path / _FINGERPRINT_FILE

    if _read_fingerprint(fingerprint_path) != fingerprint:
        if env.upgrade_pip:
            subprocess.run(
                [str(python), "-m", "pip", "install", "--upgrade", "pip"],
                check=True,
            )
        if env.packages:
            subprocess.run(
                [str(python), "-m", "pip", "install", *env.packages],
                check=True,
            )
        fingerprint_path.write_text(
            json.dumps(fingerprint, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    return str(_venv_executable(env.path, "sphinx-build"))


def _venv_executable(venv_path: Path, name: str) -> Path:
    if sys.platform == "win32":
        suffix = ".exe" if name != "python" else ".exe"
        return venv_path / "Scripts" / f"{name}{suffix}"
    return venv_path / "bin" / name


def _read_fingerprint(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if isinstance(raw, dict):
        return raw
    return None


def _fingerprint(config: AppConfig, projects: list[ProjectConfig]) -> dict[str, object]:
    return {
        "python": config.build.env.python,
        "runtime_python": platform.python_version(),
        "packages": config.build.env.packages,
        "local_projects": [
            _local_project_fingerprint(package) for package in config.build.env.packages
        ],
        "project_names": [project.name for project in projects],
    }


def _local_project_fingerprint(package: str) -> dict[str, object] | None:
    path = Path(package)
    if not path.is_absolute() or not path.exists():
        return None
    pyproject = path / "pyproject.toml"
    if not pyproject.exists():
        return {"path": str(path), "pyproject": None}
    content = pyproject.read_bytes()
    return {
        "path": str(path),
        "pyproject": {
            "mtime_ns": pyproject.stat().st_mtime_ns,
            "sha256": hashlib.sha256(content).hexdigest(),
        },
    }
