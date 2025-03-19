"""Class for holding the generated LaTeX representation of a Python
expression. It is meant to be processed further by operator visitors of
`ExprVisitor`, or its `latex` attribute is extracted by one of the
`expr_modes` functions for use in `StmtVisitor`.
"""

from dataclasses import dataclass

from rubberize.latexer.ranks import VALUE_RANK


@dataclass
class ExprLatex:
    """LaTeX representation of an expression node.

    Attributes:
        latex: The LaTeX representation of the expression node.
        rank: The precedence rank of the latex. Used by operator
            visitors to determine if the LaTeX will be wrapped in
            parentheses. Defaults to `VALUE_RANK`, the highest rank.
    """

    latex: str
    rank: int = VALUE_RANK
