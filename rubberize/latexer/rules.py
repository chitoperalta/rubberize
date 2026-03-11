"""Syntax rules for converting to LaTeX.

This module provides mappings for various expresison elements to their
corresponding LaTeX representations.
"""

# pylint: disable=line-too-long

import ast
from dataclasses import dataclass, field

from typing import Callable


OPERAND_SYNTAX: tuple[str, str] = r"\left(", r"\right)"

BOOL_OPS: dict[type[ast.boolop], str] = {
    ast.And: r" \land ",
    ast.Or: r" \lor ",
}
MULTI_BOOL_OP_SYNTAX: tuple[str, Callable[[str], str], str] = (
    r"\left\{" + "\n" + r"\begin{array}{l}",
    lambda op: r" \\" + "\n" + rf"{op.strip()}\ ",
    r"\end{array}" + "\n" + r"\right\}",
)

NAMED_EXPR_OP: str = r" \gets "


@dataclass(frozen=True)
class _BinOperand:
    """Syntax rules for an operand of a binary operation.

    Attributes:
        wrap: If True, wrap the operand in delimiters based on normal
            precedence rules.
        non_assoc: If True, the operand side is non-associative,
            thus force wrapping the operand in parentheses if the
            operand has the same rank as the operator.
    """

    wrap: bool = True
    non_assoc: bool = False


@dataclass(frozen=True)
class _BinOp:
    """Syntax rules for an operator of a binary operation.

    Attributes:
        prefix, infix, suffix: Syntax left, between, and right of the
            operands.
        left: Rules for the left operand.
        right Rules for the right operand
        is_wrapped: If True, the syntax results to a delimited form.
    """

    prefix: str
    infix: str
    suffix: str
    left: _BinOperand = field(default_factory=_BinOperand)
    right: _BinOperand = field(default_factory=_BinOperand)
    is_wrapped: bool = False


# fmt: off
BIN_OPS: dict[type[ast.operator], _BinOp] = {
    ast.Add: _BinOp("", " + ", ""),
    ast.Sub: _BinOp("", " - ", "", right=_BinOperand(non_assoc=True)),
    ast.Mult: _BinOp("", r" \cdot ", ""),
    ast.MatMult: _BinOp("", r" \cdot ", ""),
    ast.Div: _BinOp(r"\frac{", "}{", "}", left=_BinOperand(wrap=False), right=_BinOperand(wrap=False)),
    ast.Mod: _BinOp("", r" \mathbin{\%} ", "", right=_BinOperand(non_assoc=True)),
    ast.Pow: _BinOp("", "^{", "}", left=_BinOperand(non_assoc=True), right=_BinOperand(wrap=False)),
    ast.LShift: _BinOp("", r" \ll ", "", right=_BinOperand(non_assoc=True)),
    ast.RShift: _BinOp("", r" \gg ", "", right=_BinOperand(non_assoc=True)),
    ast.BitOr: _BinOp("", r" \mathbin{|} ", ""),
    ast.BitXor: _BinOp("", r" \oplus ", ""),
    ast.BitAnd: _BinOp("", r" \mathbin{\&} ", ""),
    ast.FloorDiv: _BinOp(r"\left\lfloor\frac{", "}{", r"}\right\rfloor", left=_BinOperand(wrap=False), right=_BinOperand(wrap=False), is_wrapped=True),
}
# fmt: on

UNARY_OPS: dict[type[ast.unaryop], str] = {
    ast.Invert: r"\mathord{\sim} ",
    ast.UAdd: "+",
    ast.USub: "-",
    ast.Not: r"\lnot ",
}

LAMBDA_OP: str = r" \mapsto "
LAMBDA_ARGS_SEP: str = r",\, "

PIECEWISE_SYNTAX: tuple[
    str, Callable[[str, str], str], str, Callable[[str], str], str
] = (
    r"\begin{cases}",
    lambda body, test: rf"\displaystyle {body}, &\text{{if}}\ {test}",
    r" \\" + "\n",
    lambda orelse: rf"\displaystyle {orelse}, &\text{{otherwise}}",
    r"\end{cases}",
)

# fmt: off
LIST_ROW_SYNTAX = r"\left[", r",\, ", r"\right]"
LIST_COL_SYNTAX = r"\left[" + "\n" + r"\begin{array}{c}", r" \\ ", r"\end{array}" + "\n" + r"\right]"

