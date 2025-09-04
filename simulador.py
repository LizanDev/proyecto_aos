"""
Simulador de combate para Age of Sigmar.
Versión limpia y consistente: un único conjunto de funciones.
"""

from typing import Dict, List, Tuple, Any, Union
import re
from services.unidad_service import obtener_unidad_por_id, obtener_armas_de_unidad
from combar_logic import combate_media
from utils import redondear

_dice_term = re.compile(r"\s*([+-]?)\s*(?:(\d*)[dD](\d+)|(\d+))\s*")


def dice_average(expr: Union[str, int, float, None]) -> float:
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
            try:
                return float(s)
            except ValueError:
                return 0.0
        sign, n_str, faces_str, flat_str = m.groups()
        sign_mult = -1.0 if sign == '-' else 1.0
        if faces_str:
            n = int(n_str) if n_str else 1
            faces = int(faces_str)
            avg = n * (faces + 1) / 2.0
            total += sign_mult * avg
        else:
            total += sign_mult * float(flat_str)
        i = m.end()
        while i < len(s) and s[i].isspace():
            i += 1
    return total


def construir_perfil_ataque(unidad: Dict[str, Any], arma: Dict[str, Any], carga: bool = False) -> Dict[str, Any]:
    rend_total = arma.get("rend", 0) or 0
    if carga and unidad.get("rend_on_charge"):
        try:
            rend_total += int(unidad["rend_on_charge"])
        except (ValueError, TypeError):
            pass
    attacks = arma.get("attacks")
    if attacks is None:
        attacks = dice_average(arma.get("attacks_formula"))
    damage = arma.get("damage")
    if damage is None:
        damage = dice_average(arma.get("damage_formula"))
    return {
        "base_size": int(unidad.get("base_size", 1)),
        "reinforced": bool(unidad.get("reinforced", False)),
        "points": int(unidad.get("points", 0)),
        "attacks": float(attacks),
        "to_hit": int(arma.get("to_hit", 7)),
        "to_wound": int(arma.get("to_wound", 7)),
        "rend": int(rend_total),
        "damage": float(damage),
        "crit_effect": arma.get("crit_effect", unidad.get("crit_effect", "none")),
        "crit_value": arma.get("crit_value", unidad.get("crit_value")),
    }


def combate_media_multiarmas(unidad_atac: Dict[str, Any], unidad_def: Dict[str, Any], carga: bool = False) -> Tuple[float, List[Tuple[str, Dict[str, Any]]], Dict[str, Any], Dict[str, Any]]:
    armas = obtener_armas_de_unidad(unidad_atac.get("id", ""))
    if not armas:
        return 0.0, [], {}, {}

    if unidad_atac.get("current_models") is not None:
        models_atac = int(unidad_atac.get("current_models", 0))
    else:
        models_atac = int(unidad_atac.get("base_size", 1)) * (2 if bool(unidad_atac.get("reinforced", False)) else 1)

    ataques_pm_total = 0.0
    perfiles_armas = []
    for arma in armas:
        perfil = construir_perfil_ataque(unidad_atac, arma, carga=carga)
        perfiles_armas.append((arma, perfil))
        ataques_pm_total += float(perfil.get("attacks", 0.0))

    champion_flag = bool(unidad_atac.get("champion", False))
    ataques_totales = ataques_pm_total * models_atac + (1 if champion_flag else 0)

    total_heridas = 0.0
    detalle = []
    for idx, (arma, perfil) in enumerate(perfiles_armas):
        out = combate_media(perfil, unidad_def, carga=carga)
        out['attacks'] = perfil['attacks']

        total_attacks_arma = perfil['attacks'] * models_atac
        if idx == 0 and champion_flag:
            total_attacks_arma += 1
        num_criticos = int(total_attacks_arma * (1.0 / 6.0))
        out['criticos'] = num_criticos

        crit_effect = perfil.get('crit_effect') or 'none'
        out['crit_effect'] = crit_effect

        heridas_totales = out.get('heridas_normales', 0) + out.get('auto_wound', 0)
        no_salvadas = out.get('no_salv_normales', 0) + out.get('no_salv_autow', 0)
        out['heridas_salvadas'] = heridas_totales - no_salvadas

        total_heridas += out.get('total_heridas', 0)
        detalle.append((arma.get('name', 'arma'), out))

    resumen_atac = {
        'name': unidad_atac.get('name', ''),
        'models': models_atac,
        'attacks_per_model': ataques_pm_total,
        'total_attacks': ataques_totales,
        'wounds_per_model': int(unidad_atac.get('wounds', 1)),
        'total_wounds': models_atac * int(unidad_atac.get('wounds', 1)),
    }

    if unidad_def.get("current_models") is not None:
        models_def = int(unidad_def.get("current_models", 0))
    else:
        models_def = int(unidad_def.get("base_size", 1)) * (2 if bool(unidad_def.get("reinforced", False)) else 1)

    resumen_def = {
        'name': unidad_def.get('name', ''),
        'models': models_def,
        'total_attacks': 0.0,
        'wounds_per_model': int(unidad_def.get('wounds', 1)),
        'total_wounds': models_def * int(unidad_def.get('wounds', 1)),
    }

    return total_heridas, detalle, resumen_atac, resumen_def


