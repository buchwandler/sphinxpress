"""Managed Sphinx build environment support."""

from __future__ import annotations

import json
import platform
import sys
import venv
from pathlib import Path

from .command_log import run_logged_command
from .errors import ValidationError
from .models import AppConfig, ProjectConfig
from .release import find_project_root, resolve_release_tag

_FINGERPRINT_FILE = ".sphinxpress-env.json"


def prepare_build_environment(config: AppConfig, projects: list[ProjectConfig]) -> str:
    """Return the Sphinx build command for this run."""
    env = config.build.env
    if not env.enabled:
        return config.build.sphinx_build

    env.path.mkdir(parents=True, exist_ok=True)
    venv.EnvBuilder(with_pip=True).create(env.path)
    python = _venv_executable(env.path, "python")
    install_packages = _resolved_install_packages(config, projects)
    fingerprint = _fingerprint(config, projects, install_packages)
    fingerprint_path = env.path / _FINGERPRINT_FILE

    if _read_fingerprint(fingerprint_path) != fingerprint:
        if env.upgrade_pip:
            _run_pip(
                config,
                [str(python), "-m", "pip", "install", "--upgrade", "pip"],
                "env-pip-upgrade",
            )
        if install_packages:
            _run_pip(
                config,
                [str(python), "-m", "pip", "install", *install_packages],
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


def _fingerprint(
    config: AppConfig,
    projects: list[ProjectConfig],
    install_packages: list[str],
) -> dict[str, object]:
    return {
        "python": config.build.env.python,
        "runtime_python": platform.python_version(),
        "packages": install_packages,
        "project_names": [project.name for project in projects],
    }


def _resolved_install_packages(
    config: AppConfig, projects: list[ProjectConfig]
) -> list[str]:
    """Return pip install arguments without editable local installs.

    Editable project paths in ``[build.env].packages`` are converted to exact
    package requirements using the configured project release tag. This keeps
    the temporary build venv reproducible and prevents pip from mixing local
    development versions with released dependency constraints.
    """
    packages = config.build.env.packages
    project_paths = _project_path_index(projects)
    resolved: list[str] = []
    index = 0
    while index < len(packages):
        package = packages[index]
        if package in {"-e", "--editable"}:
            if index + 1 >= len(packages):
                raise ValidationError(
                    f"Managed build environment package '{package}' requires a path."
                )
            resolved.append(
                _pinned_requirement_for_editable(
                    config,
                    package_value=packages[index + 1],
                    project_paths=project_paths,
                )
            )
            index += 2
            continue
        if package.startswith("--editable="):
            resolved.append(
                _pinned_requirement_for_editable(
                    config,
                    package_value=package.split("=", 1)[1],
                    project_paths=project_paths,
                )
            )
            index += 1
            continue
        resolved.append(package)
        index += 1
    return resolved


def _project_path_index(projects: list[ProjectConfig]) -> dict[Path, ProjectConfig]:
    indexed: dict[Path, ProjectConfig] = {}
    for project in projects:
        project_root = find_project_root(project).resolve()
        for path in {
            project_root,
            project.docs_root.resolve(),
            project.conf_dir.resolve(),
            project.docs_root.parent.resolve(),
            project.conf_dir.parent.resolve(),
        }:
            indexed[path] = project
    return indexed


def _pinned_requirement_for_editable(
    config: AppConfig,
    *,
    package_value: str,
    project_paths: dict[Path, ProjectConfig],
) -> str:
    path_value, extras = _split_editable_extras(package_value)
    path = Path(path_value)
    if not path.is_absolute():
        path = (config.config_path.parent / path).resolve()
    else:
        path = path.resolve()

    project = project_paths.get(path)
    if project is None:
        raise ValidationError(
            "Managed build environments no longer install editable local paths. "
            f"Could not map editable path '{package_value}' to a configured "
            "project. Replace it with an exact requirement such as "
            "'package==version'."
        )

    tag = resolve_release_tag(config, project)
    version = _version_from_tag(config, tag)
    return f"{project.name}{extras}=={version}"


def _split_editable_extras(package_value: str) -> tuple[str, str]:
    if package_value.endswith("]") and "[" in package_value:
        path_value, extras = package_value.rsplit("[", 1)
        return path_value, f"[{extras}"
    return package_value, ""


def _version_from_tag(config: AppConfig, tag: str) -> str:
    prefix = config.release.tag_prefix
    if prefix and tag.startswith(prefix):
        version = tag[len(prefix) :]
    else:
        version = tag
    if not version:
        raise ValidationError(f"Release tag '{tag}' did not contain a package version.")
    return version
