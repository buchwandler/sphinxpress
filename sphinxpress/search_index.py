"""Build a static per-tool search index for the generated Jekyll site."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

from .models import PageRender, ResolvedSiteTarget, SiteConfig
from .paths import ensure_within_root, write_text_if_changed

_SNIPPET_RADIUS = 70
_SNIPPET_MAX_CHARS = 140
_SECTION_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


class _SectionBuilder(HTMLParser):
    """Walk a Sphinx body and split it into {heading, text} sections."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._sections: list[dict[str, str]] = []
        self._current_heading = ""
        self._current_text: list[str] = []
        self._collecting_heading = False
        self._skip_depth = 0

    @property
    def sections(self) -> list[dict[str, str]]:
        return self._sections

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SECTION_HEADING_TAGS:
            self._flush_section()
            self._collecting_heading = True
            return
        if tag in {"script", "style"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "br":
            self._current_text.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SECTION_HEADING_TAGS and self._collecting_heading:
            self._collecting_heading = False
            return
        if tag in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag in {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}:
            self._current_text.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._collecting_heading:
            self._current_heading += data
            return
        self._current_text.append(data)

    def _flush_section(self) -> None:
        text = "".join(self._current_text).strip()
        heading = self._current_heading.strip()
        if text or heading:
            self._sections.append({"heading": heading, "text": text})
        self._current_heading = ""
        self._current_text = []

    def close(self) -> None:
        self._flush_section()
        super().close()


def html_to_text(body_html: str) -> list[dict[str, str]]:
    """Return a list of `{heading, text}` sections extracted from a Sphinx body."""
    plain = re.sub(
        r"<script\b.*?</script>", " ", body_html, flags=re.DOTALL | re.IGNORECASE
    )
    plain = re.sub(r"<style\b.*?</style>", " ", plain, flags=re.DOTALL | re.IGNORECASE)
    builder = _SectionBuilder()
    builder.feed(plain)
    builder.close()
    if builder.sections:
        return builder.sections
    plain = re.sub(r"<[^>]+>", " ", plain)
    plain = re.sub(r"\s+", " ", plain).strip()
    if plain:
        return [{"heading": "", "text": plain}]
    return []


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "\u2026"


def _build_snippet(text: str, lower_text: str, token: str) -> str:
    """Return a short HTML snippet around the first match of `token` in `text`."""
    if not text:
        return ""
    idx = lower_text.find(token)
    if idx < 0:
        start = 0
    else:
        start = max(0, idx - _SNIPPET_RADIUS)
    end = min(len(text), start + _SNIPPET_MAX_CHARS)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "\u2026 " + snippet
    if end < len(text):
        snippet = snippet + " \u2026"
    return _truncate(snippet, _SNIPPET_MAX_CHARS + 8)


def _build_index_entry(
    page: PageRender, search_config, sections: list[dict[str, str]]
) -> dict:
    capped_sections: list[dict[str, str]] = []
    for section in sections[: search_config.max_sections]:
        text = _truncate(section["text"], search_config.max_section_chars)
        if not text:
            continue
        capped_sections.append(
            {
                "anchor": "",
                "heading": section["heading"],
                "text": text,
                "lower": text.lower(),
            }
        )
    combined_text = "\n".join(section["text"] for section in capped_sections)
    combined_lower = combined_text.lower()
    snippet = ""
    if combined_text:
        first_token = ""
        for section in capped_sections:
            lower = section["lower"]
            for word in lower.split():
                if word:
                    first_token = word
                    break
            if first_token:
                break
        snippet = _build_snippet(combined_text, combined_lower, first_token)
    return {
        "url": page.permalink,
        "title": _truncate(page.title, _SNIPPET_MAX_CHARS),
        "snippet": snippet,
        "sections": capped_sections,
    }


def build_search_index(
    pages: list[PageRender], search_config, target: ResolvedSiteTarget
) -> dict:
    """Build the JSON-serialisable per-tool search index payload."""
    entries = [
        _build_index_entry(page, search_config, html_to_text(page.body_html))
        for page in pages
    ]
    return {"tool": target.nav_key, "entries": entries}


def write_search_index(
    site: SiteConfig,
    target: ResolvedSiteTarget,
    pages: list[PageRender],
) -> Path | None:
    """Write `search/<nav_key>.json` under the site root; return None when disabled."""
    if not site.search.enabled:
        return None
    if not pages:
        return None
    payload = build_search_index(pages, site.search, target)
    payload_with_marker = {"_generated_by": "sphinxpress", **payload}
    destination = ensure_within_root(
        site.root, site.root / "search" / f"{target.nav_key}.json"
    )
    content = json.dumps(
        payload_with_marker, ensure_ascii=False, sort_keys=False, indent=2
    )
    write_text_if_changed(destination, content + "\n")
    return destination.relative_to(site.root)
