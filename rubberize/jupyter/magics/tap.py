"""Magics for rendering."""

from __future__ import annotations

from typing import cast, TYPE_CHECKING

from IPython.core.interactiveshell import InteractiveShell
from IPython.core.magic import (
    Magics,
    cell_magic,
    magics_class,
    needs_local_scope,
)
from IPython.core.magic_arguments import (
    argument,
    magic_arguments,
    parse_argstring,
)
from IPython.display import display_html
from IPython.utils.capture import capture_output

import rubberize.vendor.ast_comments as ast_c
from rubberize._exceptions import RubberizeRuntimeError
from rubberize.config import config, parse_modifiers
from rubberize.latexer import latex_from_ast
from rubberize.render import render

if TYPE_CHECKING:
    from rubberize.latexer import StmtLatex


@magics_class
class TapMagics(Magics):
    """Magics for rendering."""

    @magic_arguments()
    @argument(
        "modifiers",
        nargs="*",
        help="Keyword shortcuts or config option assignments for the cell.",
    )
    @argument(
        "-g",
        "--grid",
        action="store_true",
        help="If provided, render the cell in a grid without descriptions.",
    )
    @argument(
        "-h",
        "--html",
        action="store_true",
        help="If provided, print the html output for debugging.",
    )
    @argument(
        "-d",
        "--dead",
        action="store_true",
        help="If provided, the cell is not run; only rendered.",
    )
    @needs_local_scope
    @cell_magic
    def tap(self, line, cell: str, local_ns: dict[str, object] | None) -> None:
        """Run the cell and display as mathematical notation."""

        if not isinstance(self.shell, InteractiveShell):
            raise RubberizeRuntimeError("No InteractiveShell instance found")

        args = parse_argstring(self.tap, line)
        cfg = parse_modifiers(args.modifiers)
        if "hide" in cfg:
            return

        if not args.dead:
            with capture_output():
                run_result = self.shell.run_cell(cell)
            if not run_result.success:
                return
        else:
            local_ns = None

        tree = cast(ast_c.Module, ast_c.parse(cell, mode="exec"))
        with config.override(**cfg):
            latexes = latex_from_ast(tree, local_ns)
        block_starts = _compute_block_starts(cell)
        blocks = _group_blocks(latexes, tree.body, block_starts)

        for b in blocks:
            html = render(b, local_ns, grid=args.grid)

            if args.html:
                print(html, "\n")
                continue

            display_html(html, raw=True)

    @magic_arguments()
    @argument(
        "-d",
        "--dead",
        action="store_true",
        help="If provided, the cell is not run; only dumped as AST.",
    )
    @argument(
        "-n",
        "--no-annotate-fields",
        dest="annotate_fields",
        action="store_false",
        help="If provided, do not include field names and values in output.",
    )
    @argument(
        "-a",
        "--include-attributes",
        action="store_true",
        help=(
            "If provided, include attributes such as line numbers and "
            "column offsets."
        ),
    )
    @argument(
        "-i",
        "--indent",
        type=lambda v: None if v == "none" else int(v),
        metavar="INT or 'none'",
        default=4,
        help=(
            "Pretty-print indentation level (default: %(default)s) or 'none' "
            "for compact output."
        ),
    )
    @cell_magic
    def ast(self, line: str, cell: str) -> None:
        """Run the cell and dump its AST."""

        if not isinstance(self.shell, InteractiveShell):
            raise RubberizeRuntimeError("No InteractiveShell instance found")

        args = parse_argstring(self.ast, line)
        if not args.dead:
            with capture_output():
                run_result = self.shell.run_cell(cell)
            if not run_result.success:
                return

        tree = cast(ast_c.Module, ast_c.parse(cell, mode="exec"))
        block_starts = _compute_block_starts(cell)

        blocks: list[list[ast_c.stmt]] = []
        current: list[ast_c.stmt] = []

        for stmt in tree.body:
            if stmt.lineno - 1 in block_starts and current:
                blocks.append(current)
                current = []

            current.append(stmt)

        if current:
            blocks.append(current)

        for b in blocks:
            sub_tree = ast_c.Module(body=b, type_ignores=[])

            dump = ast_c.dump(
                sub_tree,
                annotate_fields=args.annotate_fields,
                include_attributes=args.include_attributes,
                indent=args.indent,
            )

            print(dump)


def _compute_block_starts(cell: str) -> set[int]:
    lines = cell.splitlines()

    starts: set[int] = set()
    saw_code = False
    saw_blank = False

    for i, line in enumerate(lines):
        # ignore leading blank lines
        if not saw_code and line.strip() == "":
            continue

        # ignore magics or commented magics
        if line.lstrip().startswith(("%", "# %")):
            continue

        if line.strip() == "":
            saw_blank = True
            continue

        if (
            saw_code
            and saw_blank
            and line == line.lstrip(" ")
            and not line.lstrip().startswith(
                ("elif ", "else", "except", "finally")
            )
        ):
            starts.add(i)

        saw_code = True
        saw_blank = False

    return starts


def _group_blocks(
    latexes: list[StmtLatex], stmts: list[ast_c.stmt], block_starts: set[int]
) -> list[list[StmtLatex]]:
    blocks: list[list[StmtLatex]] = []
    current: list[StmtLatex] = []

    for stmt, latex in zip(stmts, latexes):
        if stmt.lineno - 1 in block_starts and current:
            blocks.append(current)
            current = []

        current.append(latex)

    if current:
        blocks.append(current)

    return blocks
