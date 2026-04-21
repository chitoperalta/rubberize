"""Converters for Pint objects.

Custom units LaTeX can be registered using register_units_latex.
"""

from __future__ import annotations

import re
from fractions import Fraction

import pint

from rubberize.config import config
from rubberize.latexer import formatters, ranks, rules
from rubberize.latexer.expr_latex import ExprLatex
from rubberize.latexer.objects.convert_object import (
    convert_object,
    register_object_converter,
)


_custom_units_latex: dict[frozenset[tuple[str, object]], str] = {}


def register_units_latex(latex: str, **kwargs: object) -> None:
    """Register custom LaTeX representation for Pint units.

    Units are specified as kwargs, where keywords are unit names and
    values are their corresponding exponents.

    Example:
    >>> register_units_latex(r"\\mathrm{N} \\cdot \\mathrm{m}", meter=1, newton=1)

    Args:
        latex: The LaTeX string for the units.
        **kwargs: Unit-exponent pairs defining the the units.
    """

    _custom_units_latex[frozenset(kwargs.items())] = latex


def _quantity(obj: pint.Quantity) -> ExprLatex | None:
    """Converter for pint.Quantity object."""

    mag = convert_object(obj.magnitude)

    if mag is None:
        return None

    if config.use_fif_units and obj.units in ("foot", "inch"):
        return _foot_inch_fraction(obj)
    if config.use_dms_units and obj.units == "degree":
        return _degree_minute_second(obj)

    units = frozenset((u, p) for u, p in obj.unit_items())
    units_latex = _custom_units_latex.get(units, f"{obj.units:~L}")
    units_latex = _format_units_latex(units_latex)

    if mag.rank <= ranks.BELOW_MULT_RANK:
        prefix, suffix = rules.OPERAND_SYNTAX
        mag_latex = formatters.format_delims(prefix, mag.latex, suffix)
    else:
        mag_latex = mag.latex

    if units_latex == r"\mathrm{deg}":
        return ExprLatex(rf"{mag_latex}^{{\circ}}", ranks.BELOW_POW_RANK)
    if units_latex:
        return ExprLatex(rf"{mag_latex}\ {units_latex}", ranks.BELOW_MULT_RANK)
    return mag


def _format_units_latex(latex: str) -> str:
    if config.use_contextual_mult:
        latex = latex.replace(r" \cdot ", r"\,")

    if not config.use_inline_units:
        return latex

    match = re.match(r"\\frac{(.*)}{(.*)}", latex)
    if not match:
        return latex

    numerator, denominator = match.groups()
    denominators = re.findall(r"(\\mathrm{[^}]+}(?:\^\{\d+\})?)", denominator)

    if len(denominators) == 1 and numerator != "1":
        # use a solidus for single-term denominators
        return f"{numerator} / {denominator}"

    units = []
    if numerator != "1":
        units.append(numerator)

    for d in denominators:
        if "^" not in d:
            units.append(d + "^{-1}")
        else:
            d = re.sub(
                r"\^\{(\d+)\}", lambda m: "^{-" + f"{int(m.group(1))}" + "}", d
            )
            units.append(d)

    op = r"\," if config.use_contextual_mult else r" \cdot "
    return op.join(units)


def _foot_inch_fraction(obj: pint.Quantity) -> ExprLatex:
    """Convert foot or inch pint.Quantity to foot-inch-fraction format
    LaTeX, e.g., 5’ 3 1/2”.
    """

    total_inches = obj.to("inch").magnitude

    feet = 0
    if obj.units == "foot":
        feet = int(total_inches // 12)
        total_inches -= feet * 12

    whole_inches = int(total_inches)
    fractional_inches = Fraction(
        round((total_inches - whole_inches) * config.fif_prec), config.fif_prec
    )

    if fractional_inches == 1:
        whole_inches += 1
        fractional_inches = Fraction(0, config.fif_prec)
    if obj.units == "foot" and whole_inches == 12:
        feet += 1
        whole_inches = 0

    parts = []

    if feet:
        parts.append(str(feet) + r"\text{{’}}")
    if whole_inches or fractional_inches:
        inch_parts = []
        if whole_inches:
            inch_parts.append(str(whole_inches))
        if fractional_inches:
            inch_parts.append(str(fractional_inches))
        parts.append(r"\ ".join(inch_parts) + r"\text{”}")

    latex = r"\ ".join(parts)
    if not latex:
        if obj.units == "foot":
            latex = r"0\text{’}"
        else:
            latex = r"0\text{”}"

    rank = ranks.BELOW_POW_RANK

    return ExprLatex(latex, rank)


def _degree_minute_second(obj: pint.Quantity) -> ExprLatex:
    """Convert angle pint.Quantity to degree-minute-second format."""

    total = obj.to("degree").magnitude

    degrees = int(total)
    minutes = int((total - degrees) * 60)
    seconds = (total - degrees - minutes / 60) * 3600

    if seconds == 60:
        minutes += 1
        seconds = 0
    if minutes == 60:
        degrees += 1
        minutes = 0

    parts = []

    if degrees:
        parts.append(str(degrees) + r"^{\circ}")
    if minutes:
        parts.append(str(minutes) + r"\text{{’}}")
    if seconds:
        parts.append(f"{seconds:.{config.float_prec}f}" + r"\text{”}")

    latex = r"\ ".join(parts)
    if not latex:
        latex = r"0^{\circ}"

    rank = ranks.BELOW_POW_RANK

    return ExprLatex(latex, rank)


def _unit(obj: pint.Unit) -> ExprLatex:
    """Converter for pint Quantity type object."""

    # pylint: disable-next=protected-access
    units = frozenset((u, p) for u, p in dict(obj._units).items())
    latex = _custom_units_latex.get(units, f"{obj:~L}")

    latex = _format_units_latex(latex)
    rank = ranks.VALUE_RANK

    return ExprLatex(latex, rank)


# fmt: off
register_object_converter(pint.Quantity, _quantity)
register_object_converter(pint.Unit, _unit)

register_units_latex(r"\mathrm{N} \cdot \mathrm{m}", meter=1, newton=1)
register_units_latex(r"\mathrm{N} \cdot \mathrm{mm}", millimeter=1, newton=1)
register_units_latex(r"\frac{1}{\mathrm{N} \cdot \mathrm{m}}", meter=-1, newton=-1)
register_units_latex(r"\frac{1}{\mathrm{N} \cdot \mathrm{mm}}", millimeter=-1, newton=-1)
register_units_latex(r"\mathrm{V} \cdot \mathrm{s}", volt=1, second=1)
