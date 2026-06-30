from scrapers.base import BaseScraper
from bs4 import BeautifulSoup
from datetime import datetime
import os

_THAI_MONTHS_SHORT = [
    "", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
    "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
]

# Incapsula bypass cookies — visid_incap lasts ~1 year.
# Override via env vars: PAT_VISID / PAT_SES / PAT_TS
_DEFAULT_COOKIES = {
    "visid_incap_3228695": os.environ.get(
        "PAT_VISID",
        "1lfZHRY4Re++yw/w9ZKesUePQ2oAAAAAQUIPAAAAAAB9l8eXH7i0FtkeMKWvWHa/",
    ),
    "incap_ses_373_3228695": os.environ.get(
        "PAT_SES",
        "0phbNREmPC6TS3QK2iktBUiPQ2oAAAAA3rDr8wGKW74fgN6xisI7eA==",
    ),
    "TS5ae52186027": os.environ.get(
        "PAT_TS",
        "082c76d36dab20000e694478cc8ce3be8c30f86322b01858ad90386bcf9a7e30915abde52336ad0d080935eded113000d8402d79b1b2814f133db4ead605b8dacf108d2da70251418b985f7762228b36d9db1d3620cc8480805b1ab832d07d69",
    ),
}


def _parse_iso_date(iso_str: str) -> "datetime | None":
    try:
        return datetime.fromisoformat(iso_str)
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


class PATScraper(BaseScraper):
    """การท่าเรือแห่งประเทศไทย (กทท.) — WordPress UAGB post grid.
    Incapsula bypass via curl_cffi + visid_incap cookie (valid ~1 year).
    """

    BASE_URL = "https://www.port.co.th/port/index.php/auctionannouncement-2/"

    def __init__(self):
        super().__init__(
            name="การท่าเรือแห่งประเทศไทย (กทท.)",
            base_url="https://www.port.co.th",
        )

    def _fetch(self, url: str) -> "str | None":
        try:
            from curl_cffi import requests as cf
            r = cf.get(url, impersonate="chrome124", cookies=_DEFAULT_COOKIES, timeout=30)
            if r.status_code != 200:
                print(f"  PAT: HTTP {r.status_code} {url}")
                return None
            if "Incapsula" in r.text and len(r.text) < 5000:
                print(f"  PAT: Incapsula blocked — cookies may have expired")
                return None
            return r.text
        except Exception as e:
            print(f"  PAT fetch error: {e}")
            return None

    def scrape(self, max_pages=3):
        print(f"Scraping {self.name}...")
        results = []

        for page_num in range(1, max_pages + 1):
            url = self.BASE_URL if page_num == 1 else f"{self.BASE_URL}page/{page_num}/"
            html = self._fetch(url)
            if not html:
                break

            soup = BeautifulSoup(html, "html.parser")
            articles = soup.select("article.uagb-post__inner-wrap")
            if not articles:
                break

            for art in articles:
                a_tag = art.select_one("h4 a, h3 a, h2 a")
                if not a_tag:
                    continue
                title = a_tag.get_text(strip=True)
                href  = a_tag.get("href", "").strip()
                if not href or not title:
                    continue

                time_tag = art.select_one("time[datetime]")
                dt = _parse_iso_date(time_tag["datetime"]) if time_tag else None

                results.append({
                    "agency":    "การท่าเรือแห่งประเทศไทย (กทท.)",
                    "unit":      "การท่าเรือแห่งประเทศไทย",
                    "title":     title,
                    "date":      _to_thai_display(dt),
                    "sort_date": _to_sort_date(dt),
                    "url":       href,
                    "source":    self.name,
                    "status":    "ขายทอดตลาด",
                })

            if not soup.select_one("a.next, a[rel='next'], .page-numbers.next"):
                break

        print(f"  {self.name}: {len(results)} items")
        return results
