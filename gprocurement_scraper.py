from scrapers.base import BaseScraper
from bs4 import BeautifulSoup
import urllib.parse
import time

class GProcurementScraper(BaseScraper):
    def __init__(self):
        # The URL is quite long and session-based, but we can try to use the base portal URL or the specific one provided.
        # However, many times these portal URLs expire. For the initial implementation, we use the provided URL.
        super().__init__(name="G-Procurement", base_url="https://www.gprocurement.go.th")
        self.search_url = "https://www.gprocurement.go.th/wps/portal/egp/auction/!ut/p/z1/04_Sj9CPykssy0xPLMnMz0vMAfIjo8zifQ3djQydnQ18_T3dzA0czU0NfANMLQ1cLc30w8EKDHAARwP9KGL041EQhd_4cP0oNCvCjM2AJgT4OvsHehgYOBtCFeAxoyA3NMIg01ERAP8P-8A!/dz/d5/L0lDUmlTUSEhL3dHa0FKRnNBLzROV3FpQSEhL3Ro/"

    def parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        # The subagent mentioned a table was found. We need to identify the exact table.
        # Based on typical e-GP pages, it might be a table with a certain class or just the first large table.
        table = soup.find('table') # We'll start with the first table and refine
        if not table:
            return []

        rows = table.find_all('tr')
        results = []
        for row in rows:
            cols = row.find_all('td')
            # Based on debug: 0: Book No, 1: Date, 2: Description, 3: Dept, 4: Download
            if len(cols) >= 5:
                book_no = cols[0].text.strip()
                date_str = cols[1].text.strip()
                subject = cols[2].text.strip()
                
                # Link is in the download column (index 4)
                link_tag = cols[4].find('a', href=True)
                detail_url = urllib.parse.urljoin(self.theme_base_url if hasattr(self, 'theme_base_url') else self.base_url, link_tag['href']) if link_tag else None

                # Extract date from Book No or Subject if Date column is empty
                import re
                date_pattern = r'\d{1,2}\s*(?:ม\.ค\.|ก\.พ\.|มี\.ค\.|เม\.ย\.|พ\.ค\.|มิ\.ย\.|ก\.ค\.|ส\.ค\.|ก\.ย\.|ต\.ค\.|พ\.ย\.|ธ\.ค\.|มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)\.?\s*\d{4}'
                
                if not date_str:
                    date_match = re.search(date_pattern, book_no)
                    if not date_match:
                        date_match = re.search(date_pattern, subject)
                    if date_match:
                        date_str = date_match.group(0)
                    else:
                        date_str = "ไม่ระบุวันที่"

                # Basic validation to avoid header row
                if "เลขที่หนังสือ" in book_no or not subject:
                    continue

                results.append({
                    "agency": "กรมบัญชีกลาง (e-GP)",
                    "unit": book_no, # Using Book No as unit/ref
                    "title": subject,
                    "date": date_str,
                    "sort_date": self.normalize_thai_date(date_str),
                    "url": detail_url,
                    "source": self.name
                })
        return results

    def scrape(self, max_pages=1):
        all_results = []
        print(f"Scraping {self.name}...")
        html = self.fetch(self.search_url)
        if not html:
            return []
            
        page_results = self.parse(html)
        all_results.extend(page_results)
        
        # Pagination for e-GP is complex due to JS/Portal state. 
        # For daily updates, the first page is usually sufficient.
        return all_results
