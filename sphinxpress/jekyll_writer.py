"""Write deterministic Jekyll pages and navigation data."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

from .models import NavEntry, ProjectConfig, ReleaseMetadata, SiteConfig
from .paths import ensure_within_root, generated_notice, write_text_if_changed

_HEADERLINK_RE = re.compile(
    r"""<a\s+[^>]*class=(["'])[^"']*\bheaderlink\b[^"']*\1[^>]*>.*?</a>""",
    re.IGNORECASE | re.DOTALL,
)


def strip_sphinx_headerlinks(body_html: str) -> str:
    """Remove Sphinx heading permalink anchors from generated page HTML."""
    return _HEADERLINK_RE.sub("", body_html)


def write_jekyll_page(
    *,
    site: SiteConfig,
    relative_path: Path,
    title: str,
    permalink: str,
    nav_tool: str,
    body_html: str,
) -> Path:
    destination = ensure_within_root(site.root, site.root / relative_path)
    content = (
        _template_environment()
        .get_template("jekyll_page.md.j2")
        .render(
            layout=site.layout,
            title=title,
            permalink=permalink,
            nav_tool=nav_tool,
            generated_notice=generated_notice(),
            body_html=strip_sphinx_headerlinks(body_html.strip()),
        )
    )
    write_text_if_changed(destination, content)
    return destination


def write_tool_nav(
    *,
    site: SiteConfig,
    project: ProjectConfig,
    release: ReleaseMetadata,
    entries: list[NavEntry],
) -> Path:
    destination = ensure_within_root(
        site.root,
        site.root / site.nav_data_dir / f"{project.name}.yml",
    )
    content = (
        _template_environment()
        .get_template("tool_nav.yml.j2")
        .render(
            generated_notice=generated_notice("#", ""),
            tool=project.name,
            repo_url=project.repo_url,
            release_tag=release.tag,
            release_url=release.url,
            entries=entries,
        )
    )
    write_text_if_changed(destination, content)
    return destination


def write_tools_index(
    *,
    site: SiteConfig,
    relative_path: Path,
    title: str,
    tools: list[tuple[str, str]],
) -> Path:
    destination = ensure_within_root(site.root, site.root / relative_path)
    lines = [
        "---",
        f"layout: {site.layout}",
        f'title: "{title}"',
        f"permalink: /{'/'.join(site.tools_dir.parts)}/",
        "---",
        "",
        generated_notice(),
        "",
        f"# {title}",
        "",
    ]
    for tool_name, url in tools:
        lines.append(f"- [{tool_name}]({url})")
    lines.append("")
    write_text_if_changed(destination, "\n".join(lines))
    return destination


def parse_nav_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _template_environment() -> Environment:
    template_dir = Path(__file__).with_name("templates")
    environment = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    environment.filters["yaml_quote"] = lambda value: json.dumps(str(value))  # type: ignore[assignment]
    return environment
