"""Subprocess execution with durable command logs."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from shlex import join as shell_join

_SAFE_STEM_RE = re.compile(r"[^A-Za-z0-9_.-]+")


@dataclass(frozen=True)
class LoggedResult:
    result: subprocess.CompletedProcess[str]
    log_path: Path | None


def sanitize_stem(value: str) -> str:
    stem = _SAFE_STEM_RE.sub("-", value).strip("-._")
    return stem or "command"


def write_command_log(
    *,
    log_dir: Path | None,
    stem: str,
    command: list[str],
    result: subprocess.CompletedProcess[str],
    cwd: Path | None = None,
) -> Path | None:
    if log_dir is None:
        return None

    log_dir.mkdir(parents=True, exist_ok=True)
    safe_stem = sanitize_stem(stem)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = log_dir / f"{timestamp}-{safe_stem}.log"
    latest = log_dir / f"latest-{safe_stem}.log"
    content = "\n".join(
        [
            f"timestamp_utc: {timestamp}",
            f"cwd: {cwd or Path.cwd()}",
            f"returncode: {result.returncode}",
            f"command: {shell_join(command)}",
            "",
            "--- stdout ---",
            result.stdout or "",
            "",
            "--- stderr ---",
            result.stderr or "",
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")
    latest.write_text(content, encoding="utf-8")
    return path


def run_logged_command(
    command: list[str],
    *,
    log_dir: Path | None,
    log_stem: str,
    cwd: Path | None = None,
) -> LoggedResult:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        cwd=str(cwd) if cwd else None,
    )
    log_path = write_command_log(
        log_dir=log_dir,
        stem=log_stem,
        command=command,
        result=result,
        cwd=cwd,
    )
    return LoggedResult(result=result, log_path=log_path)
