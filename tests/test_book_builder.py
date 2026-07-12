from __future__ import annotations

import json
from dataclasses import replace

from conftest import copy_fixture, write_config

from sphinxpress.book_builder import build_book, create_aggregate_project
from sphinxpress.config import load_config
from sphinxpress.errors import SphinxBuildError, ValidationError
from sphinxpress.html_pdf import build_weasyprint_pdf, patch_singlehtml_for_pdf
from sphinxpress.models import ResolvedSiteTarget, SiteVariantConfig


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
    assert 'version = "0.1.0"' in content
    assert "release = version" in content
    assert 'copyright = "2026, Test Author"' in content
    assert "epub_copyright = copyright" in content
    assert "suppress_warnings = []" in content
    assert 'html_theme = "basic"' in content
    assert "html_title = project" in content
    assert "html_show_sourcelink = False" in content
    assert "html_copy_source = False" in content
    assert 'singlehtml_sidebars = {"index": []}' in content


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
    assert json.dumps(str(minimal_project_root.resolve())) in content
    assert json.dumps(str((minimal_project_root / "src").resolve())) in content
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


def test_book_builder_uses_resolved_docs_variant(
    monkeypatch, tmp_path, minimal_project_root
):
    main_docs = tmp_path / "main-docs"
    main_docs.mkdir()
    (main_docs / "conf.py").write_text(
        "project = 'booktx'\nextensions = []\nroot_doc = 'index'\n",
        encoding="utf-8",
    )
    (main_docs / "index.rst").write_text(
        "Main variant\n============\n", encoding="utf-8"
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

    def fake_resolve_book_targets(config, projects):
        project = projects[0]
        return [
            ResolvedSiteTarget(
                project=project,
                variant=SiteVariantConfig(
                    name="main",
                    label="Current main",
                    source="git_ref",
                    ref="main",
                    url_segment="main",
                ),
                source_root=main_docs.parent,
                docs_root=main_docs,
                conf_dir=main_docs,
                resolved_ref="main",
                commit_sha="abc1234",
                source_url="https://example.com/booktx/tree/main",
                nav_key="booktx-main",
                is_default=False,
            )
        ]

    monkeypatch.setattr(
        "sphinxpress.book_builder.resolve_book_targets", fake_resolve_book_targets
    )

    aggregate = create_aggregate_project(config, config.projects)

    assert "Main variant" in (
        aggregate.source_dir / "projects" / "booktx" / "index.rst"
    ).read_text(encoding="utf-8")


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


def test_book_builder_builds_weasyprint_pdf_for_minimal_project(
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
    config = replace(config, pdf=replace(config.pdf, builder="weasyprint"))
    seen = {}

    def fake_run_sphinx(**kwargs):
        seen["builder"] = kwargs["builder"]
        out_dir = kwargs["out_dir"]
        (out_dir / "_static").mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(
            '<html><head></head><body><a href="index.html#usage">Usage</a>'
            '<section id="usage"><h1>Usage</h1></section></body></html>',
            encoding="utf-8",
        )

    def fake_run_weasyprint(
        *,
        weasyprint_command,
        input_html,
        output_pdf,
        log_dir=None,
        log_stem="book-pdf-weasyprint",
    ):
        seen["weasyprint_command"] = weasyprint_command
        seen["input_html"] = input_html
        seen["log_dir"] = log_dir
        seen["log_stem"] = log_stem
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        output_pdf.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr("sphinxpress.html_pdf.run_sphinx", fake_run_sphinx)
    monkeypatch.setattr("sphinxpress.html_pdf.run_weasyprint", fake_run_weasyprint)
    monkeypatch.setattr("sphinxpress.html_pdf._tool_available", lambda command: True)

    output = build_book(config, config.projects, format_name="pdf")

    assert seen["builder"] == "singlehtml"
    assert seen["weasyprint_command"] == "weasyprint"
    assert seen["input_html"].name == "index.html"
    assert seen["log_stem"] == "book-pdf-weasyprint"
    assert seen["log_dir"] == config.build.log_dir
    assert output == config.pdf.output
    assert output.read_bytes().startswith(b"%PDF")


def test_book_builder_builds_latexpdf_when_explicitly_configured(
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


def test_patch_singlehtml_for_pdf_rewrites_index_anchor_and_adds_css(tmp_path):
    html = tmp_path / "index.html"
    html.write_text(
        '<html><head></head><body><a href="index.html#usage">Usage</a></body></html>',
        encoding="utf-8",
    )

    patch_singlehtml_for_pdf(html, css_href="_static/sphinxpress-pdf.css")

    content = html.read_text(encoding="utf-8")
    assert 'href="#usage"' in content
    assert "sphinxpress-pdf.css" in content


def test_weasyprint_preflight_reports_missing_executable(tmp_path):
    import pytest

    from sphinxpress.models import AggregateProject

    project_root = copy_fixture(tmp_path)
    config_path = write_config(
        tmp_path, projects=[{"name": "booktx", "docs_root": str(project_root / "docs")}]
    )
    config = load_config(config_path)
    aggregate = AggregateProject(
        root=tmp_path / "agg",
        source_dir=tmp_path / "agg" / "source",
        build_dir=tmp_path / "agg" / "build",
        doctree_dir=tmp_path / "agg" / "doctrees",
    )
    aggregate.source_dir.mkdir(parents=True)
    aggregate.build_dir.mkdir(parents=True)
    aggregate.doctree_dir.mkdir(parents=True)

    with pytest.raises(ValidationError, match="weasyprint>=67"):
        build_weasyprint_pdf(
            config,
            aggregate,
            sphinx_build="sphinx-build",
            weasyprint_command=str(tmp_path / "missing" / "weasyprint"),
        )


def test_build_pdf_preflights_weasyprint_before_singlehtml(
    monkeypatch, tmp_path, minimal_project_root
):
    import pytest

    from sphinxpress.errors import ValidationError

    config_path = write_config(
        tmp_path,
        projects=[
            {
                "name": "booktx",
                "docs_root": str(minimal_project_root / "docs"),
            }
        ],
    )
    config = load_config(config_path)
    config = replace(
        config,
        pdf=replace(config.pdf, builder="weasyprint"),
        build=replace(
            config.build,
            env=replace(config.build.env, enabled=True),
        ),
    )
    config = replace(
        config,
        build=replace(
            config.build,
            env=replace(
                config.build.env,
                path=tmp_path / "missing-venv",
            ),
        ),
    )

    def fail_sphinx(*args, **kwargs):
        raise AssertionError("run_sphinx must not run before WeasyPrint preflight")

    monkeypatch.setattr("sphinxpress.html_pdf.run_sphinx", fail_sphinx)

    missing = tmp_path / "does-not-exist" / "weasyprint"
    with pytest.raises(ValidationError, match="weasyprint>=67"):
        build_weasyprint_pdf(
            config,
            create_aggregate_project(config, config.projects),
            sphinx_build="sphinx-build",
            weasyprint_command=str(missing),
        )


def test_build_pdf_singlehtml_failure_message_references_log_path(
    monkeypatch, tmp_path, minimal_project_root
):
    import pytest

    from sphinxpress.html_pdf import run_weasyprint as pdf_run_weasyprint

    config_path = write_config(
        tmp_path,
        projects=[
            {
                "name": "booktx",
                "docs_root": str(minimal_project_root / "docs"),
            }
        ],
    )
    config = load_config(config_path)
    config = replace(config, pdf=replace(config.pdf, builder="weasyprint"))
    aggregate = create_aggregate_project(config, config.projects)
    (config.build.log_dir).mkdir(parents=True, exist_ok=True)
    weasyprint_bin = tmp_path / "fake-weasyprint"
    weasyprint_bin.write_text("#!/bin/sh\n", encoding="utf-8")
    weasyprint_bin.chmod(0o755)

    def fail_sphinx(**kwargs):
        raise SphinxBuildError("boom")

    monkeypatch.setattr("sphinxpress.html_pdf.run_sphinx", fail_sphinx)
    monkeypatch.setattr("sphinxpress.html_pdf.run_weasyprint", pdf_run_weasyprint)
    with pytest.raises(SphinxBuildError, match="PDF was not rendered yet"):
        build_weasyprint_pdf(
            config,
            aggregate,
            sphinx_build="sphinx-build",
            weasyprint_command=str(weasyprint_bin),
        )
