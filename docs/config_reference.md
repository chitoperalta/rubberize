# Config Reference

This document lists all Config Options and Keywords supported by Rubberize, along with their effects.

## Config Options

Config Options are name-value pairs (e.g., `@use_symbols=True`) that control how Rubberize renders expressions and statements.

### Variable Name Rendering Options

> *Also see [variables rendering guide](rendering/variables.md).*

| Option            | Type           | Default                            | Description                                                                                                                                            |
|-------------------|----------------|------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| `@use_subscripts` | `bool`         | `True`                             | Convert underscores (`_`) to subscripts.                                                                                                               |
| `@use_symbols`    | `bool`         | `True`                             | Convert greek names, accents, and letters to proper mathematical symbols.                                                                              |
| `@greek_starts`   | `set[str]`[^1] | `{"Delta", "gamma", "phi", "psi"}` | Mathematical symbols (i.e., Greek letters) that will be rendered when it appears in the beginning of the base name, e.g., `DeltaT` becomes $\Delta T$. |
| `@hidden_modules` | `set[str]`[^1] | `{"math", "sp", "np", "ureg"}`     | Names found in the set will be skipped from being rendered.                                                                                            |

### Number Types Rendering Options

> *Also see [numbers rendering guide](rendering/numbers.mds) for options for number types.*  

