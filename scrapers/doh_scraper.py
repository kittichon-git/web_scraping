from scrapers.base import BaseScraper
from bs4 import BeautifulSoup
import time

class DOHScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="Department of Highways", base_url="https://www.doh.go.th")
        self.list_url = "https://www.doh.go.th/procurement-auction"

    def parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        section = soup.find('section', class_='my-5')
        if not section:
            return []
        table = section.find('table')
        if not table:
            return []

        results = []
        for row in table.find_all('tr')[1:]:  # skip header
            cols = row.find_all('td')
            if len(cols) < 3:
                continue

            date_str = cols[0].get_text(strip=True)   # DD/MM/YYYY (BE)
            title_cell = cols[1]
            unit = cols[2].get_text(strip=True) if len(cols) > 2 else ""

            a_tag = title_cell.find('a', href=True)
            if not a_tag:
                continue
            title = a_tag.get_text(strip=True)
            url = a_tag['href']
            if not url.startswith('http'):
                url = self.base_url + url

            results.append({
                "agency": "กรมทางหลวง",
                "unit": unit,
                "title": title,
                "date": date_str,
                "sort_date": self.normalize_thai_date(date_str),
                "url": url,
                "source": self.name,
            })
        return results

    def scrape(self, max_pages=5):
        all_results = []
        for page in range(1, max_pages + 1):
            print(f"Scraping {self.name} page {page}...")
            url = self.list_url if page == 1 else f"{self.list_url}?page={page}"
            html = self.fetch(url)
            if not html:
                break
            page_results = self.parse(html)
            if not page_results:
                break
            all_results.extend(page_results)
            if page < max_pages:
                time.sleep(1)
        return all_results
