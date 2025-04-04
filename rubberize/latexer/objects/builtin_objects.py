"""Converters for builtin objects and objects from the Standard Library."""

from decimal import Decimal
from fractions import Fraction
from math import floor, log10, isnan, isinf, copysign, degrees, isclose
from cmath import polar
from typing import Optional

from rubberize import exceptions
from rubberize.config import config
from rubberize.latexer.expr_latex import ExprLatex
from rubberize.latexer.expr_rules import (
    COLLECTIONS_ROW,
    COLLECTIONS_COL,
    THOUSANDS_SEPARATOR,
    DECIMAL_MARKER,
)
from rubberize.latexer.formatters import format_elts, format_delims
from rubberize.latexer.objects.convert_object import (
    convert_object,
    register_object_converter,
)
from rubberize.latexer.ranks import (
    VALUE_RANK,
    COLLECTIONS_RANK,
    SIGNED_RANK,
    BELOW_ADD_RANK,
    BELOW_MULT_RANK,
    BELOW_POW_RANK,
    DIV_RANK,
)


def convert_str(obj: str) -> ExprLatex:
    """Converter for `str` type object."""

    # Mathjax doesn't always render ``...'' properly
    # so we use the unicode characters “...”
    obj = r"\text" + config.str_font + r"{“" + obj.replace("_", r"\_") + r"”}"
    return ExprLatex(obj)


def convert_int(obj: int) -> ExprLatex:
    """Converter for `int` type object."""

    thousands = THOUSANDS_SEPARATOR[config.thousands_separator]
    return ExprLatex(
        f"{obj:,d}".replace(",", thousands),
        SIGNED_RANK if obj < 0.0 else VALUE_RANK,
    )


