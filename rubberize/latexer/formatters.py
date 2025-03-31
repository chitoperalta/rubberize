"""Functions to format source strings to LaTeX representations."""

import re
from typing import Optional

from rubberize.config import config
from rubberize.latexer.expr_rules import (
    GREEK,
    ACCENTS,
    MODIFIERS,
    COLLECTIONS_COL,
    COLLECTIONS_ROW,
)
from rubberize.utils import wrap_delims


def format_name(name: str, *, call: bool = False) -> str:
    """Convert a name into its LaTeX representation.

    This function applies various transformations to format the given
    name according to LaTeX conventions, including symbol replacements,
    subscript handling, and function call formatting.

    Leading and trailing underscores are preserved and escaped. If
    subscripts are enabled, trailing underscores are appended to the
    base part instead of the subscript.

    If symbols are enabled and the name starts in a specified allowed
    starting greek letter, it gets rendered.

    If subscripts are enabled, underscores within the name are
    interpreted as subscripts, except for consecutive underscores
    (`__`), which are escaped as `\\_`. If subscripts are disabled, all
    underscores are escaped.

    Args:
        name: The identifier to be formatted.
        call: Whether to treat the name as a function call, applying
            `\\operatorname{}` for proper LaTeX rendering.

    Returns:
        The formatted LaTeX string.
    """

    if config.use_symbols and name == "lambda_":
        # Special case: a name "lambda" conflicts with Python lambda
        return _wrap_part(r"\lambda", call)

    leading, name, trailing = _split_escape_edge(name)

    if config.use_symbols:
        greek_start, name = _get_greek_start(name)
        leading += greek_start

        name = _replace_greeks(name)
        name = _replace_accents(name)
        name = _replace_modifiers(name)

    if config.use_subscripts and "_" in name:
        name = re.sub(r"__+", lambda m: r"\_" * (len(m.group()) - 1), name)

        base, *subs = re.split(r"(?<!\\)_", name)
        base = _wrap_part(base, call)

        if not subs:
            return f"{leading}{base}{trailing}"

        subs = [_wrap_part(s) for s in subs]
        return f"{leading}{base}{trailing}_{{{', '.join(subs)}}}"

    return f"{leading}{_wrap_part(name.replace('_', r'\_'), call)}{trailing}"


def _get_greek_start(name: str) -> tuple[str, str]:
    """If the beginning of the base name is a Greek letter, extract it."""

    base, *_ = name.split("_", 1)

    for greek in config.greek_starts:
        if base.startswith(greek) and base.replace(greek, "", 1):
            return rf"\{greek} ", f"{name[len(greek):]}"

    return "", name


def _replace_greeks(name: str) -> str:
    """Replace Greek symbols in a name to LaTeX, e.g. beta -> \\beta."""

    return "_".join([f"\\{n}" if n in GREEK else n for n in name.split("_")])


def _replace_accents(name: str) -> str:
    """Replace accents in a name to LaTeX, e.g. i_hat -> \\hat{i}."""

    parts = name.split("_")
    replaced = [parts.pop(0)]

    for part in parts:
        if f"_{part}" in ACCENTS:
            replaced[-1] = ACCENTS[f"_{part}"] + "{" + replaced[-1] + "}"
        else:
            replaced.append(part)
    return "_".join(replaced)


def _replace_modifiers(name: str) -> str:
    """Replace modifiers in a name to LaTex, e.g. f_prime -> f'."""

    for k, v in MODIFIERS.items():
        if k in name:
            name = name.replace(k, v)
    return name


def _split_escape_edge(name: str) -> tuple[str, str, str]:
    """Splits a name into (leading escaped underscores, core name,
    trailing escaped underscores)
    """

    match = re.match(r"(^_*)(.*?)(_*$)", name)
    if match:
        return (
            match.group(1).replace("_", r"\_"),
            match.group(2),
            match.group(3).replace("_", r"\_"),
        )
    return "", name, ""


def _wrap_part(name: str, call: bool = False) -> str:
    """Returns a part wrapped in `\\mathrm` if not a single-character
    part. If used for a function name (`call=True`), wraps the whole
    part in `\\operatorname`.
    """

    if call:
        return r"\operatorname{" + name + "}"

    if not _is_single_char_part(name):
        return r"\mathrm{" + name + "}"

    return name


def _is_single_char_part(part: str) -> bool:
    """Checks if the part (with all symbols converted) is a single
    letter.
    """

    if config.use_symbols:
        # Remove modifiers
        for modifier in MODIFIERS.values():
            part = part.replace(modifier, "")

        # Remove accents
        while True:
            for accent in ACCENTS.values():
                if part.startswith(accent + "{") and part.endswith("}"):
                    part = part[len(accent) + 1 : -1]
                    break
            else:
                break

    # Check if single greek letter after removing modifiers and accents
    if len(part) > 1:
        return part.lstrip("\\") in GREEK if config.use_symbols else False

    # Check if single character otherwise
    return len(part) == 1


