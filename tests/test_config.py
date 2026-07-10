from __future__ import annotations

import textwrap

import pytest
from conftest import copy_fixture, write_config

from sphinxpress.config import load_config
from sphinxpress.errors import ConfigError


def test_config_loads_minimal_valid_file(tmp_path):
    project_root = copy_fixture(tmp_path)
    config_path = write_config(
        tmp_path,
        projects=[
            {
                "name": "booktx",
                "docs_root": str(project_root / "docs"),
                "release_tag": "v0.4.0",
            }
        ],
    )

    config = load_config(config_path)

    assert config.site.title == "Example Docs"
    assert config.projects[0].name == "booktx"
    assert config.projects[0].conf_py.exists()
    assert config.book.version == "0.1.0"
    assert config.book.copyright == "2026, Test Author"
    assert config.book.suppress_warnings == []


def test_config_defaults_book_epub_metadata(tmp_path):
    project_root = copy_fixture(tmp_path)
    config_path = tmp_path / "sphinxpress.toml"
    config_path.write_text(
        f'''
[site]
root = "site"
base_url = "https://example.com"
title = "Example Docs"

[book]
title = "Example Book"
author = "Example Team"

[[projects]]
name = "booktx"
title = "booktx"
docs_root = "{project_root / "docs"}"
conf_dir = "{project_root / "docs"}"
root_doc = "index"
repo_url = "https://github.com/example/booktx"
release_strategy = "manual"
''',
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.book.version == "latest"
    assert config.book.copyright == "Example Team"
    assert config.book.suppress_warnings == []
    assert config.pdf.builder == "weasyprint"


def test_config_rejects_duplicate_project_names(tmp_path):
    project_root = copy_fixture(tmp_path)
    config_path = write_config(
        tmp_path,
        projects=[
            {
                "name": "booktx",
                "docs_root": str(project_root / "docs"),
                "release_tag": "v0.4.0",
            },
            {
                "name": "booktx",
                "docs_root": str(project_root / "docs"),
                "release_tag": "v0.4.1",
            },
        ],
    )

    with pytest.raises(ConfigError, match="Duplicate project names"):
        load_config(config_path)


def test_config_rejects_missing_conf_py(tmp_path):
    missing_docs = tmp_path / "missing-docs"
    missing_docs.mkdir()
    (missing_docs / "index.rst").write_text("Index\n=====\n", encoding="utf-8")
    config_path = write_config(
        tmp_path,
        projects=[
            {
                "name": "booktx",
                "docs_root": str(missing_docs),
                "release_tag": "v0.4.0",
            }
        ],
    )

    with pytest.raises(ConfigError, match="missing conf.py"):
        load_config(config_path)


def test_config_resolves_relative_paths_from_config_file_location(tmp_path):
    project_root = copy_fixture(tmp_path)
    config_path = write_config(
        tmp_path,
        projects=[
            {
                "name": "booktx",
                "docs_root": "./minimal_sphinx_project/docs",
                "release_tag": "v0.4.0",
            }
        ],
    )

    config = load_config(config_path)

    assert config.projects[0].docs_root == (project_root / "docs").resolve()


def test_build_env_defaults_disabled(tmp_path):
    project_root = copy_fixture(tmp_path)
    config_path = write_config(
        tmp_path,
        projects=[{"name": "booktx", "docs_root": str(project_root / "docs")}],
    )

    config = load_config(config_path)

    assert config.build.env.enabled is False
    assert config.build.env.scope == "shared"
    assert config.build.env.python == "python3"
    assert config.build.env.path == tmp_path / ".sphinxpress" / "venv"
    assert config.build.env.upgrade_pip is True
    assert config.build.env.packages == []


def test_build_env_parses_and_resolves_editable_paths(tmp_path):
    project_root = copy_fixture(tmp_path)
    config_path = write_config(
        tmp_path,
        projects=[{"name": "booktx", "docs_root": str(project_root / "docs")}],
        extra="""
        [build.env]
        enabled = true
        scope = "shared"
        python = "python3.12"
        path = ".docs-venv"
        upgrade_pip = false
        packages = ["sphinx>=7", "-e", "../local-package"]
        """,
    )

    config = load_config(config_path)

    assert config.build.env.enabled is True
    assert config.build.env.scope == "shared"
    assert config.build.env.python == "python3.12"
    assert config.build.env.path == tmp_path / ".docs-venv"
    assert config.build.env.upgrade_pip is False
    assert config.build.env.packages == [
        "sphinx>=7",
        "-e",
        str((tmp_path / ".." / "local-package").resolve()),
    ]


def test_build_env_rejects_unknown_scope(tmp_path):
    project_root = copy_fixture(tmp_path)
    config_path = write_config(
        tmp_path,
        projects=[{"name": "booktx", "docs_root": str(project_root / "docs")}],
        extra="""
        [build.env]
        scope = "global"
        """,
    )

    with pytest.raises(ConfigError, match="scope"):
        load_config(config_path)


def test_build_log_dir_defaults_to_work_dir_logs(tmp_path):
    project_root = copy_fixture(tmp_path)
    config_path = write_config(
        tmp_path, projects=[{"name": "booktx", "docs_root": str(project_root / "docs")}]
    )
    config = load_config(config_path)
    assert config.build.log_dir == (config.build.work_dir / "logs").resolve()


def test_build_log_dir_can_be_configured(tmp_path):
    project_root = copy_fixture(tmp_path)
    config_path = tmp_path / "sphinxpress.toml"
    config_path.write_text(
        textwrap.dedent(
            f"""
            [site]
            root = "."
            base_url = "https://example.com"
            tools_dir = "tools"
            nav_data_dir = "_data/tool_nav"
            layout = "tool-doc"
            title = "Example Docs"

            [build]
            work_dir = ".sphinxpress"
            log_dir = "custom-logs"
            sphinx_build = "sphinx-build"
            fail_on_warning = true
            keep_build_dir = false
            parallel = "1"

            [book]
            title = "Example Book"
            author = "Test Author"
            language = "en"
            version = "0.1.0"
            copyright = "2026, Test Author"
            project_order = ["booktx"]

            [pdf]
            builder = "latexpdf"
            output = "dist/example.pdf"

            [epub]
            builder = "epub"
            output = "dist/example.epub"

            [release]
            tag_prefix = "v"
            release_url_template = "{{repo_url}}/releases/tag/{{tag}}"

            [[projects]]
            name = "booktx"
            title = "booktx"
            docs_root = "{project_root / "docs"}"
            conf_dir = "{project_root / "docs"}"
            root_doc = "index"
            repo_url = "https://example.com/booktx"
            release_strategy = "manual"
            release_tag = "v0.4.0"
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    config = load_config(config_path)
    assert config.build.log_dir == (tmp_path / "custom-logs").resolve()
