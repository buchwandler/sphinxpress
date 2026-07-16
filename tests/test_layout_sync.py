from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from sphinxpress import layout_sync
from sphinxpress.cli import app
from sphinxpress.layout_sync import (
    LayoutSyncResult,
    sync_consumer_layout,
)
from sphinxpress.models import (
    SiteConfig,
    SiteVariantConfig,
    SiteVersioningConfig,
)


def _site(tmp_path: Path, *, layout: str = "tool-doc") -> SiteConfig:
    versioning = SiteVersioningConfig(
        enabled=True,
        default="release",
        variants=[
            SiteVariantConfig(
                name="release",
                label="Latest release",
                source="release",
                url_segment="",
            )
        ],
    )
    return SiteConfig(
        root=tmp_path,
        base_url="https://example.com",
        tools_dir=Path("tools"),
        nav_data_dir=Path("_data/tool_nav"),
        layout=layout,
        title="T",
        protect_liquid=True,
        versioning=versioning,
    )


def test_read_package_layout_returns_stripped_template():
    text = layout_sync.read_package_layout()
    assert text.startswith("---\nlayout: default")
    assert text.rstrip("\n") == text


def test_sync_consumer_layout_writes_when_target_missing(tmp_path):
    site = _site(tmp_path)
    result = sync_consumer_layout(site)

    assert isinstance(result, LayoutSyncResult)
    assert result.status == "wrote"
    target = tmp_path / "_layouts" / "tool-doc.html"
    assert target.exists()
    assert (
        target.read_text(encoding="utf-8").strip() == layout_sync.read_package_layout()
    )


def test_sync_consumer_layout_skips_when_identical(tmp_path):
    site = _site(tmp_path)
    sync_consumer_layout(site)
    before = (tmp_path / "_layouts" / "tool-doc.html").read_text(encoding="utf-8")

    result = sync_consumer_layout(site)

    assert result.status == "skipped_identical"
    assert (tmp_path / "_layouts" / "tool-doc.html").read_text(
        encoding="utf-8"
    ) == before


def test_sync_consumer_layout_refuses_when_different(tmp_path):
    site = _site(tmp_path)
    sync_consumer_layout(site)
    target = tmp_path / "_layouts" / "tool-doc.html"
    target.write_text("---\nlayout: local\n---\n# local edits\n", encoding="utf-8")
    before = target.read_text(encoding="utf-8")

    result = sync_consumer_layout(site)

    assert result.status == "refused"
    assert result.diff_text
    assert target.read_text(encoding="utf-8") == before


def test_sync_consumer_layout_force_overwrites(tmp_path):
    site = _site(tmp_path)
    sync_consumer_layout(site)
    target = tmp_path / "_layouts" / "tool-doc.html"
    target.write_text("# local edits\n", encoding="utf-8")

    result = sync_consumer_layout(site, force=True)

    assert result.status == "wrote"
    assert (
        target.read_text(encoding="utf-8").strip() == layout_sync.read_package_layout()
    )


def test_sync_consumer_layout_dry_run_does_not_write(tmp_path):
    site = _site(tmp_path)
    sync_consumer_layout(site)
    target = tmp_path / "_layouts" / "tool-doc.html"
    target.write_text("# local edits\n", encoding="utf-8")
    before = target.read_text(encoding="utf-8")

    result = sync_consumer_layout(site, dry_run=True)

    assert result.status == "would_write"
    assert result.diff_text
    assert target.read_text(encoding="utf-8") == before


def test_sync_consumer_layout_dry_run_on_missing_target(tmp_path):
    site = _site(tmp_path)
    target = tmp_path / "_layouts" / "tool-doc.html"

    result = sync_consumer_layout(site, dry_run=True)

    assert result.status == "would_write"
    assert "missing" in result.diff_text
    assert not target.exists()


