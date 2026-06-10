from scrapers.base import BaseScraper
from bs4 import BeautifulSoup

class TreasuryScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="Treasury Department (กรมธนารักษ์)", base_url="https://www.treasury.go.th")
        self.search_url = (
            "https://www.treasury.go.th/th/procurement/bidding-news/department-bidding-news"
            "?search=%E0%B8%82%E0%B8%B2%E0%B8%A2%E0%B8%97%E0%B8%AD%E0%B8%94%E0%B8%95%E0%B8%A5%E0%B8%B2%E0%B8%94"
        )

    def parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        results = []

        # Each auction item is wrapped in div.block-layout-992002
        blocks = soup.find_all('div', class_='block-layout-992002')

        for block in blocks:
            # Title from <h2 class="h4"> (เว็บเปลี่ยนจาก <h4> เป็น <h2 class="h4">)
            h_el = block.find('h2', class_='h4') or block.find('h4')
            if not h_el:
                continue
            # strip img alt text — ใช้ strings แทน get_text เพื่อกรอง img
            title = ' '.join(s.strip() for s in h_el.strings if s.strip()).strip()

            # Detail page URL จาก <a> แรกภายใน h_el
            detail_a = h_el.find('a')
            if not detail_a:
                continue
            url = detail_a.get('href', '')

            # Date from <small class="thai-date" data-date="YYYY-MM-DD">
            date_el = block.find('small', class_='thai-date')
            sort_date = date_el.get('data-date', '') if date_el else ''

            results.append({
                "agency": "กรมธนารักษ์",
                "unit": "",
                "title": title,
                "date": sort_date,
                "sort_date": sort_date,
                "url": url,
                "source": self.name,
            })

        return results

    def scrape(self, max_pages=1):
        print(f"Scraping {self.name}...")
        html = self.fetch(self.search_url)
        if not html:
            return []
        return self.parse(html)