def format_equation(
    lhs: str | list[str], rhs: Optional[str | list[str]] = None
) -> str:
    """Format an equation into its LaTeX representation.

    If `config.multiline` is enabled and `rhs` has multiple elements,
    the output will use the aligned environment for each `rhs`
    expression, aligned at the equal sign (`=`).

    Args:
        lhs: The left-hand side of the equation.
        rhs: The right-hand side of the equation.

    Returns:
        A formatted LaTeX string representing the equation.
    """

    lhs = [lhs] if isinstance(lhs, str) else lhs
    rhs = [rhs] if isinstance(rhs, str) else rhs or []

    lhs = [l for l in lhs if l]
    rhs = [r for r in rhs if r and r not in lhs]

    lhs_eqn = " = ".join(lhs)
    rhs_eqn = " = ".join(rhs)

    if not rhs:
        return lhs_eqn

    eqn = " = ".join([lhs_eqn, rhs_eqn])

    if config.multiline and len(rhs) > 1:
        lines = [f"{lhs_eqn} &= {rhs.pop(0)}"]
        lines.extend(f"&= {r}" for r in rhs)
        eqn = format_elts(
            lines, r" \\" + "\n", (r"\begin{aligned}", r"\end{aligned}")
        )

    return eqn


def format_delims(
    text: str,
    delims: tuple[str, str],
    *,
    indent: int = 4,
) -> str:
    """Wrap a LaTeX expression with the specified delimiters, applying
    spacing rules.

    - No space for regular delimiters: e.g., `(...)`, `[...]`, `{...}`
    - Adds space for `\\left( ... \\right)`, etc.
    - No space if text is empty
    - Formats latex with linebreaks (`\\\\`) text as a block

    Args:
        text: The LaTeX expression to wrap.
        delims: A tuple containing the left and right delimiters.
        indent: The number of spaces used for block indentation. The
            default is `4`

    Returns:
        The formatted LaTeX string with applied delimiter rules.
    """

    has_break = r"\\" in text
    left, right = delims
    has_left_right = (
        left.startswith(r"\left")
        or right.startswith(r"\right")
        or left.startswith(r"\begin")
        or right.startswith(r"\end")
    )
    return wrap_delims(
        text,
        delims,
        force_block=has_break,
        spaced_line=has_left_right,
        indent=indent,
    )


def format_elts(
    elts: str | list[str], sep: str, delims: tuple[str, str], *, indent: int = 4
) -> str:
    """Format and wrap a collection of LaTeX expression elements using
    sepcified separator and delimiters.

    If `elts` is a string, it is treated as a single-element list.

    Args:
        elts: The LaTeX expression elements to format.
        sep: The separator to use when joining the elements.
        delims: A tuple containing the left and right delimiters.
        indent: The number of spaces used for block indentation. The
            default is `4`.

    Returns:
        The formatted LaTeX string with the joined elements wrapped in
        delimiters.
    """
    elts = list(elts) if isinstance(elts, str) else elts
    return format_delims(sep.join(elts), delims, indent=indent)


def format_array(
    array: str | list,
    *,
    indent: int = 4,
    depth: int = 0,
) -> str:
    """Recursively format a nested array of LaTeX expressions.

    This function processes a nested list structure, applying the
    appropriate formatting based on the array's depth and configuration
    settings.

    - At the top level (`depth == 0`), it determines whether to format
        the array as a column or row based on `config.show_list_as_col`.
    - At deeper levels, elements are joined according to row syntax.
    - Non-list elements are returned as-is.

    Args:
        array: The array to format.
        indent: The number of spaces used for block indentation. The
            default is `4`.
        depth: The current depth level in the recursive processing. The
            default is `0`, of course.

    Returns:
        A LaTeX-formatted string representing the structured array.
    """

    row_syntax = COLLECTIONS_ROW[list]
    col_syntax = COLLECTIONS_COL[list]

    if not isinstance(array, list):
        return array

    if all(not isinstance(elt, list) for elt in array):
        if depth == 0:
            if config.show_list_as_col:
                return format_elts(array, *col_syntax, indent=indent)
            return format_elts(array, *row_syntax, indent=indent)
        return row_syntax[0].join(array)

    formatted_sub_arrs = [
        format_array(sub_arr, indent=indent, depth=depth + 1)
        for sub_arr in array
    ]
    return format_elts(formatted_sub_arrs, *col_syntax, indent=indent)
