"""Helper functions that inspect AST nodes."""

from __future__ import annotations

import ast
import copy
import inspect
import re
from types import ModuleType
from typing import TYPE_CHECKING, overload

import rubberize.vendor.ast_comments as ast_c
from rubberize._exceptions import RubberizeTypeError
from rubberize.config import config, parse_modifiers
from rubberize.latexer import rules

if TYPE_CHECKING:
    from typing import Any, Callable, Mapping, Literal, Iterable, TypeVar

    _AstT = TypeVar("_AstT", bound=ast.AST)


def get_id(node: ast.expr) -> str | None:
    """Return the identifier of an attribute or name node.

    Args:
        node: The ast.expr node to investigate.

    Returns:
        The identifier or None if node is not an attribute or name.
    """

    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return None


def get_object(node: ast.expr, ns: dict[str, object] | None) -> Any | None:
    """Return the object of the ast.expr node directly from ns or by
    eval using ns as globals and a deepcopy of referenced names as
    locals.

    Deepcopy is needed to prevent changing mutable types when eval is
    run.

    Args:
        node: The ast.expr node to investigate.
        ns: Name and object mapping.

    Returns:
        The corresponding object from ns, object from eval(), or None if
        object cannot be retrieved or eval() fails.
    """

    if ns and isinstance(node, ast.Attribute):
        module = get_object(node.value, ns)
        if module is not None:
            return getattr(module, node.attr)

    if ns and isinstance(node, ast.Name):
        obj = ns.get(node.id)
        if obj is not None:
            return obj

    if isinstance(node, ast.Constant):
        return node.value

    try:
        if ns is None:
            return eval(ast.unparse(node))  # pylint: disable=eval-used

        ref_names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}

        ns_copy = {}
        for n in ref_names:
            if n not in ns:
                continue

            n_obj = ns[n]

            if isinstance(n_obj, ModuleType):
                continue

            try:
                import pint  # pylint: disable=import-outside-toplevel

                if isinstance(n_obj, (pint.UnitRegistry, pint.Quantity)):
                    # Pint quantities use the same unit registry
                    continue
            except ImportError:
                pass

            ns_copy[n] = copy.deepcopy(n_obj)

        return eval(ast.unparse(node), ns, ns_copy)  # pylint: disable=eval-used

    except NameError:
        return None


def get_func_object(
    node: ast.Call, ns: dict[str, object] | None
) -> Callable | None:
    """Return the function object of the ast.Call node.

    Args:
        node: The ast.Call node to investigate.
        ns: Name and object mapping.

    Returns:
        The corresponding function object.
    """

    func_obj = get_object(node.func, ns)

    if func_obj is not None:
        if inspect.ismethod(func_obj):
            return func_obj.__func__

        elif hasattr(func_obj, "__self__") and hasattr(func_obj, "__name__"):
            # handle bound built-in methods implemented in C
            return getattr(type(func_obj.__self__), func_obj.__name__, func_obj)

        else:
            return func_obj

    return None


def get_func_id(node: ast.Call, ns: dict[str, object] | None) -> str | None:
    """Return the actual function name, even if it is aliased. If ns is
    none, return the function id from the ast.Call node instead.

    Args:
        node: The ast.Call node to investigate.
        ns: Name and object mapping.
    """

    func_obj = get_func_object(node, ns)

    if func_obj is not None:
        return func_obj.__name__

    return get_id(node.func)


def get_desc(
    node: ast.AST,
) -> tuple[str | None, dict[str, bool | int | Iterable[str]]]:
    """Return the description and config override from a comment in an
    ast.AST node.

    Uses ast_comments.

    Args:
        node: The ast.AST node to investigate.

    Returns:
        A tuple of the description string, which can be None, and config
        overrides.
    """

    if not isinstance(node, ast_c.Comment):
        # maybe an inline comment:
        inline: ast_c.Comment | None = getattr(node, "comment", None)
        if inline is None:
            return None, {}
        node = inline

    comment = node.value[1:]

    # temporarily remove inline rubberize
    dummy = "\ue000"
    inline_rz_re = r"(?<!\\)(\{\{.*?\}\})"
    inline_rzs = [m.group(1) for m in re.finditer(inline_rz_re, comment)]
    comment = re.sub(inline_rz_re, dummy, comment)

    # extract modifiers
    modifier_re = (
        r"(?:(?<=\s)|^)@(\w[\w_]*"
        r"(?:=(?:{.*?}|\[.*?\]|\(.*?\)|\".*?\"|'.*?'|\S+))?)"
    )
    modifiers = [m.group(1) for m in re.finditer(modifier_re, comment)]
    comment = re.sub(r"\s*" + modifier_re, "", comment)

    # unescape
    comment = comment.replace(r"\{{", "{{").replace(r"\@", "@")

    # remove leading spaces
    comment = comment.lstrip()

    # normalize trailing spaces to 2 max
    n_space = len(comment) - len(comment.rstrip())
    comment = comment.rstrip() + " " * min(n_space, 2)

    # replace inline rubberize
    for i in inline_rzs:
        comment = comment.replace(dummy, i, 1)

    comment = comment if comment.strip() else None
    cfg = parse_modifiers(modifiers)

    return comment, cfg


