"""Tracks value comparisons in a notebook used as an engineering
calculation sheet.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, KW_ONLY
from typing import TYPE_CHECKING

from titlecase import titlecase

if TYPE_CHECKING:
    from typing import Any


class CalcSheet:
    """Contains metadata for a notebook used as an engineering
    calculation sheet, and keeps track of comparisons between values.
    """

    def __init__(
        self, *args: Any, meta: _Meta | None = None, **kwargs: Any
    ) -> None:
        if meta is not None:
            self.meta = meta
        elif len(args) == 1 and isinstance(args[0], _Meta):
            self.meta = args[0]
        else:
            self.meta = _Meta(*args, **kwargs)

        self.checks: dict[str, _Check] = {}

    def __bool__(self) -> bool:
        return all(bool(c) for c in self.checks.values())

    def check(
        self, label: str, left: Any, right: Any, *, max_ratio: float = 1.0
    ) -> bool:
        """Check if the ratio of two values is equal to or less than 1
        or a maximum allowed ratio. Store the comparison with a label.

        Args:
            label: A unique identifier for the check.
            left: The left-hand value in the comparison.
            right: The right-hand value in the comparison.
            max_ratio: The maximum allowed ratio for the check to pass.
        """

        comparison = _Check(label, left, right, max_ratio)
        self.checks[label] = comparison

        return bool(comparison)

    def conclude(self, *, each_check: bool = False) -> bool | list[bool]:
        """Check if all checks are equal to or less than their maximum
        allowed ratios.

        Args:
            each_check: If true, return a list of bool for each check.
        """

        if each_check:
            return [bool(c) for c in self.checks.values()]

        return bool(self)

    def forget(self, *labels: str) -> None:
        """Remove check entries by label(s).

        Args:
            *labels: The label of the check to remove.
        """


@dataclass
# pylint: disable-next=too-many-instance-attributes
class _Meta:
    """Contains the metadata for an engineering calculation sheet.

    Attributes:
        section: Section label.
        name: Name of the component analyzed in the calculation sheet.
        project: Project name.
        system: System of which the calculation sheet is part of.
        calc_type: Type of calculation being carried out.
        group: Group of which the component is part of.
        material: Material of the component.
        notes: Additional notes to be included in the title.
        references: Reference standards used on the calculation.
        extra: Holder for any extra metadata.
        title: Title of the calculation sheet. Concatenated from the
            above attributes after initialization, with the formula
            `[calc_type, "analysis"] + "of" + group + material + name +
            [(notes)]`, separated by spaces and in titlecase. If any of
            the attributes are None, they are silently omitted from the
            title.
    """

    section: str
    name: str

    _: KW_ONLY

    project: str | None = None
    system: str | None = None

    calc_type: str | None = None
    group: str | None = None
    material: str | None = None
    notes: str | None = None
    references: list[str] = field(default_factory=list)

    extra: dict[str, Any] = field(default_factory=dict)
    title: str = field(init=False)

    def __post_init__(self) -> None:
        parts = [
            f"{self.calc_type} of" if self.calc_type else "analysis of",
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
    """Stores the comparison between two values with a specified ratio
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
