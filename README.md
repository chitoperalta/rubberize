<picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/chitoperalta/rubberize/main/docs/assets/banner_dark.png">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/chitoperalta/rubberize/main/docs/assets/banner.png">
    <img alt="Rubberize Banner" title="Turn Python calculations into well-formatted, math-rich documents." src="https://raw.githubusercontent.com/chitoperalta/rubberize/main/docs/assets/banner.png">
</picture>

# Rubberize

Rubberize is a Python library designed to enhance the presentation of
calculations in Jupyter notebooks and Python scripts.

**In Jupyter Notebooks:** Rubberize transforms code cells containing calculations
into beautifully typeset mathematical expressions using LaTeX, making engineering
and scientific computations easier to read and review. Simply use the `%%tap`
magic command to render your code as math-rich output.

<picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/chitoperalta/rubberize/main/docs/assets/notebook_example_dark.png">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/chitoperalta/rubberize/main/docs/assets/notebook_example.png">
    <img alt="Screenshot of a Jupyter Notebook using Rubberize" src="https://raw.githubusercontent.com/chitoperalta/rubberize/main/docs/assets/notebook_example.png">
</picture>

**As an API:** Developers can use Rubberize's API to generate LaTeX representations
of Python code. These LaTeX outputs can then be integrated into custom typesetting
workflows, providing flexibility for professional-grade documents.

Rubberize bridges the gap between raw code and polished, math-rich documentation.

## Who is Rubberize For?

Rubberize is designed for:

- **Scientists and Engineers**: Simplify the presentation of complex calculations
in Jupyter notebooks by rendering them as clear, typeset math.
- **Educators and Students**: Create visually appealing and easy-to-understand
mathematical explanations directly from Python code.
- **Technical Writers**: Generate LaTeX representations of Python calculations for
seamless integration into professional-grade documents.
- **Developers**: Use Rubberize's API to build custom workflows for typesetting
and documentation.

If you work with Python code that involves mathematical computations and want to
bridge the gap between raw code and polished documentation, Rubberize is for you!

## Installation

Install Rubberize with `pip`:

```bash
pip install rubberize
```

Rubberize is primarily built for Jupyter. To enable notebook magics:

```bash
pip install rubberize[notebook]
# The headless chromium dependency of `playwright` also needs to be installed:
playwright install chromium
```

## Basic Usage

> [!WARNING]
> **Use of `eval()`**: This project uses Python's built-in `eval()` to evaluate some expressions. Since it executes code already present in the input source (e.g., a Jupyter cell or script), it poses no additional risk in such environments. However, be cautious when handling untrusted inputs outside controlled settings.

### In Jupyter Notebooks

Rubberize must be installed with `pip install rubberize[notebooks]`. Load the
extension after importing:

```python
import rubberize
%load_ext rubberize
```

Then, on the next code cell, use the `%%tap` magic command. Your code within the
cell will be rendered in math notation, along with substitutions, results, and
comments:

```python
%%tap
import math
a = 3
b = 4
c = math.sqrt(a**2 + b**2)
```
&emsp; $\displaystyle a = 3$

&emsp; $\displaystyle b = 4$
 
&emsp; $\displaystyle c = \sqrt{a^{2} + b^{2}} = \sqrt{3^{2} + 4^{2}} = 5.00$

There are a lot of customization options available, such as controlling the display
of substitutions and results, formatting the output, and integrating Rubberize with
other libraries such as [Pint](https://github.com/hgrecco/pint).

For more detailed examples and advanced usage, please refer to the
[Rubberize Documentation](https://github.com/chitoperalta/rubberize/blob/main/docs/index.md).

### As an API

You can use `latexer()` to generate LaTeX for your Python statements, and use the
output in your own typesetting code.

```python
import rubberize

source = """\
 import math
 a = 3
 b = 4
 c = math.sqrt(a**2 + b**2)
"""
namespace = {"a": 3, "b": 4, "c": 5.0}

stmts_latex = rubberize.latexer(source, namespace)
```

Please refer to the [API reference](https://github.com/chitoperalta/rubberize/blob/main/docs/api_reference.md) (TODO) section of the Rubberize
Documentation for more information.

## Why Those Names?

The name *Rubberize* is inspired by the process of tapping rubber trees for latex.
In the same way, this library **taps** into the **abstract syntax tree (AST)** of a
Python code to extract **LaTeX**. The `%%tap` magic command acts as the tap, drawing
out structured mathematical representations—just like latex flowing from a tree!

## Contributing

This is my first full project, and as a facade structural engineer by profession,
I’m still learning the ropes of software development. I would greatly appreciate
help from experienced developers in areas such as:

- Setting up a robust development environment
- Writing and organizing tests
- Improving and expanding the documentation

If you’re interested in contributing or mentoring, please feel free to contact me. I’m eager to learn and collaborate to make Rubberize even better!

Thank you for your support!

### Setting Up for Development

To set up Rubberize for development, install the development dependencies:

```bash
pip install rubberize[dev]
```

This will also install other libraries supported by Rubberize.

## License

[MIT License](LICENSE) © 2025 Chito Peralta

