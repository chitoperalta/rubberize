# Getting Started

Welcome to **Rubberize**! This guide will help you get started with using Rubberize
in Jupyter Notebooks to render your calculations as beautifully typeset math.

If you plan to use Rubberize's functions only in your scripts, consider heading
directly to the [API Reference](api_reference.md).

## Installation

To install Rubberize for Jupyter Notebooks, run the following command:

```bash
pip install rubberize[notebook]
```

Additionally, you need to install [Playwright](https://playwright.dev) dependencies
which are required for the PDF export functionality:

```bash
playwright install
```

## Before You Begin

Rubberize is designed for Jupyter Notebooks. To follow along with this guide:

1. Open a Jupyter Notebook.
2. Copy and paste the provided code examples into **separate** code cells.
3. Run each cell to see the results.

## Loading the Rubberize Extension

To load Rubberize in your notebook, import it and use the `%load_ext` line magic:

```python
import rubberize
%load_ext rubberize
```

Rubberize loads its *cell magic* commands and CSS stylesheet, enabling you to use it
in subsequent cells. You only need to do this once per notebook session.

## Rendering Python Calculations

Use the `%%tap` cell magic command **at the first line** of a code cell to render the
entire cell as typeset math. For example, paste the following into a cell and run it:

```python
%%tap
import math
a = 3
b = 4
c = math.sqrt(a**2 + b**2)
```

The cell output will display lines of math. Note that Rubberize ignores the `import`
statement. The last rendered statement will look like this:

$ \displaystyle c = \sqrt{a^{2} + b^{2}} = \sqrt{3^{2} + 4^{2}} = 5.00 $

As shown, Rubberize not only *translates* a calculation line into math notation but
also displays the substitution of known values and the final result.

## Expression Display Modes

Rubberize renders a full math expression in three ways:

| Display Mode     | Description                                                                            | Rendered Output                        |
|------------------|----------------------------------------------------------------------------------------|----------------------------------------|
| **Definition**   | The base form of the expression, before substituting specific values.                  | $ \displaystyle \sqrt{x^{2} + y^{2}} $ |
| **Substitution** | The expression after substituting numerical values for variables.                      | $ \displaystyle \sqrt{3^{2} + 4^{2}} $ |
| **Result**       | The final calculated value of the expression after all operations are performed.       | $ \displaystyle 5.00 $                 |

By default, Rubberize generates **all three display modes**, arranging them as
equalities on a single line.

## Managing the Display Modes

You can configure which display modes are included during rendering using either
the following `config` option or *keyword*:

| Display Mode     | Config Option             | Keyword to show<br>only the mode | Keyword to hide<br>only the mode |
|------------------|---------------------------|----------------------------------|----------------------------------|
| **Definition**   | `@show_definition=True`   | `@def`                           | `@nodef`                         |
| **Substitution** | `@show_substitution=True` | `@sub`                           | `@nosub`                         |
| **Result**       | `@show_result=True`       | `@res`                           | `@nores`                         |

Additionally, the keyword `@none` hides all display modes, while `@all` shows all
display modes.

You can apply this in three ways.

> [!note]
> These three methods are how you configure all settings.

- **Method 1:** Passing as an Argument to `%%tap`
    ```python
    %%tap  @show_substitution=False
    c = math.sqrt(a**2 + b**2)
    d = a - b
     ```
    or

    ```python
    %%tap  @nosub
    c = math.sqrt(a**2 + b**2)
    d = a - b
     ```
- **Method 2:** As a line comment. If done this way, the configuration will apply
    to all subsequent lines until the next line comment is encountered:
    ```python
    %%tap
    a * b
    # @def
    a + b
    a - b
    # @res
    a / b
    ```
- **Method 3:** As an inline comment. If done this way, the configuration will apply
    to the commented line only.
    ```python
    %%tap
    a + b
    a - b  # @nosub
    ```

## Annotations

You can add annotations to your calculations using Python comments. Since comments
in Python are ignored during execution, they provide a natural way to document
calculations without affecting the results.

Annotations that are typed in as **inline comments** are rendered beside the
corresponding math statements, so that explanations stay closely linked visually
to the calculations they describe. Meanwhile, comments placed **on their own lines**
remain separate when rendered, preserving their distinction as standalone annotations.

```python
%%tap
# This is a standalone annotation
x = 50.25  # This is an inline annotation.
y = x + 120.23
z = x ** 2 + 3 / y  # This is another annotation. The previous line doesn't have one!
```

### Formatting Annotations

Annotations can be formatted using the standard Markdown syntax, with a few additions:

- `^...^`: Makes the enclosed text appear smaller.
- `\\`: Forces a line break within a line, which is useful for breaking inline comments.
- `> [!NOTE]` for a blockquote-style alert box, similar to GitHub's.

### Rubberize in Annotations

Annotations can contain Python code inline, within `{{ ... }}` delimiters.
**Rubberize** will render these expressions to math notation as well. Wow!

```python
%%tap
# ### Rubberize in Annotations
# Annotations can contain Python code inline, within `{{ }}` delimiters.
# **Rubberize** will render these expressions to math notation as well. Wow!
#
# For example, we know {{ z }}, so twice of it is {{ 2 * z }}.
```

<!--
    TODO:
        - Variable naming
        - Other features and stylistic choices
        - Integrating with pint units
        - `CalcSheet` and `Table` classes
-->