def is_class(node: ast.expr, cls: type, ns: dict[str, object] | None) -> bool:
    """Check if the ast.expr node is an instance or subclass of cls.

    Args:
        node: The ast.expr node to investigate.
        cls: Class to check against.
        ns: Name and object mapping.
    """

    if ns is None:
        return False

    obj = get_object(node, ns)

    return isinstance(obj, cls)


def is_unit(node: ast.expr, ns: dict[str, object] | None) -> bool:
    """Check if the ast.expr node references a Pint unit.

    If Pint is not installed, returns False.

    Args:
        node: The ast.expr node to investigate.
        ns: Name and object mapping.
    """

    try:
        import pint  # pylint: disable=import-outside-toplevel

        return is_class(node, pint.Unit, ns)
    except ImportError:
        return False


def is_unit_assignment(node: ast.BinOp, ns: dict[str, object] | None) -> bool:
    """Check if the ast.BinOp node represents an assignment of a Pint
    unit.

    Args:
        node: The ast.expr node to investigate.
        ns: Name and object mapping.
    """

    return isinstance(node.op, (ast.Mult, ast.Div)) and is_unit(node.right, ns)


def is_ndarray(node: ast.expr, ns: dict[str, object] | None) -> bool:
    """Check if the ast.expr node references a NumPy ndarray.

    If Pint is not installed, returns False.

    Args:
        node: The ast.expr node to investigate.
        ns: Name and object mapping.
    """

    try:
        import numpy as np  # pylint: disable=import-outside-toplevel

        return is_class(node, np.ndarray, ns)
    except ImportError:
        return False


def get_mult_infix(node: ast.BinOp, left_latex: str, right_latex: str) -> str:
    """Get the appropriate sign for a multiplication ast.BinOp node.

    In mathematical notation, the symbol used for multiplication depends
    on the types of operands involved.

    For numerical values, the [SI Brochure][1] recommends using either
    the multiplication sign (x) or brackets instead of a mid-dot (·).
    However, when multiplying variable names, the sign should be omitted
    to avoid confusing it as another variable. Instead, variable names
    can be multiplied implicitly (e.g., a b instead of a·b).

    The decision on which multiplication symbol to use is governed by
    this matrix, where rows are left operand types and columns are right
    operand types:

       * N -N  L -L  W -W  C -C  B -B  ? -?
       N x  x     ⋅     ⋅     ⋅     ⋅  ⋅  ⋅
      -N x  x     ⋅     ⋅     ⋅     ⋅  ⋅  ⋅
       L ⋅  ⋅     ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅
      -L ⋅  ⋅     ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅
       W ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅
      -W ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅
       C ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅
      -C ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅
       B ⋅  ⋅     ⋅     ⋅     ⋅     ⋅  ⋅  ⋅
      -B ⋅  ⋅     ⋅     ⋅     ⋅     ⋅  ⋅  ⋅
       ? ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅
      -? ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅  ⋅

    The operand type is defined in the `get_operand_type()` docstring.

    [1]: https://www.bipm.org/en/publications/si-brochure/

    Args:
        node: The ast.BinOp node to investigate.
        left_latex: LaTeX representation of the left operand.
        right_latex: LaTeX representation of the right operand.
    """

    assert isinstance(node.op, ast.Mult)

    left_type = get_operand_type(node.left, left_latex, is_left=True)
    right_type = get_operand_type(node.right, right_latex, is_left=False)

    if left_type[-1] == "N" and right_type[-1] == "N":
        return r" \times "
    if right_type[-1] in "N?" or right_type[0] == "-":
        return rules.BIN_OPS[ast.Mult].infix
    if left_type[-1] in "NB":
        return r"\,"
    if left_type[-1] == "L" and right_type == "L":
        return r"\,"
    return rules.BIN_OPS[ast.Mult].infix