def mostrar_detalle_armas_en_combate(unidad: Dict[str, Any], detalle: List[Tuple[str, Dict[str, Any]]], miniaturas_vivas: int) -> None:
    from utils import redondear as _r
    armas = obtener_armas_de_unidad(unidad.get('id', ''))
    for nombre_arma, out in detalle:
        ataques_por_mini = 0.0
        for arma in armas:
            if arma.get('name', '') == nombre_arma:
                if arma.get('attacks') is not None:
                    ataques_por_mini = float(arma['attacks'])
                elif arma.get('attacks_formula') is not None:
                    ataques_por_mini = dice_average(arma.get('attacks_formula'))
                break
        ataques_arma = ataques_por_mini * miniaturas_vivas
        p_6 = 1.0 / 6.0
        num_criticos = _r(ataques_arma * p_6)

        crit_info = ''
        heridas_normales = out.get('heridas_finales_normales', 0)
        heridas_mortales = out.get('mortales_post_ward', 0)
        if out.get('crit_effect') == 'mortal_wounds':
            crit_info = f" → {_r(heridas_mortales)} mortales (ignoran armadura)"
        elif out.get('crit_effect') == 'auto_wound':
            crit_info = f" → {_r(out.get('no_salv_autow_post_ward', 0))} heridas auto."

        desglose = ''
        if heridas_mortales > 0:
            desglose = f" (normal={_r(heridas_normales)} + mort={_r(heridas_mortales)})"

        print(f"    - {nombre_arma}: ataques={_r(ataques_arma)} | criticos={num_criticos}{crit_info} | heridas={_r(out['total_heridas'])}{desglose} | salvadas={_r(out.get('heridas_salvadas', 0))}")


