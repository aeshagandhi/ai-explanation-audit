"""Exercise the saved study's story, interactions and saved data in a browser.

Serve site/ over HTTP first. Checks cover desktop and mobile, including repeated
answers, demographic swaps, challenge branches, supporting conditions and
an unavailable-data page.
No model API requests are made.
"""

import argparse
import re
from playwright.sync_api import sync_playwright


def check_wording(page):
    """Check prediction resets and the identical-question replay against known records."""
    page.click("#same")
    assert page.locator("#reveal").is_visible()
    assert "kept the same action" in page.locator("#reveal").inner_text()
    page.select_option("#frame", "death_first")
    assert page.locator("#reveal").is_hidden()
    page.click("#next-repeat")
    page.click("#next-repeat")
    assert "Saved answer 3 of 5" in page.locator("#repeat-answer").text_content()
    assert "STAY" in page.locator("#repeat-answer").text_content()
    assert "differs from answer 1" in page.locator("#repeat-answer").text_content()
    for _ in range(3):
        page.click("#next-repeat")
    assert "Saved answer 1 of 5" in page.locator("#repeat-answer").text_content()
    page.select_option("#scenario", "clear-forward")
    assert "SWERVE" in page.locator("#original-answer").inner_text()
    assert page.locator("#reveal").is_hidden()
    page.get_by_text("Full questions and study details", exact=True).click()
    for condition in ["standard", "symmetric_restatement"]:
        page.select_option("#condition", condition)
        page.click("#same")
        assert page.locator("#reveal").is_visible()
        page.select_option("#frame", "survival_first")
        assert page.locator("#reveal").is_hidden()
        page.select_option("#frame", "death_first")
    page.select_option("#condition", "standard")


def check_moral(page):
    """Main trade-offs must load, swap and reveal their saved answers."""
    assert page.locator("#people-bank").input_value() == "moral_machine"
    assert page.locator("#demographic-results tr").count() == 5
    assert (
        page.locator("#demographic-results").get_attribute("data-condition")
        == "moral_machine"
    )
    page.select_option("#demographic-attribute", "number")
    page.click("#guess-swerve")
    assert "five" in page.locator("#demographic-answer").inner_text().lower()
    assert "prediction matched" in page.locator("#demographic-answer").inner_text()
    page.click("#swap-people")
    assert page.locator("#demographic-answer").is_hidden()
    page.click("#guess-stay")
    assert "prediction matched" in page.locator("#demographic-answer").inner_text()
    page.get_by_text("Full questions, answers, and settings", exact=True).click()
    for attribute in ["number", "age", "role", "crossing", "conflict"]:
        page.select_option("#demographic-attribute", attribute)
        for order in ["stay_first", "swerve_first"]:
            page.select_option("#demographic-order", order)
            assert page.locator("#demographic-pair article").count() == 2
    assert page.locator(
        '#demographic-condition option[value="abstention_allowed"]'
    ).evaluate("option => option.disabled")
    page.get_by_text("Full questions, answers, and settings", exact=True).click()
    assert "Save the children" in page.locator("#reason-contrast").inner_text()
    assert "Avoid redirecting harm" in page.locator("#reason-contrast").inner_text()


def check_edges(page):
    """Edge-case controls reveal genuine saved results and preserve main results."""
    page.select_option("#people-bank", "edge_cases")
    assert page.locator("#demographic-results tr").count() == 2
    assert (
        page.locator("#demographic-results").get_attribute("data-condition")
        == "edge_cases"
    )
    assert "40 chose an action" in page.locator("#demographic-status").inner_text()
    page.select_option("#demographic-attribute", "close_count")
    page.click("#guess-stay")
    assert (
        "saves three 35-year-old pedestrians"
        in page.locator("#demographic-answer").inner_text()
    )
    page.click("#swap-people")
    assert page.locator("#demographic-answer").is_hidden()
    page.click("#guess-swerve")
    assert "prediction matched" in page.locator("#demographic-answer").inner_text()
    page.select_option("#demographic-attribute", "age_signal")
    page.click("#guess-stay")
    original = page.locator("#demographic-answer").inner_text()
    page.click("#swap-people")
    page.click("#guess-stay")
    swapped = page.locator("#demographic-answer").inner_text()
    assert original != swapped
    assert "chose STAY" in original and "chose STAY" in swapped
    page.get_by_text("Full questions, answers, and settings", exact=True).click()
    for attribute in ("close_count", "age_signal"):
        page.select_option("#demographic-attribute", attribute)
        for order in ("stay_first", "swerve_first"):
            page.select_option("#demographic-order", order)
            assert page.locator("#demographic-pair article").count() == 2
    page.locator("#demographics").screenshot(
        path=f".cache/story-edges-{page.viewport_size['width']}.png"
    )
    page.get_by_text("Full questions, answers, and settings", exact=True).click()
    page.select_option("#people-bank", "moral_machine")
    assert page.locator("#demographic-results tr").count() == 5


