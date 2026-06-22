"""
Unit test: BUG A fix — parse date from setFullDateByLocale() script tag.
Run: python -m pytest tests/test_gprocurement_date.py -v
  OR: python tests/test_gprocurement_date.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.gprocurement_scraper import GProcurementScraper

# ── Fixtures ──────────────────────────────────────────────────────────────────

# Fixture A: แถว "นศ 71202/587" — date ใน script tag (ค.ศ. 2026)
FIXTURE_CHANGKLANG = """
<html><body><table>
<tr>
  <td>เลขที่หนังสือ</td><td>วันที่</td><td>รายการ</td><td>หน่วยงาน</td><td>ดาวน์โหลด</td>
</tr>
<tr>
  <td>ที่ นศ 71202/587</td>
  <td><script>setFullDateByLocale('2026/06/16')</script></td>
  <td>ขายทอดตลาดพัสดุที่ชำรุด</td>
  <td>อบต.ช้างกลาง</td>
  <td><a href="/wps/wcm/connect/593a8301-a70d-4a11-9afc-82808d26a977/file.pdf">ดาวน์โหลด</a></td>
</tr>
</table></body></html>
"""

# Fixture B: แถว fallback — ไม่มี script tag
FIXTURE_NO_SCRIPT = """
<html><body><table>
<tr>
  <td>เลขที่หนังสือ</td><td>วันที่</td><td>รายการ</td><td>หน่วยงาน</td><td>ดาวน์โหลด</td>
</tr>
<tr>
  <td>กบ 99999/001</td>
  <td></td>
  <td>ขายทอดตลาดอื่น</td>
  <td>หน่วยงาน X</td>
  <td><a href="/wps/wcm/connect/abc/other.pdf">ดาวน์โหลด</a></td>
</tr>
</table></body></html>
"""

# Fixture C: แถว date script อื่น (ปีต่างกัน)
FIXTURE_OTHER_DATE = """
<html><body><table>
<tr>
  <td>เลขที่หนังสือ</td><td>วันที่</td><td>รายการ</td><td>หน่วยงาน</td><td>ดาวน์โหลด</td>
</tr>
<tr>
  <td>กทม 00001/999</td>
  <td><script>setFullDateByLocale('2025/12/31')</script></td>
  <td>ขายทอดตลาดสิ้นปี</td>
  <td>หน่วยงาน Y</td>
  <td><a href="/wps/wcm/connect/xyz/file.pdf">ดาวน์โหลด</a></td>
</tr>
</table></body></html>
"""

# ── Tests ─────────────────────────────────────────────────────────────────────

def test_bug_a_changklang():
    """นศ 71202/587 ต้องได้ sort_date=2026-06-16 (ไม่ใช่วันที่ scrape)"""
    scraper = GProcurementScraper()
    results = scraper.parse(FIXTURE_CHANGKLANG)
    assert len(results) == 1, f"expected 1 row, got {len(results)}"
    r = results[0]
    assert r["unit"] == "ที่ นศ 71202/587", f"unit mismatch: {r['unit']!r}"
    assert r["sort_date"] == "2026-06-16", (
        f"BUG A: sort_date={r['sort_date']!r} — ควรเป็น 2026-06-16 (CE ไม่ลบ 543)"
    )
    assert r["date"] == "2026-06-16", f"date mismatch: {r['date']!r}"
    print(f"PASS test_bug_a_changklang: sort_date={r['sort_date']} unit={r['unit']}")


def test_bug_a_no_script_fallback():
    """ไม่มี script tag → fallback ไม่ crash, sort_date ไม่ใช่ WRONG date"""
    scraper = GProcurementScraper()
    results = scraper.parse(FIXTURE_NO_SCRIPT)
    assert len(results) == 1, f"expected 1 row, got {len(results)}"
    r = results[0]
    # fallback: cols[1].text = '' → date_str = "ไม่ระบุวันที่" → sort_date = "0000-00-00"
    assert r["sort_date"] == "0000-00-00", (
        f"fallback sort_date ควรเป็น 0000-00-00 ได้ {r['sort_date']!r}"
    )
    print(f"PASS test_bug_a_no_script_fallback: sort_date={r['sort_date']}")


def test_bug_a_no_subtract_543():
    """ตรวจว่าไม่ลบ 543 — '2025/12/31' ต้องได้ 2025-12-31 ไม่ใช่ 1482-12-31"""
    scraper = GProcurementScraper()
    results = scraper.parse(FIXTURE_OTHER_DATE)
    assert len(results) == 1
    r = results[0]
    assert r["sort_date"] == "2025-12-31", (
        f"ลบ 543 ผิด: sort_date={r['sort_date']!r} — ควรเป็น 2025-12-31"
    )
    assert r["sort_date"] != "1482-12-31", "ลบ 543 ผิด!"
    print(f"PASS test_bug_a_no_subtract_543: sort_date={r['sort_date']}")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    test_bug_a_changklang()
    test_bug_a_no_script_fallback()
    test_bug_a_no_subtract_543()
    print("\nALL TESTS PASSED")