def simular_combate_completo(atacante_u: Dict[str, Any], defensor_u: Dict[str, Any], max_rondas: int = 10) -> Dict[str, Any]:
    print("\n=== SIMULACIÓN DE COMBATE COMPLETO ===")
    ronda = 1
    atacante_vivo = int(atacante_u.get('base_size', 1)) * (2 if bool(atacante_u.get('reinforced', False)) else 1)
    defensor_vivo = int(defensor_u.get('base_size', 1)) * (2 if bool(defensor_u.get('reinforced', False)) else 1)
    atacante_u = dict(atacante_u)
    defensor_u = dict(defensor_u)
    atacante_nombre = atacante_u.get('name', 'Atacante')
    defensor_nombre = defensor_u.get('name', 'Defensor')

    while atacante_vivo > 0 and defensor_vivo > 0 and ronda <= max_rondas:
        print(f"\n--- Ronda {ronda} ---")
        atacante_u['current_models'] = atacante_vivo
        defensor_u['current_models'] = defensor_vivo
        total_general, detalle, res_atac, res_def = combate_media_multiarmas(atacante_u, defensor_u, carga=(ronda==1))
        bajas_defensor = int(total_general // res_def['wounds_per_model']) if res_def['wounds_per_model'] else 0
        defensor_vivo = max(defensor_vivo - bajas_defensor, 0)

        # Mostrar ataques totales calculados de forma consistente con combate_media_multiarmas
        ataques_pm = float(res_atac.get('attacks_per_model', 0.0))
        ataques_totales_correctos = ataques_pm * atacante_vivo + (1 if bool(atacante_u.get('champion', False)) else 0)
        print(f"Atacante: {res_atac['name']} | Minis: {atacante_vivo} | Ataques totales: {redondear(ataques_totales_correctos)}")
        print(f"  Media de heridas causadas: {redondear(total_general)}")

        mostrar_detalle_armas_en_combate(atacante_u, detalle, atacante_vivo)

        print(f"Bajas defensor: {bajas_defensor} | Minis defensor restantes: {defensor_vivo}")
        if defensor_vivo == 0:
            print(f"El defensor ha sido eliminado. Gana {atacante_nombre}.")
            break

        defensor_u['current_models'] = defensor_vivo
        total_def, detalle_def, res_def_resp, res_atac_resp = combate_media_multiarmas(defensor_u, atacante_u, carga=False)
        bajas_atacante = int(total_def // res_atac['wounds_per_model']) if res_atac['wounds_per_model'] else 0
        atacante_vivo = max(atacante_vivo - bajas_atacante, 0)

        ataques_totales_defensor = float(res_def_resp.get('attacks_per_model', 0.0)) * defensor_vivo
        print(f"Defensor: {res_def['name']} | Minis: {defensor_vivo} | Ataques totales: {redondear(ataques_totales_defensor)}")
        print(f"  Media de heridas causadas: {redondear(total_def)}")

        mostrar_detalle_armas_en_combate(defensor_u, detalle_def, defensor_vivo)

        print(f"Bajas atacante: {bajas_atacante} | Minis atacante restantes: {atacante_vivo}")
        if atacante_vivo == 0:
            print(f"El atacante ha sido eliminado. Gana {defensor_nombre}.")
            break

        ronda += 1

    if ronda > max_rondas:
        ganador = "Tiempo agotado (empate)"
    elif defensor_vivo == 0 and atacante_vivo > 0:
        ganador = atacante_nombre
    elif atacante_vivo == 0:
        ganador = defensor_nombre
    else:
        ganador = "Empate"

    print(f"\n¡Victoria para: {ganador}!")
    return {
        'ganador': ganador,
        'rondas': ronda,
        'atacante_restante': atacante_vivo,
        'defensor_restante': defensor_vivo,
    }


def simular_combate_completo_str(atacante_u: Dict[str, Any], defensor_u: Dict[str, Any], max_rondas: int = 10) -> str:
    import io, sys
    buf = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = buf
        sim_result = simular_combate_completo(atacante_u, defensor_u, max_rondas=max_rondas)
        print("\nResultado resumido:")
        print(sim_result)
    finally:
        sys.stdout = old_stdout
    return buf.getvalue()


def mostrar_analisis_inicial(atacante_id: str, defensor_id: str, carga: bool = True) -> None:
    atacante_u = obtener_unidad_por_id(atacante_id)
    defensor_u = obtener_unidad_por_id(defensor_id)
    if not atacante_u or not defensor_u:
        print("ERROR: No se pudieron obtener los datos de las unidades.")
        return
    total_general, detalle, res_atac, res_def = combate_media_multiarmas(atacante_u, defensor_u, carga=carga)
    print(f"— Atacante: {res_atac['name']}  modelos={res_atac['models']}, ataques_totales={int(res_atac['total_attacks'])}, heridas_totales={res_atac['total_wounds']}")
    print(f"— Defensor: {res_def['name']}   modelos={res_def['models']},  heridas_totales={res_def['total_wounds']}")
    print(f"\nHeridas esperadas totales (todas las armas): {int(total_general)}")

    # Simular combate completo
    simular_combate_completo(atacante_u, defensor_u)

# IDs de unidades de ejemplo
# kroxigor = "500c03e5-085b-4c5f-acbf-9d78a8d40591"
# kurnoths = "7ff18894-a6e9-4203-94fa-fbea1f4ad227"
# lanceros_en_agradon = "9da7561a-6b28-4eef-a6ee-10b93504d9a5"
# guerreros saurios = 'a7ad4e3c-87b7-4182-9e8d-ce8dd0b1a03e'
# reyesplaga = 'cefbb712-fea6-4a20-8549-e88075c0f129'
if __name__ == "__main__":
    print("=== SIMULADOR DE COMBATE AGE OF SIGMAR ===")
    atacante_id = '7ff18894-a6e9-4203-94fa-fbea1f4ad227'  
    defensor_id = 'cefbb712-fea6-4a20-8549-e88075c0f129'  

    # Ejecutar la simulación desde la función principal
    mostrar_analisis_inicial(atacante_id, defensor_id, carga=True)


def mostrar_resultados_simulacion(total_general: float, detalle: List[Tuple[str, Dict[str, Any]]], 
                           res_atac: Dict[str, Any], res_def: Dict[str, Any]) -> None:
    """
    Muestra los resultados de la simulación de combate.
    
    Args:
        total_general: Daño total causado
        detalle: Detalles de daño por arma
        res_atac: Resumen del atacante
        res_def: Resumen del defensor
    """
    print(f"\n=== RESULTADOS DE LA SIMULACIÓN ===")
    print(f"— Atacante: {res_atac['name']}  modelos={res_atac['models']}, ataques_totales={int(res_atac['total_attacks'])}, heridas_totales={res_atac['total_wounds']}")
    print(f"— Defensor: {res_def['name']}   modelos={res_def['models']},  heridas_totales={res_def['total_wounds']}")
    print(f"\nHeridas esperadas totales (todas las armas): {int(total_general)}")

    # Calcular bajas del defensor
    bajas_defensor = int(total_general // res_def['wounds_per_model']) if res_def['wounds_per_model'] else 0
    print(f"Bajas estimadas del defensor: {bajas_defensor}")

    # Retirar bajas del defensor
    models_def_restantes = max(res_def['models'] - bajas_defensor, 0)
    print(f"Miniaturas restantes del defensor: {models_def_restantes}")
    
    # Mostrar detalle por arma
    print("\nDetalle por arma:")
    from utils import redondear
    for nombre_arma, out in detalle:
        total_arma = out["total_heridas"]
        normales = out["heridas_finales_normales"]
        mortales = out["mortales_post_ward"]
        
        # Mostrar efectos de crítico si hay
        crit_info = ""
        if out.get('crit_effect') == 'mortal_wounds':
            crit_info = f" → {redondear(mortales)} mortales (ignoran armadura)"
        elif out.get('crit_effect') == 'auto_wound':
            crit_info = f" → {redondear(out.get('no_salv_autow_post_ward', 0))} heridas auto."
            
        # Mostrar el desglose de heridas normales y mortales
        desglose = ""
        if mortales > 0:
            desglose = f" (normal={redondear(normales)} + mort={redondear(mortales)})"
            
        print(f"  - {nombre_arma}: total={redondear(total_arma)}{desglose} | críticos={redondear(out.get('criticos', 0))}{crit_info}")
    
    return models_def_restantes



















