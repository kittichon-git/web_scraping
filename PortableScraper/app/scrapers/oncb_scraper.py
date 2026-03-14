from scrapers.base import BaseScraper
from bs4 import BeautifulSoup
import urllib.parse
import re
from datetime import datetime

class ONCBScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="ONCB (ปปส.)", base_url="https://www.oncb.go.th")
        self.search_url = "https://www.oncb.go.th/auction?group=auction&limit=100&keywords=&department=&order=publishDate_Desc&publish-date="

    def parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # 1. Check for "Latest" cards (seen in screenshot)
        cards = soup.find_all('div', class_=re.compile(r'card|item|news'))
        
        # If no explicit cards, look for the title tags directly
        # The browser subagent found a[href^="/auction/"]
        potential_items = soup.find_all('a', href=re.compile(r'/auction/\d+'))
        
        for link in potential_items:
            title = link.get_text(strip=True)
            if not title or len(title) < 5:
                # Try to find a wrapper or parent with text
                title = link.get('title') or ""
                if not title:
                    parent_text = link.parent.get_text(strip=True)
                    if len(parent_text) > 10:
                        title = parent_text
            
            if not title:
                continue
                
            url = urllib.parse.urljoin(self.base_url, link['href'])
            
            # Look for date in sibling or parent
            # Date format: 24 ก.พ. 2569 14:07 น.
            date_pattern = r'\d{1,2}\s+(?:ม\.ค\.|ก\.พ\.|มี\.ค\.|เม\.ย\.|พ\.ค\.|มิ\.ย\.|ก\.ค\.|ส\.ค\.|ก\.ย\.|ต\.ค\.|พ\.ย\.|ธ\.ค\.|มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)\s+\d{4}'
            
            search_area = link.parent.get_text(separator=' ', strip=True)
            date_match = re.search(date_pattern, search_area)
            
            if not date_match and link.parent.parent:
                search_area = link.parent.parent.get_text(separator=' ', strip=True)
                date_match = re.search(date_pattern, search_area)
            
            date_str = date_match.group(0) if date_match else "ไม่ระบุวันที่"
            sort_date = self.normalize_thai_date(date_str)

            # Avoid duplicates
            if any(r['url'] == url for r in results):
                continue

            results.append({
                "agency": "สำนักงาน ป.ป.ส.",
                "unit": "ปปส.",
                "title": title,
                "date": date_str,
                "sort_date": sort_date,
                "url": url,
                "source": self.name
            })
            
        # Sort results by sort_date descending as requested by user
        results.sort(key=lambda x: x['sort_date'], reverse=True)
        return results

    def scrape(self, max_pages=1):
        all_results = []
        print(f"Scraping {self.name}...")
        html = self.fetch(self.search_url)
        if not html:
            return []
            
        page_results = self.parse(html)
        all_results.extend(page_results)
        
        return all_results
