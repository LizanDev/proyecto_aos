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
    res = sb.table("unit_weapons").select("attacks_formula").eq("unit_id", unit_id).execute()
    armas = res.data if res and res.data else []
    total = 0
    for arma in armas:
        try:
            total += int(arma.get("attacks_formula", 0))
        except Exception:
            pass  # Si es "1d3" o similar, ignóralo o implementa un parser si lo necesitas
    return total

def get_factions() -> List[tuple[str, str]]:
    res = sb.table("factions").select("id,name").order("name").execute()
    rows = res.data or []
    return [(r["id"], r["name"]) for r in rows]

def get_units_by_faction(faction_id: str) -> List[tuple[str, str]]:
    if not faction_id:
        return []
    res = sb.table("units").select("id,name").eq("faction_id", faction_id).order("name").execute()
    rows = res.data or []
    return [(r["id"], r["name"]) for r in rows]