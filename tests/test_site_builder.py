from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import write_config

from sphinxpress.config import load_config
from sphinxpress.errors import PathTraversalError
from sphinxpress.jekyll_writer import parse_nav_yaml
from sphinxpress.site_builder import _render_project_json, build_site


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


def test_site_builder_writes_nav_yaml(monkeypatch, tmp_path, minimal_project_root):
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

    monkeypatch.setattr("sphinxpress.site_builder.run_sphinx", fake_run_sphinx)

    build_site(config, config.projects)

    payload = parse_nav_yaml(tmp_path / "_data" / "tool_nav" / "booktx.yml")
    assert payload["release_tag"] == "v0.4.0"
    assert payload["entries"][0]["url"] == "/tools/booktx/"


def test_site_builder_is_idempotent(monkeypatch, tmp_path, minimal_project_root):
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

    monkeypatch.setattr("sphinxpress.site_builder.run_sphinx", fake_run_sphinx)

    build_site(config, config.projects)
    first = (tmp_path / "tools" / "booktx" / "index.md").read_text(encoding="utf-8")
    build_site(config, config.projects)
    second = (tmp_path / "tools" / "booktx" / "index.md").read_text(encoding="utf-8")

    assert first == second


def test_site_builder_uses_project_release_tag(
    monkeypatch, tmp_path, minimal_project_root
):
    config_path = write_config(
        tmp_path,
        projects=[
            {
                "name": "booktx",
                "docs_root": str(minimal_project_root / "docs"),
                "release_tag": "v1.2.3",
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

    monkeypatch.setattr("sphinxpress.site_builder.run_sphinx", fake_run_sphinx)

    build_site(config, config.projects)

    payload = parse_nav_yaml(tmp_path / "_data" / "tool_nav" / "booktx.yml")
    assert payload["release_tag"] == "v1.2.3"


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
    project = config.projects[0]

    class FakePath:
        def __init__(self):
            self.name = "escape.fjson"

        def read_text(self, encoding: str = "utf-8") -> str:
            return json.dumps({"title": "bad", "body": "<p>bad</p>"})

        def relative_to(self, other):
            return Path("../escape.fjson")

    def fake_run_sphinx(**kwargs):
        kwargs["out_dir"].mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("sphinxpress.site_builder.run_sphinx", fake_run_sphinx)
    monkeypatch.setattr(Path, "rglob", lambda self, pattern: [FakePath()])

    with pytest.raises(PathTraversalError):
        _render_project_json(config, project, tmp_path / "json")


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
                        <li><a class="reference internal" href="quickstart.html">Quickstart</a></li>
                        <li><a class="reference internal" href="project-layout.html">Project layout</a></li>
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


def test_site_builder_excludes_internal_pages_from_toctree_nav(
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
            json.dumps(
                {
                    "title": "Overview",
                    "body": """
                    <div class="toctree-wrapper compound">
                      <a href="quickstart.html">Quickstart</a>
                      <a href="genindex.html">Index</a>
                      <a href="py-modindex.html">Module index</a>
                      <a href="search.html">Search</a>
                      <a href="_modules/booktx/acceptance.html">Source</a>
                    </div>
                    """,
                }
            ),
            encoding="utf-8",
        )
        (out_dir / "quickstart.fjson").write_text(
            json.dumps({"title": "Quickstart", "body": "<p>Quickstart</p>"}),
            encoding="utf-8",
        )
        for docname in ["genindex", "py-modindex", "search"]:
            (out_dir / f"{docname}.fjson").write_text(
                json.dumps({"title": docname, "body": f"<p>{docname}</p>"}),
                encoding="utf-8",
            )
        modules_dir = out_dir / "_modules" / "booktx"
        modules_dir.mkdir(parents=True, exist_ok=True)
        (modules_dir / "acceptance.fjson").write_text(
            json.dumps({"title": "Source", "body": "<p>Source</p>"}),
            encoding="utf-8",
        )

    monkeypatch.setattr("sphinxpress.site_builder.run_sphinx", fake_run_sphinx)

    build_site(config, config.projects)

    payload = parse_nav_yaml(tmp_path / "_data" / "tool_nav" / "booktx.yml")
    assert [entry["slug"] for entry in payload["entries"]] == [
        "index",
        "quickstart",
    ]


def test_site_builder_falls_back_to_sorted_nav_without_root_toctree(
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
        for docname in ["zebra", "index", "alpha", "search"]:
            (out_dir / f"{docname}.fjson").write_text(
                json.dumps({"title": docname.title(), "body": f"<p>{docname}</p>"}),
                encoding="utf-8",
            )

    monkeypatch.setattr("sphinxpress.site_builder.run_sphinx", fake_run_sphinx)

    build_site(config, config.projects)

    payload = parse_nav_yaml(tmp_path / "_data" / "tool_nav" / "booktx.yml")
    assert [entry["slug"] for entry in payload["entries"]] == [
        "index",
        "alpha",
        "zebra",
    ]
