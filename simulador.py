from supabase import create_client, Client
from combar_logic import combate_media
import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def obtener_unidad_por_id(unidad_id: str):
    response = supabase.table("units").select("*").eq("id", unidad_id).single().execute()
    return response.data

if __name__ == "__name__":
    atacante_id = 'cefbb712-fea6-4a20-8549-e88075c0f129'
    defensor_id = '1229e949-9c17-481d-b54f-87ccf233c437'

    atacante = obtener_unidad_por_id(atacante_id)
    defensor = obtener_unidad_por_id(defensor_id)

    resultado = combate_media(atacante, defensor, carga=True)
    
    print(f"Resultado del combate entre {atacante['name']} y {defensor['name']}:")
    for k, v in resultado.items():
        print(f"  {k}: {round(v, 2)}")