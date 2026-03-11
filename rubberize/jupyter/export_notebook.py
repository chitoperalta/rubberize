"""Functions to export Jupyter notebooks."""

from __future__ import annotations

import asyncio
import logging
import subprocess
import shutil
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Literal


logger = logging.getLogger(__name__)


def configure_logger(verbose: bool) -> None:
    """Configure rubberize.logging"""

    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)

    logging.getLogger("asyncio").setLevel(logging.WARNING)


def export_notebook(
    path: str | Path,
    output: str | Path | None = None,
    *,
    fmt: Literal["pdf", "html"],
    show_input: bool = False,
    render_timeout: int = 100,
) -> None:
    """Export a Jupyter notebook to specified fmt.

    Args:
        path: The path to the notebook or directory to convert.
        output: Optional output path. If None, uses the input path but
            with file extension changed to .pdf, or if input path is a
            directory, the output will be saved in a new sibling dir
            named <directory>_pdf.
        fmt: The format to export to.
        show_input: If True, include input cells in the output.
        render_timeout: Time to wait for the page to render before PDF
            conversion, in milliseconds. Increase this value if the
            notebook has a lot of complex JavaScript output that needs
            more time to load.
    """

    if fmt == "html":
        return export_notebook_to_html(path, output, show_input=show_input)

    if fmt == "pdf":
        return export_notebook_to_pdf(
            path, output, show_input=show_input, render_timeout=render_timeout
        )

    return None


def export_notebook_to_html(
    path: str | Path,
    output: str | Path | None = None,
    *,
    show_input: bool = False,
) -> None:
    """Export a Jupyter notebook to HTML using nbconvert.

    Args:
        path: The path to the notebook to convert.
        output: Optional output path. If None, uses the input path but
            with file extension changed to .html.
        show_input: If True, include input cells in the output.
    """

    if shutil.which("jupyter") is None:
        raise RuntimeError("Jupyter nbconvert is required for HTML export")

    path = Path(path)
    output = Path(output) if output else path.with_suffix(".html")

    logger.debug("Exporting notebook to HTML")

    cmd = [
        "jupyter",
        "nbconvert",
        "--to",
        "html",
    ]

    if not show_input:
        cmd.append("--no-input")

    cmd += [
        str(path),
        "--output",
        output.stem,
        "--output-dir",
        str(output.parent),
    ]

    logger.debug("  Running command: %s", " ".join(cmd))

    try:
        with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        ) as proc:

            assert proc.stdout is not None

            for line in proc.stdout:
                logger.debug("  %s", line.rstrip())

            returncode = proc.wait()

            if returncode != 0:
                raise subprocess.CalledProcessError(returncode, cmd)

    except subprocess.CalledProcessError:
        logger.error("  jupyter nbconvert failed!")
        raise


def export_notebook_to_pdf(
    path: str | Path,
    output: str | Path | None = None,
    *,
    show_input: bool = False,
    render_timeout: int = 100,
) -> None:
    """Export a Jupyter notebook to PDF using nbconvert and Playwright.
    if a directory is supplied as input, all notebooks in the directory
    will be exported.

    Args:
        path: The path to the notebook or directory to convert.
        output: Optional output path. If None, uses the input path but
            with file extension changed to .pdf, or if input path is a
            directory, the output will be saved in a new sibling dir
            named {{dir}}_pdf.
        show_input: If True, include input cells in the output.
        render_timeout: Time to wait for the page to render before PDF
            conversion, in milliseconds. Increase this value if the
            notebook has a lot of complex JavaScript output that needs
            more time to load.
    """

    path = Path(path)

    if path.is_dir():
        output = Path(output) if output else path.parent / f"{path.name}_pdf"
        output.mkdir(parents=True, exist_ok=True)

        notebooks = list(path.glob("*.ipynb"))

        logger.info("Exporting %d notebooks in: %s", len(notebooks), path)

        if not notebooks:
            logger.warning("No notebooks found in %s", path.name)
            return

        for notebook in notebooks:
            output_pdf = output / notebook.with_suffix(".pdf").name
            export_notebook_to_pdf(
                notebook,
                output_pdf,
                show_input=show_input,
                render_timeout=render_timeout,
            )

        logger.info(
            "All notebooks in %s exported. PDFs saved to: %s",
            path.name,
            output,
        )

    elif path.is_file() and path.suffix == ".ipynb":
        output = Path(output) if output else path.with_suffix(".pdf")

        logger.info("Exporting notebook to PDF: %s", path)

        # create a temp file for the HTML output
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            export_notebook_to_html(path, tmp_path, show_input=show_input)
            _html_to_pdf(tmp_path, output, render_timeout)

            logger.info("PDF saved as: %s", output)
        finally:
            logger.debug("Temporary file deleted")

            tmp_path.unlink(missing_ok=True)

    else:
        logger.error("Invalid input: %s is not a notebook or directory.", path)


