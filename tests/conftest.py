from __future__ import annotations

import shutil
import textwrap
from pathlib import Path

import pytest


FIXTURES = Path(__file__).parent / "fixtures"


def copy_fixture(tmp_path: Path, name: str = "minimal_sphinx_project") -> Path:
    source = FIXTURES / name
    destination = tmp_path / name
    shutil.copytree(source, destination)
    return destination


def write_config(
    tmp_path: Path,
    *,
    projects: list[dict[str, str]],
    extra: str = "",
    root: str = ".",
) -> Path:
    project_blocks = []
    for project in projects:
        release_tag_line = ""
        if project.get("release_tag"):
            release_tag_line = f'release_tag = "{project["release_tag"]}"\n'
        project_blocks.append(
            textwrap.dedent(
                f"""
                [[projects]]
                name = "{project["name"]}"
                title = "{project.get("title", project["name"])}"
                docs_root = "{project["docs_root"]}"
                conf_dir = "{project.get("conf_dir", project["docs_root"])}"
                root_doc = "{project.get("root_doc", "index")}"
                repo_url = "{project.get("repo_url", "https://example.com/" + project["name"])}"
                release_strategy = "{project.get("release_strategy", "manual")}"
                {release_tag_line}
                """
            ).strip()
        )

    config_content = textwrap.dedent(
        f"""
        [site]
        root = "{root}"
        base_url = "https://example.com"
        tools_dir = "tools"
        nav_data_dir = "_data/tool_nav"
        layout = "tool-doc"
        title = "Example Docs"

        [build]
        work_dir = ".sphinxpress"
        sphinx_build = "sphinx-build"
        fail_on_warning = true
        keep_build_dir = false
        parallel = "1"

        [book]
        title = "Example Book"
        author = "Test Author"
        language = "en"
        project_order = [{", ".join(f'"{project["name"]}"' for project in projects)}]

        [pdf]
        builder = "latexpdf"
        output = "dist/example.pdf"

        [epub]
        builder = "epub"
        output = "dist/example.epub"

        [release]
        tag_prefix = "v"
        release_url_template = "{{repo_url}}/releases/tag/{{tag}}"

        {"\n\n".join(project_blocks)}
        """
    ).strip()
    if extra:
        config_content = f"{config_content}\n\n{textwrap.dedent(extra).strip()}\n"
    config_path = tmp_path / "sphinxpress.toml"
    config_path.write_text(config_content + "\n", encoding="utf-8")
    return config_path


@pytest.fixture
def minimal_project_root(tmp_path: Path) -> Path:
    return copy_fixture(tmp_path)


@pytest.fixture
def minimal_config_path(tmp_path: Path, minimal_project_root: Path) -> Path:
    return write_config(
        tmp_path,
        projects=[
            {
                "name": "booktx",
                "title": "booktx",
                "docs_root": str(minimal_project_root / "docs"),
                "release_tag": "v0.4.0",
            }
        ],
    )

