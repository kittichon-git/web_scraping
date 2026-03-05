from scrapers.base import BaseScraper
from bs4 import BeautifulSoup
import urllib.parse
import re

class RevenueScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="Revenue Department (สรรพากร)", base_url="https://interapp4.rd.go.th/TPW/")
        self.search_url = "https://interapp4.rd.go.th/TPW/pages/show_Post2.php"

    def parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        rows = soup.find_all('tr', height="25")
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2:
                # 0: Date, 1: Title & Link, 2: Submission
                date_str = cols[0].get_text(strip=True)
                link_tag = cols[1].find('a', href=True)
                if not link_tag:
                    continue
                    
                title = link_tag.get_text(strip=True)
                url = urllib.parse.urljoin(self.search_url, link_tag['href'])
                
                results.append({
                    "agency": "กรมสรรพากร",
                    "unit": "สรรพากร",
                    "title": title,
                    "date": date_str,
                    "sort_date": self.normalize_thai_date(date_str),
                    "url": url,
                    "source": self.name
                })
        return results

    def scrape(self, max_pages=1):
        print(f"Scraping {self.name}...")
        html = self.fetch(self.search_url)
        if not html:
            return []
        return self.parse(html)
