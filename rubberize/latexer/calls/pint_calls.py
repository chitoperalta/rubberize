"""Converters for Pint calls."""

import pint

from rubberize.latexer.calls.common import get_result_and_convert, hide_method
from rubberize.latexer.calls.convert_call import register_call_converter

# fmt: off
register_call_converter(pint.Quantity, get_result_and_convert)

register_call_converter(pint.Quantity.ito, hide_method, syntactic=False)
register_call_converter(pint.Quantity.ito_base_units, hide_method, syntactic=False)
register_call_converter(pint.Quantity.ito_preferred, hide_method, syntactic=False)
register_call_converter(pint.Quantity.ito_reduced_units, hide_method, syntactic=False)
register_call_converter(pint.Quantity.ito_root_units, hide_method, syntactic=False)

register_call_converter(pint.Quantity.to, hide_method, syntactic=False)
register_call_converter(pint.Quantity.to_base_units, hide_method, syntactic=False)
register_call_converter(pint.Quantity.to_compact, hide_method, syntactic=False)
register_call_converter(pint.Quantity.to_preferred, hide_method, syntactic=False)
register_call_converter(pint.Quantity.to_reduced_units, hide_method, syntactic=False)
register_call_converter(pint.Quantity.to_root_units, hide_method, syntactic=False)