TUPLE_ROW_SYNTAX = r"\left(", r",\, ", r"\right)"
TUPLE_COL_SYNTAX = r"\left(" + "\n" + r"\begin{array}{c}", r" \\ ", r"\end{array}" + "\n" + r"\right)"

SET_ROW_SYNTAX = r"\left\{", r",\, ", r"\right\}"
SET_COL_SYNTAX = r"\left\{" + "\n" + r"\begin{array}{c}", r" \\ ", r"\end{array}" + "\n" + r"\right\}"

DICT_ROW_SYNTAX = r"\left\{", r",\, ", r"\right\}"
DICT_ROW_KV_SYNTAX: str = r" \to "
DICT_COL_SYNTAX = r"\left\{" + "\n" + r"\begin{aligned}", r" \\" + "\n", r"\end{aligned}" + "\n" + r"\right\}"
DICT_COL_KV_SYNTAX: str = r" &\to "

UNPACKING_UNION: str = r" \cup "

ARRAY_ROW_SYNTAX = r"\begin{pmatrix}", r" & ", r"\end{pmatrix}"
ARRAY_COL_SYNTAX = r"\begin{pmatrix}", r" \\ ", r"\end{pmatrix}"
# fmt: on

COMP_SUCH_THAT = r" \;\middle|\; "
COMP_ELEMENT_OF = r" \in "
COMP_AND = r" \land "

COMPARE_OPS: dict[type[ast.cmpop], str] = {
    ast.Eq: " = ",
    ast.NotEq: r" \ne ",
    ast.Lt: " < ",
    ast.LtE: r" \le ",
    ast.Gt: " > ",
    ast.GtE: r" \ge ",
    ast.Is: r" \equiv ",
    ast.IsNot: r" \not\equiv ",
    ast.In: r" \in ",
    ast.NotIn: r" \notin ",
}

CALL_ARGS_SYNTAX: tuple[str, str, str] = r"\left(", r",\, ", r"\right)"
KWARG_ASSIGN: str = r" \leftarrow "

SUBSCRIPT_SYNTAX: tuple[str, str, str] = r"\left(", r",\, ", r"\right)"

SLICE_SEP = " : "

THOUSANDS_SEPARATOR: dict[str, str] = {
    "": "",
    " ": r"\,",
    ",": r"{,}",
    ".": r"{.}",
    "'": r"\text{’}",
}

DECIMAL_MARKER: dict[str, str] = {
    ".": ".",
    ",": "{,}",
}

# fmt: off
GREEK: set[str] = {
    "alpha",
    "beta",
    "Gamma", "gamma",
    "Delta", "delta",
    "epsilon", "varepsilon",
    "zeta",
    "eta",
    "Theta", "theta", "vartheta",
    "iota",
    "kappa", "varkappa",
    "Lambda", "lambda",
    "mu",
    "nu",
    "Xi", "xi",
    "omicron",
    "Pi", "pi", "varpi",
    "rho", "varrho",
    "Sigma", "sigma", "varsigma",
    "tau",
    "Upsilon", "upsilon",
    "Phi", "phi", "varphi",
    "chi",
    "Psi", "psi",
    "Omega", "omega",
    "digamma",
    "aleph",
    "beth",
    "gimel"
}
# fmt: on

ACCENTS: dict[str, str] = {
    "_hat": r"\hat",
    "_widehat": r"\widehat",
    "_bar": r"\bar",
    "_widebar": r"\overline",
    "_tilde": r"\tilde",
    "_widetilde": r"\widetilde",
    "_dot": r"\dot",
    "_ddot": r"\ddot",
    "_dddot": r"\dddot",
    "_ddddot": r"\ddddot",
    "_breve": r"\breve",
    "_check": r"\check",
    "_acute": r"\acute",
    "_grave": r"\grave",
    "_ring": r"\mathring",
    "_mat": r"\mathbf",
    "_vec": r"\mathbf",
    "_vec2": r"\vec",
    "_widevec2": r"\overrightarrow",
}

MODIFIERS: dict[str, str] = {
    "_prime": "'",
    "_star": "^{*}",
    "_sstar": "^{**}",
    "_ssstar": "^{***}",
    "_sssstar": "^{****}",
    "_plusminus": r"^{\pm}",
    "_minusplus": r"^{\mp}",
    "_plus": "^{+}",
    "_minus": "^{-}",
    "_oplus": r"^{\oplus}",
    "_ominus": r"^{\ominus}",
}
