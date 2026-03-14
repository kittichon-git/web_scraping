from scrapers.base import BaseScraper
from bs4 import BeautifulSoup
import urllib.parse

class PWAScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="Provincial Waterworks Authority (PWA)", base_url="https://eprocurement.pwa.co.th")
        self.search_url = "https://eprocurement.pwa.co.th/public-auction/"

    def parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # PWA table structure
        table = soup.find('table')
        if not table:
            return []
            
        rows = table.find_all('tr')[1:] # Skip header
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 5:
                # 0: Agency, 1: Project No, 2: Title, 3: Status, 4: Date
                agency = cols[0].text.strip()
                project_no_tag = cols[1].find('a')
                project_no = project_no_tag.text.strip() if project_no_tag else cols[1].text.strip()
                
                title_tag = cols[2].find('a')
                title = title_tag.text.strip() if title_tag else cols[2].text.strip()
                
                # Link is usually in the project number or title
                detail_link = project_no_tag['href'] if project_no_tag else (title_tag['href'] if title_tag else None)
                url = urllib.parse.urljoin(self.base_url, detail_link) if detail_link else None
                
                status = cols[3].text.strip()
                date_str = cols[4].text.strip()
                
                # Normalize date
                sort_date = self.normalize_thai_date(date_str)
                
                results.append({
                    "agency": "การประปาส่วนภูมิภาค (PWA)",
                    "unit": f"{agency} {project_no}",
                    "title": title,
                    "date": date_str,
                    "sort_date": sort_date,
                    "status": status,
                    "url": url,
                    "source": self.name
                })
        return results

    def scrape(self, max_pages=1):
        print(f"Scraping {self.name}...")
        all_results = []
        
        for page in range(1, max_pages + 1):
            url = f"{self.search_url}page/{page}" if page > 1 else self.search_url
            # Fetch with base class method
            html = self.fetch(url)
            if not html:
                break
                
            page_results = self.parse(html)
            if not page_results:
                break
                
            all_results.extend(page_results)
            
        return all_results
