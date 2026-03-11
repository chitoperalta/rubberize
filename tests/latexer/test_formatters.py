# pylint: disable=all

from textwrap import dedent

import pytest

from rubberize.config import config
from rubberize.latexer import formatters, rules


# -------------
# format_name
# -------------


@pytest.mark.parametrize(
    "name, call, expected",
    [
        ("x", False, "x"),
        ("x", True, r"\operatorname{x}"),
        ("foo", False, r"\mathrm{foo}"),
        ("foo", True, r"\operatorname{foo}"),
    ],
)
def test_basic_names(name, call, expected):
    assert formatters.format_name(name, call=call) == expected


@pytest.mark.parametrize(
    "name, expected",
    [
        ("_x", r"\_x"),
        ("x_", r"x\_"),
        ("__x__", r"\_\_x\_\_"),
    ],
)
def test_edge_underscore_escape(name, expected):
    with config.override(use_subscripts=False):
        assert formatters.format_name(name) == expected


@pytest.mark.parametrize(
    "name, expected",
    [
        ("x_y", r"x_{y}"),
        ("x_y_z", r"x_{y, z}"),
        ("foo_baz", r"\mathrm{foo}_{\mathrm{baz}}"),
    ],
)
def test_subscripts(name, expected):
    with config.override(use_subscripts=True):
        assert formatters.format_name(name) == expected


@pytest.mark.parametrize(
    "name, expected",
    [
        ("x__y", r"\mathrm{x\_y}"),
        ("x___y", r"\mathrm{x\_\_y}"),
    ],
)
def test_double_underscore_escape(name, expected):
    with config.override(use_subscripts=True):
        assert formatters.format_name(name) == expected


@pytest.mark.parametrize(
    "name, expected",
    [
        ("alpha", r"\alpha"),
        ("Gamma", r"\Gamma"),
        ("alpha_beta", r"\alpha_{\beta}"),
    ],
)
def test_greek_replacement(name, expected):
    with config.override(use_symbols=True):
        assert formatters.format_name(name) == expected


@pytest.mark.parametrize(
    "name, expected",
    [
        ("gammaX", r"\gamma X"),
        ("phiVar", r"\phi \mathrm{Var}"),
    ],
)
def test_greek_start_detection(name, expected):
    with config.override(use_symbols=True, greek_starts={"gamma", "phi"}):
        assert formatters.format_name(name) == expected


@pytest.mark.parametrize(
    "name, expected",
    [
        ("x_hat", r"\hat{x}"),
        ("y_bar", r"\bar{y}"),
        ("z_tilde", r"\tilde{z}"),
    ],
)
def test_accents(name, expected):
    with config.override(use_symbols=True):
        assert formatters.format_name(name) == expected


@pytest.mark.parametrize(
    "name, expected",
    [
        ("x_prime", "x'"),
        ("x_star", r"x^{*}"),
        ("x_plus", r"x^{+}"),
        ("x_minus", r"x^{-}"),
    ],
)
def test_modifiers(name, expected):
    with config.override(use_symbols=True):
        assert formatters.format_name(name) == expected


def test_lambda_special_case():
    with config.override(use_symbols=True):
        assert formatters.format_name("lambda_") == r"\lambda"


def test_lambda_special_case_call():
    with config.override(use_symbols=True):
        assert (
            formatters.format_name("lambda_", call=True)
            == r"\operatorname{\lambda}"
        )


@pytest.mark.parametrize(
    "name, expected",
    [
        ("alpha_hat", r"\hat{\alpha}"),
        ("x_hat_prime", r"\hat{x}'"),
    ],
)
def test_accent_modifier_interaction(name, expected):
    with config.override(use_symbols=True):
        assert formatters.format_name(name) == expected


def test_symbols_disabled():
    with config.override(use_symbols=False):
        assert formatters.format_name("alpha") == r"\mathrm{alpha}"


def test_subscripts_disabled():
    with config.override(use_subscripts=False):
        assert formatters.format_name("x_y") == r"\mathrm{x\_y}"


# --------------
# format_delims
# --------------


@pytest.mark.parametrize(
    "left, text, right, expected",
    [
        ("(", "", ")", "()"),
        ("[", "", "]", "[]"),
        (r"\left(", "", r"\right)", r"\left(\right)"),
    ],
)
def test_empty_text(left, text, right, expected):
    assert formatters.format_delims(left, text, right) == expected


@pytest.mark.parametrize(
    "left, text, right, expected",
    [
        ("(", "x", ")", "(x)"),
        ("[", "a+b", "]", "[a+b]"),
        ("|", "x+y", "|", "|x+y|"),
    ],
)
def test_simple_wrapping(left, text, right, expected):
    assert formatters.format_delims(left, text, right) == expected


@pytest.mark.parametrize(
    "left, text, right, expected",
    [
        (r"\left(", "x", r"\right)", r"\left( x \right)"),
        (
            r"\begin{bmatrix}",
            "1 & 2",
            r"\end{bmatrix}",
            r"\begin{bmatrix} 1 & 2 \end{bmatrix}",
        ),
    ],
)
def test_spacing_for_latex_delims(left, text, right, expected):
    assert formatters.format_delims(left, text, right) == expected


@pytest.mark.parametrize(
    "left, text, right, indent, expected",
    [
        (
            "(",
            "a\nb",
            ")",
            2,
            "(\n  a\n  b\n)",
        ),
        (
            "[",
            r"a \\ b",
            "]",
            4,
            "[\n    a \\\\ b\n]",
        ),
    ],
)
def test_multiline_or_linebreak_block(left, text, right, indent, expected):
    assert (
        formatters.format_delims(left, text, right, indent=indent) == expected
    )


