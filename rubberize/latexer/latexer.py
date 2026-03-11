"""Convert a Python source code string into LaTeX."""

from __future__ import annotations

from typing import TYPE_CHECKING

import rubberize.vendor.ast_comments as ast_c
from rubberize.latexer.visitors import ModVisitor

if TYPE_CHECKING:
    from rubberize.latexer.stmt_latex import StmtLatex


def latexer(code: str, ns: dict[str, object] | None) -> list[StmtLatex]:
    """Convert Python source code into LaTeX for its statements.

    Args:
        code: The code to convert.
        ns: Name and object mapping.
    """

    tree = ast_c.parse(code)
    return ModVisitor(ns).visit(tree)
