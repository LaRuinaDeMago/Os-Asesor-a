# NUNCA_SUBE.md

> **Documento VIGENTE, con una salvedad de fecha.** Las reglas de aquí siguen
> mandando; el inventario concreto de ficheros es del **30-07-2026** y algunos
> de los que cita ya no existen ni siquiera en local. La barrera real no es esta
> lista sino `scripts/privacy_scan.py`, que decide **por el contenido** de cada
> fichero y no por su nombre — ver `.claude/rules/datos.md`, apartado *"La
> barrera mira el CONTENIDO, no la extensión"*. Esta lista documenta el porqué;
> el escáner es quien bloquea.

Lista explícita de qué NO sube a GitHub y por qué. Ningún NIF ni nombre real se
cita en este documento — solo se describe que existe y el motivo, tal como pide
la regla de la sección 1.5 de FLUJO_CONTINUO_PLAN_DEFINITIVO.md.

## Los dos .zip — regla fija, sin excepción

- `MOTOR_PAQUETE_CLAUDE_CODE.zip`
- `OS_ASESORIA_v3_38.zip`

Motivo: regla fija de la sección 1.4 del plan — un `.zip` nunca sube, se haya
auditado su interior o no. Ya se extrajeron a una carpeta temporal local
(scratchpad de esta sesión, fuera de este proyecto), se auditó cada archivo de
dentro individualmente, y lo que resultó limpio se copió suelto al proyecto (ver
`SUBE_A_GITHUB.md`). El zip como archivo no se toca.

## Archivos con NIF, nombre de cliente o proveedor real confirmado

Cada uno se revisó línea a línea (con tu aprobación explícita para mostrar el
contenido durante la auditoría) y contiene, en al menos un punto, el nombre real
de un cliente o proveedor del despacho, o un NIF real:

- `vero_maestro_proveedores_REAL.json` — NIF/nombres reales de proveedores de un
  cliente, ya lo indica el propio nombre del archivo.
- `vero_mapeo_cuenta_gasto.json` — mapeo ligado al mismo cliente que el anterior.
- `romo_TANDA2_CORREGIDO.csv` — facturas reales de un cliente.
- `vero_FINAL_COMPLETO.csv` — facturas reales de otro cliente.
- `DIRECTORIO_NACIONAL_PROVEEDORES.json` — es, en su mayoría, un directorio
  nacional legítimo de miles de proveedores (los apellidos comunes que aparecen
  están dispersos entre cientos de entradas sin relación, no concentrados).
  **Pero** contiene también, como una entrada más entre esas miles, la ficha
  real (con NIF real como clave) del proveedor concreto de un cliente del
  despacho — confirmado porque el mismo nombre completo aparece también en el
  código ya identificado como fuga real. Por esa única entrada, todo el archivo
  se trata como NUNCA_SUBE hasta que se pueda filtrar esa ficha concreta.
- `ENCARGO_CLAUDE_CODE.md` — narra el trabajo citando nombres de cliente reales
  como referencia ("probado con...").
- `INVENTARIO.md` — igual, cita clientes reales y hashes de lotes de facturas
  reales.
- `PENDIENTE_DE_FABRICACION.md` — cita un caso real por nombre.
- `SEMAFORO_DEFINITIVO_v1_ADENDA.md` — cita casos reales por nombre (el plan
  original lo daba por aprobado para subir; la auditoría de esta sesión
  corrigió esa aprobación).
- `IVA_TIPOS_2026.json` — una línea del campo "fuente" cita un proveedor real
  como ejemplo de dónde se confirmó el tipo de IVA.
- `README (1).md` — una línea describe un archivo como perteneciente a un
  cliente real, nombrándolo.
- `OS_ASESORIA_DOCUMENTO_MAESTRO_CONSOLIDADO.md` — documento histórico completo
  del trabajo real del despacho, satura de nombres de cliente reales (más de
  cien coincidencias).

La versión ANTERIOR de `PROJECT_STATUS.md` también citaba clientes reales por
nombre — se ha sustituido por una versión nueva y genérica (ver
`SUBE_A_GITHUB.md`); el contenido viejo no se sube en ningún commit.

## Archivos con dato financiero real de Diego (no de un cliente, pero real e identificable)

Confirmado por lectura completa el 30-07-2026:

- `suite_regresion.json` — junto a 5 casos sintéticos limpios, contiene un
  sexto caso con las cifras y fechas exactas de la operativa personal de
  Diego en un exchange de criptomonedas (el mismo dato que ya aparecía en
  `adaptador_bitget_v1.py`).
