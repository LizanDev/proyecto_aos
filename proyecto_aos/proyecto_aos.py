"""Welcome to Reflex! This file outlines the steps to create a basic app."""
import reflex as rx
from typing import List,Dict,Tuple
from .data import get_factions, get_units_by_faction


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
    bonus1: str = "rend"
    bonus2: str = "rend"

    result_text: str = ""
    result_lines: list[str] = []

    
    def on_load(self):
        from .data import get_factions
        rows = get_factions()  # [(id, name)]
        self.factions_names = [n for (_id, n) in rows]
        self.factions_map   = {n: _id for (_id, n) in rows}

   
    def set_faction1_name(self, name: str):
        from .data import get_units_by_faction
        self.faction1_name = name
        fid = self.factions_map.get(name, "")
        rows = get_units_by_faction(fid)
        self.units1_names = [n for (_id, n) in rows]
        self.units1_map   = {n: _id for (_id, n) in rows}
        self.unit1_name   = self.units1_names[0] if self.units1_names else ""

    def set_faction2_name(self, name: str):
        from .data import get_units_by_faction
        self.faction2_name = name
        fid = self.factions_map.get(name, "")
        rows = get_units_by_faction(fid)
        self.units2_names = [n for (_id, n) in rows]
        self.units2_map   = {n: _id for (_id, n) in rows}
        self.unit2_name   = self.units2_names[0] if self.units2_names else ""

    def set_unit1_name(self, name: str): self.unit1_name = name
    def set_unit2_name(self, name: str): self.unit2_name = name
    def set_charge1(self, v: bool): self.charge1 = bool(v)
    def set_charge2(self, v: bool): self.charge2 = bool(v)
    def set_bonus1(self, v: str): self.bonus1 = v
    def set_bonus2(self, v: str): self.bonus2 = v


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

    return rx.box(
        rx.vstack(
            rx.text(title, class_name="text-sm font-semibold"),
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
            rx.checkbox("Ha cargado", is_checked=charge_val, on_change=set_charge),

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
            )
        ),
        class_name="flex-1 p-4 rounded-xl border border-zinc-800 bg-zinc-900",
        )
    

def set_charge1(self, v: bool):
    self.charge1 = bool(v)
    if not self.charge1:
        self.bonus1 = ""   # o "rend" si prefieres default

def set_charge2(self, v: bool):
    self.charge2 = bool(v)
    if not self.charge2:
        self.bonus2 = ""


def index() -> rx.Component:
    # Welcome Page (Index)
    return rx.box(
        rx.vstack(
            rx.text("Simulador de Combate", class_name="text-2xl font-bold text-center"),
            rx.text("Warhammer Age of Sigmar", class_name="text-sm opacity-70 text-center"),
            rx.hstack(
                side_card("Atacante", True),
                side_card("Defensor", False),
                class_name="w-full gap-6",
            ),
            rx.box("Resultado", class_name="w-full p4 rounded-xl border"),
            class_name="max-w-6xl mx-auto gap-6 p-6",
        ),
        class_name="min-h-screen bg-zinc-950 text-zinc-100",
    )

app = rx.App()
app.add_page(index, on_load=SimState.on_load, title="Simulador AoS")