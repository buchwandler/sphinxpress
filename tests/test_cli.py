from __future__ import annotations

from typer.testing import CliRunner

from sphinxpress import cli

from conftest import write_config

runner = CliRunner()


def test_cli_list_projects(minimal_config_path):
    result = runner.invoke(cli.app, ["--config", str(minimal_config_path), "list"])

    assert result.exit_code == 0
    assert "booktx" in result.stdout
    assert "v0.4.0" in result.stdout


def test_cli_check_passes_for_fake_sphinx_project(monkeypatch, minimal_config_path):
    monkeypatch.setattr(cli, "run_check", lambda config, projects: None)

    result = runner.invoke(cli.app, ["--config", str(minimal_config_path), "check"])

    assert result.exit_code == 0
    assert "Check passed." in result.stdout


def test_cli_rejects_unknown_project(minimal_config_path):
    result = runner.invoke(
        cli.app,
        ["--config", str(minimal_config_path), "build-site", "--project", "missing"],
    )

    assert result.exit_code == 1
    assert "Unknown project 'missing'." in result.stderr


def test_cli_add_project(tmp_path, minimal_project_root):
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

    result = runner.invoke(
        cli.app,
        [
            "--config",
            str(config_path),
            "add-project",
            "--name",
            "newtool",
            "--docs",
            str(minimal_project_root / "docs"),
            "--repo",
            "https://example.com/newtool",
        ],
    )

    assert result.exit_code == 0
    assert 'name = "newtool"' in config_path.read_text(encoding="utf-8")
