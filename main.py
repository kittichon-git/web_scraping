import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from scrapers.doh_scraper import DOHScraper
from scrapers.gprocurement_scraper import GProcurementScraper
from scrapers.oncb_scraper import ONCBScraper
from scrapers.pea_scraper import PEAScraper
from scrapers.rid_scraper import RIDScraper
from scrapers.customs_scraper import CustomsScraper
from scrapers.fio_scraper import FIOScraper
from scrapers.revenue_scraper import RevenueScraper
from scrapers.thailandpost_scraper import ThailandPostScraper
from scrapers.ago_scraper import AGOScraper
from scrapers.pwa_scraper import PWAScraper
from scrapers.treasury_scraper import TreasuryScraper
from scrapers.mwa_scraper import MWAScraper
from scrapers.dld_scraper import DLDScraper
from scrapers.mea_scraper import MEAScraper
from scrapers.nt_scraper import NTScraper
from scrapers.egat_scraper import EgatScraper
from scrapers.npnt_scraper import NPNTScraper
from scrapers.bkk_scraper import BKKScraper
from scrapers.pat_scraper import PATScraper
from scrapers.chula_scraper import ChulaScraper
from scrapers.nu_scraper import NUScraper
from utils.db import upsert_auctions, get_existing_urls
from utils.run_logger import RunLogger, _read_runs_json
from scrapers.gprocurement_scraper import GProcurementScraper as _GPScraper


def get_th_now():
    return datetime.now(timezone.utc) + timedelta(hours=7)


def _print_last_run_header(rl):
    """แสดงข้อมูลรอบก่อนให้พนักงานเห็นก่อนเริ่มรัน"""
    from datetime import datetime, timezone
    runs = _read_runs_json()
    last_ok = next((r for r in reversed(runs) if r.get("overall_status") == "ok"), None)
    print()
    print("=" * 48)
    if last_ok:
        try:
            last_dt = datetime.fromisoformat(last_ok["ts_end"])
            gap_h = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
            last_th = (last_dt + __import__('datetime').timedelta(hours=7)).strftime("%H:%M น. %d/%m/%y")
            gap_label = f"{gap_h:.0f} ชม.ที่แล้ว" if gap_h >= 1 else f"{gap_h*60:.0f} นาทีที่แล้ว"
            warn = "  ⚠️  นานผิดปกติ!" if gap_h > 26 else ""
            print(f"  รอบสำเร็จล่าสุด: {last_th} ({gap_label}){warn}")
            print(f"  (new={last_ok.get('items_new',0)} scraped={last_ok.get('items_scraped',0)})")
        except Exception:
            print("  รอบสำเร็จล่าสุด: ไม่สามารถอ่านได้")
    else:
        print("  รอบสำเร็จล่าสุด: ไม่มีประวัติ (รอบแรก)")
    print("  กำลังเริ่มรัน...")
    print("=" * 48)
    print()


