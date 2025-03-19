"""Tabulates the LaTeX representation of objects in a nested list.

The `Table` is a container for the data to be tabulated.

A function is provided to convert `Table` into an HTML representation
with Mathjax support.
"""

import ast
from typing import Any, Optional

from rubberize import exceptions
from rubberize.latexer.node_helpers import get_object
from rubberize.latexer.objects import convert_object
from rubberize.latexer.stmt_latex import StmtLatex
from rubberize.utils import html_tag


_Header = list[Any | tuple[Any, int]] | list[list[Any | tuple[Any, int]]]


class Table:
    """Turning tables. Contains a tabular data.

    Tables can be augmented (concatenated side by side) using the
    `augment()` method or by addition (e.g. `foo + bar`).

    Tables can be stacked (concatenated top to bottom) using the
    `stack()` method or by division (e.g. `foo / bar`).

    When instantiated on its own (i.e., `foo = Table(...)` on a single
    line) or invoked on its own line (i.e., `foo`), the cell magic
    `%%tap` renders a typeset table for report presentation.
    """

    def __init__(
        self,
        data: list[list[Any]],
        *,
        col_headers: Optional[_Header] = None,
        row_headers: Optional[_Header] = None,
    ) -> None:
        """Initialize a `Table` with data and optional headers.

        **Table Structure:**
        - `data` is a list of lists representing table rows. Each inner
            list corresponds to a row of values.
        - `col_headers` (optional) defines column headers.
        - `row_headers` (optional) defines row headers.

        **Header Format:**
        - Both `col_headers` and `row_headers` can be lists of strings,
            or a nested list. If it is a nested list, each inner list
            is treated as a row (for `col_headers`) or a column (for
            `row_headers`).
        - Each element can be a string, which will be the header text,
            or a tuple containing:
            - A string, which will be the header text (`str`).
            - An integer (`int`) specifying how many columns (for
                `col_headers`) or rows (for `row_headers`) the heading
                spans.
        - `list[Any | tuple[Any, int]] | list[list[Any | tuple[Any, int]]]`

        **Example:**
        ```python
        table = Table(
            data=[
                [1, 2, 3],
                [4, 5, 6]
            ],
            col_headers=[
                [("Group", 2), "Value"],
                [("A", 1), ("B", 1), ("C", 1)]
            ],
            row_headers=[
                [("Entries", 2)],
                ["Row 1", "Row 2"]
            ]
        )
        ```
        This creates a 2x3 table with headers. "Group" spans 2 columns,
        "Value" spans 1, and the second row of headers specifies "A", "B",
        and "C". Row headers define "Entries" that span 2 rows, and a
        second column of headers specifies "Row 1" and "Row 2".

        Args:
            data: A list of lists representing table rows.
            col_headers: A list or nested list defining column headers.
            row_headers: A list or nested list defining row headers.
        """

        row_lengths = {len(row) for row in data}
        if len(row_lengths) > 1:
            raise exceptions.RubberizeValueError(
                "All rows in data must have the same number of columns."
            )

        self.data = data
        self.col_headers = self._normalize_headers(col_headers, len(data[0]))
        self.row_headers = self._normalize_headers(row_headers, len(data))

    def __add__(self, other: "Table") -> "Table":
        return self.augment(other)

    def __truediv__(self, other: "Table") -> "Table":
        return self.stack(other)

    def set_col_headers(self, headers: Optional[_Header]) -> None:
        """Set column headers. Pass `None` to remove."""

        self.col_headers = self._normalize_headers(headers, len(self.data[0]))

    def set_row_headers(self, headers: Optional[_Header]) -> None:
        """Set row headers. Pass `None` to remove."""

        self.row_headers = self._normalize_headers(headers, len(self.data))

    def augment(self, other: "Table") -> "Table":
        """Augment two tables (concatenate side by side), enuring `data`
        and `row_headers` match.
        """

        if not isinstance(other, Table):
            raise exceptions.RubberizeTypeError(
                "Can only augment `Table` instances"
            )

        if len(self.data) != len(other.data):
            raise exceptions.RubberizeValueError(
                "Cannot augment tables with different numbers of rows"
            )

        if (
            other.row_headers is not None
            and self.row_headers != other.row_headers
        ):
            raise exceptions.RubberizeValueError(
                "Cannot augment tables with different `row_headers`"
            )

        if (self.col_headers is None) != (other.col_headers is None):
            raise exceptions.RubberizeValueError(
                "Cannot augment tables when only one has `col_headers`"
            )

        if self.col_headers and other.col_headers:
            if len(self.col_headers) != len(other.col_headers):
                raise exceptions.RubberizeValueError(
                    "Cannot augment tables with different numbers of "
                    "`col_headers` rows"
                )

            new_col_headers = []
            for row_self, row_other in zip(self.col_headers, other.col_headers):
                new_col_headers.append(row_self + row_other)
        else:
            new_col_headers = None

        new_data = [
            list(s) + list(o) for s, o in zip(list(self.data), list(other.data))
        ]

        return Table(
            data=new_data,
            col_headers=new_col_headers,
            row_headers=self.row_headers,
        )

    def stack(self, other: "Table") -> "Table":
        """Stack two tables, ensuring `data` and `col_headers` match."""

        if not isinstance(other, Table):
            raise exceptions.RubberizeTypeError(
                "Can only stack `Table` instances"
            )

        if len(self.data[0]) != len(other.data[0]):
            raise exceptions.RubberizeValueError(
                "Cannot stack tables with different numbers of columns"
            )

        if (
            other.col_headers is not None
            and self.col_headers != other.col_headers
        ):
            raise exceptions.RubberizeValueError(
                "Cannot stack tables with different `col_headers`"
            )

        if (self.row_headers is None) != (other.row_headers is None):
            raise exceptions.RubberizeValueError(
                "Cannot stack tables when only one has `row_headers`"
            )

        if self.row_headers and other.row_headers:
            if len(self.row_headers) != len(other.row_headers):
                raise exceptions.RubberizeValueError(
                    "Cannot stack tables with different numbers of "
                    "`row_headers` columns"
                )

            new_row_headers = []
            for col_self, col_other in zip(self.row_headers, other.row_headers):
                new_row_headers.append(col_self + col_other)
        else:
            new_row_headers = None

        new_data = list(self.data) + list(other.data)

        return Table(
            data=new_data,
            col_headers=self.col_headers,
            row_headers=new_row_headers,
        )

    def _normalize_headers(
        self, headers: Optional[_Header], total: int
    ) -> Optional[list[list[tuple[Any, int]]]]:
        """Normalize header input to be list[list[tuple[Any, int]]].
        Return `None` if input is `None`."""

        if headers is None:
            return None

        if not isinstance(headers, list):
            return [[(headers, 1)] + [("", 1) for _ in range(total - 1)]]

        if all(not isinstance(inner, list) for inner in headers):
            headers = [headers]

        normalized: list[list[tuple[Any, int]]] = []

        for inner in headers:
            normalized_inner: list[tuple[Any, int]] = []
            count = 0

            for header in inner:
                if isinstance(header, tuple):
                    value, span = header
                else:
                    value, span = header, 1

                if count + span > total:
                    raise exceptions.RubberizeValueError(
                        f"Header spans exceed total ({total}) "
                        f"for data: {repr(headers)}"
                    )

                normalized_inner.append((value, span))
                count += span

            while count < total:
                normalized_inner.append(("", 1))
                count += 1

            normalized.append(normalized_inner)

        return normalized


