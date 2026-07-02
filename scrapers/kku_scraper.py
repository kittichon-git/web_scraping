from scrapers.base import BaseScraper
from bs4 import BeautifulSoup
from datetime import datetime
import requests
import urllib3

urllib3.disable_warnings()

_THAI_MONTHS_FULL = {
    "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3, "เมษายน": 4,
    "พฤษภาคม": 5, "มิถุนายน": 6, "กรกฎาคม": 7, "สิงหาคม": 8,
    "กันยายน": 9, "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12,
}
_THAI_MONTHS_SHORT = [
    "", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
    "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
]
_TODAY_CE = datetime.today().year


def _parse_thai_full_date(raw: str) -> "datetime | None":
    parts = raw.strip().split()
    if len(parts) < 3:
        return None
    try:
        day   = int(parts[0])
        month = _THAI_MONTHS_FULL.get(parts[1])
        be    = int(parts[2])
        if not month:
            return None
        ce = be - 543
        if not (2000 <= ce <= _TODAY_CE + 1):
            return None
        return datetime(ce, month, day)
    except Exception:
        return None


def _to_thai_display(dt: "datetime | None") -> str:
    if dt is None:
        return ""
    return f"{dt.day} {_THAI_MONTHS_SHORT[dt.month]} {dt.year + 543}"


def _to_sort_date(dt: "datetime | None") -> str:
    if dt is None:
        return "0000-00-00"
    return dt.strftime("%Y-%m-%d")


class KKUScraper(BaseScraper):
    """มหาวิทยาลัยขอนแก่น — procurement.kku.ac.th/t/auction (table, pagination)."""

    BASE_URL = "https://procurement.kku.ac.th"
    LIST_URL = "https://procurement.kku.ac.th/t/auction"

    def __init__(self):
        super().__init__(
            name="มหาวิทยาลัยขอนแก่น",
            base_url=self.BASE_URL,
        )

    def scrape(self, max_pages=3):
        print(f"Scraping {self.name}...")
        results = []

        for page_num in range(1, max_pages + 1):
            params = {"page": str(page_num), "per-page": "15"}
            try:
                r = requests.get(
                    self.LIST_URL,
                    params=params,
                    headers=self.headers,
                    timeout=20,
                    verify=False,
                )
                r.raise_for_status()
            except Exception as e:
                print(f"  KKU fetch error page {page_num}: {e}")
                break

            soup = BeautifulSoup(r.text, "html.parser")
            rows = soup.select("table tr")
            data_rows = [row for row in rows if row.find("a", href=lambda h: h and "/view/" in h)]
            if not data_rows:
                break

            for row in data_rows:
                tds = row.find_all("td")
                if len(tds) < 4:
                    continue

                # Title & URL from link in td[1]
                a_tag = tds[1].find("a", href=True)
                if not a_tag:
                    continue
                title = a_tag.get_text(strip=True)
                href  = a_tag["href"]
                url   = href if href.startswith("http") else self.BASE_URL + href

                # Unit: first .label-faculty div (not hidden-sm)
                unit_div = tds[1].find("div", class_=lambda c: c and "label-faculty" in c and "hidden" not in c)
                unit = unit_div.get_text(strip=True) if unit_div else "มหาวิทยาลัยขอนแก่น"

                # Announced date: td[3]
                date_raw = tds[3].get_text(strip=True)
                dt = _parse_thai_full_date(date_raw)

                results.append({
                    "agency":    "มหาวิทยาลัยขอนแก่น",
                    "unit":      unit,
                    "title":     title,
                    "date":      _to_thai_display(dt),
                    "sort_date": _to_sort_date(dt),
                    "url":       url,
                    "source":    self.name,
                    "status":    "ขายทอดตลาด",
                })

            if len(data_rows) < 15:
                break

        print(f"  {self.name}: {len(results)} items")
        return results
