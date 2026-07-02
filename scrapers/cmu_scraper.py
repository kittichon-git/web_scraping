from scrapers.base import BaseScraper
from bs4 import BeautifulSoup
from datetime import datetime
import requests
import urllib3

urllib3.disable_warnings()

_THAI_MONTHS_SHORT = [
    "", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
    "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
]
_TODAY_CE = datetime.today().year


def _parse_cmu_date(raw: str) -> "datetime | None":
    """Parse 'D/M/YYYY HH:MM:SS' (Thai BE) → CE datetime. e.g. '1/7/2569 13:48:19'."""
    try:
        date_part = raw.strip().split()[0]  # "1/7/2569"
        d, m, be = date_part.split("/")
        ce = int(be) - 543
        if not (2000 <= ce <= _TODAY_CE + 1):
            return None
        return datetime(ce, int(m), int(d))
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


class CMUScraper(BaseScraper):
    """มหาวิทยาลัยเชียงใหม่ — cmu.ac.th/en/procurement กรองประเภท 10 ขายทอดตลาด."""

    BASE_URL = "https://www.cmu.ac.th"
    LIST_URL = "https://www.cmu.ac.th/en/procurement"

    def __init__(self):
        super().__init__(
            name="มหาวิทยาลัยเชียงใหม่",
            base_url=self.BASE_URL,
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
        except Exception as e:
            print(f"  CMU fetch error: {e}")
            return results

        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("table.table tr")

        for row in rows:
            tds = row.find_all("td")
            if len(tds) < 4:
                continue

            # Filter: keep only type 10 ขายทอดตลาด
            small = tds[1].find("small", class_="text-muted")
            if not small or "ขายทอดตลาด" not in small.get_text():
                continue

            a_tag = tds[1].find("a", href=True)
            if not a_tag:
                continue

            title = a_tag.get_text(strip=True)
            href  = a_tag["href"]
            url   = href if href.startswith("http") else self.BASE_URL + href

            unit_span = tds[2].find("span")
            unit = unit_span.get_text(strip=True) if unit_span else tds[2].get_text(strip=True)

            date_span = tds[3].find("span")
            date_raw  = date_span.get_text(strip=True) if date_span else tds[3].get_text(strip=True)
            dt = _parse_cmu_date(date_raw)

            results.append({
                "agency":    "มหาวิทยาลัยเชียงใหม่",
                "unit":      unit,
                "title":     title,
                "date":      _to_thai_display(dt),
                "sort_date": _to_sort_date(dt),
                "url":       url,
                "source":    self.name,
                "status":    "ขายทอดตลาด",
            })

        print(f"  {self.name}: {len(results)} items")
        return results
