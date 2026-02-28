"""Class for holding the generated LaTeX representation of a Python
statement. It is meant to be processed by the render step.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StmtLatex:
    """LaTeX representation of a statement node.

    Attributes:
        latex: The LaTeX representation of the statement node. Note that
            it's possible for a statement to be *headless*, in which
            case this attribute is `None`.
        desc: The description of the statement node, which usually is
            parsed from the inline comment of the statement. Defaults to
            `None`.
        body: A list of `StmtLatex` if the statement has a body, i.e., a
            statement block such as a function definition or an if
            statement. Defaults to an empty list.
    """

    latex: Optional[str]
    desc: Optional[str] = None
    body: list["StmtLatex"] = field(default_factory=list)
