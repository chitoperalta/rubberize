"""Class for holding the generated LaTeX of a Python expression."""

from dataclasses import dataclass

from rubberize.latexer.ranks import VALUE_RANK


@dataclass
class ExprLatex:
    """LaTeX representation of a Python expression.

    Attributes:
        latex: The LaTeX representation of the expression node.
        rank: The precedence rank of the expression. Used to determine
            if notationally the LaTeX should be wrapped in parentheses.
            Defaults to VALUE_RANK (the highest rank).
    """

    latex: str
    rank: int = VALUE_RANK