def _html_to_pdf(
    path: str | Path, output: str | Path | None, render_timeout: int
) -> None:
    """Export an HTML file to PDF."""

    path = Path(path)
    output = Path(output) if output else path.with_suffix(".pdf")

    logger.debug("Converting HTML to PDF")
    logger.debug("  Input HTML: %s", path)
    logger.debug("  Output PDF: %s", output)
    logger.debug("  Render timeout: %d ms", render_timeout)

    try:
        logger.debug("  Attempting synchronous Playwright conversion")

        _html_to_pdf_sync(path, output, render_timeout)
    except Exception:  # pylint: disable=broad-exception-caught
        logger.debug("  Sync Playwright failed, falling back to async path")

        if sys.platform.startswith("win"):
            # fix for windows (probably)
            asyncio.set_event_loop_policy(
                asyncio.WindowsSelectorEventLoopPolicy()  # type: ignore
            )

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            logger.debug("  Existing event loop detected")

            # Use nest_asyncio to allow nested loops (e.g. in Jupyter)
            try:
                # pylint: disable-next=import-outside-toplevel
                import nest_asyncio
            except ImportError as e:
                raise RuntimeError(
                    "Running PDF export inside Jupyter requires nest_asyncio"
                ) from e

            nest_asyncio.apply()

            new_loop = asyncio.new_event_loop()
            new_loop.run_until_complete(
                _html_to_pdf_async(path, output, render_timeout)
            )
            new_loop.close()

        else:
            loop.run_until_complete(
                _html_to_pdf_async(path, output, render_timeout)
            )


def _html_to_pdf_sync(
    path: Path, output: str | Path, render_timeout: int
) -> None:
    try:
        # pylint: disable-next=import-outside-toplevel
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise RuntimeError("Playwright is required for PDF export") from e

    with sync_playwright() as p:
        try:
            logger.debug("    Launching headless Chromium")

            browser = p.chromium.launch(headless=True)
        except Exception as e:
            raise RuntimeError(
                "    No suitable chromium executable found. "
                "Install using 'playwright install chromium'."
            ) from e

        try:
            url = f"file:///{path.resolve().as_posix()}"

            logger.debug("    Opening URL: %s", url)

            page = browser.new_page()
            page.set_default_timeout(0)  # Large notebooks might load for >30s
            page.emulate_media(media="print")
            page.wait_for_timeout(100)
            page.goto(url, wait_until="networkidle")

            logger.debug("    Waiting %d ms for page rendering", render_timeout)

            page.wait_for_timeout(render_timeout)

            logger.debug("    Generating PDF")

            page.pdf(path=output, prefer_css_page_size=True, outline=True)
        finally:
            logger.debug("    Closing browser")

            browser.close()


async def _html_to_pdf_async(
    path: Path, output: str | Path, render_timeout: int
) -> None:
    try:
        # pylint: disable-next=import-outside-toplevel
        from playwright.async_api import async_playwright
    except ImportError as e:
        raise RuntimeError("PDF export requires Playwright") from e

    async with async_playwright() as p:
        try:
            logger.debug("    Launching async Chromium instance")

            browser = await p.chromium.launch(headless=True)
        except Exception as e:
            raise RuntimeError(
                "    No suitable chromium executable found. "
                "Install using 'playwright install chromium'."
            ) from e

        try:
            url = f"file:///{path.resolve().as_posix()}"

            logger.debug("    Opening URL: %s", url)

            page = await browser.new_page()
            page.set_default_timeout(0)  # Large notebooks might load for >30s
            await page.emulate_media(media="print")
            await page.wait_for_timeout(100)
            await page.goto(url, wait_until="networkidle")

            logger.debug("    Waiting %d ms for page rendering", render_timeout)

            await page.wait_for_timeout(render_timeout)

            logger.debug("    Generating PDF")

            await page.pdf(path=output, prefer_css_page_size=True, outline=True)
        finally:
            logger.debug("    Closing browser")

            await browser.close()
