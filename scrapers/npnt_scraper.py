from scrapers.base import BaseScraper
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import urllib3

urllib3.disable_warnings()

# ลำดับ fields ที่ต้องการแสดงในตาราง (ตรงกับหน้า detail ของ NPNT)
_DETAIL_FIELDS = [
    "ประเภทประกวด",
    "ประเภทสิ่งของ",
    "วันที่",
    "องค์กร",
    "เลขที่อ้างอิง",
    "รายละเอียด",
    "ติดต่อที่",
]


class NPNTScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="กรมประชาสัมพันธ์ (NPNT)", base_url="http://npnt.prd.go.th")
        self.api_url = "http://npnt.prd.go.th/centerweb/BidNews/BidNewsGridData"
        self.detail_base = "http://npnt.prd.go.th/centerweb/BidNews/DetailBidNews"

    def _fetch_detail(self, bid_id):
        """ดึงหน้า detail แล้วแปลงเป็น dict {label: value}
        คืน {} ถ้าดึงไม่ได้หรือ parse ไม่สำเร็จ"""
        url = f"{self.detail_base}?BN01_BidNewsID={bid_id}"
        try:
            r = requests.get(url, headers=self.headers, timeout=15, verify=False)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            # หาตารางที่มี 'ประเภทประกวด'
            target_table = None
            for t in soup.find_all("table"):
                if "ประเภทประกวด" in t.get_text():
                    target_table = t
                    break
            if not target_table:
                return {}
            info = {}
            for tr in target_table.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) == 3:
                    label = tds[0].get_text(strip=True)
                    value = " ".join(tds[2].get_text().split())  # normalize whitespace
                    if label:
                        info[label] = value
            return info
        except Exception:
            return {}

    def _format_title(self, info, fallback_detail):
        """รวม fields จาก detail page เป็น title เดียวที่พนักงานอ่านแล้วได้ข้อมูลครบ
        ถ้าดึง detail ไม่ได้ (info={}) ใช้ fallback_detail จาก API แทน"""
        if not info:
            return fallback_detail.strip()
        lines = []
        for field in _DETAIL_FIELDS:
            val = info.get(field, "").strip()
            if val:
                lines.append(f"{field} : {val}")
        return "\n".join(lines) if lines else fallback_detail.strip()

    def scrape(self, max_pages=3):
        print(f"Scraping {self.name}...")
        raw_items = []

        # ── ขั้นที่ 1: ดึง listing จาก jqGrid API ──────────────────────────
        for page in range(1, max_pages + 1):
            params = {
                "BN02_CatBidID": "3",   # ขายทอดตลาด
                "BN03_CatMaterialID": "",
                "BN01_FullText": "",
                "txtBidNewsDateSearch": "",
                "txtBidNewsEndDateSearch": "",
                "page": str(page),
                "rows": "20",
                "sidx": "CreDate",
                "sord": "desc",
            }
            try:
                r = requests.get(
                    self.api_url,
                    params=params,
                    headers=self.headers,
                    timeout=30,
                    verify=False,
                )
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                print(f"  Error page {page}: {e}")
                break

            rows = data.get("rows", [])
            if not rows:
                break

            for row in rows:
                cell = row.get("cell", [])
                if len(cell) < 6:
                    continue
                raw_items.append({
                    "bid_id":   cell[0],   # BN01_BidNewsID
                    "date_str": cell[1],   # CreDate  e.g. "10 ก.ค.2569"
                    "org":      cell[2],   # BN01_Org
                    "refer":    cell[3],   # BN01_NoRefer
                    "detail":   cell[5],   # BN01_Detail (fallback)
                })

            total_pages = data.get("total", 1)
            if page >= total_pages:
                break

        # ── ขั้นที่ 2: ดึง detail page แบบ parallel (5 workers) ──────────
        detail_map = {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_id = {
                executor.submit(self._fetch_detail, item["bid_id"]): item["bid_id"]
                for item in raw_items
            }
            for future in as_completed(future_to_id):
                bid_id = future_to_id[future]
                try:
                    detail_map[bid_id] = future.result()
                except Exception:
                    detail_map[bid_id] = {}

        # ── ขั้นที่ 3: รวมผลลัพธ์ ────────────────────────────────────────
        results = []
        for item in raw_items:
            info = detail_map.get(item["bid_id"], {})
            title = self._format_title(info, item["detail"])
            refer = item["refer"].strip() if item["refer"] else ""
            org   = item["org"].strip()   if item["org"]   else ""
            results.append({
                "agency":    "กรมประชาสัมพันธ์ (NPNT)",
                "unit":      refer or org,
                "title":     title,
                "date":      item["date_str"].strip(),
                "sort_date": self.normalize_thai_date(item["date_str"]),
                "url":       f"{self.detail_base}?BN01_BidNewsID={item['bid_id']}",
                "source":    self.name,
                "status":    "ขายทอดตลาด",
            })

        print(f"  {self.name}: {len(results)} items")
        return results
