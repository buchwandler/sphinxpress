"""Sync the canonical sphinxpress tool layout into a consuming Jekyll site.

`read_package_layout` returns the authoritative text of
`sphinxpress/templates/tool-doc.html`. `sync_consumer_layout` compares the
package version to the consumer's `<site.root>/_layouts/<site.layout>.html`
and either writes, skips, refuses, or reports a would-write, depending on
state and flags. The helper is pure: it does not print and does not call
`sys.exit`. The CLI is the only place that translates the result into a
human-readable message and an exit code.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Literal

from .models import SiteConfig

SyncStatus = Literal["wrote", "skipped_identical", "refused", "would_write"]


@dataclass(frozen=True)
class LayoutSyncResult:
    status: SyncStatus
    source_path: Path
    target_path: Path
    diff_text: str = ""


_PACKAGE_LAYOUT_RELATIVE = Path("templates") / "tool-doc.html"


def _resolve_package_layout_path() -> Path:
    """Return a real filesystem path to the package's tool-doc.html template."""
    try:
        traversable = resources.files("sphinxpress").joinpath("templates/tool-doc.html")
        resolved = Path(traversable)
        if resolved.exists():
            return resolved
    except (ModuleNotFoundError, AttributeError):
        pass
    return Path(__file__).with_name("templates") / "tool-doc.html"


def read_package_layout() -> str:
    """Return the stripped text of the package's `tool-doc.html` template."""
    return _resolve_package_layout_path().read_text(encoding="utf-8").strip()


def _render_diff(
    source_text: str, target_text: str, source_label: str, target_label: str
) -> str:
    diff = difflib.unified_diff(
        target_text.splitlines(keepends=True),
        source_text.splitlines(keepends=True),
        fromfile=target_label,
        tofile=source_label,
    )
    return "".join(diff)


def _target_path(site: SiteConfig) -> Path:
    return site.root / "_layouts" / f"{site.layout}.html"


def sync_consumer_layout(
    site: SiteConfig, *, force: bool = False, dry_run: bool = False
) -> LayoutSyncResult:
    """Compare the package layout to the consumer's copy and act on the result.

    Returns a `LayoutSyncResult`. The helper never raises on the refused path;
    the CLI decides how to translate the result into a message and an exit
    code.
    """
    source_path = _resolve_package_layout_path()
    target_path = _target_path(site)
    source_text = source_path.read_text(encoding="utf-8").strip()

    if not target_path.exists():
        if dry_run:
            return LayoutSyncResult(
                status="would_write",
                source_path=source_path,
                target_path=target_path,
                diff_text=(
                    f"--- {target_path} (missing)\n+++ {source_path} (would create)\n"
                ),
            )
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(source_text + "\n", encoding="utf-8")
        return LayoutSyncResult(
            status="wrote",
            source_path=source_path,
            target_path=target_path,
        )

    target_text = target_path.read_text(encoding="utf-8").rstrip("\n")
    if target_text == source_text:
        return LayoutSyncResult(
            status="skipped_identical",
            source_path=source_path,
            target_path=target_path,
        )

    diff_text = _render_diff(
        source_text,
        target_text,
        source_label=str(source_path),
        target_label=str(target_path),
    )

    if dry_run:
        return LayoutSyncResult(
            status="would_write",
            source_path=source_path,
            target_path=target_path,
            diff_text=diff_text,
        )

    if not force:
        return LayoutSyncResult(
            status="refused",
            source_path=source_path,
            target_path=target_path,
            diff_text=diff_text,
        )

    target_path.write_text(source_text + "\n", encoding="utf-8")
    return LayoutSyncResult(
        status="wrote",
        source_path=source_path,
        target_path=target_path,
    )
