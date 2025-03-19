# Rubberize

**Turn Python calculations into well-formatted, math-rich documents.**

## Installation

Install Rubberize with `pip`:

```bash
pip install rubberize
```

Rubberize is primarily built for Jupyter. To enable notebook magics:

```bash
pip install rubberize[notebook]
```

## Basic Usage

### In Modules

Here's a quick example of how to use Rubberize:

```python
import rubberize

source = """\
a + b
a - b
"""

namespace = {"a": 1, "b": 2}
stmts_latex = rubberize.latexer(source, namespace)
```

`stmts_latex` will be a list of `StmtLatex` objects that contain LaTeX representations of each statement.

### In Notebooks

Rubberize is more impressive in notebooks (assuming `rubberize[notebooks]` is installed). In a Code cell, use `%%tap` and your code in the cell will be displayed as math notation, along with substitutions, results, and comments.

## Contributing

To set up a development environment, install the supported dependencies:

```bash
pip install rubberize[dev]
```

## License

MIT License © 2025 [Chito Peralta](mailto:chitoangeloperalta@gmail.com)

