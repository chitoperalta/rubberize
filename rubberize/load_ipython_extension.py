"""Loads the calcsetter extension features into IPython."""

import os

from IPython.core.display import display_html
from IPython.core.interactiveshell import InteractiveShell

from rubberize.magics import RubberizeMagics


def load_ipython_extension(ipython: InteractiveShell) -> None:
    """Load the IPython extension.

    This function is not to be called directly. It executed by the
    %load_ext line magic in the IPython InteractiveShell. It registers
    the magics of the library.
    """
    ipython.register_magics(RubberizeMagics)
    _load_css(os.path.join(os.path.dirname(__file__), "static", "styles.css"))


def _load_css(path: str) -> None:
    """Load a CSS stylesheet into IPython."""

    with open(path, "r", encoding="utf-8") as file:
        css = file.read()
    display_html(f"<style>{css}</style>", raw=True)
