from scrapers.base import BaseScraper
from bs4 import BeautifulSoup
import urllib.parse
import re

class FIOScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="Forest Industry Organization (ออป.)", base_url="https://www.fio.co.th")
        self.urls = [
            "https://www.fio.co.th/th/listAll/pcm?gid=41",
            "https://www.fio.co.th/th/listAll/pcm?gid=40"
        ]

    def parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        items = soup.find_all('li', {'data-aos': 'fade-up'})
        for item in items:
            link_tag = item.find('a', class_='link wrapper')
            if not link_tag:
                continue
                
            title = link_tag.get('title') or link_tag.find('h2', class_='desc').get_text(strip=True)
            url = urllib.parse.urljoin(self.base_url, link_tag['href'])
            
            # Date is in <div class="action"><small class="txt">...<br>Date</small></div>
            action_div = item.find('div', class_='action')
            date_str = "ไม่ระบุวันที่"
            if action_div:
                txt = action_div.get_text(separator='|', strip=True)
                # Split by | and get the last part which is usually the date
                parts = [p.strip() for p in txt.split('|') if p.strip()]
                if parts:
                    date_str = parts[-1]
            
            results.append({
                "agency": "องค์การอุตสาหกรรมป่าไม้ (ออป.)",
                "unit": "ออป.",
                "title": title,
                "date": date_str,
                "sort_date": self.normalize_thai_date(date_str),
                "url": url,
                "source": self.name
            })
        return results

    def scrape(self, max_pages=1):
        all_results = []
        for url in self.urls:
            print(f"Scraping {self.name} category: {url.split('=')[-1]}...")
            html = self.fetch(url)
            if html:
                all_results.extend(self.parse(html))
        return all_results
