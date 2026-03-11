# pylint: disable=all

import asyncio
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import rubberize.jupyter.export_notebook as export


# -----------------
# configure_logger
# -----------------


def test_configure_logger_sets_level():
    export.configure_logger(verbose=True)
    assert export.logger.level == export.logging.DEBUG

    export.configure_logger(verbose=False)
    assert export.logger.level == export.logging.INFO


# -------------------------
# export_notebook dispatch
# -------------------------


def test_export_notebook_dispatch_html(monkeypatch):
    called = {}

    def fake(path, output, *, show_input):
        called["ok"] = True

    monkeypatch.setattr(export, "export_notebook_to_html", fake)

    export.export_notebook("a.ipynb", fmt="html")

    assert called["ok"]


def test_export_notebook_dispatch_pdf(monkeypatch):
    called = {}

    def fake(path, output, *, show_input, render_timeout):
        called["ok"] = True

    monkeypatch.setattr(export, "export_notebook_to_pdf", fake)

    export.export_notebook("a.ipynb", fmt="pdf")

    assert called["ok"]


# ------------------------
# export_notebook_to_html
# ------------------------


def test_export_html_requires_jupyter(monkeypatch):
    monkeypatch.setattr(export.shutil, "which", lambda x: None)

    with pytest.raises(RuntimeError):
        export.export_notebook_to_html("a.ipynb")


def test_export_html_runs_nbconvert(monkeypatch, tmp_path):
    monkeypatch.setattr(export.shutil, "which", lambda x: "/usr/bin/jupyter")

    proc = MagicMock()
    proc.stdout = ["line\n"]
    proc.wait.return_value = 0

    class DummyPopen:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return proc

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(subprocess, "Popen", DummyPopen)

    nb = tmp_path / "test.ipynb"
    nb.write_text("{}")

    export.export_notebook_to_html(nb)


def test_export_html_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(export.shutil, "which", lambda x: "/usr/bin/jupyter")

    proc = MagicMock()
    proc.stdout = []
    proc.wait.return_value = 1

    class DummyPopen:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return proc

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(subprocess, "Popen", DummyPopen)

    nb = tmp_path / "test.ipynb"
    nb.write_text("{}")

    with pytest.raises(subprocess.CalledProcessError):
        export.export_notebook_to_html(nb)


# ----------------------------------------
# export_notebook_to_pdf directory export
# ----------------------------------------


def test_pdf_export_directory(monkeypatch, tmp_path):
    d = tmp_path / "nbs"
    d.mkdir()

    (d / "a.ipynb").write_text("{}")
    (d / "b.ipynb").write_text("{}")

    calls = []

    def fake_html(nb, tmp, *, show_input):
        Path(tmp).write_text("<html></html>")

    def fake_pdf(html, output, timeout):
        calls.append(output)

    monkeypatch.setattr(export, "export_notebook_to_html", fake_html)
    monkeypatch.setattr(export, "_html_to_pdf", fake_pdf)

    export.export_notebook_to_pdf(d)

    assert len(calls) == 2


# ----------------------------------------------
# export_notebook_to_pdf single notebook export
# ----------------------------------------------


def test_pdf_single_notebook(monkeypatch, tmp_path):
    nb = tmp_path / "a.ipynb"
    nb.write_text("{}")

    calls = []

    def fake_html(path, tmp, *, show_input):
        Path(tmp).write_text("<html></html>")

    def fake_pdf(path, output, timeout):
        calls.append(output)

    monkeypatch.setattr(export, "export_notebook_to_html", fake_html)
    monkeypatch.setattr(export, "_html_to_pdf", fake_pdf)

    export.export_notebook_to_pdf(nb)

    assert len(calls) == 1


# ----------------------
# _html_to_pdf fallback
# ----------------------


def test_html_to_pdf_sync_path(monkeypatch, tmp_path):
    called = {}

    def fake_sync(path, output, timeout):
        called["sync"] = True

    monkeypatch.setattr(export, "_html_to_pdf_sync", fake_sync)

    html = tmp_path / "a.html"
    html.write_text("x")

    export._html_to_pdf(html, tmp_path / "a.pdf", 100)

    assert called["sync"]


def test_html_to_pdf_async_fallback(monkeypatch, tmp_path):
    def fake_sync(*args, **kwargs):
        raise Exception()

    async def fake_async(path, output, timeout):
        return

    monkeypatch.setattr(export, "_html_to_pdf_sync", fake_sync)
    monkeypatch.setattr(export, "_html_to_pdf_async", fake_async)

    html = tmp_path / "a.html"
    html.write_text("x")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    export._html_to_pdf(html, tmp_path / "a.pdf", 100)

    loop.close()
