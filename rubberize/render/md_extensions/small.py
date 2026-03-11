"""Markdown extension to apply `<small>` tag."""

from markdown.extensions import Extension
from markdown.inlinepatterns import SimpleTagInlineProcessor


class Small(Extension):
    """Markdown extension to introduce new inline text pattern for
    `<small>...</small>` from `^...^`.
    """

    def extendMarkdown(self, md):
        md.inlinePatterns.register(
            SimpleTagInlineProcessor(r"()(?<!\\)\^(.*?)\^", "small"),
            "small",
            175,
        )
