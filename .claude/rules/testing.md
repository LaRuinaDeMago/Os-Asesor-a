# Criterio de "hecho"

Un cambio al motor no está terminado hasta que:
1. test_motor_veredicto.py pasa 100%.
2. audit_project.py no reporta huérfanos de cableado (guards calculados pero
   nunca consultados en el veredicto).
   **Leer el código de salida, no solo la última línea** (desde el 09-09-2026
   hay tres, porque son tres cosas distintas):
   - `0` — todo comprobado y en verde.
   - `1` — **hay un defecto real.** Eso manda sobre todo lo demás.
   - `2` — nada falla, pero algo no se ha podido comprobar (típicamente una
     dependencia sin instalar). **Un ⚠️ NO es un aprobado**: es la misma regla
     que el motor — si no se ha podido comprobar, no es OK. Se lee qué es y se
     decide, no se da por bueno.
3. Se ha probado con al menos 1 caso real conocido (de los ya validados), no
   solo con casos sintéticos, salvo que se declare explícitamente como sintético.
   Los casos reales usados en tests van SIEMPRE anonimizados (ver
   .claude/rules/datos.md) — el dato numérico y la lógica quedan intactos, solo
   se sustituye el nombre/NIF real por un placeholder ("caso piloto", NIF
   inventado con checksum válido).

## Entorno de ejecución

Este proyecto no fija una versión de Python en un venv/requirements bloqueado.
Antes de dar por bueno un cambio, confirmar que test_motor_veredicto.py corre
con: `python3 -m pytest test_motor_veredicto.py -v` o, si no hay pytest
instalado, simplemente `python3 test_motor_veredicto.py` (el propio script
corre sin pytest y termina con código de salida 1 si algo falla).