# pylint: disable-next=too-many-locals
def convert_table(node: ast.expr, namespace: dict[str, Any]) -> StmtLatex:
    """Convert a `Table` instance to an HTML table with Mathjax support.

    This function is called by `StmtVisitor` when object conversion is
    needed.

    Args:
        node: The node referencing the `Table` instance to convert.
        namespace: A dictionary of identifier and object pairs. It's
            assumed that the namespace contains the `Table` object.

    Returns:
        The rendered HTML table with Mathjax.
    """

    table_obj = get_object(node, namespace)
    assert isinstance(table_obj, Table)

    table_elts = []

    if table_obj.col_headers:
        tr = []
        for row in table_obj.col_headers:
            cells = []
            if table_obj.row_headers:
                cells.extend(
                    html_tag("th", "")
                    for _ in range(len(table_obj.row_headers))
                )

            for cell, span in row:
                colspan = str(span) if span > 1 else None
                cells.append(
                    html_tag(
                        "th",
                        _format_cell(cell),
                        scope="col",
                        colspan=colspan,
                    )
                )

            tr.append(html_tag("tr", cells, force_block=True))
        table_elts.append(html_tag("thead", tr, force_block=True))

    rowspan_tracker = [0] * (
        len(table_obj.row_headers) if table_obj.row_headers else 0
    )

    tr = []
    for row_idx, row in enumerate(table_obj.data):
        cells = []
        if table_obj.row_headers:
            for col_idx, row_header_col in enumerate(table_obj.row_headers):
                if rowspan_tracker[col_idx] > 0:
                    rowspan_tracker[col_idx] -= 1
                else:
                    if row_idx < len(row_header_col):
                        cell, span = row_header_col[row_idx]
                    else:
                        cell, span = row_header_col[-1]

                    rowspan_tracker[col_idx] = span - 1
                    rowspan = str(span) if span > 1 else None
                    cells.append(
                        html_tag(
                            "th",
                            _format_cell(cell),
                            scope="row",
                            rowspan=rowspan,
                        )
                    )

        for cell in row:
            cells.append(html_tag("td", _format_cell(cell)))

        tr.append(html_tag("tr", cells, force_block=True))
    table_elts.append(html_tag("tbody", tr, force_block=True))

    table_html = html_tag(
        "table", table_elts, force_block=True, _class="rz-table"
    )

    return StmtLatex(None, table_html)


def _format_cell(obj: Any) -> str:
    """Format a cell data to appropriate string or LaTeX string."""

    if isinstance(obj, str):
        return obj

    obj_latex = convert_object(obj)

    if obj_latex is not None:
        obj_latex = obj_latex.latex
    else:
        obj_latex = r"\text{###}"

    return rf"\( \displaystyle {obj_latex} \)"
