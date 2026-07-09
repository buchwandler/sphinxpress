"""Create aggregate Sphinx projects for EPUB and PDF output."""

from __future__ import annotations

import ast
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .env_manager import prepare_build_environment
from .errors import ValidationError
from .models import AggregateProject, AppConfig, BookFormat, ProjectConfig
from .paths import copy_tree, ensure_within_root, reset_directory, write_text_if_changed
from .release import find_project_root
from .sphinx_runner import run_sphinx


def build_book(
    config: AppConfig,
    projects: list[ProjectConfig],
    *,
    format_name: BookFormat,
    sphinx_build: str | None = None,
) -> Path:
    aggregate = create_aggregate_project(config, projects)
    sphinx_build = sphinx_build or prepare_build_environment(config, projects)
    if format_name == "epub":
        out_dir = aggregate.build_dir / "epub"
        run_sphinx(
            builder=config.epub.builder,
            conf_dir=aggregate.source_dir,
            src_dir=aggregate.source_dir,
            out_dir=out_dir,
            doctree_dir=aggregate.doctree_dir,
            fail_on_warning=config.build.fail_on_warning,
            sphinx_build=sphinx_build,
            parallel=config.build.parallel,
        )
        return _copy_artifact(out_dir, "*.epub", config.epub.output)

    run_sphinx(
        builder=config.pdf.builder,
        conf_dir=aggregate.source_dir,
        src_dir=aggregate.source_dir,
        out_dir=aggregate.build_dir,
        doctree_dir=aggregate.doctree_dir,
        fail_on_warning=config.build.fail_on_warning,
        sphinx_build=sphinx_build,
        parallel=config.build.parallel,
    )
    return _copy_artifact(aggregate.build_dir, "*.pdf", config.pdf.output)


def create_aggregate_project(
    config: AppConfig,
    projects: list[ProjectConfig],
) -> AggregateProject:
    root = config.build.work_dir / "build" / "book"
    if not config.build.keep_build_dir:
        reset_directory(root)
    else:
        root.mkdir(parents=True, exist_ok=True)
    source_dir = root / "source"
    build_dir = root / "build"
    doctree_dir = build_dir / "doctrees"
    source_dir.mkdir(parents=True, exist_ok=True)
    build_dir.mkdir(parents=True, exist_ok=True)

    project_docnames: list[str] = []
    extensions = _collect_extensions(projects)
    python_paths = _collect_python_paths(projects)
    projects_root = source_dir / "projects"

    for project in projects:
        destination = ensure_within_root(source_dir, projects_root / project.name)
        copy_tree(project.docs_root, destination)
        project_docnames.append(f"projects/{project.name}/{project.root_doc}")

    env = _template_environment()
    conf_content = env.get_template("aggregate_conf.py.j2").render(
        title=config.book.title,
        author=config.book.author,
        language=config.book.language,
        version=config.book.version,
        copyright=config.book.copyright,
        suppress_warnings=config.book.suppress_warnings,
        extensions=extensions,
        python_paths=python_paths,
    )
    index_content = env.get_template("aggregate_index.rst.j2").render(
        title=config.book.title,
        underline="=" * len(config.book.title),
        docnames=project_docnames,
    )
    write_text_if_changed(source_dir / "conf.py", conf_content)
    write_text_if_changed(source_dir / "index.rst", index_content)
    return AggregateProject(
        root=root,
        source_dir=source_dir,
        build_dir=build_dir,
        doctree_dir=doctree_dir,
    )


def _collect_python_paths(projects: list[ProjectConfig]) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    for project in projects:
        project_root = find_project_root(project)
        candidates = [project_root]
        src_dir = project_root / "src"
        if src_dir.exists():
            candidates.append(src_dir)
        for candidate in candidates:
            resolved = str(candidate.resolve())
            if resolved not in seen:
                paths.append(resolved)
                seen.add(resolved)
    return paths


def _collect_extensions(projects: list[ProjectConfig]) -> list[str]:
    extensions: set[str] = set()
    for project in projects:
        extensions.update(_read_literal_extensions(project.conf_py))
    return sorted(extensions)


def _read_literal_extensions(conf_py: Path) -> list[str]:
    tree = ast.parse(conf_py.read_text(encoding="utf-8"), filename=str(conf_py))
    for statement in tree.body:
        if not isinstance(statement, ast.Assign):
            continue
        assigns_extensions = any(
            isinstance(target, ast.Name) and target.id == "extensions"
            for target in statement.targets
        )
        if not assigns_extensions:
            continue
        try:
            value = ast.literal_eval(statement.value)
        except (SyntaxError, ValueError) as exc:
            raise ValidationError(
                f"Aggregate book builds require a literal extensions list in {conf_py}."
            ) from exc
        invalid_extensions = not isinstance(value, list) or not all(
            isinstance(item, str) for item in value
        )
        if invalid_extensions:
            raise ValidationError(
                f"Aggregate book builds require a literal extensions list in {conf_py}."
            )
        return value
    return []


def _copy_artifact(search_root: Path, pattern: str, destination: Path) -> Path:
    artifacts = sorted(search_root.rglob(pattern))
    if not artifacts:
        raise ValidationError(
            f"Expected build artifact matching {pattern} under "
            f"{search_root}, but none was produced."
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(artifacts[0], destination)
    return destination


def _template_environment() -> Environment:
    template_dir = Path(__file__).with_name("templates")
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
