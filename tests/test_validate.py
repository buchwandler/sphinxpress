from __future__ import annotations

import textwrap

import pytest
from conftest import write_config

from sphinxpress.config import load_config
from sphinxpress.errors import ConfigError, ValidationError
from sphinxpress.validate import run_check, run_validation


def test_validate_detects_broken_nav_entry(monkeypatch, tmp_path, minimal_project_root):
    config_path = write_config(
        tmp_path,
        projects=[
            {
                "name": "booktx",
                "docs_root": str(minimal_project_root / "docs"),
                "release_tag": "v0.4.0",
            }
        ],
    )
    config = load_config(config_path)

    monkeypatch.setattr(
        "sphinxpress.validate._check_sphinx_available", lambda command: None
    )
    monkeypatch.setattr(
        "sphinxpress.validate._run_builder_checks",
        lambda config, projects, include_linkcheck, sphinx_build: None,
    )

    def fake_build_site(site_config, projects, *, sphinx_build):
        nav_root = site_config.site.root / site_config.site.nav_data_dir
        nav_root.mkdir(parents=True, exist_ok=True)
        (nav_root / "booktx.yml").write_text(
            textwrap.dedent(
                """
                tool: booktx
                repo_url: "https://example.com/booktx"
                release_tag: "v0.4.0"
                release_url: "https://example.com/booktx/releases/tag/v0.4.0"
                entries:
                  - slug: index
                    title: "booktx"
                    url: /tools/booktx/
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        return [nav_root / "booktx.yml"]

    monkeypatch.setattr("sphinxpress.validate.build_site", fake_build_site)

    with pytest.raises(ValidationError, match="does not reference a generated page"):
        run_validation(config, config.projects, include_linkcheck=False)


def test_validate_detects_missing_root_doc(tmp_path):
    docs_root = tmp_path / "docs"
    docs_root.mkdir()
    (docs_root / "conf.py").write_text(
        "project = 'Example'\nroot_doc = 'index'\n", encoding="utf-8"
    )
    config_path = write_config(
        tmp_path,
        projects=[
            {
                "name": "booktx",
                "docs_root": str(docs_root),
                "release_tag": "v0.4.0",
            }
        ],
    )

    with pytest.raises(ConfigError, match="missing its configured root_doc"):
        load_config(config_path)


def test_validate_runs_dummy_builder(monkeypatch, minimal_config_path):
    config = load_config(minimal_config_path)
    seen = []

    monkeypatch.setattr(
        "sphinxpress.validate._check_sphinx_available", lambda command: None
    )

    def fake_run_sphinx(**kwargs):
        seen.append(kwargs["builder"])

    monkeypatch.setattr("sphinxpress.validate.run_sphinx", fake_run_sphinx)

    run_check(config, config.projects)

    assert seen == ["dummy"]


def test_validate_detects_broken_version_switch(
    monkeypatch, tmp_path, minimal_project_root
):
    config_path = write_config(
        tmp_path,
        projects=[
            {
                "name": "booktx",
                "docs_root": str(minimal_project_root / "docs"),
                "release_tag": "v0.4.0",
            }
        ],
    )
    config = load_config(config_path)

    monkeypatch.setattr(
        "sphinxpress.validate._check_sphinx_available", lambda command: None
    )
    monkeypatch.setattr(
        "sphinxpress.validate._run_builder_checks",
        lambda config, projects, include_linkcheck, sphinx_build: None,
    )

    def fake_build_site(site_config, projects, *, sphinx_build):
        site_root = site_config.site.root
        tools_root = site_root / "tools" / "booktx"
        tools_root.mkdir(parents=True, exist_ok=True)
        (tools_root / "index.md").write_text(
            (
                "---\nlayout: tool-doc\n---\n"
                '{% raw %}<div class="sphinxpress-doc"></div>{% endraw %}\n'
            ),
            encoding="utf-8",
        )
        nav_root = site_root / site_config.site.nav_data_dir
        nav_root.mkdir(parents=True, exist_ok=True)
        (nav_root / "booktx.yml").write_text(
            textwrap.dedent(
                """
                tool: booktx
                nav_key: booktx
                variant: release
                variant_label: Latest release
                variant_kind: release
                source_ref: v0.4.0
                source_commit: "1234567"
                source_url: https://example.com/booktx/releases/tag/v0.4.0
                is_default: true
                release_tag: v0.4.0
                release_url: https://example.com/booktx/releases/tag/v0.4.0
                versions:
                  - name: release
                    label: Latest release
                    ref: v0.4.0
                    url: /tools/booktx/
                    current: true
                  - name: main
                    label: Current main
                    ref: main
                    url: /tools/booktx/main/
                    current: false
                entries:
                  - slug: index
                    title: booktx
                    url: /tools/booktx/
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        manifest = config.build.work_dir / "site-output-manifest.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(
            '{"version": 1, "targets": {}, "shared": []}\n', encoding="utf-8"
        )
        return [tools_root / "index.md", nav_root / "booktx.yml"]

    monkeypatch.setattr("sphinxpress.validate.build_site", fake_build_site)

    with pytest.raises(ValidationError, match="Version link '/tools/booktx/main/'"):
        run_validation(config, config.projects, include_linkcheck=False)
