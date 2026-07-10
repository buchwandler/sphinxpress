from __future__ import annotations

from pathlib import Path

from sphinxpress.jekyll_writer import (
    parse_nav_yaml,
    site_api_css,
    write_jekyll_page,
    write_tool_nav,
)
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


def test_jekyll_writer_strips_sphinx_headerlinks(tmp_path):
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
        relative_path=Path("tools/booktx/troubleshooting.md"),
        title="Troubleshooting",
        permalink="/tools/booktx/troubleshooting/",
        nav_tool="booktx",
        body_html=(
            '<h1>Troubleshooting<a class="headerlink" '
            'href="#troubleshooting" title="Link to this heading">¶</a></h1>'
        ),
    )

    content = output.read_text(encoding="utf-8")
    assert "Troubleshooting" in content
    body_start = content.index('<div class="sphinxpress-doc">')
    body = content[body_start:]
    assert "headerlink" not in body
    assert "¶" not in body


def test_jekyll_writer_embeds_scoped_api_styles(tmp_path):
    site = SiteConfig(
        root=tmp_path,
        base_url="https://example.com",
        tools_dir=Path("tools"),
        nav_data_dir=Path("_data/tool_nav"),
        layout="tool-doc",
        title="Example",
    )

    output = write_jekyll_page(
        site=site,
        relative_path=Path("tools/demo/api.md"),
        title="API",
        permalink="/tools/demo/api/",
        nav_tool="demo",
        body_html=(
            '<dl class="py function">'
            '<dt class="sig sig-object py">'
            '<span class="sig-name descname">run</span>'
            "</dt><dd><p>Run it.</p></dd></dl>"
        ),
    )

    content = output.read_text(encoding="utf-8")
    assert '<style data-sphinxpress-style="api">' in content
    assert ".sphinxpress-doc dl.py" in content
    assert '<div class="sphinxpress-doc">' in content
    assert '<dl class="py function">' in content


def test_site_api_css_is_scoped():
    css = site_api_css()

    assert ".sphinxpress-doc dl.py" in css
    assert ".sphinxpress-doc dt.sig" in css
    assert "overflow-wrap: anywhere" in css
    assert "prefers-color-scheme: dark" in css
    assert "@media print" in css


def test_jekyll_writer_preserves_realistic_autodoc_signature(tmp_path):
    site = SiteConfig(
        root=tmp_path,
        base_url="https://example.com",
        tools_dir=Path("tools"),
        nav_data_dir=Path("_data/tool_nav"),
        layout="tool-doc",
        title="Example",
    )

    autodoc_fragment = (
        '<dl class="py function">'
        '<dt class="sig sig-object py" id="releaseledger.ledger.add_entry">'
        '<span class="sig-prename descclassname">'
        '<span class="pre">releaseledger.ledger.</span>'
        "</span>"
        '<span class="sig-name descname">'
        '<span class="pre">add_entry</span>'
        "</span>"
        '<span class="sig-paren">(</span>'
        '<em class="sig-param">project:&nbsp;str</em>, '
        '<em class="sig-param">tag:&nbsp;str</em>, '
        '<em class="sig-param">summary:&nbsp;str&nbsp;=&nbsp;"v0.1.0"</em>'
        '<span class="sig-paren">)</span>'
        '<span class="sig-return"> -&gt; None</span>'
        '<a class="reference internal" '
        'href="_modules/releaseledger/ledger.html#add_entry">[source]</a>'
        "</dt>"
        "<dd><p>Record a release entry for the project.</p></dd>"
        "</dl>"
    )

    output = write_jekyll_page(
        site=site,
        relative_path=Path("tools/releaseledger/api.md"),
        title="API",
        permalink="/tools/releaseledger/api/",
        nav_tool="releaseledger",
        body_html=autodoc_fragment,
    )

    content = output.read_text(encoding="utf-8")
    assert '<div class="sphinxpress-doc">' in content
    assert '<style data-sphinxpress-style="api">' in content
    assert 'class="py function"' in content
    assert 'class="sig sig-object py"' in content
    assert 'class="sig-prename descclassname"' in content
    assert 'class="sig-name descname"' in content
    assert 'class="sig-param"' in content
    assert 'class="sig-return"' in content
    assert 'href="_modules/releaseledger/ledger.html#add_entry"' in content
    assert "Record a release entry" in content
