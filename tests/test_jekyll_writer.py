from __future__ import annotations

from pathlib import Path

from sphinxpress.jekyll_writer import parse_nav_yaml, write_jekyll_page, write_tool_nav
from sphinxpress.models import NavEntry, ProjectConfig, ReleaseMetadata, SiteConfig


def test_jekyll_writer_writes_page_with_front_matter(tmp_path):
    site = SiteConfig(
        root=tmp_path,
        base_url="https://example.com",
        tools_dir=Path("tools"),
        nav_data_dir=Path("_data/tool_nav"),
        layout="tool-doc",
        title="Docs",
    )

    output = write_jekyll_page(
        site=site,
        relative_path=Path("tools/booktx/index.md"),
        title="booktx",
        permalink="/tools/booktx/",
        nav_tool="booktx",
        body_html="<p>Hello</p>",
    )

    content = output.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "nav_tool: booktx" in content


def test_jekyll_writer_writes_nav_yaml(tmp_path):
    site = SiteConfig(
        root=tmp_path,
        base_url="https://example.com",
        tools_dir=Path("tools"),
        nav_data_dir=Path("_data/tool_nav"),
        layout="tool-doc",
        title="Docs",
    )
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

    nav_path = write_tool_nav(
        site=site,
        project=project,
        release=ReleaseMetadata(
            tag="v0.4.0", url="https://example.com/booktx/releases/tag/v0.4.0"
        ),
        entries=[NavEntry(slug="index", title="booktx", url="/tools/booktx/")],
    )

    payload = parse_nav_yaml(nav_path)
    assert payload["release_tag"] == "v0.4.0"
    assert payload["entries"][0]["url"] == "/tools/booktx/"