def check_demographics(page):
    """Verify that a path swap changes who survives while the saved action stays STAY."""
    page.select_option("#people-bank", "label_swaps")
    page.click("#guess-stay")
    assert (
        "saves the White pedestrian" in page.locator("#demographic-answer").inner_text()
    )
    page.click("#swap-people")
    assert page.locator("#demographic-answer").is_hidden()
    page.locator("#guess-stay").focus()
    page.keyboard.press("Enter")
    assert (
        "saves the Black pedestrian" in page.locator("#demographic-answer").inner_text()
    )
    page.locator("#demographics").screenshot(
        path=f".cache/story-swap-{page.viewport_size['width']}.png"
    )
    page.get_by_text("Full questions, answers, and settings", exact=True).click()
    for condition in ["forced_choice", "abstention_allowed"]:
        page.select_option("#demographic-condition", condition)
        assert (
            page.locator("#demographic-results").get_attribute("data-condition")
            == condition
        )
        for attribute in ["race", "gender", "age", "control"]:
            page.select_option("#demographic-attribute", attribute)
            for order in ["stay_first", "swerve_first"]:
                page.select_option("#demographic-order", order)
                assert page.locator("#demographic-pair article").count() == 2
            if attribute == "control":
                assert page.locator("#swap-people").is_disabled()
            else:
                assert page.locator("#swap-people").is_enabled()
    page.select_option("#demographic-attribute", "occupation")
    assert page.locator("#demographic-condition").input_value() == "forced_choice"
    assert page.locator(
        '#demographic-condition option[value="abstention_allowed"]'
    ).evaluate("option => option.disabled")
    assert "doctor" in page.locator("#demographic-pair").inner_text()
    page.click("#swap-people")
    assert page.locator("#demographic-answer").is_hidden()
    for attribute in ["occupation", "criminal_history", "social_control"]:
        page.select_option("#demographic-attribute", attribute)
        for order in ["stay_first", "swerve_first"]:
            page.select_option("#demographic-order", order)
            assert page.locator("#demographic-pair article").count() == 2
    page.select_option("#demographic-attribute", "race")
    assert page.locator(
        '#demographic-condition option[value="abstention_allowed"]'
    ).evaluate("option => !option.disabled")
    page.select_option("#demographic-condition", "abstention_allowed")
    page.select_option("#demographic-attribute", "race")
    page.select_option("#demographic-order", "stay_first")
    page.click("#guess-abstain")
    assert "declined to choose" in page.locator("#demographic-answer").inner_text()
    page.get_by_text("Earlier test: allowing the model to decline", exact=True).click()
    assert "137" in page.locator("#abstention-comparison").inner_text()
    page.select_option("#demographic-condition", "forced_choice")
    assert page.locator("#guess-abstain").is_hidden()
    assert page.locator("#demographic-answer").is_hidden()


def check_challenges(page):
    """Check independent conversation branches, repeat reveal and source context."""
    assert page.locator("#challenge-results tr").count() == 3
    assert "Every follow-up kept" in page.locator("#challenge-finding").inner_text()
    for scenario in ("number", "age", "role", "crossing", "conflict"):
        page.select_option("#challenge-scenario", scenario)
        for condition in ("argument", "disagreement", "neutral"):
            page.select_option("#challenge-condition", condition)
            assert "STAY kills" in page.locator("#challenge-initial").inner_text()
            assert "SWERVE kills" in page.locator("#challenge-initial").inner_text()
            assert page.locator("#challenge-answer").is_hidden()
            page.click("#challenge-keep")
            assert (
                "It kept its choice" in page.locator("#challenge-answer").inner_text()
            )
            assert (
                "prediction matched" in page.locator("#challenge-answer").inner_text()
            )
            page.click("#challenge-next")
            assert "Answer 2:" in page.locator("#challenge-answer").inner_text()
            page.click("#challenge-next")
            assert "Answer 1:" in page.locator("#challenge-answer").inner_text()
        page.click("#challenge-swap")
        assert page.locator("#challenge-answer").is_hidden()
        page.click("#challenge-keep")
        assert "It kept its choice" in page.locator("#challenge-answer").inner_text()
        page.click("#challenge-swap")
    page.select_option("#challenge-condition", "neutral")
    assert "Please choose" not in page.locator("#challenge-prompt").inner_text()
    page.select_option("#challenge-condition", "disagreement")
    assert "I disagree" in page.locator("#challenge-prompt").inner_text()
    page.get_by_text(
        "Challenge questions, repeated answers, and method", exact=True
    ).click()
    assert "Reconsider your earlier decision" in page.locator("#challenge-exact-prompt").inner_text()
    assert "Return only JSON" not in page.locator("#challenge-exact-prompt").inner_text()
    assert page.locator("#challenge-by-anchor tr").count() == 10
    page.get_by_text(
        "Challenge questions, repeated answers, and method", exact=True
    ).click()
    page.locator('nav a[href="#challenge"]').click()
    page.screenshot(path=f".cache/challenge-{page.viewport_size['width']}.png")


