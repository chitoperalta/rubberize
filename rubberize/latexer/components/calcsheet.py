"""Tracks value comparisons with configurable ratios.

Provides functionality to add comparisons, remove specific entries, and
conclude if all comparisons are valid.

Functions to convert `CalcSheet` and its method calls into Markdown are
provided.
"""

import ast
from dataclasses import dataclass, field, asdict, KW_ONLY
from typing import Any, Optional

from titlecase import titlecase

from rubberize.config import config
from rubberize.latexer.components.table import Table
from rubberize.latexer.expr_modes import all_modes
from rubberize.latexer.formatters import format_equation
from rubberize.latexer.node_helpers import get_object
from rubberize.latexer.stmt_latex import StmtLatex


class CalcSheet:
    """Contains the metadata for a calculation sheet, and keeps track
    of comparisons between two values.

    When instantiated on its own (i.e., `foo = CalcSheet(...)` on a
    single line) or invoked on its own line (i.e., `foo`), the cell
    magic `%%tap` renders a typeset title heading for report
    presentation.
    """

    def __init__(
        self, *args: Any, meta: Optional["_Meta"] = None, **kwargs: Any
    ) -> None:
        self.checks: dict[str, _Check] = {}
        if meta is not None:
            self.meta = meta
        elif len(args) == 1 and isinstance(args[0], _Meta):
            self.meta = args[0]
        else:
            self.meta = _Meta(*args, **kwargs)

    def __bool__(self) -> bool:
        return all(bool(check) for check in self.checks.values())

    def check(
        self, label: str, left: Any, right: Any, /, max_ratio: float = 1.0
    ) -> bool:
        """Check if the ratio of two values is equal to or less than
        the maximum allowed ratio.

        When called as an expression statement (on its own on a single
        line), the cell magic `%%tap` renders a typeset check statement
        for report presentation.

        Args:
            label: A unique identifier for the check.
            left: The left-hand value in the comparison.
            right: The right-hand value in the comparison.
            max_ratio: The maximum allowed ratio for the check to pass.

        Returns:
            Whether the check passes (`True`) or fails (`False`)
        """

        comparison = _Check(label, left, right, max_ratio)
        self.checks[label] = comparison
        return bool(comparison)

    def conclude(self, *, each_check: bool = False) -> bool | list[bool]:
        """Check if all checks are equal to or less than the maximum
        allowed ratio.

        When called as an expression statement (on its own on a single
        line), the cell magic `%%tap` renders a typeset conclusion
        statement for report presentation.

        Args:
            each_check: Whether to report the results of each statement
                or just the maximum utilization.

        Returns:
            Whether all checks pass (`True`) or (`Fails`). If
            `each_check` is `True`, returns a list of booleans, the elts
            of which represent the each check.
        """

        if each_check:
            return [bool(check) for check in self.checks.values()]
        return bool(self)

    def remove(self, *labels: str) -> None:
        """Remove check entries by labels.

        Args:
            *label: The label of the check to remove from the instance.
        """

        for label in labels:
            self.checks.pop(label, None)

    def clear(self) -> None:
        """Clear all check entries."""

        self.checks.clear()

    def table(self) -> Table:
        """Return a `Table` object summarizing the checks contained by
        the instance.

        When called as an expression statement (on its own on a single
        line), the cell magic `%%tap` renders the `Table`.
        """

        col_headers = ["Required", "Capacity", "Utilization", "Result"]

        table_data = []
        row_headers = []
        for check in self.checks.values():
            row = [
                check.left,
                check.right,
                f"{check.ratio:.{config.num_format_prec}%}",
                "PASS" if bool(check) else "FAIL",
            ]
            row_headers.append(titlecase(getattr(check, "label")))
            table_data.append(row)

        return Table(
            table_data, col_headers=col_headers, row_headers=row_headers
        )


