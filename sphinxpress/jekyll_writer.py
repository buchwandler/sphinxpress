"""Write deterministic Jekyll pages and navigation data."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

from .models import NavEntry, ReleaseMetadata, ResolvedSiteTarget, SiteConfig
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
    environment.filters["yaml_quote"] = lambda value: (  # type: ignore[assignment]
        "null" if value is None else json.dumps(str(value))
    )
    return environment
