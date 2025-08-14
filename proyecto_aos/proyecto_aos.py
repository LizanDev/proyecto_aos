"""Welcome to Reflex! This file outlines the steps to create a basic app."""
import reflex as rx
from typing import List,Dict,Tuple
from services.unidad_service import get_factions, get_units_by_faction


from rxconfig import config


class SimState(rx.State):
    factions_names: list[str] = []
    factions_map: dict[str, str] = {}

    units1_names: list[str] = []
    units1_map: dict[str, str] = {}
    units2_names: list[str] = []
    units2_map: dict[str, str] = {}

    faction1_name: str = ""
    faction2_name: str = ""
    unit1_name: str = ""
    unit2_name: str = ""

    charge1: bool = False
    charge2: bool = False
    bonus1: str = ""  # <-- Cambia aquí
    bonus2: str = ""  # <-- Cambia aquí

    reinforced1: bool = False
    reinforced2: bool = False
    champion1: bool = False
    champion2: bool = False

    result_text: str = ""
    result_lines: list[str] = []

    unit1_attrs: dict = {}
    unit2_attrs: dict = {}

    
    def on_load(self):
        rows = get_factions()  # [(id, name)]
        self.factions_names = [n for (_id, n) in rows]
        self.factions_map   = {n: _id for (_id, n) in rows}
        '''self.charge1 = False
        self.charge2 = False
        self.bonus1 = ""
        self.bonus2 = ""'''
        self.update_unit1_attrs()
        self.update_unit2_attrs()

    def set_faction1_name(self, name: str):
        
        self.faction1_name = name
        fid = self.factions_map.get(name, "")
        rows = get_units_by_faction(fid)
        self.units1_names = [n for (_id, n) in rows]
        self.units1_map   = {n: _id for (_id, n) in rows}
        self.unit1_name   = self.units1_names[0] if self.units1_names else ""

    def set_faction2_name(self, name: str):
        
        self.faction2_name = name
        fid = self.factions_map.get(name, "")
        rows = get_units_by_faction(fid)
        self.units2_names = [n for (_id, n) in rows]
        self.units2_map   = {n: _id for (_id, n) in rows}
        self.unit2_name   = self.units2_names[0] if self.units2_names else ""

    def set_unit1_name(self, name: str): 
        self.unit1_name = name
        self.update_unit1_attrs()
        
    def set_unit2_name(self, name: str): 
        self.unit2_name = name
        self.update_unit2_attrs()
        
    def set_charge1(self, v: bool): 
        self.charge1 = bool(v)
        if not self.charge1:
            self.bonus1 = ""
        self.update_unit1_attrs()
            
    def set_charge2(self, v: bool): 
        self.charge2 = bool(v)
        if not self.charge2:
            self.bonus2 = ""
        self.update_unit2_attrs()

    def set_bonus1(self, v: str): 
        self.bonus1 = v
        self.update_unit1_attrs()
    def set_bonus2(self, v: str): 
        self.bonus2 = v
        self.update_unit2_attrs()
    def set_reinforced1(self, v: bool): 
        self.reinforced1 = bool(v)
        self.update_unit1_attrs() 
    def set_reinforced2(self, v: bool): 
        self.reinforced2 = bool(v)
        self.update_unit2_attrs()
    def set_champion1(self, v: bool): 
        self.champion1 = bool(v)
        self.update_unit1_attrs()
    def set_champion2(self, v: bool): 
        self.champion2 = bool(v)
        self.update_unit2_attrs()

    def update_unit1_attrs(self):
        from services.unidad_service import obtener_unidad_por_id, obtener_armas_de_unidad, obtener_ataques_totales
        units_map = self.units1_map 
        unit_name = self.unit1_name 
        unit_id = units_map.get(unit_name, "")
        if not unit_id:
            self.unit1_attrs = {}
            return
        unidad = obtener_unidad_por_id(unit_id)
        if not unidad:
            self.unit1_attrs = {}
            return
        base_size = int(unidad.get("base_size", 1))
        wounds = int(unidad.get("wounds", 1))
        attacks = obtener_ataques_totales(unit_id)
        can_be_reinforced = bool(unidad.get("reinforced", False))
        reinforced = self.reinforced1 if can_be_reinforced else False
        champion = self.champion1 
        models = base_size * (2 if reinforced else 1)
        total_attacks = models * attacks + (1 if champion else 0)
        total_wounds = models * wounds

        # Obtener arma principal
        armas = obtener_armas_de_unidad(unit_id)
        arma = armas[0] if armas else {}
        base_rend = int(arma.get("rend", 0)) if arma.get("rend") is not None else 0
        base_damage = arma.get("damage_formula", "1")
        # Ajustar rend y daño si ha cargado
        rend = base_rend
        damage = base_damage
        if self.charge1:
            if self.bonus1 == "Rend -1":
                rend = base_rend - 1
            elif self.bonus1 == "Daño +1":
                try:
                    damage = str(int(base_damage) + 1)
                except Exception:
                    damage = f"{base_damage}+1"

        self.unit1_attrs = {
            "models": models,
            "wounds_per_model": wounds,
            "total_wounds": total_wounds,
            "attacks_per_model": attacks,
            "total_attacks": total_attacks,
            "champion": champion,
            "reinforced": reinforced,
            "can_be_reinforced": can_be_reinforced,
            "arma_nombre": arma.get("name", "-"),
            "arma_rend": rend,
            "arma_damage": damage,
        }
        if not can_be_reinforced:
            self.reinforced1 = False

    def update_unit2_attrs(self):
        from services.unidad_service import obtener_unidad_por_id, obtener_armas_de_unidad, obtener_ataques_totales
        units_map = self.units2_map 
        unit_name = self.unit2_name 
        unit_id = units_map.get(unit_name, "")
        if not unit_id:
            self.unit2_attrs = {}
            return
        unidad = obtener_unidad_por_id(unit_id)
        if not unidad:
            self.unit2_attrs = {}
            return
        base_size = int(unidad.get("base_size", 1))
        wounds = int(unidad.get("wounds", 1))
        attacks = obtener_ataques_totales(unit_id)
        can_be_reinforced = bool(unidad.get("reinforced", False))
        reinforced = self.reinforced2 if can_be_reinforced else False
        champion = self.champion2 
        models = base_size * (2 if reinforced else 1)
        total_attacks = models * attacks + (1 if champion else 0)
        total_wounds = models * wounds

        armas = obtener_armas_de_unidad(unit_id)
        arma = armas[0] if armas else {}
        base_rend = int(arma.get("rend", 0)) if arma.get("rend") is not None else 0
        base_damage = arma.get("damage_formula", "1")
        rend = base_rend
        damage = base_damage
        if self.charge2:
            if self.bonus2 == "Rend -1":
                rend = base_rend - 1
            elif self.bonus2 == "Daño +1":
                try:
                    damage = str(int(base_damage) + 1)
                except Exception:
                    damage = f"{base_damage}+1"

        self.unit2_attrs = {
            "models": models,
            "wounds_per_model": wounds,
            "total_wounds": total_wounds,
            "attacks_per_model": attacks,
            "total_attacks": total_attacks,
            "champion": champion,
            "reinforced": reinforced,
            "can_be_reinforced": can_be_reinforced,
            "arma_nombre": arma.get("name", "-"),
            "arma_rend": rend,
            "arma_damage": damage,
        }
        if not can_be_reinforced:
            self.reinforced2 = False

    def get_unit_attrs(self, left: bool) -> dict:
        # Devuelve los atributos de la unidad seleccionada, calculando totales
        return self.unit1_attrs if left else self.unit2_attrs

    def simulate(self):
        uid1 = self.units1_map.get(self.unit1_name, "")
        uid2 = self.units2_map.get(self.unit2_name, "")
        if not uid1 or not uid2:
            self.result_text = "Selecciona faccion y unidad en ambos lados"
            self.result_lines = []
            return
        
        self.result_text = "Simulacion lista"
        self.result_lines = [
            f"unit1={self.unit1_name} (id={uid1}) charge={self.charge1} bonus={self.bonus1}",
            f"unit2={self.unit2_name} (id={uid2}) charge={self.charge2} bonus={self.bonus2}",
         ]

