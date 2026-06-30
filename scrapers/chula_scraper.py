from scrapers.base import BaseScraper
from bs4 import BeautifulSoup
from datetime import datetime
import requests
import urllib3
import re

urllib3.disable_warnings()

_THAI_MONTHS_REV = {
    "ม.ค.": 1, "ก.พ.": 2, "มี.ค.": 3, "เม.ย.": 4, "พ.ค.": 5, "มิ.ย.": 6,
    "ก.ค.": 7, "ส.ค.": 8, "ก.ย.": 9, "ต.ค.": 10, "พ.ย.": 11, "ธ.ค.": 12,
}
_THAI_MONTHS_SHORT = [
    "", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
    "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
]
_CLICK_RE = re.compile(r"clickToLink\((\d+),\s*'([^']+)'\)")
_TODAY_CE = datetime.today().year


def _parse_thai_date(raw: str) -> "datetime | None":
    """Parse e.g. '1  ก.ค.  2569' (Thai BE) → CE datetime."""
    parts = raw.split()
    if len(parts) < 3:
        return None
    try:
        day   = int(parts[0])
        month = _THAI_MONTHS_REV.get(parts[1])
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
    be = dt.year + 543
    return f"{dt.day} {_THAI_MONTHS_SHORT[dt.month]} {be}"


def _to_sort_date(dt: "datetime | None") -> str:
    if dt is None:
        return "0000-00-00"
    return dt.strftime("%Y-%m-%d")


class ChulaScraper(BaseScraper):
    """จุฬาลงกรณ์มหาวิทยาลัย — procurement.chula.ac.th ขายทอดตลาด (annouceType=10)."""

    BASE_URL   = "https://procurement.chula.ac.th/search"
    DETAIL_URL = "https://procurement.chula.ac.th/search"

    def __init__(self):
        super().__init__(
            name="จุฬาลงกรณ์มหาวิทยาลัย",
            base_url="https://procurement.chula.ac.th",
        )

    def scrape(self, max_pages=3):
        print(f"Scraping {self.name}...")
        results = []

        for page_num in range(1, max_pages + 1):
            params = {"annouceType": "10", "page": str(page_num)}
            try:
                r = requests.get(
                    self.BASE_URL,
                    params=params,
                    headers=self.headers,
                    timeout=20,
                    verify=False,
                )
                r.raise_for_status()
            except Exception as e:
                print(f"  Chula fetch error page {page_num}: {e}")
                break

            soup = BeautifulSoup(r.text, "html.parser")
            rows = soup.select("table.table tbody tr")
            if not rows:
                break

            for row in rows:
                cells = row.find_all(["th", "td"])
                if len(cells) < 7:
                    continue

                unit   = cells[2].get_text(separator=" ", strip=True).replace("\xa0", " ")
                method = cells[3].get_text(strip=True)
                rtype  = cells[4].get_text(strip=True)
                title  = cells[5].get_text(strip=True)
                date_raw = cells[6].get_text(strip=True)

                # Build URL from onclick
                onclick = row.get("onclick", "")
                m = _CLICK_RE.search(onclick)
                if m:
                    url = f"{self.DETAIL_URL}?projectId={m.group(1)}&depParams={m.group(2)}"
                else:
                    continue  # skip rows without a link

                if not title:
                    continue

                dt = _parse_thai_date(date_raw)

                results.append({
                    "agency":    "จุฬาลงกรณ์มหาวิทยาลัย",
                    "unit":      unit,
                    "title":     title,
                    "date":      _to_thai_display(dt),
                    "sort_date": _to_sort_date(dt),
                    "url":       url,
                    "source":    self.name,
                    "status":    rtype or "ขายทอดตลาด",
                })

            # stop if fewer than 20 rows (last page)
            if len(rows) < 20:
                break

        print(f"  {self.name}: {len(results)} items")
        return results
