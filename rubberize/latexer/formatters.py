"""Functions to format source strings to LaTeX."""

import re
import textwrap

from rubberize.config import config
from rubberize.latexer import rules


def format_name(name: str, *, call: bool = False) -> str:
    """Format a name to LaTex.

    Applies various transformations to format the name according to
    latex conventions.

    Args:
        name: The name to format.
        call: If true, treat the name as a function call, applying
            `\\operatorname{}` to the base of the name.
    """

    if config.use_symbols and name == "lambda_":
        # special case: a name "lambda" conflicts with the Python keyword
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

        subs = [_wrap_part(s, call=False) for s in subs]
        return f"{leading}{base}{trailing}_" + "{" + ", ".join(subs) + "}"

    escaped_name = name.replace("_", r"\_")
    return f"{leading}{_wrap_part(escaped_name, call)}{trailing}"


def _wrap_part(name: str, call: bool) -> str:
    if call:
        return r"\operatorname{" + name + "}"

    if not _is_single_char(name):
        return r"\mathrm{" + name + "}"

    return name


def _is_single_char(name: str) -> bool:
    if config.use_symbols:
        for m in rules.MODIFIERS.values():
            name = name.replace(m, "")

        while True:
            for a in rules.ACCENTS.values():
                if name.startswith(a + "{") and name.endswith("}"):
                    name = name[len(a) + 1 : -1]
                    break
            else:
                break

    if len(name) > 1:
        # maybe a greek letter
        return name.lstrip("\\") in rules.GREEK if config.use_symbols else False

    return len(name) == 1


def _split_escape_edge(name: str) -> tuple[str, str, str]:
    m = re.match(r"(^_*)(.*?)(_*$)", name)

    if m:
        return (
            m.group(1).replace("_", r"\_"),
            m.group(2),
            m.group(3).replace("_", r"\_"),
        )

    return "", name, ""


def _get_greek_start(name: str) -> tuple[str, str]:
    base, *_ = name.split("_", 1)

    for g in config.greek_starts:
        if base.startswith(g) and base.replace(g, "", 1):
            return rf"\{g} ", f"{name[len(g):]}"

    return "", name


def _replace_greeks(name: str) -> str:
    return "_".join(
        rf"\{n}" if n in rules.GREEK else n for n in name.split("_")
    )


def _replace_accents(name: str) -> str:
    parts = name.split("_")
    replaced = [parts.pop(0)]

    for p in parts:
        if f"_{p}" in rules.ACCENTS:
            replaced[-1] = rules.ACCENTS[f"_{p}"] + "{" + replaced[-1] + "}"
        else:
            replaced.append(p)

    return "_".join(replaced)


def _replace_modifiers(name: str) -> str:
    for k, v in rules.MODIFIERS.items():
        if k in name:
            name = name.replace(k, v)

    return name


def format_delims(left: str, text: str, right: str, *, indent: int = 4) -> str:
    """Wrap text with specified LaTeX delimiters.

    Args:
        left: Opening delimiter.
        text: The text to wrap.
        right: Closing delimiter.
        indent: Number of spaces for block indentation.
    """

    if not text:
        return f"{left}{right}"

    if r"\\" in text or "\n" in text:
        text = textwrap.indent(text, " " * indent)
        return f"{left}\n{text}\n{right}"

    if (
        left.startswith(r"\left")
        or right.startswith(r"\right")
        or left.startswith(r"\begin")
        or right.startswith(r"\end")
    ):
        return f"{left} {text} {right}"

    return f"{left}{text}{right}"


def format_equation(
    lhs: str | list[str], rhs: str | list[str] | None = None
) -> str:
    """Format an equation into its LaTeX representation.

    If `config.multiline` is enabled and `rhs` has multiple elements,
    the output will use the aligned environment for each `rhs`
    expression, aligned at the equal sign (`=`).

    Args:
        lhs: The left-hand side of the equation.
        rhs: The right-hand side of the equation.
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
        eqn = format_delims(
            r"\begin{aligned}", (r" \\" + "\n").join(lines), r"\end{aligned}"
        )

    return eqn


def format_array(array: str | list, *, is_elt: bool = False) -> str:
    """Format a nested list of strings into a LaTeX representation of an
    array.

    Args:
        array: The array to format.
        is_elt: Whether the input is an element of an array.
    """

    if not isinstance(array, list):
        return array

    elts = [format_array(a, is_elt=True) for a in array]

    if all(not isinstance(a, list) for a in array):
        if is_elt:
            # 1D
            _, sep, _ = rules.ARRAY_ROW_SYNTAX
            return sep.join(elts)

        # 2D
        if config.show_1d_as_col:
            prefix, sep, suffix = rules.ARRAY_COL_SYNTAX
        else:
            prefix, sep, suffix = rules.ARRAY_ROW_SYNTAX
        return format_delims(prefix, sep.join(elts), suffix)

    # <2D
    prefix, sep, suffix = rules.ARRAY_COL_SYNTAX
    return format_delims(prefix, sep.join(elts), suffix)
