from scrapers.base import BaseScraper
from bs4 import BeautifulSoup
import urllib.parse
import re

class CustomsScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="Customs Department (กรมศุลกากร)", base_url="https://www.customs.go.th")
        self.search_url = "https://www.customs.go.th/list_strc_download_date.php?show_search=1&ini_content=clearance&ini_menu=menu_public_relations_160421_02&lang=th&left_menu=menu_public_relations_160421_02_160421_01"

    def parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        table = soup.find('table', class_='table-hover')
        if not table:
            # Fallback to any table if class is missing
            table = soup.find('table')
            
        if not table:
            return []
            
        rows = table.find_all('tr')[1:] # Skip header
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 3:
                # 0: No, 1: Details, 2: Date, 3: Downloads
                link_tag = cols[1].find('a', href=True)
                if not link_tag:
                    continue
                    
                title = link_tag.get_text(strip=True)
                url = urllib.parse.urljoin(self.base_url, link_tag['href'])
                # ซ่อมแซมลิงก์ที่เว็บกรมศุลกากรส่งมาผิดพลาด (แปลง ¤t_id กลับเป็น &current_id)
                if "\u00a4t_id=" in url:
                    url = url.replace("\u00a4t_id=", "&current_id=")
                date_str = cols[2].get_text(strip=True)
                
                results.append({
                    "agency": "กรมศุลกากร",
                    "unit": "ศุลกากร",
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