- `GUIA_OPERATIVA.md` (el que preguntaste por su origen — resultó ser una
  copia idéntica, mismo hash MD5, de la que trae el zip; no es un archivo de
  origen desconocido, pero sí tenía fuga) — repite dos veces la cifra y la
  cadena de operaciones reales del mismo caso personal de Diego.

## Excluidos por confidencialidad de estrategia de negocio (decisión de Diego, no fallo de auditoría)

Estos dos se leyeron completos y no contienen ningún dato de privacidad de
terceros — la auditoría los daba por aprobados para subir. Diego ha decidido
no publicarlos porque exponen la estrategia comercial interna del despacho
(objetivos, métricas, plan de captación), no porque haya un problema de NIF
o nombres reales:

- `PLAN_OPERATIVO_v1_2_FINAL.md`
- `SSOT_ASESORIA_v1_2.md`

## Todo lo extraído de OS_ASESORIA_v3_38.zip que es trabajo real del despacho

En vez de listar archivo por archivo (son varias decenas), se agrupa por
carpeta porque el motivo es el mismo en todos: son las carpetas de trabajo real
del despacho con clientes reales, casos reales, o el propio caso financiero
personal de Diego.

- **`02_EXPEDIENTES/EXP-0001_DIEGO_BITGET/` (carpeta completa)** — expediente
  fiscal real de una operativa de criptomonedas, con extractos bancarios reales
  en PDF, exports reales de un exchange (CSV), y los JSON/markdown derivados de
  ese caso. Es el propio caso personal de Diego, no de un cliente — pero sigue
  siendo un registro financiero real identificable, y la regla de este proyecto
  es que Cloud/GitHub solo lleva código y datos sintéticos, sin excepción por
  ser datos propios del despacho en vez de un cliente.
- **`03_EVIDENCIA/registro_expedientes.json`** — índice que referencia el
  expediente anterior.
- **`04_CLIENTE/` (carpeta completa)** — CSV de facturas reales de clientes con
  semáforo ya calculado.
- **`05_CONTRASTE/` — archivos con nombre de cliente en el propio nombre de
  archivo** (los que empiezan por el alias de un cliente concreto) — cachés de
  formato/importes históricos de proveedores reales de ese cliente.
- **`05_CONTRASTE/motor_contraste_semillas_v0.py`** — cita un cliente real por
  nombre varias veces y además contiene sus cifras contables exactas (balances)
  junto al nombre — la fuga más grave de código encontrada en toda la auditoría.
- **`01_MOTOR/adaptadores/adaptador_bitget_v1.py`** — código en general limpio,
  pero con una constante hardcodeada: un importe exacto y el nombre de una
  entidad bancaria concreta, ligados a una fecha concreta (dato financiero
  propio de Diego, no de un cliente, pero real e identificable igualmente).
- **`01_MOTOR/ANATOMIA_FUENTES_BITGET_v1.md`**,
  **`01_MOTOR/motor_fifo_dia1_v03_CERRADO.ipynb`** — no se leyeron línea a línea
  (el notebook en particular puede llevar salidas de celda con datos reales sin
  que se note al ojear el archivo); por estar directamente ligados al caso real
  de Bitget, se excluyen por defecto hasta revisión manual, en vez de darlos por
  buenos sin comprobar.
- **`00_GOBIERNO/APARCAMIENTO.md`**, **`SPEC_SENTIDO_COMPRA_VENTA_v1.md`**,
  **`SSOT_ASESORIA_v1_3.md`**, **`SEMAFORO_DEFINITIVO_v1.md`**,
  **`ESTRUCTURA_BASE_DATOS_2016_2026.md`**, **`IDEAS_FUTURAS.md`** — documentos
  de trabajo que usan casos reales de clientes como ejemplo ilustrativo a lo
  largo del texto (confirmado por grep de conteo, con más o menos densidad
  según el archivo — `APARCAMIENTO.md` es el más afectado, con decenas de
  menciones).
- **`README.md` e `INVENTARIO.md`** (los del nivel superior de `OS_ASESORIA/`
  dentro del zip) — mismo contenido con fuga real que sus equivalentes ya
  listados arriba.

## Cualquier .DAT o .dbf de ContaPlus real

No apareció ninguno suelto en esta carpeta ni dentro de los zips auditados, pero
la regla queda declarada por si aparece en el futuro: cualquier `.DAT`/`.dbf`
real de ContaPlus es NUNCA_SUBE automático, sin necesidad de auditarlo primero.

## Criterio de verificación

Todo lo de esta lista se confirmó mostrando el contenido real en el chat (con tu
aprobación explícita, sesión del 30-07-2026) o, en el caso de las carpetas
agrupadas, por la naturaleza evidente del contenido (expediente financiero real,
facturas reales) sin necesidad de mostrar el dato exacto para saber que es real.
