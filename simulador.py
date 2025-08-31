from supabase import create_client, Client
from combar_logic import combate_media
import os
from dotenv import load_dotenv
import re
from services.unidad_service import obtener_unidad_por_id, obtener_armas_de_unidad

'''load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")

if not url or not key:
    raise ValueError("No se han encontrado las variables SUPABASE_URL o SUPABASE_ANON_KEY")

supabase: Client = create_client(url, key)'''

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


def combate_media_multiarmas(unidad_atac: dict, unidad_def: dict, carga: bool = False):
    # 1) Cargar todas las armas del atacante
    armas = obtener_armas_de_unidad(unidad_atac["id"])


    total = 0.0
    detalle = []

    # 2) Resumen atacante
    models_atac = int(unidad_atac.get("base_size", 1)) * (2 if bool(unidad_atac.get("reinforced", False)) else 1)
    wounds_pm_atac = int(unidad_atac.get("wounds", 1))
    ataques_pm_total = 0.0

    # 3) Procesar cada arma (sumar ataques por miniatura)
    perfiles_armas = []
    for arma in armas:
        perfil = construir_perfil_ataque(unidad_atac, arma, carga=carga)
        perfiles_armas.append((arma, perfil))
        ataques_pm_total += float(perfil.get("attacks", 0.0))

    ataques_totales = ataques_pm_total * models_atac

    # Calcular daño de cada arma
    for arma, perfil in perfiles_armas:
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

        # Necesitamos guardar el número de ataques por arma y críticos para poder referenciarlo después
        out = combate_media(perfil, unidad_def, carga=carga)
        out['attacks'] = perfil["attacks"]
        
        # Calcular críticos (1/6 de los ataques)
        p_6 = 1.0 / 6.0
        models = int(unidad_atac.get("base_size", 1)) * (2 if bool(unidad_atac.get("reinforced", False)) else 1)
        total_attacks = perfil["attacks"] * models
        num_criticos = total_attacks * p_6
        out['criticos'] = num_criticos
        
        # Añadir efecto de críticos para mostrar en la UI
        crit_effect = perfil.get("crit_effect")
        crit_effect = (crit_effect or "none").strip().lower()
        out['crit_effect'] = crit_effect
        
        total += out["total_heridas"]
        detalle.append((arma.get("name", "arma"), out))

    # 4) Resumen atacante/defensor para imprimir en la UI/CLI
    resumen_atac = {
        "name": unidad_atac.get("name", ""),
        "models": models_atac,
        "attacks_per_model": ataques_pm_total,  # suma de ataques de todas las armas por miniatura
        "total_attacks": ataques_totales,       # suma real de ataques
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

# kroxigor =500c03e5-085b-4c5f-acbf-9d78a8d40591
# kurnoths = 7ff18894-a6e9-4203-94fa-fbea1f4ad227
# lanceros en agradon = 9da7561a-6b28-4eef-a6ee-10b93504d9a5

if __name__ == "__main__":
    atacante_id = '7ff18894-a6e9-4203-94fa-fbea1f4ad227'
    defensor_id = '9da7561a-6b28-4eef-a6ee-10b93504d9a5'


    atacante_u = obtener_unidad_por_id(atacante_id)
    defensor_u = obtener_unidad_por_id(defensor_id)

# Resúmenes
total_general, detalle, res_atac, res_def = combate_media_multiarmas(atacante_u, defensor_u, carga=True)


print(f"— Atacante: {res_atac['name']}  modelos={res_atac['models']}, ataques_totales={res_atac['total_attacks']:.2f}, heridas_totales={res_atac['total_wounds']}")
print(f"— Defensor:  {res_def['name']}   modelos={res_def['models']},  heridas_totales={res_def['total_wounds']}")
print(f"\nHeridas esperadas totales (todas las armas): {total_general:.2f}")

# Calcular bajas del defensor
bajas_defensor = int(total_general // res_def['wounds_per_model']) if res_def['wounds_per_model'] else 0
print(f"Bajas estimadas del defensor: {bajas_defensor}")

# Retirar bajas del defensor
models_def_restantes = max(res_def['models'] - bajas_defensor, 0)
print(f"Miniaturas restantes del defensor: {models_def_restantes}")

# Simular respuesta del defensor si quedan miniaturas
if models_def_restantes > 0:
    # Crear copia del defensor con las minis restantes
    defensor_u_resp = dict(defensor_u)
    defensor_u_resp['base_size'] = models_def_restantes
    # El defensor ataca al atacante
    total_def, detalle_def, res_def_resp, res_atac_resp = combate_media_multiarmas(defensor_u_resp, atacante_u, carga=False)
    print(f"\nRespuesta del defensor:")
    print(f"Heridas esperadas al atacante: {total_def:.2f}")
    bajas_atacante = int(total_def // res_atac['wounds_per_model']) if res_atac['wounds_per_model'] else 0
    print(f"Bajas estimadas del atacante: {bajas_atacante}")
    models_atac_restantes = max(res_atac['models'] - bajas_atacante, 0)
    print(f"Miniaturas restantes del atacante: {models_atac_restantes}")
else:
    print("El defensor no tiene miniaturas para responder.")

# Determinar ganador
if bajas_defensor >= res_def['models'] and (models_atac_restantes if 'models_atac_restantes' in locals() else res_atac['models']) > 0:
    ganador = res_atac['name']
elif models_atac_restantes == 0:
    ganador = res_def['name']
else:
    ganador = 'Empate o combate indeciso'
print(f"Ganador estimado: {ganador}")

for nombre_arma, out in detalle:
    total_arma = out["total_heridas"]
    normales   = out["heridas_finales_normales"]
    mortales   = out["mortales_post_ward"]
    print(f"  - {nombre_arma}: total={total_arma:.2f} | normales={normales:.2f} | mortales={mortales:.2f}")


# Bucle de combate hasta que una unidad quede sin miniaturas
ronda = 1
atacante_vivo = res_atac['models']
defensor_vivo = res_def['models']
atacante_u = dict(atacante_u)
defensor_u = dict(defensor_u)
while atacante_vivo > 0 and defensor_vivo > 0:
    print(f"\n--- Ronda {ronda} ---")
    # Ataca el atacante
    atacante_u['base_size'] = atacante_vivo
    defensor_u['base_size'] = defensor_vivo
    total_general, detalle, res_atac, res_def = combate_media_multiarmas(atacante_u, defensor_u, carga=True)
    bajas_defensor = int(total_general // res_def['wounds_per_model']) if res_def['wounds_per_model'] else 0
    defensor_vivo = max(defensor_vivo - bajas_defensor, 0)
    
    # Calcular el total de ataques correctamente (ataques por mini * minis)
    ataques_totales_correctos = res_atac["attacks_per_model"] * atacante_vivo
    print(f"Atacante: {res_atac['name']} | Minis: {atacante_vivo} | Ataques totales: {ataques_totales_correctos:.2f}")
    print(f"  Media de heridas causadas: {total_general:.2f}")
    # Obtener ataques por miniatura de cada arma para impresión precisa
    armas_atac = obtener_armas_de_unidad(atacante_u["id"])
    for idx, (nombre_arma, out) in enumerate(detalle):
        ataques_por_mini = 0.0
        for arma in armas_atac:
            if arma.get("name", "") == nombre_arma:
                # Usar attacks como número, si es fórmula usar dice_average
                if arma.get("attacks") is not None:
                    ataques_por_mini = float(arma["attacks"])
                elif arma.get("attacks_formula") is not None:
                    ataques_por_mini = dice_average(arma["attacks_formula"])
                break
        ataques_arma = ataques_por_mini * atacante_vivo
        
        # Calcular críticos para esta cantidad de miniaturas
        p_6 = 1.0 / 6.0
        num_criticos = ataques_arma * p_6
        
        # Mostrar efectos de crítico si hay
        crit_info = ""
        heridas_normales = out.get('heridas_finales_normales', 0)
        heridas_mortales = out.get('mortales_post_ward', 0)
        
        if out.get('crit_effect') == 'mortal_wounds':
            crit_info = f" → {heridas_mortales:.2f} mortales (ignoran armadura)"
        elif out.get('crit_effect') == 'auto_wound':
            crit_info = f" → {out.get('no_salv_autow_post_ward', 0):.2f} heridas auto."
            
        # Mostrar el desglose de heridas normales y mortales
        desglose = ""
        if heridas_mortales > 0:
            desglose = f" (normal={heridas_normales:.2f} + mort={heridas_mortales:.2f})"
            
        print(f"    - {nombre_arma}: ataques={ataques_arma:.2f} | criticos={num_criticos:.2f}{crit_info} | heridas={out['total_heridas']:.2f}{desglose} | salvadas={out.get('heridas_salvadas', 0)}")
    print(f"Bajas defensor: {bajas_defensor} | Minis defensor restantes: {defensor_vivo}")
    if defensor_vivo == 0:
        print("El defensor ha sido eliminado. Gana el atacante.")
        break
    # Responde el defensor
    defensor_u['base_size'] = defensor_vivo
    total_def, detalle_def, res_def_resp, res_atac_resp = combate_media_multiarmas(defensor_u, atacante_u, carga=False)
    bajas_atacante = int(total_def // res_atac['wounds_per_model']) if res_atac['wounds_per_model'] else 0
    atacante_vivo = max(atacante_vivo - bajas_atacante, 0)
    # Calcular el total de ataques correctamente para el defensor
    ataques_totales_defensor = res_def_resp["attacks_per_model"] * defensor_vivo
    print(f"Defensor: {res_def['name']} | Minis: {defensor_vivo} | Ataques totales: {ataques_totales_defensor:.2f}")
    print(f"  Media de heridas causadas: {total_def:.2f}")
    
    # Obtener ataques por miniatura de cada arma para impresión precisa del defensor
    armas_def = obtener_armas_de_unidad(defensor_u["id"])
    for nombre_arma, out in detalle_def:
        ataques_por_mini = 0.0
        for arma in armas_def:
            if arma.get("name", "") == nombre_arma:
                if arma.get("attacks") is not None:
                    ataques_por_mini = float(arma["attacks"])
                elif arma.get("attacks_formula") is not None:
                    ataques_por_mini = dice_average(arma["attacks_formula"])
                break
        ataques_arma = ataques_por_mini * defensor_vivo
        
        # Calcular críticos para esta cantidad de miniaturas
        p_6 = 1.0 / 6.0
        num_criticos = ataques_arma * p_6
        
        # Mostrar efectos de crítico si hay
        crit_info = ""
        heridas_normales = out.get('heridas_finales_normales', 0)
        heridas_mortales = out.get('mortales_post_ward', 0)
        
        if out.get('crit_effect') == 'mortal_wounds':
            crit_info = f" → {heridas_mortales:.2f} mortales (ignoran armadura)"
        elif out.get('crit_effect') == 'auto_wound':
            crit_info = f" → {out.get('no_salv_autow_post_ward', 0):.2f} heridas auto."
            
        # Mostrar el desglose de heridas normales y mortales
        desglose = ""
        if heridas_mortales > 0:
            desglose = f" (normal={heridas_normales:.2f} + mort={heridas_mortales:.2f})"
            
        print(f"    - {nombre_arma}: ataques={ataques_arma:.2f} | criticos={num_criticos:.2f}{crit_info} | heridas={out['total_heridas']:.2f}{desglose} | salvadas={out.get('heridas_salvadas', 0)}")
    print(f"Bajas atacante: {bajas_atacante} | Minis atacante restantes: {atacante_vivo}")
    if atacante_vivo == 0:
        print("El atacante ha sido eliminado. Gana el defensor.")
        break
    ronda += 1

# Mostrar el nombre de la unidad ganadora al final
if atacante_vivo > 0:
    print(f"\n¡Victoria para: {res_atac['name']}!")
else:
    print(f"\n¡Victoria para: {res_def['name']}!")


