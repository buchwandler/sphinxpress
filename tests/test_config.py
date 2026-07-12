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
    assert config.site.protect_liquid is True
    assert config.site.versioning.enabled is False
    assert config.site.versioning.default == "legacy"
    assert [variant.name for variant in config.site.versioning.variants] == ["legacy"]
    assert config.book.docs_variant == "legacy"


def test_config_defaults_book_epub_metadata(tmp_path):
    project_root = copy_fixture(tmp_path)
    docs_root = str(project_root / "docs").replace(chr(92), "/")
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
docs_root = "{docs_root}"
conf_dir = "{docs_root}"
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
    docs_root = str(project_root / "docs").replace(chr(92), "/")
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
            docs_root = "{docs_root}"
            conf_dir = "{docs_root}"
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


def _write_versioned_config(
    tmp_path,
    docs_root,
    *,
    versioning: str,
    protect_liquid: bool = True,
    docs_variant: str = "release",
    project_extra: str = "",
    release_strategy: str = "manual",
    release_tag: str | None = "v0.4.0",
):
    release_tag_line = f'release_tag = "{release_tag}"\n' if release_tag else ""
    content = textwrap.dedent(
        f"""
        [site]
        root = "."
        base_url = "https://example.com"
        tools_dir = "tools"
        nav_data_dir = "_data/tool_nav"
        layout = "tool-doc"
        title = "Example Docs"
        protect_liquid = {str(protect_liquid).lower()}

        {versioning}

        [book]
        title = "Example Book"
        author = "Test Author"
        language = "en"
        version = "0.1.0"
        copyright = "2026, Test Author"
        project_order = ["booktx"]
        docs_variant = "{docs_variant}"

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
        docs_root = "{str(docs_root).replace(chr(92), "/")}"
        conf_dir = "{str(docs_root).replace(chr(92), "/")}"
        root_doc = "index"
        repo_url = "https://example.com/booktx"
        release_strategy = "{release_strategy}"
        {release_tag_line}{textwrap.dedent(project_extra).strip()}
        """
    ).strip()
    config_path = tmp_path / "sphinxpress.toml"
    config_path.write_text(content + "\n", encoding="utf-8")
    return config_path


def test_config_parses_enabled_versioning_and_project_overrides(
    tmp_path, minimal_project_root
):
    config_path = _write_versioned_config(
        tmp_path,
        minimal_project_root / "docs",
        versioning="""
        [site.versioning]
        enabled = true
        default = "release"

        [[site.versioning.variants]]
        name = "release"
        label = "Latest release"
        source = "release"
        url_segment = ""

        [[site.versioning.variants]]
        name = "main"
        label = "Current main"
        source = "git_ref"
        ref = "main"
        url_segment = "main"
        """,
        protect_liquid=False,
        docs_variant="main",
        release_strategy="git_tag",
        release_tag=None,
        project_extra="""
        site_variants = ["release", "main"]
        version_refs = { main = "origin/main" }
        """,
    )

    config = load_config(config_path)

    assert config.site.protect_liquid is False
    assert config.site.versioning.enabled is True
    assert config.site.versioning.default == "release"
    assert [variant.name for variant in config.site.versioning.variants] == [
        "release",
        "main",
    ]
    assert config.site.versioning.require_variant("main").ref == "main"
    assert config.book.docs_variant == "main"
    assert config.projects[0].site_variants == ["release", "main"]
    assert config.projects[0].version_refs == {"main": "origin/main"}


