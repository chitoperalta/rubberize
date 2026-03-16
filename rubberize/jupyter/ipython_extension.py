"""Loads the library into IPython"""

from __future__ import annotations

from importlib.resources import files
from typing import TYPE_CHECKING

from IPython.core.display import display_html

from rubberize.jupyter.magics import TapMagics, TapLoadMagics, ExportMagics

if TYPE_CHECKING:
    from IPython.core.interactiveshell import InteractiveShell


def load_ipython_extension(ipython: InteractiveShell) -> None:
    """Load the IPython extension."""

    ipython.register_magics(TapMagics, TapLoadMagics, ExportMagics)
    _load_css()


def _load_css() -> None:
    css = (files(__package__) / "styles.css").read_text("utf-8")
    display_html(f"<style>{css}</style>", raw=True)