def _write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "sphinxpress.toml"
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "index.rst").write_text("title\n=====\n", encoding="utf-8")
    (docs_dir / "conf.py").write_text("project = 'T'\n", encoding="utf-8")
    config_path.write_text(
        f'[site]\nroot = "{tmp_path.as_posix()}"\n'
        'base_url = "https://example.com"\n'
        'tools_dir = "tools"\n'
        'nav_data_dir = "_data/tool_nav"\n'
        'layout = "tool-doc"\n'
        'title = "T"\n'
        "protect_liquid = true\n\n"
        "[build]\n"
        'work_dir = ".sphinxpress"\n'
        'log_dir = ".sphinxpress/logs"\n'
        'sphinx_build = "sphinx-build"\n'
        "fail_on_warning = false\n"
        "keep_build_dir = false\n"
        'parallel = "auto"\n\n'
        "[build.env]\n"
        "enabled = false\n"
        'scope = "shared"\n'
        'python = "python3"\n'
        f'path = "{(tmp_path / "venv").as_posix()}"\n'
        "upgrade_pip = true\n"
        "packages = []\n\n"
        "[book]\n"
        'title = "T"\n'
        'author = "A"\n'
        'language = "en"\n'
        'version = "0.1.0"\n'
        'copyright = "2026, A"\n'
        "suppress_warnings = []\n"
        'project_order = ["t"]\n\n'
        '[pdf]\nbuilder = "weasyprint"\noutput = "dist/t.pdf"\n\n'
        '[epub]\nbuilder = "epub"\noutput = "dist/t.epub"\n\n'
        '[release]\ntag_prefix = "v"\n'
        'release_url_template = "{repo_url}/releases/tag/{tag}"\n'
        'branch_url_template = "{repo_url}/tree/{ref}"\n\n'
        "[[projects]]\n"
        'name = "t"\n'
        'title = "T"\n'
        f'docs_root = "{docs_dir.as_posix()}"\n'
        f'conf_dir = "{docs_dir.as_posix()}"\n'
        'root_doc = "index"\n'
        'repo_url = "https://example.com/t"\n'
        'release_strategy = "manual"\n'
        'release_tag = "v0.1.0"\n',
        encoding="utf-8",
    )
    return config_path


def test_sync_layout_cli_exits_zero_on_write_and_skip(tmp_path):
    config_path = _write_config(tmp_path)
    runner = CliRunner()

    first = runner.invoke(app, ["--config", str(config_path), "sync-layout"])
    assert first.exit_code == 0, first.output
    assert "Wrote" in first.output

    second = runner.invoke(app, ["--config", str(config_path), "sync-layout"])
    assert second.exit_code == 0, second.output
    assert "No changes" in second.output


def test_sync_layout_cli_exits_one_on_refused(tmp_path):
    config_path = _write_config(tmp_path)
    runner = CliRunner()

    runner.invoke(app, ["--config", str(config_path), "sync-layout"])
    target = tmp_path / "_layouts" / "tool-doc.html"
    target.write_text("# local edits\n", encoding="utf-8")

    result = runner.invoke(app, ["--config", str(config_path), "sync-layout"])
    assert result.exit_code == 1
    combined = result.output + (result.stderr or "")
    assert "Refusing to overwrite" in combined
    assert "---" in combined or "+++" in combined
    assert target.read_text(encoding="utf-8") == "# local edits\n"


def test_sync_layout_cli_force_overwrites(tmp_path):
    config_path = _write_config(tmp_path)
    runner = CliRunner()

    runner.invoke(app, ["--config", str(config_path), "sync-layout"])
    target = tmp_path / "_layouts" / "tool-doc.html"
    target.write_text("# local edits\n", encoding="utf-8")

    result = runner.invoke(
        app, ["--config", str(config_path), "sync-layout", "--force"]
    )
    assert result.exit_code == 0, result.output
    assert "Wrote" in result.output
    assert "local edits" not in target.read_text(encoding="utf-8")


def test_sync_layout_cli_dry_run_does_not_write(tmp_path):
    config_path = _write_config(tmp_path)
    runner = CliRunner()

    runner.invoke(app, ["--config", str(config_path), "sync-layout"])
    target = tmp_path / "_layouts" / "tool-doc.html"
    target.write_text("# local edits\n", encoding="utf-8")
    before = target.read_text(encoding="utf-8")

    result = runner.invoke(
        app, ["--config", str(config_path), "sync-layout", "--dry-run"]
    )
    assert result.exit_code == 0, result.output
    assert "Would update" in result.output
    assert target.read_text(encoding="utf-8") == before
