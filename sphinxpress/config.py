"""Configuration loading and mutation helpers."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w

from .errors import ConfigError, SelectionError
from .models import (
    AppConfig,
    BookConfig,
    BuildConfig,
    BuildEnvConfig,
    OutputConfig,
    ProjectConfig,
    ReleaseConfig,
    SiteConfig,
)
from .paths import ensure_url_safe_name, resolve_path


def load_config(config_path: Path | str = Path("sphinxpress.toml")) -> AppConfig:
    config_path = Path(config_path).resolve()
    if not config_path.exists():
        raise ConfigError(f"Configuration file '{config_path}' does not exist.")

    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)

    base_dir = config_path.parent
    site_data = _table(raw, "site")
    build_data = raw.get("build", {})
    book_data = raw.get("book", {})
    pdf_data = raw.get("pdf", {})
    epub_data = raw.get("epub", {})
    release_data = raw.get("release", {})
    projects_data = raw.get("projects")
    if not isinstance(projects_data, list) or not projects_data:
        raise ConfigError("Configuration must define at least one [[projects]] entry.")

    site_root = resolve_path(base_dir, _string(site_data, "root", default="."))
    site = SiteConfig(
        root=site_root,
        base_url=_string(site_data, "base_url"),
        tools_dir=Path(_string(site_data, "tools_dir", default="tools")),
        nav_data_dir=Path(_string(site_data, "nav_data_dir", default="_data/tool_nav")),
        layout=_string(site_data, "layout", default="tool-doc"),
        title=_string(site_data, "title"),
    )
    env_data = build_data.get("env", {})
    if not isinstance(env_data, dict):
        raise ConfigError("Configuration field 'env' must be a table.")
    env_scope = _string(env_data, "scope", default="shared")
    if env_scope != "shared":
        raise ConfigError(
            "Configuration field 'build.env.scope' must be 'shared'. "
            "Project-scoped managed environments are reserved for a future release."
        )
    env = BuildEnvConfig(
        enabled=_bool(env_data, "enabled", default=False),
        scope=env_scope,
        python=_string(env_data, "python", default="python3"),
        path=resolve_path(
            base_dir, _string(env_data, "path", default=".sphinxpress/venv")
        ),
        upgrade_pip=_bool(env_data, "upgrade_pip", default=True),
        packages=_resolve_package_paths(
            base_dir, _string_list(env_data.get("packages"), default=[])
        ),
    )
    build = BuildConfig(
        work_dir=resolve_path(
            base_dir, _string(build_data, "work_dir", default=".sphinxpress")
        ),
        sphinx_build=_string(build_data, "sphinx_build", default="sphinx-build"),
        fail_on_warning=_bool(build_data, "fail_on_warning", default=True),
        keep_build_dir=_bool(build_data, "keep_build_dir", default=False),
        parallel=_string(build_data, "parallel", default="auto"),
        env=env,
    )
    project_names = [
        item.get("name") for item in projects_data if isinstance(item, dict)
    ]
    book_author = _string(book_data, "author", default=site.title)
    book = BookConfig(
        title=_string(book_data, "title", default=site.title),
        author=book_author,
        language=_string(book_data, "language", default="en"),
        version=_string(book_data, "version", default="latest"),
        copyright=_string(book_data, "copyright", default=book_author),
        suppress_warnings=_string_list(book_data.get("suppress_warnings"), default=[]),
        project_order=_string_list(
            book_data.get("project_order"),
            default=[name for name in project_names if isinstance(name, str)],
        ),
    )
    pdf = OutputConfig(
        builder=_string(pdf_data, "builder", default="latexpdf"),
        output=resolve_path(
            base_dir, _string(pdf_data, "output", default="dist/documentation.pdf")
        ),
    )
    epub = OutputConfig(
        builder=_string(epub_data, "builder", default="epub"),
        output=resolve_path(
            base_dir, _string(epub_data, "output", default="dist/documentation.epub")
        ),
    )
    release = ReleaseConfig(
        tag_prefix=_string(release_data, "tag_prefix", default="v"),
        release_url_template=_string(
            release_data,
            "release_url_template",
            default="{repo_url}/releases/tag/{tag}",
        ),
    )
    projects = [_project_from_raw(base_dir, item) for item in projects_data]
    _validate_project_names(projects)
    return AppConfig(
        config_path=config_path,
        site=site,
        build=build,
        book=book,
        pdf=pdf,
        epub=epub,
        release=release,
        projects=projects,
    )


def select_projects(
    config: AppConfig,
    *,
    all_projects: bool,
    project: str | None,
    projects: str | None,
) -> list[ProjectConfig]:
    selected_flags = sum(
        1
        for value in (all_projects, project is not None, projects is not None)
        if value
    )
    if selected_flags != 1:
        raise SelectionError("Choose exactly one of --all, --project, or --projects.")
    if all_projects:
        return config.ordered_projects()
    if project is not None:
        return [config.require_project(project)]

    names = [item.strip() for item in projects.split(",") if item.strip()]
    if not names:
        raise SelectionError("--projects requires at least one project name.")
    duplicates = {name for name in names if names.count(name) > 1}
    if duplicates:
        joined = ", ".join(sorted(duplicates))
        raise SelectionError(f"Duplicate project names in --projects: {joined}.")
    return config.ordered_projects(names)


def append_project(
    config_path: Path | str,
    *,
    name: str,
    docs_root: str,
    repo_url: str,
    title: str | None = None,
    conf_dir: str | None = None,
    root_doc: str = "index",
    release_strategy: str = "git_tag",
) -> None:
    ensure_url_safe_name(name)
    raw = _load_raw(Path(config_path))
    projects = raw.setdefault("projects", [])
    if any(project.get("name") == name for project in projects):
        raise ConfigError(f"Project '{name}' already exists in {config_path}.")
    projects.append(
        {
            "name": name,
            "title": title or name,
            "docs_root": docs_root,
            "conf_dir": conf_dir or docs_root,
            "root_doc": root_doc,
            "repo_url": repo_url,
            "release_strategy": release_strategy,
        }
    )
    _write_raw(Path(config_path), raw)


def update_project_release_tag(
    config_path: Path | str,
    project_name: str,
    tag: str,
) -> None:
    raw = _load_raw(Path(config_path))
    for project in raw.get("projects", []):
        if project.get("name") == project_name:
            project["release_tag"] = tag
            _write_raw(Path(config_path), raw)
            return
    raise ConfigError(f"Unknown project '{project_name}'.")


def _load_raw(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        raise ConfigError(f"Configuration file '{config_path}' does not exist.")
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)
    if not isinstance(raw, dict):
        raise ConfigError(
            f"Configuration file '{config_path}' did not contain a TOML table."
        )
    return raw


def _write_raw(config_path: Path, raw: dict[str, Any]) -> None:
    config_path.write_text(tomli_w.dumps(raw), encoding="utf-8")


def _project_from_raw(base_dir: Path, raw: Any) -> ProjectConfig:
    if not isinstance(raw, dict):
        raise ConfigError("Each [[projects]] entry must be a TOML table.")
    name = ensure_url_safe_name(_string(raw, "name"))
    project = ProjectConfig(
        name=name,
        title=_string(raw, "title", default=name),
        docs_root=resolve_path(base_dir, _string(raw, "docs_root")),
        conf_dir=resolve_path(
            base_dir, _string(raw, "conf_dir", default=_string(raw, "docs_root"))
        ),
        root_doc=_string(raw, "root_doc", default="index"),
        repo_url=_string(raw, "repo_url"),
        release_strategy=_string(raw, "release_strategy", default="manual"),
        release_tag=raw.get("release_tag"),
    )
    if not project.conf_py.exists():
        raise ConfigError(
            f"Project '{project.name}' is missing conf.py at {project.conf_py}."
        )
    project.require_root_doc_path()
    return project


def _validate_project_names(projects: list[ProjectConfig]) -> None:
    seen: set[str] = set()
    duplicates = []
    for project in projects:
        if project.name in seen:
            duplicates.append(project.name)
        seen.add(project.name)
    if duplicates:
        joined = ", ".join(sorted(set(duplicates)))
        raise ConfigError(f"Duplicate project names are not allowed: {joined}.")


def _table(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise ConfigError(f"Configuration is missing required [{key}] table.")
    return value


def _string(raw: dict[str, Any], key: str, default: str | None = None) -> str:
    value = raw.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"Configuration field '{key}' must be a non-empty string.")
    return value


def _bool(raw: dict[str, Any], key: str, default: bool) -> bool:
    value = raw.get(key, default)
    if not isinstance(value, bool):
        raise ConfigError(f"Configuration field '{key}' must be a boolean.")
    return value


def _string_list(value: Any, *, default: list[str]) -> list[str]:
    if value is None:
        return list(default)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError("Configuration list values must contain only strings.")
    return list(value)


def _resolve_package_paths(base_dir: Path, packages: list[str]) -> list[str]:
    resolved: list[str] = []
    path_flags = {"-e", "--editable", "-r", "--requirement", "-c", "--constraint"}
    next_is_path = False
    for package in packages:
        if next_is_path:
            resolved.append(str(resolve_path(base_dir, package)))
            next_is_path = False
            continue
        resolved.append(package)
        next_is_path = package in path_flags
    return resolved
