from scrapers.base import BaseScraper
from bs4 import BeautifulSoup
import requests
import urllib3

urllib3.disable_warnings()

_LISTING_URL = (
    "https://md.go.th/category/procurement-news/"
    "%e0%b8%9b%e0%b8%a3%e0%b8%b0%e0%b8%81%e0%b8%b2%e0%b8%a8"
    "%e0%b8%82%e0%b8%b2%e0%b8%a2%e0%b8%97%e0%b8%ad%e0%b8%94"
    "%e0%b8%95%e0%b8%a5%e0%b8%b2%e0%b8%94/"
)


class MDScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="กรมเจ้าท่า (MD)", base_url="https://md.go.th")

    def scrape(self, max_pages=5):
        print(f"Scraping {self.name}...")
        results = []

        for page in range(1, max_pages + 1):
            url = _LISTING_URL if page == 1 else f"{_LISTING_URL}page/{page}/"
            try:
                r = requests.get(url, headers=self.headers, timeout=30, verify=False)
                if r.status_code == 404:
                    break
                r.raise_for_status()
            except Exception as e:
                print(f"  Error page {page}: {e}")
                break

            soup = BeautifulSoup(r.text, "html.parser")
            container = soup.select_one("div.content-post_box")
            if not container:
                break

            articles = container.select("article.card-list_terms")
            if not articles:
                break

            for article in articles:
                a_tag = article.select_one("div.box-title a")
                if not a_tag:
                    continue
                item_url = a_tag.get("href", "").strip()
                h3 = a_tag.select_one("h3.post-title")
                title = h3.get_text(strip=True) if h3 else a_tag.get_text(strip=True)

                day_span = article.select_one("span.day")
                date_str = day_span.get_text(strip=True) if day_span else ""

                results.append({
                    "agency": "กรมเจ้าท่า (MD)",
                    "unit": "กรมเจ้าท่า",
                    "title": title,
                    "date": date_str,
                    "sort_date": self.normalize_thai_date(date_str),
                    "url": item_url,
                    "source": self.name,
                    "status": "ขายทอดตลาด",
                })

        print(f"  {self.name}: {len(results)} items")
        return results


if __name__ == "__main__":
    scraper = MDScraper()
    items = scraper.scrape(max_pages=3)
    for i, it in enumerate(items, 1):
        print(f"{i}. [{it['date']}] {it['title'][:60]}")
        print(f"   {it['url']}")
