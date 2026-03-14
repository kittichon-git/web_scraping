from scrapers.base import BaseScraper
import json
import urllib3

# Suppress insecure request warnings for RID API
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class RIDScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="Royal Irrigation Department (RID)", base_url="https://egp.rid.go.th")
        # Direct API endpoint found during research
        self.api_url = "https://pms.rid.go.th:4001/api/egp_announce"

    def scrape(self, max_pages=1):
        print(f"Scraping {self.name} via API...")
        all_results = []
        
        for page in range(max_pages):
            params = {
                "atype": "SU",
                "page": page,
                "sortfield": "pubdate",
                "sortorder": "desc"
            }
            
            # RID API needs no special headers but we'll use base ones
            response_text = self.fetch(self.api_url, params=params)
            if not response_text:
                break
                
            try:
                data = json.loads(response_text)
                rows = data.get('rows', [])
                if not rows:
                    break
                    
                for row in rows:
                    # Map API fields to our standard format
                    pub_date = row.get('pubdate', '') # Format: YYYY-MM-DD
                    title = row.get('name', '')
                    unit = row.get('org_name', '')
                    code = row.get('code', '')
                    link = row.get('link', '')
                    
                    # Convert YYYY-MM-DD to Thai display format matches other scrapers
                    # 2026-03-02 -> 2 มีนาคม 2569
                    date_display = self.format_thai_date(pub_date)
                    
                    all_results.append({
                        "agency": "กรมชลประทาน (RID)",
                        "unit": f"{unit} ({code})",
                        "title": title,
                        "date": date_display,
                        "sort_date": pub_date,
                        "url": link,
                        "source": self.name
                    })
            except Exception as e:
                print(f"  Error parsing RID API on page {page}: {e}")
                break
                
        return all_results

    def format_thai_date(self, iso_date):
        """Helper to convert YYYY-MM-DD to Thai display format."""
        if not iso_date or len(iso_date) < 10:
            return iso_date
            
        try:
            year = int(iso_date[:4])
            month = int(iso_date[5:7])
            day = int(iso_date[8:10])
            
            thai_months_full = [
                "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
                "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
            ]
            
            return f"{day} {thai_months_full[month]} {year + 543}"
        except:
            return iso_date
