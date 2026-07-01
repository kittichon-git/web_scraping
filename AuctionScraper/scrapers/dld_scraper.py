import re
import os
from bs4 import BeautifulSoup
from .base import BaseScraper

_THAI_MONTHS_FULL = {
    "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3, "เมษายน": 4,
    "พฤษภาคม": 5, "มิถุนายน": 6, "กรกฎาคม": 7, "สิงหาคม": 8,
    "กันยายน": 9, "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12,
}
_THAI_MONTHS_SHORT = [
    "", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
    "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
]

from datetime import datetime
_TODAY_CE = datetime.today().year

# Incapsula bypass cookies — visid_incap lasts ~1 year.
# Override via env vars: DLD_VISID / DLD_SES
_DEFAULT_COOKIES = {
    "visid_incap_3232699": os.environ.get(
        "DLD_VISID",
        "QP5IgFAxQDy5Kgsb22N1biD4RGoAAAAAQUIPAAAAAAC41dufXikrklfCp/5/higr",
    ),
    "incap_ses_297_3232699": os.environ.get(
        "DLD_SES",
        "hk4xesLC6UpKmV6C7ycfBCD4RGoAAAAA8gYBbOafRXxOnWCuSyxUMQ==",
    ),
}


def _parse_thai_full_date(raw: str) -> "datetime | None":
    """Parse e.g. '20 พฤษภาคม 2569' (Thai BE) → CE datetime."""
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
    be = dt.year + 543
    return f"{dt.day} {_THAI_MONTHS_SHORT[dt.month]} {be}"


def _to_sort_date(dt: "datetime | None") -> str:
    if dt is None:
        return "0000-00-00"
    return dt.strftime("%Y-%m-%d")


class DLDScraper(BaseScraper):
    """กรมปศุสัตว์ — www.dld.go.th ขายทอดตลาด (Joomla, Incapsula bypass via curl_cffi)."""

    BASE_DOMAIN = "https://www.dld.go.th"
    LIST_URL    = "https://www.dld.go.th/webnew/index.php/dld-news/procurement/2569/prakas-khay-thxd-tlad"

    def __init__(self):
        super().__init__(
            name="กรมปศุสัตว์",
            base_url=self.BASE_DOMAIN,
        )

    def _fetch_cffi(self, url: str, params: dict = None) -> "str | None":
        try:
            from curl_cffi import requests as cf
            r = cf.get(url, params=params, impersonate="chrome124", cookies=_DEFAULT_COOKIES, timeout=20)
            if r.status_code == 200 and len(r.text) > 5000:
                return r.text
            if len(r.text) < 5000:
                print(f"  DLD: Incapsula blocked — cookies may have expired")
            return None
        except Exception as e:
            print(f"  DLD fetch error: {e}")
            return None

    def _parse_listing(self, html: str) -> list:
        soup  = BeautifulSoup(html, "html.parser")
        items = []

        for th in soup.select("table th.list-title"):
            a = th.find("a")
            if not a:
                continue

            title = a.get_text(strip=True)
            href  = a.get("href", "")
            url   = href if href.startswith("http") else self.BASE_DOMAIN + href

            # Date is in the next sibling <td>
            row   = th.find_parent("tr")
            cells = row.find_all(["th", "td"]) if row else []
            date_raw = cells[1].get_text(strip=True) if len(cells) > 1 else ""

            # Unit from parentheses in title e.g. "(ด่านกักกันสัตว์ชัยนาท)"
            m    = re.search(r'\(([^)]+)\)', title)
            unit = m.group(1).strip() if m else "กรมปศุสัตว์"

            dt = _parse_thai_full_date(date_raw)
            items.append({
                "title":     title,
                "url":       url,
                "unit":      unit,
                "date":      _to_thai_display(dt),
                "sort_date": _to_sort_date(dt),
            })

        return items

    def scrape(self, max_pages=3, **kwargs):
        print(f"Scraping {self.name}...")
        results = []
        start   = 0

        for _ in range(max_pages):
            params = {"start": str(start)} if start > 0 else None
            html   = self._fetch_cffi(self.LIST_URL, params=params)
            if not html:
                break

            items = self._parse_listing(html)
            if not items:
                break

            for item in items:
                results.append({
                    "agency":    "กรมปศุสัตว์",
                    "unit":      item["unit"],
                    "title":     item["title"],
                    "date":      item["date"],
                    "sort_date": item["sort_date"],
                    "url":       item["url"],
                    "source":    self.name,
                    "status":    "ขายทอดตลาด",
                })

            # Joomla pagination: 10 per page
            if len(items) < 10:
                break
            start += 10

        print(f"  {self.name}: {len(results)} items")
        return results
