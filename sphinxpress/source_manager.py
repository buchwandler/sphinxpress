"""Resolve configured projects into concrete build targets."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .command_log import run_logged_command
from .errors import ConfigError, ReleaseResolutionError
from .models import AppConfig, ProjectConfig, ResolvedSiteTarget, SiteVariantConfig
from .paths import nav_key_for
from .release import (
    build_ref_url,
    build_release_url,
    find_project_root,
    resolve_git_commit,
    resolve_release_tag,
)


def resolve_site_targets(
    config: AppConfig,
    projects: list[ProjectConfig],
    *,
    variants: list[str] | None = None,
) -> list[ResolvedSiteTarget]:
    selected_variants = _selected_variants(config, variants)
    seen_nav_keys: set[str] = set()
    targets: list[ResolvedSiteTarget] = []
    for project in projects:
        for variant in _variants_for_project(config, project, selected_variants):
            target = _resolve_target(config, project, variant)
            if target.nav_key in seen_nav_keys:
                raise ConfigError(
                    f"Resolved nav key '{target.nav_key}' is not unique across "
                    "selected project/variant targets."
                )
            seen_nav_keys.add(target.nav_key)
            targets.append(target)
    return targets


def resolve_book_targets(
    config: AppConfig,
    projects: list[ProjectConfig],
) -> list[ResolvedSiteTarget]:
    return resolve_site_targets(
        config,
        projects,
        variants=[config.book.docs_variant],
    )


def python_paths_for_target(target: ResolvedSiteTarget) -> list[Path]:
    paths = [target.source_root.resolve(), (target.source_root / "src").resolve()]
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        if path not in seen:
            unique.append(path)
            seen.add(path)
    return unique


def _selected_variants(
    config: AppConfig, variants: list[str] | None
) -> set[str] | None:
    if variants is None:
        return None
    selected = set()
    for name in variants:
        config.site.versioning.require_variant(name)
        selected.add(name)
    return selected


def _variants_for_project(
    config: AppConfig,
    project: ProjectConfig,
    selected_variants: set[str] | None,
) -> list[SiteVariantConfig]:
    allowed_names = set(project.site_variants or config.site.versioning.variant_map())
    variants = [
        variant
        for variant in config.site.versioning.variants
        if variant.name in allowed_names
        and (selected_variants is None or variant.name in selected_variants)
    ]
    if selected_variants and not variants:
        requested = ", ".join(sorted(selected_variants))
        raise ConfigError(
            f"Project '{project.name}' does not enable any of the selected "
            f"variants: {requested}."
        )
    return variants


def _resolve_target(
    config: AppConfig,
    project: ProjectConfig,
    variant: SiteVariantConfig,
) -> ResolvedSiteTarget:
    try:
        project_root = find_project_root(project).resolve()
        docs_relative = _relative_project_path(
            project_root, project.docs_root, project, "docs_root"
        )
        conf_relative = _relative_project_path(
            project_root, project.conf_dir, project, "conf_dir"
        )
        is_default = variant.name == config.site.versioning.default
        nav_key = nav_key_for(project.name, variant.name, is_default=is_default)
        if variant.source == "working_tree":
            source_root = project_root
            resolved_ref = "working_tree"
            commit_sha = _maybe_resolve_head_commit(project_root)
            source_url = project.repo_url
        elif variant.source == "release":
            resolved_ref = resolve_release_tag(config, project)
            commit_sha = resolve_git_commit(project_root, resolved_ref)
            source_root = _prepare_checkout(
                config,
                project_root=project_root,
                project_name=project.name,
                variant_name=variant.name,
                commit_sha=commit_sha,
            )
            source_url = build_release_url(config, project, resolved_ref)
        else:
            resolved_ref = project.version_refs.get(variant.name, variant.ref or "")
            if not resolved_ref:
                raise ReleaseResolutionError(
                    f"Project '{project.name}' variant '{variant.name}' has no git ref."
                )
            commit_sha = resolve_git_commit(project_root, resolved_ref)
            source_root = _prepare_checkout(
                config,
                project_root=project_root,
                project_name=project.name,
                variant_name=variant.name,
                commit_sha=commit_sha,
            )
            source_url = build_ref_url(config, project, resolved_ref)
        docs_root = source_root / docs_relative
        conf_dir = source_root / conf_relative
        _validate_target_paths(project, docs_root, conf_dir)
        return ResolvedSiteTarget(
            project=project,
            variant=variant,
            source_root=source_root,
            docs_root=docs_root,
            conf_dir=conf_dir,
            resolved_ref=resolved_ref,
            commit_sha=commit_sha,
            source_url=source_url,
            nav_key=nav_key,
            is_default=is_default,
        )
    except ReleaseResolutionError as exc:
        raise ReleaseResolutionError(
            f"Could not resolve variant '{variant.name}' for project "
            f"'{project.name}': {exc}"
        ) from exc


def _relative_project_path(
    project_root: Path,
    candidate: Path,
    project: ProjectConfig,
    field_name: str,
) -> Path:
    try:
        return candidate.resolve().relative_to(project_root)
    except ValueError as exc:
        raise ReleaseResolutionError(
            f"Configured {field_name} for project '{project.name}' must stay within "
            f"the project root {project_root}: {candidate}"
        ) from exc


def _maybe_resolve_head_commit(project_root: Path) -> str | None:
    try:
        return resolve_git_commit(project_root, "HEAD")
    except ReleaseResolutionError:
        return None


def _prepare_checkout(
    config: AppConfig,
    *,
    project_root: Path,
    project_name: str,
    variant_name: str,
    commit_sha: str,
) -> Path:
    target_dir = config.build.work_dir / "sources" / project_name / variant_name
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    if target_dir.exists():
        if not _is_registered_worktree(project_root, target_dir):
            raise ReleaseResolutionError(
                f"Refusing to reuse {target_dir}: it is not a registered git worktree "
                "owned by sphinxpress."
            )
        head_commit = _worktree_head(target_dir)
        if head_commit == commit_sha:
            return target_dir
        _run_git_logged(
            config,
            project_root=project_root,
            project_name=project_name,
            variant_name=variant_name,
            command=[
                "git",
                "--no-pager",
                "-C",
                str(project_root),
                "worktree",
                "remove",
                "--force",
                str(target_dir),
            ],
        )
    _run_git_logged(
        config,
        project_root=project_root,
        project_name=project_name,
        variant_name=variant_name,
        command=[
            "git",
            "--no-pager",
            "-C",
            str(project_root),
            "worktree",
            "add",
            "--detach",
            str(target_dir),
            commit_sha,
        ],
    )
    return target_dir


def _run_git_logged(
    config: AppConfig,
    *,
    project_root: Path,
    project_name: str,
    variant_name: str,
    command: list[str],
) -> None:
    logged = run_logged_command(
        command,
        log_dir=config.build.log_dir,
        log_stem=f"source-{project_name}-{variant_name}-git",
        cwd=project_root,
    )
    if logged.result.returncode != 0:
        detail = (
            logged.result.stderr.strip()
            or logged.result.stdout.strip()
            or "git worktree command failed"
        )
        log_hint = f"\nLog: {logged.log_path}" if logged.log_path else ""
        raise ReleaseResolutionError(f"{detail}{log_hint}")


def _is_registered_worktree(project_root: Path, target_dir: Path) -> bool:
    return target_dir.resolve() in _registered_worktrees(project_root)


def _registered_worktrees(project_root: Path) -> set[Path]:
    logged = run_logged_command(
        [
            "git",
            "--no-pager",
            "-C",
            str(project_root),
            "worktree",
            "list",
            "--porcelain",
        ],
        log_dir=None,
        log_stem="git-worktree-list",
        cwd=project_root,
    )
    if logged.result.returncode != 0:
        detail = (
            logged.result.stderr.strip()
            or logged.result.stdout.strip()
            or "git worktree list failed"
        )
        raise ReleaseResolutionError(detail)
    worktrees: set[Path] = set()
    for line in logged.result.stdout.splitlines():
        if line.startswith("worktree "):
            worktrees.add(Path(line.split(" ", 1)[1]).resolve())
    return worktrees


def _worktree_head(target_dir: Path) -> str:
    return resolve_git_commit(target_dir, "HEAD")


def _validate_target_paths(
    project: ProjectConfig,
    docs_root: Path,
    conf_dir: Path,
) -> None:
    effective_project = replace(project, docs_root=docs_root, conf_dir=conf_dir)
    if not effective_project.conf_py.exists():
        raise ReleaseResolutionError(
            f"Resolved conf.py for project '{project.name}' does not exist at "
            f"{effective_project.conf_py}."
        )
    effective_project.require_root_doc_path()
