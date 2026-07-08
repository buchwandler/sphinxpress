from pathlib import Path

from sphinxpress.book_builder import _template_environment as book_templates
from sphinxpress.jekyll_writer import _template_environment as jekyll_templates


def test_template_files_are_packaged():
    root = Path("sphinxpress/templates")
    expected = {
        "aggregate_conf.py.j2",
        "aggregate_index.rst.j2",
        "jekyll_page.md.j2",
        "tool_nav.yml.j2",
    }
    assert expected <= {path.name for path in root.glob("*.j2")}


def test_aggregate_conf_template_renders_valid_python_literals():
    rendered = (
        book_templates()
        .get_template("aggregate_conf.py.j2")
        .render(
            title="Example Book",
            author="Example Team",
            language="en",
            extensions=["myst_parser"],
        )
    )
    assert 'project = "Example Book"' in rendered
    assert 'extensions = ["myst_parser"]' in rendered


def test_jekyll_page_template_renders_front_matter():
    env = jekyll_templates()
    rendered = env.get_template("jekyll_page.md.j2").render(
        layout="tool-doc",
        title="Tool A",
        permalink="/tools/tool-a/",
        nav_tool="tool-a",
        generated_notice="<!-- generated -->",
        body_html="<p>Hello</p>",
    )
    assert rendered.startswith("---\n")
    assert "nav_tool: tool-a" in rendered
