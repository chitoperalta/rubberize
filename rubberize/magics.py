"""The class for all magic commands that the library adds to the
Interactive Shell. Called by `load_ipython_extension()`
"""

from typing import Any, Optional

from IPython.core.display import display_html
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
from IPython.utils.capture import capture_output

import rubberize.vendor.ast_comments as ast_c

from rubberize.config import config
from rubberize.latexer.latexer import latexer
from rubberize.render.render import render
from rubberize.config import parse_modifiers


@magics_class
class RubberizeMagics(Magics):
    """Contains IPython magics to be loaded."""

    @magic_arguments()
    @argument(
        "--dead",
        action="store_true",
        help="dead cell -- the cell is not run; only rendered.",
    )
    @cell_magic
    def ast(self, line: str, cell: str) -> None:
        """Magic to run the cell and dump it as AST for debugging."""

        assert isinstance(self.shell, InteractiveShell)

        args = parse_argstring(self.tap, line)
        if not args.dead:
            with capture_output():
                run_result = self.shell.run_cell(cell)
            if not run_result.success:
                return None

        # Ignore line magics
        cleaned_cell = "\n".join(
            l for l in cell.split("\n") if not l.startswith("%")
        )

        return print(ast_c.dump(ast_c.parse(cleaned_cell), indent=4))

    @magic_arguments()
    @argument(
        "modifiers",
        nargs="*",
        help="keyword shortcuts or config option assignments for the cell",
    )
    @argument(
        "--grid",
        "-g",
        action="store_true",
        help="render the cell in a grid and without descriptions",
    )
    @argument(
        "--html",
        "-h",
        action="store_true",
        help="print the html output for debugging",
    )
    @argument(
        "--dead",
        action="store_true",
        help="dead cell -- the cell is not run; only rendered.",
    )
    @needs_local_scope
    @cell_magic
    def tap(
        self, line: str, cell: str, local_ns: Optional[dict[str, Any]]
    ) -> None:
        """Magic to run the cell and render it as mathematical notation.
        It supports line args to customize the output.
        """

        assert isinstance(self.shell, InteractiveShell)

        args = parse_argstring(self.tap, line)
        override = parse_modifiers(args.modifiers)
        if "hide" in override:
            return None

        if not args.dead:
            with capture_output():
                run_result = self.shell.run_cell(cell)
            if not run_result.success:
                return None
        else:
            local_ns = None

        # Ignore line magics
        cleaned_cell = "\n".join(
            l for l in cell.split("\n") if not l.startswith("%")
        )

        with config.override(**override):
            latex_list = latexer(cleaned_cell, local_ns)
            cell_html = render(latex_list, local_ns, grid=args.grid)

        if args.html:
            return print(cell_html, "\n")
        return display_html(cell_html, raw=True)
