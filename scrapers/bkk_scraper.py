from scrapers.base import BaseScraper
import requests
import urllib3
from datetime import datetime, timezone, timedelta

urllib3.disable_warnings()

_BKK_TZ = timezone(timedelta(hours=7))

_THAI_MONTHS_SHORT = [
    "", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
    "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
]


def _parse_iso_to_bkk(iso_str: str):
    """Convert ISO UTC string e.g. '2026-06-29T17:00:00Z' → Bangkok datetime."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.astimezone(_BKK_TZ)
    except Exception:
        return None


def _format_thai_date(dt) -> str:
    """Format Bangkok datetime → '30 มิ.ย. 2569' (BE)."""
    if dt is None:
        return ""
    be_year = dt.year + 543
    month = _THAI_MONTHS_SHORT[dt.month]
    return f"{dt.day} {month} {be_year}"


def _format_sort_date(dt) -> str:
    """Format Bangkok datetime → 'YYYY-MM-DD' (CE)."""
    if dt is None:
        return "0000-00-00"
    return dt.strftime("%Y-%m-%d")


class BKKScraper(BaseScraper):
    """กรุงเทพมหานคร (กทม.) — eGP BMA2 Auction Announcements JSON API."""

    API_URL    = "https://egp2.bangkok.go.th/appapi/api/AuctionAnnouncements/GetAuctionAnnouncementFromFilter"
    DETAIL_URL = "https://egp2.bangkok.go.th/auction/{uuid}"

    def __init__(self):
        super().__init__(
            name="กรุงเทพมหานคร (กทม.)",
            base_url="https://egp2.bangkok.go.th",
        )

    def scrape(self, max_pages=10):
        print(f"Scraping {self.name}...")
        results = []
        page = 1

        while page <= max_pages:
            params = {
                "auctionAnnouncementSearchText": "",
                "masterBudgetYearId":            "",
                "masterOrgGroupId":              "",
                "masterOrgDepartmentId":         "",
                "startDate":                     "",
                "endDate":                       "",
                "pageNo":                        str(page),
                "pageSize":                      "20",
                "sortBy":                        "desc",
            }
            try:
                r = requests.get(
                    self.API_URL,
                    params=params,
                    headers={
                        **self.headers,
                        "Accept":  "application/json, text/plain, */*",
                        "Referer": "https://egp2.bangkok.go.th/auction?sortBy=desc",
                    },
                    timeout=30,
                    verify=False,
                )
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                print(f"  Error page {page}: {e}")
                break

            items = data.get("data", [])
            if not items:
                break

            for item in items:
                uuid  = item.get("auctionAnnouncementId", "")
                title = item.get("auctionAnnouncementAuctionName", "").strip()
                org   = item.get("masterOrgGroupName") or ""
                dept  = item.get("masterOrgDepartmentName") or ""
                unit  = f"{org} {dept}".strip() if dept else org.strip()
                dt    = _parse_iso_to_bkk(item.get("auctionAnnouncementAnnounceDate", ""))
                url   = self.DETAIL_URL.format(uuid=uuid)

                results.append({
                    "agency":    "กรุงเทพมหานคร (กทม.)",
                    "unit":      unit,
                    "title":     title,
                    "date":      _format_thai_date(dt),
                    "sort_date": _format_sort_date(dt),
                    "url":       url,
                    "source":    self.name,
                    "status":    "ขายทอดตลาด",
                })

            if not data.get("hasNextPage", False):
                break
            page += 1

        print(f"  {self.name}: {len(results)} items")
        return results
