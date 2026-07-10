from __future__ import annotations

import json
import sys
from pathlib import Path

from conftest import copy_fixture, write_config

from sphinxpress.config import load_config
from sphinxpress.env_manager import build_tool_executable, prepare_build_environment


def _venv_exe(venv_path: Path, name: str) -> Path:
    if sys.platform == "win32":
        return venv_path / "Scripts" / f"{name}.exe"
    return venv_path / "bin" / name


def test_disabled_env_returns_configured_sphinx_build(monkeypatch, minimal_config_path):
    config = load_config(minimal_config_path)

    def fail_create(*args, **kwargs):
        raise AssertionError("venv should not be created when env is disabled")

    monkeypatch.setattr("sphinxpress.env_manager.venv.EnvBuilder.create", fail_create)

    assert prepare_build_environment(config, config.projects) == "sphinx-build"
    assert build_tool_executable(config, "weasyprint") == "weasyprint"


def test_enabled_env_creates_venv_installs_packages_and_returns_local_sphinx_build(
    monkeypatch, tmp_path
):
    project_root = copy_fixture(tmp_path)
    config_path = write_config(
        tmp_path,
        projects=[{"name": "booktx", "docs_root": str(project_root / "docs")}],
        extra="""
        [build.env]
        enabled = true
        path = ".sphinxpress/venv"
        upgrade_pip = true
        packages = ["sphinx>=7", "myst-parser"]
        """,
    )
    config = load_config(config_path)
    created = []
    commands = []

    def fake_create(self, path):
        created.append(path)
        _venv_exe(Path(path), "python").parent.mkdir(parents=True, exist_ok=True)
        _venv_exe(Path(path), "python").write_text("", encoding="utf-8")
        _venv_exe(Path(path), "sphinx-build").write_text("", encoding="utf-8")

    def fake_run(command, *, check):
        commands.append(command)

    monkeypatch.setattr("sphinxpress.env_manager.venv.EnvBuilder.create", fake_create)
    monkeypatch.setattr("sphinxpress.env_manager.subprocess.run", fake_run)

    sphinx_build = prepare_build_environment(config, config.projects)

    assert created == [config.build.env.path]
    assert sphinx_build == str(_venv_exe(config.build.env.path, "sphinx-build"))
    assert commands == [
        [
            str(_venv_exe(config.build.env.path, "python")),
            "-m",
            "pip",
            "install",
            "--upgrade",
            "pip",
        ],
        [
            str(_venv_exe(config.build.env.path, "python")),
            "-m",
            "pip",
            "install",
            "sphinx>=7",
            "myst-parser",
        ],
    ]
    fingerprint = json.loads(
        (config.build.env.path / ".sphinxpress-env.json").read_text(encoding="utf-8")
    )
    assert fingerprint["packages"] == ["sphinx>=7", "myst-parser"]


def test_enabled_env_skips_install_when_fingerprint_matches(monkeypatch, tmp_path):
    project_root = copy_fixture(tmp_path)
    config_path = write_config(
        tmp_path,
        projects=[{"name": "booktx", "docs_root": str(project_root / "docs")}],
        extra="""
        [build.env]
        enabled = true
        packages = ["sphinx>=7"]
        """,
    )
    config = load_config(config_path)

    def fake_create(self, path):
        _venv_exe(Path(path), "python").parent.mkdir(parents=True, exist_ok=True)
        _venv_exe(Path(path), "python").write_text("", encoding="utf-8")
        _venv_exe(Path(path), "sphinx-build").write_text("", encoding="utf-8")

    monkeypatch.setattr("sphinxpress.env_manager.venv.EnvBuilder.create", fake_create)
    monkeypatch.setattr(
        "sphinxpress.env_manager.subprocess.run", lambda *args, **kwargs: None
    )
    prepare_build_environment(config, config.projects)

    def fail_run(*args, **kwargs):
        raise AssertionError("pip install should be skipped for matching fingerprint")

    monkeypatch.setattr("sphinxpress.env_manager.subprocess.run", fail_run)

    assert prepare_build_environment(config, config.projects) == str(
        _venv_exe(config.build.env.path, "sphinx-build")
    )


def test_project_scoped_managed_env_is_rejected_for_v0_1(tmp_path):
    project_root = copy_fixture(tmp_path)
    config_path = write_config(
        tmp_path,
        projects=[{"name": "booktx", "docs_root": str(project_root / "docs")}],
        extra="""
        [build.env]
        enabled = true
        scope = "project"
        """,
    )

    import pytest

    from sphinxpress.errors import ConfigError

    with pytest.raises(ConfigError, match="build.env.scope.*shared"):
        load_config(config_path)


def test_build_tool_executable_uses_managed_venv_when_enabled(tmp_path):
    project_root = copy_fixture(tmp_path)
    config_path = write_config(
        tmp_path,
        projects=[{"name": "booktx", "docs_root": str(project_root / "docs")}],
        extra="""
        [build.env]
        enabled = true
        path = ".sphinxpress/venv"
        """,
    )
    config = load_config(config_path)

    assert build_tool_executable(config, "weasyprint") == str(
        _venv_exe(config.build.env.path, "weasyprint")
    )