# pylint: disable=too-many-return-statements,too-many-branches
def get_operand_type(node: ast.expr, latex: str, is_left: bool) -> str:
    """Get the type of the ast.expr operand of an ast.BinOp node.

    Args:
        node: Operand ast.expr node to investigate.
        latex: LaTeX representation of the operand.
        is_left: Whether the node is a left operand.

    Returns:
        Any one of the following literals

        - "N": Operand is a numeric value.
        - "L": Operand is a letter variable (a single-character base
            name), including Greek letters.
        - "W": Operand is a word variables (with multiple characters
            for base name).
        - "C": Operand is a function call.
        - "B": Operand is a bracketed expression.
        - "?": Operand is of other type.

        Signed versions of each type are denoted by the "-" prefix.
    """

    if latex == r"\mathrm{i}":
        return "L"

    call_re = (
        r"(?:\\\w+ \\?\w+(?: \\?\w+)*"
        # r"|\\sqrt(?:\[\d+\])?\{.*?\}"
        r"|(?:\\operatorname\{[^}]+\}(?:_\{.*?\})?|\\\w+)"
        r" \\left\([\s\S]*?\\right\))"
    )
    call_patterns = {
        True: re.compile(f"{call_re}$"),
        False: re.compile(f"^{call_re}"),
    }

    bracket_patterns = {
        True: re.compile(r"(?:\\right[^ ,]+|\\end\{[^ },]+\})$"),
        False: re.compile(r"^(?:\\left[^ ,]+|\\begin\{[^ },]+\})"),
    }

    greek_start_re = "|".join(map(re.escape, config.greek_starts))
    word_re = rf"(?:\\(?:{greek_start_re}) )?" + r"\\mathrm\{.+\}(_\{.*?\})?"
    word_patterns = {
        True: re.compile(rf"(?:^|\ |\\\,){word_re}$"),
        False: re.compile(f"^{word_re}"),
    }

    number_re = (
        r"-?\d{1,3}(?:(?:\\,|\{[,.]\}|\\text\{’\})?\d{3})*"
        r"(?:(?:\.|\{,\})?\d+)?"
    )
    number_patterns = {
        True: re.compile(f"{number_re}$"),
        False: re.compile(f"^{number_re}"),
    }

    while True:
        if isinstance(node, ast.BinOp):
            if isinstance(node.op, (ast.Div, ast.FloorDiv)):
                return "B"
            if isinstance(node.op, ast.Pow):
                node = node.left
            else:
                node = node.right if is_left else node.left
        elif isinstance(node, ast.Compare):
            node = node.comparators[-1] if is_left else node.left
        elif isinstance(node, ast.BoolOp):
            node = node.values[-1] if is_left else node.values[0]
        else:
            break

    if isinstance(node, ast.UnaryOp):
        if isinstance(node.operand, ast.UnaryOp):
            return "-B"  # Nested unary is bracketed (e.g., -(-3))
        return "-" + get_operand_type(
            node.operand, latex.removeprefix("-"), is_left
        )

    if isinstance(node, ast.Call):
        if get_id(node.func) == "sqrt":
            return "B"
        if call_patterns[is_left].search(latex):
            return "C"
    if bracket_patterns[is_left].search(latex):
        return "B"
    if word_patterns[is_left].search(latex):
        return "W"

    number_search = number_patterns[is_left].search(latex)
    if number_search:
        return "-N" if number_search.group(0).startswith("-") else "N"

    if isinstance(node, ast.Name) and _is_id_single_char(node.id):
        return "L"

    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id in config.hidden_modules
        and _is_id_single_char(node.attr)
    ):
        return "L"

    return "?"


def _is_id_single_char(iden: str) -> bool:
    base = iden.strip("_").split("_", 1)[0]

    if config.use_symbols:
        if base in rules.GREEK:
            return True

        if base[:-1] in config.greek_starts:
            return True

    return len(base) == 1


def is_str_expr(node: ast.stmt) -> bool:
    """Check if the ast.stmt node is a string expression.

    Args:
        node: The ast.stmt node to investigate.
    """

    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def strip_docstring(node: _AstT) -> _AstT:
    """Return a copy of the given AST node with the docstring, if any,
    removed.
    """

    node = copy.deepcopy(node)

    if not isinstance(
        node,
        (ast.AsyncFunctionDef, ast.FunctionDef, ast.ClassDef, ast.Module),
    ):
        return node

    # find first non-comment
    first = next(
        (stmt for stmt in node.body if not isinstance(stmt, ast_c.Comment)),
        None,
    )

    if first is not None and is_str_expr(first):
        node.body.remove(first)

    return node


def strip_body_comments(
    body: list[ast.stmt], *, strip_str: bool = True
) -> list[ast.stmt]:
    """Return a copy of body with ast_c.Comment and strings removed.

    Args:
        body: The body to investigate.
        strip_str: If True, also strip string expressions.

    Returns:
        A list of statement nodes without comments and strings.
    """

    new_body: list[ast.stmt] = []

    for stmt in body:
        if isinstance(stmt, ast_c.Comment) or (strip_str and is_str_expr(stmt)):
            continue
        new_body.append(stmt)

    return new_body


