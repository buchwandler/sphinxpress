from __future__ import annotations

import pytest

from sphinxpress.config import load_config
from sphinxpress.errors import ConfigError

from conftest import copy_fixture, write_config


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
