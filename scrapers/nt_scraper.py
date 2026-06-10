from scrapers.base import BaseScraper
from bs4 import BeautifulSoup
import re
import time


class NTScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="NT", base_url="https://procurement.ntplc.co.th/bid")
        self.list_url = "https://procurement.ntplc.co.th/bid/first.php?type=%E0%B8%82%E0%B8%B2%E0%B8%A2"

    def _page_url(self, page):
        if page == 1:
            return self.list_url
        return f"https://procurement.ntplc.co.th/bid/first.php?type=%E0%B8%82%E0%B8%B2%E0%B8%A2&&method=&&page={page}&&keyword=&&cancel=0"

    def parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')

        # หา div.row ที่มีตารางรายการ (row ที่ 3 index 0-based)
        main_table = None
        for div in soup.find_all('div', class_='row'):
            tbl = div.find('table')
            if tbl and 'หน้าที่' in div.get_text():
                main_table = tbl
                break
        if not main_table:
            return []

        results = []
        for tr in main_table.find_all('tr'):
            td = tr.find('td')
            if not td:
                continue
            td_text = td.get_text(' ', strip=True)

            # ข้าม row pagination
            if 'หน้าที่' in td_text and 'ลงประกาศ' not in td_text:
                continue

            # ── unit: ข้อความใน <b> หลัง "ครั้งที่" (ค้นหาภายใน td เท่านั้น) ──
            unit = ""
            for content in td.children:
                text = content.strip() if isinstance(content, str) else ""
                if 'ครั้งที่' in text:
                    sib = content.next_sibling
                    while sib:
                        if hasattr(sib, 'name') and sib.name == 'b':
                            unit = sib.get_text(strip=True)
                            break
                        sib = sib.next_sibling
                    break

            # ── date: <font color="brown"> ──
            date_font = td.find('font', color='brown')
            date_raw = date_font.get_text(strip=True) if date_font else ""
            # "2 มิ.ย.2569 13:31" → ตัดเวลาออก
            date_str = re.split(r'\s+\d{1,2}:\d{2}', date_raw)[0].strip()

            # ── URL: แกะจาก javascript:Open('document/...pdf',...) ──
            pdf_url = None
            for a in td.find_all('a', href=True):
                href = a['href']
                m = re.search(r"Open\('(document/[^']+\.pdf)'", href)
                if m:
                    pdf_url = f"{self.base_url}/{m.group(1)}"
                    break
            if not pdf_url:
                continue  # ไม่มี PDF = ข้าม

            # ── title: ดึง text ส่วนกลาง (หลัง date, ก่อน "กำหนดขาย") ──
            # ใช้ full td text แล้วตัดส่วน header/footer ออก
            lines = [t.strip() for t in td.strings if t.strip()]
            # ลบ element ที่รู้จัก
            skip_words = {'ประกาศขายโดยวิธีประกวดราคา', 'ครั้งที่', 'ลงประกาศ', 'รายละเอียด', unit, date_raw}
            body_parts = [l for l in lines if l not in skip_words and not l.startswith('กำหนดขาย')]
            title = ' '.join(body_parts).strip()
            if not title:
                title = td_text[:120]

            results.append({
                "agency": "บริษัท โทรคมนาคมแห่งชาติ (NT)",
                "unit": unit,
                "title": title,
                "date": date_str,
                "sort_date": self.normalize_thai_date(date_str),
                "url": pdf_url,
                "source": self.name,
                "status": "ประกาศขายทอดตลาด",
            })

        return results

    def scrape(self, max_pages=5):
        print(f"Scraping {self.name}...")
        all_results = []
        for page in range(1, max_pages + 1):
            print(f"  NT page {page}/{max_pages}")
            html = self.fetch(self._page_url(page))
            if not html:
                print(f"  NT page {page}: fetch failed, stopping")
                break
            results = self.parse(html)
            if not results:
                print(f"  NT page {page}: no results, stopping")
                break
            all_results.extend(results)
            if page < max_pages:
                time.sleep(0.5)
        print(f"  NT: found {len(all_results)} items")
        return all_results
