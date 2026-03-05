from scrapers.base import BaseScraper
import json
import urllib.parse
import re

class PRDScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="PRD (กรมประชาสัมพันธ์)", base_url="http://npnt.prd.go.th/centerweb/BidNews/BidNews")
        self.api_url = "http://npnt.prd.go.th/centerweb/BidNews/BidNewsGridData"

    def parse(self, data):
        results = []
        rows = data.get('rows', [])
        
        for row in rows:
            cell = row.get('cell', [])
            if len(cell) >= 6:
                # 0: ID
                # 1: Date (e.g., "4 มี.ค.2569")
                # 2: Org (Agency/Unit)
                # 3: NoRefer
                # 4: Type (e.g., "ขายทอดตลาด")
                # 5: Title/Detail
                
                news_id = cell[0]
                date_str = cell[1]
                agency_unit = cell[2]
                title = cell[5]
                
                # Link is http://npnt.prd.go.th/centerweb/BidNews/DetailBidNews?BN01_BidNewsID=ID
                url = f"http://npnt.prd.go.th/centerweb/BidNews/DetailBidNews?BN01_BidNewsID={news_id}"
                
                results.append({
                    "agency": "กรมประชาสัมพันธ์",
                    "unit": agency_unit,
                    "title": title.strip() if title else "ไม่มีหัวข้อ",
                    "date": date_str,
                    "sort_date": self.normalize_thai_date(date_str),
                    "url": url,
                    "source": self.name
                })
        return results

    def scrape(self, max_pages=1):
        print(f"Scraping {self.name}...")
        params = {
            "txtBidNewsDateSearch": "",
            "txtBidNewsEndDateSearch": "",
            "BN02_CatBidID": "3",  # ขายทอดตลาด
            "BN03_CatMaterialID": "",
            "BN01_FullText": "",
            "page": "1",
            "rows": "50", # Requested 50 items per page
            "sidx": "CreDate",
            "sord": "desc",
            "_search": "false"
        }
        
        headers = {
            "X-Requested-With": "XMLHttpRequest"
        }
        
        # Use fetch as base but we need to handle JSON. 
        # Actually fetch returns text, we can convert to JSON here.
        # But we need to use params. Base fetch uses GET.
        
        all_results = []
        # We only do 1 page for now since it already returns 50 items which is usually enough for daily updates
        full_url = f"{self.api_url}?{urllib.parse.urlencode(params)}"
        html = self.fetch(full_url)
        
        if not html:
            return []
            
        try:
            data = json.loads(html)
            all_results.extend(self.parse(data))
        except Exception as e:
            print(f"Error parsing JSON from {self.name}: {e}")
            
        return all_results

    def normalize_thai_date(self, date_str):
        # Specific fix for PRD format "4 มี.ค.2569" (no space between month and year)
        if date_str:
            # Add space before year if missing
            date_str = re.sub(r'(\d{4})$', r' \1', date_str)
        return super().normalize_thai_date(date_str)