def get_arg_ids(node: ast.arguments) -> set[str]:
    """Return a set of all identifiers in an ast.arguments node.

    Args:
        node: The ast.arguments node to investigate.
    """

    idens = {a.arg for a in node.posonlyargs}
    idens.update(a.arg for a in node.args)

    if node.vararg:
        idens.add(node.vararg.arg)

    idens.update(a.arg for a in node.kwonlyargs)

    if node.kwarg:
        idens.add(node.kwarg.arg)

    return idens


def get_store_ids(
    node: ast.AST,
    *,
    stop: tuple[type, ...] = (),
) -> set[str]:
    """Get a set of identifiers appearing with ctx=ast.Store().

    Traversal stops when encountering nodes of types in `stop`.

    Args:
        node: The ast node to investigate.
    """

    ids: set[str] = set()
    stack = [node]

    while stack:
        cur = stack.pop()

        if isinstance(cur, stop):
            continue

        if isinstance(cur, ast.Name) and isinstance(cur.ctx, ast.Store):
            ids.add(cur.id)

        stack.extend(ast.iter_child_nodes(cur))

    return ids


def get_body_store_ids(body: list[ast.stmt]) -> set[str]:
    """Get a set of identifiers appearing with ctx=ast.Store() for
    a list of ast.smt nodes.

    Args:
        body: The body to investigate
    """

    stop = (
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.Lambda,
        ast.ClassDef,
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
    )

    ids: set[str] = set()
    for stmt in body:
        ids |= get_store_ids(stmt, stop=stop)

    return ids


def is_pure_return_if(node: ast.If) -> bool:
    """Check if all branches in an if-elif-else ladder only contain a
    single return statement.

    Args:
        node: The ast.If node to investigate.
    """

    cur: ast.stmt = node

    while isinstance(cur, ast.If):
        body = strip_body_comments(cur.body)
        orelse = strip_body_comments(cur.orelse)

        if (
            len(body) != 1
            or not isinstance(body[0], ast.Return)
            or len(orelse) > 1
        ):
            return False

        if not orelse:
            return True

        cur = orelse[0]

    return isinstance(cur, ast.Return)


def is_piecewise_funcdef(node: ast.FunctionDef) -> bool:
    """Check if the ast.FunctionDef node follows a piecewise function
    pattern.

    A piecewise function contains at least one "pure return if" ladder
    and an optional last return statement.

    Args:
        node: The ast.FunctionDef node to investigate.
    """

    body = strip_body_comments(node.body)

    if body and isinstance(body[-1], ast.Return):
        body.pop(-1)

    if not body:
        return False

    return all(isinstance(b, ast.If) and is_pure_return_if(b) for b in body)


def is_piecewise_if(node: ast.If) -> bool:
    """Check if all branches in an ast.If node exclusively contain a
    single assignment statement, and if all assignments target the same
    variables.

    Args:
        node: The ast.If node to investigate.
    """

    cur: ast.stmt = node
    prev_targets: list[str] | None = None
    comparisons: list[bool] = []

    while isinstance(cur, ast.If):
        body = strip_body_comments(cur.body)
        orelse = strip_body_comments(cur.orelse)

        if (
            len(body) != 1
            or not isinstance(body[0], ast.Assign)
            or len(orelse) > 1
        ):
            return False

        cur_targets = [ast.unparse(c) for c in body[0].targets]
        if prev_targets is None:
            prev_targets = cur_targets
        comparisons.append(cur_targets == prev_targets)

        if not orelse:
            return all(comparisons)

        cur = orelse[0]
        prev_targets = cur_targets

    if not isinstance(cur, ast.Assign):
        return False

    cur_targets = [ast.unparse(c) for c in cur.targets]
    comparisons.append(cur_targets == prev_targets)

    return all(comparisons)


@overload
def get_arg_node(
    node: ast.Call,
    pos: int | None,
    key: str | None,
    *,
    required: Literal[False] = False,
) -> ast.expr | None: ...
@overload
def get_arg_node(
    node: ast.Call, pos: int | None, key: str | None, *, required: Literal[True]
) -> ast.expr: ...


def get_arg_node(
    node: ast.Call, pos: int | None, key: str | None, *, required: bool = False
) -> ast.expr | None:
    """Get the node of the ast.Call argument.

    Args:
        node: The ast.Call node to investigate.
        pos: Positional index of the argument.
        kw: Keyword name of the argument.
    """

    if pos is not None and pos < len(node.args):
        return node.args[pos]

    if key is not None:
        for kw in node.keywords:
            if kw.arg == key:
                return kw.value

    if required:
        raise RubberizeTypeError("Required argument missing.")

    return None
