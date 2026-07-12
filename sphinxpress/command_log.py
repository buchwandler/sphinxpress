"""Subprocess execution with durable command logs."""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from shlex import join as shell_join

_SAFE_STEM_RE = re.compile(r"[^A-Za-z0-9_.-]+")
_SAFE_ENV_KEYS = {
    "PYTHONPATH",
    "SPHINXPRESS_DOCS_PROJECT",
    "SPHINXPRESS_DOCS_VARIANT",
    "SPHINXPRESS_DOCS_REF",
    "SPHINXPRESS_DOCS_COMMIT",
}


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
    env: Mapping[str, str] | None = None,
) -> Path | None:
    if log_dir is None:
        return None

    log_dir.mkdir(parents=True, exist_ok=True)
    safe_stem = sanitize_stem(stem)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = log_dir / f"{timestamp}-{safe_stem}.log"
    latest = log_dir / f"latest-{safe_stem}.log"
    safe_env = {
        key: value
        for key, value in (env or {}).items()
        if key in _SAFE_ENV_KEYS and value != os.environ.get(key)
    }
    env_lines = []
    if safe_env:
        env_lines.extend(["", "--- env ---"])
        for key in sorted(safe_env):
            env_lines.append(f"{key}={safe_env[key]}")
    content = "\n".join(
        [
            f"timestamp_utc: {timestamp}",
            f"cwd: {cwd or Path.cwd()}",
            f"returncode: {result.returncode}",
            f"command: {shell_join(command)}",
            *env_lines,
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
    env: Mapping[str, str] | None = None,
) -> LoggedResult:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        cwd=str(cwd) if cwd else None,
        env=dict(env) if env is not None else None,
    )
    log_path = write_command_log(
        log_dir=log_dir,
        stem=log_stem,
        command=command,
        result=result,
        cwd=cwd,
        env=env,
    )
    return LoggedResult(result=result, log_path=log_path)
