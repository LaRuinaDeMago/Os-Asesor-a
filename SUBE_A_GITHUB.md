# SUBE_A_GITHUB.md

Lista explícita de qué sube a GitHub y por qué. Cada entrada indica cómo se
verificó — no es una aprobación en bloque. Ver `NUNCA_SUBE.md` para todo lo
excluido y el motivo.

Verificación aplicada a todo lo de aquí abajo (2026-07-30): grep de solo-conteo
sobre la lista de apellidos reales de clientes/proveedores ya identificados
durante esta sesión (los citados en FLUJO_CONTINUO_PLAN_DEFINITIVO.md más los
que fueron apareciendo durante la auditoría — no se repite la lista aquí para
no tener ni siquiera esos apellidos en un archivo candidato a subir a GitHub) +
patrón de NIF/DNI (8 dígitos+letra). Cero coincidencias en todo lo listado
aquí, confirmado, no asumido.

## Código (ya limpio, existía suelto en la carpeta)

- `nif_check.py` — sin coincidencias en ninguna búsqueda.
- `audit_project.py` — sin coincidencias.
- `captura_orquestador.py` — sin coincidencias.
- `config.example.json` — plantilla de ejemplo, sin coincidencias.
- `requirements.txt` — sin coincidencias. (`requirements (1).txt` es un
  duplicado exacto — mismo hash MD5 — no subir los dos, basta con este.)
- `PGC_CUADRO_CUENTAS.json` — sin coincidencias (cuadro de cuentas oficial PGC/BOE).

## Código editado y verificado en esta sesión (contenía fuga real, ya corregida)

Los 4 archivos siguientes citaban nombre real de cliente/proveedor en
comentarios, docstrings o (en un caso) directamente en una cadena de test. Se
sustituyó por "cliente piloto"/"caso real anonimizado", manteniendo intacta
toda la lógica y los números. Verificado con test_motor_veredicto.py (100% en
verde) y con una segunda pasada de grep tras la edición (0 coincidencias).

- `motor_veredicto.py`
- `layout_diario_contaplus.py` (verificado solo por compilación, no tiene test
  propio en test_motor_veredicto.py — considerar añadir uno)
- `orquestador.py` (igual: verificado por compilación, sin test propio)
- `test_motor_veredicto.py` — además de genericar nombres, el DNI/NIF de
  ejemplo se sustituyó por uno inventado con dígito de control matemáticamente
  válido (`12345678Z` para DNI, `B12345674` para CIF), nunca el real.

## Código y specs nuevos, extraídos de OS_ASESORIA_v3_38.zip

Auditados uno a uno — el zip en sí NUNCA sube (ver `NUNCA_SUBE.md`), pero estos
archivos concretos son limpios y útiles, así que se copiaron sueltos a la
carpeta del proyecto como entradas individuales (nunca "todo el zip aprobado"):

- `guard_g7_ledger.py` — genérico, sin nombre/NIF real. La única cifra real que
  cita (una discrepancia de reconciliación en el docstring) no identifica a
  nadie.
- `triangulacion_identidad_v0.py` — editado: se genericó la única mención de un
  alias de caso real en un comentario. Verificado por compilación.
- `MATRIZ_COBERTURA_v1.md` — spec técnica genérica, sin coincidencias.
- `CATALOGO_EVENTOS_v1.md` — spec técnica genérica, sin coincidencias.
- `criterios_fiscales.json` — tabla de criterios fiscales firmados (fuentes
  AEAT/DGT). Cita el nombre de pila de Diego como revisor/firmante — es el
  propio autor del despacho publicando bajo su identidad, no un dato de
  cliente, así que no se trata como fuga.

## Leídos completos el 30-07-2026 (ya no queda nada en "verificación parcial")

Los 7 archivos que habían quedado pendientes de una lectura completa se leyeron
enteros esta misma sesión, con la misma disciplina que el resto — sin citar
contenido real en el chat, solo la clasificación y el motivo:

- `criterios_fiscales_v1_0_historico.json` — limpio: criterios fiscales
  genéricos versionados (predecesor de la v1.1 ya aprobada), sin caso real.
- `DIA3_ESTADO_PARCIAL.md` — limpio: solo referencia el caso propio de Diego
  por su código interno (EXP-0001), sin cifras que lo identifiquen.
- `DIA3_SPEC_C1_TACTICAS.md` — limpio: igual, menciona el caso propio por
  código interno, sin datos identificables.
- `TRIAJE_RONDA_2026-07-13.md` — limpio: cita competidores del sector por
  nombre público (análisis de mercado), no clientes ni proveedores del
  despacho.

`suite_regresion.json` y `GUIA_OPERATIVA.md` resultaron tener fuga real tras
la lectura completa — se han movido a `NUNCA_SUBE.md`, no se suben.
`PLAN_OPERATIVO_v1_2_FINAL.md` y `SSOT_ASESORIA_v1_2.md` eran limpios de
privacidad, pero Diego ha decidido no publicarlos por confidencialidad de
estrategia de negocio — también en `NUNCA_SUBE.md`.

## Documentación del proceso (nueva, escrita en esta sesión)

- `CLAUDE.md`
- `.claude/rules/datos.md`
- `.claude/rules/contabilidad.md`
- `.claude/rules/testing.md`
- `.claude/rules/seguridad.md`
- `PROJECT_STATUS.md` (versión nueva — la anterior contenía fuga real, ver
  `NUNCA_SUBE.md`)
- `SUBE_A_GITHUB.md` (este archivo)
- `NUNCA_SUBE.md`

## Barrera técnica de privacidad (Fase 2.5, nueva)

Genérica por diseño — no contiene ningún apellido real, solo regex (NIF/CIF,
IBAN, teléfono) y nombres de ARCHIVO ya conocidos (no de personas). Probada
en esta sesión: commit real con un archivo prohibido → bloqueado; commit real
con un archivo limpio → pasa.

- `scripts/privacy_scan.py`
- `scripts/pre-commit`
- `scripts/install_hooks.sh` (hay que ejecutarlo tras cada `git clone` nuevo —
  git no versiona `.git/hooks/` automáticamente)
- `.github/workflows/privacidad.yml`
- `NUNCA_SUBE_FILENAMES.txt` (solo nombres de archivo, no datos personales)
- `.gitignore`
- `scripts/guardar_avance.sh` (31-07-2026): automatiza la parte de "preparar"
  el guardado (escanea, `git add` de lo que corresponde, crea el commit) para
  no repetir el mismo comando a mano cada vez. Deliberadamente NO hace
  `git push` — eso sigue siendo siempre una decisión y una acción manual
  aparte, aprobada explícitamente por Diego cada vez. Probado dos veces:
  con un archivo limpio (completa el commit) y con un dato sospechoso de
  ejemplo (para sin commitear nada).

## Criterio de verificación en limpio (Fase 1, sección 2.3 del plan)

Después de subir, clonar en una carpeta aparte y repetir el mismo grep de
conteo usado aquí sobre el clon. Si aparece algo, el repositorio está
contaminado — no basta con borrar el archivo (queda en el historial de
commits), hay que reescribir el historial o empezar un repositorio nuevo.
