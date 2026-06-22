"""
Structured run logger — PHASE 1 observability.
- Per-scraper stats logged to logs/run_YYYYMMDD.jsonl
- Run summary appended to runs.json (safe read/write, handles corrupt/empty)
- Heartbeat: alerts if last successful run > STALE_HOURS ago
- Canary: row-count floor + multi-province check for G-Procurement
"""
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"
RUNS_FILE = BASE_DIR / "runs.json"

ROW_FLOOR = 3        # รอบไหนได้ < 3 แถว → ERROR
MIN_PROVINCES = 8    # e-GP ต้องมี ≥ 8 จังหวัดต่างกัน (หลัง PHASE 2B)
STALE_HOURS = 26     # ไม่มีรอบสำเร็จเกิน 26 ชม. → ALERT
MAX_RUNS_KEPT = 90   # เก็บประวัติ 90 รอบล่าสุด


def _get_th_now() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=7)


def _setup_logger(date_str: str) -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"run_{date_str}.log"
    logger = logging.getLogger("auction_scraper")
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s %(levelname)-5s %(message)s", datefmt="%H:%M:%S")
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    fh = logging.FileHandler(str(log_file), encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger


def _read_runs_json() -> list:
    if not RUNS_FILE.exists():
        return []
    try:
        text = RUNS_FILE.read_text(encoding="utf-8").strip()
        if not text:
            return []
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _write_runs_json(runs: list):
    tmp = RUNS_FILE.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(runs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(RUNS_FILE)


class ScraperRunContext:
    """Context สำหรับ 1 scraper ใน 1 รอบ"""

    def __init__(self, scraper_name: str, logger: logging.Logger, run_id: str):
        self.scraper_name = scraper_name
        self.logger = logger
        self.run_id = run_id
        self.ts_start = datetime.now(timezone.utc)
        self.rows_fetched: int = 0
        self.provinces_seen: set = set()
        self.items_new: int = 0
        self.items_dedup: int = 0
        self.errors: list = []
        self.status: str = "ok"

    def add_error(self, msg: str):
        self.errors.append(msg)
        self.status = "failed"
        self.logger.error(f"[{self.scraper_name}] ERROR: {msg}")

    def finish(self) -> dict:
        ts_end = datetime.now(timezone.utc)
        duration_s = round((ts_end - self.ts_start).total_seconds(), 2)
        return {
            "run_id": self.run_id,
            "scraper_name": self.scraper_name,
            "ts_start": self.ts_start.isoformat(),
            "ts_end": ts_end.isoformat(),
            "duration_s": duration_s,
            "status": self.status,
            "rows_fetched": self.rows_fetched,
            "provinces_seen": sorted(self.provinces_seen),
            "items_new": self.items_new,
            "items_dedup": self.items_dedup,
            "errors": self.errors,
        }


class RunLogger:
    """จัดการ logging ทั้งรอบ"""

    def __init__(self):
        th_now = _get_th_now()
        self.date_str = th_now.strftime("%Y%m%d")
        self.run_id = th_now.strftime("%Y%m%dT%H%M%S")
        self.logger = _setup_logger(self.date_str)
        self.jsonl_path = LOGS_DIR / f"run_{self.date_str}.jsonl"
        self._records: list = []

    def check_staleness(self):
        """ตรวจ heartbeat — ถ้าไม่มีรอบสำเร็จเกิน STALE_HOURS → ALERT"""
        runs = _read_runs_json()
        if not runs:
            self.logger.warning(
                "HEARTBEAT: runs.json ว่างเปล่า — ยังไม่มีประวัติการรันเลย"
            )
            return
        last_ok_ts = None
        for r in reversed(runs):
            if r.get("overall_status") == "ok":
                last_ok_ts = r.get("ts_end")
                break
        if not last_ok_ts:
            self.logger.warning("HEARTBEAT: ไม่พบรอบที่ overall_status=ok ใน runs.json")
            return
        try:
            last_ok_dt = datetime.fromisoformat(last_ok_ts)
            gap_h = (datetime.now(timezone.utc) - last_ok_dt).total_seconds() / 3600
            if gap_h > STALE_HOURS:
                self.logger.error(
                    f"HEARTBEAT ALERT: รอบสำเร็จล่าสุดเมื่อ {gap_h:.1f} ชม.ที่แล้ว "
                    f"(เกิน {STALE_HOURS} ชม.) — ตรวจสอบ scheduler!"
                )
            else:
                self.logger.info(
                    f"HEARTBEAT OK: รอบสำเร็จล่าสุดเมื่อ {gap_h:.1f} ชม.ที่แล้ว"
                )
        except Exception as e:
            self.logger.warning(f"HEARTBEAT: แปลง ts_end ไม่ได้: {e}")

    def scraper_context(self, scraper_name: str) -> ScraperRunContext:
        return ScraperRunContext(scraper_name, self.logger, self.run_id)

    def log_scraper_result(self, ctx: ScraperRunContext):
        """เรียกหลัง scraper เสร็จ 1 ตัว"""
        record = ctx.finish()
        self._records.append(record)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(str(self.jsonl_path), "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        icon = "OK  " if record["status"] == "ok" else "FAIL"
        self.logger.info(
            f"[{record['scraper_name']}] {icon} "
            f"rows={record['rows_fetched']} new={record['items_new']} "
            f"dup={record['items_dedup']} dur={record['duration_s']}s "
            f"errors={len(record['errors'])}"
        )

    def run_canary(self, scraper_name: str, rows: int, provinces: set):
        """row-count floor + multi-province canary"""
        if rows == 0:
            self.logger.error(
                f"CANARY FAIL [{scraper_name}]: 0 รายการ — ตรวจสอบการเชื่อมต่อหรือ URL!"
            )
        elif rows < ROW_FLOOR:
            self.logger.error(
                f"CANARY FAIL [{scraper_name}]: rows={rows} < floor={ROW_FLOOR} — อาจดึงไม่ครบ!"
            )
        if scraper_name == "G-Procurement" and len(provinces) < MIN_PROVINCES:
            self.logger.error(
                f"CANARY FAIL [{scraper_name}]: provinces={len(provinces)} ({provinces}) "
                f"< {MIN_PROVINCES} — scope หดหรือดึงไม่ครบ!"
            )

    def finalize(self, overall_new: int, overall_total: int, failed_scrapers: list):
        """บันทึก run summary ลง runs.json"""
        overall_status = "failed" if failed_scrapers else "ok"
        summary = {
            "run_id": self.run_id,
            "ts_end": datetime.now(timezone.utc).isoformat(),
            "overall_status": overall_status,
            "items_new": overall_new,
            "items_scraped": overall_total,
            "scrapers_failed": [s[0] for s in failed_scrapers],
            "per_scraper": self._records,
        }
        runs = _read_runs_json()
        runs.append(summary)
        runs = runs[-MAX_RUNS_KEPT:]
        _write_runs_json(runs)
        self.logger.info(
            f"=== RUN DONE: {self.run_id} status={overall_status} "
            f"new={overall_new} scraped={overall_total} "
            f"failed_scrapers={len(failed_scrapers)} ==="
        )
