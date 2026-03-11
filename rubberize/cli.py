"""The command line interface."""

import argparse

from rubberize.jupyter.export_notebook import configure_logger, export_notebook


def main() -> None:
    """The main CLI."""

    parser = argparse.ArgumentParser(prog="rubberize")

    sub = parser.add_subparsers(dest="command", required=True)

    register_export_cli(sub)

    args = parser.parse_args()
    args.func(args)


def register_export_cli(subparsers: argparse._SubParsersAction) -> None:
    """Register the export command cli to subparsers.

    Examples:
        rubberize export notebook.ipynb
        rubberize export notebook.ipynb output.pdf
        rubberize export notebook.ipynb --to html
        rubberize export notebook.ipynb --show-input
    """

    export: argparse.ArgumentParser = subparsers.add_parser(
        "export",
        help=(
            "Export a notebook or a directory of notebooks to a specified "
            "format. Note that batch export only works for exports to PDF."
        ),
    )
    export.add_argument(
        "input_path", help="The path to the notebook or directory to convert."
    )
    export.add_argument(
        "output_path",
        nargs="?",
        help=(
            "Optional output path. If not provided, uses the input path but "
            "with file extension changed to .pdf, or if input path is a "
            "directory, the output will be saved in a new sibling directory "
            "named <directory>_pdf."
        ),
    )
    export.add_argument(
        "--to",
        choices=["pdf", "html"],
        default="pdf",
        help="The format to export to (default: %(default)s).",
    )
    export.add_argument(
        "--show-input",
        action="store_true",
        help="If given, include input cells in the output.",
    )
    export.add_argument(
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
    export.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )

    export.set_defaults(func=_cmd_export)


def _cmd_export(args: argparse.Namespace) -> None:
    configure_logger(args.verbose)
    export_notebook(
        args.input_path,
        args.output_path,
        fmt=args.to,
        show_input=args.show_input,
        render_timeout=args.render_timeout,
    )


if __name__ == "__main__":
    main()
