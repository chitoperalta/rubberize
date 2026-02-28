"""Markdown extension to treat LaTeX-style line breaks as `<br>`."""

import re

from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor


# pylint: disable-next=too-few-public-methods
class DoubleBackslashPreprocessor(Preprocessor):
    """Replace `\\\\` with `<br>`. Hooks on the preprocessing step,
    actual syntax processing by Markdown.
    """

    def run(self, lines):
        return [re.sub(r"\s*\\\\\s*", "<br>", line) for line in lines]


class LatexLinebreak(Extension):
    """Markdown extension to treat LaTeX-style line breaks (`\\\\`) as
    `<br>`.
    """

    def extendMarkdown(self, md):
        md.preprocessors.register(
            DoubleBackslashPreprocessor(md), "br_dbackslash", 25
        )
