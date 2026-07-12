from __future__ import annotations

from pathlib import Path

from sphinxpress.jekyll_writer import (
    parse_nav_yaml,
    site_api_css,
    write_jekyll_page,
    write_tool_nav,
)
from sphinxpress.models import (
    NavEntry,
    ProjectConfig,
    ReleaseMetadata,
    ResolvedSiteTarget,
    SiteConfig,
    SiteVariantConfig,
    SiteVersioningConfig,
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
