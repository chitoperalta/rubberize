"""Renders LaTeX to HTML with Mathjax."""

from __future__ import annotations

import re
import textwrap
from typing import TYPE_CHECKING

from markdown import markdown

from rubberize.render.md_extensions import (
    Alert,
    InlineRubberize,
    LatexLinebreak,
    Small,
)

if TYPE_CHECKING:
    from rubberize.latexer.stmt_latex import StmtLatex


def render(
    latexes: list[StmtLatex],
    ns: dict[str, object] | None = None,
    *,
    grid: bool = False,
) -> str:
    """Render a list of StmtLatex to HTML with Mathjax.

    Args:
        latexes: The list of StmtLatex to render.
        namespace: A dictionary of identifier and object pairs, used for
            code in inline comments.
        grid: If True, arrange rendered statements on a grid.
    """

    htmls = []
    for l in latexes:
        htmls.append(_stmt_html(l, ns, grid=grid))

    if grid:
        return _html_tag("div", "\n".join(htmls), class_="rz-grid-container")

    return "\n".join(htmls)


def _stmt_html(
    stmt: StmtLatex, ns: dict[str, object] | None = None, *, grid: bool = False
) -> str:

    if stmt.latex is not None:
        latex = _mathjax_tag(stmt.latex)
    else:
        latex = None

    if stmt.desc is not None:
        desc, flags, npflags = _desc_html_and_flags(stmt.desc, ns)
    else:
        desc, flags, npflags = None, set(), set()

    if grid:
        desc = None

    classes = " ".join(
        ["rz-line"]
        + [f"rz-line--{f}" for f in flags]
        + [f"rz-line--{f}-noprint" for f in npflags]
    )

    html = ""
    if latex and desc:
        desc = desc.removeprefix("<p>").removesuffix("</p>")
        latex_html = _html_tag("div", latex, class_="rz-line__main")
        desc_html = _html_tag("div", desc, class_="rz-line__desc")
        content = "\n".join([latex_html, desc_html])
        html += _html_tag("div", content, class_=classes)
    elif latex and not desc:
        html += _html_tag("div", latex, class_=classes)
    elif not latex and desc:
        desc = desc.removeprefix("<p>").removesuffix("</p>")
        html += _html_tag("div", desc, class_=classes)

    body_lines: list[str] = []
    for b in stmt.body:
        body_lines.append(_stmt_html(b))

    if body_lines and html:
        html += "\n" + _html_tag("div", "\n".join(body_lines), class_="rz-body")
    else:
        html += "\n".join(body_lines)

    return html


def _mathjax_tag(latex: str, *, indent: int = 4) -> str:
    # "<" needs HTML escaping when it's next to a letter
    latex = re.sub(r"<(?=[a-zA-Z])", "&lt;", latex)

    mathjax = r"\( \displaystyle "

    if "\n" in latex:
        latex = "\n" + textwrap.indent(latex, " " * indent) + "\n"

    mathjax += latex + r" \)"

    return mathjax


def _html_tag(
    tag: str, content: str, *, indent: int = 4, **kwargs: str | None
) -> str:

    html = f"<{tag}"
    for k, v in kwargs.items():
        html += f' {k.rstrip("_")}="{v}"' if v is not None else ""
    html += ">"

    if "\n" in content:
        content = "\n" + textwrap.indent(content, " " * indent) + "\n"

    html += content + f"</{tag}>"

    return html


def _desc_html_and_flags(
    desc: str, ns: dict[str, object] | None
) -> tuple[str | None, set[str], set[str]]:
    flag_re = r"(?:(?<=\s)|^)\!(\w[\w_]*)"
    npflag_re = r"(?:(?<=\s)|^)\?(\w[\w_]*)"

    flags = {m.group(1) for m in re.finditer(flag_re, desc)}
    desc = re.sub(flag_re, "", desc)

    npflags = {m.group(1) for m in re.finditer(npflag_re, desc)}
    desc = re.sub(npflag_re, "", desc)

    ext = ["tables", Alert(), InlineRubberize(ns), LatexLinebreak(), Small()]
    desc = markdown(desc, extensions=ext)

    return desc, flags - npflags, npflags
