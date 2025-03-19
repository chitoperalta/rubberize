"""Functions to export IPython notebooks."""

import asyncio
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

import nest_asyncio
from playwright.sync_api import sync_playwright, Error
from playwright.async_api import async_playwright


_MATHJAX_WAITER = """
(function() {
    if (typeof MathJax !== 'undefined' && MathJax.Hub) {
        MathJax.Hub.Queue(["Typeset", MathJax.Hub]);

        return new Promise((resolve, reject) => {
            MathJax.Hub.Queue(() => {
                if (MathJax.Hub.Queue.length === 0) {
                    setTimeout(() => {
                        resolve(true);
                    }, 500);  // Wait for 500ms before resolve
                } else {
                    reject('MathJax is still rendering');
                }
            });
        });
    }
    return false;
})()
"""


def export_notebook_to_html(
    path: str | Path,
    output: Optional[str | Path] = None,
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
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _html_to_pdf(path: str | Path, output: Optional[str | Path] = None) -> None:
    """Export an HTML file to PDF.

    Use Playwright to open the HTML file, wait for MathJax to render,
    and print it to PDF.
    """

    path = Path(path)
    output = Path(output) if output else path.with_suffix(".pdf")

    try:
        _html_to_pdf_sync(path, output)
    except Error:
        if sys.platform.startswith("win"):
            # Fix for windows, probably.
            asyncio.set_event_loop_policy(
                asyncio.WindowsSelectorEventLoopPolicy()  # type: ignore
            )
        loop = asyncio.get_running_loop()
        if loop.is_running():
            # Use nest_asyncio to allow nested loops (e.g. in Jupyter)
            nest_asyncio.apply()
            new_loop = asyncio.new_event_loop()
            new_loop.run_until_complete(_html_to_pdf_async(path, output))
            new_loop.close()
        else:
            loop.run_until_complete(_html_to_pdf_async(path, output))


def _html_to_pdf_sync(path: Path, output: str | Path) -> None:
    """Sync version of Playwright routine."""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(f"file:///{path.resolve().as_posix()}")
            page.wait_for_function(_MATHJAX_WAITER)
            page.pdf(path=output, prefer_css_page_size=True, outline=True)
        finally:
            browser.close()


async def _html_to_pdf_async(path: Path, output: str | Path) -> None:
    """Async version of Playwright routine."""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(f"file:///{path.resolve().as_posix()}")
            await page.wait_for_function(_MATHJAX_WAITER)
            await page.pdf(path=output, prefer_css_page_size=True, outline=True)
        finally:
            await browser.close()


def export_notebook_to_pdf(
    path: str | Path,
    output: Optional[str | Path] = None,
    *,
    no_input: bool = True,
) -> None:
    """Export a Jupyter notebook to PDF using nbconvert and Playwright.
    if a directory is supplied as input, all notebooks in the directory
    will be exported.

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
            output_pdf = output / notebook.with_suffix(".pdf").name
            export_notebook_to_pdf(notebook, output_pdf, no_input=no_input)

        print(
            f"\nAll notebooks  in {path.name} converted."
            f"PDFs saved to: {output}"
        )

    elif path.is_file() and path.suffix == ".ipynb":
        # Handle single notebook file
        output = Path(output) if output else path.with_suffix(".pdf")

        print(f"Converting: {path}")

        # Create a temp file for the HTML output
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            export_notebook_to_html(path, tmp_path, no_input=no_input)
            _html_to_pdf(tmp_path, output)
            print(f"PDF saved as: {output}")
        finally:
            # Ensure deletion of temp file
            tmp_path.unlink(missing_ok=True)

    else:
        print(f"Invalid input: {path} is not a notebook or directory.")
