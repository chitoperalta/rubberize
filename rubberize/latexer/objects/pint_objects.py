"""Converters for Pint objects.

Custom units LaTeX representations can be registered using
`register_units_latex()`, allowing users to define their own display
formats for specific unit combinations.
"""

import re
from fractions import Fraction

import pint

from rubberize.config import config
from rubberize.latexer.expr_latex import ExprLatex
from rubberize.latexer.formatters import format_delims
from rubberize.latexer.objects.convert_object import (
    register_object_converter,
    convert_object,
)
from rubberize.latexer.objects.builtin_objects import convert_num
from rubberize.latexer.ranks import BELOW_MULT_RANK, BELOW_POW_RANK


_custom_units_latex: dict[frozenset[tuple[str, int]], str] = {}


def register_units_latex(latex: str, **kwargs: int) -> None:
    """Register a custom LaTeX representation for a unit.

    This function allows users to define a custom LaTeX format for
    specific unit combinations. The units are specified as keyword
    arguments, where keys are unit names and values are their
    corresponding exponents.

    Example:
    >>> register_units_latex(r"\\mathrm{N} \\cdot \\mathrm{m}", meter=1, newton=1)

    Args:
        latex: The LaTeX string representing the unit.
        **kwargs: Unit-exponent pairs defining the unit combination.
    """

    _custom_units_latex[frozenset(kwargs.items())] = latex


def _quantity(obj: pint.Quantity) -> ExprLatex | None:
    """Converter for pint Quantity type object."""

    mag = convert_object(obj.magnitude)

    if mag is None:
        return None

    if config.use_fif_units and obj.units in ("foot", "inch"):
        return ExprLatex(_foot_inch_fraction(obj), BELOW_POW_RANK)
    if config.use_dms_units and obj.units == "degree":
        return ExprLatex(_degree_minute_second(obj), BELOW_POW_RANK)

    units = frozenset((u, int(p)) for u, p in obj.unit_items())
    units_latex = _custom_units_latex.get(units, f"{obj.units:~L}")
    units_latex = _reformat_units(units_latex)

    if mag.rank <= BELOW_MULT_RANK:
        mag_latex = format_delims(mag.latex, (r"\left(", r"\right)"))
    else:
        mag_latex = mag.latex

    if units_latex == r"\mathrm{deg}":
        return ExprLatex(rf"{mag_latex}^{{\circ}}", BELOW_POW_RANK)
    if units_latex:
        return ExprLatex(rf"{mag_latex}\ {units_latex}", BELOW_MULT_RANK)
    return convert_num(obj.magnitude)


def _unit(obj: pint.Unit) -> ExprLatex:
    """Converter for pint Quantity type object."""

    # pylint: disable-next=protected-access
    units = frozenset((u, int(p)) for u, p in dict(obj._units).items())
    units_latex = _custom_units_latex.get(units, f"{obj:~L}")
    units_latex = _reformat_units(units_latex)
    return ExprLatex(units_latex, BELOW_MULT_RANK)


def _reformat_units(units_latex: str) -> str:
    """Make the latex for the unit compact."""

    if config.use_contextual_mult:
        units_latex = units_latex.replace(r" \cdot ", r"\,")

    if not config.use_inline_units:
        return units_latex

    match = re.match(r"\\frac{(.*)}{(.*)}", units_latex)
    if not match:
        return units_latex

    num_str, den_str = match.groups()
    dens = re.findall(r"(\\mathrm{[^}]+}(?:\^\{\d+\})?)", den_str)

    if len(dens) == 1 and num_str != "1":
        # Use a solidus for single-term denominators
        return f"{num_str} / {den_str}"

    units = []
    if num_str != "1":
        units.append(num_str)
    for den in dens:
        if "^" not in den:
            units.append(den + "^{-1}")
        else:
            den = re.sub(
                r"\^\{(\d+)\}",
                lambda m: "^{-" + f"{int(m.group(1))}" + "}",
                den,
            )
            units.append(den)

    op = r"\," if config.use_contextual_mult else r" \cdot "
    return op.join(units)


def _foot_inch_fraction(length: pint.Quantity) -> str:
    """Change foot or inch quantity display to foot-inch-fraction format
    e.g., 5’ 3 1/2”.
    """

    inches = length.to("inch").magnitude

    # Round the fractional part to the nearest `config.fif_prec`-th
    in_whole = int(inches)
    frac = round((inches - in_whole) * config.fif_prec) / config.fif_prec

    # Simplify the fraction
    if frac:
        frac = Fraction(
            int(frac * config.fif_prec), config.fif_prec
        ).limit_denominator(config.fif_prec)
        frac_str = rf"\ {frac.numerator}/{frac.denominator}"
    else:
        frac_str = ""

    if length.units == "foot":
        ft = int(inches // 12)
        in_rem = in_whole % 12
        if in_rem or frac_str:
            return rf"{ft}\text{{’}}\ {in_rem}{frac_str}\text{{”}}"
        return rf"{ft}\text{{”}}"

    return rf"{in_whole}{frac_str}\text{{”}}"


def _degree_minute_second(angle: pint.Quantity) -> str:
    """Change angle quantity display to degree-minute-second format."""

    angle = angle.to("degree").magnitude

    degrees = int(angle)
    minutes = int((angle - degrees) * 60)
    seconds = round(
        (angle - degrees - minutes / 60) * 3600, config.num_format_prec
    )

    # Handle rounding that may push seconds to 60
    if seconds == 60:
        seconds = 0
        minutes += 1
    if minutes == 60:
        minutes = 0
        degrees += 1

    deg_str = rf"{degrees}^{{\circ}}"
    min_str = rf"\ {minutes}\text{{’}}" if minutes else ""
    sec_str = (
        rf"\ {seconds:.{config.num_format_prec}f}\text{{”}}" if seconds else ""
    )

    return f"{deg_str}{min_str}{sec_str}"


# fmt: off
register_object_converter(pint.Quantity, _quantity)
register_object_converter(pint.Unit, _unit)

register_units_latex(r"\mathrm{N} \cdot \mathrm{m}", meter=1, newton=1)
register_units_latex(r"\mathrm{N} \cdot \mathrm{mm}", millimeter=1, newton=1)
register_units_latex(r"\frac{1}{\mathrm{N} \cdot \mathrm{m}}", meter=-1, newton=-1)
register_units_latex(r"\frac{1}{\mathrm{N} \cdot \mathrm{mm}}", millimeter=-1, newton=-1)
register_units_latex(r"\mathrm{V} \cdot \mathrm{s}", volt=1, second=1)