@pytest.mark.parametrize(
    ("extra", "message"),
    [
        (
            """
            [site.versioning]
            enabled = true
            default = "release"

            [[site.versioning.variants]]
            name = "release"
            label = "Latest release"
            source = "release"
            url_segment = ""

            [[site.versioning.variants]]
            name = "release"
            label = "Duplicate release"
            source = "git_ref"
            ref = "main"
            url_segment = "main"
            """,
            "Duplicate site variant names",
        ),
        (
            """
            [site.versioning]
            enabled = true
            default = "release"

            [[site.versioning.variants]]
            name = "release"
            label = "Latest release"
            source = "release"
            url_segment = "release"

            [[site.versioning.variants]]
            name = "main"
            label = "Current main"
            source = "git_ref"
            ref = "main"
            url_segment = "main"
            """,
            "Default variant 'release' must use an empty url_segment",
        ),
        (
            """
            [site.versioning]
            enabled = true
            default = "release"

            [[site.versioning.variants]]
            name = "release"
            label = "Latest release"
            source = "release"
            url_segment = ""

            [[site.versioning.variants]]
            name = "main"
            label = "Current main"
            source = "git_ref"
            ref = "main"
            url_segment = ""
            """,
            "Non-default variant 'main' must define a non-empty url_segment",
        ),
        (
            """
            [site.versioning]
            enabled = true
            default = "release"

            [[site.versioning.variants]]
            name = "release"
            label = "Latest release"
            source = "release"
            url_segment = ""

            [[site.versioning.variants]]
            name = "main"
            label = "Current main"
            source = "git_ref"
            ref = "main"
            url_segment = "docs"

            [[site.versioning.variants]]
            name = "preview"
            label = "Preview"
            source = "git_ref"
            ref = "preview"
            url_segment = "docs"
            """,
            "Duplicate site version url_segment 'docs'",
        ),
        (
            """
            [site.versioning]
            enabled = true
            default = "release"

            [[site.versioning.variants]]
            name = "release"
            label = "Latest release"
            source = "release"
            url_segment = ""

            [[site.versioning.variants]]
            name = "main"
            label = "Current main"
            source = "git_ref"
            url_segment = "main"
            """,
            "requires a ref",
        ),
        (
            """
            [site.versioning]
            enabled = true
            default = "release"

            [[site.versioning.variants]]
            name = "release"
            label = "Latest release"
            source = "release"
            ref = "v1.0.0"
            url_segment = ""

            [[site.versioning.variants]]
            name = "main"
            label = "Current main"
            source = "git_ref"
            ref = "main"
            url_segment = "main"
            """,
            "may define 'ref' only when source = 'git_ref'",
        ),
        (
            """
            [site.versioning]
            enabled = true
            default = "release"

            [[site.versioning.variants]]
            name = "Release"
            label = "Latest release"
            source = "release"
            url_segment = ""

            [[site.versioning.variants]]
            name = "main"
            label = "Current main"
            source = "git_ref"
            ref = "main"
            url_segment = "main"
            """,
            "not URL-safe",
        ),
        (
            """
            [site.versioning]
            enabled = true
            default = "release"

            [[site.versioning.variants]]
            name = "release"
            label = "Latest release"
            source = "release"
            url_segment = ""

            [[site.versioning.variants]]
            name = "main"
            label = "Current main"
            source = "git_ref"
            ref = "main"
            url_segment = "../main"
            """,
            "url_segment",
        ),
    ],
)
def test_config_rejects_invalid_versioning_shapes(
    tmp_path, minimal_project_root, extra, message
):
    config_path = _write_versioned_config(
        tmp_path,
        minimal_project_root / "docs",
        versioning=extra,
    )

    with pytest.raises(ConfigError, match=message):
        load_config(config_path)


def test_config_rejects_unknown_book_docs_variant(tmp_path, minimal_project_root):
    config_path = _write_versioned_config(
        tmp_path,
        minimal_project_root / "docs",
        versioning="""
        [site.versioning]
        enabled = true
        default = "release"

        [[site.versioning.variants]]
        name = "release"
        label = "Latest release"
        source = "release"
        url_segment = ""

        [[site.versioning.variants]]
        name = "main"
        label = "Current main"
        source = "git_ref"
        ref = "main"
        url_segment = "main"
        """,
        docs_variant="preview",
    )

    with pytest.raises(ConfigError, match="Unknown book.docs_variant"):
        load_config(config_path)


def test_config_rejects_missing_default_variant(tmp_path, minimal_project_root):
    config_path = _write_versioned_config(
        tmp_path,
        minimal_project_root / "docs",
        versioning="""
        [site.versioning]
        enabled = true
        default = "release"

        [[site.versioning.variants]]
        name = "preview"
        label = "Preview"
        source = "git_ref"
        ref = "main"
        url_segment = "preview"
        """,
    )

    with pytest.raises(ConfigError, match="references unknown variant 'release'"):
        load_config(config_path)


def test_config_rejects_unknown_project_variant_override(
    tmp_path, minimal_project_root
):
    config_path = _write_versioned_config(
        tmp_path,
        minimal_project_root / "docs",
        versioning="""
        [site.versioning]
        enabled = true
        default = "release"

        [[site.versioning.variants]]
        name = "release"
        label = "Latest release"
        source = "release"
        url_segment = ""

        [[site.versioning.variants]]
        name = "main"
        label = "Current main"
        source = "git_ref"
        ref = "main"
        url_segment = "main"
        """,
        project_extra="""
        site_variants = ["preview"]
        """,
    )

    with pytest.raises(ConfigError, match="unknown site_variants: preview"):
        load_config(config_path)


def test_config_rejects_unknown_version_ref_override(tmp_path, minimal_project_root):
    config_path = _write_versioned_config(
        tmp_path,
        minimal_project_root / "docs",
        versioning="""
        [site.versioning]
        enabled = true
        default = "release"

        [[site.versioning.variants]]
        name = "release"
        label = "Latest release"
        source = "release"
        url_segment = ""

        [[site.versioning.variants]]
        name = "main"
        label = "Current main"
        source = "git_ref"
        ref = "main"
        url_segment = "main"
        """,
        project_extra="""
        version_refs = { release = "v1.0.0" }
        """,
    )

    with pytest.raises(ConfigError, match="override refs only for git_ref variants"):
        load_config(config_path)
