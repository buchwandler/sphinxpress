"""Build Jekyll site output from Sphinx JSON pages."""

from __future__ import annotations

import json
from pathlib import Path

from .jekyll_writer import write_jekyll_page, write_tool_nav, write_tools_index
from .models import AppConfig, NavEntry, PageRender, ProjectConfig
from .paths import (
    docname_to_output_path,
    ensure_within_root,
    permalink_for,
    reset_directory,
)
from .release import resolve_release_metadata
from .sphinx_runner import run_sphinx


def build_site(config: AppConfig, projects: list[ProjectConfig]) -> list[Path]:
    work_root = config.build.work_dir / "site"
    if not config.build.keep_build_dir:
        reset_directory(work_root)
    else:
        work_root.mkdir(parents=True, exist_ok=True)

    json_root = work_root / "json"
    outputs: list[Path] = []
    tool_links: list[tuple[str, str]] = []

    for project in projects:
        rendered_pages = _render_project_json(config, project, json_root / project.name)
        release = resolve_release_metadata(config, project)
        entries: list[NavEntry] = []

        for page in rendered_pages:
            written = write_jekyll_page(
                site=config.site,
                relative_path=page.output_path,
                title=page.title,
                permalink=page.permalink,
                nav_tool=project.name,
                body_html=page.body_html,
            )
            outputs.append(written)
            entries.append(
                NavEntry(
                    slug=page.docname,
                    title=page.title,
                    url=page.permalink,
                )
            )

        nav_path = write_tool_nav(
            site=config.site,
            project=project,
            release=release,
            entries=entries,
        )
        outputs.append(nav_path)
        tool_links.append(
            (
                project.title,
                permalink_for(config.site.tools_dir, project.name, project.root_doc),
            )
        )

    tools_index = write_tools_index(
        site=config.site,
        relative_path=config.site.tools_dir / "index.md",
        title=config.site.title,
        tools=tool_links,
    )
    outputs.append(tools_index)
    return outputs


def _render_project_json(
    config: AppConfig,
    project: ProjectConfig,
    out_dir: Path,
) -> list[PageRender]:
    run_sphinx(
        builder="json",
        conf_dir=project.conf_dir,
        src_dir=project.docs_root,
        out_dir=out_dir,
        doctree_dir=config.build.work_dir / "site" / "doctrees" / project.name,
        fail_on_warning=config.build.fail_on_warning,
        sphinx_build=config.build.sphinx_build,
        parallel=config.build.parallel,
    )
    pages: list[PageRender] = []
    for json_path in sorted(out_dir.rglob("*.fjson")):
        data = json.loads(json_path.read_text(encoding="utf-8"))
        body_html = data.get("body")
        if not isinstance(body_html, str):
            continue
        docname = json_path.relative_to(out_dir).with_suffix("").as_posix()
        relative_page_path = (
            config.site.tools_dir / project.name / docname_to_output_path(docname)
        )
        page = PageRender(
            docname=docname,
            title=_page_title(project, docname, data.get("title")),
            body_html=body_html,
            output_path=ensure_within_root(
                config.site.root, config.site.root / relative_page_path
            ).relative_to(config.site.root),
            permalink=permalink_for(config.site.tools_dir, project.name, docname),
        )
        pages.append(page)
    return pages


def _page_title(project: ProjectConfig, docname: str, raw_title: object) -> str:
    title = (
        raw_title if isinstance(raw_title, str) and raw_title.strip() else project.title
    )
    if docname == project.root_doc and title == project.title:
        return title
    if docname == project.root_doc:
        return title
    if title.lower().startswith(project.title.lower()):
        return title
    return f"{project.title} {title}"
