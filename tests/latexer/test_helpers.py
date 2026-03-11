# pylint: disable=all

from textwrap import dedent

import ast

import pytest

from rubberize._exceptions import RubberizeTypeError
from rubberize.latexer import helpers, ranks
from rubberize.latexer.visitors import ExprVisitor
from rubberize.vendor import ast_comments as ast_c


def _get_expr_ast(src: str) -> ast.expr:
    tree = ast_c.parse(src, mode="eval")
    return tree.body  # type: ignore


def _get_stmt_ast(src: str) -> ast.stmt:
    tree = ast_c.parse(src, mode="exec")
    return tree.body[0]  # type: ignore


def _get_stmt_ast_body(src: str) -> list[ast.stmt]:
    tree = ast_c.parse(src, mode="exec")
    return tree.body  # type: ignore


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
    node = _get_expr_ast(src)
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
    node = _get_expr_ast("x")
    assert helpers.get_object(node, _object_ns) == 10


def test_get_object_attribute():
    node = _get_expr_ast("dummy.value")
    assert helpers.get_object(node, _object_ns) == 42


def test_get_object_nested_attribute():
    node = _get_expr_ast("dummy_a.b.c.x")
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
    assert helpers.get_object(_get_expr_ast(src), {}) == expected


def test_get_object_eval_no_ns():
    node = _get_expr_ast("1 + 2")
    assert helpers.get_object(node, None) == 3


def test_get_object_eval_with_ns():
    node = _get_expr_ast("dummy.value - (x + 2)")

    assert helpers.get_object(node, _object_ns) == 30


def test_get_object_name_error_returns_none():
    node = _get_expr_ast("missing + 1")
    assert helpers.get_object(node, _object_ns) is None


def test_get_object_deepcopy_protects_original():
    node = _get_expr_ast("lst.append(3)")
    assert _object_ns["lst"] == [1, 2]


def test_get_object_module_reference():
    import math

    ns = _object_ns.copy()
    ns["math"] = math

    node = _get_expr_ast("math.sqrt(y)")
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
    node = _get_expr_ast("f(x)")
    func = helpers.get_func_object(node, _func_object_ns)  # type: ignore
    assert callable(func)
    assert func == abs


def test_get_func_object_python_bound_method():
    node = _get_expr_ast("dummy.func()")
    func = helpers.get_func_object(node, _func_object_ns)  # type: ignore
    assert func is DummyHasMethod.func


def test_get_func_object_builtin_method():
    node = _get_expr_ast("lst.append(1)")
    func = helpers.get_func_object(node, _func_object_ns)  # type: ignore
    assert func is list.append


def test_get_func_object_none():
    node = _get_expr_ast("missing()")
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
    node = _get_expr_ast(src)
    assert helpers.get_func_id(node, _func_object_ns) == expected  # type: ignore


def test_get_func_id_alias():
    import math

    ns = _func_object_ns.copy()
    ns["m"] = math.sin

    node = _get_expr_ast("m(1)")
    assert helpers.get_func_id(node, ns) == "sin"  # type: ignore


@pytest.mark.parametrize(
    "src, expected",
    {
        "f()": "f",
        "obj.method()": "method",
    }.items(),
)
def test_get_func_id_fallback(src, expected):
    node = _get_expr_ast(src)
    assert helpers.get_func_id(node, None) == expected  # type: ignore


def test_get_func_id_unresolved():
    node = _get_expr_ast("missing()")
    assert helpers.get_func_id(node, {}) == "missing"  # type: ignore


# ---------
# get_desc
# ---------

