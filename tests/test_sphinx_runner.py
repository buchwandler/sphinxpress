from __future__ import annotations

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
