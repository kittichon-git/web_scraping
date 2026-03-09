import requests
from bs4 import BeautifulSoup
import re
from .base import BaseScraper

class AGOScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            name="Office of the Attorney General (AGO)",
            base_url="https://www.ago.go.th/procurement/"
        )

    def parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        
        # We need the table under the "ประกาศขายพัสดุชำรุดเสื่อมสภาพ" heading
        # Find the h6 that contains "ประกาศขายพัสดุ"
        target_section = None
        for h6 in soup.find_all('h6'):
            if "ประกาศขายพัสดุ" in h6.text:
                # Found the right heading - the table is nearby
                # Walk up to the tab container, then find the table in it
                container = h6.find_parent('div')
                while container:
                    table = container.find('table')
                    if table and "วันที่ลงประกาศ" in table.text:
                        target_section = table
                        break
                    container = container.find_parent('div')
                if target_section:
                    break
        
        table = target_section
        
        if not table:
            return []
        
        tbody = table.find('tbody')
        rows = tbody.find_all('tr') if tbody else table.find_all('tr')
        results = []
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2:
                # Column 0: Date (Thai BE)
                date_val = cols[0].get_text(strip=True)
                
                # Column 1: Title and Link
                title_link = cols[1].find('a')
                if title_link:
                    title = title_link.get_text(strip=True)
                    url = title_link.get('href', '')
                    
                    if not url.startswith('http'):
                        if url.startswith('/'):
                            url = "https://www.ago.go.th" + url
                        else:
                            url = self.base_url + url

                    results.append({
                        "agency": "สำนักงานอัยการสูงสุด",
                        "unit": "",
                        "title": title,
                        "date": date_val,
                        "sort_date": self.normalize_thai_date(date_val),
                        "url": url,
                        "source": self.name
                    })
        
        return results

    def scrape(self, **kwargs):
        print(f"Scraping {self.name}...")
        html = self.fetch(self.base_url)
        if html:
            return self.parse(html)
        return []
