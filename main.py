import os
import json
from datetime import datetime, timedelta
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
from utils.db import upsert_auctions

# --- Settings ---
DATA_DIR = 'data'
HISTORY_FILE = os.path.join(DATA_DIR, 'history.json')
REPORTS_DIR = 'reports'
DATA_JSON_FILE = os.path.join(REPORTS_DIR, 'data.json')

def get_th_now():
    """Get current time in Thailand (UTC+7)"""
    from datetime import datetime, timedelta, timezone
    # Fix DeprecationWarning by using timezone-aware objects
    return datetime.now(timezone.utc) + timedelta(hours=7)

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_history(history):
    os.makedirs(DATA_DIR, exist_ok=True)
    # 3. ล้างข้อมูลเก่า (Data Retention: 60 days)
    history = purge_old_history(history, days=60)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def purge_old_history(history, days=60):
    if not history:
        return []
    
    # ใช้เวลาประเทศไทยเป็นเกณฑ์
    cutoff_date = get_th_now()
    unique_history = []
    removed_count = 0
    
    for item in history:
        sort_date_str = item.get('sort_date')
        
        # ถ้าไม่มี sort_date หรือเป็นค่าว่าง (ซึ่งไม่ควรเกิดขึ้นแล้วหลังแก้ไข main)
        # ให้พยายามข้ามไปก่อน หรือถ้ามี scraped_at ก็อาจจะใช้แทน
        if not sort_date_str or sort_date_str == "0000-00-00":
            # หากยังหาค่าไม่ได้ ให้เก็บไว้ก่อน (Safe side)
            unique_history.append(item)
            continue
            
        try:
            item_date = datetime.strptime(sort_date_str, '%Y-%m-%d')
            delta = cutoff_date - item_date
            if delta.days <= days:
                unique_history.append(item)
            else:
                removed_count += 1
        except:
            # หาก Parse วันที่ไม่ได้ ให้เก็บไว้ก่อน
            unique_history.append(item)
            
    if removed_count > 0:
        print(f"Purged {removed_count} old entries (older than {days} days)")
    return unique_history

