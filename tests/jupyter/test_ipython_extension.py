# pylint: disable=all

from pathlib import Path

from IPython.core.interactiveshell import InteractiveShell

import rubberize.jupyter.ipython_extension as ipython_extension


# ---------
# load_css
# ---------


def test_load_css(monkeypatch):
    calls = {}

    def fake_display_html(html, raw=False):
        calls["html"] = html
        calls["raw"] = raw

    file_dir = Path(ipython_extension.__file__).parent

    monkeypatch.setattr(ipython_extension, "display_html", fake_display_html)
    monkeypatch.setattr(ipython_extension, "files", lambda _: file_dir)

    ipython_extension._load_css()

    assert calls["html"].startswith("<style>")
    assert (file_dir / "styles.css").read_text("utf-8") in calls["html"]
    assert calls["html"].endswith("</style>")
    assert calls["raw"] is True


# -----------------------
# load_ipython_extension
# -----------------------


class FakeShell(InteractiveShell):
    def __init__(self):
        self.magics_registered = None

    def register_magics(self, *magics):
        self.magics_registered = magics


def test_load_ipython_extension_registers_magics(monkeypatch):
    shell = FakeShell()

    monkeypatch.setattr(ipython_extension, "_load_css", lambda: None)

    ipython_extension.load_ipython_extension(shell)

    assert shell.magics_registered is not None
