# pylint: disable=all

from textwrap import dedent

from IPython.core.interactiveshell import InteractiveShell

from rubberize.jupyter.magics import tapload


class FakeShell(InteractiveShell):
    def __init__(self, src="a = 1"):
        self.src = src
        self.user_ns = {}
        self.next_input = None
        self.ask_called = False

    def find_user_code(self, arg, search_ns=False):  # type: ignore
        return self.src

    def set_next_input(self, contents, replace):  # type: ignore
        self.next_input = contents

    def ask_yes_no(self, *args, **kwargs):
        self.ask_called = True
        return True


# ---------------
# %tapload magic
# ---------------


def test_tapload_basic():
    shell = FakeShell("a = 1")

    m = tapload.TapLoadMagics(shell)
    m.tapload("file.py")

    assert shell.next_input.startswith("%%tap")
    assert "a = 1" in shell.next_input


def test_tapload_double_dash_args():
    shell = FakeShell("a = 1")

    m = tapload.TapLoadMagics(shell)
    m.tapload("file.py -- --dead")

    assert "%%tap --dead" in shell.next_input


def test_tapload_range():
    src = "a=1\nb=2\nc=3\n"
    shell = FakeShell(src)

    m = tapload.TapLoadMagics(shell)
    m.tapload("-r 2 file.py")

    assert "b=2" in shell.next_input
    assert "a=1" not in shell.next_input


def test_tapload_big_text_prompt():
    big = "x" * 210_000
    shell = FakeShell(big)

    m = tapload.TapLoadMagics(shell)
    m.tapload("file.py")

    assert shell.ask_called


def test_tapload_cancel(monkeypatch):
    class CancelShell(FakeShell):
        def ask_yes_no(self, *a, **k):  # type: ignore
            return False

    shell = CancelShell("x" * 210_000)

    m = tapload.TapLoadMagics(shell)
    m.tapload("file.py")

    assert shell.next_input is None


# ----------------
# %taploads magic
# ----------------


def test_taploads_requires_source(caplog):
    shell = FakeShell()

    m = tapload.TapLoadMagics(shell)
    m.taploads("")

    assert "SOURCE is required" in caplog.text


def test_taploads_conflict(caplog):
    shell = FakeShell()

    m = tapload.TapLoadMagics(shell)
    m.taploads("--next file.py")

    assert "Supply only SOURCE or --next" in caplog.text


def test_taploads_single_cell():
    src = dedent(
        """
        a = 1
        b = 2
        """
    )

    shell = FakeShell(src)

    m = tapload.TapLoadMagics(shell)
    m.taploads("file.py")

    assert "%%tap" in shell.next_input
    assert "_taploads_queue" not in shell.user_ns


def test_taploads_queue(monkeypatch):

    src = dedent(
        """
        # %%
        a = 1

        # %%
        b = 2
        """
    )

    shell = FakeShell(src)

    m = tapload.TapLoadMagics(shell)
    m.taploads("file.py")

    assert "_taploads_queue" in shell.user_ns
    assert len(shell.user_ns["_taploads_queue"]) == 1


def test_taploads_next():
    src = dedent(
        """
        # %%
        a = 1
        # %%
        b = 2
        """
    )

    shell = FakeShell(src)

    m = tapload.TapLoadMagics(shell)
    m.taploads("file.py")
    m.taploads("--next")

    assert "b = 2" in shell.next_input


def test_taploads_next_empty(caplog):
    shell = FakeShell()

    m = tapload.TapLoadMagics(shell)
    m.taploads("--next")

    assert "Nothing to continue" in caplog.text


def test_tln_alias(monkeypatch):
    shell = FakeShell()

    m = tapload.TapLoadMagics(shell)

    called = {}

    def fake(line):
        called["ok"] = True

    m.taploads = fake
    m.tln("")

    assert called["ok"]


# -------------------
# _split_double_dash
# -------------------


def test_split_double_dash_none():
    left, right = tapload._split_double_dash("file.py")
    assert left == "file.py"
    assert right == ""


def test_split_double_dash_with_args():
    left, right = tapload._split_double_dash("file.py -- -a -b")
    assert left == "file.py"
    assert right == "-a -b"


# ------------------------------------------
# _get_taploads_queue / _set_taploads_queue
# ------------------------------------------


def test_queue_set_and_get():
    shell = FakeShell()

    tapload._set_taploads_queue(shell, [("a", "b")])

    q = tapload._get_taploads_queue(shell)

    assert q == [("a", "b")]


def test_queue_empty():
    shell = FakeShell()

    q = tapload._get_taploads_queue(shell)

    assert q == []


# ------------------------------------------
# _render_taploads_chunk
# ------------------------------------------


def test_render_tap_chunk_default():
    out = tapload._render_taploads_chunk(
        ("", "a = 1"),
        "%taploads file",
        "",
    )

    assert "%%tap" in out
    assert "a = 1" in out


def test_render_tap_chunk_with_args():
    out = tapload._render_taploads_chunk(
        ("tap -q", "x=1"),
        "%taploads file",
        "",
    )

    assert "%%tap -q" in out


def test_render_markdown_chunk():
    out = tapload._render_taploads_chunk(
        ("[markdown]", "hello"),
        "%taploads file",
        "",
    )

    assert out.startswith("%%markdown")


def test_render_python_chunk():
    out = tapload._render_taploads_chunk(
        ("py", "x=1"),
        "%taploads file",
        "",
    )

    assert out.startswith("# %taploads")


# ------------------------------------------
# _split_percent_fmt
# ------------------------------------------


def test_split_percent_fmt_single():
    src = dedent(
        """
        a = 1
        b = 2
        """
    )

    chunks = tapload._split_percent_fmt(src)

    assert len(chunks) == 1
    assert chunks[0][1].strip().startswith("a")


def test_split_percent_fmt_multiple():
    src = dedent(
        """
        # %%
        a = 1

        # %%
        b = 2
        """
    )

    chunks = tapload._split_percent_fmt(src)

    assert len(chunks) == 2
    assert "a = 1" in chunks[0][1]
    assert "b = 2" in chunks[1][1]


def test_split_percent_fmt_marker_types():
    src = dedent(
        """
        # %% tap -q
        a = 1

        # %% [markdown]
        hello
        """
    )

    chunks = tapload._split_percent_fmt(src)

    assert chunks[0][0] == "tap -q"
    assert chunks[1][0] == "[markdown]"