_desc_cases = [
    ("# hello world", "hello world", []),
    ("#     hello world", "hello world", []),
    ("# hello world  ", "hello world  ", []),
    ("# hello world     ", "hello world  ", []),  # 2 max trailing space
    ("#", None, []),
    ("# @modifier=True hello", "hello", ["modifier=True"]),
    ("# @modifier={1, 2} hello", "hello", ["modifier={1, 2}"]),
    ("# @keyword hello", "hello", ["keyword"]),
    ("# @kw1 @kw2 hello", "hello", ["kw1", "kw2"]),
    ("# hel @keyword lo", "hel lo", ["keyword"]),
    ("# hel @kw1 @kw2 lo", "hel lo", ["kw1", "kw2"]),
    ("# hel @keyword  lo", "hel  lo", ["keyword"]),
    ("# hel @kw1 @kw2  lo", "hel  lo", ["kw1", "kw2"]),
    ("# hello @keyword", "hello", ["keyword"]),
    ("# hello @kw1 @kw2", "hello", ["kw1", "kw2"]),
    ("# hello {{x + 1}} world @kw", "hello {{x + 1}} world", ["kw"]),
    (r"# \{{literal}} @kw \@symbol", "{{literal}} @symbol", ["kw"]),
]


@pytest.mark.parametrize(
    "src, expected, modifiers",
    [
        (src, expected, modifiers)
        for comment, expected, modifiers in _desc_cases
        # also test for inline comments
        for src in (comment, f"a = 42  {comment}")
    ],
)
def test_get_desc(monkeypatch, src, expected, modifiers):
    node = _get_stmt_ast(src)

    seen = {}

    def fake_parse(mods):
        seen["mods"] = mods
        return {"fake": True}

    monkeypatch.setattr(helpers, "parse_modifiers", fake_parse)

    desc, cfg = helpers.get_desc(node)

    assert desc == expected
    assert seen["mods"] == modifiers
    assert cfg == {"fake": True}


def test_get_desc_no_comment():
    node = _get_stmt_ast("a = 42")
    desc, cfg = helpers.get_desc(node)

    assert desc is None
    assert cfg == {}


# ---------
# is_class
# ---------


class A: ...


class B(A): ...


_class_ns: dict[str, object] = {
    "a": A(),
    "b": B(),
    "c": None,
    "y": 16,
}


@pytest.mark.parametrize(
    "src, cls, expected",
    [
        ("a", A, True),
        ("b", A, True),  # subclass instance
        ("c", A, False),
        ("y", A, False),
        ("d", A, False),
    ],
)
def test_is_class(src, cls, expected):
    node = _get_expr_ast(src)
    assert helpers.is_class(node, cls, _class_ns) == expected


def test_is_clas_no_ns():
    node = _get_expr_ast("a")
    assert helpers.is_class(node, A, None) == False


# --------
# is_unit
# --------


def test_is_unit():
    import pint

    ns = _object_ns.copy()
    ns["ureg"] = pint.UnitRegistry()

    node = _get_expr_ast("ureg.furlong")
    assert helpers.is_unit(node, ns) == True


def test_is_unit_no_ns():
    node = _get_expr_ast("ureg.inch")
    assert helpers.is_unit(node, None) == False


# -------------------
# is_unit_assignment
# -------------------


@pytest.mark.parametrize(
    "src, expected",
    {
        "42.0 * ureg.furlong": True,
        "42.0 / ureg.millimeter": True,
        "42.0 * 69": False,
    }.items(),
)
def test_is_unit_assignment(src, expected):
    import pint

    ns = _object_ns.copy()
    ns["ureg"] = pint.UnitRegistry()

    node = _get_expr_ast(src)
    assert helpers.is_unit_assignment(node, ns) == expected  # type: ignore


def test_is_unit_assignment_no_ns():
    node = _get_expr_ast("6.0 * ureg.inch")
    assert helpers.is_unit(node, None) == False


# -------------------
# is_ndarray
# -------------------


def test_is_ndarray():
    import numpy as np

    ns = _object_ns.copy()
    ns["np"] = np

    node = _get_expr_ast("np.array([1, 2, 3])")
    assert helpers.is_ndarray(node, ns) == True


def test_is_ndarray_no_ns():
    node = _get_expr_ast("np.array([1, 2, 3])")
    assert helpers.is_unit(node, None) == False


# ----------------------------------
# get_mult_infix / get_operand_type
# ----------------------------------


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

    node = _get_expr_ast(src)
    visitor = ExprVisitor({"Decimal": Decimal})
    latex = visitor.visit_operand(node, ranks.MULT_RANK).latex
    result = helpers.get_operand_type(node, latex, is_left=is_left)

    assert result == expected


