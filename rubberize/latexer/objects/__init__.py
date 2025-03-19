"""Object registry system"""

from rubberize.latexer.objects.convert_object import (
    convert_object,
    register_object_converter,
)
from rubberize.latexer.objects import builtin_objects

try:
    # If Pint is installed:
    from rubberize.latexer.objects import pint_objects
    from rubberize.latexer.objects.pint_objects import register_units_latex
except ImportError:
    pass

try:
    # If Sympy is installed:
    from rubberize.latexer.objects import sympy_objects
except ImportError:
    pass

try:
    # If Numpy is installed:
    from rubberize.latexer.objects import numpy_objects
except ImportError:
    pass
