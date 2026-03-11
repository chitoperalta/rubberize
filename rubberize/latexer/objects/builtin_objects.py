"""Converters for builtin objects and objects from the Standard Library."""

import cmath
import math
from decimal import Decimal
from fractions import Fraction

from rubberize._exceptions import RubberizeSyntaxError
from rubberize.config import config
from rubberize.latexer import formatters, ranks, rules
from rubberize.latexer.expr_latex import ExprLatex
from rubberize.latexer.objects.convert_object import (
    convert_object,
    register_object_converter,
)


def convert_str(obj: str) -> ExprLatex:
    """Converter for str."""

    table = str.maketrans(
        {
            "\\": r"\\",
            "{": r"\{",
            "}": r"\}",
            "$": r"\$",
            # prefer fullwidth variants
            "_": "＿",
            "^": "＾",
            "#": "＃",
            "%": "％",
            "&": "＆",
            "~": "〜",
        }
    )

    obj = obj.translate(table)

    if config.str_quotes == "":
        left = right = ""
    elif config.str_quotes == "'":
        left, right = "‘", "’"
    else:
        left, right = "“", "”"

    latex = r"\text" + config.str_font + "{" + left + obj + right + "}"
    rank = ranks.VALUE_RANK

    return ExprLatex(latex, rank)


def convert_int(obj: int) -> ExprLatex:
    """Converter for int."""

    thousands = rules.THOUSANDS_SEPARATOR[config.thousands_separator]
    latex = f"{obj:,d}".replace(",", thousands)
    rank = ranks.SIGNED_RANK if obj < 0.0 else ranks.VALUE_RANK

    return ExprLatex(latex, rank)


