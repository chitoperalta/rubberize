"""Helper functions that get various attributes from nodes, or check
node types.
"""

import ast
import copy
import re
from types import ModuleType
from typing import Any, Optional, TypeVar

from rubberize.config import config, parse_modifiers
from rubberize.latexer.expr_rules import BIN_OPS, GREEK
from rubberize.utils import find_and_sub
import rubberize.vendor.ast_comments as ast_c

_AstT = TypeVar("_AstT", bound=ast.AST)


def get_desc_and_over(node: ast.AST) -> tuple[Optional[str], dict[str, Any]]:
    """Get the description and override from a comment statement or an
    inline comment in an AST node.

    Args:
        node: The node to get the description and overrides from.

    Returns:
        A tuple of description string and overrides mapping to be used
        as an argument in `config.override()` context manager. The
        description can be `None` if no description string is found.
    """

    if not isinstance(node, ast_c.Comment):
        if not hasattr(node, "comment"):
            return None, {}
        node = getattr(node, "comment")
        assert isinstance(node, ast_c.Comment)

    string = node.value[1:].lstrip()

    # Temporarily remove render context syntax from comment
    irbz_dummy = "\ue000"
    irbz_list, string = find_and_sub(
        r"(?<!\\)(\{\{.*?\}\})", irbz_dummy, string
    )

    # Extract modifiers
    modifier_pattern = (
        r"(?:(?<=\s)|^)@(\w[\w_]*"
        r"(?:=(?:{.*?}|\[.*?\]|\(.*?\)|\".*?\"|'.*?'|\S+))?)"
    )
    modifiers, string = find_and_sub(modifier_pattern, "", string)

    # Unescape
    string = string.replace(r"\{{", r"{{")
    string = string.replace(r"\@", "@")

    # Replace inline rubberize syntax to comment
    for irbz in irbz_list:
        string = string.replace(irbz_dummy, irbz, 1)

    return string if string.strip() else None, parse_modifiers(modifiers)


def get_id(node: ast.expr) -> Optional[str]:
    """Get the identifier of an attribute or name node.

    Args:
        node: The node to get identifier from.

    Returns:
        The identifier or `None` if node is not an attribute or name.
    """

    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return None


def get_object(
    node: ast.expr, namespace: Optional[dict[str, Any]]
) -> Optional[Any]:
    """Get the object of the expression node directly from a namespace
    or by `eval()` using the namespace as globals and a deepcopy of
    referenced names as locals.

    Deepcopy is needed to prevent changing mutable types when `eval()`
    is run.

    Args:
        node: The expression node to lookup in the namespace or to be
            unparsed and evaluated.
        namespace: A dictionary of identifier and object pairs.

    Returns:
        The object or `None` if the object cannot be retrieved or the
            unparsed expression cannot be evaluated.
    """

    if namespace and isinstance(node, ast.Attribute):
        module = get_object(node.value, namespace)
        if module is not None:
            return getattr(module, node.attr)
    if namespace and isinstance(node, ast.Name):
        obj = namespace.get(node.id)
        if obj is not None:
            return obj
    if isinstance(node, ast.Constant):
        return node.value

    try:
        if namespace is None:
            return eval(ast.unparse(node))  # pylint: disable=eval-used

        ref_names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}

        namespace_copy = {}
        for name in ref_names:
            if name not in namespace:
                continue

            name_obj = namespace[name]
            if isinstance(name_obj, ModuleType):
                continue

            try:
                import pint  # pylint: disable=import-outside-toplevel

                if isinstance(name_obj, (pint.UnitRegistry, pint.Quantity)):
                    # Pint quantities must always use the same unit registry
                    continue
            except ImportError:
                pass

            # Deepcopy referenced names to prevent changing mutable types
            namespace_copy[name] = copy.deepcopy(name_obj)

        # pylint: disable-next=eval-used
        return eval(ast.unparse(node), namespace, namespace_copy)
    except NameError:
        return None


def get_mult_infix(node: ast.BinOp, left_latex: str, right_latex: str) -> str:
    """Get the appropriate sign for a multiplication operation.

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
        node: The multiplication node to investigate.
        left_latex: LaTeX representation of the left operand.
        right_latex: LaTeX representation of the right operand.

    Returns:
        The appropriate LaTeX for the multiplication symbol.
    """

    assert isinstance(node.op, ast.Mult)

    left_type = get_operand_type(node.left, left_latex, is_left=True)
    right_type = get_operand_type(node.right, right_latex, is_left=False)

    # print("LEFT:", left_latex, left_type)
    # print("RIGHT:", right_latex, right_type)

    if left_type[-1] == "N" and right_type[-1] == "N":
        return r" \times "
    if right_type[-1] in "N?" or right_type[0] == "-":
        return BIN_OPS[ast.Mult].infix
    if left_type[-1] in "NB":
        return r"\,"
    if left_type[-1] == "L" and right_type == "L":
        return r"\,"
    return BIN_OPS[ast.Mult].infix


