"""Semantic block converter to LaTeX.

A semantic block is an expression statement or assignment that is
intended to be rendered as a whole rather than being part of a math
equation. Its meaning is determined by the object it references rather
than Python syntax.

A semantic block supports these patterns:
    1. Call: Foo(...), baz(...)   registry key: Foo, baz
    2. Method call: foo.bar(...)  registry key: Foo.bar
    3. Object reference: foo      registry key: type(foo) -> Foo
    4. Assigned versions of the above
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from rubberize.latexer import helpers
from rubberize.latexer.stmt_latex import StmtLatex

if TYPE_CHECKING:
    from typing import Callable


_block_converters: dict[
    object, Callable[[ast.expr, dict[str, object]], StmtLatex | None]
] = {}


def register_block_converter(
    block: object,
    func: Callable[[ast.expr, dict[str, object]], StmtLatex | None],
) -> None:
    """Register a converter function for a block type.

    Args:
        obj: The block the converter applies to.
        func: The converter function.
    """

    _block_converters[block] = func


def convert_block(
    node: ast.Expr | ast.Assign | ast.AnnAssign, ns: dict[str, object] | None
) -> StmtLatex | None:
    """Convert a block to LaTeX using a matching converter function.

    A semantic block supports these patterns:
    1. Call: Foo(...), baz(...)   registry key: Foo, baz
    2. Method call: foo.bar(...)  registry key: Foo.bar
    3. Object reference: foo      registry key: type(foo) -> Foo
    4. Assigned versions of the above
    """

    if ns is None:
        return None

    if isinstance(node.value, ast.Call):
        key = helpers.get_func_object(node.value, ns)
        if key is None:
            return None

    elif isinstance(node.value, (ast.Name, ast.Attribute)):
        obj = helpers.get_object(node.value, ns)
        if obj is None:
            return None

        key = type(obj)

    else:
        return None

    converter = _block_converters.get(key)
    if converter:
        return converter(node.value, ns)

    return None
