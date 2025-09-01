# Optimización del Simulador de Combate Age of Sigmar

## Cambios realizados

### 1. Corrección de errores de cálculo
- **Bug de multiplicación de ataques**: Se corrigió el bug principal donde los ataques totales se estaban multiplicando incorrectamente. Ahora 20 saurios tienen 40 ataques en lugar de 80.
- **Ajuste en combate_media_multiarmas**: Se modificó para calcular correctamente el total de ataques como `ataques_por_miniatura * número_de_miniaturas`.
- **Corrección de críticos**: Se ajustó el cálculo de ataques críticos para que estén basados en el número correcto de ataques.

### 2. Mejoras en la organización del código
- **Funciones bien definidas**: Se refactorizó el código suelto en funciones específicas con responsabilidades claras.
- **Eliminación de código duplicado**: Se eliminó código repetido y se movió a funciones reutilizables.
- **Separación de responsabilidades**: Ahora cada función tiene una responsabilidad única:
  - `mostrar_analisis_inicial`: Muestra análisis inicial del combate
  - `simular_combate_completo`: Simula el combate hasta que una unidad sea eliminada
  - `mostrar_detalle_armas_en_combate`: Muestra información detallada sobre las armas

### 3. Mejoras en la visualización
- **Detalles de críticos**: Se mejoró la visualización de críticos y sus efectos (heridas mortales o heridas automáticas).
- **Información detallada por arma**: Ahora se muestra información más completa de cada arma durante el combate.
- **Desglose de daño**: Se separó claramente el daño normal y el daño mortal para mejor comprensión.

### 4. Mejoras en la tipografía y documentación
- **Docstrings completos**: Se añadieron descripciones detalladas para todas las funciones.
- **Tipos de datos**: Se especificaron los tipos para los argumentos y valores de retorno.
- **Comentarios explicativos**: Se añadieron comentarios para explicar partes complejas del código.

### 5. Manejo de errores
- **Try/except**: Se añadieron bloques try/except para manejar posibles errores.
- **Valores por defecto**: Se utilizan valores por defecto en caso de errores para que la simulación continúe.

## Beneficios de la optimización

1. **Precisión mejorada**: Los cálculos de ataques y heridas son ahora correctos y precisos.
2. **Facilidad de mantenimiento**: El código está mejor organizado y es más fácil de mantener.
3. **Extensibilidad**: Es más sencillo añadir nuevas funcionalidades y características.
4. **Depuración más sencilla**: Con mejor estructura y manejo de errores, la depuración es más fácil.

## Ejecución del simulador

Para ejecutar el simulador, utiliza el siguiente comando:

```python
python simulador.py
```

O para simulaciones específicas:

```python
from simulador import mostrar_analisis_inicial
mostrar_analisis_inicial('id_atacante', 'id_defensor', carga=True)
```

## Nota importante

Esta optimización ha corregido el problema principal donde los ataques totales se estaban multiplicando incorrectamente. Ahora los cálculos de ataques son precisos y dan resultados correctos.
