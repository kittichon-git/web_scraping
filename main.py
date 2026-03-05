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

# --- Settings ---
DATA_DIR = 'data'
HISTORY_FILE = os.path.join(DATA_DIR, 'history.json')
REPORTS_DIR = 'reports'
DATA_JSON_FILE = os.path.join(REPORTS_DIR, 'data.json')

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
    
    cutoff_date = datetime.now()
    unique_history = []
    removed_count = 0
    
    for item in history:
        sort_date_str = item.get('sort_date')
        if not sort_date_str:
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
            unique_history.append(item)
            
    if removed_count > 0:
        print(f"Purged {removed_count} old entries (older than {days} days)")
    return unique_history

def generate_report(new_items, history):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    now = datetime.now()
    date_str = now.strftime('%d/%m/%Y %H:%M')
    
    # Sort items by sort_date descending
    all_combined = new_items + history
    # Remove duplicates based on URL
    seen_urls = set()
    unique_items = []
    for item in all_combined:
        if item['url'] not in seen_urls:
            unique_items.append(item)
            seen_urls.add(item['url'])
    
    unique_items.sort(key=lambda x: x.get('sort_date', '0000-00-00'), reverse=True)

    new_urls = [n['url'] for n in new_items]
    historical_items = [item for item in unique_items if item['url'] not in new_urls]
    
    all_data = {
        "new": new_items,
        "historical": historical_items,
        "updated_at": date_str
    }
    
    # 1. ยังคงบันทึกข้อมูลลงใน data.json (เผื่อไว้ให้ระบบอื่นใช้)
    with open(DATA_JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    # แปลงข้อมูลเป็น JSON string เพื่อฝังลงใน HTML
    data_json = json.dumps(all_data, ensure_ascii=False)

    # Calculate Thailand Time (UTC+7) for the report
    th_time = datetime.utcnow() + timedelta(hours=7)
    update_time = th_time.strftime('%d/%m/%Y %H:%M')
    
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
                
                // รวมข้อมูลทั้งหมด
                let allItems = [...data.new, ...data.historical];
                
                // ตัวกรอง (Filter)
                const filtered = filterItems(allItems);
                
                // เรียงลำดับใหม่: เอาวันที่พบข่าว (scraped_at) ล่าสุดขึ้นก่อน
                // รูปแบบวันที่คือ dd/mm/yyyy เราต้องแปลงเป็น yyyymmdd เพื่อเปรียบเทียบ
                filtered.sort((a, b) => {{
                    const dateA = (a.scraped_at || '00/00/0000').split('/').reverse().join('');
                    const dateB = (b.scraped_at || '00/00/0000').split('/').reverse().join('');
                    if (dateA !== dateB) return dateB.localeCompare(dateA);
                    // ถ้าวันที่พบข่าวเท่ากัน ให้เรียงตาม sort_date (วันที่ประกาศในเว็บ)
                    return (b.sort_date || '').localeCompare(a.sort_date || '');
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
                
                
                return `
                    <tr class="${{isRead ? 'read' : ''}}" data-url="${{item.url}}">
                        <td>${{scrapeDate}}</td>
                        <td><span class="agency-badge">${{item.agency}}</span></td>
                        <td>
                            <a href="${{item.url}}" class="title" title="${{item.title}}" target="_blank" onclick="markAsRead(event, '${{item.url}}')">
                                ${{item.title}}
                            </a>
                            <small style="color: #888;">🏢 ${{item.unit || 'N/A'}}</small>
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
                for (let i = 1; i <= totalPages; i++) {{
                    buttons += `<button class="page-btn ${{i === currentHistoryPage ? 'active' : ''}}" onclick="renderItems(${{i}})">${{i}}</button>`;
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
        RevenueScraper()
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
    now_date_str = datetime.now().strftime('%d/%m/%Y') # วันที่ปัจจุบันแบบสั้น
    now_full_str = datetime.now().strftime('%d/%m/%Y %H:%M') # วันที่และเวลาปัจจุบัน
    
    # แก้ไขข้อมูลเก่าในประวัติ (Backfill/Correction)
    for item in history:
        # 1. แก้ไขสถานะวันที่พบข่าว
        if 'scraped_at' not in item or item.get('scraped_at') == item.get('date'):
            item['scraped_at'] = "05/03/2569"
            
        # 2. ซ่อมแซมลิงก์สรรพากรที่ขาด /TPW/
        if item.get('agency') == "กรมสรรพากร" and "interapp4.rd.go.th/upload/" in item.get('url', ''):
            item['url'] = item['url'].replace("interapp4.rd.go.th/upload/", "interapp4.rd.go.th/TPW/upload/")

        # 3. ซ่อมแซมลิงก์กรมศุลกากรที่เพี้ยน (&current_id กลายเป็น ¤t_id)
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

    new_items = []
    for item in all_results:
        if item['url'] not in history_urls:
            # เพิ่มฟิลด์ระบุวันที่พบข่าว (คือวันที่เราทำการ Scraping จริงๆ)
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

    print("--- Finished ---")

if __name__ == "__main__":
    main()
