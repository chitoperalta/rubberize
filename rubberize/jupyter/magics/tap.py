"""Magics for rendering."""

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
from rubberize.latexer import latexer
from rubberize.render import render


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

        blocks = _split_blocks(cell)

        for b in blocks:
            with config.override(**cfg):
                latex = latexer(b, local_ns)
                html = render(latex, local_ns, grid=args.grid)

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
    @argument(
        "-e",
        "--show-empty",
        action="store_true",
        help="If included, show empty fields in output.",
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

        blocks = _split_blocks(cell)

        for b in blocks:
            tree = ast_c.parse(b)
            dump = ast_c.dump(
                tree,
                annotate_fields=args.annotate_fields,
                include_attributes=args.include_attributes,
                indent=args.indent,
                show_empty=args.show_empty,
            )
            print(dump)


def _split_blocks(cell: str) -> list[str]:
    lines = cell.splitlines()

    blocks: list[list[str]] = []
    current: list[str] = []
    saw_blank = False

    for line in lines:
        # ignore leading blank lines
        if not current and line.strip() == "":
            continue

        # ignore magics or commented magics
        if line.lstrip().startswith(("%", "# %")):
            continue

        if line.strip() == "":
            current.append(line)
            saw_blank = True
            continue

        if (
            current
            and saw_blank
            and line == line.lstrip(" ")
            and not line.lstrip().startswith(
                ("elif ", "else", "except", "finally")
            )
        ):
            blocks.append(current)
            current = []

        current.append(line)
        saw_blank = False

    if current:
        blocks.append(current)

    return ["\n".join(b) for b in blocks]