def convert_num(obj: float | Decimal) -> ExprLatex:
    """Converter for `float` or `Decimal` type object. If the resulting
    format is in scientific notation, the precedence rank is just under
    the rank for a multiplication operation.
    """

    if isinstance(obj, float):
        obj = _normalize_zero_float(obj)

    special = _convert_special_num(obj)
    if special is not None:
        return special

    if config.num_format == "FIX" and (
        abs(obj) >= 10**config.num_format_max_digits
        or (
            0.0 < abs(obj) < 10 ** (-config.num_format_prec)
            and round(obj, config.num_format_prec) == 0.0
        )
    ):
        num_format = "SCI"
    else:
        num_format = config.num_format

    if num_format == "FIX":
        result = f"{obj:,.{config.num_format_prec}f}"
    elif num_format == "SCI":
        result = f"{obj:,.{config.num_format_prec}E}"
    elif num_format == "GEN":
        result = f"{obj:,.{config.num_format_prec}G}"
    elif num_format == "ENG":
        exp = 3 * (floor(log10(abs(float(obj)))) // 3) if obj != 0 else 0
        base = obj / (10**exp)
        result = f"{base:,.{config.num_format_prec}f}E{int(exp):+03d}"
    else:
        raise exceptions.RubberizeSyntaxError(
            f"Unknown float format: {config.num_format}"
        )

    thousands = THOUSANDS_SEPARATOR[config.thousands_separator]
    decimal = DECIMAL_MARKER[config.decimal_marker]
    result = result.replace(".", "ddd").replace(",", "ttt")
    result = result.replace("ddd", decimal).replace("ttt", thousands)

    if "E" in result:
        base, exp = result.split("E")
        if config.num_format_e_not:
            result = base + r"\mathrm{E}" + "{" + exp + "}"
        else:
            result = base + r" \times 10^{" + str(int(exp)) + "}"
        return ExprLatex(result, BELOW_MULT_RANK)

    return ExprLatex(result, SIGNED_RANK if obj < 0.0 else VALUE_RANK)


def _normalize_zero_float(num: float) -> float:
    """
    Replace `floats` that are theoretically zero with `0.0`.

    Due to floating-point precision limitations, mathematical operations
    can produce extremely small numbers that should theoretically be
    0 (e.g., `math.cos(math.pi / 2)` returns `6.123233995736766e-17`).
    This function checks if a `float` is close to zero within a
    configurable absolute tolerance and replaces it with 0.0.

    This is necessary to avoid theoretical zeros to be displayed in
    scientific notation, but allow number types that have controlled
    precision like `Decimal` to be displayed properly.
    """

    if isclose(num, 0.0, abs_tol=config.zero_float_threshold):
        return 0.0
    return num


def _convert_special_num(obj: float | Decimal) -> ExprLatex | None:
    """Detect and convert exceptional values. Returns `None` if the
    number is not special.
    """

    if isinf(obj):
        return ExprLatex(r"-\infty" if obj < 0 else r"\infty")
    if isnan(obj):
        return ExprLatex(r"\text{NaN}")
    if copysign(1, obj) < 0.0 and obj == 0.0:
        return convert_num(0.0)
    return None


def _fraction(obj: Fraction) -> ExprLatex:
    """Converter for `Fraction` type object."""

    numerator = convert_int(obj.numerator)
    denominator = convert_int(obj.denominator)
    return ExprLatex(
        r"\frac{" + numerator.latex + "}{" + denominator.latex + "}", DIV_RANK
    )


def _complex(obj: complex) -> ExprLatex:
    """Converter for `complex` type object."""

    if config.use_polar:
        r, phi = polar(obj)
        r_latex = convert_num(r).latex

        if config.use_polar_deg:
            phi_latex = rf"{convert_num(degrees(phi)).latex}^{{\circ}}"
        else:
            phi_latex = rf"{convert_num(phi).latex}\ \mathrm{{rad}}"

        return ExprLatex(rf"{r_latex} \angle {phi_latex}", BELOW_POW_RANK)

    if not obj.real:
        if isclose(obj.imag, 1.0):
            return ExprLatex(r"\mathrm{i}")

        if _normalize_zero_float(obj.imag) == 0.0:
            return convert_num(0.0)

        imag = convert_num(obj.imag)
        if imag.rank <= BELOW_MULT_RANK:
            imag.latex = format_delims(imag.latex, (r"\left(", r"\right)"))

        return ExprLatex(rf"{imag.latex}\,\mathrm{{i}}", BELOW_MULT_RANK)

    real = convert_num(obj.real)
    imag_sign = "+" if obj.imag >= 0.0 else "-"

    imag_abs = convert_num(abs(obj.imag))
    if imag_abs.rank <= BELOW_MULT_RANK:
        imag_abs.latex = format_delims(imag_abs.latex, (r"\left(", r"\right)"))

    return ExprLatex(
        rf"{real.latex} {imag_sign} {imag_abs.latex}\,\mathrm{{i}}",
        BELOW_ADD_RANK,
    )


def _iters(obj: list | str | set) -> Optional[ExprLatex]:
    """Convert a `list`, `str`, or `set` type object. Returns `None` if
    any one of the elements return `None` when converted.
    """

    elts_latex: list[str] = []
    for o in obj:
        converted = convert_object(o)
        if converted is None:
            return None
        elts_latex.append(converted.latex)

    if getattr(config, f"show_{type(obj).__name__}_as_col"):
        syntax = COLLECTIONS_COL[type(obj)]
    else:
        syntax = COLLECTIONS_ROW[type(obj)]
    latex = format_elts(elts_latex, *syntax)

    return ExprLatex(latex, COLLECTIONS_RANK)


def _dict(obj: dict) -> Optional[ExprLatex]:
    """Convert for `dict` type object."""

    elts: list[str] = []
    obj_latex: dict[str, str] = {}
    for obj_key, obj_value in obj.items():
        key = convert_object(obj_key)
        value = convert_object(obj_value)
        if key is None or value is None:
            return None
        obj_latex[key.latex] = value.latex

    if not obj_latex:
        return ExprLatex(r"\left\{\right\}", COLLECTIONS_RANK)

    if config.show_dict_as_col:
        elts = [rf"{k} &\to {v}" for k, v in obj_latex.items()]
        syntax = COLLECTIONS_COL[dict]
    else:
        elts = [rf"{k} \to {v}" for k, v in obj_latex.items()]
        syntax = COLLECTIONS_ROW[dict]

    latex = format_elts(elts, *syntax)

    return ExprLatex(latex, COLLECTIONS_RANK)


def _range(obj: range) -> Optional[ExprLatex]:
    """Convert for `range` type object."""

    if len(obj) <= 3:
        elts = [str(o) for o in obj]
    else:
        dots = r"\vdots" if config.show_list_as_col else r"\cdots"
        elts = [str(obj[0]), str(obj[1]), dots, str(obj[-1])]

    if config.show_list_as_col:
        syntax = COLLECTIONS_COL[list]
    else:
        syntax = COLLECTIONS_ROW[list]

    return ExprLatex(format_elts(elts, *syntax), COLLECTIONS_RANK)


# fmt: off
register_object_converter(type, lambda obj: ExprLatex(r"\texttt{" + obj.__name__ + "}"))
register_object_converter(type(...), lambda _: ExprLatex(r"\dots"))
register_object_converter(type(None), lambda _: ExprLatex(r"\emptyset"))
register_object_converter(bool, lambda obj: ExprLatex(r"\text{" + str(obj) + "}"))
register_object_converter(str, convert_str)
register_object_converter(int, convert_int)
register_object_converter(float, convert_num)
register_object_converter(Decimal, convert_num)
register_object_converter(Fraction, _fraction)
register_object_converter(complex, _complex)
register_object_converter(list, _iters)
register_object_converter(tuple, _iters)
register_object_converter(set, lambda o: _iters(set(sorted(o))))
register_object_converter(dict, _dict)
register_object_converter(range, _range)
