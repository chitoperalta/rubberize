"""Markdown extension to convert Github-style alerts."""

import re
import xml.etree.ElementTree as etree

from markdown import Markdown
from markdown.extensions import Extension
from markdown.blockprocessors import BlockQuoteProcessor


class AlertProcessor(BlockQuoteProcessor):
    """Process Github-style alert blockquote syntax.

    Markdown like this:

    ```
    > [!NOTE]
    > This is an alert
    >
    > - List item 1
    > - List item 2
    ```

    converts to:

    ```
    <div class="rz-alert rz-alert--note">
    <div class="rz-alert__content">
    <p>This is an alert</p>
    <ul>
    <li>List item 1</li>
    <li>List item 2</li>
    </ul>
    </div>
    </div>
    ```
    """

    ALERT_RE = re.compile(r"^\[([?!])(\w+)\]\s*$", re.IGNORECASE)
    HEADER_RE = re.compile(r"^\[Section (.+?)\]\s*$", re.IGNORECASE)

    # pylint: disable-next=too-many-locals
    def run(self, parent: etree.Element, blocks: list[str]) -> None:
        block = blocks.pop(0)
        m = self.RE.search(block)
        if m:
            before = block[: m.start()]
            self.parser.parseBlocks(parent, [before])
            block = block[m.start() :]

        lines = [self.clean(l) for l in block.split("\n") if l.strip()]
        if not lines:
            return

        alert_m = self.ALERT_RE.match(lines[0])
        header_m = self.HEADER_RE.match(lines[0])

        if alert_m:
            prefix, alert_type = alert_m.groups()
            classes = f"rz-alert rz-alert--{alert_type.lower()}"
            if prefix == "?":
                classes += " rz-alert--noprint"
            div = etree.SubElement(parent, "div", {"class": classes})
            content_div = etree.SubElement(
                div, "div", {"class": "rz-alert__content"}
            )
            self.parser.state.set("blockquote")
            self.parser.parseChunk(content_div, "\n".join(lines[1:]))
            self.parser.state.reset()

        elif header_m:
            section = header_m.group(1)
            classes = "rz-header"
            header = etree.SubElement(parent, "header", {"class": classes})
            section_p = etree.SubElement(
                header, "p", {"class": "rz-header__section-number"}
            )
            section_p.text = f"Section {section}" if section else "1.01"
            self.parser.state.set("blockquote")
            self.parser.parseChunk(header, "\n".join(lines[1:]))
            self.parser.state.reset()

        else:
            super().run(parent, [block])


class Alert(Extension):
    """Markdown extension to convert Github-style alerts."""

    def extendMarkdown(self, md: Markdown) -> None:
        md.parser.blockprocessors.register(
            AlertProcessor(md.parser), "alert", 75
        )
