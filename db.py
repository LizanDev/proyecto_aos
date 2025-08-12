import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        raise ValueError("No se han encontrado las variables SUPABASE_URL o SUPABASE_ANON_KEY")
    return create_client(url, key)

supabase = get_supabase_client()

