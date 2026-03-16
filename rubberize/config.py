"""Config singleton."""

from __future__ import annotations

import ast
import json
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from dataclasses import dataclass, field, asdict

from rubberize._exceptions import (
    RubberizeAttributeError,
    RubberizeKeyError,
    RubberizeFileNotFoundError,
    RubberizeTypeError,
)

if TYPE_CHECKING:
    from typing import Literal, Iterable


@dataclass
# pylint: disable=too-many-instance-attributes
class _DefaultConfig:

    # symbols
    use_subscripts: bool = True
    use_symbols: bool = True
    greek_starts: set[str] = field(
        default_factory=lambda: {"Delta", "gamma", "phi", "psi"}
    )
    hidden_modules: set[str] = field(
        default_factory=lambda: {"math", "sp", "np", "ureg"}
    )

    # strings
    str_font: Literal["", "bf", "it", "rm", "sf", "tt"] = ""
    str_quotes: Literal["", "'", '"'] = '"'

    # numerical values
    float_format: Literal["FIX", "SCI", "GEN", "ENG"] = "FIX"
    float_prec: int = 2
    float_max_digits: int = 15
    use_e_not: bool = False
    thousands_separator: Literal["", " ", ",", ".", "'"] = " "
    decimal_marker: Literal[".", ","] = "."
    zero_float_threshold: float = 1e-12
    use_polar: bool = False
    use_polar_deg: bool = True

    # collections
    max_inline_elts: int = 5
    show_list_as_array: bool = False
    show_tuple_as_array: bool = False
    show_1d_as_col: bool = False
    array_delimiter: Literal["pmatrix", "bmatrix"] = "bmatrix"

    # expressions
    wrap_indices: bool = True
    convert_special_calls: bool = True
    use_contextual_mult: bool = True
    max_inline_bool: int = 3

    # display modes
    show_definition: bool = True
    show_substitution: bool = True
    show_result: bool = True
    multiline: bool = False
    math_constants: set[str] = field(
        default_factory=lambda: {"e", "pi", "phi", "varphi"}
    )

    # settings for Pint
    use_inline_units: bool = True
    use_dms_units: bool = False
    use_fif_units: bool = False
    fif_prec: int = 16


class _Config(_DefaultConfig):

    def __init__(self):
        super().__init__()
        self.load()

    def set(self, **kwargs: bool | int | Iterable[str]) -> None:
        """Update multiple config values passed as kwargs."""

        for k, v in kwargs.items():
            if not hasattr(self, k):
                raise RubberizeAttributeError(f"Invalid config key: {k}")

            if k in ("greek_starts", "hidden_modules", "math_constants"):
                if not isinstance(v, (set, list, tuple)):
                    raise RubberizeTypeError(f"Invalid {k} type: {type(v)}")
                v = set(v)

            setattr(self, k, v)

    def load(self, *args: str, path: str | Path | None = None) -> None:
        """Load config from defaults or a JSON file.

        Args:
            *args: If provided, only the specified keys are updated.
            path: Path to the JSON file. If None, the default values are used.
        """

        cfg = asdict(_DefaultConfig())

        if path is not None:
            path = Path(path)
            if not path.is_file():
                raise RubberizeFileNotFoundError(f"File not found: {str(path)}")

            cfg.update(json.loads(path.read_text("utf-8")))

        if args:
            cfg = {k: cfg[k] for k in args if k in cfg}

        self.set(**cfg)

    def reset(self, *args: str) -> None:
        """Reset the config or only the specified keys to defaults."""

        self.load(*args, path=None)

    def add_greek_start(self, *greeks: str) -> None:
        """Add one or more greek letters to greek_starts."""

        self.greek_starts.update(greeks)

    def remove_greek_start(self, *greeks: str) -> None:
        """Remove one or more greek letters from greek_starts."""

        self.greek_starts.difference_update(greeks)

    def add_hidden_module(self, *modules: str) -> None:
        """Add one or more modules to hidden_modules."""

        self.hidden_modules.update(modules)

    def remove_hidden_module(self, *modules: str) -> None:
        """Remove one or more modules from hidden_modules."""

        self.hidden_modules.difference_update(modules)

    def add_math_constant(self, *constants: str) -> None:
        """Add one or more constants to math_constants."""

        self.math_constants.update(constants)

    def remove_math_constant(self, *constants: str) -> None:
        """Remove one or more constants from math_constants."""

        self.math_constants.difference_update(constants)

    @contextmanager
    def override(self, **kwargs: bool | int | Iterable[str]):
        """Temporarily override config values within a context."""

        original = {k: getattr(self, k) for k in kwargs}

        try:
            self.set(**kwargs)
            yield
        finally:
            self.set(**original)


config = _Config()


# fmt: off
_KEYWORDS: dict[str, dict[str, bool | int | Iterable[str]]] = {
    "none": {"show_definition": False, "show_substitution": False, "show_result": False},
    "all": {"show_definition": True, "show_substitution": True, "show_result": True},
    "def": {"show_definition": True, "show_substitution": False, "show_result": False},
    "sub": {"show_definition": False, "show_substitution": True, "show_result": False},
    "res": {"show_definition": False, "show_substitution": False, "show_result": True},
    "nodef": {"show_definition": False, "show_substitution": True, "show_result": True},
    "nosub": {"show_definition": True, "show_substitution": False, "show_result": True},
    "nores": {"show_definition": True, "show_substitution": True, "show_result": False},
    "line": {"multiline": False},
    "stack": {"multiline": True},
    "fix": {"float_format": "FIX"},
    "sci": {"float_format": "SCI"},
    "gen": {"float_format": "GEN"},
    "eng": {"float_format": "ENG"},
    "0": {"float_prec": 0},
    "1": {"float_prec": 1},
    "2": {"float_prec": 2},
    "3": {"float_prec": 3},
    "4": {"float_prec": 4},
    "5": {"float_prec": 5},
    "6": {"float_prec": 6},
}
# fmt: on


def parse_modifiers(
    modifiers: list[str],
) -> dict[str, bool | int | Iterable[str]]:
    """Parse a list of modifiers to a config dict."""

    cfg = {}
    for m in modifiers:
        m = m.removeprefix("@")

        if m == "hide":
            return {"hide": True}

        if m == "endhide":
            return {"endhide": True}

        if "=" in m:
            k, v = m.split("=", 1)
            cfg[k] = ast.literal_eval(v)
        elif m in _KEYWORDS:
            cfg.update(_KEYWORDS[m])
        else:
            raise RubberizeKeyError(f"Unknown keyword: {m}")

    return cfg
