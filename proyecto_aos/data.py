from __future__ import annotations
import os
from  typing import List,Tuple,Dict,Any
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", os.getenv("SUPABASE_KEY",""))

sb: Client | None = None
if SUPABASE_URL and SUPABASE_ANON_KEY:
    sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def get_factions() -> List[Tuple[str, str]]:
    if not sb: return []
    res = sb.table("factions").select("id,name").order("name").execute()
    rows = res.data or []
    return [(r["id"], r["name"]) for r in rows]

def get_units_by_faction(faction_id:str) -> List[Tuple[str,str]]:
    if not(sb and faction_id): return []
    res = sb.table("units").select("id,name").eq("faction_id", faction_id).order("name").execute()
    rows = res.data or []
    return [(r["id"], r["name"]) for r in rows]
