"""Deprecated: This module is deprecated and may be removed in the
future.

These functions are originally intended to detect different value
patterns for operand wrapping. Now, types converted to latex are
assigned a rank based on operator precedence.
"""

import re

DECIMAL_PATTERN = (
    r"\d{1,3}(?:(?:\\,|\{[,.]\}|\\text\{’\})?\d{3})*(?:(?:\.|\{,\})?\d+)?$"
)


def is_decimal_latex(latex: str) -> bool:
    """Check if LaTeX string is an integer or a decimal number."""

    return re.fullmatch(f"[+-]?{DECIMAL_PATTERN}", latex) is not None


def is_sci_not_latex(latex: str) -> bool:
    """Check if LaTeX string is in scientific notation."""

    sci_not_pattern = (
        f"[+-]?{DECIMAL_PATTERN}"
        r"(?:\s*\\times\s*10\^{-?\d+}|\s*\\mathrm{[eE]}{[+-]\d+})"
    )
    return re.fullmatch(sci_not_pattern, latex) is not None


def is_value_latex(latex: str) -> bool:
    """Check if LaTeX string is a valid numeric value (a decimal or
    scientific notation number).
    """

    value_pattern = (
        f"[+-]?{DECIMAL_PATTERN}"
        r"(?:\s*\\times\s*10\^{-?\d+}|\s*\\mathrm{[eE]}{[+-]\d+})?"
    )
    return re.fullmatch(value_pattern, latex) is not None


def is_imaginary_latex(latex: str) -> bool:
    """Check if LaTeX string is a pure imaginary number."""

    imaginary_pattern = rf"\(?[+-]?{DECIMAL_PATTERN}\)?\\,\\mathrm{{i}}"
    return re.fullmatch(imaginary_pattern, latex) is not None


def is_complex_latex(latex: str) -> bool:
    """Check if LaTeX string is a complex number."""

    complex_match = re.fullmatch(
        r"\(?([^()]+?)\)?\ [+-]\ \(?([^()]+?)\)?\\,\\mathrm{i}", latex
    )
    if complex_match:
        real, imag = complex_match.groups()
    else:
        return False
    return (is_value_latex(real) or real is None) and is_value_latex(imag)


def is_units_latex(latex: str) -> bool:
    """Check if LaTeX string follows a valid unit format."""

    if latex == r"^{\circ}":
        return True

    units_pattern = (
        r"(?:\\mathrm{[^}]+}(?:\^{-?\d+})?(?:\s*(?:\\,|\\cdot)\s*)?)+"
    )

    frac_match = re.fullmatch(r"\\frac{(.+?)}{(.+?)}", latex)
    if frac_match:
        num, den = frac_match.groups()
        return re.fullmatch(units_pattern, den) is not None and (
            num == "1" or re.fullmatch(units_pattern, num) is not None
        )

    inline_units_den_pattern = r"(?:\\mathrm{[^}]+}(?:\^{\d+})?)"

    solidus_match = re.fullmatch(r"(.+?)\s*/\s*(.+?)", latex)
    if solidus_match:
        cnum, cden = solidus_match.groups()
        return (
            re.fullmatch(inline_units_den_pattern, cden) is not None
            and re.fullmatch(units_pattern, cnum) is not None
        )

    return re.fullmatch(units_pattern, latex) is not None


def is_quantity_latex(latex: str) -> bool:
    """Check if LaTeX string is a valid physical quantity
    (value + unit).
    """

    parts = latex.split(r"\ ", 1)
    if len(parts) == 2:
        value, units = parts
    elif latex.endswith(r"^{\circ}"):
        value, units = latex[:-8], r"^{\circ}"
        # return False
    else:
        return False
    return is_value_latex(value) and is_units_latex(units)


def is_x_eq_x(latex: str) -> bool:
    """Check if LaTeX string is `x = x` where `x` is any value including
    whitespace.
    """

    return re.fullmatch(r"\s*(.+?)\s*=\s*\1\s*", latex, re.DOTALL) is not None
