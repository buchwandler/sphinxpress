"""Typed models used across sphinxpress."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from .errors import ConfigError

ReleaseStrategy = Literal["manual", "git_tag", "pyproject"]
BookFormat = Literal["pdf", "epub"]


@dataclass(frozen=True)
class SiteConfig:
    root: Path
    base_url: str
    tools_dir: Path
    nav_data_dir: Path
    layout: str
    title: str


@dataclass(frozen=True)
class BuildConfig:
    work_dir: Path
    sphinx_build: str
    fail_on_warning: bool
    keep_build_dir: bool
    parallel: str


@dataclass(frozen=True)
class BookConfig:
    title: str
    author: str
    language: str
    project_order: list[str]


@dataclass(frozen=True)
class OutputConfig:
    builder: str
    output: Path


@dataclass(frozen=True)
class ReleaseConfig:
    tag_prefix: str = "v"
    release_url_template: str = "{repo_url}/releases/tag/{tag}"


@dataclass(frozen=True)
class ProjectConfig:
    name: str
    title: str
    docs_root: Path
    conf_dir: Path
    root_doc: str
    repo_url: str
    release_strategy: ReleaseStrategy
    release_tag: str | None = None

    @property
    def conf_py(self) -> Path:
        return self.conf_dir / "conf.py"

    def root_doc_candidates(self) -> list[Path]:
        return [
            self.docs_root / f"{self.root_doc}.rst",
            self.docs_root / f"{self.root_doc}.md",
            self.docs_root / self.root_doc,
        ]

    def require_root_doc_path(self) -> Path:
        for candidate in self.root_doc_candidates():
            if candidate.exists():
                return candidate
        raise ConfigError(
            f"Project '{self.name}' is missing its configured root_doc "
            f"'{self.root_doc}' under {self.docs_root}"
        )


@dataclass(frozen=True)
class AppConfig:
    config_path: Path
    site: SiteConfig
    build: BuildConfig
    book: BookConfig
    pdf: OutputConfig
    epub: OutputConfig
    release: ReleaseConfig
    projects: list[ProjectConfig]

    def project_map(self) -> dict[str, ProjectConfig]:
        return {project.name: project for project in self.projects}

    def require_project(self, name: str) -> ProjectConfig:
        project = self.project_map().get(name)
        if project is None:
            raise ConfigError(f"Unknown project '{name}'.")
        return project

    def ordered_projects(self, names: list[str] | None = None) -> list[ProjectConfig]:
        selected = (
            self.projects
            if names is None
            else [self.require_project(name) for name in names]
        )
        if names is not None:
            return selected

        order = {name: index for index, name in enumerate(self.book.project_order)}
        return sorted(
            selected,
            key=lambda project: (order.get(project.name, len(order)), project.name),
        )

    def with_site_root(self, root: Path) -> AppConfig:
        return replace(self, site=replace(self.site, root=root))

    def with_work_dir(self, work_dir: Path) -> AppConfig:
        return replace(self, build=replace(self.build, work_dir=work_dir))


@dataclass(frozen=True)
class ReleaseMetadata:
    tag: str
    url: str


@dataclass(frozen=True)
class PageRender:
    docname: str
    title: str
    body_html: str
    output_path: Path
    permalink: str


@dataclass(frozen=True)
class NavEntry:
    slug: str
    title: str
    url: str


@dataclass(frozen=True)
class AggregateProject:
    root: Path
    source_dir: Path
    build_dir: Path
    doctree_dir: Path
