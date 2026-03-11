"""Turn Python calculations into well-formatted, math-rich documents."""

__version__ = "0.4.0"

from rubberize.config import config

from rubberize.latexer import (
    latexer,
    ExprLatex,
    StmtLatex,
    register_block_converter,
    register_call_converter,
    register_object_converter,
)

from rubberize.render import render

from rubberize.calcsheet import CalcSheet

try:
    # requires Jupyter
    from rubberize.jupyter.ipython_extension import load_ipython_extension
except ImportError:
    pass

try:
    # requires Pint
    from rubberize.latexer import register_units_latex
except ImportError:
    pass
