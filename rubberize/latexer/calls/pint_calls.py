"""Converters for Pint calls."""

import pint

from rubberize.latexer.calls.convert_call import register_call_converter
from rubberize.latexer.calls.builtin_calls import eval_and_convert, hide_method

# fmt: off
register_call_converter("Quantity", eval_and_convert)

register_call_converter("ito", lambda v, c: hide_method(v, c, pint.Quantity))
register_call_converter("ito_base_units", lambda v, c: hide_method(v, c, pint.Quantity))
register_call_converter("ito_preferred", lambda v, c: hide_method(v, c, pint.Quantity))
register_call_converter("ito_reduced_units", lambda v, c: hide_method(v, c, pint.Quantity))
register_call_converter("ito_root_units", lambda v, c: hide_method(v, c, pint.Quantity))

register_call_converter("to", lambda v, c: hide_method(v, c, pint.Quantity))
register_call_converter("to_base_units", lambda v, c: hide_method(v, c, pint.Quantity))
register_call_converter("to_compact", lambda v, c: hide_method(v, c, pint.Quantity))
register_call_converter("to_preferred", lambda v, c: hide_method(v, c, pint.Quantity))
register_call_converter("to_reduced_units", lambda v, c: hide_method(v, c, pint.Quantity))
register_call_converter("to_root_units", lambda v, c: hide_method(v, c, pint.Quantity))
