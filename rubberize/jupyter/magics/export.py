"""Magics for exporting to pdf."""

from IPython.core.magic import Magics, line_magic, magics_class
from IPython.core.magic_arguments import (
    argument,
    magic_arguments,
    parse_argstring,
)

from rubberize.jupyter.export_notebook import configure_logger, export_notebook


@magics_class
class ExportMagics(Magics):
    """Magics for rendering."""

    @magic_arguments()
    @argument(
        "input_path", help="The path to the notebook or directory to convert."
    )
    @argument(
        "output_path",
        nargs="?",
        help=(
            "Optional output path. If not provided, uses the input path but "
            "with file extension changed to .pdf, or if input path is a "
            "directory, the output will be saved in a new sibling directory "
            "named <directory>_pdf."
        ),
    )
    @argument(
        "--to",
        choices=["pdf", "html"],
        default="pdf",
        help="The format to export to (default: %(default)s).",
    )
    @argument(
        "--show-input",
        action="store_true",
        help="If given, include input cells in the output.",
    )
    @argument(
        "--render-timeout",
        type=int,
        metavar="INT",
        default=100,
        help=(
            "Time to wait for the page to render before PDF conversion, in "
            "milliseconds (default: %(default)s). Increase this value if the "
            "notebook has a lot of complex JavaScript output that needs more "
            "time to load."
        ),
    )
    @argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    @line_magic
    def export(self, line: str) -> None:
        """Export a notebook or a directory of notebooks to a specified
        format. Note that batch export only works for exports to PDF."""

        args = parse_argstring(self.export, line)

        configure_logger(args.verbose)

        export_notebook(
            args.input_path,
            args.output_path,
            fmt=args.to,
            show_input=args.show_input,
            render_timeout=args.render_timeout,
        )
