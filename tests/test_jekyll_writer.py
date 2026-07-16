from __future__ import annotations

from pathlib import Path

from sphinxpress.jekyll_writer import (
    parse_nav_yaml,
    site_api_css,
    site_highlight_css,
    site_search_css,
    tool_search_js,
    write_jekyll_page,
    write_tool_nav,
    write_tools_index,
)

from sphinxpress.models import (
    NavEntry,
    ProjectConfig,
    ReleaseMetadata,
    ResolvedSiteTarget,
    SiteConfig,
    SiteVariantConfig,
    SiteVersioningConfig,
    ToolSummary,
)


def _site(tmp_path: Path, *, protect_liquid: bool = True) -> SiteConfig:
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
            SiteVariantConfig(
                name="main",
                label="Current main",
                source="git_ref",
                ref="main",
                url_segment="main",
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
        protect_liquid=protect_liquid,
        versioning=versioning,
    )


def _target(tmp_path: Path, *, variant_name: str = "release") -> ResolvedSiteTarget:
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
    if variant_name == "main":
        variant = SiteVariantConfig(
            name="main",
            label="Current main",
            source="git_ref",
            ref="main",
            url_segment="main",
        )
        return ResolvedSiteTarget(
            project=project,
            variant=variant,
            source_root=tmp_path,
            docs_root=tmp_path,
            conf_dir=tmp_path,
            resolved_ref="main",
            commit_sha="abcdef1",
            source_url="https://example.com/booktx/tree/main",
            nav_key="booktx-main",
            is_default=False,
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


def test_jekyll_writer_writes_page_with_front_matter(tmp_path):
    output = write_jekyll_page(
        site=_site(tmp_path),
        relative_path=Path("tools/booktx/index.md"),
        title="booktx",
        permalink="/tools/booktx/",
        nav_tool="booktx",
        body_html="<p>Hello</p>",
        docs_project="booktx",
        docs_variant="release",
        docs_ref="v0.4.0",
        docs_commit="1234567",
    )

    content = output.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "nav_tool: booktx" in content
    assert 'docs_project: "booktx"' in content
    assert 'docs_variant: "release"' in content
    assert "{% raw %}" in content
    assert "{% endraw %}" in content
    assert "search_enabled: true" in content


def test_jekyll_writer_writes_nav_yaml(tmp_path):
    nav_path = write_tool_nav(
        site=_site(tmp_path),
        target=_target(tmp_path),
        release=ReleaseMetadata(
            tag="v0.4.0", url="https://example.com/booktx/releases/tag/v0.4.0"
        ),
        versions=[
            {
                "name": "release",
                "label": "Latest release",
                "ref": "v0.4.0",
                "url": "/tools/booktx/",
                "current": True,
            },
            {
                "name": "main",
                "label": "Current main",
                "ref": "main",
                "url": "/tools/booktx/main/",
                "current": False,
            },
        ],
        entries=[NavEntry(slug="index", title="booktx", url="/tools/booktx/")],
    )
    payload = parse_nav_yaml(nav_path)
    assert payload["nav_key"] == "booktx"
    assert payload["variant"] == "release"
    assert payload["release_tag"] == "v0.4.0"
    assert payload["versions"][1]["url"] == "/tools/booktx/main/"
    assert payload["entries"][0]["url"] == "/tools/booktx/"


def test_jekyll_writer_strips_sphinx_headerlinks(tmp_path):
    output = write_jekyll_page(
        site=_site(tmp_path),
        relative_path=Path("tools/booktx/troubleshooting.md"),
        title="Troubleshooting",
        permalink="/tools/booktx/troubleshooting/",
        nav_tool="booktx",
        body_html=(
            '<h1>Troubleshooting<a class="headerlink" '
            'href="#troubleshooting" title="Link to this heading">¶</a></h1>'
        ),
        docs_project="booktx",
        docs_variant="release",
        docs_ref="v0.4.0",
        docs_commit="1234567",
    )

    content = output.read_text(encoding="utf-8")
    body = content[content.index('<div class="sphinxpress-doc">') :]
    assert "headerlink" not in body
    assert "¶" not in body


def test_jekyll_writer_embeds_scoped_api_styles(tmp_path):
    output = write_jekyll_page(
        site=_site(tmp_path),
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
        docs_project="demo",
        docs_variant="release",
        docs_ref="v0.1.0",
        docs_commit="1234567",
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


def test_site_search_css_is_scoped():
    css = site_search_css()

    assert ".tool-search" in css
    assert ".tool-search-results" in css
    assert "prefers-color-scheme: dark" in css
    assert "@media print" in css


def test_site_highlight_css_is_scoped():
    css = site_highlight_css()

    assert ".sphinxpress-doc" in css
    for token in (".c", ".c1", ".k", ".kc", ".s", ".s2", ".m", ".o", ".nf", ".nb"):
        assert token in css, f"missing token class {token}"
    assert 'html[data-theme="dark"]' in css
    assert "prefers-color-scheme: dark" in css
    assert "@media print" in css
    assert "{% endraw %}" not in css
    assert "div[class^=\"highlight-\"]" in css
    assert "div[class*=\" highlight-\"]" in css


def test_jekyll_writer_embeds_scoped_highlight_styles(tmp_path):
    output = write_jekyll_page(
        site=_site(tmp_path),
        relative_path=Path("tools/booktx/index.md"),
        title="booktx",
        permalink="/tools/booktx/",
        nav_tool="booktx",
        body_html="<p>Hello</p>",
        docs_project="booktx",
        docs_variant="release",
        docs_ref="v0.4.0",
        docs_commit="1234567",
        search_enabled=True,
    )

    content = output.read_text(encoding="utf-8")
    assert '<style data-sphinxpress-style="highlight">' in content
    assert "{% endraw %}" in content
    assert content.count("{% raw %}") == 1
    assert content.count("{% endraw %}") == 1
    raw_block = content[
        content.index("{% raw %}") : content.index("{% endraw %}") + len("{% endraw %}")
    ]
    assert 'data-sphinxpress-style="highlight"' in raw_block

    output_disabled = write_jekyll_page(
        site=_site(tmp_path),
        relative_path=Path("tools/booktx/index.md"),
        title="booktx",
        permalink="/tools/booktx/",
        nav_tool="booktx",
        body_html="<p>Hello</p>",
        docs_project="booktx",
        docs_variant="release",
        docs_ref="v0.4.0",
        docs_commit="1234567",
        search_enabled=False,
    )

    disabled_content = output_disabled.read_text(encoding="utf-8")
    assert '<style data-sphinxpress-style="highlight">' in disabled_content


def test_tool_search_js_is_present():
    js = tool_search_js()

    assert "tool-search" in js
    assert "fetch(" in js
    assert "DOMContentLoaded" in js


def test_jekyll_writer_emits_search_form_when_enabled(tmp_path):
    output = write_jekyll_page(
        site=_site(tmp_path),
        relative_path=Path("tools/booktx/index.md"),
        title="booktx",
        permalink="/tools/booktx/",
        nav_tool="booktx",
        body_html="<p>Hello</p>",
        docs_project="booktx",
        docs_variant="release",
        docs_ref="v0.4.0",
        docs_commit="1234567",
        search_enabled=True,
    )

    content = output.read_text(encoding="utf-8")
    assert "search_enabled: true" in content
    assert '<style data-sphinxpress-style="search">' in content
    assert '<script data-sphinxpress-script="search"' in content
    assert "{% endraw %}" in content


def test_jekyll_writer_omits_search_assets_when_disabled(tmp_path):
    output = write_jekyll_page(
        site=_site(tmp_path),
        relative_path=Path("tools/booktx/index.md"),
        title="booktx",
        permalink="/tools/booktx/",
        nav_tool="booktx",
        body_html="<p>Hello</p>",
        docs_project="booktx",
        docs_variant="release",
        docs_ref="v0.4.0",
        docs_commit="1234567",
        search_enabled=False,
    )

    content = output.read_text(encoding="utf-8")
    assert "search_enabled: false" in content
    assert '<form class="tool-search"' not in content
    assert 'data-sphinxpress-style="search"' not in content
    assert 'data-sphinxpress-script="search"' not in content


def test_jekyll_writer_preserves_liquid_examples_and_neutralizes_endraw(tmp_path):
    output = write_jekyll_page(
        site=_site(tmp_path),
        relative_path=Path("tools/booktx/examples.md"),
        title="Examples",
        permalink="/tools/booktx/examples/",
        nav_tool="booktx",
        body_html=(
            "<pre>{{ example }}</pre><pre>{% if example %}</pre><pre>{% endraw %}</pre>"
        ),
        docs_project="booktx",
        docs_variant="release",
        docs_ref="v0.4.0",
        docs_commit="1234567",
    )

    content = output.read_text(encoding="utf-8")
    assert "{{ example }}" in content
    assert "{% if example %}" in content
    assert "&#123;% endraw %&#125;" in content
    assert content.count("{% raw %}") == 1
    assert content.count("{% endraw %}") == 1


def test_jekyll_writer_can_disable_liquid_protection(tmp_path):
    output = write_jekyll_page(
        site=_site(tmp_path, protect_liquid=False),
        relative_path=Path("tools/booktx/index.md"),
        title="booktx",
        permalink="/tools/booktx/",
        nav_tool="booktx",
        body_html="<p>Hello</p>",
        docs_project="booktx",
        docs_variant="release",
        docs_ref="v0.4.0",
        docs_commit="1234567",
    )

    content = output.read_text(encoding="utf-8")
    assert "{% raw %}" not in content
    assert "{% endraw %}" not in content


def test_jekyll_writer_preserves_realistic_autodoc_signature(tmp_path):
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
        site=_site(tmp_path),
        relative_path=Path("tools/releaseledger/api.md"),
        title="API",
        permalink="/tools/releaseledger/api/",
        nav_tool="releaseledger",
        body_html=autodoc_fragment,
        docs_project="releaseledger",
        docs_variant="release",
        docs_ref="v0.1.0",
        docs_commit="1234567",
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
    assert "Record a release entry" in content


def test_jekyll_writer_writes_rich_tools_index(tmp_path):
    output = write_tools_index(
        site=_site(tmp_path),
        relative_path=Path("tools/index.md"),
        title="Example Tool Docs",
        tools=[
            ToolSummary(
                name="booktx",
                title="booktx",
                description="Profile-first translation toolchain for ebooks.",
                docs_url="/tools/booktx/",
                repo_url="https://example.com/booktx",
                release_tag="v0.4.0",
                release_url="https://example.com/booktx/releases/tag/v0.4.0",
            ),
            ToolSummary(
                name="sphinxpress",
                title="sphinxpress",
                description="Publish multiple Sphinx projects as one site.",
                docs_url="/tools/sphinxpress/",
                repo_url="https://example.com/sphinxpress",
                release_tag="v0.1.0",
                release_url="https://example.com/sphinxpress/releases/tag/v0.1.0",
            ),
        ],
    )

    content = output.read_text(encoding="utf-8")
    assert "layout: default" in content
    assert 'title: "Example Tool Docs"' in content
    assert "permalink: /tools/" in content
    assert "GENERATED by sphinxpress" in content
    assert '<section class="hero">' in content
    assert "Example Tool Docs" in content
    assert '<div class="hero-stat">2<span>focused tools</span></div>' in content
    assert '<section class="tool-section"' in content
    assert '<h2 id="tools-index-title">All tools</h2>' in content
    assert '<div class="cards tool-cards">' in content

    assert content.count('<article class="card tool-card">') == 2

    assert ">booktx</h3>" in content
    assert ">Profile-first translation toolchain for ebooks.</p>" in content
    assert 'href="/tools/booktx/">Read docs' in content
    assert (
        'href="https://example.com/booktx/releases/tag/v0.4.0"'
        ' rel="external noopener">Latest release: v0.4.0' in content
    )
    assert (
        'href="https://example.com/booktx" rel="external noopener">GitHub ' in content
    )

    assert ">sphinxpress</h3>" in content
    assert 'href="/tools/sphinxpress/">Read docs' in content


def test_jekyll_writer_tools_index_uses_overview_layout(tmp_path):
    site = _site(tmp_path)
    site = SiteConfig(
        root=site.root,
        base_url=site.base_url,
        tools_dir=site.tools_dir,
        nav_data_dir=site.nav_data_dir,
        layout=site.layout,
        title=site.title,
        protect_liquid=site.protect_liquid,
        versioning=site.versioning,
        overview_layout="tool-overview",
    )

    output = write_tools_index(
        site=site,
        relative_path=Path("tools/index.md"),
        title="Example Tool Docs",
        tools=[
            ToolSummary(
                name="booktx",
                title="booktx",
                docs_url="/tools/booktx/",
                repo_url="https://example.com/booktx",
            ),
        ],
    )

    content = output.read_text(encoding="utf-8")
    assert "layout: tool-overview" in content
    assert "layout: default" not in content


def test_jekyll_writer_omits_release_link_when_no_release(tmp_path):
    output = write_tools_index(
        site=_site(tmp_path),
        relative_path=Path("tools/index.md"),
        title="Example Tool Docs",
        tools=[
            ToolSummary(
                name="booktx",
                title="booktx",
                description="Profile-first translation toolchain for ebooks.",
                docs_url="/tools/booktx/",
                repo_url="https://example.com/booktx",
            ),
        ],
    )

    content = output.read_text(encoding="utf-8")
    assert "Latest release" not in content
    assert ">Profile-first translation toolchain for ebooks.</p>" in content
    assert 'href="/tools/booktx/">Read docs' in content
    assert 'href="https://example.com/booktx" rel="external noopener">GitHub' in content


def test_jekyll_writer_omits_description_when_empty(tmp_path):
    output = write_tools_index(
        site=_site(tmp_path),
        relative_path=Path("tools/index.md"),
        title="Example Tool Docs",
        tools=[
            ToolSummary(
                name="booktx",
                title="booktx",
                docs_url="/tools/booktx/",
                repo_url="https://example.com/booktx",
                release_tag="v0.4.0",
                release_url="https://example.com/booktx/releases/tag/v0.4.0",
            ),
        ],
    )

    content = output.read_text(encoding="utf-8")
    assert "Latest release" in content
    assert "<p></p>" not in content
    assert ">Profile-first" not in content
    assert "tool-card" in content
