"""Validation helpers for config, projects, and generated output."""

from __future__ import annotations

import shutil
from pathlib import Path

from .book_builder import create_aggregate_project
from .errors import ValidationError
from .jekyll_writer import parse_nav_yaml
from .models import AppConfig, ProjectConfig
from .site_builder import build_site
from .sphinx_runner import run_sphinx


def run_check(config: AppConfig, projects: list[ProjectConfig]) -> None:
    _check_sphinx_available(config)
    _run_builder_checks(config, projects, include_linkcheck=False)


def run_validation(
    config: AppConfig,
    projects: list[ProjectConfig],
    *,
    include_linkcheck: bool,
) -> None:
    _check_sphinx_available(config)
    _run_builder_checks(config, projects, include_linkcheck=include_linkcheck)
    _validate_generated_site(config, projects)
    _validate_aggregate_project(config, projects)


def _check_sphinx_available(config: AppConfig) -> None:
    command = config.build.sphinx_build
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
) -> None:
    for project in projects:
        for builder in ["dummy", *(["linkcheck"] if include_linkcheck else [])]:
            run_sphinx(
                builder=builder,
                conf_dir=project.conf_dir,
                src_dir=project.docs_root,
                out_dir=config.build.work_dir
                / "validate-build"
                / builder
                / project.name,
                doctree_dir=config.build.work_dir
                / "validate-build"
                / "doctrees"
                / project.name
                / builder,
                fail_on_warning=config.build.fail_on_warning,
                sphinx_build=config.build.sphinx_build,
                parallel=config.build.parallel,
            )


def _validate_generated_site(config: AppConfig, projects: list[ProjectConfig]) -> None:
    validation_root = config.build.work_dir / "validation-site"
    site_config = config.with_site_root(validation_root)
    outputs = build_site(site_config, projects)
    if not outputs:
        raise ValidationError("Site build produced no generated files.")

    for path in validation_root.rglob("*.md"):
        if not path.read_text(encoding="utf-8").startswith("---\n"):
            raise ValidationError(
                f"Generated Jekyll page '{path}' is missing front matter."
            )

    nav_root = validation_root / config.site.nav_data_dir
    for nav_path in sorted(nav_root.glob("*.yml")):
        payload = parse_nav_yaml(nav_path)
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


def _validate_aggregate_project(
    config: AppConfig, projects: list[ProjectConfig]
) -> None:
    aggregate = create_aggregate_project(config, projects)
    conf_py = aggregate.source_dir / "conf.py"
    index_rst = aggregate.source_dir / "index.rst"
    if not conf_py.exists() or not index_rst.exists():
        raise ValidationError("Aggregate book project was not created correctly.")
