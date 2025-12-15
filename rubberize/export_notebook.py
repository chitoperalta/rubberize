"""Functions to export IPython notebooks."""

import subprocess
from pathlib import Path


def export_notebook_to_html(
    path: str | Path,
    output: str | Path | None = None,
    *,
    no_input: bool = True,
) -> None:
    """Export a Jupyter notebook to HTML using `nbconvert`.

    Args:
        path: The path to the notebook to convert.
        output: Optional output path. If `None`, uses the input path but
            with file extension changed to `.html`.
        no_input: Whether to exclude input cells in the output. Defaults
            to `True`.
    """

    path = Path(path)
    output = Path(output) if output else path.with_suffix(".html")

    print(f"Exporting: {path}")

    subprocess.run(
        [
            "jupyter",
            "nbconvert",
            "--to",
            "html",
            "--no-input" if no_input else "",
            str(path),
            "--output",
            str(output),
        ],
        check=True,
    )

    print(f"Done: {output}.html")


def export_notebook_to_pdf(
    path: str | Path,
    output: str | Path | None = None,
    *,
    no_input: bool = True,
) -> None:
    """Export a Jupyter notebook to PDF (webpdf) using `nbconvert`.

    Args:
        path: The path to the notebook or directory to convert.
        output: Optional output path. If `None`, uses the input path but
            with file extension changed to `.pdf`, or if input path is a
            directory, the output will be saved in a new sibling dir
            named `{{dir}}_pdf`.
        no_input: Whether to exclude input cells in the output. Defaults
            to `True`.
    """

    path = Path(path)

    if path.is_dir():
        output = Path(output) if output else path.parent / f"{path.name}_pdf"
        output.mkdir(parents=True, exist_ok=True)

        notebooks = list(path.glob("*.ipynb"))
        if not notebooks:
            print(f"No notebooks found in {path.name}")
            return

        for notebook in notebooks:
            output_pdf = output / notebook.stem
            export_notebook_to_pdf(notebook, output_pdf, no_input=no_input)

        print(f"Finished exporting all notebooks.")

    elif path.is_file() and path.suffix == ".ipynb":
        # Handle single notebook file
        output = Path(output) if output else path.parent / path.stem
        print(f"Exporting: {path}")

        subprocess.run(
            [
                "jupyter",
                "nbconvert",
                "--to",
                "webpdf",
                "--no-input" if no_input else "",
                str(path),
                "--output",
                str(output),
            ],
            check=True,
        )

        print(f"Done: {output}.pdf")

    else:
        print(f"Invalid input: {path} is not a notebook or directory.")