# ------------
# is_str_expr
# ------------


@pytest.mark.parametrize(
    "src, expected",
    {
        '"hello world"': True,
        '"""hello\nworld"""': True,
    }.items(),
)
def test_is_str_expr(src, expected):
    node = _get_stmt_ast(src)
    assert helpers.is_str_expr(node) == expected


# ----------------
# strip_docstring
# ----------------


def test_strip_docstring_async_function_def():
    src = dedent(
        '''
        async def f():
            """hello"""
            x = 1
        '''
    )

    node = _get_stmt_ast(src)
    new = helpers.strip_docstring(node)

    assert isinstance(new, ast.AsyncFunctionDef)
    assert len(new.body) == 1
    assert isinstance(new.body[0], ast.Assign)


def test_strip_docstring_function_def():
    src = dedent(
        '''
        def f():
            """hello"""
            x = 1
        '''
    )

    node = _get_stmt_ast(src)
    new = helpers.strip_docstring(node)

    assert isinstance(new, ast.FunctionDef)
    assert len(new.body) == 1
    assert isinstance(new.body[0], ast.Assign)


def test_strip_docstring_class_def():
    src = dedent(
        '''
        class F:
            """hello"""
            x = 1
        '''
    )

    node = _get_stmt_ast(src)
    new = helpers.strip_docstring(node)

    assert isinstance(new, ast.ClassDef)
    assert len(new.body) == 1
    assert isinstance(new.body[0], ast.Assign)


def test_strip_docstring_module():
    src = dedent(
        '''
        """hello"""
        x = 1
        '''
    )

    node = ast.parse(src, mode="exec")
    new = helpers.strip_docstring(node)

    assert len(new.body) == 1
    assert isinstance(new.body[0], ast.Assign)


def test_strip_docstring_empty_module():
    node = ast.parse("", mode="exec")
    new = helpers.strip_docstring(node)

    assert len(new.body) == 0


def test_strip_docstring_no_docstring_node():
    src = dedent(
        """
        def f():
            x = 1
        """
    )

    node = _get_stmt_ast(src)
    new = helpers.strip_docstring(node)

    assert ast.dump(node) == ast.dump(new)


def test_strip_docstring_no_docstring_supported_node():
    src = dedent(
        """
        if x > 1:
            a = True
        """
    )

    node = _get_stmt_ast(src)
    new = helpers.strip_docstring(node)

    assert ast.dump(node) == ast.dump(new)


def test_strip_docstring_after_comments():
    src = dedent(
        '''
        def f():
            # comment
            # another comment
            """hello"""
            x = 1
        '''
    )

    node = _get_stmt_ast(src)
    new = helpers.strip_docstring(node)

    assert isinstance(new, ast.FunctionDef)
    assert len(new.body) == 3
    assert isinstance(new.body[0], ast_c.Comment)
    assert isinstance(new.body[1], ast_c.Comment)
    assert isinstance(new.body[2], ast.Assign)


def test_strip_docstring_does_not_modify_original():
    src = dedent(
        '''
        def f():
            """hello"""
            x = 1
        '''
    )

    node = _get_stmt_ast(src)
    new = helpers.strip_docstring(node)

    assert isinstance(node, ast.FunctionDef)
    assert len(node.body) == 2
    assert isinstance(new, ast.FunctionDef)
    assert len(new.body) == 1


# --------------------
# strip_body_comments
# --------------------


def test_strip_body_comments():
    src = dedent(
        """
        # hello
        x = 1
        # world
        """
    )

    body = _get_stmt_ast_body(src)
    new = helpers.strip_body_comments(body)

    assert len(new) == 1
    assert isinstance(new[0], ast.Assign)


def test_strip_body_comments_removes_string_expr():
    src = dedent(
        """
        "hello"
        x = 1
        """
    )

    body = _get_stmt_ast_body(src)
    new = helpers.strip_body_comments(body)

    assert len(new) == 1
    assert isinstance(new[0], ast.Assign)


