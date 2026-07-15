from __future__ import annotations

import json
from pathlib import Path

import pytest

from sphinxpress.errors import ConfigError
from sphinxpress.models import (
    PageRender,
    ProjectConfig,
    ResolvedSiteTarget,
    SiteConfig,
    SiteSearchConfig,
    SiteVariantConfig,
    SiteVersioningConfig,
)
from sphinxpress.search_index import (
    build_search_index,
    html_to_text,
    write_search_index,
)


def _site(tmp_path: Path, *, search: SiteSearchConfig | None = None) -> SiteConfig:
    versioning = SiteVersioningConfig(
        enabled=True,
        default="release",
        variants=[
            SiteVariantConfig(
                name="release",
                label="Latest release",
                source="release",
                url_segment="",
            ),
        ],
    )
    return SiteConfig(
        root=tmp_path,
        base_url="https://example.com",
        tools_dir=Path("tools"),
        nav_data_dir=Path("_data/tool_nav"),
        layout="tool-doc",
        title="Docs",
        protect_liquid=True,
        versioning=versioning,
        search=search or SiteSearchConfig(),
    )


def _target(tmp_path: Path) -> ResolvedSiteTarget:
    project = ProjectConfig(
        name="booktx",
        title="booktx",
        docs_root=tmp_path,
        conf_dir=tmp_path,
        root_doc="index",
        repo_url="https://example.com/booktx",
        release_strategy="manual",
        release_tag="v0.4.0",
    )
    variant = SiteVariantConfig(
        name="release",
        label="Latest release",
        source="release",
        url_segment="",
    )
    return ResolvedSiteTarget(
        project=project,
        variant=variant,
        source_root=tmp_path,
        docs_root=tmp_path,
        conf_dir=tmp_path,
        resolved_ref="v0.4.0",
        commit_sha="1234567",
        source_url="https://example.com/booktx/releases/tag/v0.4.0",
        nav_key="booktx",
        is_default=True,
    )


def _page(
    docname: str,
    title: str,
    body: str,
    permalink: str | None = None,
) -> PageRender:
    return PageRender(
        docname=docname,
        title=title,
        body_html=body,
        output_path=Path(f"tools/booktx/{docname}.md"),
        permalink=permalink or f"/tools/booktx/{docname}/",
        nav_tool="booktx",
        docs_project="booktx",
        docs_variant="release",
        docs_ref="v0.4.0",
        docs_commit="1234567",
    )


def test_html_to_text_extracts_headings_and_text():
    body = (
        "<h1>Welcome</h1>"
        "<p>Hello <em>world</em>.</p>"
        "<h2>Next</h2><p>Second section.</p>"
    )
    sections = html_to_text(body)
    assert [s["heading"] for s in sections] == ["Welcome", "Next"]
    assert "Hello world." in sections[0]["text"]
    assert "Second section." in sections[1]["text"]


def test_html_to_text_strips_script_and_style_blocks():
    body = (
        "<p>visible</p>"
        "<script>alert('x')</script>"
        "<style>p { color: red; }</style>"
        "<p>also visible</p>"
    )
    sections = html_to_text(body)
    assert "visible" in sections[0]["text"]
    assert "also visible" in sections[0]["text"]
    assert "alert" not in sections[0]["text"]
    assert "color" not in sections[0]["text"]


def test_html_to_text_handles_unstructured_body():
    sections = html_to_text("just <span>some</span> text")
    assert sections == [{"heading": "", "text": "just some text"}]


def test_html_to_text_returns_empty_for_empty_input():
    assert html_to_text("") == []


def test_build_search_index_has_required_shape():
    pages = [
        _page(
            "index", "Booktx Overview", "<h1>Booktx</h1><p>Tool for translation.</p>"
        ),
        _page(
            "usage",
            "Usage",
            "<h1>Usage</h1><p>Run <code>booktx</code> in your repo.</p>",
        ),
    ]
    payload = build_search_index(pages, SiteSearchConfig(), _target(Path("/tmp")))
    assert payload["tool"] == "booktx"
    assert len(payload["entries"]) == 2
    for entry in payload["entries"]:
        assert set(entry) == {"url", "title", "snippet", "sections"}
        for section in entry["sections"]:
            assert set(section) == {"anchor", "heading", "text", "lower"}
            assert section["lower"] == section["text"].lower()


def test_build_search_index_caps_section_chars_and_section_count():
    long_text = "a" * 5000
    body = "".join(f"<h2>Section {i}</h2><p>{long_text}</p>" for i in range(10))
    pages = [_page("index", "Long", body)]
    payload = build_search_index(
        pages,
        SiteSearchConfig(max_section_chars=200, max_sections=3),
        _target(Path("/tmp")),
    )
    sections = payload["entries"][0]["sections"]
    assert len(sections) == 3
    for section in sections:
        assert len(section["text"]) <= 201  # 200 + ellipsis


def test_build_search_index_includes_matching_term_in_snippet():
    pages = [
        _page(
            "index",
            "Booktx Overview",
            "<h1>Booktx</h1><p>booktx translates EPUB to text.</p>",
        )
    ]
    payload = build_search_index(pages, SiteSearchConfig(), _target(Path("/tmp")))
    assert payload["entries"][0]["snippet"]
    assert "booktx" in payload["entries"][0]["snippet"].lower()


def test_build_search_index_omits_empty_pages():
    payload = build_search_index(
        [_page("index", "Empty", "")],
        SiteSearchConfig(),
        _target(Path("/tmp")),
    )
    assert payload["entries"][0]["sections"] == []


def test_write_search_index_writes_file_under_site_root(tmp_path):
    pages = [_page("index", "Booktx", "<h1>Booktx</h1><p>hello</p>")]
    path = write_search_index(_site(tmp_path), _target(tmp_path), pages)
    assert path == Path("search/booktx.json")
    full = tmp_path / "search" / "booktx.json"
    assert full.exists()
    payload = json.loads(full.read_text(encoding="utf-8"))
    assert payload["tool"] == "booktx"
    assert payload["entries"][0]["title"] == "Booktx"


def test_write_search_index_returns_none_when_disabled(tmp_path):
    site = _site(tmp_path, search=SiteSearchConfig(enabled=False))
    pages = [_page("index", "Booktx", "<p>hello</p>")]
    assert write_search_index(site, _target(tmp_path), pages) is None
    assert not (tmp_path / "search").exists()


def test_write_search_index_returns_none_for_empty_pages(tmp_path):
    assert write_search_index(_site(tmp_path), _target(tmp_path), []) is None
    assert not (tmp_path / "search").exists()


def test_write_search_index_is_idempotent(tmp_path):
    pages = [_page("index", "Booktx", "<h1>Booktx</h1><p>hello</p>")]
    path = write_search_index(_site(tmp_path), _target(tmp_path), pages)
    first = (tmp_path / path).read_text(encoding="utf-8")
    write_search_index(_site(tmp_path), _target(tmp_path), pages)
    second = (tmp_path / path).read_text(encoding="utf-8")
    assert first == second


def test_site_search_config_rejects_non_positive_values():
    with pytest.raises(ConfigError, match="max_section_chars"):
        SiteSearchConfig(max_section_chars=0)
    with pytest.raises(ConfigError, match="max_sections"):
        SiteSearchConfig(max_sections=-3)
