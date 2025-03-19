"""The main function that converts a source code string into LaTeX
representations of its statements.
"""

from typing import Optional, Any

import rubberize.vendor.ast_comments as ast_c

from rubberize.latexer.node_visitors import ModVistor
from rubberize.latexer.stmt_latex import StmtLatex


def latexer(
    source: str, namespace: Optional[dict[str, Any]]
) -> list[StmtLatex]:
    """Convert source code into LaTeX representations of its statements.

    This function is the heart of the library (so dramatic!). It parses
    the given source code string into an AST and applies `ModVistor` to
    traverse it, producing a list of `StmtLatex` representations.

    Args:
        source: The source code string to process.
        namespace: A dictionary of identifier and object pairs.

    Returns:
        A list of `StmtLatex` objects representing the LaTeX output
        of the processed statements.
    """

    source_ast = ast_c.parse(source)
    return ModVistor(namespace).visit(source_ast)
