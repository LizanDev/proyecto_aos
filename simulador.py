"""
Simulador de combate para Age of Sigmar.
Calcula las probabilidades de éxito en combates entre unidades.
"""

from typing import Dict, List, Tuple, Any, Optional, Union
import os
import re
from dotenv import load_dotenv
from supabase import create_client, Client
from combar_logic import combate_media
from services.unidad_service import obtener_unidad_por_id, obtener_armas_de_unidad

# Expresión regular para parsear términos de dados
_dice_term = re.compile(r"\s*([+-]?)\s*(?:(\d*)[dD](\d+)|(\d+))\s*")

def dice_average(expr: Union[str, int, float, None]) -> float:
    """
    Convierte '2d6+1d3+3-1' en su media: 2*(6+1)/2 + 1*(3+1)/2 + 3 - 1 = 7 + 2 + 2 = 11
    Admite 'd3', 'D6', '3', combinaciones con +/-, y espacios.
    
    Args:
        expr: La expresión de dados a convertir, puede ser un string, un número o None
        
    Returns:
        El valor promedio como float
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
            except ValueError:
                return 0.0
        
        sign, n_str, faces_str, flat_str = m.groups()
        sign_mult = -1.0 if sign == '-' else 1.0

        if faces_str:  # término con dados: n d faces
            n = int(n_str) if n_str else 1
            faces = int(faces_str)
            avg = n * (faces + 1) / 2.0
            total += sign_mult * avg
        else:  # término plano
            total += sign_mult * float(flat_str)

        i = m.end()
        # saltar signos/espacios extra
        while i < len(s) and s[i].isspace():
            i += 1
    
    return total


def combate_media_multiarmas(unidad_atac: Dict[str, Any], unidad_def: Dict[str, Any], carga: bool = False) -> Tuple[float, List[Tuple[str, Dict[str, Any]]], Dict[str, Any], Dict[str, Any]]:
    """
    Calcula el resultado de un combate entre dos unidades considerando múltiples armas.
    
    Args:
        unidad_atac: Unidad atacante
        unidad_def: Unidad defensora
        carga: Si el atacante ha cargado este turno
        
    Returns:
        Tuple con (daño_total, detalles_por_arma, resumen_atacante, resumen_defensor)
    """
    # 1) Cargar todas las armas del atacante
    armas = obtener_armas_de_unidad(unidad_atac.get("id", ""))
    if not armas:
        # Sin armas no hay combate
        return 0.0, [], {}, {}

    # 2) Resumen atacante
    models_atac = int(unidad_atac.get("base_size", 1)) * (2 if bool(unidad_atac.get("reinforced", False)) else 1)
    wounds_pm_atac = int(unidad_atac.get("wounds", 1))
    ataques_pm_total = 0.0
    total = 0.0
    detalle = []

    # 3) Procesar cada arma (sumar ataques por miniatura)
    perfiles_armas = []
    for arma in armas:
        perfil = construir_perfil_ataque(unidad_atac, arma, carga=carga)
        perfiles_armas.append((arma, perfil))
        ataques_pm_total += float(perfil.get("attacks", 0.0))

    # Cálculo correcto de ataques totales: ataques por miniatura * número de miniaturas
    ataques_totales = ataques_pm_total * models_atac

    # Calcular daño de cada arma
    for arma, perfil in perfiles_armas:
        # Depuración (opcional, comentar en producción)
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
        total_attacks = perfil["attacks"] * models_atac  # Corrección: usar models_atac directamente
        num_criticos = int(total_attacks * p_6)  # Convertir a entero
        out['criticos'] = num_criticos
        
        # Añadir efecto de críticos para mostrar en la UI
        crit_effect = perfil.get("crit_effect")
        crit_effect = (crit_effect or "none").strip().lower()
        out['crit_effect'] = crit_effect
        
        # También añadir heridas salvadas para mejor visualización
        heridas_totales = out.get("heridas_normales", 0) + out.get("auto_wound", 0)
        no_salvadas = out.get("no_salv_normales", 0) + out.get("no_salv_autow", 0)
        out['heridas_salvadas'] = heridas_totales - no_salvadas
        
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

def resumen_unidad_multiarmas(unidad: Dict[str, Any], carga: bool = False) -> Dict[str, Any]:
    """
    Genera un resumen de estadísticas para una unidad considerando todas sus armas.
    
    Args:
        unidad: Datos de la unidad
        carga: Si la unidad está cargando
        
    Returns:
        Diccionario con el resumen de la unidad
    """
    try:
        armas = obtener_armas_de_unidad(unidad.get("id", ""))
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
    except Exception as e:
        print(f"Error al generar resumen de unidad: {e}")
        return {
            "name": unidad.get("name", ""),
            "models": 0,
            "attacks_per_model": 0.0,
            "total_attacks": 0.0,
            "wounds_per_model": 0,
            "total_wounds": 0,
        }

def construir_perfil_ataque(unidad: Dict[str, Any], arma: Dict[str, Any], carga: bool=False) -> Dict[str, Any]:
    """
    Construye un perfil de ataque combinando datos de unidad y arma.
    
    Args:
        unidad: Datos de la unidad
        arma: Datos del arma
        carga: Si la unidad está cargando
        
    Returns:
        Perfil de ataque completo
    """
    # rend total (arma + bonif por cargar de la unidad si existe)
    rend_total = arma.get("rend", 0) or 0
    if carga and unidad.get("rend_on_charge"):
        try:
            rend_total += int(unidad["rend_on_charge"])
        except (ValueError, TypeError):
            pass  # Si no se puede convertir, usar el valor base

    # ataques: número o fórmula
    attacks = arma.get("attacks")
    if attacks is None:
        attacks = dice_average(arma.get("attacks_formula"))

    # daño: número o fórmula
    damage = arma.get("damage")
    if damage is None:
        damage = dice_average(arma.get("damage_formula"))

    try:
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
    except Exception as e:
        print(f"Error al construir perfil de ataque: {e}")
        # Devolver un perfil mínimo en caso de error
        return {
            "base_size": 1,
            "reinforced": False,
            "attacks": 0.0,
            "to_hit": 7,
            "to_wound": 7,
            "rend": 0,
            "damage": 0.0,
            "crit_effect": "none",
        }
def resumen_unidad(unidad: Dict[str, Any], arma: Dict[str, Any], carga: bool = False) -> Dict[str, Any]:
    """
    Genera un resumen de estadísticas para una unidad considerando un arma específica.
    
    Args:
        unidad: Datos de la unidad
        arma: Datos del arma específica
        carga: Si la unidad está cargando
        
    Returns:
        Diccionario con el resumen de la unidad
    """
    try:
        # Reutiliza el builder para tener attacks/daño numéricos
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
    except Exception as e:
        print(f"Error al generar resumen de unidad con arma específica: {e}")
        return {
            "name": unidad.get("name", ""),
            "models": 0,
            "attacks_per_model": 0.0,
            "total_attacks": 0.0,
            "wounds_per_model": 0,
            "total_wounds": 0,
        }



def ejecutar_simulacion(atacante_id: str, defensor_id: str, carga: bool = True) -> None:
    """
    Ejecuta una simulación completa entre dos unidades y muestra los resultados.
    
    Args:
        atacante_id: ID de la unidad atacante
        defensor_id: ID de la unidad defensora
        carga: Si el atacante ha cargado
    """
    try:
        # Obtener datos de unidades
        print(f"Obteniendo datos de unidades...")
        atacante_u = obtener_unidad_por_id(atacante_id)
        defensor_u = obtener_unidad_por_id(defensor_id)
        
        if not atacante_u or not defensor_u:
            print(f"ERROR: No se pudieron obtener los datos de las unidades.")
            return

        # Ejecutar simulación
        print(f"Ejecutando simulación de combate...")
        total_general, detalle, res_atac, res_def = combate_media_multiarmas(atacante_u, defensor_u, carga=carga)
        
        # Mostrar resultados
        mostrar_resultados_simulacion(total_general, detalle, res_atac, res_def)
        
    except Exception as e:
        print(f"Error en la simulación: {e}")

def mostrar_detalle_armas_en_combate(unidad: Dict[str, Any], detalle: List[Tuple[str, Dict[str, Any]]], 
                                 miniaturas_vivas: int) -> None:
    """
    Muestra detalles de armas en combate con información de críticos.
    
    Args:
        unidad: Datos de la unidad
        detalle: Detalles de daño por arma
        miniaturas_vivas: Número de miniaturas vivas
    """
    armas = obtener_armas_de_unidad(unidad.get("id", ""))
    
    for nombre_arma, out in detalle:
        # Buscar el arma correspondiente
        ataques_por_mini = 0.0
        for arma in armas:
            if arma.get("name", "") == nombre_arma:
                if arma.get("attacks") is not None:
                    ataques_por_mini = float(arma["attacks"])
                elif arma.get("attacks_formula") is not None:
                    ataques_por_mini = dice_average(arma.get("attacks_formula"))
                break
                
        ataques_arma = ataques_por_mini * miniaturas_vivas
        
        # Calcular críticos y efectos
        p_6 = 1.0 / 6.0
        num_criticos = int(ataques_arma * p_6)
        
        # Formatear la información sobre críticos
        crit_info = ""
        heridas_normales = out.get('heridas_finales_normales', 0)
        heridas_mortales = out.get('mortales_post_ward', 0)
        
        if out.get('crit_effect') == 'mortal_wounds':
            crit_info = f" → {int(heridas_mortales)} mortales (ignoran armadura)"
        elif out.get('crit_effect') == 'auto_wound':
            crit_info = f" → {int(out.get('no_salv_autow_post_ward', 0))} heridas auto."
            
        # Mostrar el desglose de heridas normales y mortales
        desglose = ""
        if heridas_mortales > 0:
            desglose = f" (normal={heridas_normales:.2f} + mort={int(heridas_mortales)})"
            
        print(f"    - {nombre_arma}: ataques={ataques_arma:.2f} | criticos={num_criticos}{crit_info} | " 
              f"heridas={out['total_heridas']:.2f}{desglose} | salvadas={out.get('heridas_salvadas', 0):.2f}")


def simular_combate_completo(atacante_u: Dict[str, Any], defensor_u: Dict[str, Any], 
                        max_rondas: int = 10) -> Dict[str, Any]:
    """
    Simula un combate completo entre dos unidades hasta que una sea eliminada.
    
    Args:
        atacante_u: Datos de la unidad atacante
        defensor_u: Datos de la unidad defensora
        max_rondas: Número máximo de rondas antes de declarar empate
        
    Returns:
        Diccionario con los resultados de la simulación
    """
    print("\n=== SIMULACIÓN DE COMBATE COMPLETO ===")
    
    ronda = 1
    atacante_vivo = int(atacante_u.get("base_size", 1)) * (2 if bool(atacante_u.get("reinforced", False)) else 1)
    defensor_vivo = int(defensor_u.get("base_size", 1)) * (2 if bool(defensor_u.get("reinforced", False)) else 1)
    atacante_u = dict(atacante_u)
    defensor_u = dict(defensor_u)
    
    atacante_nombre = atacante_u.get("name", "Atacante")
    defensor_nombre = defensor_u.get("name", "Defensor")
    
    while atacante_vivo > 0 and defensor_vivo > 0 and ronda <= max_rondas:
        print(f"\n--- Ronda {ronda} ---")
        # Ataca el atacante
        atacante_u['base_size'] = atacante_vivo
        defensor_u['base_size'] = defensor_vivo
        total_general, detalle, res_atac, res_def = combate_media_multiarmas(atacante_u, defensor_u, carga=ronda==1)
        bajas_defensor = int(total_general // res_def['wounds_per_model']) if res_def['wounds_per_model'] else 0
        defensor_vivo = max(defensor_vivo - bajas_defensor, 0)
        
        # Calcular el total de ataques correctamente (ataques por mini * minis)
        ataques_totales_correctos = res_atac["attacks_per_model"] * atacante_vivo
        print(f"Atacante: {res_atac['name']} | Minis: {atacante_vivo} | Ataques totales: {ataques_totales_correctos:.2f}")
        print(f"  Media de heridas causadas: {total_general:.2f}")
        
        # Mostrar detalle por arma
        mostrar_detalle_armas_en_combate(atacante_u, detalle, atacante_vivo)
            
        print(f"Bajas defensor: {bajas_defensor} | Minis defensor restantes: {defensor_vivo}")
        if defensor_vivo == 0:
            print(f"El defensor ha sido eliminado. Gana {atacante_nombre}.")
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
        
        # Mostrar detalle por arma del defensor
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
    
    resultado = {
        "ganador": ganador,
        "rondas": ronda,
        "atacante_restante": atacante_vivo,
        "defensor_restante": defensor_vivo
    }
    
    return resultado


def mostrar_analisis_inicial(atacante_id: str, defensor_id: str, carga: bool = True) -> None:
    """
    Muestra un análisis inicial de la simulación de combate.
    
    Args:
        atacante_id: ID de la unidad atacante
        defensor_id: ID de la unidad defensora
        carga: Si el atacante ha cargado
    """
    # Obtener datos de unidades
    atacante_u = obtener_unidad_por_id(atacante_id)
    defensor_u = obtener_unidad_por_id(defensor_id)
    
    if not atacante_u or not defensor_u:
        print(f"ERROR: No se pudieron obtener los datos de las unidades.")
        return
        
    # Resúmenes
    total_general, detalle, res_atac, res_def = combate_media_multiarmas(atacante_u, defensor_u, carga=carga)
    
    # Mostrar resultados
    print(f"— Atacante: {res_atac['name']}  modelos={res_atac['models']}, ataques_totales={res_atac['total_attacks']:.2f}, heridas_totales={res_atac['total_wounds']}")
    print(f"— Defensor: {res_def['name']}   modelos={res_def['models']},  heridas_totales={res_def['total_wounds']}")
    print(f"\nHeridas esperadas totales (todas las armas): {total_general:.2f}")

    # Calcular bajas del defensor
    bajas_defensor = int(total_general // res_def['wounds_per_model']) if res_def['wounds_per_model'] else 0
    print(f"Bajas estimadas del defensor: {bajas_defensor}")

    # Retirar bajas del defensor
    models_def_restantes = max(res_def['models'] - bajas_defensor, 0)
    print(f"Miniaturas restantes del defensor: {models_def_restantes}")

    # Simular respuesta del defensor si quedan miniaturas
    models_atac_restantes = res_atac['models']  # Por defecto, no hay bajas
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
    if bajas_defensor >= res_def['models'] and models_atac_restantes > 0:
        ganador = res_atac['name']
    elif models_atac_restantes == 0:
        ganador = res_def['name']
    else:
        ganador = 'Empate o combate indeciso'
    print(f"Ganador estimado: {ganador}")

    # Mostrar detalles por arma para el reporte inicial
    print("\n=== DETALLE POR ARMA ===")
    for nombre_arma, out in detalle:
        total_arma = out["total_heridas"]
        normales = out["heridas_finales_normales"]
        mortales = out["mortales_post_ward"]
        
        # Añadir información detallada de críticos
        crit_info = ""
        if out.get('crit_effect') == 'mortal_wounds':
            crit_info = f" (incluye {int(mortales)} mortales)"
        elif out.get('crit_effect') == 'auto_wound':
            crit_info = f" (incluye {int(out.get('no_salv_autow_post_ward', 0))} de heridas automáticas)"
            
        print(f"  - {nombre_arma}: total={total_arma:.2f} | normales={normales:.2f} | mortales={int(mortales)}{crit_info}")

    # Simular combate completo
    simular_combate_completo(atacante_u, defensor_u)

# IDs de unidades de ejemplo
# kroxigor = "500c03e5-085b-4c5f-acbf-9d78a8d40591"
# kurnoths = "7ff18894-a6e9-4203-94fa-fbea1f4ad227"
# lanceros_en_agradon = "9da7561a-6b28-4eef-a6ee-10b93504d9a5"
# guerreros saurios = 'a7ad4e3c-87b7-4182-9e8d-ce8dd0b1a03e'
if __name__ == "__main__":
    print("=== SIMULADOR DE COMBATE AGE OF SIGMAR ===")
    atacante_id = '7ff18894-a6e9-4203-94fa-fbea1f4ad227'  # kurnoths
    defensor_id = '500c03e5-085b-4c5f-acbf-9d78a8d40591'  # guerreros saurios

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
    print(f"— Atacante: {res_atac['name']}  modelos={res_atac['models']}, ataques_totales={res_atac['total_attacks']:.2f}, heridas_totales={res_atac['total_wounds']}")
    print(f"— Defensor: {res_def['name']}   modelos={res_def['models']},  heridas_totales={res_def['total_wounds']}")
    print(f"\nHeridas esperadas totales (todas las armas): {total_general:.2f}")

    # Calcular bajas del defensor
    bajas_defensor = int(total_general // res_def['wounds_per_model']) if res_def['wounds_per_model'] else 0
    print(f"Bajas estimadas del defensor: {bajas_defensor}")

    # Retirar bajas del defensor
    models_def_restantes = max(res_def['models'] - bajas_defensor, 0)
    print(f"Miniaturas restantes del defensor: {models_def_restantes}")
    
    # Mostrar detalle por arma
    print("\nDetalle por arma:")
    for nombre_arma, out in detalle:
        total_arma = out["total_heridas"]
        normales = out["heridas_finales_normales"]
        mortales = out["mortales_post_ward"]
        
        # Mostrar efectos de crítico si hay
        crit_info = ""
        if out.get('crit_effect') == 'mortal_wounds':
            crit_info = f" → {mortales:.2f} mortales (ignoran armadura)"
        elif out.get('crit_effect') == 'auto_wound':
            crit_info = f" → {int(out.get('no_salv_autow_post_ward', 0))} heridas auto."
            
        # Mostrar el desglose de heridas normales y mortales
        desglose = ""
        if mortales > 0:
            desglose = f" (normal={normales:.2f} + mort={mortales:.2f})"
            
        print(f"  - {nombre_arma}: total={total_arma:.2f}{desglose} | críticos={out.get('criticos', 0):.2f}{crit_info}")
    
    return models_def_restantes

# Esta parte del código ha sido movida a la función mostrar_resultados_simulacion
# y a la función mostrar_analisis_inicial que se define más adelante
# Este código ha sido movido a la función mostrar_analisis_inicial

def simular_combate_completo(atacante_u: Dict[str, Any], defensor_u: Dict[str, Any], 
                        max_rondas: int = 10) -> Dict[str, Any]:
    """
    Simula un combate completo entre dos unidades hasta que una sea eliminada.
    
    Args:
        atacante_u: Datos de la unidad atacante
        defensor_u: Datos de la unidad defensora
        max_rondas: Número máximo de rondas antes de declarar empate
        
    Returns:
        Diccionario con los resultados de la simulación
    """
    print("\n=== SIMULACIÓN DE COMBATE COMPLETO ===")
    
    ronda = 1
    atacante_vivo = int(atacante_u.get("base_size", 1)) * (2 if bool(atacante_u.get("reinforced", False)) else 1)
    defensor_vivo = int(defensor_u.get("base_size", 1)) * (2 if bool(defensor_u.get("reinforced", False)) else 1)
    atacante_u = dict(atacante_u)
    defensor_u = dict(defensor_u)
    
    atacante_nombre = atacante_u.get("name", "Atacante")
    defensor_nombre = defensor_u.get("name", "Defensor")
    
    while atacante_vivo > 0 and defensor_vivo > 0 and ronda <= max_rondas:
        print(f"\n--- Ronda {ronda} ---")
        # Ataca el atacante
        atacante_u['base_size'] = atacante_vivo
        defensor_u['base_size'] = defensor_vivo
        total_general, detalle, res_atac, res_def = combate_media_multiarmas(atacante_u, defensor_u, carga=ronda==1)
        bajas_defensor = int(total_general // res_def['wounds_per_model']) if res_def['wounds_per_model'] else 0
        defensor_vivo = max(defensor_vivo - bajas_defensor, 0)
        
        # Calcular el total de ataques correctamente (ataques por mini * minis)
        ataques_totales_correctos = res_atac["attacks_per_model"] * atacante_vivo
        print(f"Atacante: {res_atac['name']} | Minis: {atacante_vivo} | Ataques totales: {ataques_totales_correctos:.2f}")
        print(f"  Media de heridas causadas: {total_general:.2f}")
        
        # Mostrar detalle por arma
        mostrar_detalle_armas_en_combate(atacante_u, detalle, atacante_vivo)
            
        print(f"Bajas defensor: {bajas_defensor} | Minis defensor restantes: {defensor_vivo}")
        if defensor_vivo == 0:
            print(f"El defensor ha sido eliminado. Gana {atacante_nombre}.")
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
        
        # Mostrar detalle por arma del defensor
        mostrar_detalle_armas_en_combate(defensor_u, detalle_def, defensor_vivo)
            
        print(f"Bajas atacante: {bajas_atacante} | Minis atacante restantes: {atacante_vivo}")
        if atacante_vivo == 0:
            print(f"El atacante ha sido eliminado. Gana {defensor_nombre}.")
            break
            
        ronda += 1

    # Determinar el ganador
    resultado = {}
    if atacante_vivo > 0 and defensor_vivo == 0:
        ganador = atacante_nombre
    elif atacante_vivo == 0 and defensor_vivo > 0:
        ganador = defensor_nombre
    elif ronda > max_rondas:
        ganador = "Empate por tiempo"
    else:
        ganador = "Empate"
        
    print(f"\n¡Victoria para: {ganador}!")
    
    resultado = {
        "ganador": ganador,
        "rondas": ronda,
        "atacante_restante": atacante_vivo,
        "defensor_restante": defensor_vivo
    }
    
    return resultado

def mostrar_detalle_armas_en_combate(unidad: Dict[str, Any], detalle: List[Tuple[str, Dict[str, Any]]], 
                                 miniaturas_vivas: int) -> None:
    """
    Muestra detalles de armas en combate con información de críticos.
    
    Args:
        unidad: Datos de la unidad
        detalle: Detalles de daño por arma
        miniaturas_vivas: Número de miniaturas vivas
    """
    armas = obtener_armas_de_unidad(unidad.get("id", ""))
    
    for nombre_arma, out in detalle:
        # Buscar el arma correspondiente
        ataques_por_mini = 0.0
        for arma in armas:
            if arma.get("name", "") == nombre_arma:
                if arma.get("attacks") is not None:
                    ataques_por_mini = float(arma["attacks"])
                elif arma.get("attacks_formula") is not None:
                    ataques_por_mini = dice_average(arma.get("attacks_formula"))
                break
                
        ataques_arma = ataques_por_mini * miniaturas_vivas
        
        # Calcular críticos y efectos
        p_6 = 1.0 / 6.0
        num_criticos = int(ataques_arma * p_6)
        
        # Formatear la información sobre críticos
        crit_info = ""
        heridas_normales = out.get('heridas_finales_normales', 0)
        heridas_mortales = out.get('mortales_post_ward', 0)
        
        if out.get('crit_effect') == 'mortal_wounds':
            crit_info = f" → {int(heridas_mortales)} mortales (ignoran armadura)"
        elif out.get('crit_effect') == 'auto_wound':
            crit_info = f" → {int(out.get('no_salv_autow_post_ward', 0))} heridas auto."
            
        # Mostrar el desglose de heridas normales y mortales
        desglose = ""
        if heridas_mortales > 0:
            desglose = f" (normal={heridas_normales:.2f} + mort={int(heridas_mortales)})"
            
        print(f"    - {nombre_arma}: ataques={ataques_arma:.2f} | criticos={num_criticos}{crit_info} | " 
              f"heridas={out['total_heridas']:.2f}{desglose} | salvadas={out.get('heridas_salvadas', 0):.2f}")

# Este código ha sido movido a la función mostrar_analisis_inicial