def test_strip_body_comments_keeps_string_expr():
    src = dedent(
        """
        "hello"
        x = 1
        """
    )

    body = _get_stmt_ast_body(src)
    new = helpers.strip_body_comments(body, strip_str=False)

    assert len(new) == 2
    assert isinstance(new[0], ast.Expr)
    assert isinstance(new[0].value, ast.Constant)
    assert isinstance(new[1], ast.Assign)


def test_strip_body_comments_does_not_modify_original():
    src = dedent(
        """
        # hello
        x = 1
        """
    )

    body = _get_stmt_ast_body(src)
    new = helpers.strip_body_comments(body)

    assert len(body) == 2
    assert len(new) == 1


# ------------
# get_arg_ids
# ------------


def test_get_arg_ids():
    src = "def foo(a, b, /, c, d=1, *args, e, f=2, **kwargs): ..."
    node = _get_stmt_ast(src)

    assert isinstance(node, ast.FunctionDef)
    args = helpers.get_arg_ids(node.args)

    assert args == {"a", "b", "c", "d", "args", "e", "f", "kwargs"}


# --------------
# get_store_ids
# --------------


@pytest.mark.parametrize(
    "src, expected",
    {
        "x = 1": {"x"},
        "x = y = 1": {"x", "y"},
        "a, b = f()": {"a", "b"},
        "a, (b, c) = f()": {"a", "b", "c"},
        "for i in xs: pass": {"i"},
        "with open('x') as f: pass": {"f"},
        "x += 1": {"x"},
        "(x := 5)": {"x"},
        "[x**y for x in range(5)]": {"x"},
    }.items(),
)
def test_get_store_ids_basic(src, expected):
    node = _get_stmt_ast(src)
    ids = helpers.get_store_ids(node)
    assert ids == expected


@pytest.mark.parametrize(
    "src, stop, expected",
    [
        ("if cond:\n    def g():\n        x = 1", (ast.FunctionDef,), set()),
        ("[x for x in xs]", (ast.ListComp,), set()),
    ],
)
def test_get_store_ids_stop(src, stop, expected):
    node = ast.parse(src)
    ids = helpers.get_store_ids(node, stop=stop)
    assert ids == expected


def test_get_store_ids_complex():
    src = dedent(
        """
        a = 1
        b, (c, d) = f()
        for i, j in xs:
            k = i
        with open("x") as f:
            pass
        """
    )
    node = ast.parse(src)

    ids = helpers.get_store_ids(node)

    assert ids == {"a", "b", "c", "d", "i", "j", "k", "f"}


# ------------------
# is_pure_return_if
# ------------------


@pytest.mark.parametrize(
    "src, expected",
    {
        dedent(
            """
            if x:
                return 1
            """
        ): True,
        dedent(
            """
            if x:
                return 1
            else:
                return 2
            """
        ): True,
        dedent(
            """
            if x:
                return 1
            elif y:
                return 2
                """
        ): True,
        dedent(
            """
            if x:
                return 1
            elif y:
                return 2
            else:
                return 3
            """
        ): True,
        # body not single statement
        dedent(
            """
            if x:
                a = 1
                return 1
            """
        ): False,
        # body not return
        dedent(
            """
            if x:
                a = 1
            """
        ): False,
        # orelse more than one statement
        dedent(
            """
            if x:
                return 1
            else:
                a = 1
                return 2
            """
        ): False,
        # elif branch not return
        dedent(
            """
            if x:
                return 1
            elif y:
                a = 2
            """
        ): False,
        # final else not return
        dedent(
            """
            if x:
                return 1
            else:
                a = 2
            """
        ): False,
    }.items(),
)
def test_is_pure_return_if(src, expected):
    node = _get_stmt_ast(src)

    assert isinstance(node, ast.If)
    assert helpers.is_pure_return_if(node) is expected


def test_is_pure_return_if_ignores_comments():
    src = dedent(
        """
        if x:
            # comment
            return 1
        else:
            # another
            return 2
        """
    )
    node = _get_stmt_ast(src)

    assert isinstance(node, ast.If)
    assert helpers.is_pure_return_if(node)


# ---------------------
# is_piecewise_funcdef
# ---------------------


