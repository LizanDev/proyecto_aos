import os
from supabase import create_client
from dotenv import load_dotenv
from typing import List, Dict

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", os.getenv("SUPABASE_KEY", ""))
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

def obtener_unidad_por_id(unit_id: str) -> dict:
    res = sb.table("units").select("*").eq("id", unit_id).single().execute()
    return res.data if res and res.data else {}

def obtener_armas_de_unidad(unit_id: str) -> List[Dict]:
    res = sb.table("unit_weapons").select("*").eq("unit_id", unit_id).execute()
    return res.data if res and res.data else []

def obtener_ataques_totales(unit_id: str) -> int:
    return 0