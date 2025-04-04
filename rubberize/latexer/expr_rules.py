"""Syntax rules for converting expression nodes to LaTeX.

This module provides mappings for various expresison elements to their
corresponding LaTeX representations. This module serves as the
foundational component for `ExprVisitor`.

Constants:
    GREEK: Greek (and Hebrew) letters.
    ACCENTS: Identifier accents mappings.
    MODIFIERS: Identifier modifier mappings.
    COLLECTIONS_ROW: Syntax mappings for lists, tuples, sets, and dicts
        displayed horizontally.
    COLLECTIONS_COL: Syntax mappings for lists, tuples, sets, and dicts
        displayed vertically.
    THOUSANDS_SEPARATOR: Thousand separator mappings.
    DECIMAL_MARKER: Decimal marker mappings.
    BOOL_OPS: Syntax mappings for boolean operations.
    BIN_OPS: Syntax mappings and rules for binary operations.
    UNARY_OPS: Syntax mappings for unary operations.
    COMPARE_OPS: Syntax mappings for comparisons.
"""

import ast
from dataclasses import dataclass, field


# Greek letters
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


# Identifier accents
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


# Identifier modifiers
MODIFIERS: dict[str, str] = {
    "_prime": "'",
    "_star": "^{*}",
    "_sstar": "^{**}",
    "_ssstar": "^{***}",
    "_sssstar": "^{****}",
}

# Collections syntax
COLLECTIONS_ROW: dict[type, tuple[str, tuple[str, str]]] = {
    list: (r" & ", (r"\begin{pmatrix}", r"\end{pmatrix}")),
    tuple: (r",\, ", (r"\left(", r"\right)")),
    set: (r",\, ", (r"\left\{", r"\right\}")),
    dict: (r",\, ", (r"\left\{", r"\right\}")),
}

# fmt: off
COLLECTIONS_COL: dict[type, tuple[str, tuple[str, str]]] = {
    list: (r" \\ ", (r"\begin{pmatrix}", r"\end{pmatrix}")),
    tuple: (r" \\ ", (r"\left(" + "\n" + r"\begin{array}{c}", r"\end{array}" + "\n" + r"\right)")),
    set: (r" \\ ", (r"\left\{" + "\n" + r"\begin{array}{c}", r"\end{array}" + "\n" + r"\right\}")),
    # pylint: disable-next=line-too-long
    dict: (r" \\" + "\n", (r"\left\{" + "\n" + r"\begin{aligned}", r"\end{aligned}" + "\n" + r"\right\}")),
}
# fmt: on

# Float format markers
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

# Boolean operators
BOOL_OPS: dict[type[ast.boolop], str] = {
    ast.And: r" \land ",
    ast.Or: r" \lor ",
}


# Binary operators
@dataclass(frozen=True)
class _BinOpdRule:
    """Syntax rules for an operand of a binary operation.

    Attributes:
        wrap (bool): Whether to wrap the operand in parentheses based on
            normal precedence rules.
        non_assoc (bool): Whether the operand side is non-associative,
            thus force wrapping the operand in parentheses if the
            operand has the same rank as the operator.
    """

    wrap: bool = True
    non_assoc: bool = False


@dataclass(frozen=True)
class _BinOpRule:
    """Syntax rules for an operator of a binary operation.

    Attributes:
        prefix (str): Syntax left of the left operand.
        infix (str): String in between the operands.
        suffix (str): String right of the right operand.
        left (_BinOpdRule): Syntax rules for the left operand. Defaults
            to a `_BinOpdRule` default instance.
        right (_BinOpdRule): Syntax rules for the right operand.
            Defaults to a `_BinOpdRule` default instance.
        is_wrapped (bool): Whether the syntax results to a bracketed
            LaTeX expression. Defaults to False.
    """

    prefix: str
    infix: str
    suffix: str
    left: _BinOpdRule = field(default_factory=_BinOpdRule)
    right: _BinOpdRule = field(default_factory=_BinOpdRule)
    is_wrapped: bool = False


# fmt: off
BIN_OPS: dict[type[ast.operator], _BinOpRule] = {
    ast.Add: _BinOpRule("", " + ", ""),
    ast.Sub: _BinOpRule("", " - ", "", right=_BinOpdRule(non_assoc=True)),
    ast.Mult: _BinOpRule("", r" \cdot ", ""),
    ast.MatMult: _BinOpRule("", r" \cdot ", ""),
    # pylint: disable-next=line-too-long
    ast.Div: _BinOpRule(r"\frac{", "}{", "}", left=_BinOpdRule(wrap=False), right=_BinOpdRule(wrap=False)),
    ast.Mod: _BinOpRule("", r" \mathbin{\%} ", "", right=_BinOpdRule(non_assoc=True)),
    # pylint: disable-next=line-too-long
    ast.Pow: _BinOpRule("", "^{", "}", left=_BinOpdRule(non_assoc=True), right=_BinOpdRule(wrap=False)),
    ast.LShift: _BinOpRule("", r" \ll ", "", right=_BinOpdRule(non_assoc=True)),
    ast.RShift: _BinOpRule("", r" \gg ", "", right=_BinOpdRule(non_assoc=True)),
    ast.BitOr: _BinOpRule("", r" \mathbin{|} ", ""),
    ast.BitXor: _BinOpRule("", r" \oplus ", ""),
    ast.BitAnd: _BinOpRule("", r" \mathbin{\&} ", ""),
    # pylint: disable-next=line-too-long
    ast.FloorDiv: _BinOpRule(r"\left\lfloor\frac{", "}{", r"}\right\rfloor", left=_BinOpdRule(wrap=False), right=_BinOpdRule(wrap=False), is_wrapped=True),
}
# fmt: on


# Unary operators
UNARY_OPS: dict[type[ast.unaryop], str] = {
    ast.Invert: r"\mathord{\sim} ",
    ast.UAdd: "+",
    ast.USub: "-",
    ast.Not: r"\lnot ",
}


# Comparison operators
COMPARE_OPS: dict[type[ast.cmpop], str] = {
    ast.Eq: "=",
    ast.NotEq: r"\ne",
    ast.Lt: "<",
    ast.LtE: r"\le",
    ast.Gt: ">",
    ast.GtE: r"\ge",
    ast.Is: r"\equiv",
    ast.IsNot: r"\not\equiv",
    ast.In: r"\in",
    ast.NotIn: r"\notin",
}
