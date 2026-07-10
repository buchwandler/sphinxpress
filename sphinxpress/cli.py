"""CLI entrypoints for sphinxpress."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any

import typer

from .book_builder import build_book
from .config import (
    append_project,
    load_config,
    select_projects,
    update_project_release_tag,
)
from .errors import SphinxpressError
from .release import resolve_release_metadata, resolve_release_tag
from .site_builder import build_site
from .validate import run_check, run_validation

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Publish multiple Sphinx projects as one documentation product.",
)


def _command(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except SphinxpressError as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(code=1) from exc

    return wrapper


_DEFAULT_CONFIG_PATH: Path = Path("sphinxpress.toml")


@app.callback()
def main(
    ctx: typer.Context,
    config: Path = typer.Option(  # noqa: B008
        _DEFAULT_CONFIG_PATH,
        "--config",
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to sphinxpress TOML configuration.",
    ),
) -> None:
    ctx.obj = {"config_path": config}


def _load_from_context(ctx: typer.Context):
    return load_config(ctx.obj["config_path"])


@app.command("check")
@_command
def check_command(ctx: typer.Context) -> None:
    config = _load_from_context(ctx)
    run_check(config, config.ordered_projects())
    typer.echo("Check passed.")


@app.command("list")
@_command
def list_command(ctx: typer.Context) -> None:
    config = _load_from_context(ctx)
    for project in config.ordered_projects():
        release = resolve_release_metadata(config, project)
        typer.echo(f"{project.name}\t{release.tag}\t{release.url}")


@app.command("build-site")
@_command
def build_site_command(
    ctx: typer.Context,
    all_projects: bool = typer.Option(
        False, "--all", help="Build all configured projects."
    ),
    project: str | None = typer.Option(None, "--project", help="Build one project."),
    projects: str | None = typer.Option(
        None, "--projects", help="Comma-separated project list."
    ),
) -> None:
    config = _load_from_context(ctx)
    selected = select_projects(
        config, all_projects=all_projects, project=project, projects=projects
    )
    build_site(config, selected)
    typer.echo("Site build completed.")


@app.command("build-pdf")
@_command
def build_pdf_command(
    ctx: typer.Context,
    all_projects: bool = typer.Option(
        False, "--all", help="Build all configured projects."
    ),
    project: str | None = typer.Option(None, "--project", help="Build one project."),
    projects: str | None = typer.Option(
        None, "--projects", help="Comma-separated project list."
    ),
) -> None:
    config = _load_from_context(ctx)
    selected = select_projects(
        config, all_projects=all_projects, project=project, projects=projects
    )
    output = build_book(config, selected, format_name="pdf")
    typer.echo(str(output))


@app.command("build-epub")
@_command
def build_epub_command(
    ctx: typer.Context,
    all_projects: bool = typer.Option(
        False, "--all", help="Build all configured projects."
    ),
    project: str | None = typer.Option(None, "--project", help="Build one project."),
    projects: str | None = typer.Option(
        None, "--projects", help="Comma-separated project list."
    ),
) -> None:
    config = _load_from_context(ctx)
    selected = select_projects(
        config, all_projects=all_projects, project=project, projects=projects
    )
    output = build_book(config, selected, format_name="epub")
    typer.echo(str(output))


@app.command("build-book")
@_command
def build_book_command(
    ctx: typer.Context,
    format_name: str = typer.Option(..., "--format", help="Book format: pdf or epub."),
    all_projects: bool = typer.Option(
        False, "--all", help="Build all configured projects."
    ),
    project: str | None = typer.Option(None, "--project", help="Build one project."),
    projects: str | None = typer.Option(
        None, "--projects", help="Comma-separated project list."
    ),
) -> None:
    if format_name not in {"pdf", "epub"}:
        raise typer.BadParameter("Format must be 'pdf' or 'epub'.")
    config = _load_from_context(ctx)
    selected = select_projects(
        config, all_projects=all_projects, project=project, projects=projects
    )
    output = build_book(config, selected, format_name=format_name)
    typer.echo(str(output))


@app.command("update-release")
@_command
def update_release_command(
    ctx: typer.Context,
    project: str = typer.Option(..., "--project", help="Project name."),
    tag: str | None = typer.Option(None, "--tag", help="Release tag override."),
) -> None:
    config = _load_from_context(ctx)
    target = config.require_project(project)
    resolved_tag = tag or resolve_release_tag(config, target)
    update_project_release_tag(config.config_path, project, resolved_tag)
    typer.echo(f"{project}\t{resolved_tag}")


@app.command("update-releases")
@_command
def update_releases_command(
    ctx: typer.Context,
    all_projects: bool = typer.Option(
        False, "--all", help="Update all configured projects."
    ),
) -> None:
    if not all_projects:
        raise typer.BadParameter("Pass --all to update every configured project.")
    config = _load_from_context(ctx)
    for project in config.ordered_projects():
        tag = resolve_release_tag(config, project)
        update_project_release_tag(config.config_path, project.name, tag)
        typer.echo(f"{project.name}\t{tag}")


@app.command("add-project")
@_command
def add_project_command(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name", help="Project name."),
    docs: str = typer.Option(..., "--docs", help="Path to the project's docs root."),
    repo: str = typer.Option(..., "--repo", help="Project repository URL."),
    title: str | None = typer.Option(None, "--title", help="Display title."),
    conf_dir: str | None = typer.Option(
        None, "--conf-dir", help="Path containing conf.py."
    ),
    root_doc: str = typer.Option(
        "index", "--root-doc", help="Configured Sphinx root_doc."
    ),
    release_strategy: str = typer.Option(
        "git_tag", "--release-strategy", help="manual, git_tag, or pyproject."
    ),
) -> None:
    config_path = ctx.obj["config_path"]
    append_project(
        config_path,
        name=name,
        docs_root=docs,
        repo_url=repo,
        title=title,
        conf_dir=conf_dir,
        root_doc=root_doc,
        release_strategy=release_strategy,
    )
    typer.echo(f"Added project {name}.")


@app.command("validate")
@_command
def validate_command(
    ctx: typer.Context,
    linkcheck: bool = typer.Option(
        False,
        "--linkcheck/--no-linkcheck",
        help="Run Sphinx linkcheck in addition to dummy builds.",
    ),
) -> None:
    config = _load_from_context(ctx)
    run_validation(config, config.ordered_projects(), include_linkcheck=linkcheck)
    typer.echo("Validation passed.")


if __name__ == "__main__":
    app()
