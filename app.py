import streamlit as st
from utils.db import get_supabase, mark_as_read, get_stats
import math

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Web Scraping Auction Dashboard",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

ITEMS_PER_PAGE = 50

# ─── Session State ─────────────────────────────────────────────────────────────
for key, default in [
    ("filter_agency", "ทั้งหมด"),
    ("page_new", 1),
    ("page_read", 1),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ─── Query param handler (สำรองไว้ถ้าต้องการในอนาคต) ──────────────────────────
_read_id = st.query_params.get("read", None)
if _read_id:
    mark_as_read(_read_id)
    st.query_params.clear()
    st.cache_data.clear()
    st.rerun()

# ─── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
  --bg:        #f0f2f5;
  --surface:   #ffffff;
  --surface2:  #f7f8fa;
  --border:    #e4e7ec;
  --border2:   #cbd2da;
  --blue:      #1558d6;
  --blue-bg:   #eef2fd;
  --blue-mid:  #3b74e8;
  --indigo:    #4f46e5;
  --teal:      #0d9488;
  --teal-bg:   #f0fdfa;
  --orange:    #d97706;
  --orange-bg: #fffbeb;
  --green:     #059669;
  --green-bg:  #ecfdf5;
  --gray:      #6b7280;
  --gray2:     #9ca3af;
  --dark:      #111827;
  --dark2:     #374151;
  --mono:      'IBM Plex Mono', monospace;
  --sans:      'Sarabun', sans-serif;
}

/* ── Global ── */
html, body, [class*="css"] { font-family: var(--sans) !important; }
[data-testid="stAppViewContainer"] { background: var(--bg) !important; }
[data-testid="stAppViewBlockContainer"] {
  max-width: 900px !important;
  margin: 0 auto !important;
  background: transparent !important;
  padding: 1.5rem 1rem !important;
}
#MainMenu, footer, [data-testid="stToolbar"] { display: none !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div,
[data-testid="stSidebar"] section { background: var(--surface) !important; }
[data-testid="stSidebar"] { border-right: 1px solid var(--border) !important; }
[data-testid="stSidebar"] > div:first-child { padding: 0.65rem 0.5rem !important; }
[data-testid="stSidebar"] .stVerticalBlock { gap: 0.1rem !important; }
.sb-logo {
  display: flex; align-items: center; gap: 0.45rem;
  margin-bottom: 0.6rem; padding-bottom: 0.55rem;
  border-bottom: 1px solid var(--border);
}
.sb-icon {
  width: 24px; height: 24px; border-radius: 5px;
  background: var(--blue); display: flex; align-items: center;
  justify-content: center; font-size: 12px; flex-shrink: 0;
}
.sb-title { font-family: var(--mono); font-size: 0.54rem; color: var(--blue); font-weight: 600; letter-spacing: 0.1em; line-height: 1.3; text-transform: uppercase; }
.sb-lbl {
  font-family: var(--mono); font-size: 0.53rem; color: var(--gray2);
  letter-spacing: 0.1em; text-transform: uppercase;
  padding: 0.45rem 0.2rem 0.22rem; border-top: 1px solid var(--border);
  margin-top: 0.15rem;
}
[data-testid="stSidebar"] div.stButton > button {
  text-align: left !important; justify-content: flex-start !important;
  font-size: 0.75rem !important; font-family: var(--sans) !important;
  padding: 0.16rem 0.48rem !important; border-radius: 5px !important;
  width: 100% !important; background: transparent !important;
  border: 1px solid transparent !important; color: var(--dark2) !important;
  font-weight: 400 !important; transition: all 0.12s !important;
  min-height: 0 !important; line-height: 1.35 !important;
  height: auto !important; position: static !important;
  opacity: 1 !important; pointer-events: auto !important; overflow: visible !important;
}
[data-testid="stSidebar"] div.stButton > button:hover {
  background: var(--blue-bg) !important; color: var(--blue) !important; border-color: #c5d5f7 !important;
}
[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
  background: var(--blue-bg) !important; color: var(--blue) !important;
  border-color: #a8c1f3 !important; font-weight: 600 !important;
}

