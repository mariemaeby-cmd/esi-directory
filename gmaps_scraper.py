import time
import pandas as pd
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

QUERY = "ESI Hospital India"
MAX_SCROLLS = 10

def scrape_google_maps(search_query: str):
    results = []

    with sync_playwright() as p:
        # Launch headless browser with anti-detection headers
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        stealth_sync(page)

        print(f"Navigating to Google Maps for '{search_query}'...")
        page.goto(f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}", timeout=60000)
        page.wait_for_selector('div[role="feed"]', timeout=30000)

        # Scroll the results pane to load dynamic cards
        feed = page.locator('div[role="feed"]')
        for _ in range(MAX_SCROLLS):
            page.evaluate('(el) => el.scrollTop = el.scrollHeight', feed.element_handle())
            time.sleep(2)

        # Extract details from cards
        cards = page.locator('div[role="article"]').all()
        print(f"Found {len(cards)} listings.")

        for card in cards:
            try:
                name = card.locator('.qBF1Pd').inner_text() if card.locator('.qBF1Pd').count() > 0 else "N/A"
                link = card.locator('a').first.get_attribute('href') if card.locator('a').count() > 0 else ""

                # Address / Category info in text snippet
                info_text = card.inner_text()

                results.append({
                    "name": name,
                    "info": info_text.replace("\n", " | "),
                    "url": link
                })
            except Exception:
                continue

        browser.close()

    df = pd.DataFrame(results)
    df.to_csv("gmaps_results.csv", index=False)
    print(f"Saved {len(results)} places to gmaps_results.csv")

if __name__ == "__main__":
    scrape_google_maps(QUERY)
  
