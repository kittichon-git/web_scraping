from scrapers.base import BaseScraper
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import requests
import urllib3

urllib3.disable_warnings()

_THAI_MONTHS_SHORT = [
    "", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
    "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
]
_TODAY_CE = datetime.today().year
_RETENTION_DAYS = 60

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


def _get_form_fields(soup: BeautifulSoup) -> dict:
    """Extract all ASP.NET form fields from the current page."""
    fields = {}
    for fid in ("__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"):
        tag = soup.find("input", id=fid)
        if tag:
            fields[fid] = tag.get("value", "")
    for inp in soup.select("form input[name]"):
        n = inp.get("name", "")
        if n and n not in fields:
            fields[n] = inp.get("value", "")
    for sel in soup.select("form select[name]"):
        n = sel.get("name", "")
        if n and n not in fields:
            opt = sel.find("option", selected=True)
            fields[n] = opt["value"] if opt else ""
    return fields


class CMUScraper(BaseScraper):
    """มหาวิทยาลัยเชียงใหม่ — cmu.ac.th/en/procurement กรองประเภท 10 ขายทอดตลาด."""

    BASE_URL = "https://www.cmu.ac.th"
    LIST_URL = "https://www.cmu.ac.th/en/procurement"

    def __init__(self):
        super().__init__(
            name="มหาวิทยาลัยเชียงใหม่",
            base_url=self.BASE_URL,
        )

    def _parse_auction_rows(self, soup: BeautifulSoup, seen_urls: set) -> tuple[list, int]:
        """
        Parse ขายทอดตลาด items from one page.
        Returns (new_items, total_auction_on_page).
        Skips items whose URL is already in seen_urls.
        """
        new_items = []
        total_auction = 0
        cutoff = datetime.today() - timedelta(days=_RETENTION_DAYS)

        for row in soup.select("table.table tr"):
            tds = row.find_all("td")
            if len(tds) < 4:
                continue

            small = tds[1].find("small", class_="text-muted")
            if not small or "ขายทอดตลาด" not in small.get_text():
                continue

            a_tag = tds[1].find("a", href=True)
            if not a_tag:
                continue

            total_auction += 1
            href = a_tag["href"]
            url  = href if href.startswith("http") else self.BASE_URL + href

            if url in seen_urls:
                continue  # sticky/duplicate — skip

            title = a_tag.get_text(strip=True)

            unit_span = tds[2].find("span")
            unit = unit_span.get_text(strip=True) if unit_span else tds[2].get_text(strip=True)

            date_span = tds[3].find("span")
            date_raw  = date_span.get_text(strip=True) if date_span else tds[3].get_text(strip=True)
            dt = _parse_cmu_date(date_raw)

            # Skip items beyond retention window
            if dt and dt < cutoff:
                continue

            seen_urls.add(url)
            new_items.append({
                "agency":    "มหาวิทยาลัยเชียงใหม่",
                "unit":      unit,
                "title":     title,
                "date":      _to_thai_display(dt),
                "sort_date": _to_sort_date(dt),
                "url":       url,
                "source":    self.name,
                "status":    "ขายทอดตลาด",
            })

        return new_items, total_auction

    def scrape(self, max_pages: int = 10):
        print(f"Scraping {self.name}...")
        results = []
        seen_urls: set = set()

        session = requests.Session()
        session.headers.update(self.headers)

        # --- Step 1: GET page 1 to grab form fields ---
        try:
            r = session.get(self.LIST_URL, timeout=20, verify=False)
            r.raise_for_status()
        except Exception as e:
            print(f"  CMU fetch error: {e}")
            return results

        soup = BeautifulSoup(r.text, "html.parser")

        # --- Step 2: POST with ddlType=PUBLISH_AUCTION to filter ขายทอดตลาด ---
        fields = _get_form_fields(soup)
        fields["__EVENTTARGET"]   = "ctl00$cphPageContent$wucProcurement$ddlType"
        fields["__EVENTARGUMENT"] = ""
        fields["ctl00$cphPageContent$wucProcurement$ddlType"] = "PUBLISH_AUCTION"

        try:
            r = session.post(self.LIST_URL, data=fields, timeout=20, verify=False)
            r.raise_for_status()
        except Exception as e:
            print(f"  CMU filter post error: {e}")
            return results

        soup = BeautifulSoup(r.text, "html.parser")
        page_items, _ = self._parse_auction_rows(soup, seen_urls)
        results.extend(page_items)
        print(f"  CMU page 1: {len(page_items)} auction items")

        # --- Step 3: paginate with lbtnNext ---
        for page_num in range(2, max_pages + 1):
            next_btn = soup.find("a", id=lambda x: x and "lbtnNext" in (x or ""))
            if not next_btn:
                break

            fields = _get_form_fields(soup)
            fields["__EVENTTARGET"]   = "ctl00$cphPageContent$wucProcurement$lbtnNext"
            fields["__EVENTARGUMENT"] = ""
            fields["ctl00$cphPageContent$wucProcurement$ddlType"] = "PUBLISH_AUCTION"

            try:
                r = session.post(self.LIST_URL, data=fields, timeout=20, verify=False)
                r.raise_for_status()
            except Exception as e:
                print(f"  CMU page {page_num} error: {e}")
                break

            soup = BeautifulSoup(r.text, "html.parser")
            page_items, _ = self._parse_auction_rows(soup, seen_urls)
            results.extend(page_items)
            print(f"  CMU page {page_num}: {len(page_items)} auction items")
            if not page_items:
                break

        print(f"  {self.name}: {len(results)} items")
        return results
