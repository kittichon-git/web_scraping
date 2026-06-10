import re
from bs4 import BeautifulSoup
from .base import BaseScraper

class DLDScraper(BaseScraper):
    """
    กรมปศุสัตว์ — สถาบันบำรุงพันธุ์สัตว์
    https://breeding.dld.go.th/index.php/th/about/planning/kickrrm

    โครงสร้างหน้า: Joomla CMS, ตาราง Bootstrap
    - ชื่อเรื่อง: <th class="list-title"><a href="...">
    - ไม่มีวันที่ในหน้า listing → ดึงจากหน้าย่อย
    - Pagination: ?start=N (ใช้ limit=0 เพื่อดึงทั้งหมดในครั้งเดียว)
    """

    BASE_DOMAIN = "https://breeding.dld.go.th"
    LIST_URL    = "https://breeding.dld.go.th/index.php/th/about/planning/kickrrm"

    def __init__(self):
        super().__init__(
            name="กรมปศุสัตว์ (สถาบันบำรุงพันธุ์สัตว์)",
            base_url=self.LIST_URL,
        )

    # ─────────────────────────────────────────────
    # parse listing page → list of {title, url}
    # ─────────────────────────────────────────────
    def parse(self, html):
        soup    = BeautifulSoup(html, "html.parser")
        table   = soup.find("table", class_="com-content-category__table")
        results = []

        if not table:
            return results

        for th in table.find_all("th", class_="list-title"):
            a = th.find("a")
            if not a:
                continue

            title = a.get_text(strip=True)
            href  = a.get("href", "")

            # สร้าง URL เต็ม
            if href.startswith("http"):
                url = href
            elif href.startswith("/"):
                url = self.BASE_DOMAIN + href
            else:
                url = self.BASE_DOMAIN + "/" + href

            # แกะ หน่วยงาน จากวงเล็บท้ายชื่อ เช่น "(ศบส.นครสวรรค์)"
            agency_match = re.search(r'\(([^)]+)\)\s*$', title)
            unit = agency_match.group(1).strip() if agency_match else ""

            results.append({
                "title": title,
                "url":   url,
                "unit":  unit,
            })

        return results

    # ─────────────────────────────────────────────
    # ดึงวันที่จากหน้าย่อย (article detail)
    # ─────────────────────────────────────────────
    def fetch_article_date(self, url):
        """ดึงวันที่ประกาศจากหน้าย่อย คืนค่า string หรือ '' ถ้าหาไม่เจอ"""
        html = self.fetch(url)
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")

        # Joomla มักใส่วันที่ใน <dd class="published"> หรือ <time>
        for sel in [
            "dd.published",
            "time",
            "span.article-info-term",
            ".article-info-block dd",
        ]:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(strip=True)
                if re.search(r'\d{1,2}.*\d{4}', text):
                    return text

        # fallback: หาวันที่จาก text ในหน้า (DD เดือนไทย YYYY)
        body = soup.get_text(" ")
        m = re.search(
            r'(\d{1,2}\s*(?:มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|'
            r'กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)\s*\d{4})',
            body
        )
        return m.group(1).strip() if m else ""

    # ─────────────────────────────────────────────
    # main scrape
    # ─────────────────────────────────────────────
    def scrape(self, fetch_dates=True, **kwargs):
        print(f"Scraping {self.name}...")

        # ใช้ limit=0 เพื่อดึงทั้งหมดในครั้งเดียว
        html = self.fetch(self.LIST_URL, params={"limit": 0})
        if not html:
            print("  ดึงหน้า listing ไม่ได้")
            return []

        items   = self.parse(html)
        results = []

        print(f"  พบ {len(items)} รายการ")

        for i, item in enumerate(items, 1):
            date_raw = ""
            if fetch_dates:
                date_raw = self.fetch_article_date(item["url"])

            results.append({
                "agency":    "กรมปศุสัตว์",
                "unit":      item["unit"],
                "title":     item["title"],
                "date":      date_raw,
                "sort_date": self.normalize_thai_date(date_raw) if date_raw else "0000-00-00",
                "url":       item["url"],
                "source":    self.name,
            })

        return results
