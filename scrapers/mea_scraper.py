from scrapers.base import BaseScraper
from bs4 import BeautifulSoup
import urllib.parse
import re


class MEAScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="MEA", base_url="https://www.mea.or.th")
        self.list_url = "https://www.mea.or.th/public-relations/dispose-assets"

    def _get_announcement_urls(self):
        """ดึง URL ของทุกประกาศจากหน้า listing"""
        html = self.fetch(self.list_url)
        if not html:
            return []
        soup = BeautifulSoup(html, 'html.parser')
        urls = []
        for card in soup.find_all(class_='card-item'):
            a_tag = card.find('a', href=True)
            if a_tag and '/dispose-assets/' in a_tag['href']:
                full_url = urllib.parse.urljoin(self.base_url, a_tag['href'])
                title = card.find('h3')
                pub_date_p = card.find('p', class_='card-date')
                pub_date = " ".join(t.strip() for t in pub_date_p.strings if t.strip()) if pub_date_p else ""
                urls.append({
                    "url": full_url,
                    "title": title.get_text(strip=True) if title else "",
                    "pub_date": pub_date,
                })
        return urls

    def _parse_detail(self, html, announcement):
        """ดึงทุกแถวในตารางของหน้าประกาศ — 1 แถว = 1 รายการ"""
        soup = BeautifulSoup(html, 'html.parser')
        div = soup.find('div', class_='content-md2')
        if not div:
            return []
        table = div.find('table')
        if not table:
            return []

        results = []
        rows = table.find_all('tr')

        for row in rows:
            cells = row.find_all('td')
            if not cells:
                continue  # ข้าม header row (<th>)

            # ดึง links จากแถว — link แรก = ดูรายการ, link สอง = ดูรูป
            links = [a['href'] for a in row.find_all('a', href=True)]
            if not links:
                continue  # ข้ามแถวที่ไม่มี link (อาจเป็น footer)

            # col[1] = รายการ เช่น "ท.020/2569 ดูรายการ | ดูรูป"
            # ดึงเฉพาะ ref code (ก่อนคำว่า "ดูรายการ")
            col1_text = cells[1].get_text(' ', strip=True) if len(cells) > 1 else ""
            ref_code = re.split(r'ดูรายการ|ดูรูป|\|', col1_text)[0].strip()

            item_type = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            guarantee = cells[3].get_text(strip=True) if len(cells) > 3 else ""
            row_date = cells[4].get_text(strip=True) if len(cells) > 4 else ""

            # fallback วันที่จากหน้าประกาศถ้าแถวไม่มีวันที่
            display_date = row_date if row_date else announcement["pub_date"]
            sort_date = self.normalize_thai_date(display_date)

            # title = ชื่อประกาศ + ref code + ชนิด
            title = f"{announcement['title']} — {ref_code} ({item_type})" if item_type else f"{announcement['title']} — {ref_code}"

            # dedup key = link ดูรายการ (unique ต่อ item)
            # ถ้าไม่มี link ใช้ announcement URL + "#" + ref_code
            item_url = links[0] if links else f"{announcement['url']}#{ref_code}"

            results.append({
                "agency": "การไฟฟ้านครหลวง (MEA)",
                "unit": ref_code,
                "title": title,
                "date": display_date,
                "sort_date": sort_date,
                "url": item_url,
                "source": self.name,
                "status": "ประกาศขายทอดตลาด",
            })

        return results

    def scrape(self, max_pages=1):
        print(f"Scraping {self.name}...")
        announcements = self._get_announcement_urls()
        if not announcements:
            print("  MEA: no announcements found")
            return []

        all_results = []
        for ann in announcements:
            html = self.fetch(ann["url"])
            if not html:
                continue
            items = self._parse_detail(html, ann)
            all_results.extend(items)

        print(f"  MEA: found {len(all_results)} items from {len(announcements)} announcements")
        return all_results
