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
        return create_client(SUPABASE_URL, SUPABASE_KEY)
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

    # Prepare data for upsert
    to_upsert = []
    for item in auctions_data:
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

    try:
        # Use upsert with 'url' as the conflict target (unique constraint)
        response = supabase.table("auctions").upsert(
            to_upsert, 
            on_conflict="url"
        ).execute()
        print(f"Successfully upserted {len(to_upsert)} items to Supabase.")
    except Exception as e:
        print(f"Error upserting to Supabase: {e}")

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
