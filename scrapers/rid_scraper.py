from scrapers.base import BaseScraper
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class RIDScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="Royal Irrigation Department (RID)", base_url="https://egp.rid.go.th")
        self.list_url = "https://egp.rid.go.th/announce/SU"

    def scrape(self):
        print(f"Scraping {self.name} via Playwright...")
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("  [RID] playwright not installed — skipping")
            return []

        results = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(self.list_url, wait_until="networkidle", timeout=30000)
                page.wait_for_selector("div.mantine-1q30ucv", timeout=15000)

                html = page.content()
                browser.close()

            soup = BeautifulSoup(html, "html.parser")
            div = soup.find("div", class_="mantine-1q30ucv")
            if not div:
                print("  [RID] mantine-1q30ucv div not found")
                return []

            rows = div.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if not cells:
                    continue  # header row

                code  = cells[0].get_text(strip=True) if len(cells) > 0 else ""
                title = cells[1].get_text(" ", strip=True) if len(cells) > 1 else ""
                unit  = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                date_str = cells[4].get_text(strip=True) if len(cells) > 4 else ""

                # link จาก <a href> ในแถว (PDF)
                a_tag = row.find("a", href=True)
                url = a_tag["href"] if a_tag else ""
                if not url:
                    continue  # ข้ามแถวที่ไม่มี URL

                sort_date = self.normalize_thai_date(date_str)
                date_display = self._thai_date_display(date_str)

                results.append({
                    "agency": "กรมชลประทาน (RID)",
                    "unit": f"{unit} ({code})" if code else unit,
                    "title": title,
                    "date": date_display,
                    "sort_date": sort_date,
                    "url": url,
                    "source": self.name,
                    "status": "ประกาศขายทอดตลาด",
                })

        except Exception as e:
            print(f"  [RID] Error: {e}")
            return []

        print(f"  [RID] found {len(results)} items")
        return results

    def _thai_date_display(self, date_str):
        """DD/MM/YYYY (BE) → 'D เดือน YYYY (BE)' สำหรับ display"""
        if not date_str or len(date_str) < 8:
            return date_str
        try:
            parts = date_str.strip().split("/")
            day, month, year_be = int(parts[0]), int(parts[1]), int(parts[2])
            thai_months = [
                "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
                "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
            ]
            return f"{day} {thai_months[month]} {year_be}"
        except Exception:
            return date_str
