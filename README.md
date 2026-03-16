<picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/chitoperalta/rubberize/main/docs/assets/banner_dark.png">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/chitoperalta/rubberize/main/docs/assets/banner.png">
    <img alt="Rubberize Banner" title="Turn Python calculations into well-formatted, math-rich documents." src="https://raw.githubusercontent.com/chitoperalta/rubberize/main/docs/assets/banner.png">
</picture>

# Rubberize

Rubberize converts raw Python code into readable mathematical notation so calculations can be clearly presented, reviewed, and documented.

## Who is Rubberize For?

Rubberize is designed for:

- **Scientists and Engineers**: Simplify the presentation of complex calculations in Jupyter notebooks by rendering them as clear, typeset math.
- **Educators and Students**: Create visually appealing and easy-to-understand mathematical explanations directly from Python code.
- **Technical Writers**: Generate LaTeX representations of Python calculations for seamless integration into professional-grade documents.

If you work with Python code that involves mathematical computations and want to bridge the gap between raw code and polished documentation, Rubberize is for you!

## Installation

Install Rubberize with `pip`:

```bash
pip install rubberize
```

To include dependencies that allow Rubberize to be used with Jupyter Notebooks:

```bash
pip install rubberize[jupyter]
```

## Quick Start

> [!WARNING]
> **Use of `eval()`**: This project uses Python's built-in `eval()` to evaluate some expressions. Since it executes code already present in the input source (e.g., a Jupyter cell or script), it poses no additional risk in such environments. However, be cautious when handling untrusted inputs outside controlled settings.

In a Jupyter notebook, load the extension:

```python
%load_ext rubberize
```

Use the `%%tap` magic:

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

## Documentation

Full tutorials, configuration options, and examples are found in [Rubberize Documentation](https://chitoperalta.github.io/rubberize/).

## Why The Names?

Rubberize is inspired by **tapping rubber trees for latex**.

The `%%tap` command taps a code cell and extracts **LaTeX**, turning ordinary Python calculations into structured mathematical output.

## Contributing

If you’re interested in contributing or mentoring, please feel free to contact me. I’m eager to collaborate to make Rubberize even better.

### Setting Up for Development

Clone the repository:

```bash
git clone https://github.com/chitoperalta/rubberize.git
cd rubberize
```

Set up a virtual environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate
# Windows: .venv\Scripts\activate
```

Install Rubberize in editable mode with development dependencies:

```bash
pip install -e ".[dev]"
```

## License

[MIT License](LICENSE) © 2025-2026 Chito Peralta and contributors.