# pylint: disable=too-many-return-statements,too-many-branches
def get_operand_type(node: ast.expr, latex: str, is_left: bool) -> str:
    """Get the type of the operand of a binary operation.

    Args:
        node: Operand node to investigate.
        latex: LaTeX representation of the operand.
        left: Whether the node is a left operand.

    Returns:
        Any one of the following literals

        - `"N"`: Operand is a numeric value.
        - `"L"`: Operand is a letter variable (a single-character base
            name), including Greek letters.
        - `"W"`: Operand is a word variables (with multiple characters
            for base name).
        - `"C"`: Operand is a function call.
        - `"B"`: Operand is a bracketed expression.
        - `"?"`: Operand is of other type.

        Signed versions of each type are denoted by the `"-"` prefix.
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
            return "-B"  # Nested unaries are bracketed (e.g., -(-3))
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

    if isinstance(node, ast.Name):
        # split "_" to get base
        base = node.id.strip("_").split("_", 1)[0]

        if (
            (config.use_symbols and base in GREEK)
            or (config.use_symbols and base[:-1] in config.greek_starts)
            or len(base) == 1
        ):
            return "L"

    return "?"


def get_arg_ids(node: ast.arguments) -> set[str]:
    """Get a set of all argument identifiers in an arguments node of a
    function definition.

    This helper function simulates the local scope namespace within a
    function definition. Any identifiers it collects should be excluded
    from the function definition's namespace during visitation.

    Args:
        node: The arguments node to extract from.

    Returns:
        The set of argument identifiers.
    """

    arg_names = {arg.arg for arg in node.args}
    arg_names.update(arg.arg for arg in node.kwonlyargs)
    if node.vararg:
        arg_names.add(node.vararg.arg)
    if node.kwarg:
        arg_names.add(node.kwarg.arg)
    return arg_names


def get_target_ids(body: list[ast.stmt]) -> set[str]:
    """Get a set of all assignment target identifiers in a body.

    This helper function simulates the local scope namespace within a
    function definition. Any identifiers it collects should be excluded
    from the function definition's namespace during visitation.

    Args:
        body: The body, a list of statement nodes.

    Returns:
        The set of assignment target identifiers.
    """

    target_names = set()
    for stmt in body:
        if isinstance(stmt, ast.If):
            target_names.update(get_target_ids(stmt.body))
        elif isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                target_name = get_id(target)
                if target_name:
                    target_names.add(target_name)
        elif isinstance(stmt, ast.AnnAssign):
            target_name = get_id(stmt.target)
            if target_name:
                target_names.add(target_name)
    return target_names


def is_str_expr(node: ast.stmt) -> bool:
    """Check if the statement node is a string expression node.

    Args:
        node: The statement node to investigate.

    Returns:
        Whether the node is a string expression node or not.
    """

    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def is_uniform_assign_if(node: ast.If) -> bool:
    """Check if all branches in an `if`-`elif`-`else` ladder exclusively
    contain a single assignment statement, and if all assignments target
    the same variables.

    This function traverses an `if` statement and its `elif` and `else`
    branches to verify that:

    - Each branch contains only one statement node (excluding comments).
    - That statement is an assignment node (`ast.Assign`).
    - The targets of all assignments are identical across branches.

    Args:
        node: The if node to investigate.

    Returns:
        Whether the node is a uniform assignment `if` ladder or not.
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


