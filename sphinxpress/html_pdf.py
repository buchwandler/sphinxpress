"""Internal HTML-to-PDF helpers for aggregate book builds."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from .errors import ValidationError
from .models import AggregateProject, AppConfig
from .paths import write_text_if_changed
from .sphinx_runner import run_sphinx

_LINK_CLEANUPS = [
    (re.compile(r'href="index\.html#'), 'href="#'),
    (re.compile(r'href="\./index\.html#'), 'href="#'),
]


def build_weasyprint_pdf(
    config: AppConfig,
    aggregate: AggregateProject,
    *,
    sphinx_build: str,
    weasyprint_command: str,
) -> Path:
    html_dir = aggregate.build_dir / "singlehtml"
    pdf_dir = aggregate.build_dir / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    run_sphinx(
        builder="singlehtml",
        conf_dir=aggregate.source_dir,
        src_dir=aggregate.source_dir,
        out_dir=html_dir,
        doctree_dir=aggregate.doctree_dir / "singlehtml",
        fail_on_warning=config.build.fail_on_warning,
        sphinx_build=sphinx_build,
        parallel=config.build.parallel,
    )

    index_html = html_dir / "index.html"
    if not index_html.exists():
        raise ValidationError(f"Expected singlehtml output at {index_html}.")

    css_path = html_dir / "_static" / "sphinxpress-pdf.css"
    write_text_if_changed(css_path, default_pdf_css(config))
    patch_singlehtml_for_pdf(index_html, css_href="_static/sphinxpress-pdf.css")

    built_pdf = pdf_dir / "sphinxpress.pdf"
    run_weasyprint(
        weasyprint_command=weasyprint_command,
        input_html=index_html,
        output_pdf=built_pdf,
    )
    if not built_pdf.exists():
        raise ValidationError(f"Expected WeasyPrint output at {built_pdf}.")

    config.pdf.output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(built_pdf, config.pdf.output)
    return config.pdf.output


def patch_singlehtml_for_pdf(index_html: Path, *, css_href: str) -> None:
    html = index_html.read_text(encoding="utf-8")
    for pattern, replacement in _LINK_CLEANUPS:
        html = pattern.sub(replacement, html)

    if css_href not in html:
        link = f'<link rel="stylesheet" href="{css_href}" />'
        if "</head>" in html:
            html = html.replace("</head>", f"  {link}\n</head>", 1)
        else:
            html = f"{link}\n{html}"

    index_html.write_text(html, encoding="utf-8")


def default_pdf_css(config: AppConfig) -> str:
    title = config.book.title.replace("\\", "\\\\").replace('"', '\\"')
    return f"""
@page {{
  size: A4;
  margin: 20mm 16mm 22mm 16mm;
  @bottom-center {{
    content: "{title} · " counter(page);
    font-size: 9pt;
    color: #666;
  }}
}}

@media print {{
  body {{
    font-family: sans-serif;
    font-size: 10.5pt;
    line-height: 1.45;
  }}

  a {{
    color: inherit;
    text-decoration: none;
  }}

  h1, h2, h3 {{
    page-break-after: avoid;
  }}

  pre, code {{
    font-family: monospace;
  }}

  pre {{
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    border: 1px solid #ddd;
    padding: 0.8em;
    background: #f8f8f8;
  }}

  table {{
    border-collapse: collapse;
    width: 100%;
  }}

  th, td {{
    border: 1px solid #ddd;
    padding: 0.35em;
    vertical-align: top;
  }}

  img {{
    max-width: 100%;
  }}

  .sphinxsidebar,
  .sphinxsidebarwrapper,
  .related,
  .footer {{
    display: none !important;
  }}
}}
""".lstrip()


def run_weasyprint(
    *,
    weasyprint_command: str,
    input_html: Path,
    output_pdf: Path,
) -> None:
    command = [weasyprint_command, str(input_html), str(output_pdf)]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise ValidationError(
            f"WeasyPrint executable '{weasyprint_command}' was not found."
        ) from exc

    if result.returncode != 0:
        detail = "\n".join(
            part for part in [result.stdout.strip(), result.stderr.strip()] if part
        )
        raise ValidationError(
            "WeasyPrint PDF generation failed with exit code "
            f"{result.returncode}.\nCommand: {' '.join(command)}\n{detail}".rstrip()
        )
