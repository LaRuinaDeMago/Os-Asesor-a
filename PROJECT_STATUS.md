# PROJECT_STATUS — estado operativo, no documentación

> **Para ARRANCAR una sesión, lee `EMPEZAR_AQUI.md`.** Este fichero es la
> referencia detallada: sirve para consultar, no para empezar.

Este archivo se actualiza cada vez que algo cambia de verdad. Si algo aquí no
coincide con lo que demuestran los tests o el código, mandan los tests, no este
texto. Jerarquía de verdad: Código → Tests → Git → este archivo.

## 15-09-2026 (sesión local, undécima entrada) — Repaso de limpieza: la raíz baja de 105 a 87 `.py`, y una instrucción ya cumplida deja de ser lo primero que lee cada sesión

Repaso pedido explícitamente antes de abrir trabajo nuevo: *"repasemos todo lo
que tenemos de manera minuciosa para dejarlo lo más limpio posible"*. Protocolo
completo primero — `arranque.py`, auditor (**41 checks, código 2**, el mismo ⚠️
de siempre por `anthropic`/`google-genai` sin instalar, bloqueadas por DPA) y
`test_motor_veredicto.py` (**100% en verde**). Nada roto de partida.

**Cuatro cosas encontradas, todas medidas antes de tocarlas:**

**1 · La cabecera de `PENDIENTE.md` mandaba hacer algo ya hecho.** Decía *"ANTES
DE NADA, UNA SOLA VEZ: `git checkout master && git pull`"*, y `arranque.py` la
imprime al empezar **cualquier** sesión: era literalmente lo primero que se leía.
Comprobado en vez de suponerlo: única rama local `master`; `master` y
`origin/master` a 0 commits de diferencia **en los dos sentidos**; y la rama
`claude/github-retomada-o4zyic` lleva **0 commits que master no tenga** (el diff
va en el otro sentido — está estrictamente atrasada). Sustituida por el estado
real, conservando la regla permanente (no compartir ramas largas entre PC y nube).

**2 · 18 scripts que no miraba nadie, movidos a `archivo/`.** Medido con las tres
condiciones a la vez, no a ojo: ningún `.py` los importa, ninguna documentación
los nombra (buscado con `.py` y sin él, en todos los `.md` y en `.claude/`), y
los 18 tienen `__main__` — scripts sueltos, no módulos de los que dependa nada.
La raíz pasa de **105 a 87 `.py`**. No se ha borrado ninguno: son las sondas que
produjeron `FASE0_RESULTADOS.md` y borrarlas dejaría esas cifras sin nada detrás.
`archivo/README.md` avisa de lo que importa de verdad — **varias de sus premisas
fueron corregidas después** (los cuatro errores documentados en
`ARQUITECTURA_DATOS.md` §4 son justo de esa época), así que valen para entender
**por qué** se decidió lo que se decidió, nunca como fuente del estado actual.

> El primer recuento dio 24 huérfanos y era **falso**: buscaba `fase0_reagrupa.py`
> con la extensión, y la documentación lo cita como `fase0_reagrupa`. Repetido
> buscando las dos formas, bajó a 19. Sin esa segunda pasada se habrían archivado
> 5 scripts que la documentación sí nombra, dejando referencias rotas.

**3 · Un script de la raíz no está en el repositorio, y nada lo delata.**
`diag_formato_303_local.py` lo excluye `.gitignore` por la regla `*_local.*`:
vive sólo en el PC de la asesoría y nunca ha subido a GitHub. Por eso se quedó
fuera del movimiento (está fuera del contrato del repositorio), pero queda
anotado en `archivo/README.md`: mirando `ls *.py` nada permite distinguirlo.
Salió por casualidad — su fecha de último commit venía vacía en el recuento.

**4 · `FASE0_RESULTADOS.md` decía "los seis scripts `fase0_*.py`".** Acabaron
siendo 20. Corregido con el reparto real (9 en la raíz, 11 en `archivo/`) y un
puntero al README, para que el documento sepa dónde vive lo que lo produjo.

Auditor y motor ejecutados **otra vez después** de mover: resultado idéntico
(41 verdes, código 2; 100% en verde). `scripts/privacy_scan.py` sin hallazgos.

## 15-09-2026 (sesión local, décima entrada) — Estructura de `\\PC01\Documentos`: organizada por cliente, pero solo el 24% de los PDF se identifica por el nombre solo

Continuación de la sesión (novena/octava entrada, mismo día). Dos revisiones
externas del proyecto coincidieron en una pregunta abierta: ¿está PC1
organizada por cliente (emparejar modelo↔cliente↔periodo sería casi
mecánico, como ya funciona el manifest del 303) o es un volcado plano con
nombres inconsistentes (un proyecto entero, del tamaño del 303 multiplicado
por cada modelo)? Nadie lo había medido, solo se había trabajado dentro de
PC1 con éxito para clientes concretos del 303.

**Construido `explorar_estructura_pc1.py`**: más seguro todavía que
`reconocer_303_pdf.py` (Fase 1 del 303) — no abre ni un solo fichero, solo
cuenta nombres de carpeta (nunca impresos), profundidad, extensión, y
patrones de nombre. Cuatro rondas de arreglos reales, cada uno encontrado
por Diego revisando el número con sentido crítico en vez de aceptarlo:

1. **Primera pasada: 9,2% con modelo reconocido — sospechosamente bajo.**
   Diego señaló que a simple vista la mayoría de los PDF sí llevan modelo y
   periodo. Investigado sin pedir ningún nombre real: el patrón exigía el
   número "aislado" (no pegado a otro dígito), y fallaba con nombres sin
   separador ("3032024.pdf").
2. **Patrón "suelto" (sin exigir aislamiento): subió a 36,7% — inflado.**
   El modelo 202 (Sociedades) son también los tres primeros dígitos de
   cualquier año 2020-2029. Arreglado excluyendo coincidencias dentro de un
   año ya reconocido.
3. **Con el año excluido, "202" seguía con +5.035 de diferencia.** Y "131"
   subía de 11 a 666 (×60) sin ninguna fecha de por medio. Causa real: de
   39.375 ficheros, 13.526 son `.jpg` — fotos numeradas secuencialmente por
   cámara/escáner ("IMG_1202.jpg"), donde cualquier secuencia de 3 dígitos
   común aparece por casualidad. Arreglado restringiendo la medición a
   `.pdf`, que es donde de verdad vive un modelo oficial.
4. **Añadida también una señal cruzada de Diego**: ~5.305 PDF contienen la
   palabra "modelo" (comprobado por él con una búsqueda de Windows, ningún
   nombre pasó por el chat) — con el matiz correcto de que eso no significa
   que todos sean modelos presentados ("modelo de contrato" también la
   lleva). Cruzada con el número: 3.432 llevan "modelo" + un número a la
   vez (casi seguro un impreso AEAT real), solo 63 llevan "modelo" sin
   ningún número (la ambigüedad real).

**Resultado final, con dos métodos independientes convergiendo a menos de
un 1% de diferencia (fuerte confirmación cruzada):**

```
PDF totales: 14.395
con ALGUN modelo conocido (solo PDF)  : 3.459  (24,0%)
'modelo' + numero a la vez (solo PDF) : 3.422  (23,8%)
```

Desglose por modelo (solo PDF): 303=1.154, 130=535, 111=482, 390=256,
347=199, 202=187, 115=184, 036=178, 349=127, 190=116, 180=48, resto <15.

**Otros hallazgos de la misma exploración:**
- **140 carpetas de primer nivel** (139 + una que resulta ser un ZIP,
  según confirmó Diego), de las cuales ~80-100 tienen nombre propio/cliente
  — coherente con lo ya sabido (`FASE0_RESULTADOS.md §11.4`): no todas las
  carpetas son clientes, algunas son memorias, contabilidad al Registro
  Mercantil, gestiones puntuales.
- **88,6% de las carpetas son planas o de un solo nivel**, y el 70% tiene
  entre 11 y 200 ficheros — confirma estructuralmente "carpeta por
  cliente/entidad, todo dentro", el mismo patrón que ya usa el manifest
  del 303.
- **207 ficheros con extensión de certificado digital** (.pfx/.p12/.cer/
  .crt/.key/.pem) — hallazgo de una revisión externa, incorporado: NO son
  documentación, son credenciales de acceso a la Sede Electrónica en
  nombre de un cliente. Marcados aparte para que ningún tratamiento futuro
  los confunda con un PDF por descuido de extensión.
- **2.198 ficheros `.dat`** dentro de PC1 — misma extensión que los
  contenedores ZIP de ContaPlus. Sin confirmar si son lo mismo.
- **2.360 ficheros `.tgd`** — formato sin identificar. Segunda extensión
  más común tras PDF y JPG. Pendiente de que Diego confirme qué programa
  lo genera.

**Lectura para la pregunta de fondo ("¿extrapolar el 303 a otros
modelos?"):** ni tan mecánico como el 24% sugiere de entrada, ni un
proyecto nuevo entero. La estructura por cliente está confirmada. Hay una
base real de ~3.400 PDF ya identificables sin abrir nada, con volúmenes
por modelo que tienen sentido (130 y 111 muy por delante de 390, pese a
que 390 se había propuesto antes como "casi gratis" por pura cercanía
conceptual al 303 ya resuelto). Pero el 76% restante de los PDF no se
identifica por nombre solo — peor que el 12% ya medido para el 303 en
solitario —, así que conseguir cobertura completa por cliente necesitará
el mismo trabajo paciente de afinar patrones que ya hizo falta para el
303, no una extensión automática.

`audit_project.py` código 2 (mismo aviso esperado) tras cada una de las
cuatro rondas de arreglos. Escáner de privacidad sin hallazgos en las
cinco. Ningún nombre de carpeta, cliente o ruta pasó por esta conversación
en ningún momento — solo recuentos, tal como exige `.claude/rules/datos.md`.

## 15-09-2026 (sesión local, novena entrada) — Confirmado a escala completa: 1,2% -> 99,8% sobre 1.023 documentos reales

Continuación directa de la entrada anterior (octava, misma sesión). Con los
tres bugs de lectura ya cerrados y confirmados en 3 clientes / 9 trimestres,
tocaba la comprobación que `PENDIENTE.md` punto 1.B dejaba pendiente "sin
prisa": medir la tasa de consistencia sobre el archivo completo, no solo
sobre los casos ya elegidos a mano.

```bash
python extraer_303_pdf.py "\\PC01\Documentos"
```

Diego lo ejecutó (misma disciplina de siempre: comando sobre datos reales,
salida solo de recuentos). Resultado:

```
documentos 303 con nombre reconocido : 1.023   con extraccion minima : 989
tramos que SI cuadran : 938   tramos que NO cuadran : 2   sin datos : 158
>> tasa de consistencia: 99,8%
```

**El propio script tiene escrito desde su creación el umbral de decisión:
">95% = extracción fiable, toca la fase 2b (cruzar contra `303_LOCAL.json`)".**
99,8% lo supera con margen amplio — y esa fase 2b ya existe y ya está
probada: es exactamente lo que hace `verificar_303_pdf.py`. La cadena
completa (extraer → comparar) queda validada de punta a punta, no solo el
primer tramo.

Dos observaciones, ninguna que cambie el resultado:

- **1.023 documentos reconocidos, no los 1.168 citados históricamente**
  (`FASE0_RESULTADOS.md`, `PENDIENTE.md`). Diferencia de 145, anotada sin
  alarma — el archivo de `\\PC01\Documentos` cambia con el tiempo y no hay
  ningún indicio de que sea un problema de reconocimiento. Si en el futuro
  alguien ve "1.168" en un documento antiguo, esta es la cifra viva.
- **Los 2 tramos que no cuadran (0,2%) se dejan sin perseguir, a propósito.**
  Decisión tomada con el mismo criterio que `SIGUIENTES_PASOS.md §4` pide
  para todo lo demás: el umbral se fijó ANTES de ver el número (aquí, desde
  que se escribió el script) y se cumple con margen de sobra. Construir una
  herramienta nueva para investigar 2 casos sin ningún indicio de patrón
  sistemático sería precisión de más sin necesidad real detrás (`CLAUDE.md`).
  Punto donde retomar si algún día aparecen más casos parecidos.

Con esto, `PENDIENTE.md` punto 1.B queda cerrado. Siguiente paso real:
punto 1.C (ampliar el manifest con más clientes), ahora con la confianza de
que la capa de lectura está probada a escala, no solo en los casos ya
elegidos.

## 15-09-2026 (sesión local, octava entrada) — El primer caso real del cuadre 303 destapó tres bugs reales en la lectura, cerrados y confirmados en 3 clientes y 9 trimestres

Primera sesión local tras fusionar el trabajo de BOE/normativa. Siguiendo
`PENDIENTE.md` punto 1.A, Diego ejecutó `verificar_303_pdf.py --manifest
verificacion_303_LOCAL.txt` contra el manifest real (SP_C_13, 2025T2). El
primer resultado fue `NO_CUADRA` con una diferencia de miles de euros —
sospechosamente distinto de lo que la sesión del 14-09 había medido para ese
mismo caso (entonces solo faltaba explicar el ISP). Investigarlo, sin que
ningún dato real llegara nunca a esta conversación, destapó tres defectos
reales encadenados.

### 🔴 Incidente de privacidad, en esta misma sesión — documentado sin datos

Durante la investigación, Diego pegó en el chat dos capturas de pantalla: la
ficha `_LOCAL` de `cuadre_303_ficha.py` (con el código pseudónimo `SP_C_13`,
sin NIF ni razón social) y una página real del 303 presentado (cifras reales
de un cliente real). Más tarde, al ejecutar un script desde dentro de la
carpeta del cliente en vez de desde la carpeta del proyecto, el nombre real
de ese cliente apareció en texto plano en el *prompt* de PowerShell pegado al
chat — dos veces. Señalado en el momento, con la cita literal de
`.claude/rules/datos.md` (corrección 29-07-2026: "ejecución local ≠
conversación local", la transcripción viaja a servidores de Anthropic igual).
No se puede deshacer desde esta sesión. Ninguno de los dos hechos llegó a un
commit ni a un fichero del repositorio. Lección de proceso, ya aplicada el
resto de la sesión: los comandos que tocan un `_LOCAL` o una ruta real los
ejecuta Diego, y solo se comparte el bloque `RESUMEN` (o, para diagnósticos a
medida, salida puramente estructural — números y booleanos, nunca contenido).
Guardado como regla de memoria para sesiones futuras.

### Bug 1 — `extraer_casillas()` se quedaba con la PRIMERA aparición de una etiqueta, aunque no llevara ningún número detrás

Diagnosticado con `diag_orden_extraccion_pdf.py` (nuevo), que no imprime
nunca contenido del PDF — solo, por cada etiqueta de casilla, la distancia en
caracteres hasta el siguiente importe y hasta la siguiente etiqueta. Sobre el
PDF real de SP_C_13, la etiqueta "07" aparecía **tres veces** en el texto
extraído; la primera no llevaba ningún importe cerca (ruido: una fecha, la
propia fórmula impresa del total, que cita "+ 06 + 09 + 11 + 13..." con las
etiquetas sueltas). `extraer_casillas()` y `extraer_casillas_oficiales()`
usaban `patron.search(texto)` sin bucle: se quedaban con esa primera
aparición y nunca llegaban a la segunda, que sí tenía el valor real
(6.285,14 €). Arreglado con `localizar_valor_casilla()` (nueva, en
`extraer_303_pdf.py`), que prueba todas las apariciones en orden hasta
encontrar una con número detrás — reutilizada por los dos sitios, para que no
puedan volver a divergir. 5 comprobaciones nuevas en `ensayo_extraer_casillas.py`
(familia M), reproduciendo la forma exacta del bug con cifras inventadas.

### Bug 2 — `totales_contabilidad()` tenía su PROPIA suma, y nunca recibió el arreglo del "tipo 0" del 14-09

El commit `6b2acb2` ya había excluido el tipo `"0"` (el asiento de
liquidación/cierre trimestral de IVA, no una venta ni una compra) del TOTAL
en `cuadre_303_ficha.py`. `verificar_303_pdf.py` tiene su propia función
independiente para lo mismo, que nunca recibió ese arreglo — reproducía el
mismo síntoma ("TOTAL cancelado") con datos reales: la cuota devengada y la
deducible de SP_C_13 quedaban casi enteras canceladas por su propio tipo
`"0"`. Arreglado con el mismo criterio ya validado (91,3% ratio de
cancelación, 72% contrapartida administrativa), declarando lo excluido en el
resultado (`liquidacion_excluida`) en vez de descartarlo en silencio — misma
disciplina que ya tenía `cuadre_303_ficha.py`. 6 comprobaciones nuevas en
`ensayo_verificar_303_pdf.py` (4 sobre `totales_contabilidad()`, 2 sobre que
`liquidacion_excluida` viaja hasta `comparar_caso()`).

### Bug 3 — `explicar_por_isp()` solo comprobaba la CUOTA de ISP, no la BASE, y aplicaba el ajuste aunque un lado ya cuadrara

Con los dos bugs anteriores arreglados, el devengado de SP_C_13 pasó a
cuadrar exacto (0,00 €) — pero `explicar_por_isp()` le sumaba igual la cuota
de ISP (420 €) a los dos lados sin comprobar si hacía falta, informando "420 €
sin explicar" sobre un lado que ya era perfecto. Y quedaba sin explicar del
todo un `-2.000,00 €` en la base deducible, que coincidía al céntimo con la
BASE de ISP (casilla 12) — nunca comprobada, solo la cuota (casilla 13).
Arreglado: ahora comprueba también la base, y el ajuste de ISP solo se aplica
al lado que de verdad lo necesitaba (`_evaluar_ajuste_isp()`, nueva). 10
comprobaciones nuevas. Diego confirmó por su cuenta, sin que el código se lo
pidiera, que esos 2.000 € son de una formación facturada por un proveedor
extranjero sin IVA — exactamente el patrón de ISP que el script ya había
encontrado solo.

### Revisión de rigor, antes de empujar a origin (mismo día): `_evaluar_ajuste_isp()` podía EMPEORAR una diferencia real sin relación con la ISP

Diego pidió una revisión punto por punto de todo lo hecho antes del `push`.
Auditando `_evaluar_ajuste_isp()` con más calma se encontró un segundo hueco,
sin necesitar ningún dato nuevo: la guarda añadida en el Bug 3 ("no aplicar
el ajuste si la diferencia bruta ya cuadraba") no cubre el caso de una
diferencia bruta **fuera** de tolerancia pero **sin relación con la ISP** —
sumarle el importe de ISP puede alejarla del cero en vez de acercarla.
Reproducido con un ejemplo inventado (no hay ningún caso así en el corpus
visto hasta hoy): diferencia bruta de 50 € + ISP de 420 € daba antes "sigue
sin explicar: 470 €", cuando el problema real era de 50 €, no de 470. Ahora
el ajuste solo se aplica si además **reduce** la magnitud de la diferencia; si
no ayuda, se declara la diferencia bruta tal cual. Comprobado que el caso
real de SP_C_13 se comporta exactamente igual que antes (mismo resultado,
cifra por cifra) — este arreglo no cambia nada ya validado, solo cierra un
hueco para casos futuros. 4 comprobaciones nuevas.

**Total de comprobaciones nuevas en toda la sesión: 25** (5 en
`ensayo_extraer_casillas.py`, 20 en `ensayo_verificar_303_pdf.py`) — número
contado con `grep` sobre el código final, no escrito de memoria.

### Validado contra datos reales: 3 clientes, 9 trimestres

Con SP_C_10 y SP_C_11 añadidos al manifest (las dos rutas que Diego ya tenía
comprobadas a mano el 14-09), la pasada completa dio:

```
casos totales : 9   ·   cuadran exacto : 2   ·   cuadran con redondeo (≤1 €) : 6
NO cuadran : 1 (SP_C_13, explicado entero por ISP)   ·   lectura correcta : 9/9
```

**Sin regresión**: los dos clientes que ya cuadraban con el lector viejo
siguen cuadrando con el nuevo (y con más cobertura — 4 trimestres cada uno,
no solo el que se había probado antes).

### Sobre automatizar la identidad código↔carpeta (discutido, no tocado)

Diego preguntó varias veces si se podía automatizar del todo la asignación
`SP_C_NN` ↔ carpeta de `\\PC01\Documentos` (filtrando por nombre, por
`S.L.`, etc.). Reconfirmado contra el código actual: `emparejar_carpetas.py`
solo compara a nivel de COPIA completa, nunca de código individual, y el
motivo de fondo no cambió (`datempre.dbf` con 0 registros: el código no
lleva ningún nombre pegado en ningún fichero que un script pueda leer). Sigue
siendo el único paso manual, "una vez por cliente, para siempre" — lo que sí
se acuerda es tratar `verificacion_303_LOCAL.txt` como un fichero
**permanente, que solo crece**, para que este trabajo no se pierda entre
sesiones como pasó con SP_C_10/SP_C_11 esta vez.

### Estado tras la sesión

`audit_project.py`: código 2 (mismo ⚠️ esperado de siempre: `anthropic` /
`google-genai` sin instalar). **105 archivos · 30/30 suites · motor 65/65 ·
adversarial 112/112.** No se tocó `motor_veredicto.py`. Ficheros modificados:
`extraer_303_pdf.py`, `verificar_303_pdf.py`, `ensayo_extraer_casillas.py`,
`ensayo_verificar_303_pdf.py`; nuevo: `diag_orden_extraccion_pdf.py`.

## 15-09-2026 (sesión Cloud, séptima entrada) — Diego tenía razón: si puedo leer el impreso de la AEAT, puedo leer el BOE. Ocho citas verificadas y un vigilante automático

Diego señaló una inconsistencia real y tenía toda la razón: esta misma sesión se
había bajado el formulario del 303 y leído la fórmula **de los bytes del PDF** —
y salió exacta—, y acto seguido dejaba 16 citas legales como *"esto lo verificas
tú"*. Eso hacía el módulo inútil: *"¿para qué serviría este cerebro si tengo que
verificar los artículos uno a uno?"*.

La distinción que sí se sostiene es más fina de lo que se había explicado:

| | quién lo hace |
|---|---|
| *"¿el art. 91.Dos sigue listando el aceite de oliva al 4%?"* | **automatizable**: es texto contra texto |
| *"¿este gasto de este cliente es deducible?"* | **criterio**, y lo firma el asesor |

Lo anterior dejaba **lo primero** en manos de Diego. Corregido.

### La API de datos abiertos del BOE responde, y trae las fechas de vigencia

`https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/{norma}/texto/bloque/{art}`
devuelve el texto consolidado con **todas las versiones históricas**, cada una
con su `fecha_vigencia` y la norma que la modificó. Con eso se puede saber qué
redacción rige hoy, sin interpretar nada.

### Lo verificado, leído artículo por artículo

| artículo | qué dice | en vigor desde |
|---|---|---|
| **90.Uno** | tipo general **21%** | 2012-07-15 |
| **91.Uno** | tipo reducido **10%** | — |
| **91.Dos** | tipo superreducido **4%** | 2025-01-01 |
| **91.Cuatro** | tipo **0%** — entregas en concepto de donativo | — |
| **78** | Base imponible. Regla general | 2017-11-10 |
| **88** | Repercusión del impuesto | 2013-01-01 |
| **84** | Sujetos pasivos (y su Uno.2º, la ISP) | 2023-01-01 |
| **154** | Régimen especial del recargo de equivalencia | 2015-01-01 |

**8 de 16 citas pasan de PROPUESTA a VERIFICADA**, cada una con su url, su
bloque y la fecha de vigencia de la redacción leída. Las 8 que quedan son las de
fuera de la LIVA (Reglamento de facturación, retenciones de IRPF, composición
del NIF).

### Tres hallazgos reales sobre `TABLA_IVA_4`

1. **El aceite de oliva ya no es temporal.** El RD-ley 4/2024 lo incorporó al 4%
   de forma permanente desde el 1-1-2025 (*"g) Los aceites de oliva"*). **La
   alarma levantada esta misma mañana queda resuelta, y en el sentido bueno.**
2. **Pero la tabla dice "pan" y la ley dice "pan COMÚN".** Un pan especial
   tributa al 10% y esta tabla lo aprobaría al 4%. Lo mismo con
   fruta/verdura/hortaliza/…: la ley exige que tengan *"la condición de
   productos naturales de acuerdo con el Código Alimentario"*.
3. **Y falta media lista por el otro lado**: el art. 91.Dos incluye además
   libros, periódicos y revistas, medicamentos de uso humano, vehículos para
   personas con movilidad reducida y prótesis. Una factura de libros al 4%
   saldría marcada como tipo incorrecto.

**La tabla no se ha tocado**: cambiarla mueve el comportamiento del motor y es
una decisión contable. Queda medido, escrito y en `PENDIENTE.md`.

### Y el 5% de `TIPOS_LEGALES`, que no es lo que parecía

Cuatro de los cinco tipos quedan confirmados. **El 5% no aparece ni en el 90 ni
en el 91**: era un tipo temporal de los RD-ley de la crisis de precios. Pero
**probablemente haya que dejarlo igual**, y el motivo importa: esa tupla la usa
el **lector de PDF** para validar su propia lectura sobre un archivo de 2016 a
2026, y en parte de ese periodo el 5% sí estuvo vigente. Para ese uso, aceptarlo
es correcto. Sería incorrecto reutilizarla para validar una factura de hoy.
Anotado en el registro con esas palabras.

### 24º auditor: `boe_normativa.py` — la vigilancia automática, en su versión honesta

Un comando, `python boe_normativa.py --comprobar`, descarga los artículos
registrados y compara contra la huella guardada. Contesta **una sola pregunta, y
la contesta sola**: *¿ha cambiado este artículo desde el día que lo leímos?*

**Lo que no hace, ni hará, es decir qué significa el cambio.** Esa es la línea
exacta entre esto y un resumidor: aquello produce una **afirmación** nueva (y hoy
mismo se vio a uno inventarse las casillas 40-43); esto produce una
**comparación** entre dos textos oficiales. Una se puede equivocar, la otra no.

Detalles con su motivo:

- **La auditoría no toca la red.** Descargar la haría fallar sin salida a
  internet, tardar, y dejar de ser determinista. La red es explícita y va aparte.
- **Elige la redacción EN VIGOR**, no la última del fichero: el consolidado trae
  las históricas **y** las reformas con entrada en vigor **futura**.
- **Ignora la redacción derogada** que el BOE conserva como nota dentro de la
  versión vigente. Incluirla sería dar por vigente lo que ya no lo está.
- **La huella normaliza espacios**: si cambiara por un reformateo del BOE, el
  aviso se volvería ruido y se dejaría de mirar — el final del ❌ que se enseñó
  a ignorar.
- **Un fallo de red sale como NO COMPROBADO, nunca como "sin cambios"**, y se
  reporta sólo el *tipo* de excepción, nunca su mensaje.

`ensayo_boe_normativa.py`: 23 comprobaciones, **sin tocar la red**, contra XML
sintéticos que imitan la estructura real. Resaboteado en cuatro variantes —coger
la versión futura, incluir la derogada, hacer la huella sensible al reformateo,
contar un fallo de red como "sin cambios"—: **las cuatro caen.**

Y probado contra el BOE **de verdad**: `2 sin cambios, 0 cambiados`. Falseando
una huella guardada, avisa con la vigencia, la norma modificadora y la huella
real.

### Una comprobación del ensayo anterior que caducó, y estaba bien que caducara

`ensayo_autoridad_guards.py` afirmaba *"hoy no hay ninguna verificada"*. Era
cierto esa mañana y se rompió en cuanto se leyeron los textos — que es
exactamente lo que tenía que pasar. Sustituida por el **invariante**, que no
caduca nunca: marcar algo VERIFICADO obliga a declarar **url, fecha, bloque y
vigencia**. Sin las cuatro cosas no se puede auto-aprobar.

### El motor, otra vez intacto

md5 de `motor_veredicto.py` idéntico a la línea base (`661612a2…`). Tests
**65/65** y adversarial **112/112**.

### Estado tras la sesión

`audit_project.py`: **41 ✅ · 1 ⚠️ · 0 ❌**. **30/30 suites**, privacidad sin
hallazgos. **No se tocó `motor_veredicto.py`** ni se añadió ningún guard. Todo
lo consultado es legislación pública: ningún dato de cliente.

## 15-09-2026 (sesión Cloud, sexta entrada) — `autoridad_guards.py`: qué norma hay detrás de cada guard, y cuáles no tienen ninguna

Segundo ladrillo del módulo de normativa, y el que de verdad lo conecta con el
motor. La dirección es la inversa de la que parece: **no es que el motor
consulte la normativa, es que cada guard pueda citar su autoridad.**

### Las tres preguntas que contesta

- Si mañana cambia una norma, **¿qué guards hay que revisar?**
- Cuando un guard salta, **¿se le puede decir al cliente por qué, con cita?**
- ¿Cuáles de los 28 son **derecho** y cuáles son **criterio nuestro**?

La tercera es la que más se olvida, y evita el peor error posible de cara a un
cliente: **presentar como obligación legal lo que es un criterio del despacho.**

### El reparto, y no es el que uno esperaría

| origen | guards | qué significa |
|---|---|---|
| **NORMA** | 16 | aplica una norma jurídica concreta |
| **TÉCNICO** | 11 | calidad del dato: no hay norma detrás, **ni hace falta** |
| **CRITERIO** | 1 | criterio profesional del despacho, no derecho |

Los 11 técnicos no son un hueco: `guard_confianza_captura` mide lo que sabemos
de **nuestra propia lectura**, `guard_importe_atipico` es estadística contra el
histórico —por eso no puede dar ROJO nunca—, `guard_anti_duplicado` implementa
una clave nuestra. Decir que no tienen norma detrás es la respuesta correcta.

Y `guard_cuenta_gasto_coherente` es el único CRITERIO: el PGC fija la estructura
de cuentas, **no cuál le toca a cada proveedor**. Eso son diez años de oficio
sistematizados, y presentarlo como obligación legal sería falso.

### CERO de 16 verificadas, y está escrito en grande

**Ninguna cita está verificada.** Lo que hay es una **propuesta** para que Diego
valide artículo por artículo con el texto delante. Se ha hecho así a propósito:
inventar una referencia legal en un motor contable sería el peor fallo de todo
el proyecto, y hoy mismo se vio a un resumen automático afirmar artículos que no
dicen lo que parecen.

Dos citas **no las propone Claude**: ya estaban en `motor_veredicto.py` (art. 154
LIVA en `guard_recargo_equivalencia`; la tabla de tipos en
`guard_tipo_producto_iva_semantico`). Se anotan con esa procedencia, que no es lo
mismo — pero **que estén escritas tampoco las verifica**.

### No se tocó el motor. Ni una línea.

Se podía haber metido la cita dentro de cada guard. Se decidió que no: el motor
es la pieza que `.claude/rules/contabilidad.md` protege con tests antes y
después, y esto es **metadato, no lógica**. Un registro externo da el mismo
resultado con riesgo cero — el mismo patrón que `fuentes_externas.py`.

**Verificado, no afirmado:** el md5 de `motor_veredicto.py` es idéntico antes y
después (`661612a2…`), y `layout_diario_contaplus.py` y `orquestador.py`
tampoco se tocaron. Tests del motor **65/65** y adversarial **112/112** en los
dos momentos.

### Un hallazgo real, encontrado al registrar

`TABLA_IVA_4` —la lista de productos al 4% de la que depende
`guard_tipo_producto_iva_semantico`— **sale directamente del art. 91.Dos LIVA y
no estaba registrada en ningún sitio**. Y contiene *aceite de oliva*, que pasó al
4% por una medida **temporal** (antes 10%). Si eso ha revertido y la tabla sigue
igual, **el guard aprueba un tipo incorrecto**. Anotada como `SIN_VERIFICAR` y
subida a `PENDIENTE.md` como tarea con nombre.

### 23º auditor: `ensayo_autoridad_guards.py`

21 comprobaciones. **No prueba que las citas sean correctas** —eso lo dice el
texto oficial, no un test—. Prueba que el mecanismo no miente: que ningún guard
se quede sin decidir, que una anotación huérfana salte, y sobre todo **que una
cita PROPUESTA no pueda pasar por verificada por el paso del tiempo**, que es el
riesgo real de un registro así.

Encontró dos anotaciones mías sin nota explicativa. Resaboteado en tres variantes
—auto-aprobarse las citas marcándolas VERIFICADO, ponerle una norma inventada a
un guard técnico, dejar de leer los guards del AST del motor—: **las tres caen.**

### Estado tras la sesión

`audit_project.py`: **40 ✅ · 1 ⚠️ · 0 ❌**. Motor **65/65**, adversarial
**112/112**, **29/29 suites**, privacidad sin hallazgos.

## 15-09-2026 (sesión Cloud, quinta entrada) — `fuentes_externas.py`: el primer ladrillo del módulo de normativa, y es el único que se puede poner hoy

Diego plantea, para el futuro, un módulo de normativa conectado a todo: BOE,
AEAT, registros, plataformas profesionales de pago, casuística propia, y el
conjunto enlazado al motor contable. La discusión completa y el análisis están
abajo, en la entrada de dirección. Esto es lo que **ya se puede construir sin
prometer nada que no se pueda cumplir**.

### El problema real, que no es "estar informado"

Hay números en este código que **no decidimos nosotros**: los tipos de IVA los
fija la ley, las casillas del 303 la AEAT, el plan de cuentas el PGC. Si uno
cambia y aquí no, el motor **no falla** — acierta menos, en silencio. Que es
peor, y es exactamente el tipo de fallo que este proyecto persigue.

`fuentes_externas.py` registra cada una de esas constantes con **valor, fuente
oficial, URL, fecha de verificación y estado**. `audit_project.py` comprueba en
cada pasada las dos únicas cosas que un programa puede comprobar con honestidad:

1. **que el valor anotado sigue siendo el que tiene el código** → si alguien
   edita la constante y no toca el registro, **FALLO**;
2. **que la verificación no ha envejecido** → si nadie la ha vuelto a mirar en
   12 meses, **NO_COMPROBADO**.

La distinción del punto 2 es lo importante: una verificación caducada **no dice
que la norma haya cambiado**, dice que nadie lo ha mirado. Misma regla que el
motor.

### Lo que NO es, y está escrito en su cabecera

No lee el BOE, no interpreta la ley y no contesta preguntas. Dice una sola cosa:
*"este número se copió de aquí, tal día, y nadie lo ha vuelto a comprobar desde
entonces"*.

Lo contrario —un sistema que resume normativa y te dice lo que significa— es lo
que este proyecto tiene prohibido. Hoy mismo, una consulta resumida
automáticamente afirmó que la ISP soportada va a *"las casillas 40-43"*. Se
descartó **porque estaba corroborada contra el impreso**. Sin esa corroboración
habría entrado en el repositorio como un hecho.

### Seis constantes registradas, y una anotada como PARCIAL a propósito

Las cinco del 303 (fórmula de la 27, de la 45, las dos columnas de bases y la de
tipos) van como **VERIFICADO**: se leyeron de los bytes del impreso oficial.

`TIPOS_LEGALES` va como **PARCIAL**, y esa honestidad es el punto: el 4, el 10 y
el 21 se leyeron **preimpresos** en el formulario; **el 0 y el 5 no se han leído
en ninguna fuente**. El 5% fue un tipo temporal y hay que comprobar si sigue
vigente. Queda anotado como el primer sitio donde mirar si aparecen tramos
marcados como tipo ilegal.

> Un registro que dijera VERIFICADO de todo sería más cómodo y **mentiría**. Que
> `PARCIAL` sea un estado usable y visible es la mitad del valor de esto.

### 22º auditor: `ensayo_fuentes_externas.py`

19 comprobaciones. Lo que prueba **no es que los números sean correctos** —eso lo
dice la fuente oficial, no un test— sino que **el mecanismo sabe darse cuenta**.

**Y encontró un agujero en sí mismo.** Al sabotear la caducidad *dentro de
`revisar()`* —el camino que usa la auditoría— el ensayo **seguía en verde**: la
familia A comprobaba *"no hay caducadas"* (cierto de vacío) y la D probaba el
método suelto, no el camino completo. El auditor apagado en silencio, dentro del
ensayo escrito para impedirlo. Añadida la inyección de una fuente caducada de
verdad; resaboteado: ahora cae con dos comprobaciones exactas.

Los otros dos sabotajes (editar una constante sin tocar el registro; una
verificación de hace siete años) salen ❌ y ⚠️ respectivamente, cada uno por su
puerta.

### Estado tras la sesión

`audit_project.py`: **38 ✅ · 1 ⚠️ · 0 ❌**. Motor **65/65**, adversarial
**112/112**, **28/28 suites**, privacidad sin hallazgos. **No se tocó
`motor_veredicto.py`** ni se añadió ningún guard.

## 15-09-2026 (sesión Cloud, cuarta entrada) — Las bases, y la estructura del 303 leída de la columna del impreso

Quedaba pendiente la mitad simétrica: el 27/45 arregló las **cuotas**, pero el
desglose de un `NO_CUADRA` enseña cuatro diferencias y las dos de **base**
seguían comparándose contra `01+04+07` — sólo el régimen general ordinario, sin
la base de la ISP (casilla 12) ni la de las intracomunitarias (10). El mismo
defecto que tenía la cuota, y un número grande ahí manda a investigar un
descuadre que no existe.

### El impreso da la estructura sin que haya que interpretarla

Extrayendo el formulario de 2022 apareció algo que no esperaba: el PDF **agrupa
las casillas por columna**.

```
deducible  BASE   28 30 32 34 36 38 40
deducible  CUOTA  29 31 33 35 37 39 41 42 43 44
devengado  CUOTA  03 06 09 11 13 15 18 21 24 26
devengado  BASE   01 04 07 10 12 14 16 19 22 25
devengado  TIPO   02 05 08 17 20 23
```

Eso es una **confirmación independiente** de las dos fórmulas: la columna de
cuotas del devengado es, casilla por casilla, la fórmula de la 27; la del
deducible es la de la 45. Salen de la estructura, no de la línea del total. Y de
paso da lo que faltaba para las bases. El impreso de 2024 añade los tripletes de
tipos reducidos temporales, cada uno `(base, tipo, cuota)`.

### Una diferencia de fondo, y por eso va en su propia clave

**El 303 no imprime ningún total de bases.** No hay una casilla *"total base
devengada"*. Así que `BASES_DEVENGADO` **no es una fórmula citada del impreso**:
es la columna entera, sumada por nosotros. Sigue siendo el conjunto correcto
contra el que comparar —y es incomparablemente mejor que `01+04+07`— pero su
respaldo es la estructura del impreso, no una línea que diga *"= tal + tal"*.
El script lo declara con esas palabras al imprimirlo.

### Y una tercera columna que faltaba nombrar

`CASILLAS_DE_TIPO` = 02, 05, 08, 17, 20, 23, 151, 154, 157, 166, 169. Varias
vienen **preimpresas** en el formulario (4,00 / 10,00 / 21,00 / 1,75 / 0,50 /
1,40 / 5,20): cualquier lógica que las trate como importe se equivoca en los
1.168 PDF a la vez. Ya se usó para que el aviso de recargo de equivalencia no
salte con un porcentaje preimpreso; ahora está nombrada y probada.

### Exportaciones e importaciones, que preguntó Diego

- **Exportaciones** (casilla 60) y **entregas intracomunitarias** (59) están en
  *Información adicional*, fuera de la liquidación, y son **operaciones
  exentas**: no llevan IVA, así que no pasan por el 477. **No afectan a la
  comparación.** Un cliente exportador no da problema por ese lado.
- **Importaciones**: sí entran, en la 32/33 (corrientes) y 34/35 (inversión), y
  las dos cuotas están dentro de la fórmula de la 45. Si ContaPlus lleva el IVA
  del DUA al 472, quedan cubiertas; si lo lleva aparte, no. **Es una pregunta
  empírica sin contestar**, y por eso el aviso de "conceptos que no podemos
  tener" las nombra en vez de afirmar nada. Ahora la comparación de bases ayuda
  a distinguirlo: si la base 32/34 trae importe y nuestra base no cuadra, ahí
  está la respuesta.

### Pruebas

Familia L de `ensayo_extraer_casillas.py`: las tres columnas no se pisan, ninguna
casilla de tipo se cuela entre bases o cuotas, el devengado tiene 15 filas en las
dos columnas, el deducible tiene 7 bases y 10 cuotas (42, 43 y 44 no llevan base)
y cada base va con la cuota siguiente. Más 5 comprobaciones nuevas en
`ensayo_verificar_303_pdf.py`.

Resaboteado en cuatro variantes —volver a `01+04+07`, desplazar la columna de
bases del deducible, marcar una casilla de cuota como si fuera de tipo, dar las
bases por cuadradas siempre—: **las cuatro caen, en las comprobaciones exactas.**

### Estado tras la sesión

`audit_project.py`: **36 ✅ · 1 ⚠️ · 0 ❌**. Motor **65/65**, adversarial
**112/112**, **27/27 suites**, privacidad sin hallazgos. **No se tocó
`motor_veredicto.py`** ni se añadió ningún guard.

## 15-09-2026 (sesión Cloud, tercera entrada) — Las fórmulas del 303, verificadas contra el impreso oficial de cuatro ejercicios

Diego preguntó si no podíamos ir a la AEAT y asegurarnos al 100% de que el
modelo es el que creemos, para llegar al PC sin dudas. Sí se podía, y había un
riesgo concreto que lo justificaba: **el corpus va de 2016 a 2026 y el 303 ha
cambiado en esos años.** Si la fórmula de la casilla 27 no fuera la misma en
2022 que hoy, `cuadre_interno()` daría FALLO sobre PDF perfectamente leídos.

### Cómo se hizo, y por qué así

Se descargaron los formularios oficiales de la AEAT y **se leyó la fórmula
impresa de los bytes del PDF**, no de un resumen. La precaución no es teórica:
ese mismo día, una consulta resumida afirmó que la ISP soportada va a *"las
casillas 40-43"*, que en el impreso son rectificación de deducciones,
compensaciones REAGP y regularización de bienes de inversión. **Un resumen
automático no es una fuente.**

### El resultado

| ejercicio | fórmula impresa de la casilla 27 |
|---|---|
| 2022 | `03+06+09+11+13+15+18+21+24+26` |
| 2023 | `152+03+155+06+09+11+13+15+158+18+21+24+26` |
| 2024 | `152+167+03+155+06+09+11+13+15+158+170+18+21+24+26` |
| 2026 | idéntica a 2024 |

**La casilla 45 no ha cambiado** en los cuatro: `29+31+33+35+37+39+41+42+43+44`.
**La 46 tampoco**: *"Resultado régimen general (27 − 45)"*.

La 27 **sólo crece** — cada año añade filas de tipos reducidos temporales. Como
sumamos el superconjunto de 2026, las casillas que un impreso antiguo no tiene
se leen como ausentes, cuentan 0, y la suma da igual. **La suposición que se
escribió ayer (*"sumar un superconjunto es seguro"*) queda verificada contra
impresos reales, no asumida.**

### Y se fija en código, para que no se degrade

`FORMULAS_IMPRESAS_VERIFICADAS` guarda la fórmula de cada año con su URL de
origen, y la familia K del ensayo comprueba que lo que sumamos las cubre todas —
más que la 27 de cada año está contenida en la del siguiente (si eso dejara de
cumplirse, el superconjunto no valdría y habría que elegir fórmula por año).
Saboteado quitando la casilla 26 de un lado y la 41 del otro: **cae, y nombra
exactamente la casilla que falta.**

### Lo que NO está verificado, dicho a la cara

**2016-2021.** La AEAT no publica esos formularios en su biblioteca actual.
Consecuencia si alguno tuviera una casilla que no sumamos: `cuadre_interno()`
diría FALLO sobre un PDF bien leído. Es un **error conservador** —*"no te fíes
de esta lectura"*— nunca un falso verde. Si aparecen muchos FALLO concentrados
en años antiguos, es el primer sitio donde mirar. Anotado en el código.

### Cuatro causas confirmadas con cita literal, y un respiro

Las instrucciones oficiales confirmaron, **en cita literal**, cuatro de los seis
conceptos que el script avisa como no modelables: casilla 44 (prorrata), 43
(bienes de inversión), 42 (compensaciones REAGP) y el recargo de equivalencia
—*"los tipos del 0,5%, 1,4%, 5,2% y 1,75%"*, exactamente los que estaban
escritos—.

Y un dato que reduce el problema más de lo esperado: la casilla 44 *"se
cumplimentará **únicamente en el 4T o mes 12**, o en los supuestos de cese de
actividad"*. **Un cliente con prorrata tiene 1T, 2T y 3T perfectamente
comparables** — sólo queda fuera el 4T. Recogido en el aviso del script y en
`PENDIENTE.md`.

### Estado tras la sesión

`audit_project.py`: **36 ✅ · 1 ⚠️ · 0 ❌**. Motor **65/65**, adversarial
**112/112**, **27/27 suites**, privacidad sin hallazgos. **No se tocó
`motor_veredicto.py`** ni se añadió ningún guard. Todos los documentos
consultados son formularios públicos de la AEAT: ningún dato de cliente.

## 15-09-2026 (sesión Cloud, segunda entrada) — El script avisa solo de por qué un caso NO PUEDE cuadrar

Cierra el cabo suelto de la entrada anterior. Ahí quedó escrito, como aviso en
prosa, que comparar contra las casillas 27/45 **no** arregla prorrata,
regularizaciones ni recargo — porque eso el 303 lo calcula y nuestras cuentas de
IVA no lo contienen (`EMPEZAR_AQUI.md` lo dice desde el primer día: *"no
reconstruye un 303"*).

Un aviso en prosa que hay que recordar no sirve de nada a las once de la noche.
Ahora lo detecta el script, leyendo las casillas del propio PDF:

| casilla | concepto | por qué no podemos tenerlo |
|---|---|---|
| 44 | regularización por prorrata definitiva | ajuste anual, no un apunte de factura |
| 43 | regularización de bienes de inversión | ajuste plurianual |
| 42 | compensaciones REAGP | no es una cuota de IVA soportada |
| 41 | rectificación de deducciones | puede no tener contrapartida en el 472 del trimestre |
| 33, 35 | IVA de importaciones | lo liquida la Aduana |
| 158, 170, 18, 21, 24, 26 | recargo de equivalencia | sus tipos (5,20/1,75/1,40/0,50) no están en `TIPOS_LEGALES` |

Cuando una trae importe, el caso **no puede** cuadrar, y el script lo dice con el
concepto, la casilla y los euros. El RESUMEN los cuenta aparte.

**Se declara como PISTA, no como veredicto**, y la diferencia importa: que
ContaPlus lleve o no cada uno de esos conceptos a las cuentas 477/472 es una
pregunta empírica sobre el corpus, **sin contestar**. Por eso el texto dice
*"mira esto antes de buscar un bug"* y nunca *"esto explica la diferencia"*.

Dos decisiones con su motivo:

- **Sólo casillas de CUOTA.** Las de tipo (17, 20, 23, 157, 169) llevan un
  porcentaje **preimpreso** en el formulario: mirarlas dispararía el aviso en
  todos los 303 del archivo.
- **Un cero no avisa.** Una casilla a cero es lo normal en cualquier impreso.

8 comprobaciones nuevas (familia J), resaboteadas en cuatro variantes —avisar con
ceros, incluir las casillas de tipo, quedarse sólo con el primer concepto,
olvidar la casilla 44 que motivó todo esto—: **las cuatro caen.**

### Estado tras la sesión

`audit_project.py`: **36 ✅ · 1 ⚠️ · 0 ❌**. Motor **65/65**, adversarial
**112/112**, **27/27 suites**, privacidad sin hallazgos. **No se tocó
`motor_veredicto.py`** ni se añadió ningún guard.

## 15-09-2026 (sesión Cloud) — El impreso se cuadra contra SU PROPIA aritmética: ahora cada PDF dice si se ha leído bien

Diego preguntó por qué no acudimos a la fuente de la AEAT para resolver la ISP,
y señaló que **el 1,2% nunca tuvo sentido** — los PDF se leen perfectamente a
ojo. Tenía razón en las dos cosas, y la segunda llevó a lo mejor de la sesión.

### La fuente autoritativa ya estaba delante

El propio impreso lleva sus sumas **escritas al lado de cada total**:

```
Total cuota devengada (152+167+03+155+06+09+11+13+15+158+170+18+21+24+26) → 27
Total a deducir       (29+31+33+35+37+39+41+42+43+44)                     → 45
Resultado régimen general (27 - 45)                                       → 46
```

Eso es la AEAT, en su propio documento, diciendo que **la casilla 13 (ISP) entra
en la 27**. El arreglo de ayer estaba bien fundado sin que lo supiéramos.

Se consultó además la sede electrónica. La instrucción de las casillas 12/13 se
obtuvo en cita literal y confirma lo anterior. **Pero la respuesta sobre las
casillas 28/29 era falsa** — afirmaba que la ISP soportada va a las "casillas
40-43", que en el impreso son *Rectificación de deducciones*, *Compensaciones
REAGP* y *Regularización de bienes de inversión*. No se usó, y queda anotado:
una consulta web resumida por un modelo **no es una fuente**; la cita literal sí,
y el impreso más.

**Y resulta que la pregunta no hacía falta:** la casilla 45 suma
`29+31+33+35+37+39+41+42+43+44`. Vaya la ISP soportada a la 29 o a la 41, **la
45 la incluye**. Comparar contra los totales esquiva la pregunta entera.

### 21º auditor (y el cambio que de verdad quita fricción): `cuadre_interno()`

Hasta hoy la única auto-validación del extractor era heurística: *"cuota/base
tiene que parecerse a un tipo legal"*. Eso produce una tasa global que nadie sabe
interpretar (el famoso 1,2%) y, sobre todo, **no dice nada de un documento
concreto**: no distingue *"este PDF se ha leído bien"* de *"este no"*.

Las fórmulas impresas sí. No son una heurística: son la **definición** de la
casilla. Si la lectura es correcta, tienen que cumplirse al céntimo — y se
comprueban **contra el propio documento**, sin compararlo con nada externo y sin
saber de quién es.

`veredicto_lectura()` devuelve los tres estados del motor, por documento:

| estado | significa |
|---|---|
| **OK** | alguna fórmula se ha podido comprobar y todas las comprobables cuadran. La lectura es buena |
| **FALLO** | alguna no cuadra. **La lectura está mal**, y da igual lo que diga la comparación contra la contabilidad |
| **NO_COMPROBADO** | no se leyó ningún total, así que no hay nada que cuadrar. **No es un aprobado** |

`verificar_303_pdf.py` lo imprime **antes** de interpretar ningún descuadre, y el
RESUMEN cuenta los tres. Eso es exactamente lo que quita fricción: un `NO_CUADRA`
deja de ser ambiguo. O el PDF se leyó bien y entonces el descuadre es contable, o
no se leyó bien y hay que mirar el PDF — y el script lo dice solo.

Detalles de diseño, cada uno con su motivo:

- **Sumar un superconjunto es seguro.** Las casillas 150-170 (tipos reducidos
  temporales) no existen en modelos antiguos: no se leen, cuentan 0, la suma
  sigue cuadrando. Fijado en el ensayo.
- **Una casilla ausente vale 0**, que es lo que vale una casilla vacía en el
  impreso. Tratarla como error convertiría en rojo cualquier 303 normal.
- **Sin total leído no hay aprobado.** Es la regla del motor aplicada al lector.
- **Margen de 5 céntimos**: el impreso redondea cada casilla a dos decimales y la
  suma del devengado tiene quince sumandos.

11 comprobaciones nuevas (familia I de `ensayo_extraer_casillas.py`),
resaboteadas en cuatro variantes —aprobar sin haber comprobado, olvidar la
casilla 13 en la fórmula, poner un margen absurdo, tratar una casilla vacía como
error—: **las cuatro caen.**

### Estado tras la sesión

`audit_project.py`: **36 ✅ · 1 ⚠️ · 0 ❌** (código 2). Motor **65/65**,
adversarial **112/112**, **27/27 suites**, privacidad sin hallazgos. **No se tocó
`motor_veredicto.py`** ni se añadió ningún guard.

## 14-09-2026 (sesión Cloud, tercera entrada) — SP_C_13 no es un descuadre contable: es una diferencia de CASILLA. Y la hipótesis que escribí hace dos horas era falsa

Diego confirmó dos cosas: que **sólo falla SP_C_13** (10 y 11 siguen cuadrando —
si es con el lector nuevo, la regresión obligatoria está pasada), y que en
ContaPlus una operación con ISP son **dos líneas de IVA, 477 y 472**.

### ⛔ Corrección: la propuesta de la entrada anterior era falsa

En la entrada anterior escribí que *"«tipo 0» es un cajón con dos cosas opuestas
dentro: el asiento de liquidación y la ISP"*, y propuse separarlos. **Es falso, y
lo desmiente el propio repositorio**, en la cabecera de `reconstruir_303.py`:

> *"Esto además arregla SOLO el caso ISP sin necesitar detectarlo: una línea 477
> de autorrepercusión no tiene venta detrás, así que ya no hace falta buscarla —
> **se deriva de su propia cuota**, como cualquier otra."*

La reconstrucción deriva la base como `cuota / tipo`. Eso sólo funciona con un
tipo distinto de cero, así que **la ISP se contabiliza con su tipo real (21%)** y
cae en el bucket del 21%, nunca en el del "tipo 0". El "tipo 0" es otra cosa: el
asiento de liquidación trimestral. **Nunca estuvieron en el mismo cajón**, y
separarlos no arreglaría nada porque no hay nada que separar.

La lección es la de siempre aquí: la respuesta estaba escrita en el código y no
la busqué antes de proponer. Jerarquía de verdad — Código → Tests → Git →
este fichero.

### La causa real, y es estructural

Nuestra reconstrucción suma **todo** el 477 del trimestre. El 303 lo reparte:

| lo que va en el 477 | casilla del 303 |
|---|---|
| régimen general ordinario | 01-09 |
| adquisiciones intracomunitarias | 10, 11 |
| **inversión del sujeto pasivo** | **12, 13** |
| modificaciones de bases y cuotas | 14, 15 |
| recargo de equivalencia | 16-26 |

`totales_pdf()` compara contra **03+06+09**, que es sólo la primera fila de esa
tabla. Para un cliente con ISP, nuestro devengado sale más alto **por diseño**, y
la resta da justo el importe de la ISP — que es exactamente el síntoma de
SP_C_13, al céntimo y en los dos lados.

**No es un descuadre contable. Es una diferencia de casilla.** Y no se arregla
detectando la ISP: se arregla comparando contra la casilla que sí la incluye.

### El arreglo: comparar también contra los totales que calcula el propio modelo

La **casilla 27** (total cuota devengada) es, por definición del impreso,
`03+06+09+11+13+15+...` — incluye todo lo anterior. La **casilla 45** hace lo
propio del lado deducible. Comparar contra ellas quita de golpe esa familia
entera de diferencias, **sin detectar nada y sin clasificar nada**.

`verificar_303_pdf.py` ya extraía las dos (las usaba sólo para explicar la ISP).
Ahora, cuando hay diferencia, añade una segunda comparación contra 27 y 45 y la
declara al lado de la principal.

**No cambia el veredicto, a propósito.** Cuál de las dos comparaciones manda es
una decisión contable, no un detalle de implementación: Diego ve las dos y
decide. Lo que el script dice ahora es *"contra 03+06+09 no cuadra; contra los
totales del propio modelo cuadra exacto — luego la diferencia es de casilla, no
de contabilidad"*.

Y no tapa nada: un descuadre real (un apunte que falta) **también** falla contra
el total. Esa es toda la diferencia entre las dos cosas, y está fijada en el
ensayo (familia I, 7 comprobaciones, con el patrón exacto de SP_C_13 y cifras
inventadas). Resaboteado en tres variantes —comparar contra la casilla
equivocada, dar por cuadrado siempre, inventarse la comparación cuando falta una
casilla—: **las tres caen.**

### Estado tras la sesión

`audit_project.py`: **36 ✅ · 1 ⚠️ · 0 ❌** (código 2). Motor **65/65**,
adversarial **112/112**, **27/27 suites**, privacidad sin hallazgos. **No se tocó
`motor_veredicto.py`** ni se añadió ningún guard.

## 14-09-2026 (sesión Cloud, segunda entrada) — El lector de casillas del 303 leía dígitos de DENTRO de los importes, y no tenía ni una prueba

Diego mandó cuatro capturas de un 303 real. **Eso fue una exposición de datos**
(un IBAN completo y los importes de un cliente concreto), el mismo mecanismo del
incidente del 27-08: el contenido llega en el mismo turno, antes de que se pueda
hacer nada. Ningún valor se transcribió a ningún sitio, ninguna cifra real entró
en el repositorio, y el análisis de abajo usa **sólo la estructura del
formulario**, que es pública. Queda anotado aquí sin datos, como la regla manda.

Pero las capturas contestaron una pregunta que llevaba meses abierta.

### Lo que decía el propio código

`patron_casilla()`, en `extraer_303_pdf.py`, llevaba este comentario desde el
día que se escribió:

> *"Se buscan variantes razonables porque **no se ha visto ni un solo documento
> real**: 'Casilla 01', '01.' al principio de línea/celda, o el número solo
> seguido de espacio y luego un número-moneda."*

Tres formas adivinadas, cero contrastadas. Y de ahí colgaba **todo** el cuadre
contra el 303: `verificar_303_pdf.py` importa esa función en vez de reescribirla,
justo para que las dos lecturas no puedan divergir.

### La forma real, y los dos defectos que destapa

En el 303 cada casilla es una **rejilla**: un recuadro pequeño con el número a
dos dígitos y, al lado, el recuadro del valor. Aplanado a texto queda así (con
cifras **inventadas**, de la misma forma):

```
07 9.999,99 08 21,00 09 2.099,99
```

Medido antes de tocar nada, sobre esa línea:

| casilla | lo que leía |
|---|---|
| 07 (base 21%) | **no la encontraba** |
| 09 (cuota 21%) | **999,99** — un trozo del importe |
| 02 | **99,99** — inventada de la nada |

Dos causas, independientes:

1. **Ninguna de las tres variantes adivinadas casa con un `07` suelto.** Pero
   `\b0?9\s*[.\)]` **sí** casa con el `9.` de DENTRO de `9.999,99`: el punto de
   millar español es idéntico a la marca de una lista numerada. No era
   imprecisión — era ruido con forma de dato.
2. **La ventana de 80 caracteres no respetaba la casilla siguiente.** Una casilla
   vacía se quedaba con el valor de la de al lado, y en el 303 los tramos del 4%
   y del 10% vienen vacíos casi siempre. Con el patrón viejo, la casilla 01 leía
   **111,11**, robado de la casilla 28.

Y un tercero que sale del mismo sitio: `contrato_datos` acepta el espacio como
separador de millar (con razón, en el archivo real los hay), así que en
`28 1.111,11 29 233,33` el lector veía **`29 233,33` como un solo número**,
29.233,33 — la etiqueta fundida con su propio valor.

### El arreglo

`patron_casilla()` reescrito **con el documento delante**: reconoce la etiqueta
suelta de la rejilla (siempre dos dígitos), y todas las variantes llevan guardas
para no casar dentro de un importe (`(?<![\d.,])` y `(?![\d.,])`).
`extraer_numero_tras()` corta por la **etiqueta siguiente**: en la rejilla, lo
que hay entre una etiqueta y la próxima es el valor de la primera y nada más.
Ese corte arregla de paso la fusión por el separador de espacio, porque va antes
que la lectura.

### 20º auditor: `ensayo_extraer_casillas.py`

21 comprobaciones en ocho familias. Resaboteado en tres variantes (volver al
patrón viejo, quitar el corte por etiqueta, quitar la guarda de aislamiento):
**las tres caen, en las comprobaciones exactas.** El sabotaje del patrón viejo
reproduce el defecto entero de un golpe: 07 = `None`, 09 = `999.99`, 28 = `None`,
01 = `111.11`.

El 19º auditor volvió a hacer su trabajo: puso la auditoría en rojo por este
ensayo antes de que estuviera cableado.

### ⚠️ Lo que NO se puede afirmar todavía, y es importante

Esto se ha validado contra una **reconstrucción** de la rejilla, con cifras
inventadas. En Cloud no hay ni puede haber un PDF real.

Y hay un dato que va en contra de la hipótesis y no se puede ignorar:
**`SP_C_10` y `SP_C_11` cuadraron exacto con el lector viejo.** Si el lector
fuera ruido puro sobre los PDF reales, eso no habría pasado. Luego el texto que
saca `pdfplumber` de esos PDF concretos no es exactamente la reconstrucción de
arriba. El arreglo debería ser una mejora estricta —añade la forma real y sólo
quita coincidencias dentro de números— pero *debería* no es *es*.

**Regresión obligatoria antes de fiarse:** volver a pasar `SP_C_10` y `SP_C_11`.
Si dejan de cuadrar, el arreglo ha hecho daño y se revierte. Y después, la tasa
de consistencia de `extraer_303_pdf.py` sobre el archivo real, que es la medida
de verdad.

### La duda de Diego sobre el "tipo 0" y la ISP, que está justificada

Dice que la lógica de la inversión del sujeto pasivo con el 0% "no está clara
del todo". Tiene razón, y el formulario enseña por qué:

- En el 303, la ISP tiene **casillas propias**: 12 (base) y 13 (cuota), en el
  lado devengado. Y la celda de "Tipo %" de esa fila está **en gris**: la ISP
  **no tiene tipo** en el modelo.
- La casilla 27 (total cuota devengada) **incluye** la 13.
- `totales_pdf()` suma 3+6+9, así que **excluye** la ISP a propósito.
- Y `cuadre_303_ficha.py` excluye ahora **todo** el "tipo 0" de nuestro lado.

**Ahí está el problema:** "tipo 0" es un cajón con dos cosas opuestas dentro —
el asiento de liquidación trimestral (que hay que quitar: no es una operación) y
la ISP (que es una operación real y pertenece a las casillas 12/13). Excluir el
cajón entero se lleva por delante operaciones reales.

Y encaja con lo ya medido: `diag_contrapartida_tipo0.py` encontró un **72%** con
contrapartida administrativa. El 28% restante no lo es — y ese 28% es candidato
a ser justamente la ISP.

**Propuesta, no implementada (es una decisión contable, y CLAUDE.md dice
preguntar):** dejar de tratar "tipo 0" como un cajón y clasificar **por asiento**
con el discriminador que `diag_contrapartida_tipo0.py` ya tiene (contrapartida en
Hacienda + importe exacto = liquidación). Liquidación → fuera. El resto → dentro,
mapeado a las casillas 12/13 para poder compararlo contra el PDF. Eso permitiría
que un caso con ISP **cuadre exacto**, en vez de "cuadra si le restas la ISP".

Pendiente antes de decidir: saber cómo graba ContaPlus una factura con ISP
(¿tipo 0 en las dos líneas 477/472? ¿el tipo real?). Es una pregunta empírica
sobre el corpus, contestable con un script local de tres roles.

### Estado tras la sesión

`audit_project.py`: **36 ✅ · 1 ⚠️ · 0 ❌** (código 2). Motor **65/65**,
adversarial **112/112**, guards **26/26**, **27/27 suites ejecutadas**, escáner
de privacidad sin hallazgos. **No se tocó `motor_veredicto.py`** ni se añadió
ningún guard.

## 14-09-2026 (sesión local + Cloud) — El cuadre contra el 303 presentado YA TIENE RESULTADO, y el manifest pasa a cobrarse por cliente

Doble entrada: la sesión local del 14-09 hizo el trabajo y no lo documentó aquí
(siete commits, cero entradas en este fichero y cero cambios en `PENDIENTE.md`);
la sesión Cloud del mismo día lo documenta y recorta la fricción de lo que
viene después. Los hechos salen de los commits y del código, no de la memoria
de nadie.

### Lo que hizo la sesión local: el 303 dejó de ser una promesa

`verificar_303_pdf.py` (nuevo) compara, número contra número, la reconstrucción
de `303_LOCAL.json` contra el 303 **realmente presentado** en PDF. **Primer
resultado real del proyecto contra su única verdad externa:**

| caso | resultado |
|---|---|
| `SP_C_10` | **cuadra exacto** |
| `SP_C_11` | **cuadra exacto** |
| `SP_C_13` | la diferencia en devengado **y** en deducible coincide **exacta** con la cuota de ISP declarada en el propio PDF (casillas 12/13), que este script no modela por diseño. No queda un céntimo sin explicar |

No intenta identidad: Diego la resolvió a mano abriendo ContaPlus. Es la
decisión correcta y conviene dejar escrito por qué — ver más abajo.

### El bug que hacía la ficha inservible: el "tipo 0 fantasma"

Comparando 20 fichas reales (5 clientes × 4 trimestres) apareció en **las 20**
un "tipo 0" con cuota negativa que cancelaba el resto del lado, y hacía que el
TOTAL saliera siempre 0,00. `diag_coherencia_por_lado.py` (27-08) no podía
verlo: comprueba `base × tipo = cuota` **dentro** de un tipo, nunca un tipo
contra la suma de los demás.

Perseguido en dos pasos antes de tocar nada:

1. `diag_patron_cierre_iva.py` — mide el ratio `|cuota tipo 0| / |suma de los
   demás tipos del mismo lado|`. **91,3% con ratio ~1.0**: no es ruido.
2. `diag_contrapartida_tipo0.py` — vuelve al `Diario.dbf` (el JSON ya está
   agregado por tipo y no puede decir qué hay al otro lado del asiento) y
   cuenta el prefijo de 4 dígitos del PGC de las otras líneas del mismo
   asiento. **72% en cuentas administrativas** (Hacienda, o reclasificación
   del propio 477/472), nunca un tercero real.

Conclusión: es el asiento de **liquidación/cierre trimestral de IVA**, no una
venta ni una compra. Excluido del TOTAL en `cuadre_303_ficha.py`, pero
**declarado siempre aparte** — nunca desaparece en silencio. Distinto de
`tipo_no_catalogado`, que se queda DENTRO del total a propósito porque podría
ser una casilla real de tipo desconocido.

Diego corrigió después la explicación con conocimiento de oficio: el 0%
auténtico se usa poco y, cuando aparece, la causa más habitual es **inversión
del sujeto pasivo** (se apunta a la vez en devengado y deducible, por eso
parece cancelarse). El caso medido no encajaba sólo con la liquidación, así que
el aviso ya no afirma una causa única. La lógica no cambia: es correcta con
cualquiera de las dos.

### Y el 19º auditor se ganó el sueldo en su primera semana

Cita literal del commit del arreglo: *"audit_project.py 26/26 suites cableadas
(incluidos los dos ensayos de hoy, **que el propio 19º auditor encontró sin
cablear antes de este commit**)"*. Sin él, `ensayo_diag_patron_cierre_iva.py` y
`ensayo_diag_contrapartida_tipo0.py` habrían nacido mirando a la pared, igual
que las siete del 11-09.

### Lo que hizo la sesión Cloud: el manifest se cobraba por trimestre

`verificar_303_pdf.py` pedía una línea por caso: `CLAVE|TRIMESTRE|RUTA_AL_PDF`.
Cada línea obliga a localizar el PDF de ese trimestre, copiar su ruta y
escribirla. **Diez años de un cliente son 40 líneas a mano.**

Pero el trabajo caro no está ahí. Lo caro es abrir ContaPlus para saber que
`SP_C_10` es tal empresa — y eso **se paga por cliente, una vez, y ya está para
siempre**. Localizar el PDF de un trimestre es mecánico: la carpeta ya es la del
cliente y el nombre del fichero ya declara el trimestre.

Añadida la forma de **dos campos**, `CLAVE|CARPETA`, que se expande sola a todos
los trimestres que encuentre. **Una línea por cliente en vez de una por
trimestre y año.** Las dos formas conviven: un manifest ya escrito sigue
valiendo tal cual.

No reescribe el reconocimiento de trimestre por nombre: importa
`trimestre_del_nombre()` de `cruzar_303_importes.py`, que ya se peleó con el
archivo real (su patrón estricto dejaba fuera 145 de los 1.168 ficheros, un 12%,
por escribir "2T" en vez de "2 trimestre"). Escribir aquí una cuarta versión
sería repetir el error de los TRES regex de importes, los tres mal y en
silencio.

**Lo que NO hace, a propósito:**
- Si dos PDF dicen ser el mismo trimestre (un original y una complementaria, o
  una copia), **no elige ninguno**: lo declara como ambiguo. Elegir sería
  inventarse cuál es el bueno.
- Un PDF de un trimestre sin contabilidad reconstruida **se cuenta y se
  declara**, no desaparece.
- `--solo-expandir` enseña en qué casos se expande el manifest **sin abrir ni un
  PDF**, para comprobar que las carpetas son las buenas antes de la pasada
  larga. Tampoco exige `pdfplumber`: pedir una dependencia para un trabajo que
  no la usa es el mismo error que ya tenía `extraer_303_pdf.py` al salirse en el
  import.

### Un fallo en mi propia prueba, encontrado saboteando

La familia H comprobaba *"un modelo que no es 303 no entra"* con el fichero
`modelo 347 2024.pdf`. **Pasaba por otro motivo:** ese nombre no lleva
trimestre, así que lo descarta el parseo de trimestre, no el filtro de "303".
Quitando el filtro, la comprobación seguía verde — un contraste que no
contrasta.

Y el caso real es peor de lo que parecía: en la carpeta de un cliente conviven
con el 303 los **111, 115, 130 y 349**, y varios son trimestrales con el mismo
formato de nombre. Sin filtro se compararía un 303 contra un 349. Cambiado el
contraste a `MODELO 349-1º TRIMESTRE 2024.pdf`; resaboteado: ahora cae.

Cinco sabotajes sobre la implementación (elegir un ambiguo a ciegas, no mirar
subcarpetas, callar los trimestres sin contabilidad, filtrar la carpeta en el
mensaje, quitar el filtro de 303): **los cinco caen, en las comprobaciones
exactas.**

### Por qué NO se automatiza la identidad, y no es pereza

Vuelve cada pocas sesiones, así que queda escrito con los dos motivos, cada uno
suficiente por separado:

1. **No hay dato.** Una copia de ContaPlus no dice de quién es: nombre y NIF
   viven en el registro de la instalación, no en la copia. Medido y descartado
   por siete vías (`datempre.dbf` tiene `CNIFEMP` pero **0 registros**;
   `DATOS.ASC` **0 bytes**; `M390A.dbf` **1.268 de 1.287 enteramente a cero**).
   No es difícil: no está.
2. **Por importes sería circular.** Es lo que intentó `cruzar_303_importes.py`:
   usar las cifras reconstruidas para decidir de qué cliente es, y luego esa
   identidad para comprobar si las cifras reconstruidas son correctas. Aunque se
   hiciera con un vector de doce trimestres en vez de un importe suelto, sigue
   siendo suponer lo que se quiere demostrar. **El paso manual de Diego es lo
   que rompe el círculo, y por eso vale lo que cuesta.**

### Pendiente de medir, y es de un solo comando

`verificar_303_pdf.py` razona que un `NO_CUADRA` puede ser un fallo de lectura
del PDF porque *"extraer_303_pdf.py ya midió 1,2% de consistencia"*. **Ese 1,2%
está caducado**: se midió con un regex de números que leía `12345,67` como
`345,67`, y el 47% de los importes reales vienen sin separador de millar. Lo
dice el propio `extraer_303_pdf.py`: *"candidato serio a explicar parte del
1,2%... que se atribuyó entero a la rejilla del PDF. Ahora manda
contrato_datos.py."* **Nadie lo ha vuelto a ejecutar desde el arreglo.**

Cuidado con esperar milagros: `cruzar_303_importes.py` documenta que la causa
principal es **estructural** (los importes viven en una rejilla, y al aplanarla a
texto el número junto a una etiqueta suele ser el de otra casilla). El regex
explica *parte*, no necesariamente el todo. Pero es un comando, cero trabajo
manual, sobre 1.168 PDF ya localizados — y el dato que sale decide si merece la
pena construir el camino masivo o seguir caso a caso.

Nota a favor de volver a medirlo: `verificar_303_pdf.py` usa **ese mismo
extractor**, y con él SP_C_10 y SP_C_11 cuadraron exacto. Es decir, sobre los
PDF que se han probado de verdad, funciona. Merece la pena saber sobre cuáles.

### Estado tras la sesión

`audit_project.py`: **35 ✅ · 1 ⚠️ · 0 ❌** (código 2, el ⚠️ son las dependencias
del contenedor Cloud). Motor **65/65**, adversarial **112/112**, guards
**26/26**, **26/26 suites ejecutadas**, escáner de privacidad sin hallazgos.

**No se tocó `motor_veredicto.py`**, ni `layout_diario_contaplus.py`, ni
`orquestador.py`. **No se añadió ningún guard.** Ningún dato real entró ni salió.

## 11-09-2026 (sesión Cloud) — Siete pruebas llevaban semanas mirando a la pared, y la auditoría completa salía en verde igual

Escaneo de abajo arriba del repositorio, pedido para decidir qué hacer a
continuación. Lo primero que salió no fue una tarea pendiente: fue que la rama
de trabajo iba **cinco commits por detrás de `master`** —el trabajo del 27 y 28
de agosto ya estaba fusionado y con cuatro commits más encima—. Puesta al día
antes de juzgar nada, porque el estado que se mide sobre un árbol viejo no es
el estado.

### El hallazgo

El repositorio tiene 22 suites de prueba. `audit_project.py` ejecutaba 15.
**Siete existían, estaban en verde, y nada ni nadie las ejecutaba nunca:**

| suite | qué protege |
|---|---|
| `ensayo_validar_captura_historica.py` | la regresión del **bug P0 del 21-08** (*"0.0% miente"* cuando no se reconoce el separador del CSV), la acumulación incremental del histórico y su orden cronológico |
| `ensayo_enlazador_clientes_303.py` | que la extracción a `calcular_grupos()` no cambió el agrupamiento |
| `ensayo_diag_carpetas_multiempresa.py` | que `calcular_sospechosas()` distingue mezcla de sana sin falsos positivos |
| `ensayo_diag_calibracion_sospechosa.py` | que separa mezcla real de artefacto temporal, y sabe decir NO_COMPROBADO |
| `ensayo_consolidar_identidad.py` | el caso que **ninguna** de las tres señales anteriores ve por separado |
| `test_comparar_esquema_dbf.py` | la comparación de layout `.dbf` — **lo que tiene que avisar si ContaSOL cambia el formato en enero** |
| `test_numeracion_correlativa.py` | correlatividad sin huecos: requisito de VeriFactu, no comodidad |

La primera es la que más urgía: valida el script que produce **el único número
del proyecto con umbral acordado por adelantado** (`SIGUIENTES_PASOS.md` §4).
Su hermana `ensayo_validar_captura.py` sí estaba cableada, pero cubre otra cosa
—que **cuente** bien—; ésta cubre que **no mienta** cuando no puede contar.
Ninguna de sus tres regresiones estaba protegida por la auditoría.

### Medido antes de arreglarlo, no supuesto

Con `ensayo_validar_captura_historica.py` **roto a propósito**, `audit_project.py`
imprimió la **misma salida** que con el repositorio sano y salió con el **mismo
código 2**. Ni un ❌, ni una mención. El criterio de "hecho" de
`.claude/rules/testing.md` —*"audit_project.py no reporta huérfanos"*— se
cumplía con una prueba completamente rota dentro.

### Por qué el auditor de huérfanos no podía verlo

`check_modulos_huerfanos()` existe exactamente para cazar *"una pieza probada en
aislado y nunca conectada"* —*"el fallo que MÁS se repite en este proyecto"*,
dice su propio docstring—. Y exime expresamente a todo lo que tenga `__main__` o
empiece por `test_`. **Toda suite cumple las dos cosas.** El auditor de piezas
desconectadas tenía su punto ciego justo en las piezas que auditan.

La lista de `check_estados_y_cobertura()` se mantiene **a mano**: escribir un
ensayo y no acordarse de añadirlo ahí lo deja mirando a la pared, en silencio y
para siempre.

### 19º auditor: `check_suites_sin_cablear()` + `ensayo_suites_cableadas.py`

No compara nombres: compara **ejecuciones reales**. `ejecutar_suite()` es ahora
la única puerta por la que esta auditoría lanza una suite, y anota la ruta
**antes** de lanzarla (para que una suite que reviente siga contando como
ejecutada: lo que se persigue es la que nadie mira, no la que falla — ésa ya sale
en rojo por su propio check). Al final de la pasada se compara lo que ha corrido
contra lo que hay en disco.

**Por qué no un `grep` del nombre, que era lo fácil:** `audit_project.py` está
lleno de nombres `.py` dentro de comentarios que explican qué cubre cada ensayo y
qué deja fuera. Un `grep` daría por cableada cualquier suite **nombrada**,
incluida una nombrada precisamente para explicar que se excluye. Es la *"barrera
de conveniencia"* de `.claude/rules/datos.md`: la que decide por el nombre en vez
de por el contenido. Escenario C del ensayo: una suite llamada
`ensayo_retro_semaforo.py` —nombre que aparece textualmente varias veces en el
fichero— sigue saliendo en rojo si no se ha ejecutado.

**Prueba propia de que funciona:** en cuanto se escribió `ensayo_suites_cableadas.py`,
y **antes** de añadirlo a la lista, el auditor puso la auditoría en rojo **por él
mismo**.

**Un punto ciego propio, encontrado en la segunda pasada y corregido:** la
primera versión comparaba por **nombre de fichero**. Con eso, `ensayo_x.py` y
`sub/ensayo_x.py` se tapaban la una a la otra. Cambiado a ruta relativa, y
fijado como escenario G.

**Y un falso verde propio, el tercer defecto encontrado en mi propio código y
el peor de los tres:** si la auditoría se lanza **desde otro directorio**,
`Path(".")` no encuentra ninguna suite, la resta da vacío y el check decía
**OK**. Un OK que significa *"no he mirado nada"* es exactamente lo que el motor
tiene prohibido dar, y es el mismo fallo que el escáner de privacidad tenía con
un `.DAT` (*"sin hallazgos"* porque no había abierto nada). Cero suites
encontradas sale ahora por la puerta de **NO_COMPROBADO**, que es la verdad.
Comprobado en los dos sentidos: quitando el guardarraíl, el ensayo cae; y la
auditoría lanzada de verdad desde un directorio vacío ahora avisa en vez de
aprobar.

**Y un recuento que no se entendía, corregido también:** imprimía *"25 suites
ejecutadas, 22 en el repositorio"* —25 > 22 porque por `ejecutar_suite()` pasan
también tres auditores que no son suites—. Un número que nadie puede cuadrar de
un vistazo deja de mirarse, igual que el ❌ que se enseñó a ignorar. Ahora dice
`23/23` y lista aparte los tres.

`ensayo_suites_cableadas.py`: **19 comprobaciones en nueve familias**, incluidas
dos invariantes de AST (ninguna suite se lanza con un `subprocess.run` suelto que
esquive el registro; `ejecutar_suite()` anota antes de lanzar). Resaboteado sobre
la implementación —no sobre la prueba— en seis variantes (volver al nombre,
decidir por `grep`, ignorar subdirectorios, callar las excepciones fantasma,
anotar después de lanzar, quitar el guardarraíl de "cero suites"): **las seis
caen, y en las comprobaciones exactas.**

### Excepciones: se pueden declarar, pero nunca en silencio

`EXCEPCIONES_SUITES` permite dejar una suite fuera **con motivo y fecha**, y se
imprime en cada pasada. Hoy está **vacío a propósito**: las siete se cablearon en
vez de excluirse, porque entre todas corren en 0,57 s, sin dependencias externas
y sin tocar ningún dato. Una excepción cuya suite ya no existe también sale en
rojo: un permiso caducado que sigue escrito es basura que tapa.

### Una decisión anterior revocada, y a la vista

`EMPEZAR_AQUI.md` documentaba desde el 27-08 que `test_numeracion_correlativa.py`
y `test_comparar_esquema_dbf.py` estaban fuera **a propósito** (*"código que
empieza ese día... mezclarlos ahí fingiría una madurez que no tienen"*). Se
revoca, y el documento lo dice: el argumento era sobre la madurez del **módulo**,
pero una suite cableada no afirma que el módulo esté maduro —afirma que sus
pruebas pasan—. Lo que sí garantizaba la exclusión es que **nadie se enteraría**
el día que una se pusiera roja.

`diff_comportamiento_motor.py` **sigue fuera, y ese motivo sí se mantiene**: con
el árbol limpio no encuentra nada, así que allí sería una línea verde que no
comprueba nada. Eso es un falso verde, que es distinto de una exclusión por
inmadurez. (Tampoco lleva prefijo `test_`/`ensayo_`: el auditor nuevo no lo
reclama, no es una suite sino una herramienta de mano.)

### Documentación corregida de paso

`EMPEZAR_AQUI.md` llevaba una nota explicando que **el número de comprobaciones
no se escribe a mano** porque ya había derivado una vez... y a continuación
escribía dos a mano, ambos desfasados: *"ejecuta hoy 21 comprobaciones"* y *"los
dieciocho corren dentro"*, con la auditoría en bastantes más. Retirados los dos.
Escribir la regla no basta; hay que no escribir el número.

### Estado tras la sesión

`audit_project.py`: **32 ✅ · 1 ⚠️ · 0 ❌** (código 2; el ⚠️ son las dependencias
del contenedor Cloud — `dbfread`, `anthropic`, `google-genai`, `pdfplumber`—, no
un defecto del código). Motor **65/65**, adversarial **112/112**, cobertura de
guards **26/26**, escáner de privacidad sin hallazgos. **23/23 suites del
repositorio ejecutadas.**

**No se tocó `motor_veredicto.py`**, ni `layout_diario_contaplus.py`, ni
`orquestador.py`. **No se añadió ningún guard.** Ningún dato real entró ni salió.

## 11-09-2026 (sesión local, PC de la asesoría — desktop app) — `audit_project.py` en rojo nada más arrancar: `validar_captura_historica.py` revienta en Windows por un `⚠` sin `encoding`

Sesión de retoma normal, siguiendo el orden que manda `CLAUDE.md`
(`arranque.py` → `EMPEZAR_AQUI.md` → `audit_project.py`). Antes de leer nada
del plan, `git fetch` mostró que `master` llevaba 5 commits que esta rama no
tenía (la fusión de los "32 commits del 28-08"); fast-forward limpio, sin
conflicto, verificado con `test_motor_veredicto.py` antes y después.

Con eso hecho, `python audit_project.py` salió con **código 1** — "hay un
defecto real, y eso manda sobre todo lo demás" — en la comprobación
`ensayo_validar_captura.py` ("Falsos verdes: los cuenta, no los inventa").
Por la jerarquía de `CLAUDE.md`, esto se investigó antes de tocar cualquier
otra cosa del plan.

**El defecto, reproducido antes de tocar código:** `validar_captura_historica.py`
es el único script del proyecto sin la guarda estándar
`sys.stdout.reconfigure(encoding="utf-8", errors="replace")` que llevan el
resto (`cuadre_303_ficha.py`, `emparejar_carpetas.py`, `diag_*.py`...). En
cuanto el fichero necesita imprimir `⚠` (dos sitios: campos críticos
ausentes, filas descartadas del cálculo) y la salida no va a una consola/pipe
UTF-8, revienta con `UnicodeEncodeError` **antes de escribir el agregado**.
Confirmado ejecutándolo directo con un CSV sintético de 6 filas sin `nif` ni
`fecha_expedicion`: traceback en la línea del `print`, código de salida 1, sin
`validacion_captura_agregado.json` en disco.

Esto es exactamente la familia de bug que `EMPEZAR_AQUI.md` ya documenta con
otro nombre ("verde en Cloud, roto en el PC real") — pero del lado del script
hijo, no del `subprocess.run` que lo llama: `check_subprocess_encoding`
comprueba que quien LLAMA declare `encoding`, no que el propio script se
proteja al imprimir. El ensayo lo cazó en cascada: `ejecutar()` devuelve
`agregado=None` cuando el fichero no aparece, y la comprobación de la línea
300 (`ag_e2.get("medicion_valida")`) explota con `AttributeError` sobre ese
`None` antes de que el ensayo pudiera ni reportar el fallo con claridad.

**Arreglado:** añadida la misma guarda de dos líneas que ya usa el resto del
proyecto, justo tras los imports. Nada más cambia — ni un guard, ni un
formato de salida.

**Verificado, en este orden:**
1. Reproducido el crash con el CSV sintético, antes de tocar nada.
2. Mismo CSV contra el fichero ya arreglado: código de salida 0, agregado
   escrito con `"medicion_valida": false` y `"campos_criticos_ausentes"`
   correctos.
3. `python ensayo_validar_captura.py`: las 27 comprobaciones en verde,
   incluidas las 3 de la FAMILIA E que antes fallaban en cascada.
4. `test_motor_veredicto.py` 65/65, `test_adversarial.py` 112/112 en verde
   (sin tocar el motor, se confirma que nada colateral se movió).
5. `python audit_project.py`: **código de salida 2** (no 0 — corregido a mano
   tras verificarlo de nuevo: un `| tail` en el comando de comprobación se
   comía el código real de `python`. El 2 es el esperado y documentado por
   las dependencias de captura por IA, no un defecto).

No hizo falta escribir ningún ensayo nuevo: `ensayo_validar_captura.py` ya
existía y ya probaba exactamente este caso (FAMILIA E, 09-09-2026) — lo que
faltaba era que el script bajo prueba no reventara antes de que el ensayo
pudiera comprobar nada.

**Nota al fusionar con la sesión paralela de arriba (mismo día, minutos
después):** su hallazgo (7 suites sin cablear, entre ellas
`ensayo_validar_captura_historica.py`) y este arreglo son independientes y
compatibles — ninguno toca los ficheros del otro. Con las dos fusionadas,
`audit_project.py` ejecuta ahora tanto la suite recién cableada como el
arreglo de `validar_captura_historica.py`, y la batería completa sigue en
verde (motor 65/65, adversarial 112/112, código 2 por las mismas
dependencias de siempre).

## 10-09-2026 (sesión Cloud) — Cierre de entrega: el fichero que se lee SIEMPRE mandaba al sitio equivocado, y un documento con apellidos reales no estaba bloqueado

Sesión de cierre. La pregunta era si quedaba valor en Cloud o si todo lo
restante es LOCAL. **Medido, y la respuesta es las dos cosas:** el valor de
*producto* que queda es local, pero la **entrega** tenía defectos reales que
habrían costado la primera sesión local.

### Lo que se midió para poder decirlo

Barrido de cobertura de ensayos: de 38 scripts que tocan datos reales, 35 son
diagnósticos de un solo uso ya ejecutados contra el corpus, y los 3 restantes
(`extraer_303_pdf`, `reconocer_303_pdf`, `enlazador_clientes_303`) **ya se han
ejecutado de verdad** — el primero sobre 1.168 documentos reales. Ninguno está
en la categoría de riesgo "llega a su única ejecución sin haberse ejecutado
nunca". **Esa veta está agotada.**

### Defecto 1 · El punto de entrada mandaba al sitio equivocado

`CLAUDE.md` es el único fichero que Claude Code carga siempre y obedece, en
cualquier superficie y con cualquier modelo. Ordenaba:

> *"Lee PROJECT_STATUS.md completo antes de hacer ningún cambio."*

Ese fichero tiene **140 KB y 2.379 líneas**, y en su propia línea 3 dice *"Para
ARRANCAR una sesión, lee `EMPEZAR_AQUI.md`... sirve para consultar, no para
empezar"*. Dos desenlaces posibles, los dos malos: leerlo entero y gastar media
sesión en historia, o saltárselo y perder el estado. Encima citaba dos veces un
documento que no existe en el repositorio.

*Arreglado:* `CLAUDE.md` ordena ahora, en este orden, `python arranque.py` →
`EMPEZAR_AQUI.md` → `PROJECT_STATUS.md` **sólo como consulta** → `audit_project.py`
antes de tocar el motor, con los tres códigos de salida explicados.

### Defecto 2 · Un documento con apellidos reales no estaba bloqueado

`FLUJO_CONTINUO_PLAN_DEFINITIVO.md` se cita **7 veces como autoridad** (dos en
`CLAUDE.md`, una en `.claude/rules/datos.md`), no está en el repositorio, y
`SUBE_A_GITHUB.md` dice explícitamente que contiene *"la lista de apellidos
reales de clientes/proveedores"*.

**No estaba ni en `NUNCA_SUBE_FILENAMES.txt` ni en `.gitignore`.** Comprobado
con fichero trampa antes de tocar nada: el escáner devolvía **"sin hallazgos" y
código 0**. Y `guardar_avance.sh` hace `git add` de los untracked, así que el
propio flujo de guardado del proyecto lo habría subido con el hook diciendo que
estaba limpio.

> **Es el mismo fallo del 19-08 con otro fichero**, y la misma lección ya
> escrita en `.claude/rules/datos.md`: *un "OK" que significa "no lo he
> comprobado" es exactamente el falso verde que el motor tiene prohibido.*

*Arreglado:* bloqueado en las dos capas y **verificado con el mismo fichero
trampa**: ahora el escáner sale con código 1 y `.gitignore` lo para también.

### `arranque.py` — el estado deja de ser prosa que envejece

Un documento afirma; esto **comprueba**. Todo lo que imprime lo mide en el
momento: entorno e intérprete (`python` vs `python3`), si el trabajo está en una
rama que nadie va a clonar, si el hook de privacidad está instalado, qué
dependencias faltan **y qué bloquea cada una**, y la lista de pendientes.

Lo único que lee de un fichero es `PENDIENTE.md`. **No abre ningún `_LOCAL`,
ningún `.DAT`, ningún CSV** — comprobado sobre el AST, no buscando palabras.

**Y no instala nada, deliberadamente:** `.claude/rules/seguridad.md` prohíbe
instalar software sin aprobación explícita, y eso incluye un `pip install`
automático al abrir sesión. Dice qué falta; instalarlo es una decisión, cada vez.

### `PENDIENTE.md` — una lista, no tres

Los pendientes estaban repartidos entre `EMPEZAR_AQUI.md` §7,
`SIGUIENTES_PASOS.md` §3 y las entradas de `PROJECT_STATUS.md`. Tres sitios para
lo mismo es como se pierde algo. Ahora hay uno, con los cuatro bloques ordenados,
las rutas reales, los comandos exactos y **los umbrales acordados por
adelantado** de cada medición. Los otros tres apuntan ahí.

### `.claude/hooks/session-start.sh` — para que no dependa de nadie

Registrado en `.claude/settings.json`. Corre en **toda** superficie, no sólo en
remoto: el PC de la asesoría es justo donde más importa no saltarse nada. Y
**nunca corta la sesión** — si algo falla, avisa y sigue; un hook que impide
arrancar es peor que uno que no informa. Probado sin `arranque.py`, sin Python y
fuera de un repositorio git.

### 18º auditor: `ensayo_arranque.py`

`arranque.py` está ahora en el arranque de **todas** las sesiones, lo que cambia
lo que significa que falle. 22 comprobaciones en cinco familias: que no revienta
nunca, que **fuera de un repositorio git no dice "árbol limpio"** (eso sería la
misma tranquilidad falsa que el motor tiene prohibida), que sólo abre
`PENDIENTE.md`, y que el hook nunca corta la sesión.

**El sabotaje encontró un agujero en mi propio ensayo:** al quitar el aviso de
"esta rama va por delante de master", la batería **seguía en verde** — y ese
aviso es lo más consecuente que dice el script. Añadida la familia E, que monta
un repositorio git de verdad con una rama sin fusionar y comprueba las dos
direcciones (avisa cuando toca, y **no** avisa cuando está sincronizado, o
dejaría de significar algo). Resaboteado: ahora cae con una comprobación exacta.

**Y un error propio, en la prueba y no en el código, otra vez:** la primera
familia D buscaba las cadenas `_LOCAL` y `.dbf` en el texto de `arranque.py` y
fallaba — aparecen en **mensajes que se imprimen**, no en código que abra nada.
Decidir por la FORMA es el error del 21-08 con `check_cableado`. Reescrita sobre
el AST: qué ficheros se abren de verdad.

### Estado tras la sesión

`audit_project.py`: **22 ✅ · 1 ⚠️ · 0 ❌** (código 2, el ⚠️ son las
dependencias del contenedor Cloud). Motor 36/36, adversarial 112/112, escáner de
privacidad sin hallazgos. **No se tocó `motor_veredicto.py`** ni se añadió
ningún guard.

---

## 09-09-2026 (sesión Cloud, tercera entrada) — La ficha del cuadre 303 podía comparar un cliente contra el 303 de otro, y nadie lo habría visto

Mismo criterio de selección que la entrada anterior: **qué pieza va a
ejecutarse contra datos reales sin haberse ejecutado nunca.** Medido, no
supuesto: `cuadre_303_ficha.py` era el último script de sesión LOCAL sin
ningún ensayo (`cola_revision.py` sí lo tenía, comprobado).

Y no es una pieza menor. Es la vía de **revisión humana** al cuadre contra el
303 presentado, que `SIGUIENTES_PASOS.md` §3.3 llama *"la única verdad externa
que este proyecto va a tener nunca"*. Construido el 26-08, documentado como
*"probado con datos ficticios"*, declarado **"lo primero de mañana"** en la
entrada del 27-08 — y sin que ningún fichero del repositorio lo ejercitara.

### Lo primero: comprobar que la pieza hermana no se ha quedado atrás

Antes de nada se verificó el contrato de formato contra `reconstruir_303.py`,
que se **reescribió dos veces el 27-08** (de derivar la base del gasto contable
a invertir la fórmula del 303). Es exactamente el patrón que ya mordió una vez:
`reconstruir_303.py` escrito el 21-08, el hallazgo de `BASEIMPO` el 25-08, y la
pieza hermana sin revisar hasta el 27-08.

**Resultado: el contrato coincide.** `{carpeta: {"2021T3": {"devengado": {tipo:
{base, cuota, apuntes}}, "deducible": {...}}}}`, con `tipo_no_catalogado`
compartido por los dos ficheros. Sin deriva. Verificado, no dado por bueno.

### La propiedad que más daño haría, y por qué el riesgo era real

El flujo son dos pasos separados por una decisión humana:

```
paso 1:  --listar         -> lista NUMERADA de carpetas
paso 2:  --elegir 2,5,9   -> las fichas de esas
```

> **Si el número 5 de la lista no es la misma carpeta que el número 5 de
> `--elegir`, se compara la contabilidad de un cliente contra el 303 de otro.**
> Y eso no produce un error visible: produce un descuadre inexplicable, o —peor—
> un cuadre por casualidad anotado como *"cuadra exacto"*.

El riesgo no era teórico: la lista **se salta** las carpetas sin datos al
imprimirlas, pero la numeración tiene que seguir siendo la del índice completo.
Son dos criterios en dos funciones distintas, y nada los ataba.

**Comprobado, y está bien:** con una carpeta vacía intercalada, la lista imprime
1, 2 y 4 (reservando el 3) y `--elegir 4` devuelve la carpeta que la lista
prometía. Queda fijado en código para que siga siendo verdad.

### Dos defectos reales, los dos reproducidos antes de tocar código

**1 · El TOTAL incorporaba en silencio lo que no se ha podido clasificar.**

```
tipo 21%             base        1.000,00
tipo SIN TIPO CLARO  base          300,00
TOTAL casillas 01-09 base        1.300,00   <- mezcla, sin decirlo
```

Ese TOTAL es lo que se compara contra la casilla del 303. Si no cuadra, no se
sabe si falla el motor o si esos 300 € van a otra casilla; y si cuadra, puede
haber cuadrado por casualidad. Sobre la única verdad externa del proyecto, **un
cuadre que no se puede explicar entero no es un cuadre.**

*Arreglado:* **no se saca del total** —decidir a qué casilla pertenece exigiría
saber qué tipo era, que es justo lo que no se sabe— sino que **se declara**, con
su base, su cuota y sus apuntes, justo debajo del total y donde se toma la
decisión. Y no aparece cuando todos los tipos están catalogados: un aviso que
sale siempre deja de significar algo.

**2 · Una ejecución fallida destruía la ficha anterior.**

`escribir_fichas()` escribía el fichero y **después** miraba si había salido
algo. Reproducido: ejecución buena → ficha de 1.449 bytes con el trabajo dentro;
`--elegir` sobre una carpeta sin datos → código de salida 1 **y la ficha buena
machacada por una vacía de 539 bytes**.

Y esa ficha no es una salida cualquiera: es el **documento de trabajo**, el que
se va marcando a mano trimestre a trimestre (`[ ] Cuadra exacto`) contra los 303
presentados. Perderla es perder la comparación ya hecha.

*Arreglado:* se calcula si hay algo que escribir **antes** de abrir nada
(`pares_con_datos()`), y la escritura es **atómica** (temporal + `os.replace`):
o está la ficha nueva entera, o sigue la anterior. Nunca una a medias.

> **Es la misma familia que el defecto 3 de la entrada anterior** (el ensayo que
> borraba las mediciones reales): *una herramienta no puede destruir el trabajo
> que existe para producir.* Dos apariciones en un día en sitios sin relación
> entre sí — merece la pena tenerlo presente al escribir cualquier salida.

### 17º auditor: `ensayo_cuadre_ficha.py`

**23 comprobaciones en seis familias**, todo sintético (`*_SINTETICA`, importes
inventados, ni un `.DAT` ni un PDF):

| Familia | Qué fija |
|---|---|
| **A** | El número elegido es la carpeta que la lista prometía, con una carpeta vacía intercalada para forzar el caso |
| **B** | Los totales suman **todas** sus celdas, en formato español, y un negativo (rectificativa) sale negativo |
| **C** | Un total con tipo desconocido lo declara — y no lo declara cuando no lo hay |
| **D** | Barrera de datos: nada sale de un `_LOCAL`, y por pantalla no se imprime ni un nombre de carpeta ni un importe |
| **E** | JSON inválido, vacío, inexistente, número fuera de rango o no numérico: ninguna ficha |
| **F** | Regresión del defecto 2: un fallo no se lleva por delante la ficha anterior |

### Sabotaje: seis defectos reintroducidos

| Sabotaje | En rojo |
|---|---|
| La lista numera lo impreso, no el índice completo | 2 — **incluida "`--elegir 3` devuelve otra carpeta"** |
| El TOTAL solo suma la primera celda | 2 |
| Deja de avisar del tipo desconocido | 2 |
| La barrera `_LOCAL` avisa pero no bloquea | 3 |
| Vuelve a escribir antes de saber si hay algo | 1 |
| Imprime el nombre de carpeta por pantalla | 1 |

### Un error propio, en la prueba y no en el código

La primera versión de este ensayo escribió los números de carpeta **a mano** y
falló cinco comprobaciones: daba por hecho que `MEDIA_SINTETICA` era la 3 cuando
la propia familia A acababa de imprimir que es la 2. **El ensayo se equivocaba,
no el script** — el mismo error de suponer en vez de derivar que el proyecto
lleva evitando en el código, cometido en la prueba. Corregido derivando los
índices del mismo criterio que usa el script, y anotado en su cabecera.

### Estado tras la sesión

`audit_project.py`: **21 ✅ · 1 ⚠️ · 0 ❌** (código 2, el ⚠️ son las
dependencias del contenedor Cloud). `test_motor_veredicto.py` 36/36,
`test_adversarial.py` 112/112, escáner de privacidad sin hallazgos.
**No se tocó `motor_veredicto.py`** ni se añadió ningún guard.

### Lo que esto cambia para el cuadre del 303

`python cuadre_303_ficha.py --listar` era el siguiente comando pendiente desde
el 27-08 y ahora se ejecuta con la herramienta probada: el número significa lo
que dice, un total que mezcla lo desconocido lo avisa, y un error de tecleo no
borra el trabajo hecho.

---

## 09-09-2026 (sesión Cloud, segunda entrada) — El contador de falsos verdes no estaba probado, y probarlo destapó tres defectos

Continuación directa de la entrada anterior. Elegido como trabajo de Cloud por
una razón concreta: `validar_captura_historica.py` produce el **único número
del proyecto con un umbral duro acordado por adelantado** —`SIGUIENTES_PASOS.md`
§4: *"≥ 1 falso verde → se para la automatización"*— y es además lo único que
puede hablar de falsos verdes, porque el retro-semáforo no puede por
construcción.

### El punto de partida: probado que funciona, no que sirve

Sus únicas comprobaciones eran **dos**, dentro de `ensayo_retro_semaforo.py`:
que arranca con un CSV de `;` y cabeceras no canónicas, y que detecta las
columnas solo. Las 12 filas que se le daban eran **todas VERDE/VERDE**. No se
comprobaba ni un número de la salida: solo `returncode == 0` y que aparecieran
dos palabras en el texto.

> **Traducido: si el script contara mal los falsos verdes, o se dejara alguno
> sin contar, el ensayo seguiría en verde.** La capacidad que le da todo su
> sentido era la única sin probar.

### Tres defectos reales, los tres reproducidos ANTES de tocar código

**1 · El JSON publicaba lo que la pantalla se negaba a publicar.** El bloque de
acierto se escribía siempre que existiera la columna humana, sin mirar la
decisión que la pantalla ya había tomado:

| Caso | Pantalla | JSON agregado |
|---|---|---|
| Columna humana sin valores | *"CERO no es el resultado: es la ausencia de resultado"* | `"falsos_verdes": 0, "pct_acierto_hoy": 0.0` |
| Campos críticos ausentes | *"LA TASA NO SE PUBLICA... publicarlo sería peor que no tenerlo"* | `"pct_acierto_hoy": 0.0, "falsos_verdes": 0` |

Es **el defecto del 21-08-2026 sobreviviendo** —el que ese mismo fichero
documenta tres veces en sus propios comentarios— en el sitio que más importa:
se arregló la pantalla y nadie tocó el JSON. Y los dos ficheros no valen lo
mismo: el detalle es `_LOCAL` y no sale del disco; **el agregado lleva escrito
"se puede subir" y es el que viaja**. La cifra tranquilizadora se quedaba justo
en el que viaja, sin el aviso que la desmiente, que solo existía en la consola
de quien lo ejecutó.

*Arreglado:* el agregado toma la misma decisión que la pantalla —
`estado: NO_COMPROBADO` con el motivo, y **ni un número** que pueda leerse como
resultado. Añadidos `campos_criticos_ausentes` y `medicion_valida` al nivel
superior, porque con críticos ausentes `veredictos_hoy` tampoco mide el motor:
mide que no se han encontrado las columnas.

**2 · Las filas con un veredicto humano ilegible desaparecían en silencio.**
Medido: un CSV de **10 facturas, las 10 con algo escrito en la columna humana**,
salía como *"facturas con veredicto humano: 5"*. Las otras cinco decían "NO
VALIDA" —una forma perfectamente razonable de escribirlo que no está en la lista
de sinónimos— y se caían del denominador sin un solo aviso. **Y con ellas se
caen los falsos verdes que llevaran dentro**, que es justo el número cuyo umbral
es "uno y se para". Una medición que se estrecha en silencio es peor que una que
falla: la que falla se ve.

*Arreglado:* contador `descartadas_por_no_reconocidas`, con aviso en pantalla y
campo en el agregado que **sale siempre, también cuando vale 0** — un campo
ausente no se echa de menos.

**3 · La auditoría destruía mediciones reales.** `ensayo_retro_semaforo.py`
borraba al terminar `retro_semaforo_agregado.json`, `validacion_captura_agregado.json`
y cuatro ficheros más, sin mirar si ya estaban. Están en `.gitignore`, así que
**no hay copia en ningún sitio**: el primero es el 87,71% VERDE sobre 30.013
asientos, y el segundo sería el número de falsos verdes de las 91 facturas.
Correr `python audit_project.py` después de medir los borraba.

*Arreglado:* se respaldan antes y se restauran después; se borra solo lo que el
ensayo ha creado. Verificado poniendo un fichero marcado y comprobando que
sobrevive a los dos ensayos, sin dejar respaldos sueltos.

### 16º auditor: `ensayo_validar_captura.py`

**28 comprobaciones en siete familias**, y ninguna se conforma con "no ha
petado" — todo número que el script imprime o escribe se compara contra un valor
calculado a mano:

| Familia | Qué fija |
|---|---|
| **0** | Que las facturas sintéticas dan el veredicto que el ensayo asume. Si el motor cambia, lo dice en vez de medir otra cosa creyendo que mide esta |
| **A** | Cuenta **exactamente** 3 falsos verdes de 10, con su 30,0% y su tasa de acierto del 70,0% |
| **B** | Y **no inventa ninguno** cuando no los hay. Sin esto, A la aprobaría un contador que devolviera siempre 3 |
| **C** | Motor ROJO + humano VERDE es un fallo pero **NO** un falso verde |
| **D** | El denominador son las **juzgadas**, no las filas del fichero |
| **E** | Regresión de los tres defectos de arriba |
| **F** | Regresión del 21-08: un fichero ilegible no produce **ningún** número |
| **G** | Seis formas de escribir "estaba mal" cuentan las seis |

### Sabotaje: seis defectos reintroducidos, uno a uno

Sin esto una prueba en verde no demuestra nada. Cada uno se metió a propósito y
se miró **dónde exactamente** se ponía roja la batería:

| Sabotaje | Comprobaciones en rojo |
|---|---|
| Cuenta como falso verde cualquier desacuerdo | **1, y es la de la familia C** |
| Denominador = filas en vez de juzgadas | 5 |
| Vuelve a publicar la tasa sin campos críticos | 2 (las dos de E2) |
| Deja de contar las filas ilegibles | 2 (las dos de E3) |
| Cuenta un falso verde de más (+1) | 7 |
| **Se deja uno sin contar (−1)** | **5** |

> **El primero es el que justifica la familia C entera:** un contador que suma
> todos los desacuerdos **pasa A y B** y solo cae en C. Sin esa familia, el bug
> entraría completo por una batería en verde.
>
> **Y el −1 es el que de verdad hace daño**, porque esconde falsos verdes en vez
> de inventarlos: cinco comprobaciones lo cazan.

### Estado tras la sesión

`audit_project.py`: **20 ✅ · 1 ⚠️ · 0 ❌** (código 2, el ⚠️ son las
dependencias de este contenedor Cloud). `test_motor_veredicto.py` 36/36,
`test_adversarial.py` 112/112, escáner de privacidad sin hallazgos sobre todo lo
versionado más el fichero nuevo.

**No se tocó `motor_veredicto.py`.** Ningún guard nuevo. Todo sintético y
declarado como tal: NIF inventados con dígito de control válido, proveedores
`PROV_SINTETICO_n`, ni una cifra procedente de una factura real.

### Lo que esto cambia para el día de las 91 facturas

Antes, el instrumento que produce el número que decide el proyecto llegaba a su
medición real sin haberse calibrado nunca — la misma situación que el 21-08
produjo tres defectos en la primera ejecución de los comandos LOCAL. Ahora, si
ese día sale **0 falsos verdes**, ese cero significa que se han mirado; y si
falta algo para medirlo, el fichero que se sube lo dice en vez de escribir un
cero tranquilizador.

---

## 09-09-2026 (sesión Cloud) — Escáner completo del repositorio: el 11º auditor llevaba dos semanas apagado, y la auditoría no sabía decirlo

Sesión de reincorporación tras trece días parados. Escáner completo del
repositorio antes de tocar nada, con la jerarquía de `CLAUDE.md` (Código →
Tests → Git → este archivo): se ejecutó todo, no se leyó nada como estado.

### Lo que el escáner confirmó en verde

`test_motor_veredicto.py` **36/36**. `test_adversarial.py` **112/112, 0 P0**.
Escáner de privacidad sobre los **113 ficheros versionados**: sin hallazgos.
Rama `claude/repo-full-scan-wns90w` sincronizada con `origin/master`, árbol
limpio, sin divergencia. Nada de lo cerrado el 27-08 se ha movido.

### El hallazgo: un auditor apagado, y disfrazado de auditor rojo

`audit_project.py` daba **❌ Cruce 303: identifica sin inventar — Falta
pdfplumber**. Leído en frío parece "el ensayo del cruce ha encontrado un
defecto". No era eso: **el ensayo no había llegado a ejecutar ni una sola de
sus 22 comprobaciones**, y llevaba así desde que se escribió el 26-08 en
cualquier clon sin `pdfplumber` instalado.

**Causa:** `cruzar_303_importes.py` tenía un `sys.exit(1)` en el **cuerpo del
módulo**, dentro del `except ImportError` de `pdfplumber`. Eso no corta el
script: corta a **cualquiera que lo importe**. Y quien lo importa es
`ensayo_cruce_303.py`, el 11º auditor — que por diseño explícito, escrito en
su propio docstring, **no abre ni un PDF**: sustituye `importes_del_pdf` por
una función que devuelve importes inventados. Estaba apagado por una
dependencia que su camino no llega a tocar.

Es el mismo patrón que el proyecto lleva persiguiendo, una vuelta más arriba:
**la barrera decidía en el sitio equivocado.** No en el punto donde se usa la
biblioteca, sino en el punto donde se nombra.

**Arreglo (los tres scripts de PDF, mismo patrón):** el `except ImportError`
deja `pdfplumber = None` y la exigencia pasa a `exigir_pdfplumber()`, llamada
**donde se abre el PDF de verdad** — `importes_del_pdf()` en
`cruzar_303_importes.py`, `main()` en `extraer_303_pdf.py` y
`reconocer_303_pdf.py`, que es donde ellos lo abren. Verificado en las dos
direcciones: los tres siguen cortando con el mismo mensaje y el mismo código 1
al ejecutarse como programa sin la biblioteca, y los tres se importan sin
morir. **`ensayo_cruce_303.py` pasa ahora sus 22 comprobaciones sin
`pdfplumber` instalado.**

### El defecto de fondo, que importa más que el bug

**La auditoría solo tenía dos estados, ✅ y ❌**, en un proyecto cuyo principio
entero es que un estado nunca puede afirmar lo que no ha comprobado. Con dos
estados, "no lo he podido comprobar" tenía que pintarse de rojo — y el
resultado práctico era peor que el bug:

> `EMPEZAR_AQUI.md` documentaba la salida esperada de la auditoría **con un ❌
> dentro, anotado "NORMAL, son de captura"**. Es decir: el documento de
> arranque del proyecto enseñaba a ignorar un rojo. **Un rojo que se enseña a
> ignorar deja de ser un rojo, y el siguiente rojo de verdad se va con él** —
> que es exactamente lo que pasó con el del cruce 303.

Es el fallo del escáner de privacidad del 19-08 con el color cambiado: allí un
OK que significaba "no lo he mirado", aquí un FALLO que significaba lo mismo.

**Arreglo:** `audit_project.py` tiene ahora los mismos tres estados que el
motor — **OK · FALLO · NO_COMPROBADO** (⚠️) — y tres códigos de salida, porque
son tres cosas distintas y el 1 significaba dos de ellas a la vez:

| Código | Significa |
|---|---|
| 0 | todo comprobado y en verde |
| 1 | hay un defecto real |
| 2 | nada falla, pero algo no se ha podido comprobar |

Una dependencia ausente ya no es ❌: no es un defecto del código, es una
condición del entorno. Sale por su propia puerta, con su propio código, y sin
poder confundirse con un aprobado.

### 15º auditor: `check_salida_al_importar`

Para que esto no vuelva. Comprueba sobre el **AST** que ningún módulo que
alguien importe llame a `sys.exit()` al cargarse. Solo acusa a los módulos que
**alguien importa de verdad** —conjunto derivado del propio AST, no una lista
escrita a mano que se quede desfasada—: `test_adversarial.py` termina con
`sys.exit()` a nivel de módulo a propósito y es correcto, porque nadie lo
importa. Acusarlo sería repetir la lección del 21-08 con `check_cableado`: un
auditor que mira la FORMA acusa a inocentes.

Probado con el bug reintroducido a propósito: se pone rojo señalando
`cruzar_303_importes.py` y la línea exacta; restaurado, vuelve a verde.

### Estado de la auditoría tras la sesión

**19 ✅ · 1 ⚠️ · 0 ❌**, código de salida 2. El único ⚠️ son las cuatro
dependencias sin instalar en este contenedor Cloud (`dbfread`, `anthropic`,
`google-genai`, `pdfplumber`) — no se instaló ninguna: el arreglo hace que no
hagan falta para auditar, que era justamente el punto. En el PC de la asesoría,
`pip install -r requirements.txt` deja el ⚠️ en ✅ y el código en 0.

### Corregido de paso: la numeración de auditores se contradecía a sí misma

`EMPEZAR_AQUI.md` llamaba a `ensayo_emparejar_carpetas.py` "15º auditor" en un
sitio y "14º" en la tabla; la tabla decía "los catorce" con catorce filas.
Unificado a 14º, y el nuevo entra como 15º. (Queda una discrepancia menor sin
tocar: este archivo llama "10º auditor" a `ensayo_cruce_303.py` y
`EMPEZAR_AQUI.md` "11º" — el orden bueno es el de `EMPEZAR_AQUI.md`, que lista
uno por uno.)

### Lo que NO se tocó, a propósito

`motor_veredicto.py`, `layout_diario_contaplus.py` y `orquestador.py` no se han
modificado. Ningún guard nuevo: no ha aparecido ningún caso real que lo pida.
Nada de esto necesitó datos reales ni corpus local — todo verificable con
`python audit_project.py` en cualquier clon.

### Sigue pendiente y no ha cambiado (es trabajo de sesión LOCAL)

1. Diego revisa `emparejado_LOCAL.txt`: confirmar las 14 de confianza alta,
   decidir las 23 restantes entre 2-3 candidatos nombrados.
2. Con eso, repetir `cruzar_303_importes.py` con una base de clientes fiable.
3. Las 91 facturas fotografiadas (`validar_captura_historica.py`) — lo único
   que puede hablar de **falsos verdes**, que es lo que el retro-semáforo no
   puede tocar por construcción.
4. Los pendientes que no son código: **cifrar el USB de copia** (15 minutos,
   abierto desde el 12-08, lo de mayor impacto por coste de toda la lista),
   clave de recuperación fuera del equipo, y confirmar si la copia incluye
   modelos/escrituras/DNI o solo contabilidad.
## 28-08-2026 (sesión LOCAL, trigesimosegunda entrada) — Cierre limpio del día: ROJO confirmado tres veces, ÁMBAR de 28,28% a 12,82%, identidad de cliente resuelta con precisión exacta

Diego volvió a ejecutar `retro_semaforo.py --inyectar` y `reconstruir_303.py`
con los dos arreglos de hoy (cuenta_proveedor sin truncar + clave_cliente por
carpeta+código) ya encima.

### La confirmación más limpia del día

El contador de "carpetas tratadas como cliente distinto" (añadido para
diagnosticar el hallazgo de la 29ª entrada) da ahora **1.287 reseteos** —
exactamente el número que `FASE0_RESULTADOS.md §12` ya había verificado el
12-08-2026 con 5 auditorías cruzadas independientes como "contenedores con
`Diario.dbf`". No es una cifra parecida: es la misma cifra, por dos caminos
de medición completamente distintos. Confirma que el reseteo ahora dispara
exactamente una vez por empresa real, ni más ni menos.

### Los números, con los dos arreglos de hoy aplicados

| | Antes de hoy | Arreglo `cuenta_proveedor` | + Arreglo `clave_cliente` |
|---|---|---|---|
| ROJO | 3,03% | 3,03% | **3,03%** |
| AMBAR | 28,28% | 18,23% | **12,82%** (+3,56 pts sobre el 9,26% base — "1-15: lo esperado") |
| `cuenta_gasto_coherente=FALLO` | 5.875 | 2.212 | **245** |
| Tasa ≥70% (mapeo inestable) | 198/606 (32,7%) | 18/1.129 (1,6%) | **3/1.851 (0,16%)** |
| Tasa <10% (sano) | — | 70,6% | **95,4%** |
| Detección `nif_de_otro` | 21,57% | 21,28% | **4,21%** |

### `nif_de_otro`: una caída que confirma una sospecha, no abre un problema

El 21,28% de la entrada anterior quedó anotado como hipótesis sin cerrar
("puede ser un efecto colateral bueno del histórico ya activo"). Con la
identidad de cliente corregida, cae a **4,21%** — confirma que la subida SÍ
era, al menos en parte, un artefacto de mezclar hasta 70 empresas bajo el
mismo histórico (más "material" con el que `importe_atipico` topaba con el
NIF ajeno por casualidad, no detección real). Sigue por encima del 0,4%
original de `RUN 11` — no es una regresión, es que el punto débil ya
documentado desde el 25-08 (*"un NIF ajeno con checksum válido no tiene por
qué distinguirse sin el patrón de cartera"*) sigue siendo el mismo. Los
otros cuatro tipos de error inyectado siguen al 100%.

### `reconstruir_303.py`: la fragmentación ahora es la real, no la oculta

509 combinaciones (carpeta, código) — antes 24 "carpetas-cliente" que en
realidad mezclaban docenas de empresas. 1.204 trimestres reconstruidos
(antes 139). **88.959 apuntes de IVA agregados — idéntico a antes del
arreglo**, confirmando que el cambio solo reagrupa, nunca pierde ni duplica
un apunte.

La fragmentación 509 vs ~33 clientes reales **es la esperada y no es un
defecto de hoy**: un mismo cliente real sigue apareciendo con claves
distintas en copias de fechas distintas, porque enlazar esas claves entre sí
sigue siendo el problema abierto desde el 12-08 (`enlazador_clientes_303.py`
lo intenta con cautela, sin cerrarlo del todo).

### Siguiente paso real para `§3.3` (comparación manual contra el 303 presentado)

Dado que enlazar entre carpetas sigue sin resolverse, el camino práctico no
es intentar identificar un cliente a través de varias copias: es elegir
**una sola carpeta** (una copia de una fecha concreta, con todas las
empresas de ese momento dentro — p. ej. la copia más reciente de 2026) y,
dentro de `303_LOCAL.json`, localizar las entradas de esa carpeta. Cada
código distinto dentro de ella SÍ identifica una empresa real distinta
(verificado, §12) — Diego puede reconocer a cuál corresponde cada código
abriendo esa misma copia en ContaPlus, sin que ningún dato salga de su
máquina. Con uno identificado, comparar sus casillas 01-09/28-29 contra el
303 que esa empresa presentó ese mismo trimestre.

---

## 28-08-2026 (sesión LOCAL, trigesimoprimera entrada) — `clave_cliente()`: revertida una regresión de tres días — la carpeta de ContaPlus no es el cliente, es una copia de seguridad con hasta 70 empresas dentro

Al preparar la comparación manual del 303 (`§3.3`), Diego señaló algo que
`consolidar_identidad.py` y `reconstruir_303.py` daban por sentado sin
comprobarlo de nuevo: las carpetas de nivel 1 de `100% contabilidad` no son
"una por cliente" — son copias de seguridad por fecha, con **todos los
clientes de ese momento dentro**. Los clientes reales se identificaron
durante el inventario a partir del propio `.DAT`, no de la carpeta.

### No es un hallazgo nuevo — es revertir una regresión de tres días, y la introdujo un acuerdo con Diego, no un descuido

`FASE0_RESULTADOS.md §12` (12-08-2026) ya había resuelto esto, con 5/5
auditorías cruzadas en verde: el identificador real vive en el **nombre del
fichero `.DAT`** — `SP_C_##[letra]`, donde `##` es el código de empresa
*dentro de esa copia* (una combinación empresa+ejercicio: ContaPlus crea una
"empresa" nueva cada ejercicio, incluso para el mismo cliente real, §11.1) y
la letra final (si existe) es solo una plantilla vacía del backup, no otra
empresa. Regla dura, ya escrita entonces: *"dentro de una misma carpeta, dos
códigos distintos son dos empresas distintas, nunca se fusionan."*

El commit `e35b585` (25-08-2026) cambió `clave_cliente()` de `carpeta+código`
a `solo carpeta` — de 507 "clientes" a 24. **No fue un descuido**: el propio
mensaje del commit registra que Diego confirmó entonces que organizaba las
carpetas una por cliente, y la verificación (`diag_verificar_carpeta_cliente.py`,
solape de NIF de contrapartes entre códigos de una misma carpeta, 90-100%)
parecía sólida. Pero es la **misma técnica** que el propio proyecto ya había
invalidado el 12-08 por fusionar empresas distintas (`§11.0`), y el mismo
artefacto que `SOSPECHOSA` volvió a demostrar el 27-08: proveedores comunes
(banco, suministros) inflan el solape entre empresas que no tienen nada que
ver entre sí. Verificado hoy contra el corpus real: 27 de 28 carpetas de
nivel 1 tienen los `.DAT` **directamente dentro**, sin subcarpeta por
cliente — y el propio corpus confirma hasta **70 códigos de empresa
distintos en una sola carpeta** (consistente con una copia multi-año, ~33
empresas × 2 ejercicios).

### Verificado contra el corpus real antes de tocar código

- 100% de los 3.857 `.DAT` siguen el patrón `SP_C_##[letra]` exacto, código
  siempre de 2 dígitos — cero excepciones.
- 1.287 sin letra (el fichero con `Diario.dbf`) + 2.570 con letra A/B
  (plantillas vacías) = 3.857 — coincide exactamente con `§12`.
- Distribución de códigos distintos por carpeta: mediana 40, máximo 70 —
  coherente con "empresas × ejercicios cubiertos por esa copia", no con "una
  empresa por carpeta".

### El arreglo

`reconstruir_303.py::clave_cliente()` y el reseteo de las cuatro cachés de
`retro_semaforo.py` vuelven a usar `(carpeta, código de 7 caracteres del
nombre del fichero)` — la clave *anterior* al commit del 25-08, restaurada
con el contexto de hoy. **Lo que esto NO resuelve, y sigue abierto desde el
12-08:** enlazar el mismo cliente real entre carpetas o ejercicios distintos
(código 04 en una copia, código 12 en otra) — `enlazador_clientes_303.py` ya
lo intenta con cautela (solo fusiona *entre* carpetas, nunca dentro de una),
y su propia medición de entonces (umbral 0,5 → 140 grupos de los 33 reales)
ya deja escrito que no lo cierra del todo. Sin ese enlace, un mismo cliente
real puede seguir contando varias veces con claves distintas en el
agregado — infraestima la continuidad, nunca la inventa, que es el lado
seguro del error.

### Efecto colateral encontrado y corregido: `ensayo_reconstruir_303.py` tenía sus propias claves de cliente escritas a mano

Sus lookups (`datos.get("CLIENTE_UNO", ...)`) usaban el formato antiguo
(solo carpeta) y quedaron en rojo con el cambio — el mecanismo de
deduplicación por huella de contenido (independiente de `clave_cliente()`)
seguía funcionando bien; solo el *lookup* del test apuntaba a una clave que
ya no existía. Corregido a `"CARPETA::COPIA_A"`, el formato real.

### Verificación

- Regresión directa de `clave_cliente()`: dos códigos de empresa en la
  misma carpeta dan claves distintas; la letra final del backup no cambia
  la clave (nuevo, en `ensayo_retro_semaforo.py`).
- Regresión de extremo a extremo: una carpeta sintética con **dos empresas
  reales** (dos códigos, un proveedor propio y coherente cada una, pero
  compartiendo por coincidencia la misma subcuenta de acreedor —lo normal,
  cada ContaPlus numera de forma independiente) no produce
  `cuenta_gasto_coherente=FALLO` para ninguna. Probado con sabotaje (vuelta
  al reseteo por sola carpeta): falla exactamente esa comprobación, ninguna
  otra.
- Corregido el `nodo.test.left.id == "carpeta_ruta"` de la comprobación AST
  ya existente (buscaba el nombre de variable viejo tras el renombrado; sin
  arreglarlo, las 4 comprobaciones de alcance de caché habrían fallado por
  un motivo que no es el que deben probar).
- `test_motor_veredicto.py` 65/65, `test_adversarial.py` 112/112,
  `ensayo_reconstruir_303.py` y `ensayo_retro_semaforo.py` en verde,
  `audit_project.py` sin huérfanos, escáner de privacidad sin hallazgos.

### Pendiente, y es de Diego

Volver a ejecutar `retro_semaforo.py --inyectar` y `reconstruir_303.py
--detalle 303_LOCAL.json` contra el corpus real. El resultado de la
trigésima entrada de hoy (AMBAR 18,23%, 24 "cubos" en `reconstruir_303.py`)
probablemente estaba todavía contaminado por esta mezcla más profunda —
ahora con la identidad correcta, es la primera medición que describe de
verdad "por empresa", no "por copia de seguridad".

---

## 28-08-2026 (sesión LOCAL, trigésima entrada) — Confirmado: el CSV de las 91-93 facturas fotografiadas NO existe. `§3.2` queda bloqueado por dato, no por búsqueda

Diego confirma, tras revisar: no hay ningún fichero con las facturas de la
prueba antigua (motor de entonces + veredicto humano) — ni en el repositorio,
ni anonimizado, ni real. Lo que existe son **las 93 fotos originales, sin
procesar**. Comprobado también que el repositorio no lleva ningún CSV con
esa forma (`git ls-files` — solo el script y su ensayo sintético).

**Esto cambia el estado de `SIGUIENTES_PASOS.md §2`** de "bloqueado por:
encontrar el fichero" (implica que buscar podría resolverlo) a **bloqueado
por dato: el fichero nunca se creó.** Convertir las 93 fotos en algo que
`validar_captura_historica.py` pueda usar exige pasarlas por el pipeline de
captura por IA (`captura_orquestador.py`) — el modelo tiene que **ver** la
factura, que es exactamente el paso detrás de la puerta del DPA
(`.claude/rules/datos.md`). No se hace hoy sin esa decisión tomada por
Diego. `§3.2` queda aparcado, sin fecha, hasta que exista DPA y se decida
procesar esas 93 fotos — no es un pendiente de esta sesión.

**Siguiente paso real, sin depender de esto:** `SIGUIENTES_PASOS.md §3.3`,
el cuadre contra el 303 presentado — no bloqueado por nada del DPA, solo
por localizar los modelos ya presentados.

---

## 28-08-2026 (sesión LOCAL, vigesimonovena entrada) — Primera medición real con las cachés de historial activas: ROJO estable, ÁMBAR investigado a fondo, y un bug real encontrado y cerrado

Diego ejecutó `retro_semaforo.py --inyectar` contra el corpus real completo
por primera vez con `actualizar_caches_historicas()` ya activa (arreglo de la
17ª entrada). Es la comprobación que llevaba pendiente desde entonces.

### 1 · El ROJO no se movió — predicción confirmada con datos reales, no solo con código

**3,03%**, idéntico al `RUN 11` de `FASE0_RESULTADOS.md §14`. Ninguno de los
guards despertados está en `criticos`; solo pueden mover VERDE→ÁMBAR. Sigue
en pie el `ROJO 3,03% < 5%` que cerró el retro-semáforo el 25-08.

### 2 · El ÁMBAR subió 19 puntos (9,26%→28,28%) — y eso activó la regla del `>15 puntos` de `SIGUIENTES_PASOS.md §4`

*"Demasiado ruido para ser útil. No se ajusta el umbral: se investiga qué
guard concentra los disparos."* `cuenta_gasto_coherente` dominaba con el 70%
del ÁMBAR de la factura (5.549 de 7.920).

### 3 · La investigación, capa por capa, con una herramienta nueva en cada paso

Se añadió a `retro_semaforo.py` (opcional, aditivo, sin cambiar el
comportamiento por defecto — mismo patrón que `--emitir-cartera`) un
contador de concentración por proveedor. Primera versión: agrupaba por el
hash de NIF que el propio script ya anonimiza. Resultado: 509 proveedores,
198 (32,7%) con tasa de FALLO ≥70% — demasiado alto para ser negocio mixto
real (el 21-08 caracterizó ese caso en ~47%, no en ≥70% masivo).

**Hipótesis 1, descartada con datos:** ¿se estaban fragmentando las cuatro
cachés por un reseteo de cliente mal calibrado (la misma clase de artefacto
de continuidad temporal que `SOSPECHOSA` ya demostró esta semana)? Añadido
un contador de carpetas tratadas como cliente distinto: **28**, un número
razonable frente a los ~33-37 clientes reales ya conocidos por
`emparejar_carpetas.py`. Descartada.

**El error real, encontrado leyendo el código, no adivinando:**
`guard_cuenta_gasto_coherente` y `actualizar_mapeo_cuenta_gasto()` indexan
por `cuenta_proveedor` — la subcuenta del acreedor —, **no por NIF**. Pero
`reconstruir_compra()` construía `fila['cuenta_proveedor']` a partir de
`cuenta()`, una función que trunca a **3 dígitos** (existe para clasificar
el TIPO de línea: acreedor 400/401/410/411, gasto 6xx, IVA 472 — uso
correcto ahí). Reutilizado ese mismo valor truncado como identidad de
proveedor, **todos los acreedores de un cliente bajo el mismo grupo PGC
(p. ej. todos los "410")** se trataban como una única entidad: el guard
comparaba la cuenta de gasto de un proveedor concreto contra la mezcla de
docenas de proveedores distintos.

Confirmado agrupando por `(cliente, cuenta_proveedor)` en vez de por NIF:
**solo 24 pares en todo el corpus (28 clientes) concentraban el 100% de los
5.875 FALLO, el 90% en solo 10.** Con `--detalle-cuenta-gasto` (nuevo,
fichero `_LOCAL`, nunca abierto por Claude), Diego confirmó que los códigos
dominantes eran `410`/`400` — cuentas de grupo, no subcuentas. Su propia
explicación cierra el diagnóstico: esas cuentas "pueden englobar algunas
compras/gastos donde no está claro el proveedor... se contabilizan como
'proveedor'/'acreedor' a secas".

### 4 · El arreglo

`reconstruir_compra()` ahora guarda la subcuenta COMPLETA (sin truncar) como
un campo nuevo en la tupla de línea, y `cuenta_proveedor` se construye a
partir de ella — nunca del valor de 3 dígitos usado para clasificar.
`cuenta_debe` se queda intencionadamente truncado: el propio guard compara
`habitual[:3] == propuesta[:3]` (por diseño, "629000 y 629001 son la misma
decisión"), así que pasarlo ya truncado no cambia nada y no era la causa.

### 5 · Resultado, medido de nuevo tras el arreglo

| | Antes del arreglo | Después |
|---|---|---|
| ROJO | 3,03% | **3,03%** (sin mover) |
| AMBAR | 28,28% | **18,23%** |
| `cuenta_gasto_coherente=FALLO` | 5.875 | **2.212** (−62%) |
| Proveedores distintos (agrupado bien) | 24 | **424** |
| Concentración top-10 | 90,1% | **12,8%** |
| Tasa ≥70% (mapeo inestable) | 198/606 (32,7%) | **18/1.129 (1,6%)** |
| Tasa 30-70% (negocio mixto, ~47% sintético) | 63/606 (10,4%) | **211/1.129 (18,7%)** |

**El número que decide:** el ÁMBAR sube 8,97 puntos sobre el 9,26% base
(no 19). Eso cae dentro del rango **"1-15 puntos: lo esperado"** de
`SIGUIENTES_PASOS.md §4`, no en el ">15: demasiado ruido" que había
disparado esta investigación. La regla se cumplió tal como estaba escrita:
no se tocó ningún umbral, se investigó, y el número confirmó que la
investigación iba en la dirección correcta.

### Verificación

`ensayo_retro_semaforo.py` ampliado con una regresión directa sobre
`reconstruir_compra()`: dos proveedores sintéticos distintos bajo el mismo
grupo de acreedor (`410`) deben recibir `cuenta_proveedor` distinta.
Probado con sabotaje (vuelta al valor truncado): falla **exactamente** las
2 comprobaciones que dependen del arreglo, ninguna más. `test_motor_
veredicto.py` 65/65, `test_adversarial.py` 112/112, `audit_project.py` en
verde salvo la excepción esperada, escáner de privacidad sin hallazgos.

### Lo que queda abierto, sin bloquear nada

**`estructura_reconocida` y `secuencia_documental_proveedor` siguen en CERO
FALLO** pese a tener histórico disponible (27.797 y 5.823 evaluaciones
respectivamente). Hipótesis sin confirmar: `retro_semaforo.py` lee asientos
ya contabilizados por un humano desde una factura real, no facturas
fotografiadas con OCR — el tipo de anomalía de formato/secuencia que estos
guards cazan es mucho más propio de una lectura por IA que de una
transcripción manual ya limpia. No es crítico (ninguno de los dos puede
mover ROJO) y no se investiga más hoy sin una hipótesis mejor que la
aritmética por sí sola pueda falsar.

**El residual del 1,6% (18 proveedores) con tasa ≥70%** no se investiga
más — es un tamaño de muestra normal para casos límite genuinos, no la
señal sistemática que llevó a esta investigación.

### Pendiente, siguiente paso real

Seguir el orden ya acordado en `SIGUIENTES_PASOS.md §3`: localizar el CSV
de las 91 facturas fotografiadas de la prueba antigua y ejecutar
`validar_captura_historica.py` (§3.2) — es la única medición del proyecto
que puede hablar de FALSOS VERDES, que el retro-semáforo no puede tocar
por construcción.

---

## 28-08-2026 (sesión Cloud, vigesimoctava entrada) — Orden cronológico en `validar_captura_historica.py`, y una lección de proceso propia sobre `git fetch`

**Aviso de proceso, antes que nada, por ser exactamente la misma lección que
ya documenta la entrada quinta de este archivo:** esta sesión empezó a
diagnosticar el hueco de las tres cachés de historial (`historico_proveedor`,
`formato_cache`, `secuencia_cache` nunca acumuladas) **sin haber hecho `git
fetch` primero**, sobre un checkout que resultó estar **11 commits por detrás**
de `origin` (el mismo hallazgo que la entrada decimoséptima ya había cerrado
ese mismo día, con `motor_veredicto.actualizar_caches_historicas()`, cableada
en `retro_semaforo.py` y en este mismo script). El trabajo propio equivalente
(`HistoricoIncremental` en `orquestador.py`) se completó, se probó y se auditó
en verde — y solo entonces, al hacer `git fetch --all` para investigar una
discrepancia de otro tipo (ver abajo), apareció el rango real. Comparado
contra `actualizar_caches_historicas()` ya mergeada: mismo hallazgo, mismo
diseño (acumular en `finally`, después de evaluar, nunca antes), pero la
versión ya fusionada es más completa (cableada también en `retro_semaforo.py`,
que la propia no tocaba). **Descartado sin commitear** (`git stash`, comparado,
`git stash drop`) — no aporta nada que la versión ya mergeada no tuviera.

### Lo que sí seguía siendo un hueco real, incluso con el arreglo ya mergeado

`actualizar_caches_historicas()` acumula en el **orden en que llegan las
filas**. Para `retro_semaforo.py` eso es correcto de por sí: los asientos de
ContaPlus vienen ordenados por `ASIEN`, cronológico por construcción. Para
`validar_captura_historica.py` **no hay esa garantía**: es un CSV de facturas
capturadas, que puede llegar en cualquier orden (por proveedor, por lote de
subida, alfabético). Si se acumula en orden de fichero y el fichero no es
cronológico, una factura puede "ver" en su histórico facturas que en la
realidad son **posteriores** a ella — la misma fuga de datos que el maestro de
proveedores ya corrigió el 21-08-2026 para el *alcance* (por cliente), aplicada
aquí al *orden*.

**Arreglo:** las filas se ordenan por `fecha_expedicion` ascendente (usando
`contrato_datos.parse_fecha()`, ya con la traducción de alias de columna
aplicada) antes de acumular nada; las filas sin fecha válida van al final —
se evalúan igual, pero nunca aportan su propio dato al histórico de una
factura de fecha conocida, para no fingir un orden que no se conoce.

### Verificación

`ensayo_validar_captura_historica.py` (nuevo — el script no tenía ningún
ensayo propio, pese a ser el que calcula la tasa de acierto y los falsos
verdes que decide el proyecto): 3 casos, de punta a punta contra el script
real vía `subprocess`. El caso clave coloca la factura con un importe 10
veces el habitual **primera en el fichero** pero con la **fecha más tardía**:
si el script acumulase por orden de fichero, esa factura se evaluaría sin
histórico (no se detectaría) y las cuatro normales, procesadas después,
verían un histórico contaminado por ella. El resultado correcto es el
contrario, y es lo que se mide. Probado con sabotaje (orden de fichero en vez
de cronológico): falla **exactamente** en las 2 comprobaciones que dependen
del arreglo, ninguna más. Incluye también la regresión ya conocida del bug
del separador (21-08-2026), que tampoco tenía ensayo propio hasta ahora.

`test_motor_veredicto.py` 65/65, `test_adversarial.py` 112/112,
`audit_project.py` en verde salvo la excepción esperada en Cloud
(`anthropic`/`google-genai`). Escáner de privacidad sobre los ficheros
tocados y sobre el repositorio completo: sin hallazgos.

### Pendiente, y es de Diego, en local

No hay nada nuevo que ejecutar específicamente por este cambio (no altera el
resultado cuando el CSV ya viene ordenado por fecha, que es el caso más
común). Sigue en pie lo mismo que ya pedía la entrada decimoséptima: volver a
ejecutar `retro_semaforo.py` y `validar_captura_historica.py` contra datos
reales con las cachés de historial ya activas, y comparar el nuevo
VERDE/ÁMBAR/ROJO contra el 87,71%/9,26%/3,03% ya citado.

---

## 27-08-2026 (sesión Cloud, vigesimoséptima entrada) — Medido el cambio de comportamiento REAL del motor tras seis cambios en un día

Cierre de la sesión con la pregunta que ninguna suite en verde contesta. Hoy
el motor recibió **seis cambios** (`actualizar_caches_historicas`,
`actualizar_mapeo_cuenta_gasto`, `guard_importe_atipico` reescrito, `_forma`,
`guard_secuencia_documental_proveedor`, `nif_check`). Cada uno con su prueba y
su sabotaje, y toda la batería en verde. Pero eso responde a *"¿sigue pasando
lo que ya probábamos?"*, no a lo que de verdad importa tras un día así:

> **¿QUÉ factura cambia de veredicto, y es un cambio que queríamos?**

Un cambio intencionado y uno accidental **se parecen mucho en un test en
verde: los dos pasan.** La única forma de distinguirlos es coger las mismas
facturas, pasarlas por las dos versiones y enumerar las diferencias.

### `diff_comportamiento_motor.py`

Monta el motor de una referencia de git y el del árbol actual en **procesos
separados** —los dos módulos se llaman igual y cargarlos juntos los mezclaría
sin avisar— y compara veredicto y estado de cada guard sobre 16 facturas
sintéticas: seis que tocan cada cambio del día y **diez de control que no
debían moverse**.

**El resultado del día, medido y no supuesto:**

| | |
|---|---|
| Cambian de veredicto | **5** — los cinco intencionados |
| Cambian de guard sin mover el veredicto | **1** — `secuencia_documental`, de un OK falso a `NO_COMPROBADO` |
| Idénticas en veredicto y en guards | **10 de 16** — los diez controles |

**Ningún caso de control se movió.** Los seis cambios hacen lo que dicen y
nada más.

### Nueve pasadas de auditoría sobre la propia herramienta

Se auditó repetidamente antes de guardarla, y cada pasada encontró algo:

1. **Primera ejecución:** solo aparecían 5 de los 6 cambios. Faltaba
   `secuencia_documental`, porque su guard está en `exentos` y su paso de
   `OK` a `NO_COMPROBADO` **no mueve el veredicto**. Una herramienta que solo
   mira veredictos se lo tragaba entero — justo el cambio más importante de
   los seis (un falso OK convertido en respuesta honesta). Añadida la sección
   de cambios a nivel de guard.
2. **Un control que se moviera solo a nivel de guard no hacía fallar**, por el
   mismo motivo. Corregido: las dos formas de moverse cuentan.
3. **`zip()` habría truncado en silencio** si las dos versiones devolvieran
   distinto número de resultados. Ahora sale con error: comparar listas de
   distinto tamaño sería inventar.
4. **Sabotaje** con una regresión real (`cuadre_total` desactivado): la caza
   —y la caza a nivel de guard, aunque el veredicto siguiera en ROJO por otro
   motivo. Sin la corrección 1, habría sido invisible.
5. **Fallo de diseño de fondo:** el `--ref` por defecto apuntaba al inicio de
   *hoy*, lo que la convertía en un artefacto de un día. Cambiado a `HEAD`,
   que es la pregunta reutilizable: *"el cambio que acabo de escribir, ¿qué
   mueve?"*.
6. **Mensaje deshonesto** cuando nada se movía (decía "todo lo que se mueve
   está en casos que se querían cambiar" sin que se moviera nada). Ahora dice
   que el motor se comporta idéntico, y avisa: *"si esperabas un cambio, tu
   cambio no está llegando al motor"*.
7. Una referencia de git inválida daba **traceback**; ahora, error claro y
   código de salida 2.
8. **El escáner de privacidad saltó** sobre un CIF literal escrito a mano.
   **No se amplió su lista blanca** —una lista escrita a mano rota, y hoy ya
   se han limpiado dos por haber derivado—: el CIF inválido ahora se **deriva**
   del válido, así que el fichero no contiene ni una cadena con forma de NIF y
   no hace falta excepción ninguna. Verificado que sigue siendo inválido de
   verdad (el guard lo rechaza).
9. Batería completa, los dos módulos no cableados, y escáner de privacidad
   sobre **todos** los ficheros trackeados: sin hallazgos.

### Deliberadamente NO cableada a `audit_project.py`

Con el árbol limpio siempre diría "sin cambios", así que en la auditoría
diaria sería **una línea en verde que no comprueba nada** — exactamente el
falso verde que este proyecto persigue. Es una herramienta para cuando se
toca el motor, no un vigilante permanente. Escrito en su propio docstring
para que nadie la cablee sin pensarlo.

---

## 27-08-2026 (sesión Cloud, vigesimosexta entrada) — `EMPEZAR_AQUI.md` había derivado durante la propia sesión: decía 39/39 cuando la suite iba por 65

Auditoría del punto de entrada, y el motivo es honesto: **lo he editado unas
ocho veces hoy**. Ese fichero es lo primero que lee la próxima sesión; si
quedó incoherente, la sesión arranca mal. Comprobado contra la realidad
ejecutando los comandos, no leyendo.

**Lo encontrado:** la plantilla de "salida esperada" decía `39/39 checks en
verde`. La realidad son **65/65**. Yo mismo la subí de 36 a 39 al principio
de la sesión, añadí 26 comprobaciones más a lo largo del día, y no volví.
Faltaba además la línea del auditor nuevo y el recuento de `subprocess.run`
estaba viejo.

**Por qué importa más de lo que parece:** esa plantilla es exactamente contra
lo que la próxima sesión compara. Con `39/39` escrito y `65/65` en pantalla,
la lectura natural es "algo se ha roto" — cuando lo roto era el documento.

### El arreglo no es cambiar 39 por 65

Es la **segunda vez en el mismo día** que un número escrito a mano en ese
fichero deriva (la primera fue el recuento de auditores). Cambiarlo por 65
solo aplaza el problema a la próxima vez que alguien añada una prueba.

La plantilla se ha reescrito para no llevar **ningún** recuento: ahora
enseña la **forma** —qué líneas tienen que salir en ✅— y dice explícitamente
que los números los da el comando, no el documento. Se han neutralizado
también los ordinales de auditor que quedaban en prosa ("13º", "15º"), que
fueron parte de la deriva anterior. Verificado línea a línea que la
plantilla y la salida real coinciden: 20 contra 20.

### Y una cosa que se decidió NO hacer, con su motivo

Se planteó automatizar esta comprobación (un check que compare la plantilla
contra la salida real). **Descartado**, y conviene dejar escrito por qué:
`audit_project.py` tendría que comprobar su propia salida contra el
documento, y ese check se añadiría a sí mismo a la lista que compara —
un problema de recursión por un beneficio ya pequeño, porque la plantilla
nueva es por **nombres de línea**, no por números, y los nombres cambian
mucho menos. Se prefiere no tener el auditor que tenerlo enredado. Es la
misma decisión que con el auditor de `float()` de esta mañana: no construir
también es una respuesta.

---

## 🔴 27-08-2026 (sesión Cloud, vigesimoquinta entrada) — El script que mide FALSOS VERDES tenía tres guards apagados, y el sesgo iba hacia parar el proyecto

La comprobación de paridad de la entrada anterior solo miraba
`retro_semaforo.py`. Pero **`validar_captura_historica.py` también llama al
motor** — y es el que va a producir el número de **falsos verdes**, la
métrica que `SIGUIENTES_PASOS.md` §4 dice que decide el proyecto. Nunca se
había comprobado su paridad.

### Tres parámetros que producción usa y el script no tenía forma de dar

No era que estuvieran mal pasados: **no existían las opciones de línea de
comandos**. `nif_cliente_titular`, `ejercicio_tanda` y `mapeo_cuenta_gasto`
iban fijos a `None`/ausentes, así que `sentido_compra_venta`,
`ejercicio_coherente` y `cuenta_gasto_coherente` quedaban en `NO_APLICA` de
forma estructural.

### Por qué esto era grave: el sesgo va en la dirección que más duele

Un guard apagado deja pasar a **VERDE** algo que producción sí marca. Y este
script mide falsos verdes, con un umbral durísimo acordado de antemano:
**«≥ 1 falso verde → se para la automatización»**.

Verificado con un caso concreto, ejecutando el script de verdad:

| Una factura de otro ejercicio | Veredicto |
|---|---|
| Medición, como estaba (`--ejercicio` inexistente) | **VERDE** |
| Producción (`orquestador.py` con `ejercicio_tanda`) | **ROJO** |

Si un humano marcara esa factura como incorrecta, se contaría como **falso
verde de un motor que en producción sí la caza** — y podría parar el
proyecto por un artefacto del instrumento.

### Una alarma mía que resultó exagerada, y la comprobé antes de escribirla

Supuse que `nif_cliente_titular=None` dejaría pasar una **venta archivada
como compra**. Probado: **sale ROJO igualmente**, porque `nif_casa_historico`
la caza por otra vía (el NIF del titular no está en el maestro de
proveedores). El guard queda debilitado, no mudo. Lo digo así en vez de
apuntarme un hallazgo más grande de lo que es.

### Arreglo

Añadidas `--nif-titular`, `--ejercicio` y `--mapeo-gasto-json`, **todas
opcionales y con el comportamiento de siempre por defecto**: sin ellas el
script hace exactamente lo que hacía. La diferencia es que ahora **lo dice
antes de medir**, no después — mismo patrón que ya usa `orquestador.py` con
`alta_cliente_anio`:

```
AVISO — guards APAGADOS en esta medicion, que en produccion SI corren.
Cada uno hace la medicion MAS PESIMISTA que el motor real:
   - ejercicio_coherente (falta --ejercicio): una factura de otro ano
     sale VERDE aqui y ROJO en produccion
   ...
Si sale algun falso verde, comprobar primero si lo explica uno de estos
antes de dar por malo el motor.
```

### Verificación

La comprobación de paridad se generalizó: ahora cubre **los dos** scripts de
medición, cada uno con su lista de divergencias declaradas. Probado con
sabotaje —volviendo a fijar `nif_cliente_titular=None`— y lo señala por su
nombre y por su fichero. Probado también de punta a punta: la misma factura
sintética da VERDE sin `--ejercicio` y ROJO con él.

`test_motor_veredicto.py` 65/65, `test_adversarial.py` 112/112, escáner de
privacidad sin hallazgos.

---

## 27-08-2026 (sesión Cloud, vigesimocuarta entrada) — Paridad medición↔producción: cinco divergencias, y una protegía en silencio la tasa de detección

El error de la entrada anterior (alcance de las cachés) era **una** divergencia
entre cómo llama al motor la medición y cómo lo llama producción. La pregunta
rigurosa era si había más. Se compararon los dos puntos de llamada, argumento
por argumento, sobre AST.

**Aparecieron cinco.** Ninguna estaba declarada en ningún sitio, y una resultó
ser mucho más importante de lo que parecía.

### El hallazgo que merece la pena: `vistos_duplicado=set()` en `--inyectar`

La llamada de inyección pasa un `set()` nuevo en vez del acumulado. Parecía un
detalle. **No lo es: está protegiendo la integridad del 78,99% de tasa de
detección**, y no había una sola línea que lo explicara.

La clave documental es `(nif, nº_documento, fecha, total)`. El error inyectado
`tipo_iva_cambiado` altera **solo el IVA**, así que los cuatro campos de la
clave quedan **idénticos** a los de la factura original, que ya está en el
acumulado. Con el set compartido, `anti_duplicado` dispararía → ROJO → se
contaría como **detectado** — pero por el motivo equivocado: el motor no
habría visto el IVA mal, habría visto un duplicado que solo existe porque la
propia medición fabricó la copia.

Con `set()` nuevo, cada inyección se juzga por su propio defecto. Verificado
que **ninguno de los cinco tipos inyectados es un duplicado**, así que no se
pierde detección de nada: solo se evita apuntarse un acierto que no lo es.

### Una hipótesis mía que resultó FALSA, y la verifiqué antes de actuar

Producción pasa `mapeo_cartera` y la medición no. `FASE0_RESULTADOS.md` §14
declara que el punto débil de detección es `nif_de_otro` *"que no tiene por
qué distinguirse **sin el patrón de cartera**"*, así que parecía que la
medición estuviera infravalorando la detección por no pasarlo.

**Comprobado empíricamente: no cambia el veredicto.** `guard_patron_cartera`
nunca devuelve OK (a propósito — un patrón es una hipótesis, no un hecho) y
está en `exentos`, así que su `NO_APLICA` no baja a ÁMBAR. Solo enriquece el
motivo. La frase de §14 habla de que **el humano** distinga con la evidencia
delante, no de que el guard cambie el veredicto. Divergencia real pero inocua
para los porcentajes — y además, usar la cartera durante la evaluación sería
una fuga de datos (se construye con el corpus entero).

### Las otras tres

- `alta_cliente_anio=1990` — deliberado y **sin un solo comentario**: el corpus
  mezcla ~24 clientes cuyo año de alta se desconoce, y con 1990 ninguna factura
  (2011-2026) es anterior al alta. Consecuencia declarada ahora: **esta
  medición no dice nada sobre `guard_fecha_posterior_alta`**.
- `nif_cliente_titular=None` — ya estaba declarado indirectamente vía
  `AMBAR_DEL_INSTRUMENTO`.
- `plazos_cache` omitido — **equivalente**: el motor hace `plazos_cache or {}`.
  Se declara igualmente para que la lista sea el retrato completo y nadie
  tenga que volver a averiguar si es inocua.

### Honestidad sobre lo que esta comprobación NO cubre

Se dice en el propio código, para que nadie confíe de más: **la paridad de
llamada NO habría cazado el error de las cachés de ayer.** Allí los parámetros
sí se pasaban —con el alcance equivocado—, y el alcance no se ve en el punto
de llamada. De eso se ocupa la comprobación de reseteo por cliente, que es
otra. Son dos redes distintas y hacen falta las dos.

### Verificación

Cuatro comprobaciones nuevas en `ensayo_retro_semaforo.py`. Probado con
sabotaje **en las dos direcciones**: una divergencia nueva sin declarar
(`ejercicio_tanda` fijado a una constante) → la señala por su nombre; y una
declaración que ya no corresponde a nada → la marca como caducada. Igual que
el auditor del patrón de falso verde, la lista de divergencias **se audita a
sí misma**: una lista que conserva entradas muertas acaba tapando una
divergencia real.

`test_motor_veredicto.py` 65/65, `test_adversarial.py` 112/112, escáner de
privacidad sin hallazgos.

---

## 🔴 27-08-2026 (sesión Cloud, vigesimotercera entrada) — Error propio, del día anterior: las cachés acumulaban mezclando TODOS los clientes

Al buscar si quedaba alguna otra familia de defecto conocida (la de `float()`
a pelo en vez del contrato de datos — descartada, ver abajo), se comparó el
alcance del histórico en producción contra el de la medición. **No
coincidían, y el error era mío, introducido el día anterior.**

### El error

En producción, `orquestador.py` construye el histórico con
`construir_historico_y_secuencia(filas)`, donde `filas` son las facturas de
**una tanda — es decir, de UN cliente**.

En mi arreglo de `retro_semaforo.py`, las tres cachés se inicializaban
**fuera** del bucle de contenedores, así que acumulaban a lo largo de todo el
corpus, **mezclando los ~24 clientes**. Curiosamente sí había acertado con
`mapeo_cuenta_gasto_cliente` (reseteado por cliente, porque el código de
cuenta no es identidad estable), pero no apliqué el mismo razonamiento a las
otras tres.

### Por qué importa, y no es un detalle de estilo

1. **La medición dejaría de describir a producción.** Este script existe
   para predecir qué hará el motor cuando se ejecute de verdad. Si el
   instrumento no se comporta como el sistema que mide, el número no
   describe nada — y el retro-semáforo está a punto de volver a ejecutarse
   precisamente para producir ese número.
2. **En `importe_atipico` la mezcla es además incorrecta en sí misma.** Un
   mismo proveedor puede facturar 5.000 € a un cliente grande y 100 € a uno
   pequeño; juntarlo todo desplaza la media e infla la desviación, con
   falsos positivos y detecciones perdidas a la vez.

**Matiz honesto, porque no todo apuntaba en la misma dirección:** para
`estructura_reconocida` y `secuencia_documental_proveedor`, acumular en
global sería discutiblemente **mejor** — un proveedor numera igual para todos
sus clientes, así que se vería más de su serie. Se ha elegido igualmente el
alcance por cliente: **que la medición refleje producción vale más que ser
más lista que ella.** Si algún día producción pasa a un histórico por
proveedor, se cambian las dos a la vez, no antes.

### Arreglo y regresión

Las cuatro cachés se resetean ahora **juntas y en el mismo sitio**, en la
frontera de cambio de cliente. Y el ensayo lo fija como invariante
estructural sobre AST: es fácil añadir una quinta caché y olvidarse, y el
síntoma sería un número silenciosamente equivocado, no un error visible.
Probado con sabotaje —sacando una sola caché del reseteo, exactamente el
error original— y el ensayo la señala por su nombre.

### Y una familia que se investigó y NO dio nada: `float()` a pelo

Se revisó si seguía viva la otra familia recurrente del proyecto (usar
`float()` sobre un campo de factura en vez de `contrato_datos.parse_numero()`
— causa raíz de los 8 falsos verdes y reaparecida el 26-08 en dos ficheros).
**Barrido el repositorio: no queda ningún caso vivo en el camino del motor.**
El único candidato con esa forma, `leer_ascii_completo` en
`layout_diario_contaplus.py` (`float(v) if v else 0.0`), **no es el mismo
caso**: leyendo un fichero de ancho fijo de ContaPlus, un campo numérico
vacío significa cero de verdad, no "dato ausente".

**Se decidió NO construir un auditor para esta familia**, y conviene dejar
escrito el motivo: distinguir un `float()` peligroso de uno legítimo exige
seguir de dónde viene el dato, no reconocer una forma — un detector
sintáctico daría falsos positivos constantes, y este proyecto acaba de
recordar (dos veces en dos días) que un auditor que grita cuando no toca
acaba ignorándose. Mejor no tenerlo que tenerlo gritando.

---

## 27-08-2026 (sesión Cloud, vigesimosegunda entrada) — El patrón de falso verde, convertido en auditor. Y cazó a su propio autor

La entrada anterior terminaba dejando escrito un patrón *"como forma a
buscar"*. Este proyecto ya sabe que eso no basta: `audit_estados.py` existe
porque una lección escrita no impide que el defecto vuelva. Dos razones
concretas para automatizarlo:

1. El patrón apareció **dos veces**, en guards distintos escritos en momentos
   distintos. No fue mala suerte: es una forma que se escribe sola con buena
   intención (evitar dividir por cero).
2. De **26 guards, solo 5 se auditaron a mano**. Los otros 21 no los había
   mirado nadie con esta lente.

### `audit_ok_sin_comprobar.py` — caza una forma, no un caso

Sobre AST, no con expresiones regulares: es la lección ya pagada en
`check_cableado` (21-08), donde una regex declaró siete huérfanos que no lo
eran porque solo reconocía el cableado escrito de una forma. Busca, dentro de
funciones `guard_*` que puedan devolver `OK`, un `if` con `and` que contenga
una comparación contra cero (`x > 0`, `x >= 0`, `x != 0`) cuyo cuerpo devuelva
un veredicto negativo — es decir, la forma exacta en la que "no hay con qué
comparar" acaba cayendo en un `return "OK"`.

### Lo que encontró en los 21 guards no auditados: un caso, y NO era bug

`guard_suma_tramos`: `if base_total_decl == 0 and suma != 0` → si ambos son
cero, cae a `abs(0-0) < TOL` → `OK, "suma tramos=0 = base_total=0"`. Compara
nada contra nada y lo llama correcto.

**Verificado antes de tocarlo, y resultó inalcanzable:** en
`contrato_datos.tramos()`, la rama legada solo añade un tramo `if d.valor`
(truthy), así que un cero nunca genera tramo; y `evaluar_fila_v4` solo llama a
este guard cuando `tramos` es truthy — luego `suma != 0` siempre. Comprobado
además, ejecutando el motor, que una factura con tramo pero **sin**
`base_total` no revienta: `guard_integridad_datos` la para antes. Queda como
**excepción declarada con su motivo**, no como bug ni como silencio.

### El auditor gritó cuando no tocaba — y lo cazó su propio ensayo

Primera versión: las excepciones iban indexadas por `(función, variable)` y la
caducidad se comprobaba contra el fichero que tocara analizar. Al analizar
**cualquier fichero que no fuera `motor_veredicto.py`**, todas las excepciones
salían "caducadas" y el auditor terminaba en rojo sin motivo.

Es **exactamente** el fallo que este proyecto ya pagó con `check_cableado`
—*"un auditor que grita cuando no toca acaba ignorándose, y entonces no avisa
cuando sí toca"*— cometido dentro del auditor escrito para evitar esa familia
de fallos. Lo detectó su propio ensayo antes de subir nada. Corregido
(excepciones indexadas por fichero) y **fijado como regresión explícita** en
el ensayo.

### La caducidad, que es la otra mitad del diseño

Una lista blanca que conserva entradas muertas acaba tapando un caso real —
la misma trampa que la lista `criticos` del motor, que el propio
`calcular_veredicto_v4` documenta como "una especificación, no un retrato de
lo que dispara hoy". Por eso el auditor **se audita a sí mismo**: si una
excepción declarada ya no aparece en el fichero para el que se escribió, lo
dice y termina en error.

### Verificación

`ensayo_ok_sin_comprobar.py` (nuevo, **18/18**), con las dos mitades que
exige este proyecto:

- **Detecta:** reproduce los dos bugs reales con su forma exacta y los caza,
  los dos a la vez cuando están en el mismo fichero, y en las tres formas de
  escribir la condición (`>`, `>=`, `!=`) — la forma no debe importar.
- **Se calla:** con los dos guards ya arreglados, con un `and`/`> 0` cuyo
  cuerpo afirma en vez de negar, con un guard que nunca dice `OK` (no puede
  dar falso verde por definición), y con una función que no es `guard_*`.
  Sin esta mitad, un auditor que gritara siempre aprobaría la prueba — misma
  lógica que la FAMILIA G de `test_adversarial.py`.
- **De punta a punta:** el script real, con sus códigos de salida (1 con bug,
  0 sin él), incluida la regresión del fallo de arriba.

Conectado dentro de `audit_project.py`, que pasa a ejecutar **21
comprobaciones** (contadas, no escritas a mano: de paso se quitó de
`EMPEZAR_AQUI.md` el recuento de auditores escrito a mano, que ya había
derivado —la tabla decía catorce y otra sesión hablaba del "15º"—, misma
trampa que el `21/21 OK` fijo de agosto). Todo lo demás en
verde: `test_motor_veredicto.py` 65/65, `test_adversarial.py` 112/112,
cobertura 26/26. Escáner de privacidad sin hallazgos.

---

## 27-08-2026 (sesión Cloud, vigesimoprimera entrada) — Auditados los otros tres guards dormidos: dos defectos más, y uno que NO se toca por ser decisión contable

Consecuencia directa de la entrada anterior: si `importe_atipico` llevaba dos
defectos de decisión invisibles por estar dormido, los otros tres guards
despertados estaban en la misma situación — su lógica nunca se había
ejercitado contra datos realistas, sólo contra tests unitarios con cachés
construidas a mano. Auditados los tres con el mismo método: leer, formular
hipótesis, medir con simulación **antes** de tocar nada.

### Defecto 3 — `estructura_reconocida` contaba dígitos

`_forma()` convertía cada dígito en una `D`, así que `FAC-99` daba `LLL-DD` y
`FAC-100` daba `LLL-DDD`: **formas distintas**. El primer número de factura
que cruzara un límite de dígitos (9→10, 99→100, 999→1000) salía `FALLO`
siendo perfectamente legítimo. Y numerar **sin ceros a la izquierda** es de
lo más común en el software de una pyme.

Medido por simulación (400 proveedores, compras irregulares, todas las
facturas legítimas por construcción):

| Numeración | FALLO antes | FALLO ahora |
|---|---|---|
| **sin** ceros a la izquierda (`FAC-100`) | **9,1%** | **0,0%** |
| con ceros a la izquierda (`FAC-00100`) | 0,0% | 0,0% |

Que las dos columnas se separaran así fue la prueba de la hipótesis: **todo
ese ruido venía de contar dígitos, no de detectar nada.** Arreglado: una
tirada de dígitos cuenta como una sola `D`. Las **letras no se colapsan** —
`FAC` y `FACTURA` son prefijos genuinamente distintos y ahí la longitud sí es
señal. Y no se pierde de vista la magnitud del número: de eso se ocupa el
guard de secuencia, que mira el valor, no la forma. Verificado que la
detección sigue viva: `77/XYZ` y `ALBARAN 12` sobre un histórico
`FAC-2026-00N` siguen dando `FALLO`.

### Defecto 4 — `secuencia_documental_proveedor`, la misma ceguera del `desv > 0`

Misma familia exacta que el defecto 1 de la entrada anterior, en otro guard:
la condición era `if salto_medio > 0 and dist_min > salto_medio * 20`. Si
todos los números previos son **iguales**, `salto_medio` es 0, la condición
previa no se cumple nunca y el guard caía al `return "OK"` final —
afirmando *"coherente con secuencia conocida"* sobre cualquier número.
Verificado antes de tocar nada: con previos `100` y `100`, un nº **999999**
devolvía `OK`.

Arreglado a `NO_COMPROBADO`, y **aquí no se pone un suelo** como en
`importe_atipico`: la escala de un número de factura es arbitraria (no existe
"el 5% de un número de serie"), así que inventar un umbral sería falsa
precisión. Se dice lo único que se puede sostener: sin variación previa no
hay secuencia con la que comparar.

Su umbral normal (20× el salto medio) se midió también: **~4%** de ruido
sobre secuencias legítimas con compras irregulares, antes y después. Está en
el mismo orden que el 4,6% que se aceptó para el 3σ, así que **no se toca**.

### El cuarto guard: `cuenta_gasto_coherente` NO tiene defecto — y por eso no se toca

Auditado igual, y el resultado es distinto: **no hay bug**. Sus dos ramas
`NO_APLICA` (sin histórico / sin cuenta propuesta) ya están declaradas y
ninguna devuelve `OK`. Medido:

| Proveedor | FALLO |
|---|---|
| de una sola actividad (el caso normal) | **0,0%** |
| que el 15% de las veces factura otra cosa | 14,7% |
| mixto al 50% (ferretería que además repara) | 47,0% |

**Ese 47% no es ruido: es el guard haciendo exactamente lo que dice.** Avisa
de que esta factura va a una cuenta distinta de la habitual, como `AMBAR
[CRITERIO]` — *"decide tú"*, no *"esto está mal"*. Cada aviso es
técnicamente cierto.

**Queda declarado, no arreglado, y a propósito:** si a un proveedor
legítimamente mixto conviene preguntarle cada vez, o si "habitual" debería
admitir **varios** grupos establecidos (los que superen
`MIN_ASIENTOS_PATRON_GASTO`, la constante que ya existe), **es una decisión
contable de Diego, no técnica.** La cuenta de gasto tiene consecuencias
fiscales; que el motor pregunte de más puede ser justo lo que se quiere. No
se toca sin esa respuesta.

### Verificación

7 comprobaciones nuevas en `test_motor_veredicto.py` (**65/65**), incluidas
las que impiden sobrecorregir (una forma realmente distinta y un prefijo de
letras distinto siguen dando `FALLO`; con secuencia real el guard sigue
distinguiendo en los dos sentidos). Probado con sabotaje —reintroducidos los
dos defectos a la vez— y falla **exactamente en las 3 comprobaciones** que
dependen de ellos. `test_adversarial.py` 112/112, cobertura 26/26, barrido de
falsos verdes y ensayo end-to-end en verde. Escáner de privacidad sin
hallazgos.

### El patrón, ya con cuatro casos

De cinco guards auditados en dos entradas, **cuatro tenían un defecto de
decisión** que llevaba meses invisible, y ninguno se habría visto sin
despertarlos primero. Dos de los cuatro eran **la misma ceguera** (`desv > 0`
y `salto_medio > 0`: una condición previa pensada para evitar dividir por
cero que, de paso, convertía la ausencia de dispersión en un `OK`
afirmativo). Merece quedar escrito como forma a buscar: **una condición
`if x > 0 and <comprobacion>` seguida de `return "OK"` es un falso verde
esperando** — el caso sin dispersión no es "todo correcto", es "no he podido
comprobar nada".

---

## 🔴 27-08-2026 (sesión Cloud, vigésima entrada) — `importe_atipico` tenía DOS defectos opuestos, invisibles porque el guard estaba dormido. Uno era un falso verde de manual

Al comprobar las **costuras** del arreglo anterior —los cuatro guards ya
pueden disparar, así que por primera vez importaba *cómo* deciden— aparecieron
dos defectos en `guard_importe_atipico`, en direcciones contrarias. Los dos
llevaban ahí desde siempre; ninguno se había visto nunca porque el guard
estaba estructuralmente dormido en las dos mediciones con corpus real.

**Cómo apareció, y merece anotarse:** no se buscaba esto. Se estaba
verificando si `cola_revision.py` sabía traducir los guards recién
despertados (sí sabía, sin hueco) y si `causas_de()` parseaba su motivo (sí).
En esa comprobación, una factura de prueba con **10 veces** el importe
habitual no aparecía en el motivo. El guard había dicho OK.

### Defecto 1 — falso verde afirmativo sobre el patrón más predecible que existe

La condición era `if desv > 0 and abs(total - media) > desv`. Un proveedor de
**cuota fija** (alquiler, iguala, suscripción, cuota de mantenimiento) tiene
desviación típica **exactamente cero**, así que la condición previa nunca se
cumplía y el guard caía al `return "OK"` final.

Verificado antes de tocar nada, con el guard real:

```
cuota fija 121,00 x4  ->  llega 1.210,00  (10x)   -> OK, "dentro de patron"
cuota fija 121,00 x4  ->  llega 99.999,00 (825x)  -> OK, "dentro de patron"
```

No `NO_COMPROBADO`: un **VERDE afirmativo** sobre algo que no había
comprobado. Es exactamente el falso verde que este motor existe para evitar,
y precisamente en el patrón más regular y más fácil de auditar que hay en una
contabilidad.

### Defecto 2 — el umbral era 1σ, que no es un umbral de atipicidad

`abs(total - media) > desv` es **una** desviación típica. Por definición, ~32%
de las observaciones de una normal caen fuera de 1σ. Medido por simulación
sobre facturas **legítimas** (misma distribución que su propio histórico,
ninguna anómala por construcción), 400 proveedores × 12 facturas:

| Umbral | Facturas legítimas marcadas FALLO |
|---|---|
| **1σ (el que había)** | **40,8%** |
| 2σ | 12,7% |
| 3σ | 4,6% |

**Este defecto habría envenenado la re-medición pendiente.** Si Diego hubiera
ejecutado `retro_semaforo.py` con el arreglo de las cachés pero con 1σ, el
ÁMBAR se habría disparado por ruido puro y la conclusión natural habría sido
"el arreglo empeoró el motor" — cuando el problema era el umbral. Encontrado
antes de que eso pasara.

### El arreglo: un suelo de dispersión resuelve los dos a la vez

`SIGMAS_IMPORTE_ATIPICO = 3` (convención estándar de detección de atípicos, y
el 4,6% medido arriba) y `SUELO_DISPERSION_RELATIVA = 0.05`: la desviación
efectiva es `max(desv, media × 5%)`, así que **nunca es cero** — siempre hay
vara de medir— y de paso protege del caso simétrico (desviación minúscula
pero no nula, que con 3σ a secas sería igual de hipersensible). Las dos
constantes son explícitas y con su porqué escrito, no números escondidos en
una condición.

Comportamiento resultante, validado antes de escribir el código:

| Histórico | Llega | Antes | Ahora |
|---|---|---|---|
| Cuota fija 121,00 | 121,50 (subida de precio) | OK | **OK** — no es anomalía |
| Cuota fija 121,00 | 1.210,00 (10x) | **OK** ← falso verde | **FALLO** |
| Cuota fija 121,00 | 99.999,00 (825x) | **OK** ← falso verde | **FALLO** |
| media 121,00 desv 2,07 | 124,00 (+2,5%) | **FALLO** ← ruido | **OK** |
| media 121,00 desv 2,07 | 1.210,00 (10x) | FALLO | **FALLO** |

Ruido sobre facturas legítimas con el diseño nuevo: **3,3%**, frente al 40,8%
de antes. Se ha quitado ruido sin perder detección.

### Verificación

7 comprobaciones nuevas en `test_motor_veredicto.py` (**58/58**), incluidos
los dos controles que impiden sobrecorregir: sin histórico sigue siendo
`NO_COMPROBADO`, y con media 0 (sin escala) tampoco se finge un OK. Probado
con sabotaje —reintroducida la condición `desv > 0` con umbral 1σ— y falla
**exactamente en las 3 comprobaciones** que dependen del arreglo, ninguna
más. `test_adversarial.py` 112/112, cobertura de guards 26/26, barrido de
falsos verdes en verde, `ensayo_retro_semaforo.py` (end-to-end) en verde.
Escáner de privacidad sin hallazgos.

### La lección, que no es nueva en este proyecto

Un guard **cableado y con test propio en verde** puede llevar meses siendo
incapaz de hacer su trabajo. Aquí se juntaron las dos formas: primero estaba
dormido (cache vacía), y cuando por fin despertó resultó que además decidía
mal en las dos direcciones. Es la misma familia que `guard_cuenta_gasto_
coherente` (21-08: cableado, con test, y no comparaba nada) y que el escáner
de privacidad que decía "sin hallazgos" sobre un fichero que no había leído.
**Y esta vez apareció mirando la costura de un arreglo anterior, no buscándolo
de frente** — que es justo donde este proyecto lleva encontrándolos todo el
mes.

---

## 27-08-2026 (sesión Cloud, decimonovena entrada) — El cuarto candidato, resuelto: mapeo por cliente, con la contaminación cruzada demostrada antes de confiar en el diseño

Cierra la entrada anterior. Diego, sin poder volver al PC, pidió seguir
avanzando con lo que estuviera en la mano. Se retomó `guard_cuenta_gasto_
coherente` — declarado ayer como "más difícil, no arreglado" — para ver si
el riesgo identificado (mezclar clientes bajo el mismo código de cuenta)
tenía una solución ya probada dentro del propio proyecto, en vez de inventar
una nueva.

### El diseño ya existía — solo había que replicarlo con el ámbito correcto

`orquestador.py` ya construye `mapeo_cuenta_gasto` desde `--diario` **por
cliente**, de una sola pasada (un cliente por ejecución). Es exactamente el
ámbito correcto para una clave que no es identidad estable entre clientes
(`FASE0_RESULTADOS.md` §10.1). `retro_semaforo.py` procesa varios clientes
en una sola pasada, así que hacía falta la misma idea pero incremental y con
reseteo explícito al cambiar de cliente — no una decisión nueva, una
extensión del patrón ya validado.

**Verificado antes de dar por bueno que `dats.sort()` agrupa por cliente**:
los contenedores se ordenan por ruta completa, así que los ficheros de una
misma carpeta quedan contiguos — comparar `os.path.dirname(ruta)` contra el
del contenedor anterior basta para saber cuándo tocaba resetear.

### Lo construido

- `reconstruir_compra()`: ahora copia `cuenta_proveedor` (acreedor) y
  `cuenta_debe` (gasto) a la `fila` — la información ya estaba en `gastos`/
  `acree`, solo se descartaba antes de llegar al motor.
- `actualizar_mapeo_cuenta_gasto()` (nueva, en `motor_veredicto.py`, junto a
  `construir_mapeo_cuenta_gasto()` que es su versión de lote): incremental,
  misma disciplina de "solo lo anterior" que las tres cachés de ayer.
- En `retro_semaforo.py`: `mapeo_cuenta_gasto_cliente` se **resetea a `{}`**
  cada vez que el contenedor entra en una carpeta de cliente distinta —
  nunca se acumula globalmente para todo el corpus, a diferencia de las tres
  cachés (que sí son seguras de acumular por NIF, identidad estable entre
  clientes).

### Verificación — con el riesgo real demostrado, no solo evitado de palabra

`test_motor_veredicto.py` (51/51, 6 comprobaciones nuevas): construido un
caso con dos "clientes" sintéticos que comparten el mismo código de cuenta
`400015` — cliente A paga siempre a `621000`, cliente B siempre a `600000`.
**Con el mapeo reseteado**, una factura de B coherente con su propio patrón
da `OK`. **Sin resetear** (reconstruido a propósito, no una copia superficial
que habría compartido el diccionario y corrompido las comprobaciones de
arriba — encontrado y corregido antes de ejecutar nada): esa misma factura
de B, perfectamente coherente con su propio historial, **sale `FALLO`** por
comparar contra el patrón mezclado con el de A. El error de diseño que el
reseteo evita no es silencio — es acusar a la factura correcta por un motivo
que no es suyo.

`test_adversarial.py` 112/112 sin cambios. `ensayo_retro_semaforo.py`
(end-to-end completo, vía `audit_project.py`) sigue en verde tras el cambio.
Escáner de privacidad sin hallazgos.

### Con esto, los cuatro candidatos de la última auditoría quedan cerrados

Los tres del hallazgo original (`importe_atipico`, `estructura_reconocida`,
`secuencia_documental_proveedor`) y este cuarto (`cuenta_gasto_coherente`)
tienen su arreglo escrito, probado y documentado. **Ninguno puede afectar al
ROJO** (ninguno está en `criticos`) — solo pueden mover VERDE hacia AMBAR.
Sigue pendiente lo mismo de ayer, sin cambios: Diego vuelve a ejecutar
`retro_semaforo.py` contra el corpus real cuando esté en el PC, y compara el
VERDE/AMBAR nuevo contra el 87,71%/9,26% ya citado.

---

## 27-08-2026 (sesión Cloud, decimoctava entrada) — Cuarto candidato encontrado (`cuenta_gasto_coherente`), verificado como MÁS DIFÍCIL, no arreglado a propósito

Diego no puede volver a ejecutar `retro_semaforo.py` hoy (no está en el PC).
En vez de esperar sin hacer nada, se buscó sistemáticamente si el mismo
patrón de la entrada anterior (una caché declarada, nunca rellenada por los
dos scripts de medición) se repite en otro guard — dado que ya se demostró
real una vez, valía la pena comprobar el resto antes de darlo por un caso
aislado.

### Encontrado: `guard_cuenta_gasto_coherente` está en la misma situación estructural

Está en `AMBAR_DEDICADOS` (puede mover VERDE→AMBAR igual que los tres
anteriores) y nunca puede devolver `FALLO` con lo que le llega hoy desde
`retro_semaforo.py` ni `validar_captura_historica.py` — dormido en las dos
mediciones reales, mismo síntoma.

**Pero el diagnóstico completo revela tres huecos, no uno:** `fila['cuenta_
proveedor']` y `fila['cuenta_debe']` nunca se copian desde las líneas del
asiento a la `fila` que ve el motor (la información SÍ está en `gastos`/
`acree` dentro de `reconstruir_compra()`, solo se descarta antes de llegar
al motor), y `mapeo_cuenta_gasto` nunca se pasa, igual que las tres caches
ya arregladas.

### Por qué NO se arregla igual — verificado antes de tocar nada

`construir_mapeo_cuenta_gasto()` indexa por **código de cuenta** (`400015`),
no por NIF. Y `FASE0_RESULTADOS.md` §10.1 ya demostró, con el corpus real,
que **el código de cuenta no es una identidad estable entre clientes**: el
mismo proveedor puede ser `400001` en una copia y `400035` en otra, y el
mismo código puede ser dos proveedores distintos en dos clientes. `retro_
semaforo.py` acumula `maestro_acumulado` en un único diccionario para **todo
el corpus, todos los clientes juntos** (verificado: se inicializa una sola
vez, fuera de cualquier bucle por cliente). Acumular `mapeo_cuenta_gasto` de
la misma forma, con la misma clave, mezclaría cuentas de clientes distintos
bajo la misma clave — un histórico falso, no uno real. Sería un arreglo que
rompe algo peor de lo que arregla, y no se ha hecho.

### Queda declarado, no arreglado — con la pregunta de diseño exacta

No es una decisión mecánica: hay que decidir si `mapeo_cuenta_gasto` se
acumula **por cliente** (una tabla distinta por copia, reiniciada en cada
`c` del bucle de `dats`) o si el guard necesita cambiar su clave de "código
de cuenta" a NIF — un cambio de firma, no solo de llamada. Ninguna de las
dos se ha decidido ni implementado. Copiar `cuenta_proveedor`/`cuenta_debe`
a `fila` en `reconstruir_compra()` es mecánico y de bajo riesgo por
separado, pero no aporta nada sin resolver antes la pregunta del mapeo.

**No se ha tocado ningún código para este hallazgo.** Solo diagnóstico,
verificado leyendo `guard_cuenta_gasto_coherente()`, `construir_mapeo_
cuenta_gasto()`, `reconstruir_compra()` y la firma interna de `evaluar_
fila_v4()` en la llamada real al guard (línea 1319 de `motor_veredicto.py`).

---

## 27-08-2026 (sesión Cloud, decimoséptima entrada) — Hallazgo de Diego, verificado: las tres caches de historial nunca se acumulaban en las dos mediciones con corpus real

Diego encontró algo que va más allá de un detalle de estilo, con el mismo
rigor que exige el motor, y pidió verificarlo antes de tocar nada. Se
verificó leyendo el código, no de palabra, y el hallazgo es real.

### El hallazgo, confirmado

`evaluar_fila_v4()` recibe tres cachés — `historico_proveedor`, `formato_cache`,
`secuencia_cache` — que alimentan `guard_importe_atipico`,
`guard_estructura_reconocida` y `guard_secuencia_documental_proveedor`.
Tanto `retro_semaforo.py` (el 87,71% VERDE / 3,03% ROJO ya citado en todo el
proyecto, §14 de `FASE0_RESULTADOS.md`) como `validar_captura_historica.py`
pasaban `{}, {}, {}` en **cada** factura, sin acumular nada entre ellas — a
diferencia del maestro de proveedores, que sí se acumula desde el arreglo
del 21-08. Confirmado leyendo las dos llamadas exactas en cada script.

**Con la caché vacía, los tres guards son estructuralmente incapaces de
devolver `FALLO`** (verificado leyendo cada uno): `guard_importe_atipico`
necesita `n≥3` facturas previas para siquiera comparar; `guard_estructura_
reconocida` y `guard_secuencia_documental_proveedor` necesitan una entrada
previa que, con la caché vacía, nunca existe — devuelven `NO_APLICA`
("primera vez que veo a este proveedor"), nunca `FALLO`. El motor los
degrada correctamente (nunca fuerza un OK falso — el diseño de
`NO_APLICA`/`NO_COMPROBADO` está bien hecho), pero el resultado práctico es
que **los tres han estado dormidos en las dos únicas mediciones con corpus
real que tiene este proyecto**.

### Precisión importante, verificada antes de alarmar de más

Diego preguntó si esto invalidaba el `ROJO 3,03% < 5%` ya cerrado. Respuesta,
verificada en `calcular_veredicto_v4()`: **no puede afectar al ROJO.**
Ninguno de los tres guards está en la lista `criticos` que decide ROJO — solo
aparecen en `AMBAR_DEDICADOS`. Con las cachés activas, lo único que estos
tres guards pueden hacer es mover una factura de **VERDE a ÁMBAR**, nunca a
ROJO. El umbral que cerró el retro-semáforo (`SIGUIENTES_PASOS.md` §4) sigue
siendo válido tal cual está escrito.

Lo que sí queda abierto, y no se afirma sin medirlo: **el 87,71% VERDE
probablemente esté sobreestimado** — un número no medible desde aquí sin
volver a correr `retro_semaforo.py` contra el corpus real, ya con el arreglo.

### El arreglo, no trivial por la fuga de datos que evita

Reutilizar `orquestador.py::construir_historico_y_secuencia()` tal cual
habría sido más rápido y **incorrecto**: esa función construye de golpe con
el lote entero, así que cada factura se compararía contra una media que la
incluye a ella misma y a facturas futuras — exactamente la fuga que
`retro_semaforo.py` ya identificó y corrigió para el maestro el 21-08 ("el
histórico de una factura son solo los datos anteriores a ella").

Construida `actualizar_caches_historicas()` (nueva, en `motor_veredicto.py`,
junto a `_entrada_de_proveedor()` que es su inversa): se llama **después**
de evaluar cada fila, nunca antes, y crece de la misma forma incremental que
ya usa `maestro_acumulado`. Cableada en los dos scripts, en el mismo punto
(`finally`) donde ya se acumulaba el maestro.

### Verificación, con el antes y el después lado a lado sobre el mismo caso

Nueva sección en `test_motor_veredicto.py` (45/45 en total, 6 comprobaciones
nuevas): reproduce el patrón exacto de los dos scripts (caché vacía en cada
vuelta) sobre una factura con un importe 10 veces el habitual de un
proveedor con historial limpio — **da VERDE**, el bug real, reproducido, no
supuesto. Con el arreglo, la misma factura exacta, mismo caso: `guard_
importe_atipico` devuelve `FALLO` y el veredicto es AMBAR. Segundo caso
aislado para `guard_estructura_reconocida` (número de documento con forma
nunca vista): mismo patrón, mismo resultado. `secuencia_documental_
proveedor` no se aísla en un tercer caso porque comparte la misma línea de
`actualizar_caches_historicas()` que ya prueban los dos casos de arriba, y
su lógica propia ya tenía cobertura unitaria en la FAMILIA O de
`test_adversarial.py`.

`test_adversarial.py` 112/112 sin cambios (no toca ningún guard existente,
solo añade la función que les da de comer). `ensayo_retro_semaforo.py`
(el ensayo end-to-end completo, vía `audit_project.py`) sigue en verde tras
el cambio. Escáner de privacidad sobre los cuatro ficheros tocados sin
hallazgos.

### Pendiente, y es de Diego, en local

Volver a ejecutar `retro_semaforo.py` contra el corpus real (`--inyectar`
incluido, para ver también si la tasa de detección cambia) y comparar el
nuevo VERDE/ÁMBAR/ROJO contra el 87,71%/9,26%/3,03% ya citado. Si el ROJO se
mueve de verdad, sería una señal de que algo más está pasando (no debería,
según lo verificado arriba) y merece investigarse aparte. Si solo se mueve
el ÁMBAR, es exactamente lo esperado: unas pocas facturas que antes pasaban
sin que nadie las mirara ahora piden revisión humana, que es lo que estos
tres guards existen para hacer.

---

## 27-08-2026 (sesión Cloud, decimosexta entrada) — Confirmado con datos reales: SOSPECHOSA es el artefacto de continuidad temporal, no mezcla real. `consolidar_identidad.py` ya se calibra sola

Cierra la entrada anterior. Diego ejecutó `diag_calibracion_sospechosa.py`
contra el corpus completo (3.857 contenedores, 28 carpetas analizadas):

| | |
|---|---|
| Suena a equipo/copia Y sospechosa | 24 carpetas, media 26,6 grupos |
| Suena a equipo/copia Y sana | 0 carpetas |
| NO suena a equipo/copia Y sospechosa | **3 carpetas, media 24,7 grupos** |
| NO suena a equipo/copia Y sana | 0 carpetas |

**Tasa de sospechosas: 100% entre las que suenan a equipo, 100% TAMBIÉN
entre las que no.** Es exactamente el patrón que el propio script marca como
diagnóstico en su "cómo se lee": *"si las dos tasas son parecidas -sobre
todo si la segunda también es alta-, SOSPECHOSA no distingue nada por sí
sola."* Gana la hipótesis A (artefacto de continuidad temporal) sobre la B
(mezcla real): si fuera real, las carpetas con nombre de cliente concreto
deberían salir sanas casi siempre, y no es así ni una vez.

**Conclusión operativa, sin ambigüedad:** la marca SOSPECHOSA de
`diag_carpetas_multiempresa.py`, tal como está construida hoy (Jaccard de
proveedores entre códigos de una misma carpeta), no sirve para priorizar
revisión en este corpus. No es un defecto de la implementación de hoy — es
la confirmación a escala real de lo que la tercera entrada ya había
reproducido con datos sintéticos ("sin continuidad temporal entre copias,
hasta la misma empresa parece no coincidir consigo misma").

### `calcular_contingencia()` ahora devuelve un veredicto, no solo números

`diag_calibracion_sospechosa.py` se amplió con `informativa` (True/False/
None, umbral: tasa entre las que NO suenan a equipo < 50%) y
`consolidar_identidad.py` lo llama en cada ejecución. Si sale **NO
INFORMATIVA** (el caso de hoy), la marca SOSPECHOSA se sigue mostrando en
`consolidado_LOCAL.txt` -- ninguna información se descarta -- pero deja de
competir por prioridad con una DISCREPANCIA real o con la confianza normal
del nombre. Cada aviso lleva el sufijo `[NO INFORMATIVA en este corpus, no
usada para priorizar]` para que quede explícito, no implícito.

Tres estados posibles, y los tres se prueban: INFORMATIVA (la señal sí
distingue), NO INFORMATIVA (satura los dos lados, el caso real de hoy) y
NO_COMPROBADO (sin carpetas de nombre "cliente concreto" con las que
contrastar -- nunca se finge un veredicto que no se puede sostener, misma
disciplina que `motor_veredicto.py`).

### Verificación

`ensayo_diag_calibracion_sospechosa.py` reescrito con los tres escenarios
(incluido uno que reproduce el resultado real de hoy con datos sintéticos:
saturado en los dos lados). `ensayo_consolidar_identidad.py` ampliado con un
segundo corpus sintético para probar las dos ramas de la calibración en la
priorización real del fichero de salida -- con NO INFORMATIVA, una carpeta
sin ningún aviso pero de confianza alta queda ANTES que una sospechosa en la
cola de revisión; con INFORMATIVA, es al revés. Los 12 `ensayo_*.py` del
repositorio en verde, `test_motor_veredicto.py` 39/39, `test_adversarial.py`
112/112, `test_privacidad.py` 30/30, escáner de privacidad sobre el
repositorio completo sin hallazgos.

### Lo que queda para más adelante, sin bloquear nada de hoy

Arreglar de raíz `diag_carpetas_multiempresa.py` (que la técnica tenga en
cuenta la ventana temporal de cada código, no solo el solape bruto de
proveedores) es un trabajo aparte, no trivial, y no se acomete hoy sin que
haya un caso concreto que lo pida -- la calibración automática ya evita el
daño práctico (que la marca engañe la prioridad de revisión) mientras tanto.
La marca DISCREPANCIA no tiene este problema: usa el mismo Jaccard pero en
dirección conservadora (exige similitud ALTA para fusionar entre carpetas
distintas), así que el mismo artefacto la haría fallar en detectar
fragmentación real, no inventar discrepancias.

---

## 27-08-2026 (sesión Cloud, decimoquinta entrada) — Diego ejecutó `consolidar_identidad.py` contra el corpus real: 27 de 27 carpetas "SOSPECHOSA" (100%) — cifra que no se acepta sin comprobar, y coincide con un fallo ya documentado

Primera ejecución real de `consolidar_identidad.py` (entrada anterior),
contra el corpus completo: **37 carpetas de ContaPlus, 140 de Documentos, 27
en grupo multi-carpeta, 21 con discrepancia de nombre, 27 SOSPECHOSAS de
mezclar empresas, 9 sin ningún aviso.**

**El 27 de sospechosas no se dio por bueno.** Coincide casi al dígito con el
"27 de 28" que `diag_carpetas_multiempresa.py` ya documenta en su propia
cabecera como un resultado "imposible" (implicaría cientos de empresas
ocultas en una cartera de ~33), causado entonces por códigos con pocos
proveedores ("delgados"). Diego ejecutó el script directamente para
comprobarlo: **el diagnóstico de códigos delgados NO explica esto hoy** —
solo 78 de 958 códigos (8%) son delgados; el 72% tiene 10+ proveedores. Con
el filtro de difusión ya activo (heredado del 27-08) y códigos ricos en
proveedores, el resultado sigue siendo **27 de 27 (100%)**, un salto de
imposibilidad todavía mayor que el original.

### Dos hipótesis igual de plausibles, ninguna aceptada sin dato

**A) Artefacto de continuidad temporal**, ya reproducido con datos
sintéticos en la tercera entrada de hoy: *"una sola empresa real, con sus
códigos viendo cada uno una muestra aleatoria de un pool de proveedores,
salió como 29 grupos... sin continuidad temporal entre copias, hasta la
misma empresa parece no coincidir consigo misma."* Si una empresa trata con
200 proveedores a lo largo de los años pero cada copia registra solo 20-30,
dos copias de la MISMA empresa pueden solapar poco por pura estadística.

**B) Real**: el corpus ya tiene un caso confirmado a mano ("Contabilidad
ordenador de Jose") de carpetas organizadas por EQUIPO/COPIA en vez de por
cliente. Si eso es la norma y no la excepción en estas 27-28 carpetas, un
100% de sospechosas sería correcto, no un fallo de medición.

### `diag_calibracion_sospechosa.py` (nuevo): distingue las dos sin que nadie mire un nombre todavía

Cruza la señal SOSPECHOSA contra la pista de nombre que ya usa
`cuadre_303_ficha.py` (`suena_a_equipo`: contiene "ordenador", "copia",
"backup", "pc0/1/2"...). Si sospechosa correlaciona con nombres de
equipo/copia, gana la hipótesis B. Si sale sospechosa por igual entre
carpetas con nombre de equipo y con nombre de cliente concreto, es la A —y
la señal SOSPECHOSA no es fiable tal cual está hoy. Por consola solo sale
una tabla de contingencia de 4 números y dos porcentajes, nunca un nombre:
Diego puede pegar la salida completa en el chat sin ningún problema.

`ensayo_diag_calibracion_sospechosa.py` (nuevo) fija en código que, con
datos donde la hipótesis B es cierta por construcción (2 carpetas de
"equipo" mezclando de verdad, 2 de "cliente" sanas), la tabla lo detecta al
100%/0% exacto. En verde. `test_motor_veredicto.py` 39/39,
`test_adversarial.py` 112/112, escáner de privacidad sin hallazgos.

### Pendiente, y decide qué hacer con `consolidar_identidad.py` mientras tanto

```bash
python diag_calibracion_sospechosa.py "C:\Users\SERVILAB\Desktop\100% contabilidad"
```

Hasta tener este resultado, la recomendación es **no fiarse todavía** de la
marca SOSPECHOSA en `consolidado_LOCAL.txt` — puede estar sobre-marcando por
el artefacto A. La marca DISCREPANCIA (del cruce nombre↔proveedor entre
carpetas hermanas) es una historia distinta: usa el mismo Jaccard pero en
dirección conservadora (exige similitud ALTA para fusionar entre carpetas
distintas, nunca al revés), así que un fallo de continuidad temporal la haría
FALLAR EN DETECTAR fragmentación real, no inventar discrepancias — es mucho
menos sospechosa de dar falsos positivos que SOSPECHOSA.

---

## 27-08-2026 (sesión Cloud, decimocuarta entrada) — `consolidar_identidad.py`: cruza las tres señales de identidad cliente↔carpeta en una sola vista, sin resolver por estadística lo que ya se demostró que no se puede

Diego preguntó, tras el cierre de la tercera entrada de hoy (revisión humana
vía `cuadre_303_ficha.py --listar`, sin conjunto de referencia limpio en
ningún lado), si había una forma de aprovechar mejor los datos ya
disponibles. **Respuesta razonada, no un reintento del mismo enfoque:** la
conclusión de la tercera entrada sigue en pie —no hay estadística que
resuelva la identidad desde cero—, pero las tres señales que se construyeron
ese mismo día (similitud de nombre en `emparejar_carpetas.py`, agrupación por
proveedor en `enlazador_clientes_303.py`, homogeneidad interna en
`diag_carpetas_multiempresa.py`) nunca se habían cruzado entre sí. Cada una
vivía en su propio informe suelto.

### Qué añade, exactamente, que ninguna de las tres por separado tenía

Dos carpetas de ContaPlus con nombres **distintos** pueden agruparse como la
misma empresa real por proveedores compartidos (`enlazador_clientes_303.py`),
pero cada una, mirada solo por nombre, puede emparejar con una carpeta de
Documentos **distinta** y con alta confianza cada una. Ninguno de los dos
scripts por separado puede ver esa discrepancia, porque cada uno solo conoce
su propia señal. Igual de importante: si una carpeta de ContaPlus está
marcada como sospechosa de mezclar varias empresas reales
(`diag_carpetas_multiempresa.py`), cualquier emparejamiento por nombre que se
le proponga es sospechoso por construcción — puede que ni siquiera exista
"el cliente" singular al que emparejar.

### Diseño de tres roles, sin excepción ni una vez

`consolidar_identidad.py` **importa** las funciones ya escritas de los otros
tres scripts (nunca las duplica — mismo criterio que centralizó el patrón de
importes en `contrato_datos.py` el 26-08). Por consola solo salen recuentos.
El nombre real de cualquier carpeta vive únicamente en el fichero de salida,
que debe llevar `_LOCAL` en el nombre (mismo guardia que los otros tres). No
se leyó, no se imprimió y no se escribió ni un solo dato real en esta sesión.

**Cambio necesario en dos scripts existentes, sin tocar su comportamiento:**
`enlazador_clientes_303.py` y `diag_carpetas_multiempresa.py` solo imprimían
recuentos — nunca guardaban el nombre real de las carpetas en ningún sitio,
ni siquiera en un fichero `_LOCAL`, así que no había nada que cruzar. Los dos
se refactorizaron para exponer una función reutilizable
(`calcular_grupos()` / `calcular_sospechosas()`) y un `--detalle` opcional
que escribe el nombre real a un fichero `_LOCAL` **solo si se pide** — sin
`--detalle`, los dos se comportan exactamente igual que antes, verificado con
los ensayos nuevos de abajo.

### Verificación

Los dos scripts refactorizados **no tenían ningún ensayo propio en el
repositorio** pese a llevar dos arreglos reales cada uno (filtro de difusión,
segundo bug de `clave_cliente()`) — las "seis pruebas sintéticas" que
documenta la tercera entrada de hoy se corrieron a mano esa sesión y no
quedaron fijadas en código. Cerrado ese hueco de paso:

| Fichero | Qué fija en código |
|---|---|
| `ensayo_enlazador_clientes_303.py` (nuevo) | Dos carpetas con nombre distinto pero mismos proveedores se agrupan; una tercera sin solape no se contamina; el detalle solo lista grupos de 2+ carpetas |
| `ensayo_diag_carpetas_multiempresa.py` (nuevo) | Una carpeta con dos códigos sin solape de proveedores sale SOSPECHOSA; una con proveedores compartidos sale sana, sin falso positivo |
| `ensayo_consolidar_identidad.py` (nuevo) | El caso que importa: dos carpetas de nombre distinto, agrupadas por proveedor, con candidatos de nombre discrepantes → marcadas DISCREPANCIA; una carpeta mixta → SOSPECHOSA; una carpeta sana sin avisos → ningún ruido; por consola, ningún fragmento de los nombres inventados aparece nunca (comprobado carácter a carácter) |

Los tres ensayos nuevos en verde. Batería completa repetida tras el cambio:
`test_motor_veredicto.py` 39/39, `test_adversarial.py` 112/112,
`test_privacidad.py` 30/30, y los **11** `ensayo_*.py` del repositorio (los 8
de antes más los 3 nuevos) en verde — incluidos los que ya existían para
`emparejar_carpetas.py`, `retro_semaforo.py` y `reconstruir_303.py`, que no
cambiaron de comportamiento con este refactor. `audit_project.py`: 15/16
(la dependencia que falta es la excepción normal ya conocida, `anthropic`/
`google-genai`). Escáner de privacidad sobre el repositorio completo: sin
hallazgos.

**A propósito, sin cablear a `audit_project.py` todavía:** mismo criterio que
`numeracion_correlativa.py` y `comparar_esquema_dbf.py` — código nuevo de
hoy, sin haberse probado contra el corpus real, no se mezcla con el motor ya
estable y auditado 14 veces.

### Pendiente, y lo ejecuta Diego, no Claude (regla de tres roles)

```bash
python consolidar_identidad.py "C:\Users\SERVILAB\Desktop\100% contabilidad" "\\PC01\Documentos" --detalle consolidado_LOCAL.txt
```

El fichero de salida viene ordenado por prioridad de revisión: primero las
discrepancias y los avisos de mezcla, después por confianza del nombre (baja
primero). Si algo sale con `DISCREPANCIA`, compara los dos candidatos con
calma — puede ser un error de una de las dos señales, o puede ser real (la
misma empresa cambió de nombre comercial entre una copia y otra). Ninguna
marca de este fichero decide nada por sí sola.

---

## 27-08-2026 (sesión Cloud, decimotercera entrada) — `comparar_esquema_dbf.py` ejecutado de verdad, y una fecha nueva: migración a ContaSOL/FactuSOL a principios de 2027

Diego consiguió instalar Python en un segundo equipo (no es el que documenta
`EMPEZAR_AQUI.md` §0) y ejecutó `comparar_esquema_dbf.py` contra un `.dbf`
real de un **segundo cliente** (distinto del "cliente piloto" original).
Resultado: **IDÉNTICO** al layout de ContaPlus ya verificado — 98 campos,
mismo orden, mismos anchos.

### Lo que este resultado SÍ demuestra, y lo que no

Antes de anotarlo como un cierre, se preguntó explícitamente de dónde salía
el fichero — la disciplina de no dar nada por bueno sin comprobar el origen,
no solo el contenido. Respuesta de Diego: **es de ContaPlus, el sistema que
se usa actualmente.** No es una exportación de ContaSOL.

- ✅ **Sí demuestra algo real y nuevo:** el layout de `CAMPOS`
  (`layout_diario_contaplus.py`) ya no está verificado contra un solo
  cliente ("cliente piloto") sino contra **dos clientes reales distintos**,
  con resultado idéntico — el layout es estable entre empresas, no una
  coincidencia de un caso. Es una confirmación genuina, aunque no sea la que
  se buscaba.
- ❌ **No demuestra nada sobre ContaSOL.** Un fichero de ContaPlus tiene el
  layout de ContaPlus porque ese layout se derivó precisamente de ahí — es
  circular, no una prueba. La pregunta de si ContaSOL usa el mismo layout
  **sigue abierta**, exactamente como quedó en la entrada anterior.

### El dato nuevo que sí cambia la prioridad: la fecha de migración

Diego confirma: el despacho **migrará a ContaSOL y FactuSOL a principios de
2027** (no hay fecha exacta más allá de eso). Esto no estaba anotado en
ningún sitio del proyecto hasta hoy, y cambia dos cosas:

1. **La verificación de ContaSOL deja de ser urgente, sin dejar de ser
   necesaria.** No hay forma de conseguir un `.dbf` real de ContaSOL antes
   de que exista una instalación de ContaSOL en marcha — eso no pasará hasta
   la migración. `comparar_esquema_dbf.py` queda preparado y probado
   (12/12, sabotaje incluido, y ahora también probado de extremo a extremo
   contra un `.dbf` real aunque fuera el sistema equivocado) para el día que
   sí haya un fichero real que comparar.
2. **El módulo de facturas EMITIDAS** (`numeracion_correlativa.py`, entrada
   novena de hoy) gana contexto: FactuSOL no es una opción entre varias para
   exportar, es **el sistema que va a usarse de verdad** a partir de esa
   fecha. La plantilla vacía de importación de FactuSOL sigue siendo el
   bloqueante pendiente de Diego (`Utilidades > Ficheros XLS`).

**Nada de esto cambia lo que se usa hoy:** ContaPlus sigue siendo el sistema
en producción, y `escribir_xdiario()` sigue siendo la exportación real y
verificada mientras dure.

---

## 27-08-2026 (sesión Cloud, duodécima entrada) — `comparar_esquema_dbf.py`: la herramienta segura para lo que el incidente anterior intentaba hacer mal

Tras el incidente de la entrada anterior, se construyó la vía correcta para
responder la pregunta original (¿tiene ContaSOL el mismo layout de `.dbf`
que ContaPlus?) sin que ningún dato real tenga que acercarse nunca a Cloud.

**Reutiliza, no reinventa:** `leer_cabecera()` ya existía en
`fase0_esquema_dbf.py`, construida y verificada en la Fase 0 para leer
**solo la cabecera** de un `.dbf` — nombres de campo, tipos, anchos, número
de registros — y pararse ahí, con un tope duro de 65535 bytes, sin tocar
jamás la zona de filas. Una cabecera dBase no contiene ningún dato de
cliente: es la definición de estructura, el mismo tipo de información que
ya vive en el propio `CAMPOS` de `layout_diario_contaplus.py`.

`comparar_esquema_dbf.py` (nuevo) abre esa misma función contra un `.dbf`
**suelto** (no dentro de un ZIP/.DAT, a diferencia del uso original en
Fase 0) y compara el resultado campo a campo contra el layout ya verificado
de ContaPlus. La salida son solo nombres de campo técnicos y números — es
segura de pegar entera en el chat, a diferencia de cualquier fichero
original.

`test_comparar_esquema_dbf.py`: 12/12 en verde, con cabeceras dBase
construidas a mano (cero filas, cero datos) para los tres casos que
importan — esquema idéntico, un campo con distinto ancho, un campo de
menos. Probado con sabotaje (la comparación forzada a decir siempre
"idéntico"): el ensayo lo detecta y revienta con fuerza, más visible
todavía que un simple fallo. `test_motor_veredicto.py` 39/39,
`test_adversarial.py` 112/112 sin cambios. Escáner de privacidad sin
hallazgos.

**Siguiente paso real, de Diego, sin ningún dato de cliente:**

```bash
python comparar_esquema_dbf.py "ruta\al\fichero_diario.dbf"
```

Si dice **IDÉNTICO**, el `xDiario.txt` que ya genera este proyecto sirve
para ContaSOL sin cambios. Si dice **DIFERENTE**, señala exactamente qué
campo difiere y en qué — no hay que adivinar nada ni traer el fichero
completo a ningún sitio para saberlo. Complementa, no sustituye, la
comprobación pendiente de la entrada del "paso final a ContaPlus/ContaSOL"
(importar un xDiario sintético en una empresa de pruebas): esta herramienta
responde si el **layout de entrada** coincide; esa otra prueba responde si
la **importación** funciona de verdad.

---

## 🔴 27-08-2026 (sesión Cloud, undécima entrada) — INCIDENTE: 4 ficheros reales subidos a Cloud, expuestos pese a pedir que no se leyeran

Al intentar avanzar la verificación de ContaSOL (entrada anterior), Diego
adjuntó 4 ficheros reales del corpus (subcuentas y diario de un cliente,
en `.txt` ASCII y `.dbf`) a esta conversación **Cloud**, con la instrucción
explícita "no los leas, dime cómo los anonimizo". **La instrucción no
bastó**: el propio mecanismo de la plataforma que procesa los adjuntos
`@archivo` muestra su contenido en el turno **antes** de que Claude pueda
actuar sobre la petición del usuario — no es una decisión de la sesión, es
el orden en que el sistema entrega el contexto. Dos de los cuatro ficheros
(los de subcuentas) se mostraron completos.

**Qué se expuso, sin repetirlo aquí:** razón social y CIF real de una
veintena de proveedores/acreedores de un cliente, y el nombre y NIF real de
una persona física (una cuenta de acreedor, no una sociedad). Sesión Cloud,
sin `ANTHROPIC_API_KEY` ni DPA — exactamente el escenario que
`.claude/rules/datos.md` lleva un mes documentando como línea que nunca
debe cruzarse. Se cruzó, por un mecanismo de plataforma, no por una decisión
tomada aquí.

**Contención, en el momento, antes de continuar con nada más:**
1. Ningún dato del contenido se usó, repitió, ni sirvió de base para
   construir nada — la sesión se detuvo ahí explícitamente.
2. Confirmado que nada tocó el repositorio git: los 4 ficheros vivían en
   un directorio de subida temporal del contenedor, fuera de
   `/home/user/Os-Asesor-a`, nunca en la ruta del proyecto.
3. Los 4 ficheros **borrados del contenedor** tras confirmar con Diego.
4. La copia original de Diego, en su propia máquina, no se ha tocado en
   ningún momento — esto es solo sobre lo que llegó a esta sesión Cloud.

**La lección, para que no se repita — y es nueva, no una repetición de la
regla del `.zip`/`.DAT`:** hasta hoy, la barrera de datos de este proyecto
asumía que "no leer un archivo" era una decisión que Claude podía tomar
dentro de la conversación. **No lo es, cuando el archivo llega como adjunto
a un mensaje**: el contenido se entrega en el mismo turno, antes de que
haya ocasión de decidir nada. La barrera real tiene que estar **antes** de
adjuntar el archivo, no después.

**Regla nueva, añadida a `.claude/rules/datos.md`:** ningún fichero con
datos reales de cliente se adjunta a una conversación Cloud, bajo ninguna
circunstancia, ni siquiera con instrucciones de "no lo leas" — la
anonimización o extracción de estructura tiene que ocurrir **antes**, con
un script que Diego ejecuta en su máquina (mismo diseño de tres roles ya
usado en toda la Fase 0: Claude escribe el script sin ver datos, Diego lo
ejecuta, solo la salida ya segura sale de su máquina).

---

## 27-08-2026 (sesión Cloud, décima entrada del día) — El paso final a ContaPlus/ContaSOL: una afirmación sin comprobar, corregida antes de construir nada nuevo

Diego pidió trabajar el último tramo del motor: exportar los asientos
validados a ContaPlus **y** ContaSOL. Antes de escribir código nuevo, se
revisó lo que ya existe (`layout_diario_contaplus.py`, `escribir_xdiario()`,
construido y auditado desde el 20/21-08) — y apareció algo que corregir
antes de construir nada más.

### No es una decisión reabierta

`PROJECT_STATUS.md` tiene una decisión cerrada: *"Alojamiento CONTASOL (API
en tiempo real): descartado por ahora, no es el cuello de botella."* **Eso
sigue en pie y no se toca.** Es una decisión sobre una integración API en
vivo. Lo de hoy es un fichero de exportación por lotes (`xDiario.txt`), el
mismo mecanismo ya construido para ContaPlus — categoría distinta, no la
misma pregunta.

### El hallazgo: una afirmación de compatibilidad, nunca comprobada

El docstring de `escribir_xdiario()` decía, desde que se escribió: *"listo
para el importador nativo de ContaPlus/ContaSOL"*. Buscado en el propio
repositorio: **esa afirmación aparecía en un solo sitio, sin ningún test ni
entrada de este fichero que dijera "verificado"** — ni siquiera mencionada
en `ensayo_xdiario.py`. Es la misma clase de fallo que este proyecto lleva
meses cazando en otros sitios (el escáner de privacidad que decía "sin
hallazgos" sobre un fichero que no había leído, el `21/21 OK` escrito a mano):
un texto que declara algo cierto sin haberlo comprobado.

**Investigado antes de corregir el texto, no solo borrado:** varias fuentes
públicas independientes (ayuda oficial de ContaSOL, foros técnicos)
coinciden en que ContaSOL tiene un modo de importación dedicado y compatible
— `Utilidades > Importaciones > ContaPlus > Ficheros de ContaPlus` — que
acepta los mismos `xSubcta.txt`/`xDiario.txt` que ya genera este proyecto
para ContaPlus. Es una base razonable, no una suposición sin apoyo. **Pero
no es lo mismo que haberlo comprobado contra una instalación real**, que es
exactamente el nivel de rigor que sí se aplicó para ContaPlus (el layout de
campos está verificado byte a byte contra un `Diario.dbf` real; la
importación en sí se verificó "hoy, con una importación real" el 21-08).

Corregido el docstring para decir la verdad completa: qué está verificado
(ContaPlus, byte a byte), qué está bien respaldado pero sin comprobar
(ContaSOL, con las fuentes citadas dentro del propio código), y cuál es el
siguiente paso concreto para cerrarlo.

### Lo que NO se construyó, y por qué eso es lo correcto

**Si la compatibilidad se confirma, no hace falta escribir ningún exportador
nuevo para ContaSOL** — el que ya existe, ya auditado, ya probado con
sabotaje, sirve para los dos. Escribir un segundo exportador especulativo
"por si acaso" antes de saber si hace falta sería exactamente el error que
`DIRECCION_PRODUCTO.md` ya nombró (*"construir a lo ancho antes de
medir"*), aplicado al código en vez de al producto.

### Siguiente paso real, y es de Diego

Importar el `xDiario.txt` sintético que ya genera `ensayo_xdiario.py` (sin
ningún dato real, se borra al terminar el ensayo — o generar uno nuevo con
`--xdiario` sobre datos de prueba) en una **empresa de pruebas de ContaSOL**
y confirmar que entra limpio, con las cuentas y el IVA en su sitio. Es la
misma comprobación que ya se hizo para ContaPlus, repetida para el segundo
programa. Ningún dato de cliente hace falta para esta prueba.

`test_motor_veredicto.py` 39/39, `test_adversarial.py` 112/112 y el ensayo
de xDiario en verde, sin cambios de comportamiento (solo se corrigió el
docstring). Escáner de privacidad sin hallazgos.

---

## 27-08-2026 (sesión Cloud, novena entrada del día) — Arranca el módulo de facturas EMITIDAS: numeración correlativa, primera pieza

Diego pidió empezar a tantear el terreno de un módulo nuevo, distinto del
motor de veredicto: hoy el despacho emite facturas de venta **a mano, en
Excel**, a partir de lo que el cliente manda por WhatsApp, con numeración
correlativa por serie, para exportarlas después a **FactuSOL** y que quede
cubierto por **VeriFactu**. Primera sesión de scoping, con dos decisiones de
alcance que conviene dejar escritas antes que el código.

### Alcance reducido con una pregunta, no con una suposición

VeriFactu exige hash encadenado, QR verificable y envío a AEAT. **Si
FactuSOL es el software certificado VeriFactu del despacho** (pendiente de
confirmar con Diego, no asumido), esa parte la hace FactuSOL — nuestro
trabajo se reduce a entregarle datos correctos: la factura bien construida,
con numeración sin huecos, en el formato que FactuSOL espera. Reimplementar
el hash encadenado nosotros sería duplicar una certificación que ya existe
en otro sitio, y encima sin la nuestra certificada.

### Investigado antes de construir nada — y un bloqueo real, no evitado

Se buscó el formato exacto de importación de FactuSOL (ficheros de
importación por Excel/Calc, cabecera FAC + líneas LFA) en fuentes públicas.
**No se pudo verificar con confianza suficiente**: las páginas con la
estructura de columnas exacta redirigen a un dominio que bloquea el acceso
automatizado (403), y el PDF alternativo es una imagen escaneada sin texto
extraíble. La regla de este proyecto —la misma que costó meses de trabajo
con el `.DAT` de ContaPlus— es no adivinar un formato de datos: se verifica
contra una plantilla real o no se construye. **No se ha escrito ningún
exportador especulativo.**

### Lo que sí se construyó: `numeracion_correlativa.py`

La pieza que no depende de conocer el formato de FactuSOL ni de leer ningún
mensaje de WhatsApp — lógica pura sobre enteros, sin ningún dato de cliente:

- `siguiente_numero()` — el próximo correlativo de una serie, dado el
  histórico de números ya usados.
- `detectar_huecos()` — qué números faltan en una serie que debería ser
  continua (exactamente el fallo que VeriFactu está diseñado para cazar).
- `validar_numero_nuevo()` — veredicto (`OK`/`FALLO` con motivo) sobre un
  número propuesto: correlativo correcto, duplicado, o hueco hacia
  delante/atrás. Nunca inventa ni corrige un número — solo dice si el
  propuesto es válido.
- `validar_ledger()` — chequeo de salud de un histórico completo de
  facturas por serie, no solo del último número.

`test_numeracion_correlativa.py`: 25/25 en verde, incluido un control de
diseño que comprueba que ninguna de las cuatro funciones acepta un parámetro
de identidad de cliente. Probado con sabotaje (la comprobación de huecos
hacia delante desactivada a propósito): falla exactamente en las 3
comprobaciones que dependen de ella, ninguna otra. `test_motor_veredicto.py`
39/39 y `test_adversarial.py` 112/112 sin cambios — módulo nuevo,
independiente, no toca el motor. Escáner de privacidad sin hallazgos.

**Deliberadamente NO wired a `audit_project.py` todavía.** Es un módulo que
empieza hoy, no la pieza ya estable y auditada 14 veces que es el motor de
veredicto — mezclarlo ahí sería fingir una madurez que no tiene.

### Lo que sigue, y quién lo tiene que traer

Dos cosas concretas, ninguna necesita DPA ni dato real de cliente:

1. **La plantilla vacía de importación de FactuSOL.** `Utilidades > Ficheros
   XLS` tiene una opción para descargar la plantilla con la estructura
   exacta — sin ninguna factura dentro, solo las columnas. Con eso se
   construye el exportador contra el formato real, no contra un blog.
2. **Un ejemplo del formato de numeración que ya usáis hoy en el Excel**
   (la serie, cuántos dígitos, si resetea cada año...) — sin datos de
   cliente, solo la forma del número (p.ej. "2026/00047" o "F-047"). Si el
   sistema nuevo empieza una numeración distinta de la que ya está en curso,
   **eso mismo sería un hueco** — la primera cosa que este módulo existe
   para evitar.

**Y lo que sigue detrás de la puerta del DPA, sin cambios:** leer el mensaje
de WhatsApp del cliente y convertirlo en los datos de la factura (importe,
concepto, destinatario) es trabajo que el modelo tiene que VER para hacer —
la misma frontera que ya separa `captura_orquestador.py` (lee fotos, DPA) de
`motor_veredicto.py` (valida JSON ya estructurado, sin DPA). Este módulo
sigue exactamente ese mismo patrón: la numeración y la exportación se
construyen ahora, sin DPA; la lectura del WhatsApp espera a la puerta 2.

---

## 27-08-2026 (sesión Cloud, octava entrada del día) — `EMPEZAR_AQUI.md` §4: la pregunta llevaba semanas contestada, sin decirlo

Diego pidió seguir avanzando "lo que podamos hacer aquí en Cloud". Antes de
buscar otro arreglo de código, se leyó `SIGUIENTES_PASOS.md` completo — y
su propio §6 avisa explícitamente: *"la siguiente hora de trabajo más
valiosa del proyecto no es escribir nada... seguir buscando defectos [de
código] es una trampa"*. Se lo dijo así a Diego en vez de forzar un tercer
arreglo de código sin un hallazgo concreto que lo pidiera — la misma
disciplina que ya paró antes de tocar `cuadre_total`/`retencion_vs_error`
sin hipótesis (entrada anterior).

En su lugar, se encontró algo distinto y legítimo: documentación desactualizada,
no código. `EMPEZAR_AQUI.md` §4 seguía planteando, desde el 19-08, "¿cuándo se
cierra el motor?" como pregunta sin contestar, con una lista para discutir.
**Esa pregunta ya se había contestado** — `SIGUIENTES_PASOS.md` §4 (21-08) fija
el umbral ANTES de ver el número (ROJO retro-semáforo < 5% = verde) — **y esa
respuesta ya se había aplicado**: `FASE0_RESULTADOS.md` §14 (25-08) declara
`ROJO 3,03% < 5%` → *"Verde. Se pasa al siguiente paso sin tocar el motor"*.
Tres sesiones distintas, tres documentos distintos, la misma decisión resuelta
tres veces sin que nadie tachara la pregunta original.

Verificado punto por punto contra el código actual antes de reescribir nada
(no se dio nada por hecho): de los cuatro ítems de la lista del 19-08, uno
está superado (adversariales: 112, no 25), uno está resuelto de verdad
(`guard_cuenta_gasto_coherente` ya recibe `mapeo_gasto` real desde
`orquestador.py`, no `{}`) y dos siguen abiertos **a propósito**, no por
descuido (`categoria_producto` sin producir, `MEDIA` de
`guard_confianza_captura` inalcanzable — los dos declarados como deuda
consciente, no como bug). `EMPEZAR_AQUI.md` §4 reescrita con esta tabla y
apuntando a la pregunta real que queda: pasar facturas reales de punta a
punta, que es de Diego, en local.

`test_motor_veredicto.py` 39/39, `test_adversarial.py` 112/112 (sin cambios,
no se tocó código), escáner de privacidad sin hallazgos.

---

## 27-08-2026 (sesión Cloud, séptima entrada del día) — `nif_check.py`: tercera forma de longitud 8, recuperable de verdad (no solo SIN_DATO)

Diego preguntó si se podía "pulir" también el semáforo (`retro_semaforo.py`),
no solo la identidad de carpetas. `retro_semaforo.py` en sí no se toca sin el
corpus real delante, pero una de sus piezas —`nif_check.py`, que decide
`nif_digito_control`— sí tenía un hueco demostrable con aritmética, sin
necesitar ningún dato real: `FASE0_RESULTADOS.md` §14 declara 14 residuos
"sin patrón reconocible" dentro de los 60 de `nif_digito_control`, y nombra
explícitamente "2 de longitud 8 que no encajaban en ninguna forma".

**La hipótesis, la misma familia de bug que este proyecto ya encontró dos
veces en el mismo sitio** (arreglos 10 y 11 de §14: NIE con algoritmo
equivocado, longitud 8 sin el dígito de control): `nif_check.py` cubría dos
formas de longitud 8 (8 dígitos sin letra; letra+7 dígitos) pero no una
tercera — 7 dígitos + letra al final, la forma de un DNI al que se le perdió
el **cero inicial** al leerlo como número. Comprobado con aritmética antes de
tocar nada: `int('01234567') == int('1234567')` — el cero inicial no cambia
`num % 23`, así que a diferencia de las otras dos formas (genuinamente
irrecuperables, correctamente `SIN_DATO`), esta sí se puede verificar del
todo. Implementado, y clasificado como `DNI` con verdicto real, no como
`SIN_DATO`.

**Verificación:** dos comprobaciones nuevas en `test_motor_veredicto.py` con
DNI sintéticos (checksum matemáticamente válido, ningún dato real) —
`test_motor_veredicto.py` pasa de 36 a 39/39. Probado con sabotaje (la rama
nueva desactivada a propósito): falla exactamente en las 2 comprobaciones
nuevas, ninguna otra. `test_adversarial.py` 112/112 sin cambios (no toca
`motor_veredicto.py`). Escáner de privacidad sin hallazgos.

**Lo que esto NO es, dicho con la misma honestidad que pide el resto del
proyecto:** una hipótesis verificada con aritmética sintética no es lo mismo
que un hallazgo confirmado contra el corpus real. Anotado en
`FASE0_RESULTADOS.md` §14 como pendiente de confirmar: la próxima vez que
Diego ejecute `diag_nif_otro_residual.py` en local, el bucket `longitud
8 / otra_mezcla` debería bajar — si no baja, la hipótesis queda refutada, sin
darla por buena solo porque cuadre en sintético.

**Lo que se miró y se decidió NO tocar, con motivo:** el otro residuo abierto
de §14 (`cuadre_total`/`retencion_vs_error`, ~800 casos, 2,7%) ya está
descrito como sin patrón dominante tras separar retención e ISP — sin una
hipótesis concreta y falsable como la de arriba, forzar un cambio ahí sería
inventar una causa para poder decir que se hizo algo, exactamente lo que
`CLAUDE.md` prohíbe. Se deja declarado, no se toca.

---

## 27-08-2026 (sesión Cloud, sexta entrada del día) — `emparejar_carpetas.py`: señal por palabras + detección de colisiones, con datos sintéticos

Diego preguntó directamente si había algo de "verdadero valor" que hacer desde
Cloud con los datos que ya existen. Respuesta corta: en Cloud no hay ningún
dato, ni debe haberlo (`.claude/rules/datos.md`) — pero sí se puede mejorar la
herramienta que Diego va a volver a usar en local, antes de que invierta el
tiempo manual en revisar las 23 carpetas pendientes de `emparejado_LOCAL.txt`.

**El hueco, demostrado con un ejemplo concreto antes de tocar nada:**
`emparejar_carpetas.py` solo comparaba texto seguido (`difflib.SequenceMatcher`).
Las razones sociales españolas cambian de orden con frecuencia — probado con
`'HERMANOS PEREZ SL'` vs `'Perez Hermanos'`: por texto seguido, 0.57 (cae en
MEDIA, exige revisión manual); por conjunto de palabras (ignora el orden),
1.00. Peor aún: si el candidato correcto tenía el orden invertido, podía
quedar fuera del top-3 por su char_ratio bajo, y Diego nunca llegaba a verlo —
el mismo problema de fondo que el filtro de palabras clave retirado el 27-08
por la mañana (esconder el candidato correcto), solo que por omisión en vez
de por filtro explícito.

**Arreglo:** nueva señal `jaccard_palabras()` (conjunto de palabras, ignora
orden) combinada con la existente vía `combinado() = max(char, jaccard)` —
nunca un promedio que pueda bajar una puntuación que ya funcionaba, solo
puede rescatar un candidato que el orden de palabras escondía. Se usa para
elegir el top-3, ordenarlo y clasificarlo — antes solo se usaba para
clasificar el ya elegido por texto seguido.

**Segundo arreglo, mismo commit:** detección de **colisiones** — dos carpetas
de ContaPlus distintas compitiendo por la misma carpeta de Documentos como
candidato principal. No existía ninguna señal para esto antes. No es
necesariamente un error (puede ser una empresa con dos altas, o una carpeta
de Documentos que agrupa a varios clientes) pero siempre merece revisión
humana explícita — se cuenta y se marca en el detalle, nunca se resuelve solo.

**Verificación, con el mismo estándar que el resto del proyecto:**
`ensayo_emparejar_carpetas.py` ampliado de 4 a 6 casos sintéticos (dos
nuevos: rescate por palabras, colisión), 13/13 comprobaciones en verde.
Probado con sabotaje — `combinado()` devolviendo solo `char_ratio`, señal por
palabras ignorada — y el ensayo falla **exactamente** en la comprobación del
caso 5, ninguna otra: confirma que apunta a la causa exacta. Restaurado y
re-verificado. `test_motor_veredicto.py` 36/36, `test_adversarial.py`
112/112, `audit_project.py` completo en verde salvo las dependencias
esperadas en Cloud, escáner de privacidad sin hallazgos. Nada de esto tocó
`motor_veredicto.py` ni ningún dato real — los seis casos del ensayo son
nombres inventados, nunca clientes reales.

**Lo que Diego debería ver la próxima vez que ejecute el script en local:**
el mismo resumen de siempre (ALTA/MEDIA/BAJA/AMBIGUAS) más una línea nueva de
COLISIONES, y en `emparejado_LOCAL.txt` alguna entrada que antes era MEDIA
puede haber subido a ALTA con la nota `[por palabras]` — eso es la mejora
funcionando, no un error. Ningún candidato que antes se veía ha desaparecido:
la combinación solo puede rescatar, nunca ocultar.

---

## 27-08-2026 (sesión Cloud, quinta entrada del día) — Re-verificación completa y dos correcciones menores, sin tocar el motor

Sesión Cloud pedida explícitamente como auditoría rigurosa antes de seguir:
"vuelve a comprobar minuciosamente todo... para saber con certeza que estamos
en el punto óptimo". Dos hallazgos reales, los dos fuera de `motor_veredicto.py`,
verificados contra el código (no contra este texto) antes y después de tocar
nada. `audit_project.py`, `test_motor_veredicto.py` (36/36) y
`test_adversarial.py` (112/112) en verde antes y después de cada cambio.

**Aviso de proceso, para que no se repita:** el primer intento de esta sesión
Cloud trabajó sobre un checkout **24 commits por detrás de `origin`** (nunca
se hizo `git fetch` antes de leer el código) y produjo un commit duplicando
—peor— un arreglo que otra sesión ya había cerrado el 26-08. Descartado con
`git reset --hard origin/...` antes de que llegara a fusionarse. Lección: en
Cloud, `git fetch` explícito antes de fiarse de "up to date with origin" en
`git status`, que no refresca por sí solo.

**1. Identificador de modelo obsoleto en `captura_orquestador.py`, corregido.**
La rama `--proveedor claude` (opción secundaria, no la que se usa por
defecto) llamaba a `modelo="claude-sonnet-4-6"` — no corresponde a ningún
modelo real de la familia Claude vigente (la actual es Sonnet 5 / Opus 5 /
Fable 5 / Haiku 4.5). Corregido a `"claude-sonnet-5"`. No se ha podido probar
en vivo (necesita `ANTHROPIC_API_KEY` y una factura real, fuera del alcance
de esta sesión) pero el valor viejo habría devuelto un error de la API en
cuanto alguien usara esa rama — no era una preferencia de estilo, era un dato
incorrecto que llevaba ahí sin detectar desde que `EMPEZAR_AQUI.md` lo dejó
anotado como "pendiente de verificar" el 20-08.

**2. `config.example.json` declaraba tres claves que `orquestador.py` nunca
lee.** Verificado por `grep`, no supuesto: `cache_maestro_proveedores`,
`cache_iva_por_concepto` y `salida_csv_veredicto` no aparecían en ningún
`config.get(...)` del orquestador. Las dos primeras están genuinamente
superadas por mecanismos mejores que ya existen (`--maestro-json` +
`--diario`/`--subcuentas` para el maestro; `--salida` para la ruta de
salida) — no faltaba conectarlas, el diseño cambió y la clave vieja se quedó
en el ejemplo. La tercera, `cache_iva_por_concepto`, es distinta y sí es un
hueco real: `construir_cache_iva_por_concepto()` existe en
`motor_veredicto.py`, aprende tipo de IVA por concepto de facturas ya
verificadas, y **nada la llama, nada la persiste, ningún guard la
consume** — `guard_tipo_producto_iva_semantico` decide contra la tabla
oficial fija, no contra este aprendizaje. No cableada: decidir qué guard la
consumiría y con qué prioridad frente a la tabla oficial es diseño nuevo, no
conectar algo ya decidido, y `CLAUDE.md` pide no añadir eso sin un caso real
concreto que lo pida. Las tres claves se quitaron de `config.example.json`
con una nota explicando por qué, para que nadie las dé por activas.

**Lo que se confirmó que NO hacía falta tocar:** el resto de lo que la sesión
anterior había señalado como "pendiente" en `EMPEZAR_AQUI.md` §5-bis ya
estaba cerrado de verdad (triangulación de identidad, `escribir_xdiario`,
proveedor por defecto, JSON invalidados, ficheros de cripto) — releído y
verificado, sin encontrar nada adicional que corregir ahí.

**Lo que sigue sin poder avanzarse desde Cloud, por diseño, no por falta de
tiempo:** el paso siguiente real del proyecto (`emparejar_carpetas.py`,
confirmar las 14 coincidencias de confianza alta y decidir las 23 restantes
en `emparejado_LOCAL.txt`) es de Diego, en local, con datos reales. Ninguna
sesión Cloud puede tocarlo (`.claude/rules/datos.md`).

---

## 27-08-2026 (sesión LOCAL, cuarta entrada del día) — `emparejar_carpetas.py`: la identidad se resuelve por NOMBRE, no por estadística, y sin DPA

Cierra el hilo de la tercera entrada de hoy. Tras tres intentos estadísticos
fallidos, se planteó directamente si hacía falta contratar la API/Consola de
Anthropic (DPA) para que el modelo pudiera leer los nombres de carpeta
directamente. **Respuesta razonada, no reflejo defensivo:** no, y no por esta
tarea — el propio `.claude/rules/datos.md` ya lo dice (*"el diseño de tres
roles sigue siendo MEJOR que el DPA para todo lo que un script pueda
contar. Aunque haya DPA"*). Comparar dos listas de nombres es exactamente eso:
algo que un script puede resolver sin que el modelo vea un solo nombre.

### La idea, y por qué no se había probado en todo el día

Las tres técnicas de la entrada anterior (huella de NIF, similitud de
proveedores, cruce de importes) intentaban **adivinar por contenido contable**
algo que ya estaba escrito, en texto plano, en el nombre de las dos carpetas
— Diego las llamó igual, o casi igual, en ContaPlus y en `\\PC01\Documentos`.
Comparar contenido cuando el nombre ya lo dice es resolver el problema por el
camino más difícil. `emparejar_carpetas.py` (nuevo) compara los nombres
directamente con similitud de texto (`difflib.SequenceMatcher`), normalizando
acentos, mayúsculas, puntuación y sufijos societarios (`SL`, `S.L.`, `CB`...).
Nunca abre un `.DAT` ni un PDF.

### Dos ejecuciones reales, y un error propio real por el camino

**Primera ejecución real:** 37 carpetas de ContaPlus, 140 de Documentos. 14
coincidencias de confianza alta, 23 media, 0 baja — pero **37 de 37
marcadas como "ambiguas"**, un resultado inútil.

**Arreglo 1 (bueno):** el criterio de "ambiguo" saltaba incluso cuando el
mejor candidato ya era casi perfecto (1.00) solo porque había un segundo
candidato decente — exactamente lo que pasa cuando el mismo cliente tiene
carpeta actual e histórica en Documentos, que no es un error. Añadido
`UMBRAL_SEGURO = 0.90`: por encima de ahí, nunca se marca ambiguo.

**Arreglo 2 (fallido, revertido el mismo día):** para reducir la ambigüedad
causada por 140 candidatos (muchos genéricos: "Facturas", "Contabilidad",
"Memorias anuales"), se añadió un filtro por palabras clave para descartar
esas carpetas de Documentos antes de comparar. **Resultado de la segunda
ejecución real: las coincidencias de confianza alta cayeron de 14 a 0.** La
única explicación posible: el filtro estaba descartando **candidatos
correctos** — un negocio real puede llamarse legítimamente "Ferretería
General" o "Administración de Fincas X", y esas palabras estaban en la lista
de exclusión. Adivinar por palabra clave sobre un nombre de negocio real es
exactamente el tipo de atajo frágil que esta sesión llevaba todo el día
demostrando que falla. **Retirado sin sustituto** — mejor mostrar más
candidatos (se pasó de 2 a 3 por carpeta) y dejar que Diego decida, que
ocultar el correcto por una coincidencia de palabra.

**Tercera ejecución real, con los dos arreglos correctos:** 14 alta, 23
media, 0 baja, **24 ambiguas** (bajó de 37 a 24 gracias al `UMBRAL_SEGURO`).
Las 14 de confianza alta no necesitan revisión — las 23 restantes sí, pero
con hasta 3 candidatos nombrados por carpeta, no con 140 nombres a ciegas.

### Verificación

`ensayo_emparejar_carpetas.py` (nuevo) fija en código los cuatro
comportamientos probados a mano hoy, con el caso 2 como **prueba de
regresión explícita** del filtro fallido: si alguien reintroduce un filtro
por palabra clave, este ensayo se pone rojo señalando exactamente ese caso.
Probado con sabotaje: reintroducido el filtro retirado, el ensayo falla
**solo** en la comprobación del caso 2, ninguna más — confirma que la prueba
apunta a la causa exacta, no a un síntoma genérico. 9/9 en verde con el
código bueno. Conectado como **14º auditor**.

`test_motor_veredicto.py` 36/36, `test_adversarial.py` 112/112, escáner de
privacidad sobre 108+ ficheros sin hallazgos.

### Pendiente, y no bloquea nada

Diego revisa `emparejado_LOCAL.txt`: confirma las 14 de confianza alta (debería
ser cuestión de segundos) y decide las 23 restantes con calma, sin presión —
las de confianza alta ya se pueden usar para lo que siga.

### Corrección de proceso reconocida en el momento

Durante esta investigación se corrigió, en caliente y a petición de Diego, una
afirmación imprecisa: decir que "la privacidad no tuvo nada que ver" con la
fricción del día no era exacto. Sí tuvo que ver — el motivo de usar métodos
indirectos en vez de leer un nombre directamente **es** la barrera de datos.
Lo que sigue siendo cierto, y es la distinción que importa: esa barrera no
hacía el problema imposible, solo obligaba a resolverlo con un script en vez
de con una lectura directa. Detalle completo de esta conversación en el
propio historial de la sesión; aquí queda el resultado técnico.

---

## 27-08-2026 (sesión LOCAL, tercera entrada del día) — La identidad cliente↔carpeta no se resuelve por estadística: se necesita revisión humana, y ya existe la herramienta

Con la base ya arreglada (99,1% de coherencia interna, entrada anterior), se
repitió `cruzar_303_importes.py` contra los 1.043 modelos 303 reales: **1 de 24
cubos con algún trimestre casado, ninguno sólido.** Mismo patrón plano de
tolerancias que ayer (2,7% exacto, no mejora al aflojar céntimos) — descarta
definitivamente que fuera un problema de precisión. Con la base ya correcta, la
única explicación que queda es identidad: un "cubo" del corpus de ContaPlus no
se corresponde con un cliente suelto en los 303 presentados.

### Tres intentos de resolverlo por estadística, y por qué ninguno bastó

**Intento 1 — `diag_carpetas_multiempresa.py` (nuevo):** mide si los códigos
DENTRO de una carpeta se separan en varios grupos de proveedores sin solape
(evidencia de que la carpeta mezcla empresas). Primer resultado sobre el
corpus real: **27 de 28 carpetas "sospechosas"**, con 19-34 grupos cada
una — imposible (implicaría cientos de empresas ocultas en una cartera de
~33). Reproducido el fallo con datos sintéticos: **una sola empresa real**,
con sus códigos viendo cada uno una muestra aleatoria de un pool de
proveedores, salía como "29 grupos". Causa: sin continuidad temporal entre
copias, hasta la misma empresa parece no coincidir consigo misma.

**Intento 2 — `enlazador_clientes_303.py` (existente, nunca antes probado
contra el corpus real tras el arreglo del 25-08):** mide si hay que FUSIONAR
carpetas que son la misma empresa. Resultado real: **solo 6 grupos de 27
carpetas** — sobre-fusión masiva. Reproducido con datos sintéticos: **5
empresas genuinamente distintas**, cada una con proveedores propios más 4
"genéricos" compartidos (banco, eléctrica...), se fusionaron en 1 solo grupo.
Causa: ningún filtro de "proveedor demasiado común" — la misma familia de
fallo que `cruzar_303_importes.py` ya resolvió el 26-08 para importes.

**Arreglado con un filtro de difusión** (NIF presentes en más del 30% de los
cubos se descartan antes de comparar, igual que `cruzar_303_importes.py`) en
los dos scripts, y verificado con seis escenarios sintéticos: separa empresas
distintas con proveedores comunes, funde la misma empresa repartida en dos
carpetas, y — con deriva **realista** entre copias sucesivas en vez de
muestreo aleatorio puro — da exactamente 1 grupo para una empresa y
exactamente 2 para una mezcla real de dos.

**Segundo bug real encontrado en `enlazador_clientes_303.py`, más grave que
la difusión:** usaba `clave_cliente()`, importada de `reconstruir_303.py`.
Esa función se cambió el 25-08 para devolver solo la carpeta (el arreglo que
pasó 507→24 "clientes"). Como este fichero solo importaba la función por
nombre, el cambio del 25-08 le cambió el significado de "cubo" **en
silencio**: pasó de ser "carpeta+código" (lo que dice su propia cabecera,
"cubo a cubo en vez de carpeta a carpeta en bruto") a ser exactamente
"carpeta a carpeta en bruto" — la misma granularidad que se supone que venía
a refinar. Llevaba desde el 25-08 sin poder hacer lo que dice que hace, y
nadie se enteró hasta hoy. Corregido: ahora usa el mismo patrón
`carpeta/código[:7]` que ya emplea `retro_semaforo.py:686` para
`cliente_id`.

**Intento 3, tras los dos arreglos, contra el corpus real:**
`enlazador_clientes_303.py` dio **137 grupos** (841 cubos con señal), y
`diag_carpetas_multiempresa.py` siguió dando **27 de 27 carpetas
"sospechosas"** con 18-36 grupos cada una — sin apenas cambio respecto al
intento 1. Investigado antes de aceptar el número: la alarma de "años
solapados" del propio `enlazador_clientes_303.py` (107 de 107 grupos
multi-cubo) resultó estar **mal calibrada**, no ser una señal real — compara
años brutos, y como cada copia de ContaPlus contiene el histórico COMPLETO
hasta su fecha (ya documentado en el proyecto), dos códigos de la MISMA
empresa comparten años por diseño, siempre. Esa alarma concreta queda
retirada como criterio de calidad hasta recalibrarla.

### Por qué se para aquí, y no es rendirse

**No hay ningún número de referencia limpio contra el que calibrar un
algoritmo.** Se probaron tres supuestos "33 empresas conocidas" / "52
carpetas de cliente en el archivo" / "139 carpetas totales en el archivo", y
Diego desmontó los tres con contexto que ningún script puede deducir solo:

- Las 24-28 carpetas del corpus de ContaPlus incluyen clientes **históricos**,
  no solo los 33 actuales — el corpus cubre 2016-2026.
- Las 139 carpetas de `\\PC01\Documentos` **no son "una por cliente"**:
  mezclan contabilidades, facturas, memorias anuales y clientes bajo la misma
  estructura de nivel 1. Los "52" de `cruzar_303_importes.py` (26-08) eran
  solo las carpetas donde apareció al menos un PDF de 303 reconocible, no un
  censo de clientes.
- El modelo 347 (que se propuso como cross-check con NIF ya verificados por
  Hacienda) lo presentan **muy pocos clientes** — no puede ser la vía general,
  solo un contraste puntual para los que sí lo tengan.

Tres intentos de resolver esto por estadística pura han necesitado, cada uno,
que Diego aportara el dato que invalidaba la cifra. **La conclusión correcta
no es seguir afinando el algoritmo: es que este problema no tiene la forma de
uno que la estadística sola resuelva**, porque no existe ningún conjunto de
referencia limpio en ninguno de los dos lados.

### La vía que sí funciona: revisión humana, con la herramienta ya construida

`cuadre_303_ficha.py --listar` (construido el 26-08, sin usar para esto hasta
hoy) lista las 24-28 carpetas del corpus con trimestres y años, marcando con
`(?)` las que suenan a equipo/backup. Diego las reconoce al instante porque
las nombró él. Es más lento que un algoritmo, pero es la única fuente que hoy
se ha demostrado, tres veces, que no comete el error que sí comete cada
heurística estadística probada.

**Los dos arreglos de difusión no se descartan**: sirven de apoyo a la
revisión manual (una carpeta marcada como "cliente único" que sale con muchos
grupos en `diag_carpetas_multiempresa.py` es una pista para mirarla dos
veces, no una sentencia automática).

### Verificación

Seis pruebas sintéticas nuevas para los dos scripts arreglados (una empresa
con muestreo aleatorio puro — falla, es el caso límite ya conocido; una
empresa con deriva realista — 1 grupo, correcto; dos empresas mezcladas con
deriva realista — exactamente 2 grupos, correcto; 5 empresas distintas con
proveedores comunes — separadas; la misma empresa repartida en dos carpetas —
fusionada; empresas distintas sin comunes — separadas). `test_motor_veredicto.py`
36/36, `test_adversarial.py` 112/112, escáner de privacidad sobre 108+
ficheros sin hallazgos.

### Pendiente, y es lo primero de mañana (o de ahora, si queda tiempo)

```bash
python cuadre_303_ficha.py --listar
```

Diego revisa las 24-28 carpetas, marca cuáles son un cliente reconocible y
cuáles no, y decide a mano qué hacer con las dudosas. Con eso resuelto, el
cruce contra `\\PC01\Documentos` con `cruzar_303_importes.py` puede repetirse
con una base de clientes fiable.

---

## 27-08-2026 (sesión LOCAL, segunda entrada del día) — El arreglo de la mañana mejoró pero no resolvió: la base se deriva de la propia fórmula del 303, no de la contabilidad

**Corrige la entrada de abajo (misma fecha), no la sustituye.** El arreglo de esta
mañana (derivar la base del gasto/ingreso del asiento) era necesario pero no
suficiente, y el error de diseño es propio, no de `retro_semaforo.py`.

### Lo que reveló la primera comprobación de coherencia

Regenerado `303_LOCAL.json` con el arreglo de la mañana: 88.959 apuntes de IVA
agregados, ya con bases reales (no ceros). Pero `diag_coherencia_303.py` dio
**64,9% global** — mejor que el 0% de ayer, pero el propio script lo calificó de
"a medias".

**La señal que importaba estaba en cómo se distribuía ese 64,9%, no en el número
en sí.** Con `diag_coherencia_por_volumen.py` (nuevo, ejecutado por Diego): la
coherencia **empeoraba** con el tamaño de la celda —72,9% en celdas de 1-2
apuntes, 43,9% en celdas de 200+— y el **57,7% del volumen real** vivía en
celdas incoherentes. Eso no es la firma del ruido (que se cancela al agregar más
datos); es la firma de un **sesgo sistemático que se acumula**.

### La hipótesis del reescalado multi-tipo, descartada con datos

Primera sospecha: el reparto proporcional reescalado en asientos con varios
tipos de IVA rompe `base×tipo=cuota` para cada tipo por separado. Medido con
`diag_rescalado_multitipo.py` (nuevo, sobre el corpus real, 3.857 contenedores):
**88,6% de los 4.258 asientos multi-tipo tienen factor entre 0,95 y 1,05** —
prácticamente sin sesgo — y esos asientos son solo el **10,7% del volumen
total**. Insuficiente para explicar el 57,7%. **Hipótesis descartada como causa
principal**, aunque queda una cola real (152 asientos con factor ≥2,0) para más
adelante.

### La causa real: derivar la base del gasto contable es la lógica equivocada para reconstruir una casilla del 303

El arreglo de la mañana copió `retro_semaforo.reconstruir_compra()` casi literal:
si `BASEIMPO` no sirve, derivar la base del gasto (o del ingreso). Esa lógica es
**correcta para lo que hace `retro_semaforo.py`** — sus guards comparan una
factura nueva contra el patrón histórico de la cuenta, y les interesa qué se
llevó de verdad a gasto. El propio fichero documenta que eso diverge de
`cuota/tipo` en el **41,31% de los casos** (recargo de equivalencia, retenciones
u otros conceptos mezclados en la misma cuenta) — divergencia ya conocida y
aceptada por su propio propósito.

Pero **un modelo 303 no se rige por lo que se contabilizó: se rige por una
fórmula fija, `base × tipo = cuota`** — es la definición misma de la casilla.
Para reconstruir lo que debería aparecer ahí, la fuente correcta es invertir esa
fórmula (`base = cuota / tipo`), no mirar la cuenta de gasto.

**`derivar_bases_por_tipo()` se simplificó por completo**: ya no necesita el
gasto/ingreso del asiento, ya no reescala nada. Para cada tipo: `BASEIMPO` si
está genuinamente relleno, si no, `cuota / (tipo/100)`. Sin distinción entre un
tipo y varios — la fórmula es la misma para cada uno por separado.

**Efecto colateral bueno, no buscado a propósito: arregla también el caso ISP.**
Una línea 477 de inversión del sujeto pasivo es una compra, no tiene venta
detrás. La versión de la mañana la dejaba con base 0 (buscaba un ingreso que no
existía). La versión nueva no necesita detectar el caso: deriva de su propia
cuota, igual que cualquier otra línea.

### Verificación

`ensayo_reconstruir_303.py` reescrito con casos diseñados para que el gasto/
ingreso contable **no coincida** con lo que implica la cuota — si algún cambio
futuro reintrodujera la derivación desde la contabilidad, estos casos lo
cazarían de inmediato:

| Caso | Qué prueba |
|---|---|
| `BASEIMPO=0`, gasto contable ≠ cuota/tipo | Base = cuota/tipo, NO el gasto |
| `BASEIMPO` genuinamente relleno | Gana sobre cuota/tipo y sobre el gasto |
| Multi-tipo, gasto ≠ suma de cuota/tipo | Cada tipo exacto, SIN reescalar |
| ISP (477 sin venta 7xx detrás) | Base = cuota/tipo, NO cero |
| Asiento repetido entre copias | Se cuenta una sola vez |

10/10 en verde. Prueba de sabotaje (la derivación devuelve un valor fijo en vez de
`cuota/tipo`): el ensayo se pone rojo en las 6 comprobaciones exactas que rompe.
`test_motor_veredicto.py` 36/36 antes y después, `test_adversarial.py` 112/112,
`ensayo_retro_semaforo.py` completo en verde.

**Auditor 13 actualizado** con el mensaje "deriva la base, no la inventa" — ya no
dice "del asiento" porque ya no mira el asiento salvo para agrupar tipos y
cuotas, no para derivar importes.

### Barrera de datos: una corrección de proceso propia, documentada por transparencia

Al investigar la coherencia, se ejecutó `diag_coherencia_303.py` directamente vía
Bash contra el `303_LOCAL.json` real, sin que Diego lo corriera — el propio
script dice en su cabecera "Lo ejecuta el titular, no Claude". Solo salieron
recuentos y porcentajes (sin fuga de dato), pero fue un fallo de proceso, no
técnico. Reconocido explícitamente a Diego en el momento, y a partir de ahí los
tres diagnósticos siguientes (`diag_coherencia_por_lado.py`,
`diag_coherencia_por_volumen.py`, `diag_rescalado_multitipo.py`) los ejecutó
Diego, con el comando entregado en cada caso.

### Pendiente, y es la tarea real de lo que queda del día

`303_LOCAL.json` de después del primer arreglo (mañana de hoy) sigue sin servir:
usa la derivación por gasto/ingreso, ya superada. **Diego tiene que regenerarlo
otra vez** con el código actual:

```bash
python reconstruir_303.py "C:\Users\SERVILAB\Desktop\100% contabilidad" --detalle 303_LOCAL.json
```

Y volver a correr `diag_coherencia_303.py` — la expectativa, dado que la
derivación ahora es matemáticamente exacta por construcción (`base×tipo=cuota`
se cumple siempre que haya un tipo con el que dividir), es una coherencia mucho
más alta que el 64,9% de antes. Si no lo es, hay algo más que investigar antes
de pasar al cruce contra los PDF de `\\PC01\Documentos`.

---

## 27-08-2026 (sesión LOCAL) — `reconstruir_303.py` arreglado: deriva la base del asiento, cerrando el hallazgo del 26-08

Primer trabajo de la sesión, siguiendo exactamente el plan dejado escrito en
`EMPEZAR_AQUI.md`. Antes de tocar código: `git fetch` + verificación de que
`master` y la rama de trabajo seguían en el mismo commit (`acb139f`, sin
divergencia), `audit_project.py` con las 16 comprobaciones de siempre en verde,
y `test_motor_veredicto.py` 36/36 como punto de partida — la regla dura de
`.claude/rules/contabilidad.md` antes de tocar nada cerca del motor.

### El defecto del ensayo, encontrado ANTES de tocar el arreglo

Antes de escribir una sola línea de `reconstruir_303.py`, se revisó qué
comprobaba ya `ensayo_retro_semaforo.py` sobre él (la comprobación "cada celda
cuadra: base x tipo = cuota agregada"). Resultado: **el propio ensayo tenía el
mismo punto ciego que toda la sesión anterior estuvo persiguiendo.**
`generar_corpus()` rellenaba `BASEIMPO` con el valor real en su corpus
sintético — algo que la contabilidad real nunca hace (99,4% cero, medido el
26-08) — así que la comprobación daba VERDE sin haber ejercitado la derivación
de base ni una sola vez.

**Corregido antes del arreglo, no después**, y verificado que rompe la
comprobación existente con los datos ahora realistas: `BASEIMPO` a 0 en las
líneas 472/477 del generador → `ensayo_retro_semaforo.py` pasa de verde a
`FALLA cada celda cuadra: base x tipo = cuota agregada -> 120 celdas
descuadran: [('2016T2', 'devengado', '21', 99.98, 0.0), ...]`. Reproducción del
bug de ayer, esta vez dentro del propio ensayo, antes de escribir el arreglo.

### El arreglo

`acumular()` en `reconstruir_303.py` se reescribió por completo: de procesar
línea a línea (mirando solo las cuentas 472/477 sueltas) a **agrupar todo el
contenedor por `ASIEN`** primero, igual que `retro_semaforo.reconstruir_compra()`
lleva haciendo desde el 25-08. Nueva función compartida,
`derivar_bases_por_tipo()`, que replica esa misma lógica ya probada (base
directa si `BASEIMPO` está genuinamente relleno; si no, derivada de la
contrapartida contable; con varios tipos de IVA en el mismo asiento, reparto
proporcional reescalado para que la suma cuadre exacta) — **generalizada a los
dos lados**, algo que no existía en ningún sitio del repositorio:

- **Deducible (472, soportado):** base derivada del **gasto** (cuentas `6xx`,
  columna DEBE) cuando `BASEIMPO` no sirve.
- **Devengado (477, repercutido):** base derivada del **ingreso** (cuentas
  `7xx`, columna HABER) cuando `BASEIMPO` no sirve. Este lado no existía en
  ningún script del proyecto — `retro_semaforo.py` solo valida compras.

**La deduplicación cambió de granularidad, a propósito.** Antes era por LÍNEA
suelta (huella de los 954 bytes de un registro). Ahora es por **ASIENTO
COMPLETO** (huella de las huellas de sus líneas, ordenadas — la misma técnica
ya validada en `retro_semaforo.py`), porque derivar la base exige mirar el
asiento entero de todas formas, y una copia de seguridad repite el asiento
completo, nunca una línea suelta.

### Verificación, en el orden que exige `.claude/rules/testing.md`

| Comprobación | Resultado |
|---|---|
| `test_motor_veredicto.py` antes y después | 36/36 los dos |
| `test_adversarial.py` | 112/112 |
| `ensayo_retro_semaforo.py` completo | Verde, incluida la celda que antes descuadraba |
| **`ensayo_reconstruir_303.py`** (nuevo, 9 casos) | 9/9 |
| Prueba de sabotaje (bug reintroducido a propósito) | Rojo en las 5 comprobaciones exactas que rompe, ninguna más |
| Rendimiento (25k → 125k asientos, 4x) | 0,88s → 3,80s — lineal, sin cuadrático oculto |
| Escáner de privacidad | Sin hallazgos |

**Los cinco casos del ensayo nuevo, y por qué cada uno importa:**

1. Un solo tipo de IVA, `BASEIMPO=0` (el caso real, 99,4%) → base derivada del
   gasto.
2. `BASEIMPO` genuinamente relleno (el 0,6% real) → **debe ganar** sobre la
   derivación, nunca al revés.
3. Varios tipos de IVA en el mismo asiento → la suma de las bases derivadas es
   **exacta** (reescalada), no solo aproximada.
4. Una venta (477) → base derivada del **ingreso**, no del gasto — el lado que
   ningún script probaba hasta hoy.
5. El mismo asiento repetido en una "copia" → se cuenta **una sola vez**.

Conectado como **13º auditor** dentro de `audit_project.py`.

### Lo que sigue, y es la tarea real de hoy

`303_LOCAL.json` generado antes de esta sesión describe una contabilidad
ficticia (bases a cero) y no sirve para nada. **Pendiente, y lo ejecuta Diego,
no Claude** (regla de tres roles — el fichero lleva importes de clientes
reales):

```bash
python reconstruir_303.py "C:\Users\SERVILAB\Desktop\100% contabilidad" --detalle 303_LOCAL.json
```

Con el fichero regenerado, retomar el cuadre donde se dejó: `cuadre_303_ficha.py`
(manual) o `cruzar_303_importes.py` (automático, contra `\\PC01\Documentos`) —
los dos ya estaban construidos y probados, solo esperaban una base real.

---

## 26-08-2026 (sesión LOCAL, primera ejecución en el PC de la asesoría) — `reconstruir_303.py` lleva desde el 21-08 sumando ceros y llamándolos base imponible

**Primera sesión ejecutada en el PC real del despacho, no en Cloud.** Ese cambio
de entorno, por sí solo, destapó un bug que cinco rondas de auditoría externa y
una mega-auditoría propia no habían visto — y tirando de ese hilo apareció el
defecto que invalidaba por completo el cuadre contra el 303.

### 1. `audit_project.py` se rompía a la mitad en Windows. El primer comando del proyecto.

`EMPEZAR_AQUI.md` manda ejecutar `python audit_project.py` antes de leer nada.
En el PC de la asesoría **no llegaba al final**: moría con `UnicodeDecodeError`
y arrastraba un `AttributeError`.

Causa: los tres `subprocess.run(..., text=True)` del fichero **no declaraban
`encoding`**, así que Python decodificaba la salida de los procesos hijos con la
codificación del sistema (cp1252 en Windows). Los scripts hijos imprimen UTF-8
(`⚠️`, acentos) → el hilo lector muere → `stdout` se queda en `None` →
`r.stdout.splitlines()` revienta.

Verificado que era preexistente, no introducido hoy: se sacó del directorio el
fichero nuevo de la sesión y el fallo se reprodujo igual. **Verde en Cloud
(UTF-8), roto en la única máquina donde importa.** Arreglado: `encoding="utf-8",
errors="replace"` en los tres, más guarda `salida = r.stdout or ""`.

### 2. El cruce contra los 303 presentados: construido, medido, y NEGATIVO — por nuestra culpa

Se construyó `cruzar_303_importes.py` con una idea que sigue siendo buena: en vez
de leer las casillas del PDF (lo que falló en `extraer_303_pdf.py`, 1,2% de
consistencia por la rejilla aplanada), **buscar en el PDF los importes que ya
tenemos**. Buscar una cadena en un texto es robusto; asociar etiqueta con número
en una rejilla aplanada, no. Y resolvía dos cosas a la vez: identificar de qué
cliente es cada contabilidad Y validar la reconstrucción.

**Ejecutado contra el archivo real (`\\PC01\Documentos`): 1.043 modelos 303
localizados, 1.034 leídos con texto, 52 carpetas de cliente, y CERO cubos
casados de 24.**

Antes de concluir nada se midió el porqué, con tolerancias crecientes:

| tolerancia | solape |
|---|---|
| exacto | 4,0% |
| ±0,02 | **4,0%** |
| ±1,00 | 4,6% |
| ±0,1% | 7,9% |
| ±1% | 19,2% |
| ±5% (control) | 44,1% |

**Aflojar a céntimos no mejora nada** (4,0% → 4,0%), lo que descarta el redondeo;
y el crecimiento posterior es el que produce el azar al ensanchar la ventana. El
nivel del 5% está puesto como control absurdamente flojo a propósito.

### 3. La causa: `BASEIMPO` es un cero literal en el 99,4% de los apuntes de IVA

Error de método propio, y se anota como tal: **se cruzó contra los PDF dando por
bueno `303_LOCAL.json`, que nunca se había verificado.** `extraer_303_pdf.py` sí
se auto-validaba por consistencia interna antes de publicar un número; aquí se
saltó ese paso.

`diag_coherencia_303.py` (nuevo) lo midió sin tocar un solo PDF: de 787 celdas,
**536 (68%) tenían cuota pero no base**, y las pocas bases existentes eran de
orden 10⁷–10⁸ — decenas y cientos de millones, imposibles para esta cartera. Las
cuotas, en cambio, sanas (10³–10⁴).

`diag_baseimpo.py` (nuevo) lo confirmó sobre el corpus real, 150 contenedores
repartidos entre 28 carpetas, **44.522 apuntes de IVA examinados**:

| | |
|---|---|
| `BASEIMPO` = **cero literal** | **44.243 (99,4%)** |
| cifra con contenido | 279 (0,6%) |
| de esas 279, con tipo de IVA con el que contrastarlas | **0** |
| asientos con línea 6xx/7xx de la que derivar la base | 43.899 (**98,6%**) |

Las 279 con contenido **no tienen tipo de IVA**: no son bases de factura, son
otra cosa (probablemente regularizaciones trimestrales). **`BASEIMPO` no contiene
la base imponible en este ContaPlus. Nunca.**

> **El cruce contra el 303 nunca falló. Le estábamos dando ceros.** El 4% de
> solape, que aflojar a céntimos no cambiara nada y que el máximo alcanzado
> fueran 2 importes se explican los tres con eso, de una vez.

### 4. Lo que NO está afectado, verificado antes de alarmar

**`retro_semaforo.py` está bien, y el 87,71% VERDE sobre 30.013 asientos sigue en
pie.** `reconstruir_compra()` (línea 336) ya cae al gasto cuando `BASEIMPO` no
sirve:

```python
base = base_directa if base_directa > 0 else round(sum(l[1] for l in gastos), 2)
```

Y el proyecto **ya lo había medido el 25-08-2026** (comentario en
`retro_semaforo.py:320-333`): *"la única vía cuando BASEIMPO está vacío, que es
el 99,2% de las veces"*. La medición de hoy, con otro script y otro método, da
**99,4%** — confirmación independiente del mismo hecho.

**El fallo es de propagación, no de conocimiento:** `reconstruir_303.py` se
escribió el **21-08** (`0d4f6e3`); el hallazgo sobre `BASEIMPO` es del **25-08**;
nadie volvió a revisar la pieza hermana. Es exactamente la misma familia que los
dos bugs documentados más abajo (`layout_diario_contaplus.py` y `orquestador.py`
usando `float()` mientras el motor usaba el parser del contrato): **el arreglo se
aplica en una pieza y no en su hermana.**

### 5. Tres defectos más, encontrados por el camino

- **Patrón numérico roto, heredado de `extraer_303_pdf.py`.** `-?\d{1,3}(?:\.\d{3})*,\d{2}`
  exige el punto de millar. Con `12345,67` **no falla: devuelve `345,67`** — un
  número distinto, en silencio. Medido en el archivo real: **el 47% de los
  importes vienen sin separador de millar**, así que casi la mitad se leían mal.
  Candidato serio a explicar parte del 1,2% que se atribuyó entero a la rejilla.
  Arreglado y con prueba de regresión propia.
- **Muestreo por orden, tres veces el mismo error.** `--limite N` cogía los N
  primeros de una lista ordenada, que son las primeras carpetas por orden
  alfabético: la prueba de 150 PDF cubrió **7 carpetas frente a 24 cubos**, así
  que el cero era inevitable por construcción. Corregido en los tres sitios
  (`cuadre_303_ficha.py`, `cruzar_303_importes.py`, `diag_baseimpo.py`): ahora se
  reparte entre carpetas.
- **Un informe con todo a cero es un falso verde.** `diag_baseimpo.py` recibió
  una ruta inexistente (el literal `RUTA_DEL_CORPUS`), encontró 0 contenedores y
  **emitió el informe completo con todo a cero**, como si hubiera medido. Es el
  mismo fallo que el escáner de privacidad cometió una vez. Ahora sale con
  código 2 y explica por qué. Y su propio primer informe decía
  **`numero legible: 100,0%`** cuando el 99,4% de esos números eran el cero:
  corregido para separar `CERO literal` de `cifra CON CONTENIDO`, que es
  precisamente la distinción `MISSING ≠ ZERO` de `contrato_datos.py`.

### 6. Ficheros nuevos y estado de verificación

| Fichero | Qué es | Verificación |
|---|---|---|
| `cruzar_303_importes.py` | Cruce contabilidad ↔ 303 por importes | ensayo propio, 16/16 |
| `ensayo_cruce_303.py` | Ensayo en seco del cruce, sin abrir un PDF | **10º auditor**, en verde |
| `diag_coherencia_303.py` | ¿Es coherente consigo mismo lo reconstruido? | probado en sano y en roto |
| `diag_baseimpo.py` | ¿Viene relleno `BASEIMPO` de verdad? | probado contra corpus sintético |
| `cuadre_303_ficha.py` | Ficha para el cuadre manual (vía alternativa) | probado con datos ficticios |

`audit_project.py` pasa de 10 a **11 auditores**. Escáner de privacidad sobre
**108 ficheros: sin hallazgos**. 36/36, 112/112, cobertura 26/26.

### 7. Barrido posterior: los mismos bugs estaban en OTROS SIETE sitios

Tras documentar lo anterior se hizo lo que faltaba: **buscar los bugs de hoy en
el resto del repositorio**, porque el patrón que se acababa de describir es
precisamente *"el arreglo se aplicó en una pieza y no en su hermana"*. Aparecieron
en siete sitios más, ninguno detectado hasta ahora.

**a) El patrón numérico roto vivía en TRES copias.** Se arregló en
`cruzar_303_importes.py` y se dejó intacto en `extraer_303_pdf.py:53` y
`reconocer_303_pdf.py:66` — los dos scripts del 303 que ya existían. Es decir: se
cometió el mismo error que se estaba documentando, en la misma sesión.

**Arreglado de raíz, no parcheado tres veces.** El patrón y su conversión viven
ahora en un solo sitio, `contrato_datos.py`, que ya era la única regla de números
del proyecto:

- `RE_IMPORTE_EN_TEXTO` — localiza importes dentro de texto libre (una página de
  PDF, un OCR). Trabajo distinto de `parse_numero()`, que convierte un texto que
  ya se sabe que es un número.
- `importes_en_texto(texto)` — localiza y convierte, usando `parse_numero()`, de
  modo que no hay dos formas de interpretar `1.234,56` según quién lo lea.
- `parse_numero()` ampliado: ahora también limpia **espacio duro (` `) y fino
  (` `)**, que es lo que mete la extracción de PDF donde el documento
  mostraba un separador de millar. Sin eso, `12 345,67` salía `INVALID` por un
  espacio que el ojo humano no distingue del normal.

Los tres ficheros importan esa definición. `ensayo_cruce_303.py` comprueba
explícitamente que **el cruce no tenga su propia copia** (`cruce.NUM_ES is
contrato_datos.RE_IMPORTE_EN_TEXTO`): es la única defensa real contra que la
familia vuelva.

**b) El `subprocess.run` sin `encoding` estaba latente en CINCO llamadas más.**
`ensayo_corpus_roto.py:61` y las **cuatro** de `test_privacidad.py`. No habían
reventado todavía por pura suerte —depende de qué carácter concreto imprima el
proceso hijo— pero eran la misma bomba. Las 18 llamadas del repositorio declaran
ya `encoding` explícito.

**c) Y se convirtió en auditor permanente, el 12º.** `check_subprocess_encoding()`
recorre el **AST** (no el texto: la lección del 21-08 con `check_cableado` fue que
un auditor que mira la forma acusa a inocentes en cuanto alguien reformatea) y
exige `encoding` en toda llamada con `text=True`.

**Probado que sabe ponerse rojo**, sobre una copia temporal del repositorio con el
bug reintroducido a propósito: `❌ sin encoding (revientan en consola cp1252):
ensayo_corpus_roto.py:67`. Un auditor que solo se ha visto en verde no ha
demostrado nada — misma disciplina que la batería de privacidad.

> **La lección de método, que vale más que los siete arreglos:** documentar un
> patrón de bug no basta. Hay que **barrer el repositorio buscándolo**, en la
> misma sesión, antes de dar el hallazgo por cerrado. Aquí el barrido multiplicó
> por más de dos los defectos encontrados, y uno de ellos se había introducido
> ese mismo día al arreglar los otros.

### 8. Cuarto repaso: un defecto introducido AL ARREGLAR los otros

Cuarta pasada, esta vez leyendo críticamente el código escrito ese día en vez de
volver a ejecutar lo ya verificado. Barrido de código muerto sobre el AST
(importaciones sin usar, funciones nunca llamadas, constantes nunca leídas).

**El hallazgo, y es de la misma familia que todo lo demás de hoy:** al unificar
el patrón de importes se dejó la conversión escrita como
`abs(parse_numero(m).valor)` **a pelo**. `parse_numero()` devuelve `valor=None`
cuando el estado es `INVALID`, así que **un solo importe no convertible en un PDF
lanzaba `TypeError`**, el `except` del bucle lo contaba como *"PDF ilegible"*, y
**se perdían TODOS los importes de ese documento por culpa de uno**.

Un fallo de una línea que descarta un documento entero, en silencio, y contado
como si el problema fuera el PDF. Es exactamente el patrón que esta sesión lleva
persiguiendo — cometido, otra vez, al arreglar la versión anterior del mismo.

Corregido usando `importes_en_texto()`, que **filtra por estado en vez de
convertir a ciegas**. Efecto secundario bueno: esa función pasa de estar usada
solo por su propio test a usarse en producción, que es donde tenía que estar.
Con prueba de regresión propia en `ensayo_cruce_303.py` (22 comprobaciones).

**Lo demás del barrido salió limpio**, y conviene decirlo con el mismo detalle:
una importación sin usar en `diag_baseimpo.py` y una constante vestigial en
`extraer_303_pdf.py` (`TRIM_A_NUM`, resto de copiar un bloque; ese script solo
comprueba el nombre del fichero, no extrae el trimestre). Los otros cuatro avisos
—`canonizar()`, `importes_en_texto()`, `NATURALEZAS`, `TIPOS_IVA_CONOCIDOS`—
eran **falsos positivos** del comprobador, que solo mira dentro del propio
fichero: los cuatro se usan desde otros módulos, verificado uno a uno. **Cero
código muerto real en el repositorio.**

**Y una prueba que no se había hecho nunca: clonar `master` en limpio desde
GitHub y ejecutarlo.** 108 ficheros, 16 comprobaciones en verde, ningún fichero
`_LOCAL`, ningún dato real. `master` funciona por sí solo en cualquier máquina —
que es justo lo que no se cumplía antes de ayer y nadie había comprobado.

> **Decisión deliberada: el comprobador de referencias rotas NO se convierte en
> auditor permanente.** Produce demasiados falsos positivos (`Diario.dbf` y
> compañía viven *dentro* de los contenedores `.DAT`, no en el repositorio), y
> este proyecto ya tiene escrito que *"un auditor que grita cuando no toca acaba
> ignorándose, y entonces no avisa cuando sí toca"*. Se queda como herramienta
> puntual, y esa es la respuesta correcta, no una excusa.

### 9. PENDIENTE, y es lo primero de la próxima sesión

**Arreglar `reconstruir_303.py` para que derive la base del asiento**, como ya
hace `retro_semaforo.reconstruir_compra()`. No es trivial: hoy procesa línea a
línea mirando solo 472/477, y necesita **agrupar por `ASIEN`** y leer las líneas
de contrapartida (6xx compras, 7xx ventas). Viable: el 98,6% de los asientos las
tienen. Hasta que eso esté, `303_LOCAL.json` **no describe ninguna contabilidad**
y ningún cuadre contra el 303 puede funcionar.

Cabo suelto menor, anotado: de 150 contenedores, **95 (63%) no tienen
`Diario.dbf` dentro**. Puede ser normal (copias parciales), pero conviene
explicarlo antes de fiarse de cualquier recuento sobre "el corpus completo".

---

## 26-08-2026 (cierre real de sesión) — `master` estaba congelado desde el primer commit: fusionado. Reinterpreta las 5 rondas de auditoría externa

**Este es probablemente el hallazgo más importante de toda la sesión, y corrige
una conclusión repetida en las cinco entradas de auditoría externa de arriba.**

Al preparar el traspaso a LOCAL, se intentó fusionar `claude/repository-
analysis-xbb60b` (la rama de trabajo de todo lo de hoy) contra `master` para
que nada se perdiera. Git se negó: `fatal: refusing to merge unrelated
histories`. Al inspeccionar `origin/master` directamente: **782 líneas en
`motor_veredicto.py`, título de módulo "MOTOR DE VEREDICTO MECANICO — v1"**,
sin `contrato_datos.py`, sin `EMPEZAR_AQUI.md`, con `_f()` convirtiendo
ausencia en 0.0, `guard_confianza_captura` con el default `'OK'` sin
protección, `guard_fecha_posterior_alta` comparando solo el año, y
`calcular_veredicto()` con la lista manual de críticos — **exactamente y con
precisión los mismos hallazgos, número de línea aproximado incluido, que las
cinco rondas de auditoría externa fueron repitiendo sesión tras sesión.**

**Reinterpretación necesaria:** las cinco entradas de arriba concluían que la
auditoría externa citaba "código desactualizado" o "no ejecutaba de verdad".
Eso era cierto para la comparación contra `claude/repository-analysis-
xbb60b`, la rama de trabajo — pero **`master` es la rama por defecto de
GitHub, lo único que ve cualquiera que clone el repositorio sin especificar
rama, y lo que sirve un enlace `github.com/.../blob/master/...`**. Las
auditorías no estaban leyendo una copia vieja de memoria: estaban leyendo,
correctamente, el código real y público del proyecto — que llevaba desde
`ea36e8d` (el primer commit del repositorio, antes incluso de las
correcciones del 28-07-2026) sin recibir NINGÚN commit posterior. Todo el
trabajo de endurecimiento del motor, la Fase 0, las auditorías y la sesión de
hoy vivía exclusivamente en ramas `claude/*`, nunca fusionadas.

**No se perdió ningún archivo de valor:** comparado árbol contra árbol, los
únicos 6 ficheros exclusivos de `master` eran exactamente los del módulo de
cripto ya eliminados deliberadamente hoy mismo (`guard_g7_ledger.py` y 4
`.md`) — nada que recuperar. Los 35 ficheros exclusivos de la rama de trabajo
son todo el motor endurecido, `contrato_datos.py`, los tests, los ensayos y
la documentación operativa.

**Arreglado con la técnica correcta para "unrelated histories" sin perder
rastro**: `git merge --allow-unrelated-histories -s ours master` desde una
rama temporal basada en `claude/repository-analysis-xbb60b` — el árbol
resultante es idéntico, byte a byte, al de la rama de trabajo (verificado con
`git diff --stat`, sin salida), pero el commit tiene DOS padres, así que el
historial completo de `master` sigue siendo alcanzable como ancestro, no se
descarta. Empujado a `origin/master` como fast-forward puro (`59566c0 →
87f7aa3`, sin forzar nada). **Verificado en un clon nuevo y limpio, desde
cero, directamente de GitHub:** 1.585 líneas, `contrato_datos.py` presente,
`test_motor_veredicto.py` 36/36, `test_adversarial.py` 112/112.

> **Lección para toda auditoría futura, externa o propia:** antes de dar por
> "desactualizada" una discrepancia con GitHub, comprobar primero **qué
> rama** se está mirando. La jerarquía de verdad de este archivo (Código →
> Tests → Git → documentación) daba por hecho un único estado de "el
> código" — y durante semanas hubo dos: el real, en ramas de trabajo, y el
> público, congelado en `master`. Ahora coinciden.

## 26-08-2026 (cierre de sesión) — Mega-auditoría propia: todo lo que las 5 rondas externas no tocaron

Tras cinco rondas de auditoría externa centradas casi enteramente en
`motor_veredicto.py`, Diego pidió una auditoría propia de **todo lo demás**:
`contrato_datos.py`, `nif_check.py`, `orquestador.py`, `captura_orquestador.py`,
`layout_diario_contaplus.py`, la barrera de privacidad, el `.gitignore`, la
GitHub Action, y la coherencia entre documentación y código. Objetivo:
dejarlo todo verificado y limpio para continuar en LOCAL sin perder nada.

### 🔴 Dos hallazgos reales, nuevos, y de la misma familia — arreglados

**Ningún caso de las cinco auditorías externas los vio**, porque los cinco se
quedaron dentro de `motor_veredicto.py` y estos dos viven justo en la
costura de después: el motor da VERDE, y el paso siguiente no sabe leer lo
que el motor sí sabe leer.

1. **`layout_diario_contaplus.py::generar_asiento_desde_factura()` no
   entendía el formato español.** Usaba `float()` a pelo sobre `base_10`,
   `base_4`, `base_21`, `base_total`, `iva_total`, `total_factura`,
   `irpf_retencion` — los mismos campos que `contrato_datos.parse_numero()`
   sí sabe leer en formato español (`'132,90'`), y que por eso el motor SÍ da
   VERDE (`test_adversarial.py` FAMILIA G ya lo prueba con `'1.328,90'`).
   **Reproducido antes de arreglar nada:** una factura VERDE con importes en
   coma decimal reventaba con `ValueError` en el ÚLTIMO paso — el objetivo
   declarado del producto, *"foto de la factura → motor → fichero
   importable → ContaPlus"* — y `escribir_xdiario()` la descartaba en
   silencio, contada solo como `"1 ValueError"` sin más explicación.
   `ensayo_xdiario.py` no lo cazaba porque solo probaba el formato español en
   la FECHA (ya arreglado el 21-08), nunca en los importes.

   Arreglado: nueva función `_num()` dentro de `generar_asiento_desde_factura`
   que usa `contrato_datos.parse_numero()`. Nuevo caso en `ensayo_xdiario.py`
   ("importes en formato español"), que pasó de 6 a 7 facturas buenas — se
   corrigió también un conteo `== 6` escrito a mano que se habría
   desincronizado (`len(casos)` ahora). 31/31 en verde.

2. **`orquestador.py::construir_historico_y_secuencia()` perdía en silencio
   toda factura con importes en formato español.** Mismo patrón: `float()` a
   pelo con un `except ValueError: t = 0`, y como `if t > 0` es la condición
   para entrar en el histórico, ninguna factura con `'132,90'` llegaba nunca
   a alimentar `guard_importe_atipico` ni `guard_secuencia_documental_
   proveedor` para ese proveedor. **Reproducido:** tres facturas reales con
   totales en coma decimal producían un histórico `{}`, vacío. No rompía
   nada de forma visible — simplemente apagaba dos guards en silencio para
   cualquier proveedor cuyas facturas vinieran así, exactamente el patrón
   "protección apagada sin que nadie lo note" que este proyecto ya cerró dos
   veces antes (nombre vs. NIF en las cuatro cachés, 21-08-2026).

   Arreglado con `contrato_datos.parse_numero()`. **`orquestador.py` no tenía
   ningún ensayo propio** — creado `ensayo_orquestador.py` (5 pruebas: el bug
   reproducido, que el formato inglés no se rompe, y que un total ausente/
   ilegible no cuenta como cero) y cableado en `audit_project.py` como
   décimo auditor.

### 🟡 Un tercer hallazgo real, de robustez, arreglado

**`captura_orquestador.py::procesar_carpeta()` usaba las claves de la
PRIMERA foto leída como cabecera del CSV de salida.** Si una foto posterior
devuelve un JSON con una clave que la primera no tenía (plausible: el modelo
no siempre incluye las mismas claves opcionales, ej. `tramos_iva` o
`confianza_campos`), `csv.DictWriter` revienta con `ValueError` y se pierde
el CSV de **toda la carpeta**, incluidas las fotos ya leídas bien.
Reproducido con un caso mínimo. Arreglado: cabecera = unión de las claves de
TODAS las filas, en orden de aparición — no requiere adivinar qué campo
concreto lo dispararía, defiende contra cualquiera.

### 🟢 Verificado en profundidad, sin defecto: `contrato_datos.py` y `nif_check.py`

Los dos ficheros que sostienen la frontera de datos y la identidad fiscal se
leyeron completos y se probaron con una batería de casos límite manual
(formatos numéricos mixtos y con miles: `'1.234.567,89'`, NIE, NIF-IVA UE,
cadenas de longitud 1/8/9 con formas ambiguas). Los dos se comportan
exactamente como documentan. Es la primera vez que se auditan a este nivel de
detalle — las cinco rondas externas nunca los tocaron.

### 🟠 Dos inconsistencias documentales cerradas (no afectan al motor)

- `CLAUDE.md` y `captura_orquestador.py` referenciaban un `README.md` que
  **nunca ha existido en este repositorio** (confirmado también por la
  primera auditoría externa). `CLAUDE.md` corregido para reflejar la
  práctica real (docstring, no catálogo aparte); `captura_orquestador.py`
  apunta ahora a `.claude/rules/datos.md`, donde sí vive esa decisión.

### Verificación de cierre de la mega-auditoría

`test_motor_veredicto.py` 36/36, `test_adversarial.py` 112/112,
`test_privacidad.py` 30/30, `ensayo_xdiario.py` 31/31, `ensayo_orquestador.py`
5/5 (nuevo), y los 10 auditores de `audit_project.py` en verde (antes 9) salvo
las dependencias de captura (normal en Cloud). Escáner de privacidad sobre
los 102 ficheros del repositorio: sin hallazgos.

**Lo que NO se tocó, deliberadamente:** ningún dato real, ningún script de
Fase 0 que exige el corpus local, ninguna decisión de producto. Todo lo de
esta entrada es código y tests, verificable por cualquiera que clone el repo.

## 26-08-2026 (noche, quinta ronda) — Quinta auditoría externa (ChatGPT): mismo patrón, un hallazgo demostrado falso con cifras propias del repo

Verificada por ejecución, misma disciplina. **Repite, palabra por palabra en
varios casos, las mismas cuatro afirmaciones ya refutadas en las rondas 3 y 4**
(`_f()` convierte ausencia en 0 y esto llega a producción, `guard_retencion_
vs_error` da OK sin que el IRPF confirme la hipótesis, `guard_signo_efectivo`
da OK a un negativo sin `tipo_documento`, `guard_nif_casa_historico` da FALLO
cuando el NIF no está en el maestro) — las cuatro re-verificadas con grep
directo sobre el código actual, mismo resultado: las cuatro siguen cerradas
desde el 19/20-08-2026, sin regresión.

**Un hallazgo nuevo en esta ronda, y resultó ser el más fácil de refutar de
las cinco auditorías:** afirma que falta "una batería específica de falsos
verdes" que demuestre que el motor no puede fabricar VERDE cuando falta
evidencia crítica, y propone crearla como el "siguiente salto de calidad".
**Ya existe, se llama `barrido_falsos_verdes.py`, y sus números están en este
mismo archivo desde el 21-08-2026:**

```
1.786 mutaciones de un solo campo sobre facturas VERDE
1.644 cazadas por el motor, 87 equivalentes (nada que cazar)
0 escapes sin explicar (100% de deteccion sobre lo detectable)
control positivo: 172 de 172 escapes detectados con el motor saboteado
```

Es, en la práctica, más rigurosa que la batería que la auditoría propone
crear (`TEST_FALSE_GREEN_001..008`, ~8 casos manuales): mutación exhaustiva
de campo por campo sobre datos reales, no una lista de casos escritos a mano.

Sin cambios de código en esta ronda — quinta consecutiva sin un hallazgo
nuevo y real tras la del `anti_duplicado`/`reevaluar_tras_correccion`
(ronda 3). Se mantiene la conclusión operativa ya escrita en la ronda 4: las
afirmaciones de esta herramienta externa que ya constan como CERRADAS aquí no
se re-verifican desde cero salvo que aporten código o un caso reproducible
nuevo, no prosa repetida.

## 26-08-2026 (noche, más tarde) — Cuarta auditoría externa (ChatGPT), función por función: sin hallazgo nuevo grave, un patrón que sí importa

Misma disciplina que las tres anteriores. Esta vez con una diferencia notable
respecto a las tres rondas previas: **no apareció ningún bug nuevo, real y en
producción.** Lo más señalable no es un hallazgo de código, es un patrón en
la propia auditoría.

### 🔁 El patrón que hay que anotar: la misma afirmación falsa, tercera vez

La auditoría vuelve a decir que `guard_cuenta_gasto_coherente`,
`guard_tipo_producto_iva_semantico` y `guard_tipo_operacion_especial` "existen
con test propio pero no están cableados a `evaluar_fila_v4`/
`calcular_veredicto_v4`". **Es la tercera ronda de auditoría externa que
repite exactamente esta afirmación**, y las tres veces es falsa: están
cableados desde el 19-08-2026 (línea 1259-1265 de `motor_veredicto.py`) y SÍ
cambian el veredicto — se verificó de nuevo con una ejecución en vivo:

```
factura con cuenta_debe=218000 (inmovilizado), aritmetica perfecta
-> VEREDICTO: AMBAR (sería VERDE sin este guard)
-> tipo_operacion_especial: AMBAR "cuenta de destino 218000 es del grupo 2..."
```

También repite (segunda vez) que `guard_nif_casa_historico` da FALLO cuando el
NIF no está en el maestro — cerrado el 20-08-2026, ahora da `NO_COMPROBADO`
("proveedor NUEVO... no es un error, es un alta que decidir") — y (tercera
vez) el caso `irpf` sin confirmar en `guard_retencion_vs_error` y el
`guard_signo_efectivo` con negativo sin `tipo_documento`, ambos cerrados el
19-08-2026 y ya refutados dos veces con evidencia en las entradas de arriba.

**Conclusión operativa:** esta herramienta de auditoría externa concreta no
está leyendo el estado real del repositorio en cada ronda — repite el mismo
subconjunto de hallazgos (algunos reales en su día, ya cerrados) en vez de
progresar. A partir de aquí, cualquier afirmación suya que ya conste como
CERRADA en este archivo se descarta sin re-verificar salvo que aporte una
línea de código o un caso reproducible nuevo, no una descripción en prosa.

### 🟡 Dos observaciones sí eran ciertas, ninguna urgente, ninguna con caso real todavía

- **`TOL = 0.02` es una única constante global** reutilizada en aritmética de
  IVA, cuadre total, suma de tramos y retenciones. Es una simplificación
  deliberada y medida (documentada contra 91 facturas reales, margen 2x), no
  un bug — pero mezclar la semántica de "redondeo de IVA" con "tolerancia de
  retención" bajo el mismo número es una decisión a revisar si algún día un
  caso real la fuerza en direcciones opuestas. No se toca sin ese caso.
- **`guard_ejercicio_coherente` no tiene forma de representar la excepción
  que su propio docstring promete** ("NO_APLICA si se declara explícitamente
  que es un gasto de ejercicio anterior aportado a propósito") — no existe
  ningún parámetro en toda la cadena de llamada (confirmado con grep en
  `motor_veredicto.py` y `orquestador.py`) para declarar esa excepción. Falla
  del lado seguro (una factura de ejercicio anterior legítima da FALLO/ROJO,
  fuerza revisión humana, nunca un falso VERDE), así que es un defecto de
  experiencia, no de seguridad. Declarado como deuda; no se implementa sin un
  caso real de gasto de ejercicio anterior que lo pida.

Sin cambios de código en esta ronda — no había nada que reproducir.

## 26-08-2026 (noche) — Tercera auditoría externa (ChatGPT), línea por línea del motor: 1 hallazgo real y grave, resto ya cerrado o no reproducible

Misma disciplina que las dos anteriores: cada afirmación se reprodujo contra
el código actual antes de aceptarla. Patrón que se repite y ya es sistemático
en las tres rondas: varios de los "hallazgos" citan, casi palabra por palabra,
el comportamiento ANTIGUO que los propios comentarios de `motor_veredicto.py`
describen como ya corregido (ej. el ejemplo exacto `irpf=999` vs
`diferencia=150` que cita el código como el caso que motivó el arreglo del
19-08-2026, presentado por la auditoría como si fuera el estado actual). Los
números de línea citados (782 líneas, 32 funciones) tampoco coinciden con el
fichero real (1.571 líneas, 47 funciones): la auditoría no está leyendo HEAD.

### 🔴 Un hallazgo SÍ era real, grave, y reproducible de punta a punta

**`reevaluar_tras_correccion()` podía marcar una factura como duplicada de sí
misma.** `guard_anti_duplicado()` registra la clave documental
(NIF+nº documento+fecha+total) en el set `vistos_duplicado` en el momento en
que la evalúa, antes de saber el veredicto final de la fila. Es el diseño
correcto para detectar duplicados dentro de una tanda — pero
`reevaluar_tras_correccion()` reutiliza ese MISMO set cuando el asesor corrige
un campo de una factura AMBAR y la reenvía, y la mayoría de correcciones
reales (IRPF, categoría de producto, tipo de documento…) no tocan los cuatro
campos de la clave. **Reproducido antes de arreglar nada:** una factura AMBAR
por duda de captura, corregida sin tocar su identidad, volvía **ROJO
"duplicado exacto de una factura ya vista"** — contra sí misma. Esto rompía
el flujo declarado del propio proyecto (AMBAR → corrección humana → VERDE
corregido) en el caso normal, no en un borde raro.

Arreglado: `reevaluar_tras_correccion()` descarta la clave de la propia
factura de `vistos_duplicado` antes de reevaluar (si de verdad coincide con
OTRA factura distinta de la tanda, `guard_anti_duplicado` la vuelve a detectar
igual, porque la reinserta dentro de `evaluar_fila_v4`). Nueva prueba de
regresión en `test_motor_veredicto.py` (36/36 ahora) que reproduce el flujo
completo: AMBAR → corrección de un campo no identificativo → debe llegar a
VERDE (corregido), no ROJO.

### ❌ Lo que esta tercera auditoría afirmó y resultó ser FALSO o desactualizado

| Afirmación | Realidad verificada |
|---|---|
| `_f()` convierte ausencia/vacío en `0.0`, violando "ausencia ≠ OK" | Cierto para `_f()`, pero `evaluar_fila_v4` (producción) no la usa para los importes — usa `contrato_datos.canonizar()/canon.num()`, que distingue MISSING/ZERO/INVALID/VALUE desde el 19-08-2026, con `guard_integridad_datos` como frontera previa. El propio docstring de ese guard describe este bug como ya cerrado |
| `guard_retencion_vs_error` acepta una retención típica (ej. 19%) sin que el IRPF declarado la confirme | Cerrado el 19-08-2026 — el guard exige que `irpf` coincida con la diferencia o declara `NO_COMPROBADO`; el propio código cita el caso `irpf=999 vs diferencia=150` como el bug ya corregido, con esos mismos números |
| `guard_signo_efectivo` da OK a un importe negativo sin `tipo_documento` | Cerrado el 19-08-2026 — da `NO_COMPROBADO` explícitamente en ese caso |
| `guard_cuenta_gasto_coherente`, `guard_tipo_producto_iva_semantico`, `guard_tipo_operacion_especial` fuera de `evaluar_fila_v4` | Cableados desde el 19-08-2026 (mismo hallazgo ya refutado en la ronda anterior) |
| `nif_cliente_titular=None` no llega desde el orquestador | `orquestador.py` acepta `--nif-titular` desde el 19-08-2026 (mismo hallazgo ya refutado) |
| `audit_project.py` declara "21/21" solo por la cadena `"TODAS LAS PRUEBAS PASAN"` | Ya cuenta `check()` declarados vs. `OK` reales y los cruza, desde el 19-08-2026 (mismo hallazgo ya refutado) |

### 🟡 Confirmado pero de prioridad baja, declarado sin arreglar

- **`guard_nif_casa_historico` compara `nif.strip()` contra las claves del
  maestro sin normalizar mayúsculas/minúsculas.** Confirmado en el código: no
  hay `.upper()`. No se ha arreglado porque no hay un caso real que lo pida
  todavía (regla de `CLAUDE.md`) — a diferencia del bug de `anti_duplicado`,
  que se reprodujo con datos de entrada perfectamente normales.
- Comparación `< TOL` en vez de `<= TOL` en los guards de aritmética/cuadre:
  un descuadre de exactamente 0,02 € da FALLO. Podría ser intencional (margen
  estricto); si aparece un caso real en el borde, revisar entonces.
- Legacy `evaluar_fila_v2/v3` y test no integrado en `pytest`: mismos hallazgos
  ya declarados como deuda técnica en la entrada anterior de hoy.

Verificado tras el arreglo: `test_motor_veredicto.py` 36/36,
`test_adversarial.py` 112/112, `test_privacidad.py` 30/30, `audit_project.py`
en verde salvo dependencias de captura (normal en Cloud).

## 26-08-2026 (tarde) — Segunda auditoría externa (ChatGPT): 3 hallazgos reales arreglados, varios falsos por código desactualizado

Diego trajo dos auditorías externas hechas con ChatGPT sobre el proyecto. Se
verificó cada afirmación **ejecutando el código actual**, no aceptándola de
palabra — misma disciplina que pide este archivo sobre sí mismo. Resultado:
la primera auditoría (arquitectónica) era mayormente correcta pero analizaba
un snapshot antiguo del repo; la segunda decía haber "ejecutado el código y
creado casos adversariales", pero su hallazgo estrella (una fecha
`2026-99-99` que supuestamente daba VERDE) **da AMBAR al ejecutarlo de
verdad** — ya estaba cerrado el 21-08-2026. No se dio nada por bueno sin
reproducirlo.

### ⚠️ Sigue sin resolver, y es lo más importante de las dos sesiones de hoy

**El repositorio de GitHub es PÚBLICO ahora mismo** (`curl
https://api.github.com/repos/LaRuinaDeMago/Os-Asesor-a` → `"private": false`),
no privado como dice este mismo archivo más abajo y como asume `.claude/rules/
datos.md` entero. No hay herramienta disponible en esta sesión Cloud con
permiso para cambiarlo — **lo tiene que hacer Diego a mano**: `Settings →
General → Danger Zone → Change repository visibility → Private`. No hay
indicio de fuga de dato real (el contenido está limpio, verificado), pero la
barrera del candado del repo lleva rota un tiempo indeterminado.

### 🟢 Tres hallazgos reales de la segunda auditoría, verificados y arreglados

1. **`guard_confianza_captura` convertía la AUSENCIA del campo `verificacion`
   en la misma certeza que una lectura confirmada.** `fila.get('verificacion',
   'OK')` — si la captura nunca escribe esa clave (fallo de la API, prompt que
   cambia, campo renombrado: el mismo modo de fallo que ya rompió este
   proyecto varias veces), el guard devolvía `ALTA` igual que si estuviera
   confirmado. **Probado antes de arreglar nada: una factura coherente sin esa
   clave llegaba a VERDE de verdad.** Ninguna de las 111 pruebas anteriores
   omitía la clave (todas la fijaban a `'OK'` o `'DUDA'`). Corregido: ausencia
   → `NO_COMPROBADO`, nunca `ALTA`. Nueva prueba, FAMILIA T de
   `test_adversarial.py` (112 pruebas ahora).
2. **El escáner de privacidad no reconocía un NIE** (extranjero residente,
   prefijo X/Y/Z) como posible dato identificable — su patrón de letra
   inicial no incluía esas tres letras, y además el carácter de control de un
   NIE sale del alfabeto de 23 letras del DNI, no de `[0-9A-J]` como el CIF
   (se necesitó una rama de patrón aparte, no ampliar la existente). Un NIE
   real en un fichero pasaba "sin hallazgos". Corregido en
   `scripts/privacy_scan.py`; nueva prueba en `test_privacidad.py` (30/30).
3. **`audit_project.py` no revisaba `.py` de forma recursiva** —
   `os.listdir(".")` se saltaba en silencio todo `scripts/*.py`, incluido el
   propio escáner de privacidad. Cambiado a `Path(".").rglob("*.py")`.

Verificado tras los tres arreglos: `test_motor_veredicto.py` 33/33,
`test_adversarial.py` 112/112, `test_privacidad.py` 30/30, escáner de
privacidad sobre el repo completo sin hallazgos, `audit_project.py` en verde
salvo las dependencias de captura (normal en Cloud).

### 🟠 Deuda técnica real, declarada, NO arreglada todavía (no urgente)

- **Sesgo de mirar al futuro en `orquestador.py::construir_historico_y_secuencia`**:
  construye el histórico de importes y de secuencia documental a partir de
  **todo el CSV de la tanda de una vez**, antes de evaluar ninguna fila. Una
  factura se compara contra un histórico que ya incluye su propio número de
  documento y su propio importe. No es peligroso hoy (los guards afectados
  bajan a NO_APLICA/AMBAR, nunca fabrican un OK), pero infla artificialmente
  la aparente "normalidad" de `secuencia_documental_proveedor` e
  `importe_atipico` cuando se procesan lotes grandes — afecta más a la
  medición (retro-semáforo) que a la seguridad. Arreglo correcto: construir el
  histórico de forma incremental, fila a fila, no de una sentada.
- **`evaluar_fila_v2`/`evaluar_fila_v3`/`calcular_veredicto_v2` siguen vivos
  dentro de `motor_veredicto.py`** sin que nada del repo los llame ni ningún
  test los cubra — código legacy dentro del fichero más sensible del
  proyecto. Heredan además el bug de `_f()` con el formato español
  (`_f('1.234')` da `1.234`, no `1234.0`: el parser de producción,
  `contrato_datos.parse_numero`, ya resuelve esa ambigüedad de forma
  explícita y declarada, pero `_f()` no la usa). Sin riesgo real mientras
  nadie los llame; candidatos a borrar en la próxima limpieza de motor,
  siguiendo la misma disciplina de tests antes/después.
- **`aprender_cuenta_gasto()` no valida que la cuenta que confirma el asesor
  exista en el PGC** antes de guardarla con `confianza: CONFIRMADA_ASESOR`
  (la más alta). Bajo riesgo — es un paso ya mediado por un humano — pero
  merece una validación mínima contra `PGC_CUADRO_CUENTAS.json`.
- `test_motor_veredicto.py` es un script de aserciones manuales, no un módulo
  `unittest`/`pytest` (`python -m unittest discover` no lo encuentra). No es
  un bug — `audit_project.py` ya lo ejecuta directamente y cruza el conteo de
  `check()` declarados contra los que pasan, así que no depende de un texto
  fijo — pero conviene saberlo si se integra CI externo en el futuro.

### ❌ Lo que la segunda auditoría afirmó y resultó ser FALSO o desactualizado (verificado por ejecución)

| Afirmación | Realidad verificada |
|---|---|
| Fecha `2026-99-99` sobre factura coherente → VERDE | **AMBAR**, cerrado el 21-08-2026 (`_anio_de` usa `contrato_datos.parse_fecha`, no `fecha[:4]`) |
| `nif_check.py` no soporta NIE (X/Y/Z) | Soportado desde el 25-08-2026, con el algoritmo correcto (X→0, Y→1, Z→2) |
| `DE123456789` (NIF-IVA UE) da FALLO→ROJO | Da `NO_COMPROBADO` explícitamente — no hay rama que lo convierta en ROJO |
| `guard_cuenta_gasto_coherente`, `guard_tipo_producto_iva_semantico`, `guard_tipo_operacion_especial` no están en `evaluar_fila_v4` | Los tres están cableados, línea 1248-1254, desde el 19-08-2026 |
| `guard_cuenta_gasto_coherente` no compara la cuenta propuesta contra el histórico | Sí compara, desde el 21-08-2026 (antes SÍ era así — arreglado ese día) |
| El escáner de privacidad no distingue `.DAT`/ZIP por contenido | Ya detecta por firma de bytes desde el 19-08-2026 |
| `audit_project.py` compara con el string fijo `"21/21 OK"` sin contar nada | Ya cuenta `check()` declarados vs. `OK` reales y los cruza, desde el 19-08-2026 |
| Ficheros de otro dominio (cripto) siguen mezclados en el repo | Eliminados esta misma tarde, antes de esta segunda auditoría (ver entrada anterior) |
| `motor_veredicto.py` tiene 712 líneas / 19 guards | Tiene 1.560 líneas / 28 funciones `guard_*` — la auditoría trabajó sobre una versión de hace semanas |

**Lección para las próximas auditorías externas (humanas o de otra IA):**
tratarlas como hipótesis a verificar por ejecución, nunca como hechos —
exactamente la regla que este archivo ya aplica sobre sí mismo con los tests.
Una auditoría que "dice haber ejecutado código" puede no haberlo hecho de
verdad; el único juez es correr el motor aquí y ahora.

## 26-08-2026 — Auditoría cloud completa: 5-bis ya cerrado, 6 ficheros de cripto fuera del repo

Sesión Cloud, sin datos reales, siguiendo `CLAUDE.md`: `PROJECT_STATUS.md` leído
entero, `audit_project.py` ejecutado (todo verde salvo lo ya declarado "normal":
dependencias de captura no instaladas aquí), `EMPEZAR_AQUI.md` leído entero.

**Auditoría §5-bis de `EMPEZAR_AQUI.md` (20-08-2026) verificada contra el código
actual, no contra el texto: está desactualizada, los tres hallazgos ya estaban
cerrados** — confirmado con grep, no supuesto: `triangulacion_identidad_v0.py`
ya cableado (`motor_veredicto.py:152`, `guard_triangulacion_identidad`),
`escribir_xdiario()` ya la llama `orquestador.py:230`, y `--proveedor` de
`captura_orquestador.py` ya tiene default `"gemini"` (la migración que el
documento seguía llamando "a medias" ya está hecha). Los 4 JSON invalidados
(`fase0_huella*.json`, `fase0_reagrupa.json`, `fase0_umbral.json`) ya llevan
`"INVALIDADO": true`. Nada de esto necesitaba trabajo — solo confirmarlo, para
que la próxima sesión no lo dé por pendiente otra vez.

**Lo único de §5-bis que seguía abierto y con valor real: los ficheros del
módulo de cripto (Bitget/FIFO) mezclados en este repo del motor de facturas.**
`guard_g7_ledger.py` seguía sin conectar (confirmado por `audit_project.py`) y
el propio proyecto ya documentaba que había confundido a un auditor externo.
Verificado uno a uno que ninguno lleva NIF/nombre de cliente real (son specs
de un caso propio del titular, EXP-0001, y análisis de competidores públicos)
y que nada del motor los importa. **Eliminados del repositorio** (no solo
movidos, con la venia expresa de Diego para decidir con rigor):
`guard_g7_ledger.py`, `DIA3_ESTADO_PARCIAL.md`, `DIA3_SPEC_C1_TACTICAS.md`,
`MATRIZ_COBERTURA_v1.md`, `CATALOGO_EVENTOS_v1.md`,
`TRIAJE_RONDA_2026-07-13.md` — seis, no cinco: `DIA3_SPEC_C1_TACTICAS.md` no
estaba en la lista original de `EMPEZAR_AQUI.md` pero es del mismo dominio
(spec + táctica comercial del módulo cripto) y quedó fuera por descuido, no
por decisión.

Verificado tras el borrado: `audit_project.py` — el aviso de "módulo sin
conectar" desaparece (antes marcaba `guard_g7_ledger.py`, ahora "ninguno"),
`test_motor_veredicto.py` 33/33, `test_adversarial.py` 111/111 sin cambio
(ninguno de los seis ficheros tocaba el motor). `SUBE_A_GITHUB.md` se deja
intacto: es el registro histórico de qué se auditó y subió en su día, no una
lista de lo que hay hoy — reescribirlo perdería la trazabilidad de la
auditoría de privacidad original.

## 25-08-2026 — Retro-semáforo contra el corpus real: diez arreglos, ROJO 45,97%→3,15%

**Números completos y tabla de los diez arreglos en `FASE0_RESULTADOS.md` §14
— ese archivo manda, esto es el resumen.**

Diego pidió correr `retro_semaforo.py` (mide falsos rojos: asientos ya
contabilizados y presentados que el motor marcaría ROJO hoy) contra el corpus
real completo. Cada ejecución destapó un defecto nuevo en cómo el asiento
contable se traduce al contrato del motor — nunca en el motor mismo — y se
arregló, verificó y volvió a correr, diez veces seguidas:

```
RUN 4  (tras arreglo 3)   VERDE 49,19%   ROJO 45,97%   AMBAR 4,84%
RUN 10 (tras arreglo 10)  VERDE 87,71%   ROJO  3,15%   AMBAR 9,15%
```

**Confirma, con datos reales, lo que `TECHO_Y_LIMITES.md` predijo el
20-08-2026** sin tenerlos delante: *"si dominan `cuadre_total`, `suma_tramos` y
`nif_digito_control`, el problema no es el motor: es el modelo de datos
fiscal."* Los diez arreglos están en `retro_semaforo.py` y `nif_check.py` —
deduplicación entre copias de seguridad, cabecera del `.DAT`, número de
documento, derivación de base y cuota, retención de IRPF, inversión del sujeto
pasivo, NIE y NIF-IVA extranjero. **Ninguno tocó `motor_veredicto.py`.**

Verificación de cierre antes de dar la sesión por buena: `test_motor_veredicto.py`
(30/30, 6 tests nuevos), `test_adversarial.py` (108/108 en ese momento — ver
nota de fusión abajo, ahora 111/111), cobertura de guards (26/26), escáner de
privacidad (`scripts/privacy_scan.py`) ejecutado sobre los 16 archivos
tocados —y confirmado con un control positivo real que sí lo detecta, no solo
"sin hallazgos" a ciegas—, y el diff completo de los ocho archivos
modificados releído línea a línea.

Queda abierto y caracterizado, no urgente: ~800 casos de `cuadre_total` sin
patrón dominante ya identificable, y 94 de `nif_digito_control` (46 CIF con
checksum real, 48 sin patrón). Lectura de ambos: parece señal real del
histórico, no ceguera del instrumento — pero no está descartado del todo.

### Fusión con un hilo paralelo (mismo día): robustez y rendimiento

Al ir a subir el commit de arriba, la rama había divergido: otra sesión había
corregido en paralelo, sobre la misma base, que un `.DAT` con cabecera
corrupta colgaba `retro_semaforo.py` para siempre (bucle sin condición de
salida) y que el maestro de proveedores se copiaba entero en cada fila
(cuadrático — 15+ minutos → 55 segundos al arreglarlo). Cambios
complementarios a los diez de arriba, no alternativos, pero con conflicto real
en `parse_cabecera()`: la rama de robustez añadió validaciones sobre el
algoritmo de lectura VIEJO, que esta misma sesión ya había diagnosticado y
corregido. Resuelto a mano conservando el algoritmo corregido y añadiéndole
las validaciones nuevas encima.

**El auto-merge de git dejó, por su cuenta, una referencia suelta** a una
variable (`maestro`) que el arreglo de rendimiento había eliminado —dentro de
un `except` que la habría tragado en silencio, así que cada factura inyectada
con `--inyectar` habría fallado sin avisar—. Encontrado y corregido en la
revisión posterior al merge, no antes: el propio git no lo marcó como
conflicto porque ninguna de las dos ramas había tocado esa línea en concreto.

Verificado tras la fusión: `test_adversarial.py` 111/111 (incluye FAMILIA S,
nueva, sobre por qué `TOL=0,02`), `ensayo_corpus_roto.py` 15/15 (nuevo), y una
ejecución completa contra el corpus real con resultado **idéntico, cifra por
cifra**, al de antes de fusionar — la prueba de que la fusión no perdió ni
añadió nada por accidente. Rama `claude/github-retomada-o4zyic` empujada a
GitHub, sincronizada.

### Después de la fusión: el 303, la identidad de cliente, y el residuo de NIF

**El 303 fragmentaba clientes: 507 → 24.** `reconstruir_303.py` no
deduplicaba nada entre copias de seguridad (mismo bug de origen que el
primero de `retro_semaforo.py`: 63,3% de apuntes inflados, cifra exacta
otra vez) y usaba carpeta+código como identidad de cliente, cuando el
código lo reasigna ContaPlus en cada copia — Diego confirmó que organiza
una carpeta por cliente de verdad, y `diag_profundidad_carpetas.py` (solo
cuenta carpetas, ningún nombre real) lo confirmó: 28 carpetas de nivel 1,
casi las 33 empresas reales. `clave_cliente()` pasó a usar solo esa
carpeta. Resultado: 24 clientes, 88.932 apuntes de IVA (idéntico antes y
después del cambio de identidad — las dos correcciones no se pisan).

**Undécimo arreglo: NIF/CIF incompleto (falta el dígito de control) →
SIN_DATO, no FALLO.** De los 94 residuales de `nif_digito_control`, 34 de
36 casos de longitud 8 eran un CIF o DNI real al que le faltaba
exactamente el último carácter — mismo principio que el campo de 1-2
caracteres del décimo arreglo, un escalón más arriba. Verificado contra
fuentes externas antes de tocar nada más (los 46 CIF con checksum
genuinamente incorrecto: sin evidencia de bug, se dejan como están).
`ROJO` 3,15% → **3,03%**.

**Exploración: automatizar el cuadre del 303 leyendo los PDF ya
presentados.** Diego confirmó que vive en `\\PC01\Documentos`, con
"prácticamente todos los datos de la asesoría" — nunca navegada ni
listada directamente; solo scripts que Diego ejecuta y que devuelven
agregados. Los PDF llevan texto seleccionable de verdad, así que en
principio no hace falta DPA (extracción mecánica, no lectura semántica).
Fase 1 (`reconocer_303_pdf.py`, solo cuenta patrones): 1.168 PDF del 303
de 14.386 totales, etiquetas "Casilla NN" en el 98-99% — señal muy limpia.
Fase 2a (`extraer_303_pdf.py`, extrae y se auto-valida por consistencia
interna, nunca deja ver un valor): **falló, 1,2% de consistencia** — la
proximidad en texto plano no basta para un formulario tabular. Se decidió
NO seguir invirtiendo en el extractor antes de tener el número real:
la vía barata (comparar 5-10 trimestres a mano contra `303_LOCAL.json`)
va primero, seguido de decidir si merece la pena un extractor consciente
de tabla/posición. **Pendiente de retomar mañana.**

`requirements.txt` actualizado con `pdfplumber` (usado por las dos
fases de arriba). Verificación final de cierre: `test_motor_veredicto.py`
33/33, `test_adversarial.py` 111/111, `ensayo_retro_semaforo.py` 34/34,
`ensayo_corpus_roto.py` 15/15, escáner de privacidad sobre el repositorio
COMPLETO (no solo lo tocado hoy) — sin hallazgos.

## 21-08-2026 — Sesión cloud de verificación: qué cambió y qué mide ahora

Un día entero sin tocar datos reales, buscando defectos en vez de añadir
funciones. Once defectos, y **ninguno estaba dentro de una pieza: todos estaban
en las costuras** — entre una pieza y la siguiente. Las piezas tenían test
propio; lo que nadie había ejecutado nunca era la cadena.

### Los defectos, por gravedad

| | Qué pasaba | Dónde |
|---|---|---|
| **P0** | El xDiario emitía **asientos DESCUADRADOS** (haber sin debe) para toda factura sin desglose — que desde ese mismo día es el caso normal | `layout_diario_contaplus.py` |
| **P0** | `guard_cuenta_gasto_coherente` **no comparaba nada**; su rama `FALLO` llevaba semanas siendo código inalcanzable | `motor_veredicto.py` |
| **P0** | Un desglose contradictorio (`base_21=0` con `base_total=1000`) daba **VERDE**: MISSING vs ZERO otra vez | `contrato_datos.py` |
| **P0** | La barrera de privacidad **no veía una clave asignada** sin prefijo conocido | `scripts/privacy_scan.py` |
| **P0** | `--emitir-cartera` **no escribía nada, nunca** | `retro_semaforo.py` |
| **P1** | Una fecha `15/03/2026` (formato español) daba ÁMBAR en el motor y **reventaba la exportación entera** en el xDiario | tres guards + layout |
| **P1** | El `€` y las comillas curvas **tumbaban la exportación completa** (latin-1 en vez de cp1252) | `layout_diario_contaplus.py` |
| **P1** | Cuatro guards se **apagaban en silencio** si el nombre del proveedor cambiaba (las cachés se consultaban por nombre, no por NIF) | `motor_veredicto.py` |
| **P1** | `validar_captura_historica.py` imprimía *«TASA DE ACIERTO 0.0%, FALSOS VERDES 0»* cuando **no había podido leer el fichero** (separador `;` de Excel) | idem |
| **P1** | Un ROJO con seis defectos reportaba **uno**: seis vueltas para una factura | `motor_veredicto.py` |
| **P1** | La clasificación `[CRITERIO]`/`[FALTA DATO]` **no la leía nadie** | (faltaba `cola_revision.py`) |

### Lo que ahora se mide y antes no

- **Cobertura útil de guards: 26/26.** No "están cableados": han llegado a decir
  que no, al menos una vez, en alguna prueba.
- **1.786 mutaciones de un solo campo sobre facturas VERDE → 0 escapes sin
  explicar** (100% sobre lo detectable). Los 2 campos sin redundancia interna —el
  nº de documento y el nombre— se cuentan aparte y se declaran, no se esconden en
  el denominador.
- **El AMBAR del retro-semáforo, desglosado por a qué se debe.** Sobre corpus
  sintético salía 51,04% ÁMBAR y el atribuible a las facturas era **0,0%**: todo
  era el instrumento (el diario no trae el NIF del titular, y el maestro se
  acumula sobre la marcha). Ese matiz decide cómo se lee el primer número real.
- **Siete auditores**, todos dentro de `audit_project.py`. Los cuatro nuevos
  encontraron defectos reales en su primera ejecución.

### Lo que se puede hacer en LOCAL que antes no

| | |
|---|---|
| `reconstruir_303.py` | Agrega bases y cuotas de IVA por trimestre (casillas 01-09 y 28-29) para cuadrarlas contra el 303 presentado. **La única verdad externa del proyecto**, sin usar hasta hoy |
| `cola_revision.py` | Convierte el `veredicto.csv` en un plan de trabajo agrupado **por causa**: *«23 facturas: falta el desglose»* es UNA tarea, no 23 |
| Factura de cámara → VERDE | Antes toda factura sin desglose por tipos era ÁMBAR para siempre. Ahora las del **21% y del 0%** llegan a VERDE — y solo esas dos, porque son los únicos tipos que no se pueden fabricar mezclando (demostrado sobre 400.000 mezclas con aritmética exacta) |

### Lo que sigue sin poder saberse aquí

Ninguna de estas cifras dice nada del mundo real: el corpus es sintético. Lo que
demuestran es que **la cadena arranca y no miente**. La medición sigue estando en
el PC de la asesoría, y sigue siendo lo que falta.

---

## FASE ACTUAL
FASE 0 — Auditoría de privacidad: CERRADA (31-07-2026).
FASE 1 — GitHub como columna vertebral del código: CERRADA (31-07-2026, ver
más abajo). Repo privado: `https://github.com/LaRuinaDeMago/Os-Asesor-a`.

**FASE 0 DEL FLUJO OPERATIVO (medición del histórico) — EN CURSO desde
11-08-2026.** No confundir con la "Fase 0" de privacidad de arriba: son cosas
distintas con el mismo nombre. Los números medidos están en
`FASE0_RESULTADOS.md` — ese archivo manda sobre cualquier resumen de aquí.

Resuelto: formato del corpus, esquema, codificación, volumen, y si el motor se
puede reejecutar sobre el histórico (**68,26% de asientos reconstruibles**).
Pendiente: el núcleo de la Fase 0 (consistencia por par cliente–tercero).

FASE 2 — PoC Gemini: aplazada. No es el cuello de botella: el corpus histórico
no lleva facturas escaneadas, lleva asientos, y se lee sin IA ninguna.

Nota: se está siguiendo `PLAN_FLUJO_CONTINUO_v2.md` (fuera de este repo, en
local del usuario) a partir de aquí — sustituye la numeración de fases del
`FLUJO_CONTINUO_PLAN_DEFINITIVO.md` original. v2 añade el canal de datos
reales (Fase 5 de v2, Google Workspace + DPA) como pieza separada del canal
código — todavía sin empezar, ver "Pendiente" abajo.

## OBJETIVO DE LA FASE 1 (siguiente)
Una factura real → Gemini API → JSON estructurado → motor → veredicto.
Criterio de aprobación: funcionamiento técnico reproducible (no precisión todavía).

## ÚLTIMO RESULTADO
(vacío — se rellena la primera vez que se ejecute `captura_orquestador.py --proveedor gemini` de verdad)

## MOTOR — estado verificado el 19-08-2026
- **20 guards activos** en el veredicto principal (`evaluar_fila_v4`), todos
  cableados y consultados (`audit_project.py`, sin huérfanos). Eran 16 hasta el
  19-08: los otros cuatro son `integridad_datos` (nuevo) y los tres que existían
  pero nadie llamaba.
- `test_motor_veredicto.py`: **21/21 en verde** (regresión).
- `test_adversarial.py`: **25/25 en verde** (ataque + control positivo + auditoría propia).
- `contrato_datos.py`: frontera IA→motor con estados
  `VALUE`/`ZERO`/`MISSING`/`INVALID`.
- Probado en su día con 91 facturas reales de clientes piloto anonimizados + 1
  factura nueva en vivo → VERDE correcto (cifras conservadas, nombres reales ya
  no viven en el código ni en este archivo).
- Orquestador (`orquestador.py`) probado de punta a punta, reproducible.

## ✅ FALSOS VERDES — 8 encontrados y CERRADOS el 19-08-2026

**Encontrados y arreglados el mismo día.** No hizo falta Gemini ni datos reales:
bastó atacar el motor con entradas construidas.

```
test_motor_veredicto.py  ->  21/21 EN VERDE   (regresion, no se ha roto nada)
test_adversarial.py      ->  25/25 EN VERDE   (ataque, ningun falso verde en pie)
audit_project.py         ->  20 guards, todos cableados y consultados
```

**Lo que se construyó para cerrarlos: `contrato_datos.py`**, la frontera entre la
IA y el motor. Distingue cuatro estados donde antes solo había un número:

| Estado | Significado | Ejemplo |
|---|---|---|
| `VALUE` | Hay un dato útil | `125.40`, `"1.234,56"` |
| `ZERO` | Hay un cero **declarado**, que es un dato fiscal válido | `0`, `"0"` |
| `MISSING` | No venía el campo, o venía vacío | `""`, `None`, clave ausente |
| `INVALID` | Venía algo que no se puede interpretar | `"abc"`, `"2026-02-30"`, `NaN` |

> **`MISSING` ≠ `ZERO`. `INVALID` ≠ `ZERO`.** Ahí estaba todo el problema.

Y un guard nuevo, `guard_integridad_datos`, que corre **antes que ningún guard
fiscal** y es crítico: si falta un campo crítico, los guards aritméticos **ni
siquiera se ejecutan**, en vez de operar con ceros inventados.

### Estado de los ocho, uno a uno

| Ataque | Antes | Ahora |
|---|---|---|
| Todos los importes ausentes (`''`) | VERDE | **AMBAR** (integridad) |
| Todos los importes a `None` | VERDE | **AMBAR** (integridad) |
| Importes ilegibles (`'abc'`) | VERDE | **AMBAR** (integridad) |
| Fechas `2026-99-99`, `2026-02-30`, `2026-13-01` | VERDE | **AMBAR** (fecha `INVALID`) |
| Falta la clave `total_factura` | `KeyError` | **AMBAR**, con veredicto |
| Importes como número JSON | `AttributeError` | **veredicto normal** |
| `irpf` = 999 con diferencia de 150 | OK | **FALLO** (se contradicen) |
| Negativo sin `tipo_documento` | OK | **NO_COMPROBADO** |

### Y el control positivo, que es la otra mitad

Una batería que solo comprueba "no debe dar VERDE" se aprueba entera con un motor
que diga siempre ROJO. Por eso `test_adversarial.py` incluye la familia G:

- Una factura completa y correcta **sigue dando VERDE**.
- La misma con importes en formato español (`1.328,90`) **también**.
- Los tramos de IVA ausentes de forma legítima **no impiden el VERDE**.
- Un IVA que no cuadra, un NIF con dígito de control malo y un duplicado escrito
  de otra forma **siguen detectándose**.

### Auditoría propia del código escrito ese mismo día

Terminado el arreglo, se auditó el código recién escrito. **Salieron tres
defectos, dos de ellos introducidos al arreglar los P0.** Los cuatro casos están
ahora en la batería (familia I) para que no puedan volver:

| Defecto | Estado |
|---|---|
| Una fila que no es un `dict` (`None`) reventaba el proceso entero | ✅ corregido |
| **Falso rojo nuevo:** una factura coherente (`base+IVA=total`) sin desglose de tramos daba ROJO por "DESCUADRE", cuando lo que falta es el desglose, no el cuadre | ✅ corregido |
| **Semántica mal decidida:** los importes ilegibles daban ROJO. En este motor ROJO significa *"he encontrado un error en la factura"*, y no poder leerla no es un error de la factura | ✅ ahora AMBAR |

Sobre el tercero, que es el más importante de los tres: es la misma razón que este
proyecto ya documentó en `scripts/privacy_scan.py` al descartar un patrón ruidoso
—*"un escáner que grita demasiado deja de mirarse"*—. Si cada foto mal hecha
produce un ROJO, ROJO deja de significar error. Lo innegociable no cambia: **nunca
puede salir VERDE**, y AMBAR lo cumple.

### Prueba de punta a punta (orquestador, datos sintéticos)

```
3 facturas -> 2 VERDE + 1 AMBAR (la que no traía importes, parada por integridad)
```

Sin excepciones, con `--nif-titular` y `mapeo_cuenta_gasto` llegando al motor.

### Lo que sigue sin medirse, y no ha cambiado

Esto cierra los falsos verdes **del motor ante entradas construidas**. La métrica
que decide el proyecto —**cuántas facturas reales dan VERDE siendo incorrectas**—
sigue sin medir, y para eso hacen falta facturas reales, captura real y las
etiquetas de `DISENO_APRENDIZAJE.md`. Un motor que resiste el ataque sintético es
condición necesaria, no suficiente.

### La causa raíz, para que no se repita

**`_f()` convertía ausencia e ilegibilidad en `0.0`.** Y `0` es un dato fiscal
válido, así que "no sé qué había" y "había cero" eran indistinguibles para todos
los guards aritméticos. Con todo a cero, `0+0+0=0` cuadra y los tres daban OK.

> La invariante *"si no hay dato, NO_COMPROBADO, nunca OK por omisión"* estaba
> escrita en el docstring del módulo y desmentida por el parser numérico tres
> líneas más abajo. **Es la tercera vez en esta sesión que aparece el mismo
> patrón**: el escáner de privacidad decía "sin hallazgos" sobre un fichero que
> no había leído, y `audit_project.py` decía "21/21" sin contar. Un "correcto"
> que en realidad significa "no lo he comprobado".

**Los tres guards huérfanos, también cerrados:** `guard_cuenta_gasto_coherente`,
`guard_tipo_producto_iva_semantico` y `guard_tipo_operacion_especial` existían con
test propio en verde y `evaluar_fila_v4` no los llamaba. Ya están cableados (de 16
a **20 guards**), con parámetros opcionales para no romper a quien ya llamaba a la
función: si el dato no viene, `NO_APLICA`, nunca OK. Al cablear el segundo se
descubrió además que **reventaba** (`TypeError`) si la categoría venía sin tipo de
IVA; arreglado.

### Cuatro hallazgos más, verificados el 19-08-2026 (auditoría externa)

| # | Hallazgo | Estado |
|---|---|---|
| 1 | El agujero `.DAT`/`.zip` de la barrera de privacidad | ✅ **CERRADO** (`d204f56`) |
| 2 | `audit_project.py` imprimía `"21/21 OK"` como **cadena escrita a mano** | ✅ **CERRADO** — ahora cuenta |
| 3 | El estado `MEDIA` de `guard_confianza_captura` es **inalcanzable** | 🟠 ABIERTO (documentado) |
| 4 | `nif_cliente_titular` va siempre `None` desde el orquestador | ✅ **CERRADO** — `--nif-titular` |

**Sobre el 2, que merece una nota:** el informe de auditoría del propio proyecto
declaraba `21/21 OK` sin contar nada. Si se añadía o quitaba un check, seguiría
imprimiendo `21/21` para siempre. **Es la misma clase de fallo que el motor existe
para evitar** — un informe que declara éxito sin haberlo medido — y es la tercera
vez que aparece en esta sesión, después del escáner de privacidad que decía "sin
hallazgos" sobre un fichero que no había leído, y del motor que da VERDE a una
factura sin importes. Ya cuenta las líneas de resultado y falla si no cuadran.

**Sobre el 3:** `OK_INFERIDO` solo aparece en `motor_veredicto.py`, en el guard que
lo consume. **Nadie lo produce**: el prompt de `captura_orquestador.py` solo pide
`OK` o `DUDA`. El escalón `MEDIA` es código muerto esperando un valor que ningún
componente emite.

**Sobre el 4 (ya cerrado):** en `orquestador.py:140`
el argumento posicional que corresponde a `nif_cliente_titular` es literalmente
`None`. Por tanto `guard_sentido_compra_venta` **nunca puede disparar su rama
crítica** —"el emisor es el propio cliente, esto es una venta y no un gasto"— en
ninguna ejecución real. Solo se ha probado en el test unitario. Es exactamente el
patrón que la Fase 0 ya nombró: guards construidos sin caso real que los respalde.
**Cerrado el 19-08-2026:** el orquestador acepta `--nif-titular` y se lo pasa al
motor. Sin ese argumento el guard se declara `NO_COMPROBADO`, nunca OK. En la
misma pasada se le pasa también `mapeo_cuenta_gasto`, que tampoco llegaba.

**Sobre el 3, que sigue abierto:** `OK_INFERIDO` solo existe en el guard que lo
consume; el prompt de captura solo pide `OK` o `DUDA`. El escalón `MEDIA` es
código muerto. No se ha tocado a propósito: arreglarlo bien significa **confianza
por campo** (`DISENO_APRENDIZAJE.md` §4), no parchear el prompt para que emita una
palabra más.

## SIGUIENTE ACCIÓN CONCRETA

> ## 👉 Para arrancar, lee `EMPEZAR_AQUI.md`, no este fichero.
>
> Este documento tiene 700 líneas y sirve para **consultar**. `EMPEZAR_AQUI.md`
> dice en una página por dónde empezar hoy y en qué orden.

**Primer mensaje al retomar, literal:**

> Continuamos. Ejecuta `python3 audit_project.py` y dime qué sale. Luego lee
> `EMPEZAR_AQUI.md` entero y seguimos por ahí.

**Orden de construcción acordado el 19-08-2026** (detalle y motivos en
`ARQUITECTURA_DATOS.md`): **ordenar → situar los modelos → validar.** No es una
preferencia de método: el 390 dentro de las copias está en blanco, así que la
validación fiscal necesita el corpus de modelos presentados situado en el tiempo
primero. Entra como conjunto nuevo el **036** (altas, bajas y obligaciones
declaradas): es la única fuente que dice lo que TENDRÍA que haber, y convierte
"faltan modelos" en una resta comprobable.

**Estado al cerrar el 12-08-2026.** Todo lo de abajo está medido y verificado:

| | |
|---|---|
| Corpus detallado | **2019–2026**, 33 clientes, 1.287 copias, 101.122 asientos |
| 2016–2018 | Solo cuentas depositadas en PDF. El detalle diario **no existe** |
| Formato / esquema / codificación | ZIP+dBase · 91 campos estables · cp1252 |
| Estructura del backup | 3 ficheros por empresa (1 con datos + 2 vacíos de 1.384 B) |
| Auditoría independiente | **5 de 5 en verde** (`fase0_verificacion.py`) |
| Cifrado de disco · copia en USB | ✅ activado · ✅ existe |

**Pendiente de decidir con Diego, no urgente:** los 478 PDF del Registro (segundo
corpus, cubre 2016–2018, es la verdad dura para validar) se dejan para después
del motor — no deben retrasarlo.

**Criterio acordado para decidir qué se pule:** *¿lo consume el motor?* El mapa
cliente-año sí; los `.wma` y `.jpg` no; los `.cat` sin determinar.

**Cerrado el 12-08-2026:** la identidad del cliente **no está** en las copias
(siete vías descartadas con número, ver `FASE0_RESULTADOS.md` §11.1). Se resuelve
por **huella dactilar de contrapartes**, y el método está validado: histograma
bimodal, meseta estable de 35 grupos entre umbrales 0,30 y 0,60, 34 de 35 grupos
presentes en varias subcarpetas, y el grupo mayor verificado a mano por el titular
(89–100% de contrapartes en común → un solo cliente).

Inventario construido: 35 clientes, 206 pares cliente-ejercicio, **79,1% de
ejercicios completos hasta diciembre**, tramos continuos sin agujeros interiores.
**El corpus es 2018–2026, no 2016–2026.**

## ✅ BLOQUEANTE CERRADO (12-08-2026, tarde) — las copias están completas

La identidad estaba **en el nombre del fichero**, no en su contenido: el patrón real es
`SP_C_04A` (con letra final), no `SP_C_04`. El número es el código de empresa y la letra
es la parte del backup. Cada copia de empresa son **3 ficheros**: uno con datos y dos
plantillas vacías de 1.384 bytes. `3.857 = 1.287 × 3`.

**Auditoría independiente: 5 de 5 en verde** (`fase0_verificacion.py`). Y el número que
cierra la duda, confirmado en dos carpetas por separado:

```
ejercicio 2025 -> 33 empresas      ejercicio 2026 -> 33 empresas
```

**Coincide exactamente con los 14 S.L. + 19 autónomos declarados. No falta ningún
cliente.** El déficit anterior era un artefacto del agrupamiento por huella.

### ⛔ Números anteriores que quedan INVALIDADOS

La huella fusionaba clientes, así que **todos sus recuentos son falsos**: "35 / 38 / 39 /
40 clientes", "23–24 activos en 2025" y el mapa de cobertura con su 78,9%. Los ficheros
`fase0_huella.json`, `fase0_reagrupa.json`, `fase0_huella_v2.json`, `fase0_umbral.json` e
`inventario_agregado.json` contienen recuentos de cliente erróneos; se conservan como
registro del proceso, no como resultado. Detalle en `FASE0_RESULTADOS.md` §11.0 y §12.

**No se invalida** nada que no dependa del agrupamiento: formato, esquema, codificación
cp1252, 348.716 líneas únicas, 101.122 asientos, 68,26% reconstruibles, y el recuento de
sociedades presentadas por año.

### Lo único que queda para cerrar la Fase 0

Enlazar el código de empresa **entre carpetas distintas** (mismo cliente, códigos
distintos según la copia), con esta regla dura ya verificada:

> Dentro de una misma carpeta, **dos códigos distintos son dos empresas distintas**.
> Nunca se pueden fusionar.

Con esa restricción, la huella enlaza entre carpetas pero no puede pegar clientes dentro
de una. Es media hora de trabajo y el mapa queda cuadrado con la realidad.

## 🔴 Histórico del bloqueante (resuelto, se conserva por trazabilidad)

El titular confirma 43 clientes solo en 2025; el mapa detecta 23 ese año y 35 en
total. **La Fase 0 no avanza hasta cerrarlo.** Cinco candidatas en
`FASE0_RESULTADOS.md` §11.4; la principal es que **2.570 contenedores (67% del
corpus) están sin examinar** — no tienen diario ni subcuentas y nunca se ha mirado
qué son.

**Siguiente acción, ya escrita como plan:** diagnóstico de los 2.570 (qué tablas
llevan dentro), test de fusión de grupos (similitud mínima intra-grupo y
contenedores repetidos de mismo grupo/ejercicio/carpeta) y distribución real de
NIF por contenedor para revisar el umbral arbitrario `MIN_NIFS = 5`.

**Dos preguntas que solo puede contestar el titular, y que pueden explicarlo
entero sin ningún script:**
1. De los 43 clientes de 2025, ¿cuántos son S.L. con contabilidad completa en
   ContaPlus y cuántos son autónomos que solo llevan libros registro?
2. ¿Existe todavía el "ordenador de José" que aparece en varios nombres de
   carpeta, o sus copias ya están volcadas aquí? Si faltan clientes y faltan
   2016–2017, pueden estar allí.

**Qué es el inventario y por qué va antes que la consistencia por par.** Es el
entregable que desbloquea el resto y vale por sí solo: dice hasta dónde se
puede fiar uno del propio histórico. Resuelve de una vez la identidad del
cliente (índice anónimo estable), la cobertura parcial (última fecha de asiento
de cada copia), y qué años son utilizables.

Dos salidas, patrón de los dos planos:
- `inventario_LOCAL.csv` — con nombres reales. Nunca sube, nunca lo lee Claude.
- `inventario_agregado.json` — solo cobertura en porcentajes. Ese sí sube.

**Restricciones que ya están resueltas y NO hay que volver a investigar**
(detalle en `FASE0_RESULTADOS.md` §10):
- La identidad del tercero sale del **NIF** (`TERNIF`), nunca del código de
  subcuenta: los códigos se copian entre clientes de actividad parecida.
- La identidad del cliente sale de la tabla de empresas de dentro del ZIP, no
  del código de empresa de ContaPlus (varía de un año a otro) ni del nombre de
  subcarpeta (van por fecha, no por cliente).
- El cuadro de cuentas se arrastra de un ejercicio al siguiente, así que una
  consistencia alta es **esperable y no prueba corrección**. La señal está
  donde la consistencia se rompe.
- La clave necesita el **concepto** como tercera dimensión (S14 confirmado).

**Acuerdo de método para la próxima sesión:** el inventario lo ejecuta Diego,
no Claude. El dato no llega a Claude en ninguno de los dos casos, pero
ejecutándolo Diego hay un control humano de más: ve la salida antes y decide
si la pasa. Aplica a todo script que toque nombres o NIF.

**Regla dura declarada por Claude:** no abre nunca un fichero `_LOCAL`. Si hace
falta mirar algo de ahí, se lo pide a Diego. Cumplido dos veces el 11-08-2026.

Aplazado a propósito, no olvidado: los 478 PDF de diarios del Registro (se
usarán al final, para blindar el histórico cuando el motor esté afinado),
Gemini/OCR (el corpus no lo necesita: no hay facturas escaneadas), Google
Workspace, y la contratación de API/Consola de Anthropic.

### ⚠️ RIESGO PRINCIPAL DEL PROYECTO — y no es Claude ni el DPA

Declarado por el titular el 11-08-2026: este equipo concentra en un solo disco
diez años de contabilidad, **todos los modelos fiscales presentados**, altas y
bajas, escrituras y copias de DNI. Es el patrimonio de datos personales
completo del despacho.

Con eso, las dos casillas sin marcar de mayor impacto son de la §11 del flujo,
y valen hoy más que `osa-check`, la Action, VeraCrypt y los once tests juntos:

- **§11.1 — Cifrado de disco. ✅ RESUELTO 12-08-2026.** Estaba **desactivado**
  (comprobado en Ajustes > Privacidad y seguridad > Cifrado de dispositivo:
  interruptor en "Desactivado"). El titular lo **activó** ese mismo día.
  `manage-bde -status` no sirve para comprobarlo en esta edición de Windows: da
  error de acceso aunque la consola sea de administrador, porque en Home no
  existe BitLocker como tal, solo Cifrado de dispositivo. Se comprueba por la
  interfaz de Ajustes.
- **§11.2b — Copia de seguridad. ✅ PARCIAL 12-08-2026.** El titular confirma
  el 100% de la **contabilidad** en un USB externo. **Pendiente confirmar** si
  esa copia incluye también modelos, escrituras y DNIs.

**Tres cabos sueltos derivados, sin cerrar:**
1. **Clave de recuperación del cifrado**: debe guardarse FUERA del equipo
   (impresa o en un USB aparte). Está en la cuenta Microsoft asociada, que es
   hoy un punto único de fallo: perder el acceso a esa cuenta = perder los datos.
2. **El USB de copia es ahora el eslabón débil.** Cifrado el disco principal, la
   copia sin cifrar es lo único que se lee sin barrera. Robarla produce la misma
   brecha que antes producía robar el equipo. Cifrarla (BitLocker To Go o
   VeraCrypt).
3. **Alcance de la copia**: confirmar que cubre modelos, escrituras y DNIs, no
   solo contabilidad.

### Frontera de alcance — escrita para que no se erosione

Este proyecto toca **contabilidad (`.DAT`)** y, más adelante, **facturas**. Los
**DNIs y las escrituras no entran en ningún pipeline automatizado, nunca**: no
aportan nada al motor y multiplican el daño de cualquier fallo. Los **modelos
presentados sí entran, pero solo como verdad contra la que cuadrar**, nunca
como material a procesar.

### Dos cosas que cambian el plan, aportadas por el titular el 11-08-2026

1. **Existen todos los modelos presentados de diez años.** Eso convierte la
   validación fiscal en la mejor disponible: un 303 presentado es un hecho, no
   un criterio, así que no arrastra la ambigüedad de "lo que contabilizaste vs
   lo que era correcto".

   > ⛔ **CORREGIDO 19-08-2026 — el corte vertical propuesto aquí el 11-08 no se
   > puede hacer como estaba escrito.** Decía: "reconstruir el 303/390 desde el
   > diario y cuadrarlo contra el `M390A.dbf` que ContaPlus guarda en cada
   > copia". **Esa tabla está en blanco:** 1.268 de las 1.287 copias la tienen
   > enteramente a cero, todas de 29.716 bytes exactos (medido el 12-08,
   > `fase0_identidad_v2.json`; conclusión ya escrita en `FASE0_RESULTADOS.md`
   > §11.1 y no propagada hasta hoy a este fichero).
   >
   > **Consecuencia, y no es menor:** la validación fiscal necesita el corpus de
   > **modelos presentados**, que vive FUERA de las copias de contabilidad. Hay
   > que inventariarlo y situarlo en el tiempo antes de poder cuadrar nada. Por
   > eso el orden es ordenar → situar modelos → validar, y no al revés
   > (`ARQUITECTURA_DATOS.md` §4).
2. **Existen las altas y bajas de clientes.** El inventario DEBE cruzarlas: una
   copia que corta a mitad de ejercicio porque el cliente se dio de alta en
   junio **no es un hueco, es la historia real**. Sin ese cruce, el inventario
   marcaría como incompleto lo que está correcto.

### Objetivo del producto, en palabras del titular (para que no se pierda)

`foto de la factura → motor → fichero importable → ContaPlus`, más los modelos
fiscales (303, 130, 111, 115) y el valor añadido al cliente. **Exportar a
ContaPlus en vez de sustituirlo** es decisión deliberada y acertada: no obliga a
cambiar la forma de trabajar.

Prueba previa informal con Opus: ~98% de facturas fotografiadas dadas por
buenas. **No cuenta como evidencia todavía** — no consta el tamaño de la
muestra, mezclaba tasa de extracción con tasa del motor, y "verde" significaba
"el motor no encontró problema", que no es lo mismo que "el asiento es
correcto". **El número de falsos verdes sigue sin medirse y es la métrica que
decide el proyecto.**

## NO HACER TODAVÍA (declarado explícitamente, no por omisión)
- No añadir Vertex AI — solo si la Fase 1/2 sale bien Y se necesita residencia UE garantizada.
- No añadir Claude API a producción — ya se decidió que Gemini va primero.
- No migrar cachés a SQLite — el volumen actual (ms de ejecución, MB de tamaño) no lo justifica.
- No añadir guards nuevos al motor — está construido y probado; esta fase es sobre captura, no sobre el motor.
- No montar entorno cloud persistente separado — probar primero con GitHub + Claude Code Web a secas.
- No subir datos reales de ningún cliente a GitHub — GitHub es solo para código. Ver `NUNCA_SUBE.md`.

## DECISIONES YA CERRADAS (no reabrir sin motivo nuevo)
- Infraestructura de lectura: Gemini API de pago (no Vertex, no gratis) — Fase 1.
- AutoApunte: descartado como producción, solo prueba gratuita para estudiar enfoque.
- Alojamiento CONTASOL (API en tiempo real): descartado por ahora, no es el cuello de botella.
- Modelo local (Ollama/Qwen3-VL): aparcado, no descartado — opción de respaldo si Gemini falla en Fase 1/2.

---

## Auditoría de privacidad — sesión 2026-07-30

No hay todavía repositorio de GitHub creado. Esta sesión ha sido la auditoría de
privacidad de la Fase 0 (`FLUJO_CONTINUO_PLAN_DEFINITIVO.md`), hecha por Claude
Code en Local, antes de tocar GitHub — el orden que pide el plan tras el
incidente de subida accidental documentado en su sección 1.4.

### Hecho en esta sesión

1. Extraídos ambos `.zip` (`OS_ASESORIA_v3_38.zip`, `MOTOR_PAQUETE_CLAUDE_CODE.zip`)
   a una carpeta temporal local (fuera de este proyecto), nunca al propio proyecto.
2. Auditado cada archivo de dentro de los zips con la misma disciplina que los
   archivos sueltos — no aprobado en bloque.
3. Encontrada una discrepancia importante respecto a la versión anterior del
   plan: varios archivos que la Fase 0 original daba por seguros para subir
   (`motor_veredicto.py`, `layout_diario_contaplus.py`, `orquestador.py`,
   `test_motor_veredicto.py`, `ENCARGO_CLAUDE_CODE.md`, `INVENTARIO.md`,
   `PENDIENTE_DE_FABRICACION.md`, `SEMAFORO_DEFINITIVO_v1_ADENDA.md`, este
   mismo archivo en su versión anterior, `README (1).md`, `IVA_TIPOS_2026.json`)
   en realidad citaban nombres de cliente/proveedor reales en comentarios,
   docstrings o mensajes de test (esta versión de `PROJECT_STATUS.md` incluía
   dos nombres de cliente reales en la línea de "MOTOR" — ya corregido arriba).
4. Los 4 archivos de código con más peso (`motor_veredicto.py`,
   `layout_diario_contaplus.py`, `orquestador.py`, `test_motor_veredicto.py`) se
   editaron para genericar esas menciones (nombres → "cliente piloto"/"caso real
   anonimizado"; en `test_motor_veredicto.py` además se sustituyó el DNI/NIF de
   ejemplo por uno inventado con dígito de control matemáticamente válido, nunca
   el real). El resto de archivos con fuga (documentación .md y el JSON de
   tipos de IVA) se dejaron sin editar y quedan en `NUNCA_SUBE.md` — no estaba
   en el alcance aprobado de esta sesión tocarlos.
5. Verificado tras cada edición: `test_motor_veredicto.py` pasa 100% y una
   segunda pasada de grep confirma 0 coincidencias de los nombres reales
   conocidos en esos 4 archivos.
6. Auditado también el resto del contenido de `OS_ASESORIA_v3_38.zip`
   (documentación de gobierno, motor, expedientes, contraste) — la inmensa
   mayoría es trabajo real del despacho con clientes reales y va a
   `NUNCA_SUBE.md`. Se rescataron como código/spec limpios y nuevos:
   `guard_g7_ledger.py`, `triangulacion_identidad_v0.py` (editado para genericar
   una mención), `MATRIZ_COBERTURA_v1.md`, `CATALOGO_EVENTOS_v1.md`,
   `criterios_fiscales.json`.
7. Creados: `CLAUDE.md`, `.claude/rules/{datos,contabilidad,testing,seguridad}.md`,
   `SUBE_A_GITHUB.md`, `NUNCA_SUBE.md`, y este `PROJECT_STATUS.md`.

### Sesión 31-07-2026 — Fase 2.5 (barrera técnica) + Fase 1 (GitHub) cerradas

1. Construida la barrera técnica de dos capas (Fase 2.5 de ambos planes):
   `scripts/privacy_scan.py` (genérico, sin apellidos reales — regex de
   NIF/CIF/DNI, IBAN, teléfono + lista de nombres de archivo prohibidos),
   hook de pre-commit local (`scripts/pre-commit` + `scripts/install_hooks.sh`
   para reinstalarlo tras cada clon nuevo, git no versiona `.git/hooks/`), y
   GitHub Action (`.github/workflows/privacidad.yml`) como segunda barrera
   independiente. Probado con casos reales: commit con archivo prohibido →
   bloqueado; commit limpio → pasa. Los NIF sintéticos ya creados en la
   auditoría anterior (`12345678Z`, `B12345674`, `B12345678`, `B99999999`,
   `12345678Y`) están en un allowlist explícito dentro del propio script —
   son ficticios, es seguro que el script (público) los mencione.
2. `.gitignore` añadido como capa extra (bloquea `*.zip`, los archivos de
   `NUNCA_SUBE.md` por nombre, `.claude/settings.local.json`, caché de Python).
3. Repositorio GitHub creado por Diego (privado): `LaRuinaDeMago/Os-Asesor-a`.
   `git init` local, commit único con exactamente los 33 archivos de
   `SUBE_A_GITHUB.md` (verificado con `git status` antes de commitear, nunca
   `git add -A`), `git push` hecho por Diego desde Git Bash (autenticado vía
   Git Credential Manager, OAuth oficial de la org `git-ecosystem` — yo no
   toqué ninguna credencial).
4. **Verificación en limpio ejecutada de verdad** (no asumida): clon nuevo en
   carpeta separada, grep de apellidos reales + patrón NIF/CIF sobre el clon.
   Resultado: 0 coincidencias reales — solo nombres de archivo ya conocidos y
   los NIF sintéticos documentados. Fase 1 cerrada con criterio de éxito
   cumplido, no supuesto.

### Sesión 31-07-2026 (tarde) — v3 revisado, escáner ampliado, Fase 3 empezada a probar

1. Revisado `PLAN_FLUJO_CONTINUO_v3.md` (Diego, fuera del repo). Valoración
   crítica: el principio "la barrera real es justo antes del `git push`, no el
   momento en que se dispara un hook" se acepta como correcto. Se corrige al
   plan en un punto: el "Hook Stop" que propone NO es una capa de seguridad
   independiente (lo ejecuta el mismo agente, con las mismas reglas que ya
   sigue) — es automatización de conveniencia, no una barrera nueva. Las
   barreras reales siguen siendo git local + GitHub Action + revisión humana,
   ya construidas. Decisión: no construir el Hook Stop todavía (sobreingeniería
   prematura, no hay problema real que resuelva hoy); sí ampliar el escáner
   (barato, valor real) y declarar el modo real/sintético al empezar sesiones
   con datos — ver `.claude/rules/datos.md`.
2. `scripts/privacy_scan.py` ampliado: detección de email y de prefijos
   conocidos de claves API (Anthropic, OpenAI, Google, AWS, Slack...).
   Descartado a propósito un patrón genérico de "bloque alfanumérico largo"
   tras probarlo y dar ~20 falsos positivos reales en el propio repo (hashes
   de commit, nombres de variable, referencias normativas) — un escáner que
   grita demasiado deja de mirarse, así que se prefirió menos alcance pero
   fiable. Probado contra los 33 archivos ya subidos (0 falsos positivos) y
   contra un email/clave de ejemplo inventados (sí los detecta). Commiteado y
   subido (`82af9cf`), verificado en clon limpio.
3. **Fase 3 (multi-superficie) empezada a probar de verdad, no solo en teoría:**
   - Remote Control probado: `claude remote-control` desde el PC + móvil
     conectado por QR → sesión `pc02-radiant-backus`, funciona.
   - Cloud/Web probado sin querer (al pulsar "Nueva sesión" en el móvil sin
     seleccionar Remote Control): crea una sesión en infraestructura de
     Anthropic, no en el PC — confirmado porque respondió correctamente
     leyendo `PROJECT_STATUS.md` del repo. Esto es la prueba de fuego 3.3
     (funciona con el PC apagado), aunque no se hizo con el PC físicamente
     apagado esta vez — pendiente confirmarlo a propósito.
   - Confirmado con la documentación oficial (`code.claude.com/docs/en/remote-control`):
     una sesión Local normal (como esta) NO es accesible desde el móvil salvo
     que se arranque explícitamente con `/remote-control`, `claude --remote-control`,
     o se active el ajuste global "Enable Remote Control for all sessions".
     También confirmado por la fuente oficial (no solo por el plan): mientras
     Remote Control está conectado, el transcript se guarda en servidores de
     Anthropic — coincide con la regla ya escrita en `.claude/rules/datos.md`.
   - **Enganchada la propia conversación de esta sesión al modo remoto**
     (`/remote-control`, la opción "From an existing session" de la
     documentación oficial — carga el historial completo, no crea una sesión
     vacía). Confirmado accediendo desde el móvil y escribiendo en él: mismo
     hilo, mismo contexto, acceso real al PC. Con esto, las 3 formas de
     trabajar fuera de la asesoría (esta conversación por Remote Control,
     sesión nueva por Remote Control, sesión Cloud/Web) quedan probadas de
     verdad, no solo documentadas.
   - Además, entra Dispatch como cuarta pieza conocida (pestaña "Cowork" del
     Desktop, tarea mandada desde el móvil que se convierte en sesión de
     código en el PC) — revisado en la documentación oficial, decidido NO
     usarla por ahora: no resuelve nada que Remote Control/Cloud no resuelvan
     ya, sería sobreingeniería añadida sin necesidad concreta.

4. **Hallazgo importante sobre "Local" y datos reales — corrige una asunción
   de `.claude/rules/datos.md`:** "Local" en Claude Code significa que las
   HERRAMIENTAS (archivos, git, bash) se ejecutan en el PC — no significa que
   el contenido nunca llegue a los servidores de Anthropic. El modelo en sí
   siempre corre en la nube de Anthropic, así que cualquier archivo que Claude
   lea (real o no) se envía a la API para poder procesarlo, sea Local, Remote
   Control o Cloud. Confirmado con la documentación oficial
   (`code.claude.com/docs/en/data-usage` y `privacy.claude.com`, sesión de
   Diego 31-07-2026):
   - Cuenta actual de Diego: **Pro (consumidor)** — regida por "Consumer
     Terms", pensada para uso individual, **sin marco de DPA**.
   - El DPA (Adenda de Procesamiento de Datos) solo existe para **clientes
     comerciales** (API, Consola, **Team**, Enterprise) — hay un trámite de
     autoservicio documentado ("¿Cómo puedo ver y firmar su DPA?") una vez en
     un plan comercial, sin necesidad de contrato a medida.
   - **Conclusión REVISADA (31-07-2026, tras investigar a fondo
     `code.claude.com/docs/en/authentication.md`):** NO hace falta pasar toda
     la cuenta a Team. Se puede combinar Pro + API/Consola en el mismo PC:
     - **Pro (el que ya paga Diego)** se queda para el canal código de
       siempre — Remote Control, Cloud, este repositorio, datos sintéticos.
       Cero cambios.
     - **API/Consola (nueva, de pago por uso, SIN el mínimo de 2 asientos de
       Team)** se activa solo para sesiones con datos reales, poniendo la
       variable de entorno `ANTHROPIC_API_KEY` — Claude Code la prioriza
       automáticamente sobre la suscripción una vez aprobada (documentado:
       "la API key tiene prioridad una vez aprobada... `unset
       ANTHROPIC_API_KEY` para volver a tu suscripción"). Comprobar con
       `/status` cuál está activa en cada momento.
     - **Límite real confirmado (no evitable):** Claude Code on the Web
       SIEMPRE usa las credenciales de la suscripción, nunca la API key —
       así que el modo "datos reales" solo puede darse en sesión **Local**,
       nunca en Remote Control ni en Cloud/Web. Encaja exactamente con el
       objetivo ya replanteado por Diego (datos reales solo desde el PC de
       la asesoría, no en remoto).
     - Coste esperado: bastante por debajo de los $50/mes de Team, al ser
       pago por uso y sin mínimo — pendiente de confirmar importe real con
       uso propio, no asumido.
   - `.claude/rules/datos.md` corregido con la distinción Local=ejecución de
     herramientas vs. modelo=siempre en la nube de Anthropic, y con este
     mecanismo de interruptor Pro↔API key (pendiente de un segundo ajuste
     menor para reflejar la conclusión revisada, ver Pendiente).

5. **`scripts/guardar_avance.sh` construido y probado (dos veces: caso limpio
   y caso con dato sospechoso de ejemplo).** Automatiza la parte de
   "preparar" el guardado (escanea, `git add` de lo que corresponde, crea el
   commit) — decidido tras suficiente uso real repetido en la propia sesión
   de hoy como para justificarlo (ya no era sobreingeniería hipotética). El
   `git push` sigue siendo SIEMPRE una acción manual aparte, aprobada
   explícitamente por Diego cada vez — eso no se automatiza sin decisión en
   contra explícita.
6. Guardadas dos reglas de memoria (fuera de este repo, en el sistema de
   memoria de Claude) para que cualquier sesión futura las respete sin que
   Diego tenga que repetirlas: (a) recordar activamente guardar avances, no
   solo al cerrar sesión, cada vez que se cierre un bloque de trabajo con
   sentido propio; (b) explicar en llano cualquier comando o decisión antes
   de pedir aprobación, no solo las "importantes" — reforzado explícitamente
   por Diego el 31-07-2026.

### Sesión 11-08-2026 — Fase 0 del flujo operativo: reconocimiento del corpus

Sesión local, con el corpus real en el PC. **Ninguna fila de dato real llegó al
modelo en ningún momento.** Todo se midió con seis scripts que solo emiten
recuentos. Números completos en `FASE0_RESULTADOS.md`.

1. **Diagnóstico del intento anterior de Fase 0.** `fase0_csv.py` corría contra
   `censo_despacho_v8.csv`, que es el *catálogo* de las copias (columnas
   `nombre, ejercicio, apuntes, hash, origen…`), no la contabilidad. La pregunta
   central de la Fase 0 no se puede calcular ahí: no hay `tercero` ni `cuenta`.
   Además sumaba apuntes fila a fila sobre 1.022 filas que son solo 264 pares
   empresa-ejercicio, así que sus 798.375 apuntes estaban inflados ~4x. Es
   exactamente la trampa que avisa el §3.6c del flujo, y ocurrió igual.
2. **Formato resuelto:** los `.DAT` son ZIP (firma `PK\x03\x04`) con dBase III+
   dentro. 3.857 contenedores, 3.857 ZIP válidos, 0 corruptos.
3. **Esquema resuelto:** `Diario.dbf`, 91 campos, 954 bytes/registro, **un solo
   esquema estable en las 1.287 copias de 2016 a 2026**.
4. **TEST_ENCODING resuelto: `cp1252`**, no CP850 — corrige el §3.6c del flujo,
   que lo daba por hecho. 14.141 bytes en rango cp1252, **0** en rango cp850.
5. **Volumen medido (S15):** 348.716 líneas únicas, 101.122 asientos únicos,
   factor de duplicación 2,7x. 98,42% de los asientos cuadran debe = haber.
6. **Reejecutar el motor sobre el histórico: 68,26% de asientos reconstruibles**
   (S16). La primera medición dio 0% porque se hizo por línea; la unidad
   correcta es el asiento. Error detectado y corregido dentro de la sesión.
7. **`BASEIMPO` está vacío al 0,78% y no importa:** la base se deriva del
   asiento con 97,27% de acierto (`base + cuota = total`) y 96,44%
   (`base × tipo = cuota`).
8. **Los 7 casos especiales de la spec v1.4 aparecen 0,00% de las veces** en
   941.435 líneas. Hay guards construidos sin caso real que los respalde.
   Pendiente de decidir qué hacer con eso.
9. **§11.2 comprobado y limpio:** Escritorio y Documentos sin redirigir a
   OneDrive, ningún cliente de sincronización corriendo.
10. **Dos agujeros tapados:** `censo_despacho_v8.csv` estaba sin trackear y
    fuera del `.gitignore` con razones sociales reales dentro (añadido, junto
    con el patrón `*_LOCAL.json`). Y se detectó que la regla "ningún `.zip`
    sube" está escrita sobre la extensión: estos ZIP se llaman `.dat` y
    pasarían por delante de ella. **Sin arreglar todavía.**
11. **Método de trabajo acordado:** ningún script para pegar en el terminal
    (se crea como fichero y se ejecuta), rutas por parámetro, ningún script
    aborta al primer fallo, y se dice qué se espera ver antes de ejecutar.

### Pendiente (primer mensaje al retomar)

1. Repasar a mano `DIRECTORIO_NACIONAL_PROVEEDORES.json` (ver `NUNCA_SUBE.md`)
   si se quiere filtrar la única ficha real que lo contamina y poder subir el
   resto del directorio — sigue completo fuera de GitHub por ahora.
2. Terminar de probar Fase 3: repetir la prueba Cloud/Web con el PC
   físicamente apagado a propósito (prueba de fuego 3.3 real — la de hoy fue
   sin querer, con el PC encendido), y probar Teleport (traer de vuelta al PC
   algo hecho en Cloud/Remote Control).
3. **Antes de tocar la Fase 5 de v2/v3 (Google Workspace + datos reales):**
   decidir con Diego el mecanismo técnico concreto de consulta (¿RAG? ¿conector
   MCP de Drive? ¿adjunto manual por consulta?) — sin esto especificado, no
   contratar Workspace todavía.
4. **Gestión de cuenta pendiente (revisada 31-07-2026):** contratar acceso de
   API/Consola de Anthropic (comercial, con DPA incluido automáticamente al
   aceptar los Términos de Servicio Comerciales) — NO hace falta pasar a
   Team. Configurar `ANTHROPIC_API_KEY` como interruptor para sesiones
   Locales con datos reales; confirmar el coste real de uso una vez
   contratada. Misma familia de gestión que el DPA de Google Workspace
   (punto 3), pero son dos trámites independientes, ambos necesarios.

   > **Reevaluado el 19-08-2026 (`DIRECCION_PRODUCTO.md` §2 de "las tres
   > puertas"):** esto ha dejado de ser un trámite administrativo en una lista.
   > Validar una factura procesa un documento; el análisis financiero continuo
   > por cliente al que apunta la dirección de producto procesa *todo* — y todo
   > eso pasa por la API. **Sin API/Consola con DPA, esa dirección no se puede
   > construir sobre datos reales.** Es la puerta de entrada, no un pendiente.
5. Seguir con Fase 2/PoC Gemini (activar facturación, `GEMINI_API_KEY`,
   primera factura real por `captura_orquestador.py`).
6. Diego dejó una frase a medias en la sesión del 31-07-2026 ("Además de...",
   tras pedir el script `guardar_avance.sh`) sin completar — preguntarle qué
   quería añadir ahí al retomar, no se ha resuelto todavía.
7. Pequeño ajuste pendiente en `.claude/rules/datos.md`: reflejar el
   mecanismo de interruptor Pro↔`ANTHROPIC_API_KEY` en vez de "hace falta
   Team" (la sección de DPA ya está bien, solo falta afinar esta frase).

### Nota técnica de entorno

**Actualizado 11-08-2026:** este equipo **ya tiene Python 3.14.6 instalado** de
forma persistente, disponible como `python` y como `py`. La nota anterior (que
decía que no había Python y que se usó una distribución portátil de 3.12 en un
directorio temporal) queda obsoleta. Los seis scripts `fase0_*.py` corren con
biblioteca estándar únicamente — `zipfile`, `struct`, `zlib`, `hashlib` — sin
instalar ninguna dependencia.

Sigue vigente: ejecutar `scripts/install_hooks.sh` tras clonar el repo en otro
equipo (el hook de pre-commit no viaja con `git clone`).
