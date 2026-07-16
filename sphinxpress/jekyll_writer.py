"""Write deterministic Jekyll pages and navigation data."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

from .models import (
    NavEntry,
    ReleaseMetadata,
    ResolvedSiteTarget,
    SiteConfig,
    ToolSummary,
)
from .paths import ensure_within_root, generated_notice, write_text_if_changed

_HEADERLINK_RE = re.compile(
    r"""<a\s+[^>]*class=(["'])[^"']*\bheaderlink\b[^"']*\1[^>]*>.*?</a>""",
    re.IGNORECASE | re.DOTALL,
)
_RAW_TERMINATOR_RE = re.compile(r"{%-?\s*endraw\s*-?%}")


def strip_sphinx_headerlinks(body_html: str) -> str:
    """Remove Sphinx heading permalink anchors from generated page HTML."""
    return _HEADERLINK_RE.sub("", body_html)


def neutralize_liquid_terminators(body_html: str) -> str:
    """Prevent literal endraw examples from terminating the outer raw block."""

    def _replace(match: re.Match[str]) -> str:
        return match.group(0).replace("{", "&#123;").replace("}", "&#125;")

    return _RAW_TERMINATOR_RE.sub(_replace, body_html)


@lru_cache(maxsize=1)
def site_api_css() -> str:
    """Return the packaged sphinxpress API stylesheet for generated pages."""
    template_dir = Path(__file__).with_name("templates")
    return (template_dir / "site_api.css").read_text(encoding="utf-8").strip()


@lru_cache(maxsize=1)
def site_search_css() -> str:
    """Return the packaged sphinxpress search stylesheet for generated pages."""

    template_dir = Path(__file__).with_name("templates")

    return (template_dir / "site_search.css").read_text(encoding="utf-8").strip()


@lru_cache(maxsize=1)
def site_highlight_css() -> str:
    """Return the packaged sphinxpress Pygments/Rouge highlight stylesheet."""

    template_dir = Path(__file__).with_name("templates")

    return (template_dir / "site_highlight.css").read_text(encoding="utf-8").strip()


@lru_cache(maxsize=1)
def tool_search_js() -> str:
    """Return the packaged sphinxpress search script for generated pages."""
    template_dir = Path(__file__).with_name("templates")
    return (template_dir / "tool_search.js").read_text(encoding="utf-8")


def write_jekyll_page(
    *,
    site: SiteConfig,
    relative_path: Path,
    title: str,
    permalink: str,
    nav_tool: str,
    body_html: str,
    docs_project: str,
    docs_variant: str,
    docs_ref: str,
    docs_commit: str | None,
    search_enabled: bool = True,
) -> Path:
    destination = ensure_within_root(site.root, site.root / relative_path)
    sanitized_body = neutralize_liquid_terminators(
        strip_sphinx_headerlinks(body_html.strip())
    )
    content = (
        _template_environment()
        .get_template("jekyll_page.md.j2")
        .render(
            layout=site.layout,
            title=title,
            permalink=permalink,
            nav_tool=nav_tool,
            docs_project=docs_project,
            docs_variant=docs_variant,
            docs_ref=docs_ref,
            docs_commit=docs_commit,
            generated_notice=generated_notice(),
            liquid_raw_start="{% raw %}" if site.protect_liquid else "",
            liquid_raw_end="{% endraw %}" if site.protect_liquid else "",
            site_css=site_api_css(),
            site_search_css=site_search_css() if search_enabled else "",
            site_search_js=tool_search_js() if search_enabled else "",
            site_highlight_css=site_highlight_css(),
            search_enabled=bool(search_enabled),
            body_html=sanitized_body,
        )
    )
    write_text_if_changed(destination, content)
    return destination


def write_tool_nav(
    *,
    site: SiteConfig,
    target: ResolvedSiteTarget,
    release: ReleaseMetadata | None,
    versions: list[dict[str, object]],
    entries: list[NavEntry],
) -> Path:
    destination = ensure_within_root(
        site.root,
        site.root / site.nav_data_dir / f"{target.nav_key}.yml",
    )
    payload = {
        "tool": target.project.name,
        "nav_key": target.nav_key,
        "variant": target.variant.name,
        "variant_label": target.variant.label,
        "variant_kind": target.variant.source,
        "source_ref": target.resolved_ref,
        "source_commit": target.commit_sha,
        "source_url": target.source_url,
        "is_default": target.is_default,
        "repo_url": target.project.repo_url,
        "release_tag": release.tag if release else None,
        "release_url": release.url if release else None,
        "versions": versions,
        "entries": [
            {"slug": entry.slug, "title": entry.title, "url": entry.url}
            for entry in entries
        ],
    }
    content = (
        generated_notice("#", "")
        + "\n"
        + yaml.safe_dump(
            payload,
            sort_keys=False,
            allow_unicode=False,
        )
    )
    write_text_if_changed(destination, content)
    return destination


def write_tools_index(
    *,
    site: SiteConfig,
    relative_path: Path,
    title: str,
    tools: list[ToolSummary],
) -> Path:
    destination = ensure_within_root(site.root, site.root / relative_path)
    body = _render_tools_index_body(title=title, tools=tools)
    content = (
        "\n".join(
            [
                "---",
                f"layout: {site.overview_layout}",
                f'title: "{title}"',
                f"permalink: /{'/'.join(site.tools_dir.parts)}/",
                "---",
                "",
                generated_notice(),
                "",
                body,
                "",
            ]
        )
        + "\n"
    )
    write_text_if_changed(destination, content)
    return destination


def _render_tools_index_body(*, title: str, tools: list[ToolSummary]) -> str:
    count = len(tools)
    lede = (
        "Each tool handles one step in the pipeline: extracting text, "
        "building output, splitting passages, and publishing documentation."
    )
    hero = (
        '<section class="hero">\n'
        '  <div class="hero-copy">\n'
        '    <p class="eyebrow">Documentation</p>\n'
        f"    <h1>{title}</h1>\n"
        f'    <p class="hero-lede">{lede}</p>\n'
        "  </div>\n"
        '  <div class="hero-panel" aria-label="Toolkit summary">\n'
        '    <div class="hero-panel-label">The toolkit</div>\n'
        f'    <div class="hero-stat">{count}<span>focused tools</span></div>\n'
        "    <p>File-based, reviewable state for each step of the pipeline.</p>\n"
        "  </div>\n"
        "</section>"
    )
    cards = [_render_tool_card(tool) for tool in tools]
    section = (
        '<section class="tool-section" aria-labelledby="tools-index-title">\n'
        '  <div class="section-heading">\n'
        "    <div>\n"
        '      <p class="eyebrow">The toolkit</p>\n'
        '      <h2 id="tools-index-title">All tools</h2>\n'
        "    </div>\n"
        "  </div>\n"
        '  <div class="cards tool-cards">\n' + "\n".join(cards) + "\n  </div>\n"
        "</section>"
    )
    return "\n\n".join([hero, section])


def _render_tool_card(tool: ToolSummary) -> str:
    lines = [
        '    <article class="card tool-card">',
        '      <p class="card-label">Tool</p>',
        f"      <h3>{tool.title}</h3>",
    ]
    if tool.description:
        lines.append(f"      <p>{tool.description}</p>")
    lines.append('      <div class="card-links">')
    if tool.docs_url:
        lines.append(
            f'        <a href="{tool.docs_url}">Read docs '
            '<span aria-hidden="true">↗</span></a>'
        )
    if tool.release_url:
        release_label = (
            f"Latest release: {tool.release_tag}"
            if tool.release_tag
            else "Latest release"
        )
        lines.append(
            f'        <a href="{tool.release_url}" rel="external noopener">'
            f'{release_label} <span aria-hidden="true">↗</span></a>'
        )
    if tool.repo_url:
        lines.append(
            f'        <a href="{tool.repo_url}" rel="external noopener">'
            'GitHub <span aria-hidden="true">↗</span></a>'
        )
    lines.append("      </div>")
    lines.append("    </article>")
    return "\n".join(lines)


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
    environment.filters["yaml_quote"] = lambda value: (  # type: ignore[assignment]
        "null" if value is None else json.dumps(str(value))
    )
    return environment