/* ── Header card ── */
.hdr-card {
  background: var(--surface);
  border-radius: 12px;
  border: 1px solid var(--border);
  padding: 1.2rem 1.5rem 1rem;
  margin-bottom: 1rem;
}
.hdr-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; flex-wrap: wrap; margin-bottom: 0.8rem; }
.main-title { font-size: 1.25rem; font-weight: 700; color: var(--dark); letter-spacing: -0.02em; margin: 0; }
.main-title em { color: var(--blue); font-style: normal; }
.unread-pill {
  display: inline-flex; align-items: center; gap: 0.45rem;
  background: var(--blue-bg); border: 1px solid #a8c1f3;
  border-radius: 20px; padding: 0.25rem 0.9rem;
  font-size: 0.82rem; color: var(--blue); white-space: nowrap;
}
.pulse { width: 6px; height: 6px; border-radius: 50%; background: var(--blue); flex-shrink: 0; animation: pls 2s infinite; }
@keyframes pls { 0%,100%{opacity:1;transform:scale(1.3)} 50%{opacity:.2;transform:scale(.5)} }
.ub-count { font-family: var(--mono); font-weight: 700; font-size: 0.95rem; }

/* ── Stats row ── */
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.6rem; margin-bottom: 1.2rem; }
.stat-box {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; padding: 0.7rem 0.8rem; text-align: center;
}
.stat-box.s-blue  { border-top: 3px solid var(--blue); }
.stat-box.s-teal  { border-top: 3px solid var(--teal); }
.stat-box.s-orange{ border-top: 3px solid var(--orange); }
.stat-box.s-gray  { border-top: 3px solid var(--border2); }
.stat-n { font-family: var(--mono); font-size: 1.3rem; font-weight: 700; line-height: 1; margin-bottom: 0.18rem; }
.stat-l { font-size: 0.62rem; color: var(--gray); letter-spacing: 0.06em; text-transform: uppercase; font-weight: 600; }
.n-blue  { color: var(--blue); }
.n-teal  { color: var(--teal); }
.n-orange{ color: var(--orange); }
.n-gray  { color: var(--gray); }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
  background: var(--surface) !important; border-radius: 10px 10px 0 0 !important;
  border: 1px solid var(--border) !important; border-bottom: none !important;
  padding: 0.3rem 0.5rem 0 !important; gap: 0.2rem !important; margin-bottom: 0 !important;
}
.stTabs [data-baseweb="tab"] {
  font-family: var(--sans) !important; font-size: 0.88rem !important;
  color: var(--gray) !important; padding: 0.55rem 1.1rem !important;
  border-radius: 7px 7px 0 0 !important; border: none !important;
}
.stTabs [aria-selected="true"] {
  color: var(--blue) !important; font-weight: 700 !important;
  background: var(--bg) !important; border-bottom: 2px solid var(--blue) !important;
}
.stTabs [data-baseweb="tab-panel"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important; border-top: none !important;
  border-radius: 0 0 10px 10px !important; padding: 1.2rem 1.2rem !important;
}

/* ── Caption (แสดง X–Y จาก Z) ── */
.stCaption, [data-testid="stCaptionContainer"] p {
  font-family: var(--mono) !important; font-size: 0.68rem !important;
  color: var(--gray2) !important; margin-bottom: 0.7rem !important;
}

