"""Low-level wrapper around sphinx-build."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from .command_log import run_logged_command
from .errors import SphinxBuildError


def build_sphinx_command(
    *,
    sphinx_build: str = "sphinx-build",
    builder: str,
    conf_dir: Path,
    src_dir: Path,
    out_dir: Path,
    doctree_dir: Path,
    fail_on_warning: bool,
    parallel: str | None = None,
    extra_args: list[str] | None = None,
) -> list[str]:
    args = [sphinx_build]
    if builder == "latexpdf":
        args.extend(
            [
                "-M",
                "latexpdf",
                str(src_dir),
                str(out_dir),
                "-c",
                str(conf_dir),
                "-d",
                str(doctree_dir),
            ]
        )
    else:
        args.extend(["-b", builder, "-c", str(conf_dir), "-d", str(doctree_dir)])
        if fail_on_warning:
            args.append("-W")
        if parallel and parallel != "1":
            args.extend(["-j", parallel])
        if extra_args:
            args.extend(extra_args)
        args.extend([str(src_dir), str(out_dir)])
        return args

    if fail_on_warning:
        args.append("-W")
    if parallel and parallel != "1":
        args.extend(["-j", parallel])
    if extra_args:
        args.extend(extra_args)
    return args


def run_sphinx(
    *,
    builder: str,
    conf_dir: Path,
    src_dir: Path,
    out_dir: Path,
    doctree_dir: Path,
    fail_on_warning: bool,
    extra_args: list[str] | None = None,
    sphinx_build: str = "sphinx-build",
    parallel: str | None = None,
    log_dir: Path | None = None,
    log_stem: str | None = None,
    python_paths: list[Path] | None = None,
    environment: Mapping[str, str] | None = None,
) -> None:
    command = build_sphinx_command(
        sphinx_build=sphinx_build,
        builder=builder,
        conf_dir=conf_dir,
        src_dir=src_dir,
        out_dir=out_dir,
        doctree_dir=doctree_dir,
        fail_on_warning=fail_on_warning,
        parallel=parallel,
        extra_args=extra_args,
    )
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    doctree_dir.mkdir(parents=True, exist_ok=True)
    logged = run_logged_command(
        command,
        log_dir=log_dir,
        log_stem=log_stem or f"sphinx-{builder}",
        env=_build_environment(python_paths=python_paths, environment=environment),
    )
    result = logged.result
    if result.returncode != 0:
        detail = "\n".join(
            part for part in [result.stdout.strip(), result.stderr.strip()] if part
        )
        log_hint = f"\nLog: {logged.log_path}" if logged.log_path else ""
        raise SphinxBuildError(
            f"Sphinx builder '{builder}' failed with exit code {result.returncode}.\n"
            f"Command: {' '.join(command)}{log_hint}\n{detail}".rstrip()
        )


def _build_environment(
    *,
    python_paths: list[Path] | None,
    environment: Mapping[str, str] | None,
) -> dict[str, str] | None:
    if not python_paths and not environment:
        return None
    env = dict(os.environ)
    if environment:
        env.update(environment)
    if python_paths:
        existing = env.get("PYTHONPATH", "")
        new_paths = [str(path) for path in python_paths]
        env["PYTHONPATH"] = os.pathsep.join(
            [*new_paths, *([existing] if existing else [])]
        )
    return env
