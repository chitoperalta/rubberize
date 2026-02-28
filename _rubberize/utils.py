"""Utility functions used throughout the library."""

import re
import textwrap
from typing import Any, Callable, Literal, Optional


_FlagsType = re.RegexFlag | Literal[0]


def find_and_sub(
    pattern: str | re.Pattern[str],
    repl: str | Callable[[re.Match[str]], str],
    string: str,
    group: int = 1,
    flags: _FlagsType = 0,
) -> tuple[list[str | Any], str]:
    """Find occurrences of a pattern in a string, extract matches from
    the specified capturing group, and perform a substitution.

    Args:
        pattern: The regex pattern to search for.
        repl: The replacement string or a function that takes a match
            object and returns a replacement string.
        string: The input string to search within.
        group: The capturing group whose matches should be extracted.
        flags: Regex flags modifying the search behavior.

    Returns:
        A tuple containing a list of matches from the capturing group,
        and the string after performing the substitution.
    """
    matches = [m.group(group) for m in re.finditer(pattern, string, flags)]
    return matches, re.sub(pattern, repl, string, flags)


def wrap_delims(
    text: str,
    delims: tuple[str, str],
    *,
    force_block: bool = False,
    spaced_line: bool = False,
    indent: int = 4,
) -> str:
    """Wrap text with a pair of delimiters, optionally formatting it as
    a block.

    Default behavior, for delims `"{{...}}"`:
    - `""` -> `"{{}}"`
    - `"text 1\\ntext 2"` -> `"{{\\n    text 1\\n    text 2\\n}}"`
    - `"text"` -> `"{{text}}"`

    Args:
        text: The text to be wrapped.
        delims: A tuple specifying the opening and closing delimiters.
        force_block: If True, forces block formatting even for single
            line input.
        spaced_line: If True, adds spaces between delimiters and text
            when inline.
        indent: The number of spaces to indent each line when using
            block format.

    Returns:
        The text wrapped with the given delimiters.
    """

    if not text:
        return delims[0] + delims[1]
    if force_block or ("\n" in text):
        text = textwrap.indent(text, " " * indent)
        return delims[0] + "\n" + text + "\n" + delims[1]
    if spaced_line:
        return delims[0] + " " + text + " " + delims[1]
    return delims[0] + text + delims[1]


def html_tag(
    tag: str,
    content: str | list[str],
    *,
    force_block=False,
    indent: int = 4,
    **kwargs: Optional[str],
) -> str:
    """Wrap content in an HTML tag. Supports attributes and block
    formatting.

    Notes:
    - If `content` is a list, it is joined into a single string with
        line breaks.
    - Attributes with a leading underscore (`_class`) are stripped of
        the underscore.

    Args:
        tag: The HTML tag name.
        content: The text or list of strings to wrap within the tag.
        force_block: If True, forces block formatting even for single
            line content.
        indent: The number of spaces to indent block content.
        **kwargs: Optional HTML attributes as key-value pairs.

    Returns:
        A string representing the formatted HTML element.
    """

    if isinstance(content, list):
        content = "\n".join(content)

    open_tag = f"<{tag}"
    for attr, value in kwargs.items():
        open_tag += (
            f' {attr.lstrip("_")}="{value}"' if value is not None else ""
        )
    open_tag += ">"
    close_tag = f"</{tag}>"

    return wrap_delims(
        content,
        (open_tag, close_tag),
        force_block=force_block,
        spaced_line=False,
        indent=indent,
    )