def side_card(title: str, left: bool) -> rx.Component:
    S = SimState
    fac_val, set_fac = (S.faction1_name, S.set_faction1_name) if left else (S.faction2_name, S.set_faction2_name)
    unit_val, set_unit = (S.unit1_name, S.set_unit1_name) if left else (S.unit2_name, S.set_unit2_name)
    units_items = S.units1_names if left else S.units2_names
    charge_val, set_charge = (S.charge1, S.set_charge1) if left else (S.charge2, S.set_charge2)
    bonus_val, set_bonus = (S.bonus1, S.set_bonus1) if left else (S.bonus2, S.set_bonus2)
    reinforced_val, set_reinforced = (S.reinforced1, S.set_reinforced1) if left else (S.reinforced2, S.set_reinforced2)
    champion_val, set_champion = (S.champion1, S.set_champion1) if left else (S.champion2, S.set_champion2)
    attrs = S.unit1_attrs if left else S.unit2_attrs
    can_be_reinforced = attrs.get("can_be_reinforced", False)

    vstack_class = "items-end text-right" if not left else ""
    box_class = "flex-1 p-4 rounded-xl border border-zinc-800 bg-zinc-900" + (" text-right" if not left else "")
    return rx.box(
        rx.vstack(
            rx.text(title, class_name="text-lg font-bold"),
            rx.select(
                items=S.factions_names,
                value=fac_val,
                on_change=set_fac,
                placeholder="Facción",
            ),
            rx.select(
                items=units_items,
                value=unit_val,
                on_change=set_unit,
                placeholder="Unidad",
            ),
            rx.hstack(
                rx.checkbox("Ha cargado", is_checked=charge_val, on_change=set_charge),
                rx.checkbox(
                    "Reforzada",
                    is_checked=reinforced_val,
                    on_change=set_reinforced,
                    disabled=~can_be_reinforced
                ),
                rx.checkbox("Campeón", is_checked=champion_val, on_change=set_champion),
                class_name="gap-4"
            ),
            rx.cond(
                charge_val,
                rx.box(
                    rx.radio_group(
                        items=["Rend -1", "Daño +1"],
                        value=bonus_val,
                        on_change=set_bonus,
                        class_name="gap-2",
                    ),
                    class_name="mt-2"
                )
            ),
            rx.cond(
                attrs != {},
                rx.box(
                    rx.text(f"Tamaño de unidad: {attrs.get('models', '-')}", class_name="text-xs"),
                    rx.text(f"Heridas por miniatura: {attrs.get('wounds_per_model', '-')}", class_name="text-xs"),
                    rx.text(f"Heridas totales: {attrs.get('total_wounds', '-')}", class_name="text-xs"),
                    rx.text(f"Ataques por miniatura: {attrs.get('attacks_per_model', '-')}", class_name="text-xs"),
                    rx.text(f"Ataques totales: {attrs.get('total_attacks', '-')}", class_name="text-xs"),
                    rx.text(f"Arma principal: {attrs.get('arma_nombre', '-')}", class_name="text-xs"),
                    rx.text(f"Rend: {attrs.get('arma_rend', '-')}", class_name="text-xs"),
                    rx.text(f"Daño: {attrs.get('arma_damage', '-')}", class_name="text-xs"),
                    class_name="mt-2 p-2 rounded bg-zinc-800"
                )
            )
        , class_name=vstack_class),
        class_name=box_class,
    )

def index() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text("Simulador de Combate", class_name="text-3xl font-bold text-center"),
            rx.text("Warhammer Age of Sigmar", class_name="text-sm opacity-70 text-center"),
            rx.grid(
                side_card("Atacante", True),
                side_card("Defensor", False),
                class_name="w-full grid grid-cols-1 lg:grid-cols-2 gap-6",
            ),
            class_name="w-full mx-auto py-8 space-y-8",
        ),
        class_name="w-full px-4 md:px-12",  # <-- padding lateral aquí
    )

app = rx.App()
app.add_page(index, on_load=SimState.on_load, title="Simulador AoS")