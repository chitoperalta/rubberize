# Rubberize

**Turn Python calculations into well-formatted, math-rich documents.**

![image](examples/example.png "Example Rubberize usage in a notebook environment")

## Installation

Install Rubberize with `pip`:

```bash
pip install rubberize
```

Rubberize is primarily built for Jupyter. To enable notebook magics:

```bash
pip install rubberize[notebook]
# The dependency `playwright` also needs to be installed:
playwright install
```

To set up a development environment, install the supported dependencies:

```bash
pip install rubberize[dev]
playwright install
```

## Basic Usage

### In Notebooks

 Assuming `rubberize[notebooks]` is installed, load the IPython extension after importing:

 ```python
 import rubberize
 %load_ext rubberize
 ```
 
 Then, on the next Code cell, use `%%tap`. Your code within the cell will be displayed as math notation, along with substitutions, results, and comments.

 See the [example](/docs/examples/example.ipynb) notebook for an in-depth look.

### In Modules

You can use `latexer()` to generate LaTeX for your Python statements, and use the returned list of `StmtLatex` instances in your own typesetting code.

```python
import rubberize

source = """\
a + b
a - b
"""

namespace = {"a": 1, "b": 2}
stmts_latex = rubberize.latexer(source, namespace)
```

A `StmtLatex` instance contains the LaTeX representation of a Python statement, including substitutions, results, and comments.

## Why Rubberize and `%%tap`?

The name *Rubberize* is inspired by the process of tapping rubber trees for latex. In the same way, this library taps into the **abstract syntax tree (AST)** of a Python code to extract LaTeX. The `%%tap` magic command acts as the tap, drawing out structured mathematical representations—just like latex flowing from a tree!

## License

[MIT License](LICENSE) © 2025 Chito Peralta

