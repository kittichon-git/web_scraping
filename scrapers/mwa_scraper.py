from scrapers.base import BaseScraper
from bs4 import BeautifulSoup
import datetime

BASE_URL   = "https://www.mwa.co.th"
SEARCH_P1  = BASE_URL + "/?s=%E0%B8%82%E0%B8%B2%E0%B8%A2%E0%B8%A7%E0%B8%B1%E0%B8%AA%E0%B8%94%E0%B8%B8"
SEARCH_PN  = BASE_URL + "/?query-999-page={page}&month&year&order=desc&s=%E0%B8%82%E0%B8%B2%E0%B8%A2%E0%B8%A7%E0%B8%B1%E0%B8%AA%E0%B8%94%E0%B8%B8&lang=th&action=list_of_file"


class MWAScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="การประปานครหลวง (MWA)", base_url=BASE_URL)

    # ── BaseScraper interface (ไม่ใช้ fetch/parse เพราะต้องใช้ Playwright) ──
    def parse(self, html):
        return []

    def _parse_page(self, html: str) -> list:
        soup = BeautifulSoup(html, "html.parser")
        container = soup.find(class_="lof-list")
        if not container:
            return []

        today = datetime.date.today()
        results = []
        for li in container.find_all("li", class_=lambda c: c and "wp-block-post" in c):
            h2 = li.find("h2")
            a  = li.find("a", class_="wp-block-read-more")
            if not h2 or not a:
                continue

            title = h2.get_text(strip=True)
            url   = a.get("href", "").strip()
            if not url or not title:
                continue

            results.append({
                "agency":    "การประปานครหลวง (MWA)",
                "unit":      "กปน.",
                "title":     title,
                "date":      today.strftime("%d/%m/%Y"),
                "sort_date": today.strftime("%Y-%m-%d"),
                "url":       url,
                "source":    self.name,
                "status":    "ประกาศขายทอดตลาด",
            })
        return results

    def scrape(self, max_pages=2):
        from playwright.sync_api import sync_playwright

        print(f"Scraping {self.name}...")
        all_results = []
        seen_urls   = set()

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page    = browser.new_page(
                user_agent=self.headers["User-Agent"]
            )

            for p in range(1, max_pages + 1):
                url = SEARCH_P1 if p == 1 else SEARCH_PN.format(page=p)

                print(f"  หน้า {p}/{max_pages}...")
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_selector("ul.lof-list", timeout=15000)
                    page.wait_for_timeout(1500)
                except Exception as e:
                    print(f"  ⚠️ โหลดหน้า {p} ไม่ได้: {e}")
                    break

                items = self._parse_page(page.content())
                if not items:
                    print(f"  ⚠️ ไม่พบรายการในหน้า {p} — หยุด")
                    break

                new = 0
                for item in items:
                    if item["url"] not in seen_urls:
                        seen_urls.add(item["url"])
                        all_results.append(item)
                        new += 1
                print(f"  พบ {new} รายการใหม่ (รวม {len(all_results)})")

            browser.close()

        return all_results
