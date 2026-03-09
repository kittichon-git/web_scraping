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
        
        # Find the table that contains "วันที่ลงประกาศ" and "หัวข้อ"
        # The data is managed by Kadence Blocks and DataTables, but content is in HTML
        table = None
        all_tables = soup.find_all('table')
        for t in all_tables:
            # Check headers or identifying text
            text_content = t.text
            if "วันที่ลงประกาศ" in text_content and "หัวข้อ" in text_content:
                # Target the tab "ประกาศขายพัสดุชำรุดเสื่อมสภาพ"
                # We can check the previous heading or just ensure "สำนักงานอัยการ" is in the rows
                table = t
                break
        
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
