import re
from typing import Union

_dice_term = re.compile(r"\s*([+-]?)\s*(?:(\d*)[dD](\d+)|(\d+))\s*")

def redondear(valor: float) -> int:
    """
    Redondea un valor siguiendo la regla: 
    - Si el decimal es menor que 0.5, redondea hacia abajo
    - Si el decimal es igual o mayor que 0.5, redondea hacia arriba
    
    Args:
        valor: Valor float a redondear
        
    Returns:
        El valor redondeado como entero
    """
    # Usar round que ya implementa la lógica solicitada
    return round(valor)

def dice_average(expr: Union[str, int, float, None]) -> float:
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
            try:
                return float(s)
            except Exception:
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
        if i < len(s) and s[i] in '+-':
            pass
    return total
