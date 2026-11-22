"""Visit the live app in a real browser so Streamlit Community Cloud doesn't put it to sleep.

Community Cloud hibernates apps with no visitors for 12 hours. A scheduled GitHub Action runs this
every few hours: it opens the app, clicks "Yes, get this app back up!" if the app is asleep, and
checks that the FarmFit page actually loads. Exits 1 if it doesn't, so the failed run shows up in GitHub.
"""

import os
import sys

from playwright.sync_api import sync_playwright

URL = os.environ.get("APP_URL", "https://hurricanetoharvest.streamlit.app/?farm=trinidad")
WAKE = "Yes, get this app back up"


def app_text(page):
    texts = []
    for frame in page.frames:
        try:
            texts.append(frame.inner_text("body", timeout=2000))
        except Exception:  # noqa: BLE001
            pass
    return "\n".join(texts)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(URL, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(15_000)
        woke = False
        button = page.get_by_role("button", name=WAKE)
        if button.count():
            print("App was asleep: waking it up")
            button.first.click()
            woke = True
        for _ in range(24):  # up to about 4 minutes for a cold start
            text = app_text(page)
            if "Plant now, or wait?" in text or "FarmFit" in text:
                print("App is awake" + (" (woken from sleep)" if woke else ""))
                browser.close()
                return 0
            page.wait_for_timeout(10_000)
        page.screenshot(path="keep_awake_failure.png", full_page=True)
        print("App did not load. Page text was:\n" + app_text(page)[:1500])
        browser.close()
        return 1


if __name__ == "__main__":
    sys.exit(main())