@dataclass
class _Meta:  # pylint: disable=too-many-instance-attributes
    """Contains metadata for the calculation sheet."""

    section: str
    name: str

    _: KW_ONLY

    group: Optional[str] = None
    notes: Optional[str] = None

    project: Optional[str] = None
    system: Optional[str] = None

    calc_type: Optional[str] = None
    material: Optional[str] = None
    references: list[str] = field(default_factory=list)

    extra: dict[str, Any] = field(default_factory=dict)
    title: str = field(init=False)

    def __post_init__(self) -> None:
        parts = [
            f"{self.calc_type} of" if self.calc_type else "Analysis of",
            self.group,
            self.material,
            self.name,
            f"({self.notes})" if self.notes else None,
        ]
        self.title = titlecase(" ".join(p for p in parts if p))

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to a dictionary."""

        return asdict(self)


@dataclass
class _Check:
    """Contains a comparison between two values with a specified ratio
    constraint.

    Attributes:
        label: A unique identifier for the check.
        left: The left-hand value in the comparison.
        right: The right-hand value in the comparison.
        max_ratio: The maximum allowed ratio for the check to pass.
        ratio: The ratio of left to right (left / right).
        adj_ratio: The adjusted ratio (ratio / max_ratio).
    """

    label: str
    left: Any
    right: Any
    max_ratio: float = 1.0
    ratio: float = field(init=False)
    adj_ratio: float = field(init=False)

    def __post_init__(self) -> None:
        self.ratio = float(self.left / self.right)
        self.adj_ratio = self.ratio / self.max_ratio

    def __bool__(self) -> bool:
        return self.adj_ratio <= 1.0


def convert_calc_sheet(node: ast.expr, namespace: dict[str, Any]) -> StmtLatex:
    """Convert a `CalcSheet` instance to a title heading for report
    presentation.

    This function is called by `StmtVisitor` when object conversion is
    needed.

    Args:
        node: The node referencing the `CalcSheet` instance to convert.
        namespace: A dictionary of identifier and object pairs. It's
            assumed that the namespace contains the `CalcSheet` object.

    Returns:
        The rendered title heading, in custom Markdown format.
    """

    calc_sheet = get_object(node, namespace)
    assert isinstance(calc_sheet, CalcSheet)

    subtitle_parts = [calc_sheet.meta.system, calc_sheet.meta.project]
    header_lines = [
        f"> [Section {calc_sheet.meta.section}]",
        f"> # {calc_sheet.meta.title}",
        f"> {' ⋅ '.join(p for p in subtitle_parts if p)}",
        ">",
        "\n".join(f"> - {r}" for r in calc_sheet.meta.references),
    ]
    return StmtLatex(None, "\n".join(header_lines))


def convert_conclude_method(
    node: ast.expr, namespace: dict[str, Any]
) -> StmtLatex:
    """Convert a `conclude()` method call on a `CalcSheet` instance to a
    typeset conclusion statement.

    This function is called by `StmtVisitor` when object conversion is
    needed.

    Args:
        node: The node referencing the CalcSheet instance.
        namespace: A dictionary of identifier and object pairs. It's
            assumed that the namespace contains the CalcSheet instance.

    Returns:
        The rendered conclusion statement, in custom Markdown format.
    """

    assert isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)

    calc_sheet = get_object(node.func.value, namespace)
    assert isinstance(calc_sheet, CalcSheet)

    is_each = get_object(node.keywords[0].value, {}) if node.keywords else False
    assert isinstance(is_each, bool)

    conclusion = "> [!PASS]\n" if calc_sheet.conclude() else "> [!FAIL]\n"
    if is_each and len(calc_sheet.checks) > 1:
        for check in calc_sheet.checks.values():
            conclusion += "> " if check else "> FAIL: "
            conclusion += (
                f"Utilization of {check.label} is {_format_util(check)}.  \n"
            )
    if len(calc_sheet.checks) > 1:
        max_check = max(calc_sheet.checks.values(), key=lambda c: c.adj_ratio)
        conclusion += (
            f"> Maximum utilization is {_format_util(max_check)}, "
            f"{max_check.label}.  \n"
        )
    if calc_sheet.conclude():
        conclusion += f"> Thus, the {calc_sheet.meta.name} is adequate."
    else:
        conclusion += f"> Thus, the {calc_sheet.meta.name} is inadequate."
    return StmtLatex(None, conclusion)


def convert_check_method(
    node: ast.expr, namespace: dict[str, Any]
) -> StmtLatex:
    """Convert a `check()` method call on a `CalcSheet` instance to a
    typeset check statement.

    This function is called by `StmtVisitor` when object conversion is
    needed.

    Args:
        node: The node referencing the CalcSheet instance.
        namespace: A dictionary of identifier and object pairs. It's
            assumed that the namespace contains the CalcSheet instance.

    Returns:
        The rendered check statement, in custom Markdown format.
    """

    assert isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)

    calc_sheet = get_object(node.func.value, namespace)
    assert isinstance(calc_sheet, CalcSheet)

    label = get_object(node.args[0], namespace)
    assert isinstance(label, str)

    check = calc_sheet.checks[label]
    comp = "<" if check.ratio < 1.0 else "=" if check.ratio == 1.0 else ">"
    left_latex = format_equation(all_modes(node.args[1], namespace))
    right_latex = format_equation(all_modes(node.args[2], namespace))

    checked_latex = left_latex + r" \quad " + comp + r" \quad " + right_latex

    conclusion = "> [!PASS]\n" if check else "> [!FAIL]\n"
    conclusion += f"> Utilization is {_format_util(check)}.  \n"

    if check:
        conclusion += f"> Thus, the {label} is adequate."
    else:
        conclusion += f"> Thus, the {label} is not adequate."

    return StmtLatex(
        None,
        body=[
            StmtLatex(None, "Comparing,", [StmtLatex(checked_latex)]),
            StmtLatex(None, conclusion),
        ],
    )


def _format_util(check: "_Check") -> str:
    """Format the utilization ratio for a given `_Check` instance."""

    ratio_string = f"{check.ratio:.{config.num_format_prec}%}"
    if check.max_ratio != 1.0:
        ratio_string += (
            f" (or {check.adj_ratio:.{config.num_format_prec}%} relative to "
            f"{check.max_ratio:.{config.num_format_prec}%} utilization limit)"
        )
    return ratio_string
