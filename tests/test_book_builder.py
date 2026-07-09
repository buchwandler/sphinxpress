from __future__ import annotations

from conftest import copy_fixture, write_config

from sphinxpress.book_builder import build_book, create_aggregate_project
from sphinxpress.config import load_config
from sphinxpress.errors import ValidationError


def test_book_builder_creates_aggregate_project(tmp_path, minimal_project_root):
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

    aggregate = create_aggregate_project(config, config.projects)

    assert aggregate.source_dir.exists()
    assert aggregate.build_dir.exists()


def test_book_builder_writes_aggregate_conf_py(tmp_path, minimal_project_root):
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

    aggregate = create_aggregate_project(config, config.projects)

    content = (aggregate.source_dir / "conf.py").read_text(encoding="utf-8")
    assert 'project = "Example Book"' in content


def test_book_builder_writes_project_python_paths(tmp_path, minimal_project_root):
    (minimal_project_root / "pyproject.toml").write_text(
        "[project]\nname = 'booktx'\nversion = '0.4.0'\n",
        encoding="utf-8",
    )
    (minimal_project_root / "src").mkdir()
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

    aggregate = create_aggregate_project(config, config.projects)

    content = (aggregate.source_dir / "conf.py").read_text(encoding="utf-8")
    assert str(minimal_project_root.resolve()) in content
    assert str((minimal_project_root / "src").resolve()) in content
    assert "sys.path.insert(0, _path)" in content


def test_book_builder_writes_aggregate_index_rst(tmp_path, minimal_project_root):
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

    aggregate = create_aggregate_project(config, config.projects)

    content = (aggregate.source_dir / "index.rst").read_text(encoding="utf-8")
    assert "\n   projects/booktx/index\n" in content


def test_book_builder_copies_project_docs_under_unique_prefixes(tmp_path):
    first = copy_fixture(tmp_path, "minimal_sphinx_project")
    second = copy_fixture(tmp_path, "second_sphinx_project")
    config_path = write_config(
        tmp_path,
        projects=[
            {
                "name": "booktx",
                "docs_root": str(first / "docs"),
                "release_tag": "v0.4.0",
            },
            {
                "name": "epub2text",
                "docs_root": str(second / "docs"),
                "release_tag": "v0.5.0",
            },
        ],
    )
    config = load_config(config_path)

    aggregate = create_aggregate_project(config, config.projects)

    assert (aggregate.source_dir / "projects" / "booktx" / "index.rst").exists()
    assert (aggregate.source_dir / "projects" / "epub2text" / "index.rst").exists()


def test_collect_extensions_does_not_execute_conf_py(tmp_path, minimal_project_root):
    marker = tmp_path / "executed"
    conf_py = minimal_project_root / "docs" / "conf.py"
    conf_py.write_text(
        "extensions = ['myst_parser']\n"
        f"open({str(marker)!r}, 'w', encoding='utf-8').write('executed')\n",
        encoding="utf-8",
    )
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

    aggregate = create_aggregate_project(config, config.projects)

    assert not marker.exists()
    assert "myst_parser" in (aggregate.source_dir / "conf.py").read_text(
        encoding="utf-8"
    )


def test_collect_extensions_rejects_non_literal_list(tmp_path, minimal_project_root):
    conf_py = minimal_project_root / "docs" / "conf.py"
    conf_py.write_text(
        "extensions = ['myst_parser'] + ['sphinx.ext.autodoc']\n",
        encoding="utf-8",
    )
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

    import pytest

    with pytest.raises(ValidationError, match="literal extensions list"):
        create_aggregate_project(config, config.projects)


def test_book_builder_builds_epub_for_minimal_project(
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
        (out_dir / "example.epub").write_text("epub", encoding="utf-8")

    monkeypatch.setattr("sphinxpress.book_builder.run_sphinx", fake_run_sphinx)

    output = build_book(config, config.projects, format_name="epub")

    assert output == config.epub.output
    assert output.exists()


def test_book_builder_builds_pdf_command_for_minimal_project(
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
    seen = {}

    def fake_run_sphinx(**kwargs):
        seen["builder"] = kwargs["builder"]
        pdf_root = kwargs["out_dir"] / "latex"
        pdf_root.mkdir(parents=True, exist_ok=True)
        (pdf_root / "example.pdf").write_text("pdf", encoding="utf-8")

    monkeypatch.setattr("sphinxpress.book_builder.run_sphinx", fake_run_sphinx)

    output = build_book(config, config.projects, format_name="pdf")

    assert seen["builder"] == "latexpdf"
    assert output == config.pdf.output
