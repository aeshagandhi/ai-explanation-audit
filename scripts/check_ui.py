"""Check the saved scrolling demo at desktop and mobile sizes.

Serve site/ over HTTP before running. This uses recorded data and makes no
model API calls. Chrome can be selected with --channel chrome.
"""

import argparse
from playwright.sync_api import sync_playwright


def main():
    """Exercise framing controls, evidence visibility and mobile overflow."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8766")
    parser.add_argument("--channel")
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=args.channel)
        for width, height in [(1440, 1000), (390, 844)]:
            page = browser.new_page(
                viewport={"width": width, "height": height}, reduced_motion="reduce"
            )
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(args.url)
            page.wait_for_function(
                "document.querySelectorAll('#scenario option').length === 8"
            )
            assert page.locator("#metric-rows tr").count() == 16
            assert page.evaluate(
                "Array.from(document.images).every(image => image.complete && image.naturalWidth > 0)"
            )
            assert page.evaluate(
                "document.documentElement.scrollWidth <= innerWidth + 1"
            )
            for condition in ["standard", "symmetric_restatement"]:
                page.select_option("#condition", condition)
                page.select_option("#scenario", "equal_expected-forward")
                page.select_option("#frame", "death_first")
                if page.locator("#same").is_enabled():
                    page.click("#same")
                    assert page.locator("#reveal").is_visible()
                    page.select_option("#frame", "survival_first")
                    assert page.locator("#reveal").is_hidden()
            for anchor in ["question", "experiment", "results", "meaning"]:
                page.locator(f'nav a[href="#{anchor}"]').click()
                assert page.locator(f"#{anchor}").is_visible()
            for path in ["data/study.json", "data/trials.csv"]:
                assert page.request.get(args.url + "/" + path).status == 200
            assert not errors, errors
            page.screenshot(path=f".cache/framing-ui-{width}.png", full_page=True)
            page.close()
        browser.close()
    print("Desktop/mobile UI controls, anchors, downloads and layout passed.")


if __name__ == "__main__":
    main()
