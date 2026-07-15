from __future__ import annotations

import os
from pathlib import Path

import pytest

from sphinxpress.command_log import LoggedResult
from sphinxpress.errors import SphinxBuildError
from sphinxpress.sphinx_runner import build_sphinx_command, run_sphinx


def test_sphinx_runner_builds_json_for_minimal_project(tmp_path, minimal_project_root):
    out_dir = tmp_path / "out"
    doctree_dir = tmp_path / "doctrees"

    run_sphinx(
        builder="json",
        conf_dir=minimal_project_root / "docs",
        src_dir=minimal_project_root / "docs",
        out_dir=out_dir,
        doctree_dir=doctree_dir,
        fail_on_warning=True,
    )

    assert (out_dir / "index.fjson").exists()


def test_sphinx_runner_adds_warning_as_error_when_configured():
    command = build_sphinx_command(
        builder="json",
        conf_dir=Path("/tmp/conf"),
        src_dir=Path("/tmp/src"),
        out_dir=Path("/tmp/out"),
        doctree_dir=Path("/tmp/doctrees"),
        fail_on_warning=True,
    )

    assert "-W" in command


def test_sphinx_runner_latexpdf_uses_dash_M_not_dash_b():
    command = build_sphinx_command(
        builder="latexpdf",
        conf_dir=Path("/tmp/conf"),
        src_dir=Path("/tmp/src"),
        out_dir=Path("/tmp/build"),
        doctree_dir=Path("/tmp/doctrees"),
        fail_on_warning=False,
    )

    assert command[1:3] == ["-M", "latexpdf"]
    assert "-b" not in command


def test_run_sphinx_writes_failure_log_and_mentions_path(
    tmp_path, monkeypatch, minimal_project_root
):
    log_dir = tmp_path / "logs"

    class _Result:
        def __init__(self, returncode, stdout, stderr):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    monkeypatch.setattr(
        "sphinxpress.sphinx_runner.run_logged_command",
        lambda *args, **kwargs: LoggedResult(
            result=_Result(1, "out", "err"), log_path=log_dir / "latest-x.log"
        ),
    )

    with pytest.raises(SphinxBuildError, match="Log: "):
        run_sphinx(
            builder="json",
            conf_dir=minimal_project_root / "docs",
            src_dir=minimal_project_root / "docs",
            out_dir=tmp_path / "out",
            doctree_dir=tmp_path / "doctrees",
            fail_on_warning=True,
            log_dir=log_dir,
            log_stem="book-pdf-singlehtml",
        )


def test_run_sphinx_writes_success_log(tmp_path, minimal_project_root):
    out_dir = tmp_path / "out"
    doctree_dir = tmp_path / "doctrees"
    log_dir = tmp_path / "logs"

    run_sphinx(
        builder="json",
        conf_dir=minimal_project_root / "docs",
        src_dir=minimal_project_root / "docs",
        out_dir=out_dir,
        doctree_dir=doctree_dir,
        fail_on_warning=True,
        log_dir=log_dir,
        log_stem="site-booktx-json",
    )

    latest = log_dir / "latest-site-booktx-json.log"
    assert latest.exists()
    assert "returncode: 0" in latest.read_text(encoding="utf-8")


def test_run_sphinx_passes_target_environment(
    monkeypatch, tmp_path, minimal_project_root
):
    captured = {}

    class _Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run_logged_command(command, **kwargs):
        captured["command"] = command
        captured["env"] = kwargs["env"]
        return LoggedResult(result=_Result(), log_path=None)

    monkeypatch.setattr(
        "sphinxpress.sphinx_runner.run_logged_command", fake_run_logged_command
    )
    python_paths = [Path("/workspace/booktx"), Path("/workspace/booktx/src")]
    expected_pythonpath = os.pathsep.join(str(path) for path in python_paths)

    run_sphinx(
        builder="json",
        conf_dir=minimal_project_root / "docs",
        src_dir=minimal_project_root / "docs",
        out_dir=tmp_path / "out",
        doctree_dir=tmp_path / "doctrees",
        fail_on_warning=True,
        python_paths=python_paths,
        environment={
            "SPHINXPRESS_DOCS_PROJECT": "booktx",
            "SPHINXPRESS_DOCS_VARIANT": "main",
            "SPHINXPRESS_DOCS_REF": "main",
            "SPHINXPRESS_DOCS_COMMIT": "abc1234",
        },
    )

    env = captured["env"]
    assert env["SPHINXPRESS_DOCS_PROJECT"] == "booktx"
    assert env["SPHINXPRESS_DOCS_VARIANT"] == "main"
    assert env["SPHINXPRESS_DOCS_REF"] == "main"
    assert env["SPHINXPRESS_DOCS_COMMIT"] == "abc1234"
    assert env["PYTHONPATH"].startswith(expected_pythonpath)


def test_run_sphinx_logs_safe_environment_entries(tmp_path, minimal_project_root):
    out_dir = tmp_path / "out"
    doctree_dir = tmp_path / "doctrees"
    log_dir = tmp_path / "logs"
    python_paths = [Path("/workspace/booktx"), Path("/workspace/booktx/src")]
    expected_pythonpath = os.pathsep.join(str(path) for path in python_paths)

    run_sphinx(
        builder="json",
        conf_dir=minimal_project_root / "docs",
        src_dir=minimal_project_root / "docs",
        out_dir=out_dir,
        doctree_dir=doctree_dir,
        fail_on_warning=True,
        log_dir=log_dir,
        log_stem="site-booktx-main-json",
        python_paths=python_paths,
        environment={
            "SPHINXPRESS_DOCS_PROJECT": "booktx",
            "SPHINXPRESS_DOCS_VARIANT": "main",
            "SPHINXPRESS_DOCS_REF": "main",
            "SPHINXPRESS_DOCS_COMMIT": "abc1234",
        },
    )

    latest = log_dir / "latest-site-booktx-main-json.log"
    content = latest.read_text(encoding="utf-8")
    assert "SPHINXPRESS_DOCS_PROJECT=booktx" in content
    assert "SPHINXPRESS_DOCS_VARIANT=main" in content
    assert "SPHINXPRESS_DOCS_REF=main" in content
    assert "SPHINXPRESS_DOCS_COMMIT=abc1234" in content
    assert f"PYTHONPATH={expected_pythonpath}" in content
