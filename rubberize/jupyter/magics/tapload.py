"""Magics for rendering."""

import itertools
import logging
import warnings
import shlex

from IPython.core.error import StdinNotImplementedError
from IPython.core.interactiveshell import InteractiveShell
from IPython.core.magic import Magics, line_magic, magics_class
from IPython.core.magic_arguments import (
    argument,
    magic_arguments,
    parse_argstring,
)
from IPython.core.magics.code import (
    extract_symbols,
    extract_code_ranges,
    strip_initial_indent,
)
from IPython.utils.text import get_text_list

from rubberize._exceptions import RubberizeRuntimeError


@magics_class
class TapLoadMagics(Magics):
    """Magics for rendering."""

    @magic_arguments()
    @argument(
        "-r",
        help="Lines/ranges to load, e.g. 5-10 or 10-20,30,40:",
    )
    @argument(
        "-s",
        help="Comma-separated functions/classes to extract from Python source",
    )
    @argument(
        "-y",
        action="store_true",
        help="Don't ask confirmation for big sources (>200 000 characters)",
    )
    @argument(
        "-n",
        action="store_true",
        help="Search in user namespace for objects/modules",
    )
    @argument(
        "source",
        nargs="*",
        metavar="SOURCE",
        help=(
            "Filename, URL, history range, macro, or name in namespace. "
            "You may end the source with `--` to pass `tap` cell magic args."
        ),
    )
    @line_magic
    def tapload(self, line: str) -> None:
        """Load code like %load, but rewrite the the cell to start with
        %%tap.
        """

        if not isinstance(self.shell, InteractiveShell):
            raise RubberizeRuntimeError("No InteractiveShell instance found")

        load_part, tap_args = _split_double_dash(line)
        args = parse_argstring(self.tapload, load_part)
        arg_s = " ".join(args.source).strip()  # "" => history, same w/ %load

        contents = self.shell.find_user_code(arg_s, search_ns=args.n)

        if args.s:
            try:
                blocks, not_found = extract_symbols(contents, args.s)
            except SyntaxError:
                logging.error("Unable to parse the input as valid Python code")
                return

            if len(not_found) == 1:
                warnings.warn(f"The symbol {not_found[0]} was not found")
            elif len(not_found) > 1:
                warnings.warn(
                    "The symbols "
                    f"{get_text_list(not_found, wrap_item_with='`')} "
                    "were not found"
                )

            contents = "\n".join(blocks)

        if args.r:
            ranges = args.r.replace(",", " ")
            lines = contents.splitlines()
            slices = extract_code_ranges(ranges)
            contents = [lines[slice(*slc)] for slc in slices]
            contents = "\n".join(
                strip_initial_indent(itertools.chain.from_iterable(contents))
            )

        l = len(contents)
        if l > 200_000 and not args.y:
            try:
                ans = self.shell.ask_yes_no(
                    "The text you're trying to load seems pretty big "
                    f"({l} characters). Continue (y/[N]) ?",
                    default="n",
                )
            except StdinNotImplementedError:
                ans = True

            if ans is False:
                print("Operation cancelled.")
                return

        contents = (
            f"%%tap {tap_args}\n" f"# %tapload {line}\n" f"{contents.rstrip()}"
        )
        self.shell.set_next_input(contents, replace=True)

    @magic_arguments()
    @argument(
        "--next",
        action="store_true",
        help="Insert the next cell in the queue. Alias is `%%tln`.",
    )
    @argument(
        "source",
        nargs="*",  # required unless --next is used
        metavar="SOURCE",
        help=(
            "Filename or URL of a percent format snippet."
            "You may end the source with `--` to pass global tap options."
        ),
    )
    @line_magic
    def taploads(self, line: str) -> None:
        """Load a multi-cell snippet in percent format and rewrite each
        cell to start with %%tap.

        Splits the snippet on lines that begin with `# %%`. These cell
        types are recognized:
        - `# %%` -> `%%tap`
        - `# %% tap [ARGS]` -> `%%tap [ARGS]`
        - `# %% py` or `# %% code` => code cell without `%%tap`
        - `# %% [markdown]` => `%%markdown`
        """

        if not isinstance(self.shell, InteractiveShell):
            raise RubberizeRuntimeError("No InteractiveShell instance found")

        load_part, tap_args = _split_double_dash(line)
        args = parse_argstring(self.taploads, load_part)

        if args.next and args.source:
            logging.error("Supply only SOURCE or --next, not both")
            return

        if args.next:
            queue = _get_taploads_queue(self.shell)
            if not queue:
                logging.error("Nothing to continue")
                return

            cur_chunk = queue.pop(0)
            _set_taploads_queue(self.shell, queue)

            remaining = len(queue)
            if remaining:
                print(
                    f"Inserted next cell ({remaining} remaining). "
                    "Run `%taploads --next` or `%tln` on the next cell "
                    "to continue."
                )
            else:
                print("Inserted the final cell. Done!")

            contents = _render_taploads_chunk(
                cur_chunk, "%taploads --next", tap_args
            )
            self.shell.set_next_input(contents, replace=True)
            return

        if not args.source:
            logging.error("SOURCE is required (or use --next)")
            return

        src = self.shell.find_user_code(" ".join(args.source))
        first, *rest = _split_percent_fmt(src)

        if rest:
            _set_taploads_queue(self.shell, rest)
            print(
                f"Inserted the first cell ({len(rest)} remaining). "
                "Run `%taploads --next` or `%tln` on the next cell "
                "to continue."
            )
        else:
            print("Inserted the only cell. Done!")

        contents = _render_taploads_chunk(first, f"%taploads {line}", tap_args)
        self.shell.set_next_input(contents, replace=True)

    @line_magic
    def tln(self, _) -> None:
        """Alias of `%taploads --next` to quickly insert the next queued
        cell.
        """

        return self.taploads("--next")