def convert_float(obj: float) -> ExprLatex:
    """Converter for float."""

    obj = _normalize_zero(obj)

    special = _convert_special_float(obj)
    if special is not None:
        return special

    if config.float_format == "FIX" and (
        abs(obj) >= 10**config.float_max_digits
        or (
            0.0 < abs(obj) < 10 ** (-config.float_prec)
            and round(obj, config.float_prec) == 0.0
        )
    ):
        float_format = "SCI"
    else:
        float_format = config.float_format

    if float_format == "FIX":
        latex = f"{obj:,.{config.float_prec}f}"
    elif float_format == "SCI":
        latex = f"{obj:,.{config.float_prec}E}"
    elif float_format == "GEN":
        latex = f"{obj:,.{config.float_prec}G}"
    elif float_format == "ENG":
        if obj != 0:
            exp = 3 * (math.floor(math.log10(abs(float(obj)))) // 3)
        else:
            exp = 0
        base = obj / 10**exp
        latex = f"{base:,.{config.float_prec}f}E{int(exp):+03d}"
    else:
        raise RubberizeSyntaxError(f"Invalid format: {config.float_format}")

    return _format_number_latex(latex)


def _normalize_zero(num: float) -> float:
    if math.isclose(num, 0.0, abs_tol=config.zero_float_threshold):
        return 0.0
    return num


def _convert_special_float(obj: float | Decimal) -> ExprLatex | None:
    if math.isinf(obj):
        return ExprLatex(r"-\infty" if obj < 0 else r"\infty")
    if math.isnan(obj):
        return ExprLatex(r"\text{NaN}")
    if math.copysign(1, obj) < 0.0 and obj == 0.0:
        return convert_float(0.0)
    return None


def _format_number_latex(latex: str) -> ExprLatex:
    thousands = rules.THOUSANDS_SEPARATOR[config.thousands_separator]
    decimal = rules.DECIMAL_MARKER[config.decimal_marker]
    latex = latex.replace(".", "ddd").replace(",", "ttt")
    latex = latex.replace("ddd", decimal).replace("ttt", thousands)

    if "E" in latex:
        base, exp = latex.split("E")

        if config.use_e_not:
            latex = base + r"\mathrm{E}" + "{" + exp + "}"
        else:
            latex = base + r" \times 10^{" + str(int(exp)) + "}"

        rank = ranks.BELOW_MULT_RANK
        return ExprLatex(latex, rank)

    rank = ranks.SIGNED_RANK if latex.startswith("-") else ranks.VALUE_RANK

    return ExprLatex(latex, rank)


def _complex(obj: complex) -> ExprLatex:
    """Converter for complex."""

    if config.use_polar:
        r, phi = cmath.polar(obj)
        r_latex = convert_float(r).latex

        if config.use_polar_deg:
            phi_latex = rf"{convert_float(math.degrees(phi)).latex}^{{\circ}}"
        else:
            phi_latex = rf"{convert_float(phi).latex}\ \mathrm{{rad}}"

        latex = rf"{r_latex} \angle {phi_latex}"
        rank = ranks.BELOW_POW_RANK

    elif not obj.real:
        if math.isclose(obj.imag, 1.0):
            return ExprLatex(r"\mathrm{i}")

        if _normalize_zero(obj.imag) == 0.0:
            return convert_float(0.0)

        imag = convert_float(obj.imag)
        latex = imag.latex

        if imag.rank <= ranks.BELOW_MULT_RANK:
            latex = formatters.format_delims(r"\left( ", latex, r" \right)")

        latex += r"\,\mathrm{i}"
        rank = ranks.BELOW_MULT_RANK

    else:
        real = convert_float(obj.real)
        imag_sign = "+" if obj.imag >= 0.0 else "-"
        latex = f"{real.latex} {imag_sign} "

        imag_abs = convert_float(abs(obj.imag))
        latex += imag_abs.latex

        if imag_abs.rank <= ranks.BELOW_MULT_RANK:
            latex = formatters.format_delims(r"\left(", latex, r"\right)")

        latex += r"\,\mathrm{i}"
        rank = ranks.BELOW_ADD_RANK

    return ExprLatex(latex, rank)


def _iters(obj: list | str | set) -> ExprLatex | None:
    """Converter for list, str, or set.

    Returns None if any one of the elements return None when converted.
    """

    elts: list[str] = []
    for o in obj:
        converted = convert_object(o)
        if converted is None:
            return None
        elts.append(converted.latex)

    iter_type = type(obj).__name__.upper()

    if len(elts) > config.max_inline_elts:
        prefix, sep, suffix = getattr(rules, f"{iter_type}_COL_SYNTAX")
    else:
        prefix, sep, suffix = getattr(rules, f"{iter_type}_ROW_SYNTAX")

    latex = formatters.format_delims(prefix, sep.join(elts), suffix)
    rank = ranks.COLLECTIONS_RANK

    return ExprLatex(latex, rank)


def _dict(obj: dict) -> ExprLatex | None:
    """Convert for `dict` type object."""

    obj_latex: dict[str, str] = {}

    for k, v in obj.items():
        key = convert_object(k)
        value = convert_object(v)
        if key is None or value is None:
            return None
        obj_latex[key.latex] = value.latex

    if len(obj_latex) > config.max_inline_elts:
        prefix, sep, suffix = rules.DICT_COL_SYNTAX
        kv_sep = rules.DICT_COL_KV_SYNTAX
    else:
        prefix, sep, suffix = rules.DICT_ROW_SYNTAX
        kv_sep = rules.DICT_ROW_KV_SYNTAX

    elts = [rf"{k}{kv_sep}{v}" for k, v in obj_latex.items()]
    latex = formatters.format_delims(prefix, sep.join(elts), suffix)
    rank = ranks.COLLECTIONS_RANK

    return ExprLatex(latex, rank)


def _range(obj: range) -> ExprLatex | None:
    """Convert for `range` type object."""

    if len(obj) <= 4:
        elts = [str(o) for o in obj]
    else:
        elts = [str(obj[0]), str(obj[1]), "\ue000", str(obj[-1])]

    if len(elts) > config.max_inline_elts:
        prefix, sep, suffix = rules.TUPLE_COL_SYNTAX
        dots = r"\vdots"
    else:
        prefix, sep, suffix = rules.TUPLE_ROW_SYNTAX
        dots = r"\cdots"

    latex = formatters.format_delims(
        prefix, sep.join(elts).replace("\ue000", dots), suffix
    )
    rank = ranks.COLLECTIONS_RANK

    return ExprLatex(latex, rank)


def convert_decimal(obj: Decimal) -> ExprLatex:
    """Converter for decimal.Decimal."""

    special = _convert_special_decimal(obj)
    if special is not None:
        return special

    latex = f"{obj:,}"

    return _format_number_latex(latex)


def _convert_special_decimal(obj: Decimal) -> ExprLatex | None:
    if obj.is_infinite():
        return ExprLatex(r"-\infty" if obj < 0 else r"\infty")
    if obj.is_nan():
        return ExprLatex(r"\text{NaN}")
    if obj.is_signed() and obj == Decimal("0"):
        return convert_decimal(Decimal("0"))
    return None


def _fraction(obj: Fraction) -> ExprLatex:
    """Converter for fractions.Fraction."""

    numerator = convert_int(obj.numerator)
    denominator = convert_int(obj.denominator)

    latex = r"\frac{" + numerator.latex + "}{" + denominator.latex + "}"
    rank = ranks.DIV_RANK

    return ExprLatex(latex, rank)


# fmt: off
register_object_converter(type, lambda obj: ExprLatex(r"\texttt{" + obj.__name__ + "}"))
register_object_converter(type(...), lambda _: ExprLatex(r"\dots"))
register_object_converter(type(None), lambda _: ExprLatex(r"\emptyset"))
register_object_converter(bool, lambda obj: ExprLatex(r"\text{" + str(obj) + "}"))
register_object_converter(str, convert_str)
register_object_converter(int, convert_int)
register_object_converter(float, convert_float)
register_object_converter(complex, _complex)
register_object_converter(list, _iters)
register_object_converter(tuple, _iters)
register_object_converter(set, lambda o: _iters(set(sorted(o))))
register_object_converter(dict, _dict)
register_object_converter(range, _range)

register_object_converter(Decimal, convert_decimal)
register_object_converter(Fraction, _fraction)
