from scrapers.base import BaseScraper
from bs4 import BeautifulSoup
import urllib.parse
import re

class PEAScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="Provincial Electricity Authority (PEA)", base_url="https://bidding.pea.co.th")
        self.search_url = "https://bidding.pea.co.th/asset-auctions"
        # PEA often requires more browser-like headers
        self.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'th,en-US;q=0.9,en;q=0.8',
            'Referer': 'https://bidding.pea.co.th/',
        })

    def parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        table = soup.find('table')
        if not table:
            return []
            
        rows = table.find_all('tr')[1:] # Skip header
        for row in rows:
            cols = row.find_all(['td', 'th'])
            if len(cols) >= 3:
                # 0: Ref No, 1: Subject, 2: Dates, 3: Docs
                ref_text = cols[0].text.strip()
                subject = cols[1].text.strip()
                date_info = cols[2].text.strip().replace('\n', ' ')
                
                # Link: Usually in Col 1 as a detail page or Col 3 as PDF
                detail_link_tag = cols[1].find('a', href=True) or cols[3].find('a', href=True)
                url = urllib.parse.urljoin(self.base_url, detail_link_tag['href']) if detail_link_tag else None
                
                # Date pattern
                date_pattern = r'\d{1,2}\s*(?:ม\.ค\.|ก\.พ\.|มี\.ค\.|เม\.ย\.|พ\.ค\.|มิ\.ย\.|ก\.ค\.|ส\.ค\.|ก\.ย\.|ต\.ค\.|พ\.ย\.|ธ\.ค\.|มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)\.?\s*\d{4}'
                
                # Check Ref Text first (e.g. "ลว. 4 มี.ค.2569")
                date_match = re.search(date_pattern, ref_text)
                if not date_match:
                    # Check date_info
                    date_match = re.search(date_pattern, date_info)
                
                first_date = date_match.group(0) if date_match else "ไม่ระบุวันที่"
                
                results.append({
                    "agency": "การไฟฟ้าส่วนภูมิภาค (PEA)",
                    "unit": ref_text,
                    "title": subject,
                    "date": date_info if "ไม่ระบุ" not in first_date else ref_text,
                    "sort_date": self.normalize_thai_date(first_date if "ไม่ระบุ" not in first_date else None),
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
