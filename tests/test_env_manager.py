from __future__ import annotations

import json
import sys
from pathlib import Path

from conftest import copy_fixture, write_config

from sphinxpress.config import load_config
from sphinxpress.env_manager import (
    build_tool_executable,
    prepare_build_environment,
)


def _venv_exe(venv_path: Path, name: str) -> Path:
    if sys.platform == "win32":
        return venv_path / "Scripts" / f"{name}.exe"
    return venv_path / "bin" / name


def _noop_logged_result():
    from sphinxpress.command_log import LoggedResult

    class _Result:
        returncode = 0
        stdout = ""
        stderr = ""

    return LoggedResult(result=_Result(), log_path=None)


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

    def fake_run_logged(command, *, log_dir, log_stem, cwd=None):
        commands.append(command)
        from sphinxpress.command_log import LoggedResult

        class _Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return LoggedResult(result=_Result(), log_path=None)

    monkeypatch.setattr("sphinxpress.env_manager.venv.EnvBuilder.create", fake_create)
    monkeypatch.setattr("sphinxpress.env_manager.run_logged_command", fake_run_logged)

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


def test_enabled_env_converts_editable_project_paths_to_pinned_releases(
    monkeypatch, tmp_path
):
    project_root = copy_fixture(tmp_path)
    config_path = write_config(
        tmp_path,
        projects=[
            {
                "name": "booktx",
                "docs_root": str(project_root / "docs"),
                "release_tag": "v0.4.0",
            }
        ],
        extra=f"""
        [build.env]
        enabled = true
        path = ".sphinxpress/venv"
        upgrade_pip = false
        packages = ["sphinx>=7", "-e", "{project_root}"]
        """,
    )
    config = load_config(config_path)
    commands = []

    def fake_create(self, path):
        _venv_exe(Path(path), "python").parent.mkdir(parents=True, exist_ok=True)
        _venv_exe(Path(path), "python").write_text("", encoding="utf-8")
        _venv_exe(Path(path), "sphinx-build").write_text("", encoding="utf-8")

    def fake_run_logged(command, *, log_dir, log_stem, cwd=None):
        commands.append(command)
        return _noop_logged_result()

    monkeypatch.setattr("sphinxpress.env_manager.venv.EnvBuilder.create", fake_create)
    monkeypatch.setattr("sphinxpress.env_manager.run_logged_command", fake_run_logged)

    prepare_build_environment(config, config.projects)

    assert commands == [
        [
            str(_venv_exe(config.build.env.path, "python")),
            "-m",
            "pip",
            "install",
            "sphinx>=7",
            "booktx==0.4.0",
        ]
    ]
    fingerprint = json.loads(
        (config.build.env.path / ".sphinxpress-env.json").read_text(encoding="utf-8")
    )
    assert fingerprint["packages"] == ["sphinx>=7", "booktx==0.4.0"]


def test_editable_forms_preserve_project_extras(monkeypatch, tmp_path):
    project_root = copy_fixture(tmp_path)
    config_path = write_config(
        tmp_path,
        projects=[
            {
                "name": "booktx",
                "docs_root": str(project_root / "docs"),
                "release_tag": "v0.4.0",
            }
        ],
        extra=f"""
        [build.env]
        enabled = true
        path = ".sphinxpress/venv"
        upgrade_pip = false
        packages = [
          "--editable", "{project_root / 'docs'}[docs]",
          "--editable={project_root}[pdf]",
        ]
        """,
    )
    config = load_config(config_path)
    commands = []

    def fake_create(self, path):
        _venv_exe(Path(path), "python").parent.mkdir(parents=True, exist_ok=True)
        _venv_exe(Path(path), "python").write_text("", encoding="utf-8")
        _venv_exe(Path(path), "sphinx-build").write_text("", encoding="utf-8")

    def fake_run_logged(command, *, log_dir, log_stem, cwd=None):
        commands.append(command)
        return _noop_logged_result()

    monkeypatch.setattr("sphinxpress.env_manager.venv.EnvBuilder.create", fake_create)
    monkeypatch.setattr("sphinxpress.env_manager.run_logged_command", fake_run_logged)

    prepare_build_environment(config, config.projects)

    assert commands == [
        [
            str(_venv_exe(config.build.env.path, "python")),
            "-m",
            "pip",
            "install",
            "booktx[docs]==0.4.0",
            "booktx[pdf]==0.4.0",
        ]
    ]

def test_unmapped_editable_build_env_package_is_rejected(monkeypatch, tmp_path):
    project_root = copy_fixture(tmp_path)
    config_path = write_config(
        tmp_path,
        projects=[
            {
                "name": "booktx",
                "docs_root": str(project_root / "docs"),
                "release_tag": "v0.4.0",
            }
        ],
        extra=f"""
        [build.env]
        enabled = true
        packages = ["-e", "{tmp_path / 'not-a-project'}"]
        """,
    )
    config = load_config(config_path)

    def fake_create(self, path):
        _venv_exe(Path(path), "python").parent.mkdir(parents=True, exist_ok=True)
        _venv_exe(Path(path), "python").write_text("", encoding="utf-8")
        _venv_exe(Path(path), "sphinx-build").write_text("", encoding="utf-8")

    monkeypatch.setattr("sphinxpress.env_manager.venv.EnvBuilder.create", fake_create)

    import pytest

    from sphinxpress.errors import ValidationError

    with pytest.raises(ValidationError, match="no longer install editable"):
        prepare_build_environment(config, config.projects)


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

    def fake_run_logged(*args, **kwargs):
        return _noop_logged_result()

    monkeypatch.setattr("sphinxpress.env_manager.venv.EnvBuilder.create", fake_create)
    monkeypatch.setattr("sphinxpress.env_manager.run_logged_command", fake_run_logged)
    prepare_build_environment(config, config.projects)

    def fail_run(*args, **kwargs):
        raise AssertionError("pip install should be skipped for matching fingerprint")

    monkeypatch.setattr("sphinxpress.env_manager.run_logged_command", fail_run)

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


def test_env_manager_logs_pip_install_failure(monkeypatch, tmp_path):
    project_root = copy_fixture(tmp_path)
    config_path = write_config(
        tmp_path,
        projects=[{"name": "booktx", "docs_root": str(project_root / "docs")}],
        extra="""
        [build.env]
        enabled = true
        path = ".sphinxpress/venv"
        packages = ["sphinx>=7", "myst-parser"]
        """,
    )
    config = load_config(config_path)

    def fake_create(self, path):
        _venv_exe(Path(path), "python").parent.mkdir(parents=True, exist_ok=True)
        _venv_exe(Path(path), "python").write_text("", encoding="utf-8")
        _venv_exe(Path(path), "sphinx-build").write_text("", encoding="utf-8")

    class _Result:
        def __init__(self):
            self.returncode = 1
            self.stdout = "out"
            self.stderr = "err"

    from sphinxpress.command_log import LoggedResult

    monkeypatch.setattr("sphinxpress.env_manager.venv.EnvBuilder.create", fake_create)
    monkeypatch.setattr(
        "sphinxpress.env_manager.run_logged_command",
        lambda *args, **kwargs: LoggedResult(
            result=_Result(),
            log_path=config.build.log_dir / "latest-env-pip-install.log",
        ),
    )

    import pytest

    from sphinxpress.errors import ValidationError

    with pytest.raises(ValidationError, match="env-pip-install"):
        prepare_build_environment(config, config.projects)
