from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import write_config

from sphinxpress.config import load_config
from sphinxpress.errors import PathTraversalError
from sphinxpress.jekyll_writer import parse_nav_yaml
from sphinxpress.models import ResolvedSiteTarget, SiteVariantConfig
from sphinxpress.site_builder import _render_target_json, build_site
from sphinxpress.source_manager import resolve_site_targets


def _versioned_config_text(docs_root: Path) -> str:
    return f"""
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


def _fake_targets(config, docs_root: Path) -> list[ResolvedSiteTarget]:
    project = config.projects[0]
    return [
        ResolvedSiteTarget(
            project=project,
            variant=SiteVariantConfig(
                name="release",
                label="Latest release",
                source="release",
                url_segment="",
            ),
            source_root=docs_root.parent,
            docs_root=docs_root,
            conf_dir=docs_root,
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
            source_root=docs_root.parent,
            docs_root=docs_root,
            conf_dir=docs_root,
            resolved_ref="main",
            commit_sha="2222222",
            source_url="https://example.com/booktx/tree/main",
            nav_key="booktx-main",
            is_default=False,
        ),
    ]


def test_site_builder_writes_jekyll_pages(monkeypatch, tmp_path, minimal_project_root):
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
    config = load_config(config_path)

    def fake_run_sphinx(**kwargs):
        out_dir = kwargs["out_dir"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.fjson").write_text(
            json.dumps({"title": "booktx", "body": "<p>Index</p>"}),
            encoding="utf-8",
        )
        (out_dir / "quickstart.fjson").write_text(
            json.dumps({"title": "quickstart", "body": "<p>Quickstart</p>"}),
            encoding="utf-8",
        )

    monkeypatch.setattr("sphinxpress.site_builder.run_sphinx", fake_run_sphinx)

    outputs = build_site(config, config.projects)

    index_path = tmp_path / "tools" / "booktx" / "index.md"
    quickstart_path = tmp_path / "tools" / "booktx" / "quickstart.md"
    assert index_path in outputs
    assert index_path.exists()
    assert quickstart_path.exists()


def test_site_builder_writes_variant_aware_pages_and_nav(
    monkeypatch, tmp_path, minimal_project_root
):
    config_path = tmp_path / "sphinxpress.toml"
    config_path.write_text(
        _versioned_config_text(minimal_project_root / "docs").strip() + "\n",
        encoding="utf-8",
    )
    config = load_config(config_path)

    def fake_run_sphinx(**kwargs):
        out_dir = kwargs["out_dir"]
        variant = kwargs["environment"]["SPHINXPRESS_DOCS_VARIANT"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.fjson").write_text(
            json.dumps({"title": "booktx", "body": f"<p>{variant}</p>"}),
            encoding="utf-8",
        )

    monkeypatch.setattr("sphinxpress.site_builder.run_sphinx", fake_run_sphinx)
    monkeypatch.setattr(
        "sphinxpress.site_builder.resolve_site_targets",
        lambda config, projects, variants=None: _fake_targets(
            config, minimal_project_root / "docs"
        ),
    )

    build_site(config, config.projects)

    release_page = tmp_path / "tools" / "booktx" / "index.md"
    main_page = tmp_path / "tools" / "booktx" / "main" / "index.md"
    release_nav = parse_nav_yaml(tmp_path / "_data" / "tool_nav" / "booktx.yml")
    main_nav = parse_nav_yaml(tmp_path / "_data" / "tool_nav" / "booktx-main.yml")

    assert release_page.exists()
    assert main_page.exists()
    assert "nav_tool: booktx" in release_page.read_text(encoding="utf-8")
    assert "nav_tool: booktx-main" in main_page.read_text(encoding="utf-8")
    assert release_nav["versions"][1]["url"] == "/tools/booktx/main/"
    assert main_nav["versions"][0]["url"] == "/tools/booktx/"
    assert main_nav["variant"] == "main"


def test_site_builder_removes_stale_generated_pages_but_keeps_manual_content(
    monkeypatch, tmp_path, minimal_project_root
):
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
    config = load_config(config_path)
    state = {"with_old_page": True}

    def fake_run_sphinx(**kwargs):
        out_dir = kwargs["out_dir"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.fjson").write_text(
            json.dumps({"title": "booktx", "body": "<p>Index</p>"}),
            encoding="utf-8",
        )
        if state["with_old_page"]:
            (out_dir / "old.fjson").write_text(
                json.dumps({"title": "Old", "body": "<p>Old</p>"}),
                encoding="utf-8",
            )

    monkeypatch.setattr("sphinxpress.site_builder.run_sphinx", fake_run_sphinx)

    build_site(config, config.projects)
    manual_page = tmp_path / "tools" / "booktx" / "manual.md"
    manual_page.parent.mkdir(parents=True, exist_ok=True)
    manual_page.write_text("hand-written page\n", encoding="utf-8")

    state["with_old_page"] = False
    build_site(config, config.projects)

    assert not (tmp_path / "tools" / "booktx" / "old.md").exists()
    assert manual_page.exists()


def test_site_builder_skips_jekyll_hidden_sphinx_internal_pages(
    monkeypatch, tmp_path, minimal_project_root
):
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
    config = load_config(config_path)

    def fake_run_sphinx(**kwargs):
        out_dir = kwargs["out_dir"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.fjson").write_text(
            json.dumps({"title": "booktx", "body": "<p>Index</p>"}),
            encoding="utf-8",
        )
        modules_dir = out_dir / "_modules" / "booktx"
        modules_dir.mkdir(parents=True, exist_ok=True)
        (modules_dir / "acceptance.fjson").write_text(
            json.dumps({"title": "booktx.acceptance", "body": "<p>source</p>"}),
            encoding="utf-8",
        )

    monkeypatch.setattr("sphinxpress.site_builder.run_sphinx", fake_run_sphinx)

    outputs = build_site(config, config.projects)

    assert tmp_path / "tools" / "booktx" / "index.md" in outputs
    assert not (tmp_path / "tools" / "booktx" / "_modules").exists()
    payload = parse_nav_yaml(tmp_path / "_data" / "tool_nav" / "booktx.yml")
    assert [entry["slug"] for entry in payload["entries"]] == ["index"]


def test_site_builder_rejects_path_traversal(
    monkeypatch, tmp_path, minimal_project_root
):
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
    config = load_config(config_path)
    target = resolve_site_targets(config, config.projects)[0]

    class FakePath:
        def read_text(self, encoding: str = "utf-8") -> str:
            return json.dumps({"title": "bad", "body": "<p>bad</p>"})

        def relative_to(self, other):
            return Path("../escape.fjson")

    def fake_run_sphinx(**kwargs):
        kwargs["out_dir"].mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("sphinxpress.site_builder.run_sphinx", fake_run_sphinx)
    monkeypatch.setattr(Path, "rglob", lambda self, pattern: [FakePath()])

    with pytest.raises(PathTraversalError):
        _render_target_json(config, target, tmp_path / "json", tmp_path / "doctrees")


def test_site_builder_orders_nav_by_root_toctree(
    monkeypatch, tmp_path, minimal_project_root
):
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
    config = load_config(config_path)

    def fake_run_sphinx(**kwargs):
        out_dir = kwargs["out_dir"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "project-layout.fjson").write_text(
            json.dumps({"title": "Project layout", "body": "<p>Project layout</p>"}),
            encoding="utf-8",
        )
        (out_dir / "quickstart.fjson").write_text(
            json.dumps({"title": "Quickstart", "body": "<p>Quickstart</p>"}),
            encoding="utf-8",
        )
        (out_dir / "orphan.fjson").write_text(
            json.dumps({"title": "Orphan", "body": "<p>Not in toctree</p>"}),
            encoding="utf-8",
        )
        (out_dir / "index.fjson").write_text(
            json.dumps(
                {
                    "title": "Overview",
                    "body": """
                    <div class="toctree-wrapper compound">
                      <ul>
                        <li><a class="reference internal" href="quickstart/">
                          Quickstart</a></li>
                        <li><a class="reference internal" href="quickstart/#setup">
                          Setup</a></li>
                        <li><a class="reference internal" href="project-layout/">
                          Project layout</a></li>
                      </ul>
                    </div>
                    """,
                }
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr("sphinxpress.site_builder.run_sphinx", fake_run_sphinx)

    build_site(config, config.projects)

    payload = parse_nav_yaml(tmp_path / "_data" / "tool_nav" / "booktx.yml")
    assert [entry["slug"] for entry in payload["entries"]] == [
        "index",
        "quickstart",
        "project-layout",
    ]
