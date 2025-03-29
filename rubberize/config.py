"""Config system.

The configuration is a singleton instance of `_Config`.
"""

import ast
import json
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterable, Literal, Optional

from rubberize import exceptions


@dataclass
class _ConfigDefaults:  # pylint: disable=too-many-instance-attributes
    """Default config."""

    # Name
    use_subscripts: bool = True
    use_symbols: bool = True
    greek_starts: set[str] = field(
        default_factory=lambda: {"Delta", "gamma", "phi", "psi"}
    )

    # Display modes
    show_definition: bool = True
    show_substitution: bool = True
    show_result: bool = True

    # String display options
    str_font: Literal["", "bf", "it", "rm", "sf", "tt"] = ""

    # Number display options
    num_format: Literal["FIX", "SCI", "GEN", "ENG"] = "FIX"
    num_format_prec: int = 2
    num_format_max_digits: int = 15
    num_format_e_not: bool = False
    thousands_separator: Literal["", " ", ",", ".", "'"] = " "
    decimal_marker: Literal[".", ","] = "."
    zero_float_threshold: float = 1e-12

    use_polar: bool = False
    use_polar_deg: bool = True

    use_inline_units: bool = True
    use_dms_units: bool = False
    use_fif_units: bool = False
    fif_prec: int = 16

    # Expressions
    wrap_indices: bool = True
    convert_special_funcs: bool = True
    use_contextual_mult: bool = True
    hidden_modules: set[str] = field(
        default_factory=lambda: {"math", "sp", "np", "ureg"}
    )
    math_constants: set[str] = field(
        default_factory=lambda: {"e", "pi", "phi", "varphi"}
    )
    show_list_as_col: bool = True
    show_tuple_as_col: bool = False
    show_set_as_col: bool = False
    show_dict_as_col: bool = True

    # Statements
    multiline: bool = False


class _Config(_ConfigDefaults):
    """Singleton global configuration."""

    def __init__(self):
        super().__init__()
        self.load()

    def set(self, **kwargs: bool | int | Iterable[str]) -> None:
        """Update multiple config values passed as keyword arguments."""

        for key, value in kwargs.items():
            if not hasattr(self, key):
                raise AttributeError(f"Invalid config key: {key}")

            if key in ("greek_starts", "hidden_modules", "math_constants"):
                if not isinstance(value, (set, list, tuple)):
                    raise exceptions.RubberizeTypeError(
                        f"Invalid {key} type: {type(value)}"
                    )
                value = set(value)

            setattr(self, key, value)

    def load(self, *args: str, path: Optional[str | Path] = None) -> None:
        """Load config from defaults or a specified JSON file.

        If a file exists for a given `path`, its contents are loaded and
        used to update the config. Otherwise, default values are used.

        Args:
            *args: If provided, only the specified keys are updated.
            path: Path to the JSON file. If `None`, the default values
                are used.
        """

        data = asdict(_ConfigDefaults())

        if path is not None:
            path = Path(path)
            if path.exists():
                with path.open("r", encoding="utf-8") as f:
                    data.update(json.load(f))

        if args:
            data = {k: data[k] for k in args if k in data}
        self.set(**data)

    def reset(self, *args: str) -> None:
        """Reset the config or only the specified keys to defaults."""

        self.load(*args, path=None)

    def save(self, path: str | Path) -> None:
        """Save the current config to a JSON file."""

        config_dict = asdict(self)
        config_dict["greek_starts"] = list(config_dict["greek_starts"])
        config_dict["hidden_modules"] = list(config_dict["hidden_modules"])
        config_dict["math_constants"] = list(config_dict["math_constants"])

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=4)

    def add_greek_start(self, *modules: str) -> None:
        """Add one or more modules to `greek_starts`."""

        self.greek_starts.update(modules)

    def remove_greek_start(self, *modules: str) -> None:
        """Remove one or more modules from `greek_starts`."""

        self.greek_starts.difference_update(modules)

    def add_hidden_module(self, *modules: str) -> None:
        """Add one or more modules to `hidden_modules`."""

        self.hidden_modules.update(modules)

    def remove_hidden_module(self, *modules: str) -> None:
        """Remove one or more modules from `hidden_modules`."""

        self.hidden_modules.difference_update(modules)

    def add_math_constant(self, *constant: str) -> None:
        """Add one or more constant to `math_constants`."""

        self.math_constants.update(constant)

    def remove_math_constant(self, *constant: str) -> None:
        """Remove one or more constant from `math_constants`."""

        self.math_constants.difference_update(constant)

    @contextmanager
    def override(self, **kwargs: bool | int | Iterable[str]):
        """Temporarily override config values within a context."""

        original_values = {key: getattr(self, key) for key in kwargs}

        try:
            self.set(**kwargs)
            yield
        finally:
            self.set(**original_values)


# fmt: off
_KEYWORDS: dict[str, dict[str, Any]] = {
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
    "fix": {"num_format": "FIX"},
    "sci": {"num_format": "SCI"},
    "gen": {"num_format": "GEN"},
    "eng": {"num_format": "ENG"},
    "0": {"num_format_prec": 0},
    "1": {"num_format_prec": 1},
    "2": {"num_format_prec": 2},
    "3": {"num_format_prec": 3},
    "4": {"num_format_prec": 4},
    "5": {"num_format_prec": 5},
    "6": {"num_format_prec": 6},
}
# fmt: on


def parse_modifiers(modifiers: list[str]) -> dict[str, Any]:
    """Parse a list of modifiers to an overrides dict for use with
    `config.override()`.
    """

    override_dict = {}
    for modifier in modifiers:
        modifier = modifier.removeprefix("@")

        if modifier == "hide":
            return {"hide": ...}
        if modifier == "endhide":
            return {"endhide": ...}

        if "=" in modifier:
            key, value = modifier.split("=", 1)
            override_dict[key] = ast.literal_eval(value)
        elif modifier in _KEYWORDS:
            override_dict.update(_KEYWORDS[modifier])
        else:
            raise exceptions.RubberizeKeywordError(
                f"Unknown keyword: '{modifier}'"
            )
    return override_dict


# Singleton instance
config = _Config()
