from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

from conftest import write_config
from typer.testing import CliRunner

from sphinxpress import cli
from sphinxpress.models import ProjectConfig, ResolvedSiteTarget, SiteVariantConfig

runner = CliRunner()


def _write_versioned_config(tmp_path: Path, docs_root: Path) -> Path:
    config_path = tmp_path / "sphinxpress.toml"
    config_path.write_text(
        textwrap.dedent(
            f"""
            [site]
            root = "."
            base_url = "https://example.com"
            tools_dir = "tools"
            nav_data_dir = "_data/tool_nav"
            layout = "tool-doc"
            title = "Example Docs"

            [site.versioning]
            enabled = true
            default = "release"

            [[site.versioning.variants]]
            name = "release"
            label = "Latest release"
            source = "working_tree"
            url_segment = ""

            [[site.versioning.variants]]
            name = "main"
            label = "Current main"
            source = "git_ref"
            ref = "main"
            url_segment = "main"

            [book]
            title = "Example Book"
            author = "Test Author"
            language = "en"
            version = "0.1.0"
            copyright = "2026, Test Author"
            project_order = ["booktx"]
            docs_variant = "release"

            [pdf]
            builder = "latexpdf"
            output = "dist/example.pdf"

            [epub]
            builder = "epub"
            output = "dist/example.epub"

            [release]
            tag_prefix = "v"
            release_url_template = "{{repo_url}}/releases/tag/{{tag}}"

            [[projects]]
            name = "booktx"
            title = "booktx"
            docs_root = "{str(docs_root).replace(chr(92), "/")}"
            conf_dir = "{str(docs_root).replace(chr(92), "/")}"
            root_doc = "index"
            repo_url = "https://example.com/booktx"
            release_strategy = "manual"
            release_tag = "v0.4.0"
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    return config_path


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


def test_cli_list_shows_variants_when_versioning_enabled(
    tmp_path, minimal_project_root, monkeypatch
):
    config_path = _write_versioned_config(tmp_path, minimal_project_root / "docs")

    def fake_targets(config, projects):
        project = ProjectConfig(
            name="booktx",
            title="booktx",
            docs_root=minimal_project_root / "docs",
            conf_dir=minimal_project_root / "docs",
            root_doc="index",
            repo_url="https://example.com/booktx",
            release_strategy="manual",
            release_tag="v0.4.0",
        )
        return [
            ResolvedSiteTarget(
                project=project,
                variant=SiteVariantConfig(
                    name="release",
                    label="Latest release",
                    source="release",
                    url_segment="",
                ),
                source_root=minimal_project_root,
                docs_root=minimal_project_root / "docs",
                conf_dir=minimal_project_root / "docs",
                resolved_ref="v0.4.0",
                commit_sha="1111111",
                source_url="https://example.com/booktx/releases/tag/v0.4.0",
                nav_key="booktx",
                is_default=True,
            ),
            ResolvedSiteTarget(
                project=project,
                variant=SiteVariantConfig(
                    name="main",
                    label="Current main",
                    source="git_ref",
                    ref="main",
                    url_segment="main",
                ),
                source_root=minimal_project_root,
                docs_root=minimal_project_root / "docs",
                conf_dir=minimal_project_root / "docs",
                resolved_ref="main",
                commit_sha="2222222",
                source_url="https://example.com/booktx/tree/main",
                nav_key="booktx-main",
                is_default=False,
            ),
        ]

    monkeypatch.setattr(cli, "resolve_site_targets", fake_targets)

    result = runner.invoke(cli.app, ["--config", str(config_path), "list"])

    assert result.exit_code == 0
    assert "booktx\trelease\tv0.4.0\t1111111" in result.stdout
    assert "booktx\tmain\tmain\t2222222" in result.stdout


def test_cli_build_site_accepts_variant_filter(
    tmp_path, minimal_project_root, monkeypatch
):
    config_path = _write_versioned_config(tmp_path, minimal_project_root / "docs")
    seen = {}

    def fake_build_site(config, projects, *, variants=None):
        seen["variants"] = variants
        return []

    monkeypatch.setattr(cli, "build_site", fake_build_site)

    result = runner.invoke(
        cli.app,
        ["--config", str(config_path), "build-site", "--all", "--variant", "main"],
    )

    assert result.exit_code == 0
    assert seen["variants"] == ["main"]


def test_cli_module_runs_as_python_module():
    result = subprocess.run(
        [sys.executable, "-m", "sphinxpress.cli", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Publish multiple Sphinx projects" in result.stdout