def is_pure_return_if(node: ast.If) -> bool:
    """Check if all branches in an `if`-`elif`-`else` ladder exclusively
    contain a single return statement.

    This function traverses an `if` statement and its `elif` and `else`
    branches to verify that:

    - Each branch contains only one statement node (excluding comments).
    - That statement is a return node (`ast.Return`).

    Args:
        node: The if node to investigate.

    Returns:
        Whether the node is a pure return `if` ladder or not.
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


def is_piecewise_functiondef(node: ast.FunctionDef) -> bool:
    """Check if the function definition is meant to be displayed as a
    piecewise function, which is a function that only contains at least
    one pure return `if` ladder and an optional last return statement.

    Args:
        node: The function definition node to investigate.

    Returns:
        Whether the node is a piecewise function definition or not.
    """

    body = strip_body_comments(node.body)
    body = body[:-1] if body and isinstance(body[-1], ast.Return) else body

    if not body:
        return False

    return all(isinstance(b, ast.If) and is_pure_return_if(b) for b in body)


def is_method(
    node: ast.expr, cls: type, method: str, namespace: Optional[dict[str, Any]]
) -> bool:
    """Check if the given expression node represents a method call on
    an instance of `cls`, using `namespace` for type lookup.

    A valid method call is an `ast.Call` node where:

    - The `func` attribute is an `ast.Attribute` instance.
    - The `value` of this attribute is an instance or subclass of `cls`,
      determined using `namespace`.
    - The attribute name matches the specified `method`.

    Args:
        node: The expression node to investigate.
        cls: The class to check against.
        method: The method name to look for.
        namespace: A dictionary of identifier and object pairs.

    Returns:
        Whether the node is a method call on an instance of `cls`
            or not.
    """

    if namespace is None:
        return False
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and is_class(node.func.value, cls, namespace)
        and hasattr(cls, method)
        and node.func.attr == method
    )


def is_class(
    node: ast.expr, cls: type, namespace: Optional[dict[str, Any]]
) -> bool:
    """Determine whether the given expression node represents an
    instance of `cls`, using `namespace` for type resolution.

    This function retrieves the object corresponding to `node` from
    `namespace` and checks if it is an instance of `cls` or a subclass.

    Args:
        node: The expression node to investigate.
        cls: The class to check against.
        namespace: A dictionary of identifier and object pairs.

    Returns:
        Whether the node is an instance or subclass of `cls`, or not.
    """

    if namespace is None:
        return False
    obj = get_object(node, namespace)
    return issubclass(type(obj), cls) or isinstance(obj, cls)


def get_call_args(node: ast.Call) -> tuple[list[ast.expr], dict[str, ast.expr]]:
    """Retrieve the positional and keyword arguments of a call node.

    Extracts the argument expressions from an `ast.Call` node, returning
    them as separate lists for positional and keyword arguments.

    Args:
        node: The call node to extract arguments from.

    Returns:
        A tuple containing
        - A list of positional argument expression nodes.
        - A dictionary of keyword argument names and their corresponding
            expression nodes.
    """

    return node.args, {f"{k.arg}": k.value for k in node.keywords}


def is_unit_assignment(
    node: ast.BinOp, namespace: Optional[dict[str, Any]]
) -> bool:
    """Check if the given binary operation represents an assignment of a
    Pint unit.

    A unit assignment is a binary operation where:

    - The operator is either multiplication or division.
    # - The left operand is a name, attribute, constant, function call,
    #     subscript expression, or unary operation.
    - The right operand is a node representing a Pint unit.

    Args:
        node: The binary operation node to investigate.
        namespace: A dictionary of identifier and object pairs.

    Returns:
        Whether the node represents an assignment of a Pint unit or not.
    """

    # if isinstance(node.left, ast.UnaryOp):
    #     left = node.left.operand
    # else:
    #     left = node.left

    return (
        isinstance(node.op, (ast.Mult, ast.Div))
        # and isinstance(
        #     left,
        #     (ast.Name, ast.Attribute, ast.Constant, ast.Call, ast.Subscript),
        # )
        and is_unit(node.right, namespace)
    )


def is_unit(node: ast.expr, namespace: Optional[dict[str, Any]]) -> bool:
    """Check if the given expression node references a Pint unit object,
    using `namespace` for lookup.

    A Pint unit reference is an instance or subclass of `pint.Unit`. If
    Pint not installed, this functions returns `False`.

    Args:
        node: The expression node to investigate.
        namespace: A dictionary of identifier and object pairs.

    Returns:
        Whether the node references a Pint unit object or not.
    """

    try:
        import pint  # pylint: disable=import-outside-toplevel

        return is_class(node, pint.Unit, namespace)
    except ImportError:
        return False


def is_quantity(node: ast.expr, namespace: Optional[dict[str, Any]]) -> bool:
    """Check if the given expression node references a Pint quantity
    object, using `namespace` for lookup.

    A Pint quantity reference is an instance of `pint.Quantity` with
    a unit other than dimensionless (i.e., not equal to `1`).

    Args:
        node: The expression node to investigate.
        namespace: A dictionary of identifier and object pairs.

    Returns:
        Whether the node references a Pint quantity object or not.
    """

    try:
        import pint  # pylint: disable=import-outside-toplevel

        obj = get_object(node, namespace)
        return isinstance(obj, pint.Quantity) and not obj.units == 1
    except ImportError:
        return False


def strip_docstring(node: _AstT) -> _AstT:
    """Return a copy of the given AST node with the docstring removed.
    If the node does not have a docstring or if the node does not
    suport docstrings, it returns a copy of the node.

    Args:
        node: The AST node to investigate.
    Returns:
        The node without the docstring.
    """

    supports_docstring = (
        ast.AsyncFunctionDef,
        ast.FunctionDef,
        ast.ClassDef,
        ast.Module,
    )

    if not isinstance(node, supports_docstring):
        return node

    if node.body and is_str_expr(node.body[0]):
        new_node = copy.copy(node)
        new_node.body = node.body[1:]
        return new_node

    if (
        node.body
        and isinstance(node.body[0], ast_c.Comment)
        and is_str_expr(node.body[1])
    ):
        new_node = copy.copy(node)
        new_node.body = [node.body[0]] + node.body[2:]
        return new_node

    return node


def strip_body_comments(
    body: list[ast.stmt], strip_str: bool = True
) -> list[ast.stmt]:
    """Return a copy of body with comments, and optionally also strings,
    removed.

    Args:
        body: A list of statement nodes. Usually an attribute of some
            statement nodes such as `ast.If` and `ast.FunctionDef`.
        strip_str: Whether to also strip string expressions. Defaults to
            `True`.

    Returns:
        A list of statement nodes without comments and strings.
    """

    new_body = []
    for stmt in body:
        if not isinstance(stmt, ast_c.Comment) and not (
            strip_str and is_str_expr(stmt)
        ):
            new_body.append(stmt)
    return new_body
