from supabase import create_client, Client
from combar_logic import combate_media
import os
from dotenv import load_dotenv
import re

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")

if not url or not key:
    raise ValueError("No se han encontrado las variables SUPABASE_URL o SUPABASE_ANON_KEY")

supabase: Client = create_client(url, key)

_dice_term = re.compile(r"\s*([+-]?)\s*(?:(\d*)[dD](\d+)|(\d+))\s*")

def dice_average(expr: str | int | float | None) -> float:
    """
    Convierte '2d6+1d3+3-1' en su media: 2*(6+1)/2 + 1*(3+1)/2 + 3 - 1 = 7 + 2 + 2 = 11
    Admite 'd3', 'D6', '3', combinaciones con +/-, y espacios.
    """
    if expr is None:
        return 0.0
    if isinstance(expr, (int, float)):
        return float(expr)
    s = str(expr).strip()
    if not s:
        return 0.0

    total = 0.0
    i = 0
    while i < len(s):
        m = _dice_term.match(s, i)
        if not m:
            # Si encuentra algo raro, intenta convertir todo a float (p. ej. '5')
            try:
                return float(s)
            except Exception:
                return 0.0
        sign, n_str, faces_str, flat_str = m.groups()
        sign_mult = -1.0 if sign == '-' else 1.0

        if faces_str:  # término con dados: n d faces
            n = int(n_str) if n_str else 1
            faces = int(faces_str)
            avg = n * (faces + 1) / 2.0
            total += sign_mult * avg
        else:         # término plano
            total += sign_mult * float(flat_str)

        i = m.end()
        # saltar signos/espacios extra
        while i < len(s) and s[i].isspace():
            i += 1
        if i < len(s) and s[i] in '+-':
            # el signo lo recogerá el siguiente match
            pass
    return total

def obtener_unidad_por_id(unid_id: str):
    response = supabase.table("units").select("*").eq("id", unid_id).single().execute()
    return response.data


def obtener_armas_de_unidad(unit_id: str):
    resp = supabase.table("unit_weapons").select("*").eq("unit_id", unit_id).execute()
    return resp.data or []

    
def combate_media_multiarmas(unidad_atac: dict, unidad_def: dict, carga: bool = False):
    # 1) Cargar todas las armas del atacante
    armas = obtener_armas_de_unidad(unidad_atac["id"])

    total = 0.0
    detalle = []

    # 2) Resumen atacante
    models_atac = int(unidad_atac.get("base_size", 1)) * (2 if bool(unidad_atac.get("reinforced", False)) else 1)
    wounds_pm_atac = int(unidad_atac.get("wounds", 1))
    ataques_pm_total = 0.0

    # 3) Procesar cada arma
    for arma in armas:
        perfil = construir_perfil_ataque(unidad_atac, arma, carga=carga)
        ataques_pm_total += float(perfil.get("attacks", 0.0))

        # Depuración: comprobar que los valores llegan numéricos y correctos
        print(arma.get("name", "arma"), {
            "attacks": perfil["attacks"],
            "to_hit": perfil["to_hit"],
            "to_wound": perfil["to_wound"],
            "rend": perfil["rend"],
            "damage": perfil["damage"],
            "crit": perfil.get("crit_effect"),
            "crit_v": perfil.get("crit_value"),
        })
        print({"save_def": unidad_def.get("save"), "ward_def": unidad_def.get("ward_save")})

        out = combate_media(perfil, unidad_def, carga=carga)
        total += out["total_heridas"]
        detalle.append((arma.get("name", "arma"), out))

    # 4) Resumen atacante/defensor para imprimir en la UI/CLI
    resumen_atac = {
        "name": unidad_atac.get("name", ""),
        "models": models_atac,
        "attacks_per_model": ataques_pm_total,
        "total_attacks": models_atac * ataques_pm_total,
        "wounds_per_model": wounds_pm_atac,
        "total_wounds": models_atac * wounds_pm_atac,
    }

    models_def = int(unidad_def.get("base_size", 1)) * (2 if bool(unidad_def.get("reinforced", False)) else 1)
    wounds_pm_def = int(unidad_def.get("wounds", 1))
    resumen_def = {
        "name": unidad_def.get("name", ""),
        "models": models_def,
        "total_attacks": 0.0,  # si quieres, puedes sumar también las armas del defensor en otra función espejo
        "wounds_per_model": wounds_pm_def,
        "total_wounds": models_def * wounds_pm_def,
    }

    return total, detalle, resumen_atac, resumen_def

