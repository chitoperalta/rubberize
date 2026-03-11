# pylint: disable=all

import ast
import pytest

from rubberize.latexer import helpers, ranks
from rubberize.latexer.visitors import ExprVisitor
from rubberize.vendor import ast_comments as ast_c


def _get_ast(src: str) -> ast.expr:
    """Helper function to parse an expression and return its AST node."""
    tree = ast.parse(src, mode="eval")
    return tree.body


# -------
# get_id
# -------


@pytest.mark.parametrize(
    "src, expected",
    {
        "x": "x",
        "obj.attr": "attr",
        "a.b.c": "c",
        "1 + 2": None,
        "f()": None,
        "f().foo": "foo",
    }.items(),
)
def test_get_id(src, expected):
    node = _get_ast(src)
    assert helpers.get_id(node) == expected


# -----------
# get_object
# -----------


class Dummy:
    value = 42


class DummyC:
    x = 7


class DummyB:
    c = DummyC()


class DummyA:
    b = DummyB()


_object_ns: dict[str, object] = {
    "x": 10,
    "dummy": Dummy(),
    "dummy_a": DummyA(),
    "lst": [1, 2],
    "y": 16,
}


def test_get_object_name():
    node = _get_ast("x")
    assert helpers.get_object(node, _object_ns) == 10


def test_get_object_attribute():
    node = _get_ast("dummy.value")
    assert helpers.get_object(node, _object_ns) == 42


def test_get_object_nested_attribute():
    node = _get_ast("dummy_a.b.c.x")
    assert helpers.get_object(node, _object_ns) == 7


@pytest.mark.parametrize(
    "src, expected",
    [
        ("5", 5),
        ("3.14", 3.14),
        ("'abc'", "abc"),
        ("True", True),
    ],
)
def test_get_object_constant(src, expected):
    assert helpers.get_object(_get_ast(src), {}) == expected


def test_get_object_eval_no_ns():
    node = _get_ast("1 + 2")
    assert helpers.get_object(node, None) == 3


def test_get_object_eval_with_ns():
    node = _get_ast("dummy.value - (x + 2)")

    assert helpers.get_object(node, _object_ns) == 30


def test_get_object_name_error_returns_none():
    node = _get_ast("missing + 1")
    assert helpers.get_object(node, _object_ns) is None


def test_get_object_deepcopy_protects_original():
    node = _get_ast("lst.append(3)")
    assert _object_ns["lst"] == [1, 2]


def test_get_object_module_reference():
    import math

    ns = _object_ns.copy()
    ns["math"] = math

    node = _get_ast("math.sqrt(y)")
    assert helpers.get_object(node, ns) == 4


# ----------------
# get_func_object
# ----------------


class DummyHasMethod:
    def func(self):
        return 1


_func_object_ns: dict[str, object] = {
    "f": abs,
    "dummy": DummyHasMethod(),
    "lst": [],
    "lam": lambda: None,
}


def test_get_func_object_simple():
    node = _get_ast("f(x)")
    func = helpers.get_func_object(node, _func_object_ns)  # type: ignore
    assert callable(func)
    assert func == abs


def test_get_func_object_python_bound_method():
    node = _get_ast("dummy.func()")
    func = helpers.get_func_object(node, _func_object_ns)  # type: ignore
    assert func is DummyHasMethod.func


def test_get_func_object_builtin_method():
    node = _get_ast("lst.append(1)")
    func = helpers.get_func_object(node, _func_object_ns)  # type: ignore
    assert func is list.append


def test_get_func_object_none():
    node = _get_ast("missing()")
    assert helpers.get_func_object(node, _func_object_ns) is None  # type: ignore


# ------------
# get_func_id
# ------------


@pytest.mark.parametrize(
    "src, expected",
    {
        "lam()": "<lambda>",
        "f()": "abs",
        "dummy.func()": "func",
    }.items(),
)
def test_get_func_id_resolved(src, expected):
    node = _get_ast(src)
    assert helpers.get_func_id(node, _func_object_ns) == expected  # type: ignore


def test_get_func_id_alias():
    import math

    ns = _func_object_ns.copy()
    ns["m"] = math.sin

    node = _get_ast("m(1)")
    assert helpers.get_func_id(node, ns) == "sin"  # type: ignore


@pytest.mark.parametrize(
    "src, expected",
    [
        ("f()", "f"),
        ("obj.method()", "method"),
    ],
)
def test_get_func_id_fallback(src, expected):
    node = _get_ast(src)
    assert helpers.get_func_id(node, None) == expected  # type: ignore


def test_get_func_id_unresolved():
    node = _get_ast("missing()")
    assert helpers.get_func_id(node, {}) == "missing"  # type: ignore


# -----------------
# get_operand_type
# -----------------


_opd_type_cases = {
    # Numeric values (N)
    "0": "N",
    "1": "N",
    "1000": "N",
    "-5": "-N",
    "3.14": "N",
    "-2.718": "-N",
    "Decimal(4.0000000000001)": "N",
    "float(3)": "N",
    # Sci not is not handled because its always bracketed (B)
    # Letter variables (L)
    "x": "L",
    "y_foo": "L",
    "z_hat": "L",
    "S_star_ult": "L",
    "epsilon": "L",
    "DeltaT": "L",
    "psiQ": "L",
    "-a": "-L",
    "-b_foo": "-L",
    "-c_hat": "-L",
    "-phiR_n": "-L",
    # Word variables (W)
    "foo": "W",
    "bar123": "W",
    "foo_alpha": "W",
    "gammaLoad": "W",  # starting greek case
    "-baz_ly": "-W",
    "-tot_bar": "-W",
    "-xalpha": "-W",
    # Calls (C)
    "f(x)": "C",
    "sin(theta)": "C",
    "foo_baz(a + b)": "C",
    "-g(y, z)": "-C",
    # Bracketed expressions (B)
    "(a + b)": "B",
    "(x - y)": "B",
    "-(m + n)": "-B",
    "a / b": "B",  # Div renders as B
    "a // b": "B",  # Floor div renders as B
    "ceil(132.23)": "B",  # ceil() renders B
    "sqrt(x^2 + y^2)": "B",  # sqrt syntax is treated as B
}


@pytest.mark.parametrize(
    "src, is_left, expected",
    [
        (src, is_left, expected)
        for src, expected in _opd_type_cases.items()
        for is_left in [True, False]
    ],
)
def test_get_operand_type(src, is_left, expected):
    from decimal import Decimal

    node = _get_ast(src)
    visitor = ExprVisitor({"Decimal": Decimal})
    latex = visitor.visit_operand(node, ranks.MULT_RANK).latex
    result = helpers.get_operand_type(node, latex, is_left=is_left)

    assert result == expected