@pytest.mark.parametrize(
    "left, text, right, expected",
    [
        (
            r"\left(",
            "a\nb",
            r"\right)",
            "(\n    a\n    b\n)".replace("(", r"\left(").replace(
                ")", r"\right)"
            ),
        ),
    ],
)
def test_multiline_overrides_left_right_spacing(left, text, right, expected):
    # multiline rule should take precedence over spacing rule
    assert formatters.format_delims(left, "a\nb", right) == expected


# ----------------
# format_equation
# ----------------


@pytest.mark.parametrize(
    "lhs,rhs,expected",
    [
        ("x", None, "x"),
        ("x", [], "x"),
        (["x"], None, "x"),
    ],
)
def test_no_rhs(lhs, rhs, expected):
    assert formatters.format_equation(lhs, rhs) == expected


@pytest.mark.parametrize(
    "lhs,rhs,expected",
    [
        ("x", "y", "x = y"),
        (["x"], ["y"], "x = y"),
        (["x", "y"], "z", "x = y = z"),
        ("x", ["y", "z"], "x = y = z"),
    ],
)
def test_basic_equations(lhs, rhs, expected):
    with config.override(multiline=False):
        assert formatters.format_equation(lhs, rhs) == expected


@pytest.mark.parametrize(
    "lhs,rhs,expected",
    [
        ("x", ["", "y"], "x = y"),
        (["x", ""], ["y"], "x = y"),
        ("x", ["x", "y"], "x = y"),  # rhs duplicate removed
    ],
)
def test_filtering(lhs, rhs, expected):
    with config.override(multiline=False):
        assert formatters.format_equation(lhs, rhs) == expected


@pytest.mark.parametrize(
    "lhs,rhs,expected",
    [
        (
            "x",
            ["y", "z"],
            dedent(
                r"""
                \begin{aligned}
                    x &= y \\
                    &= z
                \end{aligned}
                """
            ).strip(),
        ),
        (
            ["a", "b"],
            ["c", "d"],
            dedent(
                r"""
                \begin{aligned}
                    a = b &= c \\
                    &= d
                \end{aligned}
                """
            ).strip(),
        ),
    ],
)
def test_multiline_equations(lhs, rhs, expected):
    with config.override(multiline=True):
        assert formatters.format_equation(lhs, rhs) == expected


def test_multiline_single_rhs_stays_inline():
    with config.override(multiline=True):
        assert formatters.format_equation("x", ["y"]) == "x = y"


@pytest.mark.parametrize(
    "lhs,rhs,expected",
    [
        (["a", "b"], ["b", "c"], "a = b = c"),  # rhs duplicate removed
    ],
)
def test_rhs_duplicate_removal(lhs, rhs, expected):
    with config.override(multiline=False):
        assert formatters.format_equation(lhs, rhs) == expected


# -------------
# format_array
# -------------


@pytest.mark.parametrize(
    "value",
    ["x", "1", r"\alpha"],
)
def test_non_list_passthrough(value):
    assert formatters.format_array(value) == value


@pytest.mark.parametrize(
    "array",
    [
        ["a", "b"],
        ["1", "2", "3"],
    ],
)
def test_1d_row_array_default(array):
    prefix, sep, suffix = rules.ARRAY_ROW_SYNTAX

    with config.override(show_1d_as_col=False):
        expected = formatters.format_delims(prefix, sep.join(array), suffix)
        assert formatters.format_array(array) == expected


@pytest.mark.parametrize(
    "array",
    [
        ["a", "b"],
        ["1", "2", "3"],
    ],
)
def test_1d_column_array(array):
    prefix, sep, suffix = rules.ARRAY_COL_SYNTAX

    with config.override(show_1d_as_col=True):
        expected = formatters.format_delims(prefix, sep.join(array), suffix)
        assert formatters.format_array(array) == expected


@pytest.mark.parametrize(
    "array",
    [
        [["a", "b"], ["c", "d"]],
        [["1", "2"], ["3", "4"]],
    ],
)
def test_2d_array(array):
    prefix, sep, suffix = rules.ARRAY_COL_SYNTAX

    with config.override(show_1d_as_col=False):
        rows = []
        _, row_sep, _ = rules.ARRAY_ROW_SYNTAX
        for row in array:
            rows.append(row_sep.join(row))

        expected = formatters.format_delims(prefix, sep.join(rows), suffix)

        assert formatters.format_array(array) == expected


def test_nested_row_elements_do_not_get_wrapped():
    # ensures recursive is_elt=True behavior
    row = ["a", "b"]
    _, row_sep, _ = rules.ARRAY_ROW_SYNTAX

    result = formatters.format_array(row, is_elt=True)

    assert result == row_sep.join(row)


@pytest.mark.parametrize(
    "array",
    [
        [["a", "b"], ["c"]],
        [["1"], ["2", "3"]],
    ],
)
def test_irregular_nested_array(array):
    prefix, sep, suffix = rules.ARRAY_COL_SYNTAX
    _, row_sep, _ = rules.ARRAY_ROW_SYNTAX

    rows = [row_sep.join(r) for r in array]
    expected = formatters.format_delims(prefix, sep.join(rows), suffix)

    assert formatters.format_array(array) == expected
