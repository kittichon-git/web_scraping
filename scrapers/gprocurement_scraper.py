from scrapers.base import BaseScraper
from bs4 import BeautifulSoup
import urllib.parse
import re
import logging
import time
from datetime import datetime, timedelta, timezone

log = logging.getLogger("auction_scraper")

_UUID_RE = re.compile(
    r'/wps/wcm/connect/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/',
    re.IGNORECASE,
)


class GProcurementScraper(BaseScraper):
    # BUG B FIX: ใช้ URL หน้าแรกเดียว แล้ว follow pagination links จาก HTML
    START_URL = (
        "https://www.gprocurement.go.th/wps/portal/egp/auction/"
        "!ut/p/z1/04_Sj9CPykssy0xPLMnMz0vMAfIjo8zifQ3djQydnQ18_T3dzA0czU0Nf"
        "ANMLQ1cLc30w8EKDHAARwP9KGL041EQhd_4cP0oNCvCjM2AJgT4OvsHehgYOBtCFeA"
        "xoyA3NMIg01ERAP8P-8A!/dz/d5/L0lDUmlTUSEhL3dHa0FKRnNBLzROV3FpQSEhL3Ro/"
    )
    MAX_PAGES = 20    # cap กันวนไม่จบ
    CUTOFF_DAYS = 30  # หยุดถ้า sort_date เก่ากว่านี้

    def __init__(self):
        super().__init__(name="G-Procurement", base_url="https://www.gprocurement.go.th")

    @staticmethod
    def extract_uuid(url: str):
        """ดึง UUID จาก /wps/wcm/connect/{UUID}/... เป็น stable identity"""
        if not url:
            return None
        m = _UUID_RE.search(url)
        return m.group(1).lower() if m else None

    def parse(self, html: str) -> list:
        """
        Parse 1 หน้า — คืน list of dict
        BUG A FIX: date จาก setFullDateByLocale() ใน <script> (ค.ศ. แล้ว ไม่ลบ 543)
        """
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')
        if not table:
            return []

        results = []
        for row in table.find_all('tr'):
            cols = row.find_all('td')
            if len(cols) < 5:
                continue

            book_no = cols[0].text.strip()
            subject = cols[2].text.strip()

            # BUG A FIX: date อยู่ใน <script>setFullDateByLocale('YYYY/MM/DD')</script>
            script_tag = cols[1].find('script')
            js_date = None
            if script_tag and script_tag.string:
                m = re.search(
                    r"setFullDateByLocale\('(\d{4}/\d{2}/\d{2})'\)",
                    script_tag.string,
                )
                if m:
                    js_date = m.group(1).replace('/', '-')  # "2026-06-16" — ค.ศ. แล้ว

            if js_date:
                sort_date = js_date
                date_str = js_date
            else:
                log.warning(
                    f"[G-Procurement] ไม่พบ setFullDateByLocale ใน col[1] "
                    f"(book_no={book_no!r}) — fallback cols[1].text"
                )
                date_str = cols[1].text.strip() or "ไม่ระบุวันที่"
                sort_date = self.normalize_thai_date(date_str)

            link_tag = cols[4].find('a', href=True)
            detail_url = (
                urllib.parse.urljoin(self.base_url, link_tag['href'])
                if link_tag else None
            )

            if "เลขที่หนังสือ" in book_no or not subject:
                continue

            results.append({
                "agency": "กรมบัญชีกลาง (e-GP)",
                "unit": book_no,
                "title": subject,
                "date": date_str,
                "sort_date": sort_date,
                "url": detail_url,
                "source": self.name,
            })
        return results

    def _find_forward_link(self, html: str, current_url: str, target_page: int):
        """
        หา URL ของ target_page จาก pagination ในหน้าปัจจุบัน
        ลำดับ: หา text == str(target_page) ก่อน → fallback '>>' / '›'
        คืน None ถ้าไม่มีหน้าถัดไป
        """
        soup = BeautifulSoup(html, 'html.parser')
        target_str = str(target_page)
        fallback_url = None
        for a in soup.find_all('a', href=True):
            txt = a.get_text(strip=True)
            href = a['href']
            if txt == target_str:
                return urllib.parse.urljoin(current_url, href)
            if txt in ('>>', '›') and fallback_url is None:
                fallback_url = urllib.parse.urljoin(current_url, href)
        return fallback_url

    @staticmethod
    def extract_province(unit: str) -> str:
        """
        ดึงรหัสจังหวัดจาก unit field
        format: "ที่ {PROV} {NO}/..." หรือ "ด่วนที่สุด ที่ {PROV} {NO}/..."
        คืน token หลัง "ที่" แรก เช่น "ชม", "นศ", "กทม"
        """
        tokens = (unit or '').split()
        for i, tok in enumerate(tokens):
            if tok == 'ที่' and i + 1 < len(tokens):
                return tokens[i + 1]
        return ''

    def scrape(self, cutoff_days: int = CUTOFF_DAYS) -> list:
        """
        BUG B FIX: loop pagination จนครบ (ไม่ hardcode จำนวนหน้า)

        กลไก (ทาง B LINEAR): page 1 → ตามลิงก์หน้า 2 → 3 → ... เป็นเส้นตรง
        ไม่ใช้ BFS (ป้องกัน WebSphere state URL loop)
        STOP: หน้าว่าง | UUID ซ้ำทั้งหน้า | sort_date เกิน cutoff | ชน MAX_PAGES
        Dedup: UUID จาก /wps/wcm/connect/{UUID}/
        """
        th_now = datetime.now(timezone.utc) + timedelta(hours=7)
        cutoff_date = (th_now - timedelta(days=cutoff_days)).date()
        log.info(f"[G-Procurement] เริ่ม scrape | cutoff={cutoff_date} | MAX_PAGES={self.MAX_PAGES}")

        all_results: list = []
        seen_uuids: set = set()
        current_url = self.START_URL
        next_page_num = 2  # เลขหน้าถัดไปที่เราต้องการหา

        for page_num in range(1, self.MAX_PAGES + 1):
            log.info(f"[G-Procurement] หน้า {page_num}")
            html = self.fetch(current_url)
            if not html:
                log.error(f"[G-Procurement] ดึงหน้า {page_num} ไม่ได้ — หยุด")
                break

            rows = self.parse(html)
            if not rows:
                log.info(f"[G-Procurement] หน้า {page_num}: ไม่มีแถว — หยุด")
                break

            new_count = 0
            cutoff_hit = False
            for r in rows:
                uuid = self.extract_uuid(r.get('url') or '')
                if uuid and uuid in seen_uuids:
                    continue
                if uuid:
                    seen_uuids.add(uuid)

                sd = r.get('sort_date', '')
                if sd and sd != '0000-00-00':
                    try:
                        if datetime.strptime(sd, '%Y-%m-%d').date() < cutoff_date:
                            cutoff_hit = True
                            continue
                    except ValueError:
                        pass

                all_results.append(r)
                new_count += 1

            log.info(
                f"[G-Procurement] หน้า {page_num}: "
                f"rows={len(rows)} new={new_count} total={len(all_results)}"
            )

            if new_count == 0:
                log.info(f"[G-Procurement] ไม่มี UUID ใหม่เลย — หยุด")
                break
            if cutoff_hit and new_count == 0:
                log.info(f"[G-Procurement] ทุกแถวเก่ากว่า cutoff={cutoff_date} — หยุด")
                break

            # หาลิงก์หน้าถัดไปแบบ linear (ไม่ backtrack)
            next_url = self._find_forward_link(html, current_url, next_page_num)
            if not next_url:
                log.info(f"[G-Procurement] ไม่มีหน้าถัดไป — หยุด")
                break

            current_url = next_url
            next_page_num += 1
            time.sleep(1)

        else:
            log.warning(
                f"[G-Procurement] ชนเพดาน MAX_PAGES={self.MAX_PAGES} — "
                f"อาจยังมีหน้าเหลือ ตรวจสอบด้วยมือ"
            )

        log.info(
            f"[G-Procurement] เสร็จ: {len(all_results)} รายการ | UUIDs={len(seen_uuids)}"
        )
        return all_results