| Option                   | Type    | Default | Description                                                                                                                                                                                                                                                                         |
|--------------------------|---------|---------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `@str_font`              | `str`   | `""`    | Set the $\LaTeX$ font style for `str` types. Options are `""` for default, `"bf"` for bold, `"it"` for italics, `"rm"` for roman, `"sf"` for sans serif, `"tt"` for typewriter.                                                                                                     |
| `@num_format`            | `str`   | `"FIX"` | Set the number format used to render real number types. Options are `"FIX"` for fixed-point decimal notation, `"SCI"` for scientific notation, `"GEN"` for general notation, `"ENG"` for engineering notation.                                                                      |
| `@num_format_prec`       | `int`   | `2`     | If `@num_format="FIX"`, set the **number of decimal digits** to be displayed. Otherwise, it is the **number of significant figures** to be displayed.                                                                                                                               |
| `@num_format_max_digits` | `int`   | `15`    | Only works when `@num_format="FIX"`. Real numbers with more digits than this value will automatically switch to scientific notation for readability.                                                                                                                                |
| `@num_format_e_not`      | `bool`  | `False` | For `@num_format` that uses the scientific notation (`"SCI"`,`"GEN"`, or `"ENG"`), use [E notation](https://en.wikipedia.org/wiki/Scientific_notation#E_notation) instead of the standard scientific notation format, e.g., $6.942\mathrm{E}{+4}$ instead of $6.942 \times 10^{4}$. |
| `@thousands_separator`   | `str`   | `" "`   | Set the thousands separator. Also applied to `int` types. Options are `""` for no separator, `" "` for thin space, `","` for comma, `"."` for point, `"'"` for apostrophe.                                                                                                          |
| `@decimal_marker`        | `str`   | `"."`   | Set the decimal marker. Options are `"."` or `","`.                                                                                                                                                                                                                                 |
| `@zero_float_threshold`  | `float` | `1e-12` | If the absolute value of the number is less than this value, it will be rendered as zero. This behavior accounts for floating-point precision errors in computations.                                                                                                               |
| `@use_polar`             | `bool`  | `False` | Display `complex` types in polar form.                                                                                                                                                                                                                                              |
| `@use_polar_deg`         | `bool`  | `True`  | Only works when `@use_polar=True`. Use degrees for phase angles of complex numbers instead of radians.                                                                                                                                                                              |

### Collection Types Rendering Options

> *Also see [collections rendering guide](rendering/collections.md) for option for collection types.*

| Option               | Type   | Default | Description                       |
|----------------------|--------|---------|-----------------------------------|
| `@show_list_as_col`  | `bool` | `True`  | Show lists as column arrays.      |
| `@show_tuple_as_col` | `bool` | `False` | Show tuples as column arrays.     |
| `@show_set_as_col`   | `bool` | `False` | Display sets on a column.         |
| `@show_dict_as_col`  | `bool` | `True`  | Display dictionaries on a column. |

### Pint Rendering Options

> *Also see [Pint rendering guide](rendering/pint.md) for options for Pint quantity and unit types.*

| Option              | Type   | Default | Description                                                                                                                                                                                                                                |
|---------------------|--------|---------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `@use_inline_units` | `bool` | `True`  | Display fractions in units using a solidus ($a/b$) instead of a fraction ($\frac{a}{b}$) for a more compact but readable appearance. If the fraction has multiple denominator terms, negative exponents will be used instead of a solidus. |
| `@use_dms_units`    | `bool` | `False` | Display angle quantities in degree-minute-second (DMS) format.                                                                                                                                                                             |
| `@use_fif_units`    | `bool` | `False` | Display length quantities in foot-inch-fraction (FIF) format.                                                                                                                                                                              |
| `@fif_prec`         | `int`  | `16`    | Only works when `@use_fif_units=True`. Set the precision of the fractional part in FIF units, e.g., `16` for 1/16 of an inch precision.                                                                                                    |

### Expression Display Mode Options

Display modes are the distinct forms an expression can take: its general definition, its substituted version with values, and its final evaluated result. Also see [expression display modes guide](rendering/expressions.md#expression-display-modes).

| Option               | Type           | Default                        | Description                                                                              |
|----------------------|----------------|--------------------------------|------------------------------------------------------------------------------------------|
| `@show_definition`   | `bool`         | `True`                         | Show the base form of the expression, before specific values have been substituted.      |
| `@show_substitution` | `bool`         | `True`                         | Show the expression after substituting numerical values to variables.                    |
| `@show_result`       | `bool`         | `True`                         | Show the final calculated value for the expression.                                      |
| `@multiline`         | `bool`         | `False`                        | Arrange display modes such that each mode is on its own line.                            |
| `@math_constants`    | `set[str]`[^1] | `{"e", "pi", "phi", "varphi"}` | Symbol names found in this set will not be substituted in the substitution display mode. |

### Expression Rendering Options

| Option                   | Type   | Default | Description                                                                                                                                                                                                          |
|--------------------------|--------|---------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `@wrap_indices`          | `bool` | `True`  | Enclose element access indices and dictionary keys in parentheses. Also see [collections guide for accessing elements](rendering/collections.md#accessing-collection-elements).                                      |
| `@convert_special_funcs` | `bool` | `True`  | Prevent the rendering of class and function calls based on defined special conversion rules.                                                                                                                         |
| `@use_contextual_mult`   | `bool` | `True`  | Use a multiplication symbol appropriate to the factors being multiplied. Also see [expressions guide for contextual multiplication](rendering/expressions.md#contextual-multiplication-symbol) for more information. |

[^1]: When passing Config Options that take sets as arguments to `%%tap`, wrap the set in quotes, e.g., `@greek_starts='{"pi","nu"}'`

## Keywords

Keywords are shorthand names that represent one or more Config Options, allowing quick adjustments.

| Keyword  | Equivalent Config                                                    | Description                                       |
|----------|----------------------------------------------------------------------|---------------------------------------------------|
| `@none`  | `@show_definition=False @show_substitution=False @show_result=False` | Hide all display modes.                           |
| `@all`   | `@show_definition=True @show_substitution=True @show_result=True`    | Show all display modes.                           |
| `@def`   | `@show_definition=True @show_substitution=False @show_result=False`  | Show only the definition display mode.            |
| `@sub`   | `@show_definition=False @show_substitution=True @show_result=False`  | Show only the substitution display mode.          |
| `@res`   | `@show_definition=False @show_substitution=False @show_result=True`  | Show only the results display mode.               |
| `@nodef` | `@show_definition=False @show_substitution=True @show_result=True`   | Show all display modes except the definition.     |
| `@nosub` | `@show_definition=True @show_substitution=False @show_result=True`   | Show all display modes except the substitution.   |
| `@nores` | `@show_definition=True @show_substitution=True @show_result=False`   | Show all display modes except the result.         |
| `@line`  | `@multiline=False`                                                   | Arrange display modes on a line.                  |
| `@stack` | `@multiline=True`                                                    | Stack the display modes.                          |
| `@fix`   | `@num_format="FIX"`                                                  | Use a fixed-point decimal notation number format. |
| `@sci`   | `@num_format="SCI"`                                                  | Use a scientific notation number format.          |
| `@gen`   | `@num_format="GEN"`                                                  | Use a general notation number format.             |
| `@eng`   | `@num_format="ENG"`                                                  | Use an engineering notation number format.        |
| `@0`     | `@num_format_prec=0`                                                 |                                                   |
| `@1`     | `@num_format_prec=1`                                                 |                                                   |
| `@2`     | `@num_format_prec=2`                                                 |                                                   |
| `@3`     | `@num_format_prec=3`                                                 |                                                   |
| `@4`     | `@num_format_prec=4`                                                 |                                                   |
| `@5`     | `@num_format_prec=5`                                                 |                                                   |
| `@6`     | `@num_format_prec=6`                                                 |                                                   |