def generate_report(new_items, history):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    # ใช้ตัวช่วยเก็ตเวลาไทย
    th_now = get_th_now()
    date_str = th_now.strftime('%d/%m/%Y %H:%M')
    
    # Sort items by scraped_at descending, then sort_date descending
    all_combined = new_items + history
    # Remove duplicates based on URL
    seen_urls = set()
    unique_items = []
    for item in all_combined:
        if item['url'] not in seen_urls:
            unique_items.append(item)
            seen_urls.add(item['url'])
    
    def sort_key(x):
        scraped = x.get('scraped_at', '00/00/0000')
        parts = scraped.split('/')
        if len(parts) == 3:
            scraped_sortable = f"{parts[2]}{parts[1].zfill(2)}{parts[0].zfill(2)}"
        else:
            scraped_sortable = "00000000"
        return (scraped_sortable, x.get('sort_date', '0000-00-00'))

    unique_items.sort(key=sort_key, reverse=True)

    new_urls = [n['url'] for n in new_items]
    historical_items = [item for item in unique_items if item['url'] not in new_urls]
    
    all_data = {
        "new": [item for item in unique_items if item['url'] in new_urls], # Keep new_items sorted correctly
        "historical": historical_items,
        "updated_at": date_str
    }
    
    # 1. ยังคงบันทึกข้อมูลลงใน data.json (เผื่อไว้ให้ระบบอื่นใช้)
    with open(DATA_JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    # แปลงข้อมูลเป็น JSON string เพื่อฝังลงใน HTML
    data_json = json.dumps(all_data, ensure_ascii=False)

    # Calculate Thailand Time (UTC+7) for the report
    th_now = get_th_now()
    update_time = th_now.strftime('%d/%m/%Y %H:%M')
    
    # 2. สร้างหน้า index.html (ฝังข้อมูลลงไปเลยเพื่อให้รันแบบ offline ได้)
    html_template = f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="robots" content="noindex, nofollow">
        <title>Auction Dashboard - อัพเดทล่าสุด {update_time} (เวลาไทย)</title>
        <link rel="stylesheet" href="styles.css">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Sarabun:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            :root {{
                --primary: #1976d2;
                --bg: #f8f9fa;
                --text: #333;
                --unread-bg: #fff;
                --read-bg: #f5f5f5;
            }}
            .table-container {{
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                overflow-x: auto;
                margin-bottom: 2rem;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                min-width: 900px;
            }}
            th, td {{
                padding: 12px 15px;
                text-align: left;
                border-bottom: 1px solid #eee;
            }}
            th {{
                background: #f1f3f5;
                font-weight: 600;
                color: #555;
                position: sticky;
                top: 0;
            }}
            tr.read {{
                background-color: #f8f9fa !important;
                opacity: 0.5;
            }}
            tr.read .title {{ 
                color: #888 !important;
                text-decoration: line-through;
            }}
            tr.read .agency-badge, tr.read .fetch-date-badge {{
                opacity: 0.7;
                filter: grayscale(1);
            }}
            .agency-badge {{
                font-size: 0.7rem;
                padding: 2px 6px;
                border-radius: 4px;
                background: #e9ecef;
                color: #495057;
                white-space: nowrap;
            }}
            .fetch-date-badge {{
                display: inline-block;
                font-size: 0.85rem;
                padding: 4px 10px;
                border-radius: 6px;
                background: #1976d2;
                color: white;
                font-weight: 700;
                white-space: nowrap;
            }}
            .title {{
                font-weight: 600;
                font-size: 0.95rem;
                color: var(--primary);
                text-decoration: none;
                display: block;
                max-width: 450px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }}
            .title:hover {{ text-decoration: underline; }}
            .btn.btn-preview {{
                background: #4caf50;
            }}
            .btn.btn-preview:hover {{
                background: #45a049;
            }}
            .http-warning {{
                background: #fff3e0;
                border-left: 4px solid #ff9800;
                padding: 10px 15px;
                margin-bottom: 20px;
                font-size: 0.9rem;
            }}
            tr.new-row {{
                background-color: #fffde7;
            }}
            .new-badge {{
                font-size: 0.75rem;
                padding: 2px 6px;
                border-radius: 4px;
                background: #ff5722;
                color: white;
                font-weight: bold;
                margin-right: 8px;
                vertical-align: middle;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>🚀 ระบบแจ้งเตือนประมูล (GitHub Dashboard)</h1>
                <p class="subtitle" id="last-update">อัพเดทล่าสุด: {all_data['updated_at']}</p>
            </header>

            <div class="filter-bar">
                <div class="filter-group">
                    <button class="page-btn active" onclick="setFilter('all', this)">ทั้งหมด</button>
                    <button class="page-btn" onclick="setFilter('unread', this)">ยังไม่ได้อ่าน</button>
                </div>
                <div class="filter-group">
                    <select id="agency-filter" class="select-filter" onchange="updateAgencyFilter()">
                        <option value="all">ทุกหน่วยงาน</option>
                        <option value="กรมทางหลวง">กรมทางหลวง</option>
                        <option value="กรมบัญชีกลาง (e-GP)">กรมบัญชีกลาง (e-GP)</option>
                        <option value="สำนักงาน ป.ป.ส.">สำนักงาน ป.ป.ส.</option>
                        <option value="การไฟฟ้าส่วนภูมิภาค (PEA)">การไฟฟ้าส่วนภูมิภาค (PEA)</option>
                        <option value="กรมชลประทาน (RID)">กรมชลประทาน (RID)</option>
                        <option value="กรมศุลกากร">กรมศุลกากร</option>
                        <option value="องค์การอุตสาหกรรมป่าไม้ (ออป.)">องค์การอุตสาหกรรมป่าไม้ (ออป.)</option>
                        <option value="กรมสรรพากร">กรมสรรพากร</option>
                        <option value="ไปรษณีย์ไทย">บริษัท ไปรษณีย์ไทย จำกัด</option>
                        <option value="สำนักงานอัยการสูงสุด">สำนักงานอัยการสูงสุด</option>
                        <option value="การประปาส่วนภูมิภาค (PWA)">การประปาส่วนภูมิภาค (PWA)</option>
                        <option value="กรมธนารักษ์">กรมธนารักษ์</option>
                    </select>
                </div>
            </div>
            
            <section>
                <div class="section-header">
                    <h2 class="section-title">✨ รายการประกาศทั้งหมด</h2>
                    <span class="badge" id="total-count">0 รายการ</span>
                </div>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th style="width: 150px;">วันที่ระบบพบข่าว</th>
                                <th style="width: 120px;">หน่วยงาน</th>
                                <th>หัวข้อข่าว/ประกาศ (คลิกเพื่อเปิด)</th>
                                <th style="width: 140px;">วันที่ประกาศ</th>
                            </tr>
                        </thead>
                        <tbody id="items-container"></tbody>
                    </table>
                </div>
                <div class="pagination" id="pagination"></div>
            </section>

            <footer>
                <p>© 2026 Auction Web Scraper System | Running on GitHub Pages</p>
            </footer>
        </div>

        <script>
            // ฝังข้อมูลลงในตัวแปรโดยตรง เพื่อให้เปิดแบบ Offline ได้
            let data = {data_json};
            const itemsPerPage = 50;
            let currentHistoryPage = 1;
            let currentFilter = 'all';
            let currentAgency = 'all';

            function getReadItems() {{
                return JSON.parse(localStorage.getItem('read_urls') || '[]');
            }}

            function filterItems(items) {{
                const readUrls = getReadItems();
                return items.filter(item => {{
                    const isItemRead = readUrls.includes(item.url);
                    const matchesUnread = currentFilter === 'all' || !isItemRead;
                    const matchesAgency = currentAgency === 'all' || item.agency === currentAgency;
                    return matchesUnread && matchesAgency;
                }});
            }}

            function updateAgencyFilter() {{
                currentAgency = document.getElementById('agency-filter').value;
                renderItems(1);
            }}

            function renderItems(page = 1) {{
                currentHistoryPage = page;
                const container = document.getElementById('items-container');
                
                // เครื่องหมายสำหรับข่าวที่เพิ่งค้นพบในรอบรันล่าสุด
                const newItemsMod = data.new.map(item => ({{...item, isNewToday: true}}));
                const histItemsMod = data.historical.map(item => ({{...item, isNewToday: false}}));
                
                // โครงสร้างใหม่: นำข่าวใหม่ล่าสุดจริงๆ ไว้บนสุดเสมอ ตามด้วยประวัติ
                // (Python หลังบ้านเรียงลำดับถูกจัดมาให้สมบูรณ์แล้ว ไม่ต้อง sort ด้วย JS อีก)
                let allItems = [...newItemsMod, ...histItemsMod];
                
                // ตัวกรอง (Filter)
                const filtered = filterItems(allItems);
                
                // เรียงลำดับเพิ่มเติม: ให้ข่าวที่ "ยังไม่ได้อ่าน" อยู่ด้านบนเสมอ
                const readUrls = getReadItems();
                filtered.sort((a, b) => {{
                    const aIsRead = readUrls.includes(a.url);
                    const bIsRead = readUrls.includes(b.url);
                    if (aIsRead && !bIsRead) return 1;   // a อ่านแล้ว ให้ลงไปข้างล่าง
                        if (!aIsRead && bIsRead) return -1;  // a ยังไม่อ่าน ให้อยู่ข้างบน
                        return 0; // ถ้าอ่านแล้วหรือยังไม่อ่านทั้งคู่ ให้คงลำดับเดิมไว้ (ตามที่ Python จัดมา)
                }});
                
                document.getElementById('total-count').innerText = filtered.length + " รายการ";
                
                const start = (page - 1) * itemsPerPage;
                const end = start + itemsPerPage;
                const pageItems = filtered.slice(start, end);

                if (filtered.length === 0) {{
                    container.innerHTML = "<tr><td colspan='4' class='no-data' style='text-align:center; padding: 20px;'>ไม่มีรายการที่ต้องการแสดง</td></tr>";
                    document.getElementById('pagination').innerHTML = '';
                    return;
                }}

                container.innerHTML = pageItems.map(item => renderCard(item)).join('');
                renderPagination(filtered.length);
            }}

            function renderCard(item) {{
                const isRead = getReadItems().includes(item.url);
                const scrapeDate = item.scraped_at ? `<span class="fetch-date-badge">${{item.scraped_at}}</span>` : '-';
                
                // Highlight for new items from latest run
                const rowClass = isRead ? 'read' : (item.isNewToday ? 'new-row' : '');
                const newBadge = item.isNewToday ? `<span class="new-badge">⭐ ข่าวใหม่ (ล่าสุด)</span>` : '';
                
                return `
                    <tr class="${{rowClass}}" data-url="${{item.url}}">
                        <td>${{scrapeDate}}</td>
                        <td><span class="agency-badge">${{item.agency}}</span></td>
                        <td>
                            ${{newBadge}}
                            <a href="${{item.url}}" class="title" style="display:inline-block; vertical-align:middle; width: calc(100% - 100px);" title="${{item.title}}" target="_blank" onclick="markAsRead(event, '${{item.url}}')">
                                ${{item.title}}
                            </a>
                            <small style="color: #888; display:block; margin-top:4px;">🏢 ${{item.unit || 'N/A'}}</small>
                        </td>
                        <td><span style="font-size: 0.9rem;">${{item.date}}</span></td>
                    </tr>
                `;
            }}

            function renderPagination(totalItems) {{
                const totalPages = Math.ceil(totalItems / itemsPerPage);
                const pagination = document.getElementById('pagination');
                if (totalPages <= 1) {{
                    pagination.innerHTML = '';
                    return;
                }}

                let buttons = '';
                
                // ปุ่ม "« ก่อนหน้า"
                if (currentHistoryPage > 1) {{
                    buttons += `<button class="page-btn" onclick="renderItems(${{currentHistoryPage - 1}})">« ก่อนหน้า</button>`;
                }}

                // แสดงปุ่มหน้า 1 เสมอ
                buttons += `<button class="page-btn ${{1 === currentHistoryPage ? 'active' : ''}}" onclick="renderItems(1)">1</button>`;

                // จุดไข่ปลาฝั่งซ้าย (ถ้าระยะห่างจากหน้าปัจจุบันกับหน้า 1 มากเกินไป)
                if (currentHistoryPage > 3) {{
                    buttons += `<span style="padding: 5px 10px; color: #888;">...</span>`;
                }}

                // แสดงเลขหน้าตรงกลาง (ลบหน้าปัจจุบัน 1, บิดบวกหน้าปัจจุบัน 1) แต่ไม่เกิน Total และไม่น้อยกว่า 2
                for (let i = Math.max(2, currentHistoryPage - 1); i <= Math.min(totalPages - 1, currentHistoryPage + 1); i++) {{
                    buttons += `<button class="page-btn ${{i === currentHistoryPage ? 'active' : ''}}" onclick="renderItems(${{i}})">${{i}}</button>`;
                }}

                // จุดไข่ปลาฝั่งขวา (ถ้าระยะห่างตอนท้ายมากเกินไป)
                if (currentHistoryPage < totalPages - 2) {{
                    buttons += `<span style="padding: 5px 10px; color: #888;">...</span>`;
                }}

                // แสดงปุ่มหน้าสุดท้ายเสมอ
                buttons += `<button class="page-btn ${{totalPages === currentHistoryPage ? 'active' : ''}}" onclick="renderItems(${{totalPages}})">${{totalPages}}</button>`;

                // ปุ่ม "ถัดไป »"
                if (currentHistoryPage < totalPages) {{
                    buttons += `<button class="page-btn" onclick="renderItems(${{currentHistoryPage + 1}})">ถัดไป »</button>`;
                }}

                pagination.innerHTML = buttons;
            }}

            function setFilter(filter, btn) {{
                currentFilter = filter;
                document.querySelectorAll('.filter-bar .page-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                renderItems(1);
            }}

            function markAsRead(event, url) {{
                let readUrls = getReadItems();
                if (!readUrls.includes(url)) {{
                    readUrls.push(url);
                    localStorage.setItem('read_urls', JSON.stringify(readUrls));
                }}
                
                // หาแถวของตาราง (tr) และเพิ่มคลาส read ทันทีเพื่อให้เห็นผลโดยไม่ต้องรีเฟรช
                const row = event.target.closest('tr');
                if (row) row.classList.add('read');
            }}

            // Start
            renderItems(1);
        </script>
    </body>
    </html>
    """
    
    # เขียน index.html (เวอร์ชันคงที่สำหรับ Git)
    index_path = os.path.join(REPORTS_DIR, 'index.html')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html_template)

    return index_path

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
        TreasuryScraper()
    ]
    
    all_results = []
    for scraper in scrapers:
        try:
            # Scrape pages for data
            results = scraper.scrape(max_pages=2) 
            all_results.extend(results)
        except Exception as e:
            print(f"Error running {scraper.name}: {e}")

    # 1. Filter for NEW items
    history = load_history()
    history_urls = {item['url'] for item in history if 'url' in item}
    
    # ใช้เวลาประเทศไทยเป็นเกณฑ์ (UTC+7) แจกแจงรูปแบบที่ต้องการใช้ในส่วนต่างๆ
    th_now = get_th_now()
    now_date_str = th_now.strftime('%d/%m/%Y') # วันที่ปัจจุบันแบบสั้นสำหรับ scraped_at
    now_full_str = th_now.strftime('%d/%m/%Y %H:%M') # วันที่และเวลาปัจจุบัน
    today_sort_date = th_now.strftime('%Y-%m-%d') # รูปแบบ YYYY-MM-DD สำหรับ sort_date fallback
    
    # แก้ไขข้อมูลเก่าในประวัติ (Backfill/Correction)
    for item in history:
        # 1. แก้ไขสถานะวันที่พบข่าว
        if 'scraped_at' not in item or item.get('scraped_at') == item.get('date') or item.get('scraped_at', '').endswith('2569'):
            item['scraped_at'] = "05/03/2026"
            
        # 2. แก้ไข sort_date ที่หายไป (Fallback to scraped_at or today)
        if not item.get('sort_date') or item.get('sort_date') == "0000-00-00":
            # พยายามแกะจาก scraped_at (รูปแบบ dd/mm/yyyy)
            sc_at = item.get('scraped_at', '')
            if sc_at and len(sc_at) == 10 and sc_at[2] == '/' and sc_at[5] == '/':
                try:
                    d, m, y = sc_at.split('/')
                    item['sort_date'] = f"{y}-{m}-{d}"
                except:
                    item['sort_date'] = today_sort_date
            else:
                item['sort_date'] = today_sort_date

        # 3. ซ่อมแซมลิงก์สรรพากรที่ขาด /TPW/
        if item.get('agency') == "กรมสรรพากร" and "interapp4.rd.go.th/upload/" in item.get('url', ''):
            item['url'] = item['url'].replace("interapp4.rd.go.th/upload/", "interapp4.rd.go.th/TPW/upload/")

        # 4. ซ่อมแซมลิงก์กรมศุลกากรที่เพี้ยน (&current_id กลายเป็น ¤t_id)
        if item.get('agency') == "กรมศุลกากร" and "\u00a4t_id=" in item.get('url', ''):
            item['url'] = item['url'].replace("\u00a4t_id=", "&current_id=")

    # กำจัดรายการซ้ำในประวัติ (ถ้ามี)
    seen_urls = set()
    unique_history = []
    for item in history:
        if item['url'] not in seen_urls:
            unique_history.append(item)
            seen_urls.add(item['url'])
    history = unique_history
    history_urls = seen_urls # ใช้ชุด URL ที่อัปเดตแล้ว

    retention_days = 60
    new_items = []
    
    for item in all_results:
        # 0. Fallback: ถ้าไม่พบวันประกาศ ให้ใช้วันที่พบข่าว (วันนี้) แทน เพื่อให้เรียงลำดับและล้างข้อมูลได้
        if not item.get('sort_date') or item.get('sort_date') == "0000-00-00":
            item['sort_date'] = today_sort_date
            # หากชื่อวันที่ไม่มี ให้บันทึกว่าพบเมื่อไหร่ด้วย
            if not item.get('date') or item.get('date') == "ไม่ระบุวันที่":
                item['date'] = f"ตรวจพบเมื่อ {now_date_str}"

        if item['url'] not in history_urls:
            # เพิ่มการตรวจสอบความเก่า: ถ้าข่าวเก่าเกินกว่าเกณฑ์ประวัติ (60 วัน) ไม่ต้องถือว่าเป็นข่าวใหม่
            sort_date_str = item.get('sort_date')
            if sort_date_str:
                try:
                    item_date = datetime.strptime(sort_date_str, '%Y-%m-%d')
                    delta = th_now - item_date
                    if delta.days > retention_days:
                        continue
                except:
                    pass

            # เพิ่มฟิลด์ระบุวันที่พบข่าว
            item['scraped_at'] = now_date_str
            new_items.append(item)
            history.append(item) 
            history_urls.add(item['url'])

    # 2. Save updated history
    save_history(history)

    # 3. Generate Report (Pass list of new AND total history)
    report_path = generate_report(new_items, history)
    print(f"Report generated: {report_path}")
    print(f"Stats: {len(new_items)} New, {len(history)} Total")
    
    # Sync with Supabase (New for Global Sync)
    print("Syncing with Supabase...")
    upsert_auctions(all_results)
    
    print("--- Finished ---")

if __name__ == "__main__":
    main()
