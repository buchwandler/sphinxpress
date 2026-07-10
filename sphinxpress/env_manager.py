"""Managed Sphinx build environment support."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import venv
from pathlib import Path

from .command_log import run_logged_command
from .errors import ValidationError
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
            _run_pip(
                config,
                [str(python), "-m", "pip", "install", "--upgrade", "pip"],
                "env-pip-upgrade",
            )
        if env.packages:
            _run_pip(
                config,
                [str(python), "-m", "pip", "install", *env.packages],
                "env-pip-install",
            )
        fingerprint_path.write_text(
            json.dumps(fingerprint, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    return str(_venv_executable(env.path, "sphinx-build"))


def _run_pip(config: AppConfig, command: list[str], log_stem: str) -> None:
    logged = run_logged_command(
        command,
        log_dir=config.build.log_dir,
        log_stem=log_stem,
    )
    result = logged.result
    if result.returncode != 0:
        detail = "\n".join(
            part for part in [result.stdout.strip(), result.stderr.strip()] if part
        )
        log_hint = f"\nLog: {logged.log_path}" if logged.log_path else ""
        raise ValidationError(
            "Managed build environment setup failed during pip command "
            f"({log_stem}).{log_hint}\n{detail}".rstrip()
        )


def build_tool_executable(config: AppConfig, name: str) -> str:
    if config.build.env.enabled:
        return str(_venv_executable(config.build.env.path, name))
    return name


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
