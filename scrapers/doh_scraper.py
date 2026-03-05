from scrapers.base import BaseScraper
from bs4 import BeautifulSoup
import urllib.parse
import time

class DOHScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="Department of Highways", base_url="https://www.doh.go.th")
        self.search_url = f"{self.base_url}/project_detail"
        # Initial parameters for Auction (prcTypeSearch=13) and Announcement (step_id=6)
        self.params = {
            "year": "",
            "departmentSearch": "",
            "prcTypeSearch": "13",
            "step_id": "6",
            "textSearch": "",
            "start_date": "",
            "end_date": ""
        }

    def parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', class_='table')
        if not table:
            return []

        rows = table.find_all('tr')[1:]  # Skip header
        results = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 5:
                # Based on observation:
                # 0: No., 1: Unit, 2: Subject, 3: Date, 4: Budget, 5: Status, 6: Link
                unit = cols[1].text.strip()
                subject_cell = cols[2]
                subject = subject_cell.text.strip()
                date_str = cols[3].text.strip()
                
                # Link is usually in the last column or hidden in the subject
                link_tag = row.find('a', href=True)
                detail_url = urllib.parse.urljoin(self.base_url, link_tag['href']) if link_tag else None

                results.append({
                    "agency": "กรมทางหลวง",
                    "unit": unit,
                    "title": subject,
                    "date": date_str,
                    "sort_date": self.normalize_thai_date(date_str),
                    "url": detail_url,
                    "source": self.name
                })
        return results

    def scrape(self, max_pages=1):
        all_results = []
        for page in range(1, max_pages + 1):
            print(f"Scraping {self.name} page {page}...")
            params = self.params.copy()
            if page > 1:
                params["page"] = str(page)
            
            html = self.fetch(self.search_url, params=params)
            if not html:
                break
                
            page_results = self.parse(html)
            if not page_results:
                break
                
            all_results.extend(page_results)
            time.sleep(1) # Be polite
            
        return all_results
