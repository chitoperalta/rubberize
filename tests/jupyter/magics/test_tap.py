# pylint: disable=all

import types
from textwrap import dedent

from IPython.core.interactiveshell import InteractiveShell

import rubberize.vendor.ast_comments as ast_c
from rubberize.jupyter.magics import tap


class FakeRunResult:
    def __init__(self, success=True):
        self.success = success


class FakeShell(InteractiveShell):
    def __init__(self, success=True):
        self.success = success
        self.ran = False

    def run_cell(self, cell):  # type: ignore
        self.ran = True
        return FakeRunResult(self.success)


# ------------
# %%tap magic
# ------------


def test_tap_renders(monkeypatch):
    calls = []

    monkeypatch.setattr(tap, "latex_from_ast", lambda tree, ns: ["LATEX"])
    monkeypatch.setattr(tap, "render", lambda latex, ns, grid=False: "<html>")
    monkeypatch.setattr(
        tap, "display_html", lambda html, raw=True: calls.append(html)
    )
    monkeypatch.setattr(tap, "parse_modifiers", lambda m: {})

    m = tap.TapMagics(shell=FakeShell())

    m.tap("", "a = 1", {})

    assert calls == ["<html>"]


def test_tap_dead_skips_execution(monkeypatch):
    calls = []

    monkeypatch.setattr(tap, "latex_from_ast", lambda tree, ns: ["LATEX"])
    monkeypatch.setattr(tap, "render", lambda latex, ns, grid=False: "<html>")
    monkeypatch.setattr(
        tap, "display_html", lambda html, raw=True: calls.append(html)
    )
    monkeypatch.setattr(tap, "parse_modifiers", lambda m: {})

    shell = FakeShell()

    m = tap.TapMagics(shell=shell)

    m.tap("--dead", "a = 1", {})

    assert shell.ran is False
    assert calls == ["<html>"]


def test_tap_execution_failure_stops_render(monkeypatch):
    calls = []

    monkeypatch.setattr(tap, "latex_from_ast", lambda tree, ns: ["LATEX"])
    monkeypatch.setattr(tap, "render", lambda latex, ns, grid=False: "<html>")
    monkeypatch.setattr(
        tap, "display_html", lambda html, raw=True: calls.append(html)
    )
    monkeypatch.setattr(tap, "parse_modifiers", lambda m: {})

    m = tap.TapMagics(shell=FakeShell(success=False))

    m.tap("", "a = 1", {})

    assert calls == []


def test_tap_html_flag_prints(monkeypatch, capsys):
    monkeypatch.setattr(tap, "latex_from_ast", lambda tree, ns: ["LATEX"])
    monkeypatch.setattr(tap, "render", lambda latex, ns, grid=False: "<html>")
    monkeypatch.setattr(tap, "display_html", lambda *args, **kwargs: None)
    monkeypatch.setattr(tap, "parse_modifiers", lambda m: {})

    m = tap.TapMagics(shell=FakeShell())

    m.tap("--html", "a = 1", {})

    out = capsys.readouterr().out
    assert "<html>" in out


def test_tap_hide_modifier(monkeypatch):
    called = False

    def fake_render(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(tap, "latex_from_ast", lambda tree, ns: ["LATEX"])
    monkeypatch.setattr(tap, "render", fake_render)
    monkeypatch.setattr(tap, "display_html", lambda *a, **k: None)
    monkeypatch.setattr(tap, "parse_modifiers", lambda m: {"hide": True})

    m = tap.TapMagics(shell=FakeShell())

    m.tap("", "a = 1", {})

    assert called is False


# ------------
# %%ast magic
# ------------


def test_ast_dump(monkeypatch, capsys):
    fake_stmt = types.SimpleNamespace(lineno=1)

    fake_tree = types.SimpleNamespace(body=[fake_stmt])

    monkeypatch.setattr(ast_c, "parse", lambda b, mode="exec": fake_tree)
    monkeypatch.setattr(ast_c, "dump", lambda *args, **kwargs: "AST_DUMP")

    m = tap.TapMagics(shell=FakeShell())

    m.ast("", "a = 1")

    out = capsys.readouterr().out
    assert "AST_DUMP" in out


def test_ast_dead_skips_execution(monkeypatch, capsys):
    import types

    fake_stmt = types.SimpleNamespace(lineno=1)
    fake_tree = types.SimpleNamespace(body=[fake_stmt])

    monkeypatch.setattr(ast_c, "parse", lambda b, mode="exec": fake_tree)
    monkeypatch.setattr(ast_c, "dump", lambda *a, **k: "AST")

    shell = FakeShell()

    m = tap.TapMagics(shell=shell)

    m.ast("--dead", "a = 1")

    assert shell.ran is False


# ----------------------
# _compute_block_starts
# ----------------------


def test_compute_block_starts_simple():
    src = dedent(
        """
        a = 1

        b = 2
        """
    )

    starts = tap._compute_block_starts(src)

    # "b = 2" line index
    assert starts == {3}


def test_compute_block_starts_top_level_only():
    src = dedent(
        """
        if True:
            a = 1

        b = 2
        """
    )

    starts = tap._compute_block_starts(src)

    # only "b = 2" starts a new block
    assert starts == {4}


def test_compute_block_starts_elif_not_split():
    src = dedent(
        """
        if x:
            a = 1

        elif y:
            b = 2
        """
    )

    starts = tap._compute_block_starts(src)

    assert starts == set()


def test_compute_block_starts_magic_lines_removed():
    src = dedent(
        """\
        %time

        a = 1

        b = 2
        """
    )

    starts = tap._compute_block_starts(src)

    # only split before "b = 2"
    assert starts == {4}
