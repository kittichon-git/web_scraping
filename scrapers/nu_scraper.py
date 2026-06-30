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
    """Parse e.g. '19 มิถุนายน 2569' (Thai BE) → CE datetime."""
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


class NUScraper(BaseScraper):
    """มหาวิทยาลัยนเรศวร — finance.nu.ac.th ขายทอดตลาด (single-page table)."""

    LIST_URL = "https://www.finance.nu.ac.th/procurementids/marketsale.php"
    BASE_URL = "https://www.finance.nu.ac.th/procurementids/"

    def __init__(self):
        super().__init__(
            name="มหาวิทยาลัยนเรศวร",
            base_url="https://www.finance.nu.ac.th",
        )

    def scrape(self, max_pages=1):
        print(f"Scraping {self.name}...")
        results = []

        try:
            r = requests.get(
                self.LIST_URL,
                headers=self.headers,
                timeout=20,
                verify=False,
            )
            r.raise_for_status()
            r.encoding = "utf-8"
        except Exception as e:
            print(f"  NU fetch error: {e}")
            return results

        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("section.content table tbody tr")

        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 7:
                continue

            title       = cells[1].get_text(strip=True)
            date_raw    = cells[6].get_text(strip=True)  # วันที่ลงประกาศ
            link_tag    = cells[7].find("a") if len(cells) > 7 else None

            if not title:
                continue

            # Build absolute PDF URL
            href = link_tag.get("href", "").strip() if link_tag else ""
            if href:
                url = href if href.startswith("http") else self.BASE_URL + href
            else:
                url = self.LIST_URL

            dt = _parse_thai_full_date(date_raw)

            results.append({
                "agency":    "มหาวิทยาลัยนเรศวร",
                "unit":      "มหาวิทยาลัยนเรศวร",
                "title":     title,
                "date":      _to_thai_display(dt),
                "sort_date": _to_sort_date(dt),
                "url":       url,
                "source":    self.name,
                "status":    "ขายทอดตลาด",
            })

        print(f"  {self.name}: {len(results)} items")
        return results
