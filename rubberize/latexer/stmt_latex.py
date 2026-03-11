"""Class for holding the generated LaTeX of a Python statement."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StmtLatex:
    """LaTeX representation of a Python statement.

    Attributes:
        latex: The LaTeX representation of the statement node. It's
            possible for a statement to be "headless", in which case
            this attribute is None.
        desc: The description of the statement, which is parsed from
            the inline comment. Defaults to None.
        body: If the statement is a block (e.g. if, def), LaTeX
            representation of its body is stored here. Defaults to an
            empty list.
    """

    latex: str | None
    desc: str | None = None
    body: list[StmtLatex] = field(default_factory=list)
