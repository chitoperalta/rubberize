# pylint: disable=all

from rubberize.jupyter.magics import export


class FakeShell:
    pass


# ---------------
# %%export magic
# ---------------


def test_export_pdf_default(monkeypatch):
    calls = {}

    def fake_logger(verbose):
        calls["verbose"] = verbose

    def fake_export(
        input_path, output_path, *, fmt, show_input, render_timeout
    ):
        calls["export"] = (
            input_path,
            output_path,
            fmt,
            show_input,
            render_timeout,
        )

    monkeypatch.setattr(export, "configure_logger", fake_logger)
    monkeypatch.setattr(export, "export_notebook", fake_export)

    m = export.ExportMagics(shell=FakeShell())

    m.export("notebook.ipynb")

    assert calls["verbose"] is False
    assert calls["export"] == ("notebook.ipynb", None, "pdf", False, 100)


def test_export_html(monkeypatch):
    calls = {}

    def fake_logger(verbose):
        calls["verbose"] = verbose

    def fake_export(
        input_path, output_path, *, fmt, show_input, render_timeout
    ):
        calls["fmt"] = fmt

    monkeypatch.setattr(export, "configure_logger", fake_logger)
    monkeypatch.setattr(export, "export_notebook", fake_export)

    m = export.ExportMagics(shell=FakeShell())

    m.export("notebook.ipynb --to html")

    assert calls["fmt"] == "html"


def test_export_with_output_path(monkeypatch):
    calls = {}

    def fake_logger(verbose):
        pass

    def fake_export(
        input_path, output_path, *, fmt, show_input, render_timeout
    ):
        calls["paths"] = (input_path, output_path)

    monkeypatch.setattr(export, "configure_logger", fake_logger)
    monkeypatch.setattr(export, "export_notebook", fake_export)

    m = export.ExportMagics(shell=FakeShell())

    m.export("nb.ipynb out.pdf")

    assert calls["paths"] == ("nb.ipynb", "out.pdf")


def test_export_show_input(monkeypatch):
    calls = {}

    def fake_logger(verbose):
        pass

    def fake_export(
        input_path, output_path, *, fmt, show_input, render_timeout
    ):
        calls["show"] = show_input

    monkeypatch.setattr(export, "configure_logger", fake_logger)
    monkeypatch.setattr(export, "export_notebook", fake_export)

    m = export.ExportMagics(shell=None)

    m.export("nb.ipynb --show-input")

    assert calls["show"] is True


def test_export_render_timeout(monkeypatch):
    calls = {}

    def fake_logger(verbose):
        pass

    def fake_export(
        input_path, output_path, *, fmt, show_input, render_timeout
    ):
        calls["timeout"] = render_timeout

    monkeypatch.setattr(export, "configure_logger", fake_logger)
    monkeypatch.setattr(export, "export_notebook", fake_export)

    m = export.ExportMagics(shell=None)

    m.export("nb.ipynb --render-timeout 500")

    assert calls["timeout"] == 500


def test_export_verbose(monkeypatch):
    calls = {}

    def fake_logger(verbose):
        calls["verbose"] = verbose

    def fake_export(*args, **kwargs):
        pass

    monkeypatch.setattr(export, "configure_logger", fake_logger)
    monkeypatch.setattr(export, "export_notebook", fake_export)

    m = export.ExportMagics(shell=None)

    m.export("nb.ipynb -v")

    assert calls["verbose"] is True
