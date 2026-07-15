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
    ReleaseStrategy,
    SiteConfig,
    SiteSearchConfig,
    SiteVariantConfig,
    SiteVariantSource,
    SiteVersioningConfig,
)
from .paths import ensure_url_safe_name, ensure_variant_segment, resolve_path


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
    versioning = _site_versioning_from_raw(site_data)
    site = SiteConfig(
        root=site_root,
        base_url=_string(site_data, "base_url"),
        tools_dir=Path(_string(site_data, "tools_dir", default="tools")),
        nav_data_dir=Path(_string(site_data, "nav_data_dir", default="_data/tool_nav")),
        layout=_string(site_data, "layout", default="tool-doc"),
        title=_string(site_data, "title"),
        protect_liquid=_bool(site_data, "protect_liquid", default=True),
        versioning=versioning,
        overview_layout=_string(site_data, "overview_layout", default="default"),
        search=_site_search_from_raw(site_data),
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
        scope="shared",
        python=_string(env_data, "python", default="python3"),
        path=resolve_path(
            base_dir, _string(env_data, "path", default=".sphinxpress/venv")
        ),
        upgrade_pip=_bool(env_data, "upgrade_pip", default=True),
        packages=_resolve_package_paths(
            base_dir, _string_list(env_data.get("packages"), default=[])
        ),
    )
    work_dir_raw = _string(build_data, "work_dir", default=".sphinxpress")
    work_dir = resolve_path(base_dir, work_dir_raw)
    log_dir = resolve_path(
        base_dir,
        _string(
            build_data,
            "log_dir",
            default=str(Path(work_dir_raw) / "logs"),
        ),
    )
    build = BuildConfig(
        work_dir=work_dir,
        log_dir=log_dir,
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
        docs_variant=_string(
            book_data,
            "docs_variant",
            default=site.versioning.default,
        ),
    )
    pdf = OutputConfig(
        builder=_string(pdf_data, "builder", default="weasyprint"),
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
        branch_url_template=_string(
            release_data,
            "branch_url_template",
            default="{repo_url}/tree/{ref}",
        ),
    )
    if book.docs_variant not in site.versioning.variant_map():
        raise ConfigError(
            f"Unknown book.docs_variant '{book.docs_variant}'. "
            "Choose a configured site versioning variant."
        )

    projects = [
        _project_from_raw(base_dir, item, versioning=site.versioning)
        for item in projects_data
    ]
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

    assert projects is not None
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


def _project_from_raw(
    base_dir: Path,
    raw: Any,
    *,
    versioning: SiteVersioningConfig,
) -> ProjectConfig:
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
        release_strategy=_release_strategy(raw, "release_strategy", default="manual"),
        description=_optional_string(raw, "description", default=""),
        release_tag=raw.get("release_tag"),
        site_variants=(
            None
            if raw.get("site_variants") is None
            else _string_list(raw.get("site_variants"), default=[])
        ),
        version_refs=_string_dict(raw.get("version_refs"), default={}),
    )
    if project.site_variants:
        unknown_variants = [
            name
            for name in project.site_variants
            if name not in versioning.variant_map()
        ]
        if unknown_variants:
            joined = ", ".join(sorted(unknown_variants))
            raise ConfigError(
                f"Project '{project.name}' references unknown site_variants: {joined}."
            )
    for variant_name, ref in project.version_refs.items():
        variant = versioning.variant_map().get(variant_name)
        if variant is None:
            raise ConfigError(
                f"Project '{project.name}' references unknown version_refs key "
                f"'{variant_name}'."
            )
        if variant.source != "git_ref":
            raise ConfigError(
                f"Project '{project.name}' can override refs only for git_ref "
                f"variants, but '{variant_name}' uses source '{variant.source}'."
            )
        if not ref.strip():
            raise ConfigError(
                f"Project '{project.name}' version_refs entry '{variant_name}' must "
                "be a non-empty string."
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


def _int(raw: dict[str, Any], key: str, default: int) -> int:
    value = raw.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"Configuration field '{key}' must be an integer.")
    return value


def _optional_string(raw: dict[str, Any], key: str, default: str = "") -> str:
    value = raw.get(key, default)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ConfigError(f"Configuration field '{key}' must be a string when set.")
    return value


def _string_list(value: Any, *, default: list[str]) -> list[str]:
    if value is None:
        return list(default)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError("Configuration list values must contain only strings.")
    return list(value)


def _string_dict(value: Any, *, default: dict[str, str]) -> dict[str, str]:
    if value is None:
        return dict(default)
    if not isinstance(value, dict):
        raise ConfigError("Configuration dictionary values must be TOML tables.")
    if not all(
        isinstance(key, str) and isinstance(item, str) for key, item in value.items()
    ):
        raise ConfigError(
            "Configuration dictionary values must contain only string keys and values."
        )
    return {key: item for key, item in value.items()}


