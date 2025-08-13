import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", os.getenv("SUPABASE_KEY", ""))
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

def obtener_unidad_por_id(unit_id: str) -> dict:
    res = sb.table("units").select("*").eq("id", unit_id).single().execute()
    return res.data if res and res.data else {}

def obtener_ataques_totales(unit_id: str) -> int:
    res = sb.table("unit_weapons").select("attacks_formula").eq("unit_id", unit_id).execute()
    armas = res.data if res and res.data else []
    total = 0
    for arma in armas:
        # Si attacks_formula es un número, lo sumamos. Si es texto tipo "2d6", puedes adaptar el parseo.
        try:
            total += int(arma.get("attacks_formula", 0))
        except Exception:
            pass  # Si es "1d3" o similar, ignóralo o implementa un parser si lo necesitas
    return total