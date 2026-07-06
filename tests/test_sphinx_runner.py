from __future__ import annotations

from pathlib import Path

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
