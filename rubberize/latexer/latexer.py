"""Convert a Python source code string into LaTeX."""

from __future__ import annotations

from typing import TYPE_CHECKING

import rubberize.vendor.ast_comments as ast_c
from rubberize.latexer.visitors import ModVisitor

if TYPE_CHECKING:
    from rubberize.latexer.stmt_latex import StmtLatex


def latex_from_ast(
    tree: ast_c.AST, ns: dict[str, object] | None
) -> list[StmtLatex]:
    """Get LaTeX for each stmt in the given tree.

    Args:
        tree: The AST to convert.
        ns: Name and object mapping.
    """
    return ModVisitor(ns).visit(tree)


def latexer(code: str, ns: dict[str, object] | None) -> list[StmtLatex]:
    """Convert Python source code into LaTeX.

    Args:
        code: The code to convert.
        ns: Name and object mapping.
    """

    tree = ast_c.parse(code)
    return latex_from_ast(tree, ns)
