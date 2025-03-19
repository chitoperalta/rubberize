"""The main function that typesets LaTeX representation of statements
and their descriptions to HTML with Mathjax support.
"""

import re
from typing import Any, Optional, TYPE_CHECKING

from markdown import markdown

from rubberize.render.md_extensions.alert import Alert
from rubberize.render.md_extensions.irbz import Irbz
from rubberize.render.md_extensions.latex_linebreak import LatexLinebreak
from rubberize.render.md_extensions.small import Small
from rubberize.utils import find_and_sub, wrap_delims
from rubberize.utils import html_tag

if TYPE_CHECKING:
    from rubberize.latexer.stmt_latex import StmtLatex


def render(
    latex_list: list["StmtLatex"],
    namespace: Optional[dict[str, Any]],
    *,
    grid: bool = False,
) -> str:
    """Render the Python code to HTML with Mathjax support.

    This function takes a list of `StmtLatex` instances, wraps LaTeX in
    `\\( \\)` for Mathjax conversion, converts Markdown syntax to HTML,
    and applies `<div>` tags as necessary to format.

    Args:
        latex_list: A list of `StmtLatex`, which usually comes from
            `latexer()`.
        namespace: A dictionary of identifier and object pairs.

    Returns:
        The HTML string for list of `StmtLatex`.
    """

    html = []
    for latex in latex_list:
        html.append(_stmt_html(latex, namespace, grid=grid))

    if grid:
        return html_tag("div", html, _class="rz-grid-container")
    return "\n".join(html)


def _stmt_html(
    latex: "StmtLatex",
    namespace: Optional[dict[str, Any]] = None,
    *,
    grid: bool = False,
) -> str:
    """Transform a single `StmtLatex` instance into HTML."""

    main = _mathjax(latex.latex) if latex.latex else None
    desc, classes, classes_noprint = _md_and_classes(latex.desc, namespace)

    if grid:
        desc = None

    line_classes = " ".join(
        ["rz-line"]
        + [f"rz-line--{c}" for c in classes]
        + [f"rz-line--{c_noprint}-noprint" for c_noprint in classes_noprint]
    )

    html = ""
    if main and desc:
        desc = desc.removeprefix("<p>").removesuffix("</p>")
        main_html = html_tag("div", main, _class="rz-line__main")
        desc_html = html_tag("div", desc, _class="rz-line__desc")
        html += html_tag("div", [main_html, desc_html], _class=line_classes)
    elif main and not desc:
        html += html_tag("div", main, _class=line_classes)
    elif not main and desc:
        html += desc

    body_lines: list[str] = []
    for nested_latex in latex.body:
        body_lines.append(_stmt_html(nested_latex))

    if body_lines and html:
        html += "\n" + html_tag("div", body_lines, _class="rz-body")
    else:
        html += "\n".join(body_lines)

    return html


def _mathjax(latex: str, *, force_block: bool = False, indent: int = 4) -> str:
    """Wrap latex for MathJax display."""

    # "<" needs HTML escaping when it's next to a letter
    latex = re.sub(r"<(?=[a-zA-Z])", "&lt;", latex)

    return wrap_delims(
        latex,
        (r"\( \displaystyle", r"\)"),
        force_block=force_block,
        spaced_line=True,
        indent=indent,
    )


def _md_and_classes(
    desc: Optional[str], namespace: Optional[dict[str, Any]]
) -> tuple[str | None, set[str], set[str]]:
    """Process a description string."""

    if desc is None:
        return None, set(), set()

    classes, desc = find_and_sub(r"(?:(?<=\s)|^)\!(\w[\w_]*)", "", desc)
    classes_noprint, desc = find_and_sub(r"(?:(?<=\s)|^)\?(\w[\w_]*)", "", desc)

    desc = markdown(
        desc,
        extensions=[
            "tables",
            Alert(),
            Irbz(namespace),
            LatexLinebreak(),
            Small(),
        ],
    )

    return desc, set(classes) - set(classes_noprint), set(classes_noprint)
