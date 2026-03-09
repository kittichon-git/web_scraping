from scrapers.base import BaseScraper
from bs4 import BeautifulSoup
import urllib.parse

class ThailandPostScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="Thailand Post", base_url="https://www.thailandpost.co.th/un/purchase_file_list/article/24")
        # Define search URL specifically
        self.search_url = "https://www.thailandpost.co.th/un/purchase_file_list/article/24"

    def parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        # Thailand Post uses 'table_default' class for their main list
        table = soup.find('table', class_='table_default')
        if not table:
            # Fallback for different page versions
            table = soup.find('table', class_='table')
            
        if not table:
            return []

        rows = table.find_all('tr')
        results = []
        
        for row in rows:
            cols = row.find_all('td')
            # Columns: 0: Ref No, 1: Subject, 2: Post Date, 3: Submission Date, 4: Download
            if len(cols) >= 5:
                ref_no = cols[0].text.strip()
                subject = cols[1].text.strip()
                date_str = cols[2].text.strip()
                
                # Check for header row
                if "ประกาศเลขที่" in ref_no or not subject:
                    continue
                
                # Link is in the 5th column icon
                link_tag = cols[4].find('a', href=True)
                detail_url = urllib.parse.urljoin(self.base_url, link_tag['href']) if link_tag else None
                
                # Use base class method for Thai date normalization
                sort_date = self.normalize_thai_date(date_str)
                
                results.append({
                    "agency": "ไปรษณีย์ไทย",
                    "unit": ref_no,
                    "title": subject,
                    "date": date_str,
                    "sort_date": sort_date,
                    "url": detail_url,
                    "source": self.name
                })
        return results

    def scrape(self, max_pages=1):
        all_results = []
        print(f"Scraping {self.name}...")
        
        # Initial page
        html = self.fetch(self.search_url)
        if html:
            page_results = self.parse(html)
            all_results.extend(page_results)
            
            # Simple pagination if max_pages > 1
            # Page 2: https://www.thailandpost.co.th/un/purchase_file_list/article/24/0/2
            if max_pages > 1:
                for p in range(2, max_pages + 1):
                    p_url = f"{self.search_url}/0/{p}"
                    p_html = self.fetch(p_url)
                    if p_html:
                        p_results = self.parse(p_html)
                        if not p_results: break # No more data
                        all_results.extend(p_results)
                    else:
                        break
                        
        return all_results
