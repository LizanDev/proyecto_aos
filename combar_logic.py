def _clamp(x, lo, hi):
    return max(lo, min(hi, x))

def _p_x_plus(target):  # prob de sacar >= target en 1d6
    if target is None:
        return 0.0
    t = int(target)
    if t >= 7: return 0.0
    if t <= 2: t = 2
    return _clamp((7 - t) / 6.0, 0.0, 1.0)

def _to_int(x, default=0):
    try:
        return int(x)
    except Exception:
        try:
            return int(float(x))
        except Exception:
            return default

def _to_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def _impactos_promedio(attacker: dict):
    """Devuelve (models, total_attacks, impactos_normales, auto_wounds, mortal_wounds)."""
    base_size  = _to_int(attacker.get("base_size", 1), 1)
    reinforced = bool(attacker.get("reinforced", False))
    models     = base_size * (2 if reinforced else 1)

    attacks  = _to_float(attacker.get("attacks", 0.0), 0.0)
    to_hit   = _to_int(attacker.get("to_hit", 7), 7)

    total_attacks = attacks * models

    p_hit = _p_x_plus(to_hit)
    p_6   = 1.0 / 6.0

    # normaliza crítico
    crit_effect = attacker.get("crit_effect")
    crit_effect = (crit_effect or "none").strip().lower()
    crit_value  = _to_float(attacker.get("crit_value", 0.0), 0.0)

    # Por defecto, todo va a impactar normal
    impactos_normales = total_attacks * p_hit
    auto_wounds   = 0.0
    mortal_wounds = 0.0

    if crit_effect == "mortal_wounds":
        # mortales EN AÑADIDO (los 6s siguen pudiendo impactar normal)
        mortal_wounds = total_attacks * p_6 * (crit_value if crit_value else 1.0)
    elif crit_effect == "auto_wound":
        # los 6s se convierten en heridas automáticas y no tiran para herir
        auto_wounds = total_attacks * p_6
        impactos_normales = max(0.0, impactos_normales - total_attacks * p_6)
    elif crit_effect == "impactos_dobles":
        # los 6s generan impactos dobles (2 impactos en lugar de 1)
        impactos_criticos = total_attacks * p_6
        impactos_normales = impactos_normales - impactos_criticos + (impactos_criticos * 2)

    # Asegura tupla válida SIEMPRE
    return (models, total_attacks, impactos_normales, auto_wounds, mortal_wounds)

def _heridas_promedio(attacker: dict, impactos_para_herir: float):
    p_wound = _p_x_plus(_to_int(attacker.get("to_wound", 7), 7))
    return impactos_para_herir * p_wound

def _fallan_salv(defender: dict, heridas_para_salvar: float, rend_total: int):
    save_base = _to_int(defender.get("save", 7), 7)
    eff_rend  = -abs(_to_int(rend_total, 0))     
    objetivo  = save_base - eff_rend             # p.ej. 5 - (-1) = 6+
    p_exito   = _p_x_plus(objetivo)
    return heridas_para_salvar * (1.0 - p_exito)



def _aplica_ward(defender: dict, heridas: float):
    ward = defender.get("ward_save", None)
    if ward is None:
        return heridas
    p_ward_ok = _p_x_plus(_to_int(ward, 7))
    return heridas * (1.0 - p_ward_ok)

def combate_media(attacker: dict, defender: dict, carga: bool = False) -> dict:
    """Calcula medias para UN perfil de arma (attacker) contra una unidad (defender)."""

    # rend total (normaliza: siempre negativo)
    rend_total = _to_int(attacker.get("rend", 0), 0)
    rend_total = -abs(rend_total)
    if carga and attacker.get("rend_on_charge"):
        roc = _to_int(attacker.get("rend_on_charge", 0), 0)
        rend_total += -abs(roc)

    models, total_attacks, impactos_normales, auto_wounds, mortal_wounds = _impactos_promedio(attacker)

    # Herir (solo para impactos normales)
    to_wound = _to_int(attacker.get("to_wound", 7), 7)
    p_wound  = _p_x_plus(to_wound)
    heridas_normales = impactos_normales * p_wound

    # Van a salvación normal (separado por claridad)
    heridas_para_salvar_normales = heridas_normales
    heridas_para_salvar_autow    = auto_wounds

    # Fallo de salvación normal aplicando rend
    def _fallan_salv(heridas):
        save_base = _to_int(defender.get("save", 7), 7)
        objetivo  = save_base - rend_total   # rend_total ya es negativo
        p_save_ok = _p_x_plus(objetivo)
        return max(0.0, heridas * (1.0 - p_save_ok))

    no_salv_normales = _fallan_salv(heridas_para_salvar_normales)
    no_salv_autow    = _fallan_salv(heridas_para_salvar_autow)

    # Ward: trata 0/None como sin ward
    ward_raw = defender.get("ward_save", None)
    ward_val = _to_int(ward_raw, 0)
    if ward_val <= 0:
        p_ward_ok = 0.0
    else:
        p_ward_ok = _p_x_plus(ward_val)

    no_salv_normales_post_ward = no_salv_normales * (1.0 - p_ward_ok)
    no_salv_autow_post_ward    = no_salv_autow * (1.0 - p_ward_ok)
    mortales_post_ward         = mortal_wounds * (1.0 - p_ward_ok)

    damage = _to_float(attacker.get("damage", 0.0), 0.0)
    heridas_finales_normales = (no_salv_normales_post_ward + no_salv_autow_post_ward) * damage
    total_heridas = mortales_post_ward + heridas_finales_normales

    return {
        "models_atacante": models,
        "ataques_totales_atacante": total_attacks,

        "impactos_para_herir": impactos_normales,
        "heridas_normales": heridas_normales,
        "auto_wound": auto_wounds,
        "mortal_wounds": mortal_wounds,

        "no_salv_normales": no_salv_normales,
        "no_salv_normales_post_ward": no_salv_normales_post_ward,
        "no_salv_autow": no_salv_autow,
        "no_salv_autow_post_ward": no_salv_autow_post_ward,
        "mortales_post_ward": mortales_post_ward,

        "heridas_finales_normales": heridas_finales_normales,
        "total_heridas": total_heridas,
    }

