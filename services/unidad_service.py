from db import supabase
from typing import Optional, Dict, List

def obtener_unidad_por_id(unid_id: str) -> Optional[Dict]:
    response = supabase.table("units").select("*").eq("id", unid_id).single().execute()
    return response.data

def obtener_armas_de_unidad(unit_id: str) -> List[Dict]:
    resp = supabase.table("unit_weapons").select("*").eq("unit_id", unit_id).execute()
    return resp.data or []