def _split_double_dash(line: str) -> tuple[str, str]:
    parts = shlex.split(line, posix=True)
    if "--" in parts:
        k = parts.index("--")
        return " ".join(parts[:k]), " ".join(parts[k + 1 :])
    return line, ""


def _get_taploads_queue(shell: InteractiveShell) -> list[tuple[str, str]]:
    return list(shell.user_ns.get("_taploads_queue") or [])


def _set_taploads_queue(
    shell: InteractiveShell, cells: list[tuple[str, str]]
) -> None:
    shell.user_ns["_taploads_queue"] = list(cells)


def _render_taploads_chunk(
    chunk: tuple[str, str], provenance: str, global_args: str
) -> str:
    marker, body = chunk

    if "[markdown]" in marker:
        return f"%%markdown\n<!-- {provenance} -->\n{body.rstrip()}"

    if marker.startswith(("py", "code")):
        return f"# {provenance}\n{body.rstrip()}"

    args = marker[3:].strip() if marker.startswith("tap") else global_args
    return f"%%tap {args}\n# {provenance}\n{body.rstrip()}"


def _split_percent_fmt(src: str) -> list[tuple[str, str]]:
    lines = src.splitlines()
    chunks: list[tuple[str, list[str]]] = []
    cur_marker = ""
    cur_body: list[str] = []
    saw_percent = False

    for line in lines:
        # ignore leading blank lines
        if not cur_body and line.strip() == "":
            continue

        stripped = line.lower().lstrip()
        if stripped.startswith("# %%"):
            # commit previous chunk
            if cur_body or saw_percent:
                chunks.append((cur_marker, cur_body))
                cur_body = []

            # parse marker: remove `# %%` and trim the rest
            cur_marker = stripped.removeprefix("# %%").strip()
            saw_percent = True
        else:
            cur_body.append(line)
    chunks.append((cur_marker, cur_body))

    return [(m, "\n".join(b).rstrip()) for m, b in chunks]
