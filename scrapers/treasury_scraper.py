from scrapers.base import BaseScraper
from bs4 import BeautifulSoup
import urllib.parse
import re

class TreasuryScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="Treasury Department (กรมธนารักษ์)", base_url="https://www.treasury.go.th")
        self.search_url = "https://www.treasury.go.th/th/procurement-tendering/?keyword=%E0%B8%82%E0%B8%B2%E0%B8%A2%E0%B8%97%E0%B8%AD%E0%B8%94%E0%B8%95%E0%B8%A5%E0%B8%B2%E0%B8%94&site=%23any%23&news_group=%23any%23&category=&order=news"

    def parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Based on verified debug sessions
        items = soup.find_all('div', class_='boxlists')
        
        for item in items:
            title_tag = item.select_one('.name')
            time_container = item.select_one('.time')
            link_tag = item.select_one('.filedownloadlists a.name._blank')
            
            if title_tag:
                title = title_tag.get_text(strip=True)
                
                # Agency is in span.font-weight-light inside .time
                agency_tag = time_container.select_one('.font-weight-light') if time_container else None
                agency = agency_tag.get_text(strip=True) if agency_tag else "กรมธนารักษ์"
                
                # Date is in .time, after the dot/clock icon
                date_str = ""
                if time_container:
                    # Clear out the agency text to get the rest
                    time_text = time_container.get_text(" ", strip=True)
                    if agency:
                        time_text = time_text.replace(agency, "").strip()
                    
                    # Match date pattern: DD Month YYYY
                    date_match = re.search(r'\d{1,2}\s+[^\s\d]+\s+\d{4}', time_text)
                    if date_match:
                        date_str = date_match.group(0)
                
                sort_date = self.normalize_thai_date(date_str)
                
                url = urllib.parse.urljoin(self.base_url, link_tag['href']) if link_tag else None
                
                results.append({
                    "agency": "กรมธนารักษ์",
                    "unit": agency,
                    "title": title,
                    "date": date_str,
                    "sort_date": sort_date,
                    "status": "ประกาศขายทอดตลาด",
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
