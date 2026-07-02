from scrapers.base import BaseScraper
from bs4 import BeautifulSoup
import urllib.parse


class MEAScraper(BaseScraper):
    """การไฟฟ้านครหลวง (MEA) — card listing หน้าประกาศขายพัสดุเก่า.
    1 card = 1 รายการ, URL = หน้าประกาศ (ให้พนักงานเปิดดูเอง).
    """

    LIST_URL = "https://www.mea.or.th/public-relations/dispose-assets"

    def __init__(self):
        super().__init__(name="การไฟฟ้านครหลวง (MEA)", base_url="https://www.mea.or.th")

    def scrape(self, max_pages=1):
        print(f"Scraping {self.name}...")
        html = self.fetch(self.LIST_URL)
        if not html:
            print("  MEA: fetch failed")
            return []

        soup = BeautifulSoup(html, 'html.parser')
        results = []

        for card in soup.find_all(class_='card-item'):
            a_tag = card.find('a', href=True)
            if not a_tag or '/dispose-assets/' not in a_tag['href']:
                continue

            url   = urllib.parse.urljoin(self.base_url, a_tag['href'])
            h3    = card.find('h3')
            title = h3.get_text(strip=True) if h3 else a_tag.get('title', '').strip()
            if not title:
                continue

            date_p = card.find('p', class_='card-date')
            date   = " ".join(t.strip() for t in date_p.strings if t.strip()) if date_p else ""

            results.append({
                "agency":    "การไฟฟ้านครหลวง (MEA)",
                "unit":      "การไฟฟ้านครหลวง",
                "title":     title,
                "date":      date,
                "sort_date": self.normalize_thai_date(date),
                "url":       url,
                "source":    self.name,
                "status":    "ขายทอดตลาด",
            })

        print(f"  {self.name}: {len(results)} items")
        return results