@pytest.mark.parametrize(
    "src, expected",
    {
        dedent(
            """
            def f(x):
                if x > 0:
                    return 1
                else:
                    return -1
            """
        ): True,
        dedent(
            """
            def f(x):
                if x > 0:
                    return 1
                else:
                    return -1
                return 0
            """
        ): True,
        dedent(
            """
            def f(x):
                if x > 0:
                    return 1
                if x < 0:
                    return 2
                return 0
            """
        ): True,
        # empty body
        dedent(
            """
            def f(x):
                pass
            """
        ): False,
        # only return (no ladder)
        dedent(
            """
            def f(x):
                return 1
            """
        ): False,
    }.items(),
)
def test_is_piecewise_funcdef(src, expected):
    node = _get_stmt_ast(src)

    assert isinstance(node, ast.FunctionDef)
    assert helpers.is_piecewise_funcdef(node) is expected


def test_is_piecewise_funcdef_ignores_comments():
    src = dedent(
        """
        def f(x):
            # comment
            if x > 0:
                return 1
            else:
                return 2
            # trailing comment
            return 0
        """
    )
    node = _get_stmt_ast(src)

    assert isinstance(node, ast.FunctionDef)
    assert helpers.is_piecewise_funcdef(node)


# ----------------
# is_piecewise_if
# ----------------


@pytest.mark.parametrize(
    "src, expected",
    {
        dedent(
            """
            if x > 0:
                y = 1
            else:
                y = 2
            """
        ): True,
        dedent(
            """
            if x > 0:
                y = 1
            elif x < 0:
                y = -1
            """
        ): True,
        dedent(
            """
            if x > 0:
                y = 1
            elif x < 0:
                y = -1
            else:
                y = 0
            """
        ): True,
        dedent(
            """
            if x > 0:
                a, b = 1, 2
            else:
                a, b = 3, 4
            """
        ): True,
        # different targets across branches
        dedent(
            """
            if x > 0:
                y = 1
            else:
                z = 2
            """
        ): False,
        # body contains more than one statement
        dedent(
            """
            if x > 0:
                y = 1
                z = 2
            else:
                y = 3
            """
        ): False,
        # else has multiple statements
        dedent(
            """
            if x > 0:
                y = 1
            else:
                y = 2
                z = 3
            """
        ): False,
    }.items(),
)
def test_is_piecewise_if(src, expected):
    node = _get_stmt_ast(src)

    assert isinstance(node, ast.If)
    assert helpers.is_piecewise_if(node) is expected


def test_is_piecewise_if_ignores_comments():
    src = dedent(
        """
        if x > 0:
            # comment
            y = 1
        else:
            # another comment
            y = 2
        """
    )
    node = _get_stmt_ast(src)

    assert isinstance(node, ast.If)
    assert helpers.is_piecewise_if(node)


# -------------
# get_arg_node
# -------------


@pytest.mark.parametrize(
    "src, pos, key, expected",
    [
        # positional argument
        ("f(1, 2)", 0, None, "1"),
        ("f(1, 2)", 1, None, "2"),
        # positional out of range -> None
        ("f(1)", 2, None, None),
        # keyword argument
        ("f(x=1)", None, "x", "1"),
        # keyword among others
        ("f(a=1, b=2)", None, "b", "2"),
        # positional preferred if available
        ("f(1, x=2)", 0, "x", "1"),
        # fallback to keyword if positional missing
        ("f(x=2)", 0, "x", "2"),
        # neither present
        ("f()", 0, "x", None),
    ],
)
def test_get_arg_node(src, pos, key, expected):
    node = _get_expr_ast(src)

    assert isinstance(node, ast.Call)

    result = helpers.get_arg_node(node, pos, key)

    if expected is None:
        assert result is None
    else:
        assert ast.unparse(result) == expected  # type: ignore


def test_get_arg_node_required_raises():
    node = _get_expr_ast("f()")

    assert isinstance(node, ast.Call)

    with pytest.raises(RubberizeTypeError):
        helpers.get_arg_node(node, 0, None, required=True)


def test_get_arg_node_required_missing_keyword():
    node = _get_expr_ast("f(a=1)")

    assert isinstance(node, ast.Call)

    with pytest.raises(RubberizeTypeError):
        helpers.get_arg_node(node, None, "b", required=True)