def check_layout(page, url, width):
    """Check required data, navigation, layout and absence of download links."""
    assert page.locator("#metric-rows tr").count() == 8
    assert page.locator("#explanation-checks tr").count() == 3
    assert page.locator("#explanation-annotations details").count() == 62
    assert (
        "62 explanations reviewed" in page.locator("#explanation-summary").inner_text()
    )
    assert page.locator("a[download], a[href^='data/']").count() == 0
    assert "24 × 24-inch poster (PDF)" not in page.locator("body").inner_text()
    assert "820 recorded" in page.locator("#study-status").inner_text()
    content = page.locator("body").text_content()
    for internal in ("README", "source-file hash", "source_sha256", "Return only JSON", "project-v2", "http.server", "datasets/"):
        assert internal not in content, internal
    assert not re.search(r"\b[\w-]+\.(?:json|csv|py)\b", content)
    assert page.locator("h1").count() == 1
    assert "Aesha Gandhi" in page.locator("footer").inner_text()
    assert page.locator("thead th").evaluate_all("headings => headings.every(h => h.scope === 'col')")
    assert page.evaluate("new Set([...document.querySelectorAll('[id]')].map(el => el.id)).size === document.querySelectorAll('[id]').length")
    assert page.evaluate(
        "Array.from(document.images).every(image => image.complete && image.naturalWidth > 0)"
    )
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    for anchor in [
        "question",
        "experiment",
        "demographics",
        "challenge",
        "meaning",
        "data",
    ]:
        page.locator(f'nav a[href="#{anchor}"]').click()
        assert page.locator(f"#{anchor}").is_visible()
        page.wait_for_function("id => document.querySelector(`nav a[href='#${id}']`).getAttribute('aria-current') === 'location'", arg=anchor)
    for path in [
        "study.json",
        "demographics.json",
        "demographics_forced.json",
        "demographics_social.json",
        "demographics_moral.json",
        "demographics_edges.json",
        "explanation_analysis.json",
        "challenges.json",
    ]:
        response = page.request.get(f"{url}/data/{path}")
        assert response.status == 200, path
    page.locator('nav a[href="#question"]').click()
    page.screenshot(path=f".cache/story-{width}.png", full_page=True)
    page.screenshot(path=f".cache/story-intro-{width}.png")


def check_load_failure(browser, url):
    """Missing evidence must show an actionable error without enabling fake results."""
    page = browser.new_page()
    page.route(
        "**/data/study.json", lambda route: route.fulfill(status=404, body="Missing")
    )
    page.goto(url)
    page.wait_for_function(
        "document.querySelector('#study-status').getAttribute('role') === 'alert'"
    )
    assert "refresh the page" in page.locator("#study-status").inner_text()
    assert "study.json" not in page.locator("#study-status").inner_text()
    assert page.locator("#same").is_disabled()
    assert page.locator("#guess-stay").is_disabled()
    assert page.locator("#next-repeat").is_disabled()
    assert page.locator("#challenge-keep").is_disabled()
    assert page.locator("main select").evaluate_all("controls => controls.every(control => control.disabled)")
    page.close()


def check_narrow_layout(browser, url):
    """Navigation and content must fit small phones, tablets and narrow desktops."""
    page = browser.new_page(reduced_motion="reduce")
    for width in (320, 768, 900, 1024):
        page.set_viewport_size({"width": width, "height": 900})
        page.goto(url)
        page.wait_for_function("document.querySelectorAll('#explanation-checks tr').length === 3")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), width
        for section in ("experiment", "demographics", "challenge", "meaning", "data"):
            page.locator(f'nav a[href="#{section}"]').click()
            page.wait_for_function("id => document.querySelector(`#${id}`).getBoundingClientRect().top >= document.querySelector('header').getBoundingClientRect().bottom - 1", arg=section)
            page.wait_for_function("id => document.querySelector(`nav a[href='#${id}']`).getAttribute('aria-current') === 'location'", arg=section)
        page.screenshot(path=f".cache/story-layout-{width}.png")
    page.close()


def main():
    """Run the same research-demo workflow at desktop and mobile widths."""
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
                "document.querySelectorAll('#explanation-checks tr').length === 3"
            )
            check_wording(page)
            check_moral(page)
            check_edges(page)
            check_demographics(page)
            check_challenges(page)
            check_layout(page, args.url, width)
            assert not errors, errors
            page.close()
        check_load_failure(browser, args.url)
        check_narrow_layout(browser, args.url)
        browser.close()
    print(
        "Desktop/mobile story, predictions, repeat replay, swaps, conditions, hidden download links and loading errors passed."
    )


if __name__ == "__main__":
    main()
