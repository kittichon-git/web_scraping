import os
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        # Explicitly set auth header for PostgREST to bypass RLS with service_role key
        client.postgrest.auth(SUPABASE_KEY)
        return client
    except Exception as e:
        print(f"Error connecting to Supabase: {e}")
        return None

def upsert_auctions(auctions_data):
    supabase = get_supabase()
    if not supabase:
        print("Supabase not configured. Skipping DB update.")
        return
    
    if not auctions_data:
        return

    # Prepare data for upsert — skip items with null/empty URL (would violate NOT NULL constraint)
    to_upsert = []
    skipped = 0
    for item in auctions_data:
        if not item.get("url"):
            skipped += 1
            continue
        to_upsert.append({
            "url": item.get("url"),
            "agency": item.get("agency"),
            "unit": item.get("unit"),
            "title": item.get("title"),
            "date_str": item.get("date"),
            "sort_date": item.get("sort_date"),
            "status": item.get("status", "ประกาศขายทอดตลาด"),
            "source": item.get("source"),
            # Note: is_read and read_at are managed by the dashboard
        })

    if skipped:
        print(f"  ⚠️ Skipped {skipped} item(s) with null URL before upsert.")
    if not to_upsert:
        print("No valid items to upsert.")
        return

    try:
        # Use upsert with 'url' as the conflict target (unique constraint)
        response = supabase.table("auctions").upsert(
            to_upsert, 
            on_conflict="url"
        ).execute()
        print(f"Successfully upserted {len(to_upsert)} items to Supabase.")
    except Exception as e:
        print(f"Error upserting to Supabase: {e}")

def get_existing_urls() -> set:
    """ดึง URL ทั้งหมดที่มีใน Supabase แล้ว"""
    supabase = get_supabase()
    if not supabase:
        return set()
    try:
        all_urls = set()
        offset = 0
        limit = 1000
        while True:
            response = supabase.table("auctions").select("url").range(offset, offset + limit - 1).execute()
            if not response.data:
                break
            for row in response.data:
                if row.get("url"):
                    all_urls.add(row["url"])
            if len(response.data) < limit:
                break
            offset += limit
        return all_urls
    except Exception as e:
        print(f"⚠️ ดึง existing URLs ไม่ได้: {e}")
        return set()

def mark_as_read(auction_id):
    supabase = get_supabase()
    if not supabase:
        return False
    
    try:
        supabase.table("auctions").update({
            "is_read": True,
            "read_at": datetime.now().isoformat()
        }).eq("id", auction_id).execute()
        return True
    except Exception as e:
        print(f"Error marking as read: {e}")
        return False

def get_stats():
    supabase = get_supabase()
    if not supabase:
        return {"unread": 0, "total": 0}
    
    try:
        # Count unread
        unread = supabase.table("auctions").select("id", count="exact").eq("is_read", False).execute()
        total = supabase.table("auctions").select("id", count="exact").execute()
        return {
            "unread": unread.count if unread.count is not None else 0,
            "total": total.count if total.count is not None else 0
        }
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {"unread": 0, "total": 0}

def clear_all_data():
    supabase = get_supabase()
    if not supabase:
        return False
    try:
        # Delete all rows in the auctions table
        # In Supabase, delete() requires a filter. To delete all, we can use ne('id', 0) if IDs start at 1
        # or just a filter that matches all.
        supabase.table("auctions").delete().neq("id", -1).execute()
        print("Successfully cleared all data from Supabase.")
        return True
    except Exception as e:
        print(f"Error clearing data: {e}")
        return False