def _release_strategy(
    raw: dict[str, Any], key: str, default: str = "manual"
) -> ReleaseStrategy:
    value = _string(raw, key, default=default)
    if value == "manual":
        return "manual"
    if value == "git_tag":
        return "git_tag"
    if value == "pyproject":
        return "pyproject"
    raise ConfigError(
        f"Configuration field '{key}' must be one of: manual, git_tag, pyproject."
    )


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


def _site_versioning_from_raw(site_data: dict[str, Any]) -> SiteVersioningConfig:
    raw = site_data.get("versioning")
    if raw is None:
        return _legacy_site_versioning()
    if not isinstance(raw, dict):
        raise ConfigError("Configuration field 'site.versioning' must be a table.")
    enabled = _bool(raw, "enabled", default=True)
    if not enabled:
        return _legacy_site_versioning()
    variants_data = raw.get("variants")
    if not isinstance(variants_data, list) or not variants_data:
        raise ConfigError(
            "Configuration field 'site.versioning.variants' must define at least "
            "one variant when versioning is enabled."
        )
    default = _string(raw, "default")
    variants = [_site_variant_from_raw(item) for item in variants_data]
    names = [variant.name for variant in variants]
    duplicates = {name for name in names if names.count(name) > 1}
    if duplicates:
        joined = ", ".join(sorted(duplicates))
        raise ConfigError(f"Duplicate site variant names are not allowed: {joined}.")
    if default not in names:
        raise ConfigError(
            f"Configuration field 'site.versioning.default' references unknown "
            f"variant '{default}'."
        )
    seen_segments: set[str] = set()
    for variant in variants:
        is_default = variant.name == default
        if is_default and variant.url_segment:
            raise ConfigError(
                f"Default variant '{variant.name}' must use an empty url_segment."
            )
        if not is_default and not variant.url_segment:
            raise ConfigError(
                f"Non-default variant '{variant.name}' must define a non-empty "
                "url_segment."
            )
        if variant.url_segment:
            if variant.url_segment in seen_segments:
                raise ConfigError(
                    f"Duplicate site version url_segment '{variant.url_segment}' is "
                    "not allowed."
                )
            seen_segments.add(variant.url_segment)
    return SiteVersioningConfig(enabled=True, default=default, variants=variants)


def _site_search_from_raw(site_data: dict[str, Any]) -> SiteSearchConfig:
    raw = site_data.get("search")
    if raw is None:
        return SiteSearchConfig()
    if not isinstance(raw, dict):
        raise ConfigError("Configuration field 'site.search' must be a table.")
    return SiteSearchConfig(
        enabled=_bool(raw, "enabled", default=True),
        max_section_chars=_int(raw, "max_section_chars", default=800),
        max_sections=_int(raw, "max_sections", default=50),
    )


def _site_variant_from_raw(raw: Any) -> SiteVariantConfig:
    if not isinstance(raw, dict):
        raise ConfigError(
            "Each [[site.versioning.variants]] entry must be a TOML table."
        )
    name = ensure_url_safe_name(_string(raw, "name"))
    source_value = _string(raw, "source")
    if source_value == "working_tree":
        source: SiteVariantSource = "working_tree"
    elif source_value == "release":
        source = "release"
    elif source_value == "git_ref":
        source = "git_ref"
    else:
        raise ConfigError(
            f"Variant '{name}' uses unsupported source '{source_value}'. "
            "Choose working_tree, release, or git_ref."
        )
    ref_value = raw.get("ref")
    ref = None
    if ref_value is not None:
        if not isinstance(ref_value, str) or not ref_value.strip():
            raise ConfigError(
                f"Variant '{name}' field 'ref' must be a non-empty string."
            )
        ref = ref_value
    if source == "git_ref" and ref is None:
        raise ConfigError(f"Variant '{name}' with source 'git_ref' requires a ref.")
    if source != "git_ref" and ref is not None:
        raise ConfigError(
            f"Variant '{name}' may define 'ref' only when source = 'git_ref'."
        )
    url_segment_value = raw.get("url_segment", "")
    if not isinstance(url_segment_value, str):
        raise ConfigError(f"Variant '{name}' field 'url_segment' must be a string.")
    return SiteVariantConfig(
        name=name,
        label=_string(raw, "label", default=name),
        source=source,
        ref=ref,
        url_segment=ensure_variant_segment(url_segment_value),
    )


def _legacy_site_versioning() -> SiteVersioningConfig:
    return SiteVersioningConfig(
        enabled=False,
        default="legacy",
        variants=[
            SiteVariantConfig(
                name="legacy",
                label="Working tree",
                source="working_tree",
                url_segment="",
            )
        ],
    )
