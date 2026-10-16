"""Check the HTML poster's preview controls, PDF download and physical print size.

Serve site/ first, then run with --channel chrome or an installed Chromium.
No model API requests are made.
"""

import argparse
import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def check_pdf(content):
    """A download must be a one-page, 24 × 24-inch PDF with embedded fonts."""
    assert content.startswith(b"%PDF-")
    assert len(re.findall(rb"/Type\s*/Page\b", content)) == 1
    assert re.search(rb"/MediaBox\s*\[0 0 1728 1728\]", content)
    assert b"/FontFile2" in content


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8766/poster.html")
    parser.add_argument("--channel")
    args = parser.parse_args()
    cache = ROOT / ".cache"
    cache.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({"channel": args.channel} if args.channel else {}))
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(args.url, wait_until="load")
            assert page.locator(".experiment").count() == 8
            banks = ("framing", "framing", "demographics", "demographics_forced", "social_roles", "moral_machine", "edge_cases", "challenges")
            for index, bank in enumerate(banks, start=1):
                experiment = page.locator(f'.experiment[data-experiment="{index}"]')
                assert experiment.locator(".question-example").count() >= 1
                cells = {cell["id"]: cell for cell in json.loads((ROOT / f"datasets/{bank}/protocol.json").read_text())["cells"]}
                for example in experiment.locator("[data-source-cell]").all():
                    cell_id = example.get_attribute("data-source-cell")
                    assert cell_id in cells, (bank, cell_id)
                    if index == 8:
                        assert example.locator(".question-text").inner_text() in cells[cell_id]["followup"]
            assert page.locator(".question-text").evaluate_all(
                "examples => examples.every(p => parseFloat(getComputedStyle(p).fontSize) >= 24)"
            )
            assert "820" in page.locator(".procedure").inner_text()
            assert page.locator(".comparison-label strong").all_text_contents() == ["92/95", "61/95"]
            assert page.locator("table").count() == 0
            assert page.locator(".poster h2, .poster h3").evaluate_all(
                "headings => headings.every(h => getComputedStyle(h).color === 'rgb(0, 0, 0)')"
            )
            assert page.locator(".poster .metric").evaluate_all(
                "metrics => metrics.every(n => getComputedStyle(n).color === 'rgb(1, 33, 105)')"
            )
            assert page.locator(".poster .procedure strong:not(.metric)").evaluate_all(
                "labels => labels.every(label => getComputedStyle(label).color === 'rgb(0, 0, 0)')"
            )
            assert page.get_by_role("heading", name="Overall results and conclusions", exact=True).is_visible()
            conclusions = page.locator(".conclusion").inner_text()
            for finding in ("137/140", "240/240", "17/20", "60/60", "Stable choices still need explanation checks."):
                assert finding in conclusions, finding
            assert page.locator(".branch strong").all_text_contents() == ["20/20", "20/20", "20/20"]
            assert page.locator(".research-column p:not(.answer-count):not(.parameters):not(.example-label):not(.question-text)").evaluate_all(
                "paragraphs => paragraphs.every(p => parseFloat(getComputedStyle(p).fontSize) >= 25)"
            )
            assert page.locator(".poster h1, .poster h2, .poster h3, .poster p, .poster strong, .poster em, .poster svg text, button, .download").evaluate_all(
                "elements => elements.every(el => getComputedStyle(el).fontFamily.startsWith('\"Times New Roman\"'))"
            )
            assert page.locator(".research-column").count() == 3
            assert page.locator(".saving-row").count() == 5
            assert page.locator(".saving-label strong").all_text_contents() == ["20/20", "17/20", "20/20", "20/20", "10/20"]
            assert page.locator(".research-column").evaluate_all(
                "columns => columns.map(column => column.querySelectorAll('.experiment').length).join(',') === '4,3,1'"
            )
            assert page.locator(".poster").evaluate(
                "poster => getComputedStyle(poster).backgroundColor === 'rgb(255, 255, 255)'"
            )
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.get_by_role("button", name="View at full size").click()
            assert page.locator(".poster").bounding_box()["width"] == 2304
            assert page.get_by_role("button", name="Fit to window").get_attribute("aria-pressed") == "true"
            page.get_by_role("button", name="Fit to window").click()
            page.evaluate("window.print = () => { window.posterPrintRequested = true; }")
            page.get_by_role("button", name="Print / Save as PDF").click()
            assert page.evaluate("window.posterPrintRequested === true")
            with page.expect_download() as pending:
                page.get_by_role("link", name="Download PDF", exact=True).click()
            downloaded = cache / "poster-download-check.pdf"
            pending.value.save_as(str(downloaded))
            check_pdf(downloaded.read_bytes())
            assert downloaded.read_bytes() == (ROOT / "outputs/poster/class_fair_24x24.pdf").read_bytes()
            page.emulate_media(media="print")
            assert not page.locator(".controls").is_visible()
            assert not page.locator(".screen-note").is_visible()
            assert page.locator(".poster").bounding_box()["width"] == 2304
            assert page.locator(".poster").bounding_box()["height"] == 2304
            assert page.locator(".poster").evaluate("poster => poster.scrollHeight <= poster.clientHeight")
            assert page.locator(".research-columns").evaluate("grid => [...grid.children].every(column => column.getBoundingClientRect().bottom <= grid.getBoundingClientRect().bottom + 1)")
            exported = page.pdf(prefer_css_page_size=True, print_background=True, display_header_footer=False)
            check_pdf(exported)
            page.emulate_media(media="screen")
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_function("document.querySelector('.poster').getBoundingClientRect().width <= innerWidth")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert page.get_by_role("link", name="Download PDF", exact=True).is_visible()
            page.screenshot(path=str(cache / "poster-mobile.png"), full_page=True)
            page.goto((ROOT / "outputs/poster/class_fair_24x24.html").as_uri())
            assert page.locator(".experiment").count() == 8
            assert page.locator(".download").get_attribute("href") == "class_fair_24x24.pdf"
            assert not errors, errors
        finally:
            browser.close()
    print("Poster checks passed: desktop/mobile, full-size preview, print button, PDF download, three-column layout, sourced question examples, file opening and one-page 24-inch export.")


if __name__ == "__main__":
    main()
