def media_impactos(unit):
    total_attacks = unit["attacks"]*(unit["base_size"] * (2 if unit [reinforced] else 1))
    prob_hit = (7 - unit["to_hit"])/6

    crit_effect = unit.get("crit_effect", "none")
    crit_value = unit.get("crit_value", 0)

    prob_6 = 1/6

    impactos_normales = total_attacks * (prob_hit - prob_6) if crit_effect in ["mortal_wounds","auto_wound"] else total_attacks * prob_hit
    heridas_mortales = total_attacks * prob_6 * crit_value if crit_effect == "mortal_wounds else" else 0
    heridas_auto = total_attacks * prob_6 if crit_effect == "auto_wound" else 0

    return{
        "Impactor_normales": impactos_normales,
        "Heridas_mortales": heridas_mortales,
        "Heridas_auto": heridas_auto
    }

def media_heridas(unit, impactos):
    prob_wound = (7 - unit["to_wound"])/6
    return impactos * prob_wound

def media_salvadas(defender, heridas, rend):
    save_total = defender["save"] + rend
    prob_fail = (save_total -1)/6 if save_total <= 6 else 1
    return heridas * prob_fail

def combate_media(attacker, defender, carga=False):
    rend_total = attacker["rend"]
    if carga and attacker.get("rend_on_charge"):
        rend_total += attacker["rend_on_charge"]

    resultado = media_impactos(attacker)
    heridas_normales = media_heridas(attacker, resultado["impactos_normales"])
    heridas_auto = resultado["heridas_auto"]

    heridas_totales = heridas_normales + heridas_auto
    no_salvadas = media_salvadas(defender, heridas_totales, rend_total)
    heridas_finales = no_salvadas * attacker["damage"]

    total_heridas = resultado["heridas_mortales"]+heridas_finales

    return{
        "impactos_normales": resultado["impactos_normales"],
        "heridas_mortales": resultado["heridas_mortales"],
        "heridas_automaticas": heridas_auto,
        "heridas_normales": heridas_normales,
        "heridas_no_salvadas": no_salvadas,
        "heridas__finales": heridas_finales,
        "total_heridas": total_heridas
    }