def resumen_unidad_multiarmas(unidad: dict, carga: bool = False) -> dict:
    armas = obtener_armas_de_unidad(unidad["id"])
    models = int(unidad.get("base_size", 1)) * (2 if bool(unidad.get("reinforced", False)) else 1)
    heridas_por_mini = int(unidad.get("wounds", 1))

    ataques_por_mini_total = 0.0
    for arma in armas:
        perfil = construir_perfil_ataque(unidad, arma, carga=carga)
        ataques_por_mini_total += float(perfil.get("attacks", 0.0))

    return {
        "name": unidad.get("name", ""),
        "models": models,
        "attacks_per_model": ataques_por_mini_total,
        "total_attacks": models * ataques_por_mini_total,
        "wounds_per_model": heridas_por_mini,
        "total_wounds": models * heridas_por_mini,
    }

def construir_perfil_ataque(unidad: dict, arma: dict, carga: bool=False) -> dict:
    # rend total (arma + bonif por cargar de la unidad si existe)
    rend_total = arma.get("rend", 0) or 0
    if carga and unidad.get("rend_on_charge"):
        rend_total += int(unidad["rend_on_charge"])

    # ataques: número o fórmula
    attacks = arma.get("attacks")
    if attacks is None:
        attacks = dice_average(arma.get("attacks_formula"))

    # daño: número o fórmula
    damage = arma.get("damage")
    if damage is None:
        damage = dice_average(arma.get("damage_formula"))

    return {
        "base_size":    int(unidad.get("base_size", 1)),
        "reinforced":   bool(unidad.get("reinforced", False)),
        "points":       int(unidad.get("points", 0)),
        "attacks":      float(attacks),
        "to_hit":       int(arma.get("to_hit", 7)),
        "to_wound":     int(arma.get("to_wound", 7)),
        "rend":         int(rend_total),
        "damage":       float(damage),
        "crit_effect":  arma.get("crit_effect", unidad.get("crit_effect", "none")),
        "crit_value":   arma.get("crit_value", unidad.get("crit_value")),
    }
def resumen_unidad(unidad: dict, arma: dict, carga: bool = False) -> dict:
    # Reutiliza tu builder para tener attacks/daño numéricos
    perfil = construir_perfil_ataque(unidad, arma, carga=carga)

    models = int(unidad.get("base_size", 1)) * (2 if bool(unidad.get("reinforced", False)) else 1)
    ataques_por_mini = float(perfil.get("attacks", 0.0))
    heridas_por_mini = int(unidad.get("wounds", 1))

    return {
        "name": unidad.get("name", ""),
        "models": models,
        "attacks_per_model": ataques_por_mini,
        "total_attacks": models * ataques_por_mini,
        "wounds_per_model": heridas_por_mini,
        "total_wounds": models * heridas_por_mini,
    }


if __name__ == "__main__":
    atacante_id = '87b4d112-0b36-4053-bbc1-5e0e1313328e'
    defensor_id = '15daddf4-52d8-42d8-87e0-19b0f02f4204'


    atacante_u = obtener_unidad_por_id(atacante_id)
    defensor_u = obtener_unidad_por_id(defensor_id)

# Resúmenes
total_general, detalle, res_atac, res_def = combate_media_multiarmas(atacante_u, defensor_u, carga=True)


print(f"— Atacante: {res_atac['name']}  modelos={res_atac['models']}, ataques_totales={res_atac['total_attacks']:.2f}, heridas_totales={res_atac['total_wounds']}")
print(f"— Defensor:  {res_def['name']}   modelos={res_def['models']},  heridas_totales={res_def['total_wounds']}")
print(f"\nHeridas esperadas totales (todas las armas): {total_general:.2f}")

for nombre_arma, out in detalle:
    total_arma = out["total_heridas"]
    normales   = out["heridas_finales_normales"]
    mortales   = out["mortales_post_ward"]
    print(f"  - {nombre_arma}: total={total_arma:.2f} | normales={normales:.2f} | mortales={mortales:.2f}")


