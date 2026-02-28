"""**I**nline **R**u**B**beri**Z**e. Markdown extension to run Python
code in `{{...}}` through the latexer.
"""

from typing import Any, Optional

from markdown.extensions import Extension
from markdown.inlinepatterns import (
    InlineProcessor,
)

import rubberize.vendor.ast_comments as ast_c
from rubberize.latexer.stmt_latex import StmtLatex
from rubberize.latexer.node_visitors import ModVistor


class IrbzProcessor(InlineProcessor):
    """Run Python code in `{{...}}` syntax through the latexer."""

    def __init__(
        self, pattern, md=None, namespace: Optional[dict[str, Any]] = None
    ):
        super().__init__(pattern, md)
        self.namespace = namespace

    def handleMatch(self, m, data):
        text = m.group(1).strip()
        text_ast = ast_c.parse(text)
        text_latex: StmtLatex = ModVistor(self.namespace).visit(text_ast)[0]

        text_str = ""
        if text_latex.latex:
            text_str += r"\( \displaystyle " + text_latex.latex + r" \)"
        if text_latex.desc:
            text_str += " (" + text_latex.desc.strip() + ")"
        return text_str, m.start(0), m.end(0)


class Irbz(Extension):
    """Markdown extension to Rubberize a Python code within `{{...}}`
    syntax.
    """

    def __init__(self, namespace: Optional[dict[str, Any]] = None, **kwargs):
        super().__init__(**kwargs)
        self.namespace = namespace

    def extendMarkdown(self, md):
        pattern = r"(?<!\\)\{\{\s*(.*?)\s*\}\}"
        md.inlinePatterns.register(
            IrbzProcessor(pattern, md, self.namespace),
            "python_expression",
            175,
        )
