"""Validation helpers for config, projects, and generated output."""

from __future__ import annotations

import shutil
from pathlib import Path

from .book_builder import create_aggregate_project
from .env_manager import prepare_build_environment
from .errors import SphinxBuildError, ValidationError
from .jekyll_writer import parse_nav_yaml
from .models import AppConfig, ProjectConfig
from .site_builder import build_site
from .source_manager import python_paths_for_target, resolve_site_targets
from .sphinx_runner import run_sphinx


def run_check(config: AppConfig, projects: list[ProjectConfig]) -> None:
    sphinx_build = prepare_build_environment(config, projects)
    _check_sphinx_available(sphinx_build)
    _run_builder_checks(
        config, projects, include_linkcheck=False, sphinx_build=sphinx_build
    )


def run_validation(
    config: AppConfig,
    projects: list[ProjectConfig],
    *,
    include_linkcheck: bool,
) -> None:
    sphinx_build = prepare_build_environment(config, projects)
    _check_sphinx_available(sphinx_build)
    _run_builder_checks(
        config,
        projects,
        include_linkcheck=include_linkcheck,
        sphinx_build=sphinx_build,
    )
    _validate_generated_site(config, projects, sphinx_build=sphinx_build)
    _validate_aggregate_project(config, projects)


def _check_sphinx_available(command: str) -> None:
    if Path(command).is_absolute():
        if not Path(command).exists():
            raise ValidationError(f"Sphinx build command '{command}' does not exist.")
        return
    if shutil.which(command) is None:
        raise ValidationError(
            f"Sphinx build command '{command}' is not available on PATH."
        )


def _run_builder_checks(
    config: AppConfig,
    projects: list[ProjectConfig],
    *,
    include_linkcheck: bool,
    sphinx_build: str,
) -> None:
    for target in resolve_site_targets(config, projects):
        for builder in ["dummy", *(["linkcheck"] if include_linkcheck else [])]:
            try:
                run_sphinx(
                    builder=builder,
                    conf_dir=target.conf_dir,
                    src_dir=target.docs_root,
                    out_dir=config.build.work_dir
                    / "validate-build"
                    / builder
                    / target.project.name
                    / target.variant.name,
                    doctree_dir=config.build.work_dir
                    / "validate-build"
                    / "doctrees"
                    / target.project.name
                    / target.variant.name
                    / builder,
                    fail_on_warning=config.build.fail_on_warning,
                    sphinx_build=sphinx_build,
                    parallel=config.build.parallel,
                    log_dir=config.build.log_dir,
                    log_stem=f"validate-{target.project.name}-{target.variant.name}-{builder}",
                    python_paths=python_paths_for_target(target),
                    environment={
                        "SPHINXPRESS_DOCS_PROJECT": target.project.name,
                        "SPHINXPRESS_DOCS_VARIANT": target.variant.name,
                        "SPHINXPRESS_DOCS_REF": target.resolved_ref,
                        **(
                            {"SPHINXPRESS_DOCS_COMMIT": target.commit_sha}
                            if target.commit_sha
                            else {}
                        ),
                    },
                )
            except SphinxBuildError as exc:
                raise ValidationError(
                    f"Validation build failed for project '{target.project.name}', "
                    f"variant '{target.variant.name}'."
                ) from exc


def _validate_generated_site(
    config: AppConfig, projects: list[ProjectConfig], *, sphinx_build: str
) -> None:
    validation_root = config.build.work_dir / "validation-site"
    site_config = config.with_site_root(validation_root)
    outputs = build_site(site_config, projects, sphinx_build=sphinx_build)
    if not outputs:
        raise ValidationError("Site build produced no generated files.")

    for path in validation_root.rglob("*.md"):
        if not path.read_text(encoding="utf-8").startswith("---\n"):
            raise ValidationError(
                f"Generated Jekyll page '{path}' is missing front matter."
            )
        content = path.read_text(encoding="utf-8")
        if (
            '<div class="sphinxpress-doc">' in content
            and site_config.site.protect_liquid
        ):
            if content.count("{% raw %}") != 1 or content.count("{% endraw %}") != 1:
                raise ValidationError(
                    f"Generated page '{path}' does not contain one balanced "
                    "sphinxpress Liquid raw wrapper."
                )

    nav_root = validation_root / config.site.nav_data_dir
    seen_nav_keys: set[str] = set()
    for nav_path in sorted(nav_root.glob("*.yml")):
        payload = parse_nav_yaml(nav_path)
        nav_key = payload.get("nav_key")
        if isinstance(nav_key, str):
            if nav_key in seen_nav_keys:
                raise ValidationError(
                    f"Duplicate nav key '{nav_key}' found in nav data."
                )
            seen_nav_keys.add(nav_key)
        for version in payload.get("versions", []):
            url = version["url"].strip("/")
            relative = Path(url)
            page_path = validation_root / relative / "index.md"
            if not page_path.exists():
                page_path = validation_root / relative.with_suffix(".md")
            if not page_path.exists():
                raise ValidationError(
                    f"Version link '{version['url']}' in {nav_path.name} does not "
                    "reference a generated page."
                )
        for entry in payload.get("entries", []):
            url = entry["url"].strip("/")
            relative = Path(url)
            page_path = validation_root / relative / "index.md"
            if not page_path.exists():
                page_path = validation_root / relative.with_suffix(".md")
            if not page_path.exists():
                raise ValidationError(
                    f"Navigation entry '{entry['url']}' in "
                    f"{nav_path.name} does not reference a generated page."
                )
    manifest_path = config.build.work_dir / "site-output-manifest.json"
    if not manifest_path.exists():
        raise ValidationError("Site build did not write a generated-output manifest.")


def _validate_aggregate_project(
    config: AppConfig, projects: list[ProjectConfig]
) -> None:
    aggregate = create_aggregate_project(config, projects)
    conf_py = aggregate.source_dir / "conf.py"
    index_rst = aggregate.source_dir / "index.rst"
    if not conf_py.exists() or not index_rst.exists():
        raise ValidationError("Aggregate book project was not created correctly.")
