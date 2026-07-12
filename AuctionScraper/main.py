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
from scrapers.kku_scraper import KKUScraper
from scrapers.cmu_scraper import CMUScraper
from scrapers.md_scraper import MDScraper
from utils.db import upsert_auctions, get_existing_urls


def get_th_now():
    return datetime.now(timezone.utc) + timedelta(hours=7)


def main():
    print(f"--- Starting Auction Scraper {datetime.now()} ---")

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
        KKUScraper(),
        CMUScraper(),
        MDScraper(),
    ]

    failed_scrapers = []

    def run_scraper(scraper):
        try:
            results = scraper.scrape()
            if not results:
                failed_scrapers.append((scraper.name, "ไม่พบข้อมูล (0 รายการ)"))
            return results
        except Exception as e:
            failed_scrapers.append((scraper.name, str(e)[:120]))
            return []

    all_results = []
    with ThreadPoolExecutor(max_workers=14) as executor:
        futures = {executor.submit(run_scraper, s): s for s in scrapers}
        for future in as_completed(futures):
            all_results.extend(future.result())

    # ดึง existing URLs จาก Supabase
    print("\nกำลังตรวจสอบข้อมูลใน Supabase...")
    existing_urls = get_existing_urls()
    print(f"มีในระบบแล้ว {len(existing_urls)} รายการ")

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
                    item_date = datetime.strptime(sort_date_str, '%Y-%m-%d')
                    delta = th_now - item_date
                    if delta.days > retention_days:
                        continue
                except Exception:
                    pass
            new_items.append(item)
            existing_urls.add(item['url'])

    # --- Summary ---
    print(f"\nStats: {len(new_items)} New, {len(existing_urls)} Total")
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
        print(f"\n*** WARNING: {len(failed_scrapers)} scraper(s) มีปัญหา ***")
        print("-" * 55)
        for name, reason in failed_scrapers:
            print(f"  [FAIL] {name}: {reason}")
        print("-" * 55)
    print()

    # บันทึกลง Supabase เฉพาะรายการใหม่
    if new_items:
        print("กำลังบันทึกลง Supabase...")
        upsert_auctions(new_items)
    else:
        print("ไม่มีข้อมูลใหม่ในรอบนี้")

    print("--- Finished ---")


if __name__ == "__main__":
    main()
