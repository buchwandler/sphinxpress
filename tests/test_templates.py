import re
from pathlib import Path

import sphinxpress
from sphinxpress.book_builder import _template_environment as book_templates
from sphinxpress.jekyll_writer import (
    _template_environment as jekyll_templates,
)
from sphinxpress.jekyll_writer import (
    site_api_css,
)


def test_template_files_are_packaged():
    root = Path("sphinxpress/templates")
    expected = {
        "aggregate_conf.py.j2",
        "aggregate_index.rst.j2",
        "jekyll_page.md.j2",
        "tool_nav.yml.j2",
    }
    assert expected <= {path.name for path in root.glob("*.j2")}


def test_tool_doc_layout_is_packaged():
    root = Path("sphinxpress/templates")
    assert (root / "tool-doc.html").is_file()


def test_site_api_css_is_packaged():
    root = Path("sphinxpress/templates")
    assert (root / "site_api.css").is_file()


def test_aggregate_conf_template_renders_valid_python_literals():
    rendered = (
        book_templates()
        .get_template("aggregate_conf.py.j2")
        .render(
            title="Example Book",
            author="Example Team",
            language="en",
            version="0.1.0",
            copyright="2026, Example Team",
            suppress_warnings=["ref.python"],
            extensions=["myst_parser"],
            python_paths=["/workspace/tool-a"],
        )
    )
    assert 'project = "Example Book"' in rendered
    assert 'version = "0.1.0"' in rendered
    assert "release = version" in rendered
    assert 'copyright = "2026, Example Team"' in rendered
    assert "epub_title = project" in rendered
    assert "epub_author = author" in rendered
    assert "epub_language = language" in rendered
    assert "epub_copyright = copyright" in rendered
    assert 'suppress_warnings = ["ref.python"]' in rendered
    assert 'extensions = ["myst_parser"]' in rendered
    assert '_python_paths = ["/workspace/tool-a"]' in rendered


def test_jekyll_page_template_renders_front_matter():
    env = jekyll_templates()
    rendered = env.get_template("jekyll_page.md.j2").render(
        layout="tool-doc",
        title="Tool A",
        permalink="/tools/tool-a/",
        nav_tool="tool-a",
        docs_project="tool-a",
        docs_variant="release",
        docs_ref="v0.1.0",
        docs_commit="1234567",
        generated_notice="<!-- generated -->",
        liquid_raw_start="{% raw %}",
        liquid_raw_end="{% endraw %}",
        site_css=site_api_css(),
        body_html="<p>Hello</p>",
    )
    assert rendered.startswith("---\n")
    assert "nav_tool: tool-a" in rendered
    assert 'docs_variant: "release"' in rendered
    assert "{% raw %}" in rendered
    assert '<style data-sphinxpress-style="api">' in rendered
    assert '<div class="sphinxpress-doc">' in rendered
    assert "<p>Hello</p>" in rendered


def test_aggregate_index_template_indents_toctree_entries():
    rendered = (
        book_templates()
        .get_template("aggregate_index.rst.j2")
        .render(title="Example Book", docnames=["projects/booktx/index"])
    )
    assert "\n   projects/booktx/index\n" in rendered


def test_site_api_css_is_installed_in_package():
    template_dir = Path(sphinxpress.__file__).with_name("templates")
    assert (template_dir / "site_api.css").is_file()


def test_tool_doc_layout_renders_version_switcher():
    template_dir = Path("sphinxpress/templates")
    text = (template_dir / "tool-doc.html").read_text(encoding="utf-8")
    assert text.startswith("---\n")
    second_line = text.splitlines()[1]
    assert second_line.strip() == "layout: default"
    assert "nav.versions" in text
    assert 'class="tool-nav-versions"' in text
    assert "v.current" in text
    assert "{% raw %}" not in text
    assert "{% endraw %}" not in text
    # Prettier wraps the frontmatter at 80 chars and can split Liquid tags
    # across lines (e.g. `{%` on one line and `endif %}` on the next). Count
    # tags with a regex that tolerates whitespace between `{%` and the tag
    # name so wrapped tags are still matched.
    open_tags = len(re.findall(r"\{%\s*if\b", text))
    end_tags = len(re.findall(r"\{%\s*endif\b", text))
    for_tags = len(re.findall(r"\{%\s*for\b", text))
    endfor_tags = len(re.findall(r"\{%\s*endfor\b", text))
    details_open = text.count("<details")
    details_close = text.count("</details>")
    assert open_tags == end_tags
    assert for_tags == endfor_tags
    assert details_open == details_close
