"""Build Jekyll site output from Sphinx JSON pages."""

from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .env_manager import prepare_build_environment
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


def build_site(
    config: AppConfig,
    projects: list[ProjectConfig],
    *,
    sphinx_build: str | None = None,
) -> list[Path]:
    work_root = config.build.work_dir / "site"
    if not config.build.keep_build_dir:
        reset_directory(work_root)
    else:
        work_root.mkdir(parents=True, exist_ok=True)

    json_root = work_root / "json"
    outputs: list[Path] = []
    tool_links: list[tuple[str, str]] = []
    sphinx_build = sphinx_build or prepare_build_environment(config, projects)

    for project in projects:
        rendered_pages = _render_project_json(
            config, project, json_root / project.name, sphinx_build=sphinx_build
        )
        release = resolve_release_metadata(config, project)
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

        entries = [
            NavEntry(
                slug=page.docname,
                title=page.title,
                url=page.permalink,
            )
            for page in _ordered_nav_pages(project, rendered_pages)
        ]

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
    *,
    sphinx_build: str | None = None,
) -> list[PageRender]:
    run_sphinx(
        builder="json",
        conf_dir=project.conf_dir,
        src_dir=project.docs_root,
        out_dir=out_dir,
        doctree_dir=config.build.work_dir / "site" / "doctrees" / project.name,
        fail_on_warning=config.build.fail_on_warning,
        sphinx_build=sphinx_build or config.build.sphinx_build,
        parallel=config.build.parallel,
    )
    pages: list[PageRender] = []
    for json_path in sorted(out_dir.rglob("*.fjson")):
        data = json.loads(json_path.read_text(encoding="utf-8"))
        body_html = data.get("body")
        if not isinstance(body_html, str):
            continue
        docname = json_path.relative_to(out_dir).with_suffix("").as_posix()
        if _is_jekyll_hidden_docname(docname):
            continue
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


def _is_jekyll_hidden_docname(docname: str) -> bool:
    return any(part.startswith("_") for part in Path(docname).parts)


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


class _SphinxToctreeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._inside_stack: list[bool] = []
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {name: value or "" for name, value in attrs}
        classes = set(attrs_dict.get("class", "").split())
        inside = bool(self._inside_stack and self._inside_stack[-1]) or (
            "toctree-wrapper" in classes
        )
        self._inside_stack.append(inside)
        if inside and tag == "a":
            href = attrs_dict.get("href")
            if href:
                self.hrefs.append(href)

    def handle_endtag(self, tag: str) -> None:
        if self._inside_stack:
            self._inside_stack.pop()


def _ordered_nav_pages(
    project: ProjectConfig, rendered_pages: list[PageRender]
) -> list[PageRender]:
    pages_by_docname = {page.docname: page for page in rendered_pages}
    ordered_docnames: list[str] = []
    seen: set[str] = set()

    def append_docname(docname: str) -> None:
        if docname in pages_by_docname and docname not in seen:
            ordered_docnames.append(docname)
            seen.add(docname)

    append_docname(project.root_doc)

    root_page = pages_by_docname.get(project.root_doc)
    toctree_docnames = (
        _extract_toctree_docnames(root_page.body_html) if root_page else []
    )
    for docname in toctree_docnames:
        append_docname(docname)

    if not toctree_docnames:
        for docname in sorted(pages_by_docname):
            if not _is_sphinx_internal_docname(docname):
                append_docname(docname)

    return [pages_by_docname[docname] for docname in ordered_docnames]


def _extract_toctree_docnames(body_html: str) -> list[str]:
    parser = _SphinxToctreeParser()
    parser.feed(body_html)
    docnames: list[str] = []
    seen: set[str] = set()
    for href in parser.hrefs:
        docname = _docname_from_html_href(href)
        if docname and docname not in seen and not _is_sphinx_internal_docname(docname):
            docnames.append(docname)
            seen.add(docname)
    return docnames


def _docname_from_html_href(href: str) -> str | None:
    split = urlsplit(href)
    if split.scheme or split.netloc or not split.path:
        return None
    path = unquote(split.path)
    if path.startswith("/"):
        return None
    if path.endswith("/"):
        path = f"{path}index"
    if path.endswith(".html"):
        path = path[: -len(".html")]
    parts = Path(path).parts
    if not parts or ".." in parts or parts == (".",):
        return None
    return Path(*parts).as_posix()


def _is_sphinx_internal_docname(docname: str) -> bool:
    return _is_jekyll_hidden_docname(docname) or docname in {
        "genindex",
        "py-modindex",
        "search",
    }
