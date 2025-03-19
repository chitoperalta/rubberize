"""Call registry system."""

from rubberize.latexer.calls.convert_call import (
    convert_call,
    register_call_converter,
)
from rubberize.latexer.calls import builtin_calls

try:
    # If Pint is installed:
    from rubberize.latexer.calls import pint_calls
except ImportError:
    pass

try:
    # If Sympy is installed:
    from rubberize.latexer.calls import sympy_calls
except ImportError:
    pass

try:
    # If Numpy is installed:
    from rubberize.latexer.calls import numpy_calls
except ImportError:
    pass