/* ── News card UNREAD ── */
.nc {
  display: flex;
  align-items: stretch;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 0.5rem;
  overflow: hidden;
  transition: box-shadow 0.15s, border-color 0.15s, transform 0.1s;
  cursor: pointer;
}
.nc:hover {
  border-color: #93b4f5;
  box-shadow: 0 2px 8px rgba(21,88,214,0.10);
  transform: translateY(-1px);
}
.nc-accent { width: 4px; flex-shrink: 0; background: var(--blue); }
.nc-body { flex: 1; padding: 0.75rem 1rem 0.65rem; min-width: 0; }
.nc-title {
  font-size: 0.92rem; font-weight: 600; color: var(--dark);
  line-height: 1.45; margin-bottom: 0.45rem;
  display: block; text-decoration: none;
  word-break: break-word;
}
.nc:hover .nc-title { color: var(--blue); text-decoration: underline; text-decoration-color: #93b4f5; }
.nc-meta { display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; }

/* ── News card READ ── */
.nc-r {
  display: flex; align-items: stretch;
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 8px; margin-bottom: 0.4rem; overflow: hidden;
  opacity: 0.6; transition: opacity 0.15s;
}
.nc-r:hover { opacity: 0.88; }
.nc-r-accent { width: 4px; flex-shrink: 0; background: var(--border2); }
.nc-r-body { flex: 1; padding: 0.65rem 1rem 0.55rem; min-width: 0; }
.nc-r-title {
  font-size: 0.87rem; color: var(--gray2);
  text-decoration: line-through; text-decoration-color: var(--border2);
  line-height: 1.4; margin-bottom: 0.35rem;
  display: block; word-break: break-word;
}

/* ── Badges ── */
.bdg {
  display: inline-flex; align-items: center; gap: 0.2rem;
  border-radius: 5px; font-size: 0.67rem; font-weight: 600;
  padding: 0.12rem 0.45rem; white-space: nowrap; line-height: 1.4;
}
.b-ag   { background: var(--blue-bg);   color: var(--blue);   border: 1px solid #c5d5f7; }
.b-dt   { background: var(--orange-bg); color: var(--orange); border: 1px solid #fde68a; font-family: var(--mono); font-size: 0.65rem; }
.b-unit { background: var(--teal-bg);   color: var(--teal);   border: 1px solid #99f6e4; font-size: 0.64rem; }
.b-read { background: var(--surface2);  color: var(--gray2);  border: 1px solid var(--border); font-family: var(--mono); font-size: 0.63rem; }

/* ── st.link_button ใน card — ทำให้ดูเหมือน title link ── */
[data-testid="stAppViewBlockContainer"] a[data-testid="stLinkButton"] button,
[data-testid="stAppViewBlockContainer"] [data-testid="stLinkButton"] button {
  background: none !important;
  border: none !important;
  padding: 0 0 0.4rem 0 !important;
  color: var(--dark) !important;
  font-size: 0.92rem !important;
  font-weight: 600 !important;
  text-align: left !important;
  line-height: 1.45 !important;
  font-family: var(--sans) !important;
  width: 100% !important;
  min-height: 0 !important;
  white-space: normal !important;
  box-shadow: none !important;
  justify-content: flex-start !important;
}
[data-testid="stAppViewBlockContainer"] a[data-testid="stLinkButton"] button:hover,
[data-testid="stAppViewBlockContainer"] [data-testid="stLinkButton"] button:hover {
  color: var(--blue) !important;
  text-decoration: underline !important;
  text-decoration-color: #93b4f5 !important;
  background: none !important;
}

/* ── ซ่อนปุ่ม mark-read ✓ (class .mark-read-wrap) ── */
/* ทำให้เล็กมาก วางซ้อนตรงขอบขวาบนของ card ก่อนหน้า */
.mark-read-wrap {
  position: relative;
  height: 0;
  overflow: visible;
  margin: 0;
  padding: 0;
}
.mark-read-wrap > div {
  position: absolute;
  top: -2.4rem;
  right: 0;
  z-index: 10;
}
.mark-read-wrap div.stButton > button {
  background: rgba(255,255,255,0.85) !important;
  border: 1px solid var(--border2) !important;
  color: var(--gray2) !important;
  border-radius: 4px !important;
  font-size: 0.7rem !important;
  padding: 0.08rem 0.45rem !important;
  min-height: 0 !important;
  line-height: 1.3 !important;
  transition: all 0.12s !important;
  opacity: 0.5 !important;
}
.mark-read-wrap div.stButton > button:hover {
  border-color: var(--teal) !important;
  color: var(--teal) !important;
  background: var(--teal-bg) !important;
  opacity: 1 !important;
}

/* ── ปุ่ม mark as read ทั่วไปใน main (fallback) ── */
[data-testid="stAppViewBlockContainer"] div.stButton > button {
  background: transparent !important;
  border: 1px solid var(--border2) !important;
  color: var(--gray) !important;
  border-radius: 5px !important;
  font-size: 0.72rem !important;
  padding: 0.12rem 0.5rem !important;
  font-family: var(--sans) !important;
  min-height: 0 !important;
  line-height: 1.4 !important;
  transition: all 0.12s !important;
}
[data-testid="stAppViewBlockContainer"] div.stButton > button:hover {
  border-color: var(--teal) !important;
  color: var(--teal) !important;
  background: var(--teal-bg) !important;
}

/* ── Pagination compact ── */
.pg-col div.stButton > button {
  background: var(--surface) !important; border: 1px solid var(--border2) !important;
  color: var(--dark2) !important; border-radius: 5px !important;
  font-size: 0.8rem !important; padding: 0.15rem 0.5rem !important;
  font-family: var(--mono) !important; min-height: 0 !important;
  line-height: 1.5 !important; transition: all 0.12s !important;
  height: auto !important; width: auto !important;
  position: static !important; opacity: 1 !important;
  pointer-events: auto !important; overflow: visible !important;
}
.pg-col div.stButton > button:hover {
  border-color: var(--blue) !important; color: var(--blue) !important;
  background: var(--blue-bg) !important;
}
.pg-col div.stButton > button:disabled { opacity: 0.3 !important; cursor: default !important; }
.pg-info {
  font-family: var(--mono); font-size: 0.72rem; color: var(--gray);
  padding: 0 0.3rem; white-space: nowrap; text-align: center;
}

/* ── Empty state ── */
.empty { text-align: center; padding: 3.5rem 2rem; color: var(--gray2); font-size: 0.9rem; }
.empty-ico { font-size: 2rem; margin-bottom: 0.5rem; opacity: 0.4; }

/* ── HR divider ── */
hr { border: none; border-top: 1px solid var(--border) !important; margin: 0.8rem 0 !important; }

/* ── Footer ── */
.footer {
  margin-top: 2rem; padding-top: 1.2rem; border-top: 1px solid var(--border);
  text-align: center; color: var(--gray2); font-family: var(--mono); font-size: 0.65rem;
}
</style>
""", unsafe_allow_html=True)

# ─── Data Functions ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_data(tab_type: str, agency_filter: str, page: int, per_page: int = ITEMS_PER_PAGE):
    supabase = get_supabase()
    if not supabase:
        return [], 0

    query = supabase.table("auctions").select("*", count="exact")

    if tab_type == "new":
        query = query.eq("is_read", False)
        if agency_filter != "ทั้งหมด":
            query = query.eq("agency", agency_filter)
        query = query.order("sort_date", desc=True).order("discovered_at", desc=True)
    else:
        query = query.eq("is_read", True)
        if agency_filter != "ทั้งหมด":
            query = query.eq("agency", agency_filter)
        query = query.order("read_at", desc=True)

    start = (page - 1) * per_page
    end   = start + per_page - 1

    try:
        res = query.range(start, end).execute()
        return res.data or [], res.count or 0
    except Exception:
        return [], 0


@st.cache_data(ttl=60)
def get_agency_unread_counts() -> dict:
    supabase = get_supabase()
    if not supabase:
        return {}
    try:
        res = supabase.table("auctions").select("agency").eq("is_read", False).execute()
        counts: dict = {}
        for row in res.data:
            ag = row.get("agency", "")
            counts[ag] = counts.get(ag, 0) + 1
        return counts
    except Exception:
        return {}


# ─── Sidebar ───────────────────────────────────────────────────────────────────
AGENCIES = [
    "ทั้งหมด",
    "กรมทางหลวง",
    "กรมศุลกากร",
    "กรมสรรพากร",
    "กรมธนารักษ์",
    "สำนักงาน ป.ป.ส.",
    "การไฟฟ้าส่วนภูมิภาค (PEA)",
    "การประปาส่วนภูมิภาค (PWA)",
    "กรมชลประทาน (RID)",
    "องค์การอุตสาหกรรมป่าไม้ (ออป.)",
    "สำนักงานอัยการสูงสุด",
    "ไปรษณีย์ไทย",
    "กรมบัญชีกลาง (e-GP)",
]

with st.sidebar:
    st.markdown(
        '<div class="sb-logo"><div class="sb-icon">📬</div><div class="sb-title">AUCTION<br>MONITOR</div></div>',
        unsafe_allow_html=True,
    )

    ag_counts = get_agency_unread_counts()

    st.markdown('<div class="sb-lbl">เลือกหน่วยงาน</div>', unsafe_allow_html=True)

    for ag in AGENCIES:
        if ag == "ทั้งหมด":
            cnt = sum(ag_counts.values())
        else:
            cnt = ag_counts.get(ag, 0)

        label = f"{ag}  ({cnt})" if cnt > 0 else ag
        is_active = st.session_state.filter_agency == ag

        if st.button(
            label,
            key=f"sb_{ag}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state.filter_agency = ag
            # reset หน้าเมื่อเปลี่ยน filter
            st.session_state.page_new  = 1
            st.session_state.page_read = 1
            st.cache_data.clear()
            st.rerun()

    st.markdown('<div class="sb-lbl">ตัวเลือก</div>', unsafe_allow_html=True)
    if st.button("↺ รีเฟรชข้อมูล", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ─── Header ────────────────────────────────────────────────────────────────────
stats = get_stats()
unread_total = stats.get("unread", 0)
total_all    = stats.get("total", 0)

read_total   = total_all - unread_total
filter_label = st.session_state.filter_agency

st.markdown(f"""
<div class="hdr-card">
  <div class="hdr-top">
    <div class="main-title">Web Scraping <em>หน่วยงานใหญ่</em></div>
    <div class="unread-pill">
      <span class="pulse"></span>
      <span>มีข่าวมาใหม่ที่ยังไม่อ่าน</span>
      <span class="ub-count">{unread_total}</span>
      <span>ข่าว</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─── Stats Row ─────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="stats-row">
  <div class="stat-box s-blue">
    <div class="stat-n n-blue">{unread_total}</div>
    <div class="stat-l">ยังไม่อ่าน</div>
  </div>
  <div class="stat-box s-teal">
    <div class="stat-n n-teal">{read_total}</div>
    <div class="stat-l">อ่านแล้ว</div>
  </div>
  <div class="stat-box s-orange">
    <div class="stat-n n-orange">{total_all}</div>
    <div class="stat-l">รวมทั้งหมด</div>
  </div>
  <div class="stat-box s-gray">
    <div class="stat-n n-gray" style="font-size:0.75rem;line-height:1.3;padding-top:0.1rem">{filter_label}</div>
    <div class="stat-l">มุมมอง</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─── Helper: Pagination UI ─────────────────────────────────────────────────────
def pagination_ui(page: int, total_pages: int, page_key: str, total_items: int, pos: str = "top"):
    k = f"{page_key}_{pos}"
    start_item = (page - 1) * ITEMS_PER_PAGE + 1 if total_items else 0
    end_item   = min(page * ITEMS_PER_PAGE, total_items)
    st.caption(f"แสดง {start_item}–{end_item} จาก {total_items} รายการ")

    if total_pages <= 1:
        return

    # compact pagination: ‹‹  ‹  1/10  ›  ››
    c1, c2, c3, c4, c5 = st.columns([1, 1, 2, 1, 1])
    with c1:
        st.markdown('<div class="pg-col">', unsafe_allow_html=True)
        if st.button("«", key=f"{k}_f", disabled=page==1, use_container_width=True):
            st.session_state[page_key] = 1; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="pg-col">', unsafe_allow_html=True)
        if st.button("‹", key=f"{k}_p", disabled=page==1, use_container_width=True):
            st.session_state[page_key] -= 1; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="pg-info">{page} / {total_pages}</div>', unsafe_allow_html=True)
    with c4:
        st.markdown('<div class="pg-col">', unsafe_allow_html=True)
        if st.button("›", key=f"{k}_n", disabled=page==total_pages, use_container_width=True):
            st.session_state[page_key] += 1; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c5:
        st.markdown('<div class="pg-col">', unsafe_allow_html=True)
        if st.button("»", key=f"{k}_l", disabled=page==total_pages, use_container_width=True):
            st.session_state[page_key] = total_pages; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


# ─── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["🆕  ข่าวมาใหม่", "✅  อ่านแล้ว"])

# ── Tab 1: ข่าวมาใหม่ ──────────────────────────────────────────────────────────
with tab1:
    page_new   = st.session_state.page_new
    items, total = fetch_data("new", filter_label, page_new)
    total_pages  = max(1, math.ceil(total / ITEMS_PER_PAGE))

    # clamp page ถ้า total เปลี่ยน
    if page_new > total_pages:
        st.session_state.page_new = total_pages
        st.rerun()

    if not items:
        st.markdown('<div class="empty"><div class="empty-ico">✨</div>อ่านข่าวครบทุกรายการแล้ว</div>', unsafe_allow_html=True)
    else:
        pagination_ui(page_new, total_pages, "page_new", total, pos="top")

        for item in items:
            title   = item.get("title", "")
            url     = item.get("url", "#")
            agency  = item.get("agency", "")
            date_s  = item.get("date_str", "—")
            unit    = item.get("unit", "")
            item_id = item["id"]

            unit_badge = f'<span class="bdg b-unit">🏢 {unit}</span>' if unit else ""

            # ── card wrapper เปิด
            st.markdown('<div class="nc"><div class="nc-accent"></div><div class="nc-body">', unsafe_allow_html=True)

            # ── title เป็น st.link_button (เปิด URL จริง target=_blank)
            st.link_button(title, url=url, use_container_width=True)

            # ── meta badges
            st.markdown(
                f'<div class="nc-meta">'
                f'<span class="bdg b-ag">🏛 {agency}</span>'
                f'<span class="bdg b-dt">📅 {date_s}</span>'
                f'{unit_badge}'
                f'</div>',
                unsafe_allow_html=True,
            )

            # ── card wrapper ปิด + ปุ่ม mark-read ซ่อนด้วย CSS class
            st.markdown('</div></div><div class="mark-read-wrap">', unsafe_allow_html=True)
            if st.button("✓", key=f"rd_{item_id}"):
                mark_as_read(item_id)
                st.cache_data.clear()
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        if total_pages > 1:
            st.markdown("---")
            pagination_ui(page_new, total_pages, "page_new", total, pos="bot")


# ── Tab 2: อ่านแล้ว ─────────────────────────────────────────────────────────────
with tab2:
    page_read    = st.session_state.page_read
    items_r, total_r = fetch_data("read", filter_label, page_read)
    total_pages_r    = max(1, math.ceil(total_r / ITEMS_PER_PAGE))

    if page_read > total_pages_r:
        st.session_state.page_read = total_pages_r
        st.rerun()

    if not items_r:
        st.markdown('<div class="empty"><div class="empty-ico">📭</div>ยังไม่มีประวัติการอ่าน</div>', unsafe_allow_html=True)
    else:
        pagination_ui(page_read, total_pages_r, "page_read", total_r, pos="top")

        for item in items_r:
            read_at_str = str(item.get("read_at") or "—")
            if len(read_at_str) > 16:
                read_at_str = read_at_str[:16]

            unit_html = f'<span class="bdg b-unit">🏢 {item.get("unit","")}</span>' if item.get("unit") else ""
            st.markdown(f"""
            <div class="nc-r">
              <div class="nc-r-accent"></div>
              <div class="nc-r-body">
                <a href="{item.get('url','#')}" target="_blank" class="nc-r-title">{item.get('title','')}</a>
                <div class="nc-meta">
                  <span class="bdg b-ag">🏛 {item.get('agency','')}</span>
                  <span class="bdg b-dt">📅 {item.get('date_str','—')}</span>
                  {unit_html}
                  <span class="bdg b-read">✓ อ่านเมื่อ {read_at_str}</span>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        if total_pages_r > 1:
            st.markdown("---")
            pagination_ui(page_read, total_pages_r, "page_read", total_r, pos="bot")

# ─── Footer ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="footer">
  &copy; 2026 AUCTION INTEL SYSTEM &nbsp;·&nbsp; {filter_label}
</div>
""", unsafe_allow_html=True)