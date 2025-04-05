"""Rubberize turns Python calculations into well-formatted, math-rich
documents.
"""

__version__ = "0.3.3"

from rubberize.config import config

from rubberize.latexer import (
    latexer,
    CalcSheet,
    Table,
    ExprLatex,
    StmtLatex,
    register_call_converter,
    register_object_converter,
)

try:
    # If Pint is installed:
    from rubberize.latexer import register_units_latex
except ImportError:
    pass

from rubberize.render import render

try:
    # If IPython is installed:
    from rubberize.load_ipython_extension import load_ipython_extension
except ImportError:
    pass

try:
    # If exporter deps are installed:
    from rubberize.export_notebook import (
        export_notebook_to_html,
        export_notebook_to_pdf,
    )
except ImportError:
    pass
