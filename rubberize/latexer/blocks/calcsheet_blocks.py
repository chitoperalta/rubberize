"""Block converters to support rubberize.CalcSheet rendering."""

from __future__ import annotations

import ast

from rubberize.config import config
from rubberize.calcsheet import CalcSheet, _Check
from rubberize.latexer import displays, formatters, helpers
from rubberize.latexer.stmt_latex import StmtLatex
from rubberize.latexer.blocks.convert_blocks import register_block_converter


def _calcsheet(node: ast.expr, ns: dict[str, object]) -> StmtLatex | None:
    """Convert a CalcSheet object to a title heading."""

    obj = helpers.get_object(node, ns)

    if not isinstance(obj, CalcSheet):
        return None

    subtitle_parts = [obj.meta.system, obj.meta.project]
    subtitle = " ⋅ ".join(p for p in subtitle_parts if p)

    references = "\n".join(f"> - {r}" for r in obj.meta.references)

    heading_lines = [
        f"> [Section {obj.meta.section}]",
        f"> # {obj.meta.title}",
        f"> {subtitle}",
        ">",
        references,
    ]
    heading = "\n".join(heading_lines)

    return StmtLatex(None, heading)


def _calcsheet_check(node: ast.expr, ns: dict[str, object]) -> StmtLatex | None:
    """Convert a CalcSheet.check() method call."""

    if not isinstance(node, ast.Call):
        return None

    if not isinstance(node.func, ast.Attribute):
        return None

    obj = helpers.get_object(node.func.value, ns)

    if not isinstance(obj, CalcSheet):
        return None

    label_node = helpers.get_arg_node(node, 0, "label", required=True)
    left_node = helpers.get_arg_node(node, 1, "left", required=True)
    right_node = helpers.get_arg_node(node, 2, "right", required=True)

    label = helpers.get_object(label_node, ns)
    if not isinstance(label, str):
        return None

    check = obj.checks[label]

    op = "<" if check.ratio < 1.0 else "=" if check.ratio == 1.0 else ">"
    left = formatters.format_equation(displays.all_modes(left_node, ns))
    right = formatters.format_equation(displays.all_modes(right_node, ns))

    check_latex = left + r" \quad " + op + r" \quad " + right

    statement = "> [!PASS]\n" if check else "> [!FAIL]\n"
    statement += f"> Utilization is {_fmt_ratio(check)}.  \n"

    if check:
        statement += f"> Thus, the {label} is adequate."
    else:
        statement += f"> Thus, the {label} is inadequate."

    return StmtLatex(
        None,
        body=[
            StmtLatex(None, "Comparing,", [StmtLatex(check_latex)]),
            StmtLatex(None, statement),
        ],
    )


def _calcsheet_conclude(
    node: ast.expr, ns: dict[str, object]
) -> StmtLatex | None:
    """Convert a CalcSheet.conclude() method call."""

    if not isinstance(node, ast.Call):
        return None

    if not isinstance(node.func, ast.Attribute):
        return None

    obj = helpers.get_object(node.func.value, ns)

    if not isinstance(obj, CalcSheet):
        return None

    each_check_node = helpers.get_arg_node(node, None, "each_check")
    if each_check_node is None:
        each_check_node = ast.Constant(False)

    each_check = helpers.get_object(each_check_node, ns)

    statement = "> [!PASS]\n" if obj.conclude() else "> [!FAIL]\n"

    if each_check and len(obj.checks) > 1:
        for label, check in obj.checks.items():
            statement += "> " if check else "> FAIL: "
            statement += f"Utilization of {label} is {_fmt_ratio(check)}.  \n"

    if len(obj.checks) > 1:
        max_check = max(obj.checks.values(), key=lambda c: c.adj_ratio)
        statement += f"> Maximum utilization is {_fmt_ratio(max_check)}, "
        statement += f"{max_check.label}. \n"

    if obj.conclude():
        statement += f"> Thus, the {obj.meta.name} is adequate."
    else:
        statement += f"> Thus, the {obj.meta.name} is inadequate."

    return StmtLatex(None, statement)


def _fmt_ratio(check: _Check) -> str:
    prec = config.float_prec

    ratio = f"{check.ratio:.{prec}%}"
    if check.max_ratio != 1.0:
        ratio += f" (or {check.adj_ratio:.{prec}%} relative to "
        ratio += f"{check.max_ratio:.{prec}%} utilization limit)"

    return ratio


register_block_converter(CalcSheet, _calcsheet)
register_block_converter(CalcSheet.check, _calcsheet_check)
register_block_converter(CalcSheet.conclude, _calcsheet_conclude)