def main():
    rl = RunLogger()
    rl.logger.info(f"=== Starting Auction Scraper run_id={rl.run_id} ===")
    rl.check_staleness()
    _print_last_run_header(rl)

    scrapers = [
        DOHScraper(),
        GProcurementScraper(),
        ONCBScraper(),
        PEAScraper(),
        RIDScraper(),
        CustomsScraper(),
        FIOScraper(),
        RevenueScraper(),
        ThailandPostScraper(),
        AGOScraper(),
        PWAScraper(),
        TreasuryScraper(),
        MWAScraper(),
        DLDScraper(),
        MEAScraper(),
        NTScraper(),
        EgatScraper(),
        NPNTScraper(),
        BKKScraper(),
        PATScraper(),
        ChulaScraper(),
        NUScraper(),
    ]

    failed_scrapers = []

    def run_scraper(scraper):
        ctx = rl.scraper_context(scraper.name)
        try:
            results = scraper.scrape()
            ctx.rows_fetched = len(results) if results else 0
            if not results:
                # นับเป็น failed เพื่อไม่ให้หลุดเงียบ
                ctx.add_error("ไม่พบข้อมูล (0 รายการ)")
            else:
                # provinces_seen: รหัสจังหวัดหลัง "ที่" (เช่น "นศ" จาก "ที่ นศ 71202/587")
                for r in results:
                    unit = r.get("unit", "") or ""
                    prov = _GPScraper.extract_province(unit) if r.get("source") == "G-Procurement" \
                        else unit.split(" ")[0].strip()
                    if prov:
                        ctx.provinces_seen.add(prov)
            rl.log_scraper_result(ctx)
            return (results or [], scraper.name, None)
        except Exception as e:
            err_msg = str(e)[:200]
            ctx.add_error(err_msg)
            rl.log_scraper_result(ctx)
            return ([], scraper.name, err_msg)

    all_results = []
    with ThreadPoolExecutor(max_workers=14) as executor:
        futures = {executor.submit(run_scraper, s): s for s in scrapers}
        for future in as_completed(futures):
            results, sname, err = future.result()
            all_results.extend(results)
            if err is not None:
                failed_scrapers.append((sname, err))

    # ── CANARY ──────────────────────────────────────────────
    # e-GP: row-count floor + multi-province
    egp_rows = [r for r in all_results if r.get("source") == "G-Procurement"]
    egp_provinces = {
        _GPScraper.extract_province(r.get("unit", "") or "")
        for r in egp_rows
        if (r.get("unit", "") or "").strip()
    } - {""}  # กรอง empty string ออก
    rl.run_canary("G-Procurement", len(egp_rows), egp_provinces)

    # global: ถ้าไม่มีผลลัพธ์เลย
    if not all_results:
        rl.logger.error("CANARY FAIL [GLOBAL]: 0 รายการจากทุก scraper รวมกัน!")

    # ── DEDUP & RETENTION ────────────────────────────────────
    rl.logger.info("กำลังตรวจสอบข้อมูลใน Supabase...")
    existing_urls = get_existing_urls()
    rl.logger.info(f"มีในระบบแล้ว {len(existing_urls)} รายการ")

    th_now = get_th_now()
    now_date_str = th_now.strftime('%d/%m/%Y')
    today_sort_date = th_now.strftime('%Y-%m-%d')
    retention_days = 60

    new_items = []
    for item in all_results:
        if not item.get('sort_date') or item.get('sort_date') == "0000-00-00":
            item['sort_date'] = today_sort_date
            if not item.get('date') or item.get('date') == "ไม่ระบุวันที่":
                item['date'] = f"ตรวจพบเมื่อ {now_date_str}"

        if item['url'] not in existing_urls:
            sort_date_str = item.get('sort_date')
            if sort_date_str:
                try:
                    # FIX: make item_date tz-aware (UTC) เพื่อเทียบกับ th_now ที่ tz-aware
                    item_date = datetime.strptime(sort_date_str, '%Y-%m-%d').replace(
                        tzinfo=timezone.utc
                    )
                    delta = th_now - item_date
                    if delta.days > retention_days:
                        continue
                except Exception as e:
                    rl.logger.error(
                        f"retention filter error: sort_date={sort_date_str!r} "
                        f"url={item.get('url', '')[:60]} err={e}"
                    )
            new_items.append(item)
            existing_urls.add(item['url'])

    # ── SUMMARY TABLE ────────────────────────────────────────
    rl.logger.info(f"\nStats: {len(new_items)} New, {len(all_results)} Total Scraped")
    print("\n" + "=" * 55)
    print(f" {'Agency':<40} | {'New':<5} | {'Total':<5}")
    print("-" * 55)

    new_counts = {}
    for item in new_items:
        agency = item.get('agency', 'Unknown')
        new_counts[agency] = new_counts.get(agency, 0) + 1

    total_counts = {}
    for item in all_results:
        agency = item.get('agency', 'Unknown')
        total_counts[agency] = total_counts.get(agency, 0) + 1

    all_agencies = sorted(set(total_counts) | set(new_counts))
    for agency in all_agencies:
        agency_display = agency[:39]
        padding = " " * max(0, 40 - len(agency_display))
        print(f" {agency_display}{padding} | {new_counts.get(agency, 0):<5} | {total_counts.get(agency, 0):<5}")

    print("-" * 55)
    print(f" {'TOTAL':<40} | {len(new_items):<5} | {len(all_results):<5}")
    print("=" * 55)

    if failed_scrapers:
        rl.logger.warning(f"*** {len(failed_scrapers)} scraper(s) มีปัญหา ***")
        print("-" * 55)
        for name, reason in failed_scrapers:
            rl.logger.error(f"  [FAIL] {name}: {reason}")
        print("-" * 55)

    # ── UPSERT ──────────────────────────────────────────────
    if new_items:
        rl.logger.info("กำลังบันทึกลง Supabase...")
        upsert_auctions(new_items)
    else:
        rl.logger.info("ไม่มีข้อมูลใหม่ในรอบนี้")

    rl.finalize(len(new_items), len(all_results), failed_scrapers)

    # ── OPERATOR RUN SUMMARY (ภาษาไทย อ่านง่าย) ─────────────
    canary_ok = (len(egp_rows) >= 3) and (len(egp_provinces) >= 2) and bool(all_results)
    has_fail = bool(failed_scrapers) or not canary_ok
    status_icon = "✅ OK" if not has_fail else "⚠️  ต้องตรวจ"
    th_time = get_th_now().strftime("%H:%M น. %d/%m/%y")

    print()
    print("=" * 48)
    print(f"  สรุปรอบ {th_time}")
    print(f"  สถานะ: {status_icon}")
    print(f"  ดึงได้ {len(all_results)} รายการ จาก {len(egp_provinces)} จังหวัด (e-GP)")
    print(f"  ใหม่ {len(new_items)} รายการ | ซ้ำ/เก่า {len(all_results) - len(new_items)} รายการ")
    if failed_scrapers:
        print(f"  Scraper ล้มเหลว: {', '.join(n for n, _ in failed_scrapers)}")
    if not canary_ok:
        if len(egp_rows) < 3:
            print(f"  !! e-GP ดึงได้แค่ {len(egp_rows)} รายการ (ต่ำกว่าปกติ)")
        if len(egp_provinces) < 2:
            print(f"  !! e-GP เห็นแค่ {len(egp_provinces)} จังหวัด (ต่ำกว่าปกติ)")
        print()
        print("  >>> รันซ้ำก่อนปิด / แจ้งหัวหน้า <<<")
    print("=" * 48)


if __name__ == "__main__":
    main()
