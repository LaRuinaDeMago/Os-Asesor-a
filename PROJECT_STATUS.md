# PROJECT_STATUS — estado operativo, no documentación

> **Para ARRANCAR una sesión, lee `EMPEZAR_AQUI.md`.** Este fichero es la
> referencia detallada: sirve para consultar, no para empezar.

Este archivo se actualiza cada vez que algo cambia de verdad. Si algo aquí no
coincide con lo que demuestran los tests o el código, mandan los tests, no este
texto. Jerarquía de verdad: Código → Tests → Git → este archivo.

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
(30/30, 6 tests nuevos), `test_adversarial.py` (108/108), cobertura de guards
(26/26), escáner de privacidad (`scripts/privacy_scan.py`) ejecutado sobre
los 16 archivos tocados —y confirmado con un control positivo real que sí lo
detecta, no solo "sin hallazgos" a ciegas—, y el diff completo de los ocho
archivos modificados releído línea a línea.

Queda abierto y caracterizado, no urgente: ~800 casos de `cuadre_total` sin
patrón dominante ya identificable, y 94 de `nif_digito_control` (46 CIF con
checksum real, 48 sin patrón). Lectura de ambos: parece señal real del
histórico, no ceguera del instrumento — pero no está descartado del todo.

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
