# EMPEZAR AQUÍ — 27-08-2026

Punto de entrada único. Corto a propósito: `PROJECT_STATUS.md` sirve para
consultar, no para arrancar. Esto sirve para arrancar.

---

## 0. Dos cosas del entorno que ahorran media hora

**En el PC de la asesoría el intérprete se llama `python`, no `python3`.**
Comprobado el 26-08-2026: `python3` da *command not found*. En este documento
verás `python3` en comandos antiguos — sustitúyelo por `python`.

**Los scripts se ejecutan SIEMPRE desde la carpeta del proyecto, y la carpeta
de datos va como argumento.** Nunca al revés: si abres el terminal dentro de
la carpeta de datos, Python no encuentra el script. Las dos rutas reales:

| Qué | Ruta |
|---|---|
| Corpus ContaPlus (`.DAT`, 2016-2026) | `C:\Users\SERVILAB\Desktop\100% contabilidad` |
| Archivo de modelos AEAT presentados | `\\PC01\Documentos` |

```bash
cd "C:\Users\SERVILAB\Downloads\Proyecto asesoria completo"
python diag_baseimpo.py "C:\Users\SERVILAB\Desktop\100% contabilidad" --limite 150
```

---

## 1. Primer comando, antes de leer nada

```bash
python audit_project.py
```

Debe salir esto. Si no sale, algo se rompió y eso manda sobre todo lo demás:

```
✅ Sintaxis de todos los .py (recursivo)
✅ Cableado de guards (sin huérfanos): 26 guards, todos consultados
✅ Modulos sin conectar: ninguno
✅ Suite de pruebas (test_motor_veredicto.py): 36/36 checks en verde
✅ Bateria adversarial (test_adversarial.py): 112 en verde, 0 fallan
✅ Estados: sin ramas muertas ni guards mudos
✅ Cobertura: guards probados de verdad — 26/26 (100%)
✅ Ensayo en seco: retro_semaforo + orquestador
✅ Historico del orquestador: no pierde facturas por formato   <- 10º auditor, nuevo
✅ Barrido: ningun falso verde sin explicar
✅ Barrera de privacidad: bloquea lo que debe
✅ xDiario: ningun asiento descuadrado
✅ Captura <-> motor: los campos cuadran
✅ Corpus roto: no cuelga ni contamina
✅ Cruce 303: identifica sin inventar                     <- 11º auditor, 26-08
✅ subprocess.run: encoding explicito (18 llamadas)       <- 12º auditor, 26-08
✅ Reconstruir 303: deriva la base, no la inventa         <- 13º auditor, 27-08
❌ Dependencias: faltan anthropic, google-genai   <- NORMAL, son de captura
```

> ⚠️ **Si `audit_project.py` muere con `UnicodeDecodeError` a mitad de la
> lista, tu copia es anterior al 26-08-2026.** Los tres `subprocess.run` no
> declaraban `encoding`, así que en una consola de Windows (cp1252) el
> auditor reventaba al leer la salida UTF-8 de los scripts hijos. Pasaba en
> el PC de la asesoría y no en Cloud. Ya está arreglado: haz `git pull`.

> **Números actualizados el 26-08-2026 (cierre de sesión, tras la mega-auditoría
> propia).** Si tu `audit_project.py` da otros números de test, no asumas que
> algo se rompió: mandan los tests que corren delante de ti, no esta plantilla
> — puede quedarse desfasada según se añaden pruebas.
>
> ⚠️ **Si vienes de clonar el repositorio hoy o antes, vuelve a clonarlo o haz
> `git pull` en `master` antes de nada.** Hasta el cierre de esta sesión,
> `master` (la rama por defecto) llevaba desde el primer commit sin recibir
> ninguna de las correcciones — todo vivía en ramas `claude/*`, nunca
> fusionadas. Ya está arreglado (`PROJECT_STATUS.md`, entrada de cierre real
> de sesión), pero si tu copia local es de antes de hoy, es la versión vieja
> de una sola pieza sin `contrato_datos.py`.
>
> **Esta sesión (26-08) fue casi toda auditoría, no producto — y encontró y
> arregló defectos reales:** cinco rondas de auditoría externa (verificadas
> una por una por ejecución, no de palabra — la mayoría de sus hallazgos ya
> estaban cerrados o eran repeticiones, pero una encontró que
> `reevaluar_tras_correccion()` podía marcar una factura como duplicada de sí
> misma) más una mega-auditoría propia que encontró dos bugs reales y nuevos,
> los dos en la misma familia: **el paso *después* del motor no entendía el
> formato español que el motor sí entiende.** `layout_diario_contaplus.py`
> (el fichero que entra en ContaPlus) y `orquestador.py` (el histórico que
> alimenta dos guards) usaban `float()` a pelo en vez del parser del
> contrato. Detalle completo, con reproducción de cada bug antes de tocar
> nada, en `PROJECT_STATUS.md`, entradas del 26-08-2026. Nada de esto tocó
> datos reales ni necesitó el corpus local — todo verificable con
> `python3 audit_project.py` en cualquier clon.

### ✅ El paso 3.1 de abajo (retro-semáforo) YA SE HIZO — 25-08-2026

**No lo repitas desde cero: lee el resultado primero.** El corpus real ya se
pasó por el motor, once arreglos reales encontrados por el camino (diez el
25-08 más uno de auto-revisión). Resultado final: **VERDE 87,71% · ROJO
3,03% · AMBAR 9,26%**, sobre 30.013 asientos evaluados. Detalle completo,
arreglo por arreglo, en `FASE0_RESULTADOS.md` §14 — ese archivo manda sobre
cualquier número de aquí.

**Por el umbral ya acordado en `SIGUIENTES_PASOS.md` §4 (fijado ANTES de ver
el número): ROJO 3,03% < 5% = "Verde. Se pasa al siguiente paso sin tocar el
motor."** Cerrado, no toca seguir picando en el retro-semáforo.

Sigue abierto, y no es urgente: `cuadre_total`/`retencion_vs_error` (~800
casos, 2,7%) y `nif_digito_control` (60 casos tras el arreglo 11, 0,2%) sin
patrón dominante ya identificable — parece señal real del histórico, no
ceguera del instrumento, pero no está descartado del todo. Ver
`FASE0_RESULTADOS.md` §14 para el desglose.

> ✅ **RESUELTO EL 27-08-2026 (segunda versión — la primera mejoró pero no
> bastó).** El bloqueo de abajo (histórico, no lo borres: explica por qué
> hizo falta el arreglo) ya está cerrado.
>
> **Primer intento de la mañana** (ya superado, no lo repitas): derivar la
> base del gasto/ingreso contable del asiento, copiando
> `retro_semaforo.reconstruir_compra()`. Mejoró el 0% del 26-08 a un 64,9% de
> coherencia (`base×tipo=cuota`), pero esa coherencia **empeoraba** con el
> tamaño de la celda (72,9% → 43,9%) — la firma de un sesgo sistemático, no
> de ruido. Investigado con `diag_rescalado_multitipo.py` sobre el corpus
> real: el reescalado multi-tipo NO era la causa (88,6% de esos asientos sin
> sesgo, solo el 10,7% del volumen).
>
> **La causa real:** un 303 no se rige por lo contabilizado, se rige por una
> fórmula fija — `base × tipo = cuota`. Correcto usar el gasto contable
> para lo que hace `retro_semaforo.py` (comparar contra el patrón
> histórico); equivocado para reconstruir una casilla fiscal. `reconstruir_
> 303.py` ahora invierte la propia fórmula (`base = cuota / tipo`) en vez de
> mirar la contabilidad. **Efecto colateral bueno:** arregla también el caso
> ISP sin necesitar detectarlo — una línea 477 sin venta detrás ya no se
> queda en base 0.
>
> Probado con `ensayo_reconstruir_303.py` (10/10, casos diseñados para que
> el gasto/ingreso contable NO coincida con cuota/tipo — si algo reintrodujera
> la derivación desde la contabilidad, lo cazarían) y con el bug reintroducido
> a propósito: 6 comprobaciones exactas en rojo. 13º auditor, dentro de
> `audit_project.py`.
>
> **👉 SIGUIENTE PASO REAL: regenerar `303_LOCAL.json` OTRA VEZ.** El que
> generaste esta mañana con el primer arreglo también está superado — usa la
> derivación por gasto/ingreso, ya sustituida:
>
> ```bash
> python reconstruir_303.py "C:\Users\SERVILAB\Desktop\100% contabilidad" --detalle 303_LOCAL.json
> python diag_coherencia_303.py
> ```
>
> Con la fórmula nueva, `base×tipo=cuota` se cumple por construcción siempre
> que haya un tipo con el que dividir, así que la coherencia debería salir
> muy por encima del 64,9% de antes. Si no es así, hay algo más que
> investigar antes de pasar al cruce contra los PDF de `\\PC01\Documentos`
> con `cuadre_303_ficha.py` o `cruzar_303_importes.py` — los dos ya
> construidos y probados, esperando una base que valga.

> 🛑 **BLOQUEO HISTÓRICO, YA CERRADO (ver el aviso de arriba). Se conserva
> como registro de por qué hizo falta el arreglo, no como estado actual.**
> Lo que decía este bloque —"comparar a mano 5-10 trimestres de
> `303_LOCAL.json` contra los 303 presentados"— **no se podía hacer, y no
> por falta de tiempo: `303_LOCAL.json` no describía ninguna contabilidad.**
>
> Medido el 26-08 con `diag_baseimpo.py` sobre el corpus real (44.522
> apuntes de IVA): el campo `BASEIMPO` es un **cero literal en el 99,4%**
> de los apuntes, y `reconstruir_303.py` lo sumaba tal cual y llamaba "base
> imponible" al resultado. Las bases de ese fichero eran ficticias. El cruce
> automático contra los 1.043 modelos 303 del archivo dio **0 cubos casados
> de 24**, y el diagnóstico por tolerancias demostró que no era un problema
> de redondeo (aflojar a céntimos no movía el 4,0%). Detalle completo en
> `PROJECT_STATUS.md`, entrada del 26-08 (sesión LOCAL).
>
> **`retro_semaforo.py` NO estaba afectado** y el 87,71% VERDE sigue en pie:
> `reconstruir_compra()` ya deriva la base del gasto cuando `BASEIMPO` no
> sirve. El fallo era de propagación — `reconstruir_303.py` se escribió el
> 21-08, el hallazgo sobre `BASEIMPO` es del 25-08, y nadie había revisado
> la pieza hermana hasta el 27-08.

### Los trece auditores, y por qué hacen falta los trece

Cada uno tapa un agujero que los demás no ven. No es redundancia:

| | pregunta | agujero que caza |
|---|---|---|
| `audit_project.py` | ¿el guard existe y alguien lo llama? | **huérfano** |
| `cobertura_guards.py` | ¿ha llegado alguna vez a decir que no? | **nunca probado** |
| `audit_estados.py` | ¿lo que dice cambia el veredicto? | **mudo / rama muerta** |
| `barrido_falsos_verdes.py` | ¿sobrevive algún VERDE a romperle un campo? | **falso verde que nadie imaginó** |
| `ensayo_retro_semaforo.py` | ¿los comandos de la sesión LOCAL arrancan? | **sesión perdida** |
| `ensayo_xdiario.py` | ¿el fichero que entra en ContaPlus cuadra? | **asiento descuadrado** |
| `test_privacidad.py` | ¿la barrera bloquea lo que dice bloquear? | **dato de cliente subido** |
| `ensayo_contrato_captura.py` | ¿la captura pide lo que el motor usa? | **campo que llega con otro nombre** |
| `ensayo_corpus_roto.py` | ¿un fichero corrupto para la medición? | **cuelgue y cifras contaminadas** |
| `ensayo_orquestador.py` | ¿el histórico pierde facturas por el formato? | **guard alimentado en vacío** |
| `ensayo_cruce_303.py` | ¿el cruce inventa una correspondencia? | **cliente identificado por azar** |
| `check_subprocess_encoding` | ¿algún `subprocess.run` sin `encoding`? | **verde en Cloud, roto en el PC real** |
| `ensayo_reconstruir_303.py` | ¿la base se deriva o se sigue leyendo a pelo? | **base ficticia con aspecto de real** |

Los trece corren dentro de `audit_project.py`: basta el primer comando.

> El 13º es del 27-08 y cierra el hallazgo mayor de la sesión anterior: la
> base de `303_LOCAL.json` era un cero disfrazado de dato. Reescrito DOS
> veces el mismo día: la primera versión derivaba del gasto/ingreso
> contable (mejoraba el problema, no lo resolvía); la definitiva invierte la
> propia fórmula del 303 (`base = cuota / tipo`). Prueba cinco casos, con el
> gasto/ingreso contable deliberadamente distinto de lo que implica la
> cuota — para que si algo reintrodujera la derivación desde la
> contabilidad, lo cace de inmediato: `BASEIMPO` genuinamente relleno que
> debe ganar, multi-tipo sin reescalar, ISP (línea 477 sin venta detrás) sin
> quedarse en cero, y un asiento duplicado entre copias. Probado con el bug
> reintroducido a propósito: se pone rojo exactamente en las comprobaciones
> que ese bug rompe.
>
> Y de paso se encontró que `ensayo_retro_semaforo.py` tenía el MISMO punto
> ciego que todo esto lleva persiguiendo: su corpus sintético rellenaba
> `BASEIMPO` con el valor correcto, así que daba verde sin haber probado la
> derivación ni una vez. Corregido para que refleje la realidad (cero).

> El 12º es del 26-08 y nace de un bug que ya había mordido: `audit_project.py`
> **se rompía a la mitad en el PC de la asesoría** y no en Cloud, porque
> `text=True` sin `encoding` decodifica con la codificación del sistema. Al
> arreglarlo se barrió el repositorio y aparecieron **cinco llamadas más** con
> la misma bomba, latentes. Comprueba sobre el **AST**, no sobre el texto, y
> está probado con el bug reintroducido a propósito: se pone rojo y dice
> fichero y línea.

`audit_estados.py` se escribió tras encontrar a mano, después de semanas, que
`guard_cuenta_gasto_coherente` estaba cableado, tenía su rama `FALLO -> AMBAR`
escrita en el veredicto desde el primer día, y **no comparaba nada**: la rama era
inalcanzable. Las otras dos preguntas daban verde. Con el bug reintroducido a
propósito, lo señala en menos de un segundo.

> **Los cinco últimos son del 21-08 y los cinco encontraron defectos reales en
> su PRIMERA ejecución.** Ninguno era teórico: `--emitir-cartera` no escribía
> nada nunca, el xDiario emitía asientos descuadrados, la barrera de privacidad
> no veía una clave asignada en el código, y el barrido destapó tres agujeros que
> los 108 ataques escritos a mano no habían tocado.
>
> La lección práctica, por si sirve para lo que venga: **casi todo lo que se
> encontró estaba en las costuras** —entre una pieza y la siguiente—, no dentro
> de las piezas. Las piezas estaban bien probadas. Lo que nadie había ejecutado
> era la cadena.

---

## 2. Dónde quedó todo (20-08-2026)

| | |
|---|---|
| **Motor** | 26 guards cableados. Los 8 falsos verdes P0 **cerrados**. Resiste 87 ataques + controles positivos. Cobertura útil 26/26 |
| **Contrato de datos** | `contrato_datos.py`. `MISSING` ≠ `ZERO` ≠ `INVALID`. La ausencia ya no vale 0 |
| **Barrera de privacidad** | Agujero del `.DAT` **cerrado**: decide por contenido, no por extensión |
| **Inventario del histórico** | Falta poco. Es el trabajo de hoy |
| **Facturas reales por el pipeline** | **Cero.** Nada se ha validado todavía contra la realidad |

---

## 3. Lo primero de hoy, en este orden

### 🔍 A — Buscar las 91 facturas de la prueba antigua (30 min, puede ahorrar meses)

`PROJECT_STATUS.md` dice que el motor se probó en su día con **91 facturas reales**
más una en vivo. **Si esa ejecución sigue guardada en el disco con dos cosas —lo
que dijo el motor y lo que resultó ser correcto—, ya existe el primer conjunto de
deltas del proyecto, con 91 casos, sin pasar una factura nueva.**

Sería el primer número real, sacado de trabajo ya hecho. Mirar esto antes que nada.

**Y ya está la herramienta esperándolo:**

```bash
python validar_captura_historica.py "ruta/al/fichero.csv"
```

No hace falta que el CSV tenga ningún formato concreto: detecta las columnas
solo y dice lo que ha encontrado antes de calcular nada. Compara **tres cosas**:

| | |
|---|---|
| Lo que dijo el motor **entonces** | la columna que ya trae el fichero |
| Lo que dice el motor **de hoy** | se recalcula ahí mismo |
| Lo que resultó ser **correcto** | si alguien lo anotó |

- **Si hay veredicto humano** → la tasa de acierto real y el número de falsos
  verdes, con matriz de confusión. Es *el* número.
- **Si no lo hay** → sigue habiendo premio: te dice qué facturas cambian de
  veredicto con el motor nuevo. Eso convierte *"revisar 95"* en *"revisar las 12
  que han cambiado"*: una tarde en vez de una semana.
- **En los dos casos** → si el trabajo de estos días ha movido algo o no. Un
  motor que cambia entero y no mueve ni un caso real no ha mejorado nada, y el
  script lo dice con esas palabras.

> Es un fichero **local con datos reales**: lo abre Diego, no Claude. A Claude se
> le pasan recuentos, nunca filas.

### 📊 A-bis — El retro-semáforo (esto puede dar el primer número real HOY)

```bash
python retro_semaforo.py "RUTA_DEL_CORPUS" --limite 2000
python retro_semaforo.py "RUTA_DEL_CORPUS" --inyectar        # la pasada completa
```

**La idea:** la contabilidad de los últimos años ya está hecha. Cada asiento de
compra del histórico **es** una factura que en su día se leyó, se contabilizó y se
presentó. No hacen falta las fotos: el asiento trae los mismos campos que el motor
consume. Se reconstruye la fila desde el asiento, se pasa por el motor y se compara.

> Eso convierte *"esperar tres meses de paralelo"* en *"ejecutar un script"*, y con
> miles de casos en vez de veinte.

**Qué mide de verdad:**

| | |
|---|---|
| ✅ **Falsos rojos** | Estos asientos se presentaron. Si el motor marca ROJO al 40%, es inservible, y se sabe hoy |
| ✅ **Dónde está el ruido** | Qué guards saltan más sobre datos reales |
| ✅ **Tasa de detección** (`--inyectar`) | Coge asientos correctos, les mete errores realistas (IVA cambiado, decimal desplazado, NIF de otro) y cuenta cuántos caza |
| ❌ **Falsos verdes reales** | **No.** Que un asiento se contabilizara así demuestra que se hizo así, no que fuera correcto. Eso sigue necesitando criterio humano |

**No necesita el inventario terminado, ni fotos, ni Gemini, ni el DPA.** Solo leer
los `.DAT`, que ya se sabe hacer. Probado aquí contra un corpus sintético que
incluye los casos nuevos (tipos 21/10/4/0/5, recargo y compras sin IVA): 300
asientos correctos → 100% VERDE, 0% falsos rojos; 205 errores inyectados → 100%
detectados. Esos números son de datos inventados y no valen como medición: solo
demuestran que el mecanismo funciona.

> **Lo ejecuta Diego.** Salida agregada = recuentos, se puede subir.
> `retro_semaforo_LOCAL.json` se queda en el disco y Claude no lo abre.

### ⏱️ Cuánto tarda cada cosa — medido a escala real (21-08-2026)

Sobre un corpus fabricado del tamaño del real (**1.287 contenedores, 344.916
asientos, 275.418 evaluados**). Sirve para saber si es un café o una tarde:

| Comando | Tiempo | Memoria pico |
|---|---|---|
| `retro_semaforo.py` (pasada completa) | **55 s** | 258 MB |
| `retro_semaforo.py --emitir-cartera` | **63 s** | **713 MB** ← el más pesado |
| `reconstruir_303.py` | **5 s** | bajo |

> **Antes de hoy, la primera pasada tardaba más de 15 minutos y hubo que
> cortarla sin que terminara.** La causa era una línea que copiaba el maestro de
> proveedores entero en cada fila — cuadrático. Ya no.
>
> Todos imprimen **avance cada 5%**. No es cosmética: hoy se arregló también un
> cuelgue por cabecera corrupta, y un script callado un minuto se parece
> demasiado a uno colgado. Si ves avanzar el contador, está trabajando.

**Aviso sobre la cifra:** el corpus medido tiene el mismo *número* de asientos
que el real pero registros más cortos (10 campos frente a 91), así que en el PC
de la asesoría habrá más lectura de disco. El trabajo de CPU, que es lo que se
arregló, es el mismo.

### 🧾 A-ter — Cuadrar contra el 303 presentado (la ÚNICA verdad externa)

```bash
python reconstruir_303.py "RUTA_DEL_CORPUS" --detalle 303_LOCAL.json
```

Todo lo demás del proyecto se valida **contra sí mismo**: la aritmética de la
factura contra la factura, el patrón del proveedor contra el histórico. Es
coherencia interna, y su techo lleva escrito desde el principio en
`DISENO_APRENDIZAJE.md` §1: *el histórico dice lo que se hizo, no lo que era
correcto*.

Hay **una sola excepción**: los 303 presentados. Los presentó el despacho, los
aceptó Hacienda y llevan diez años en pie. Es un **hecho externo**, no un criterio.

**Lo que el script NO hace, y hay que tenerlo claro antes de mirar un número:**
no reconstruye un 303. Un 303 lleva prorrata, bienes de inversión,
intracomunitarias, ISP y compensación de cuotas, y nada de eso se deduce de las
cuentas de IVA. Decir «reconstruye el 303» sería vender precisión inexistente.

**Lo que sí hace:** agrega por cliente y trimestre las **bases y cuotas por
tipo**, separando repercutido (477) de soportado (472) — el contenido de las
casillas **01-09 y 28-29**.

> Si esas casillas cuadran con el 303 presentado durante cuarenta trimestres, lo
> que queda validado no es una factura: es **la cadena entera de lectura** contra
> algo que Hacienda ya dio por bueno.

**La segunda mitad del trabajo es humana y no tiene atajo:** abrir el 303
presentado de un trimestre y comparar las casillas con el `_LOCAL`. Lo único que
sube después es el recuento de cuántos cuadran — y ese recuento se le puede
enseñar a cualquiera sin enseñar un dato de cliente.

### 📑 A-quater — La cola de revisión (convierte «91 facturas» en «una tarde»)

```bash
python cola_revision.py veredicto.csv --detalle cola_LOCAL.csv
```

Toma la salida del orquestador y la agrupa **por causa, no por factura**:

```
EMPIEZA POR AQUI — la accion que mas facturas quita de la cola:
    23 facturas  ·  Conseguir el DESGLOSE por tipos de IVA de la factura
    No son 23 tareas: es UNA. Se arregla una vez y se repasan.
```

Tres montones, porque son **tres trabajos distintos** que no se hacen
entremezclados: **CORREGIR** (ROJO), **BUSCAR/VERIFICAR** (`[FALTA DATO]`) y
**DECIDIR** (`[CRITERIO]`). Y las 26 causas están traducidas a lo que hay que
hacer — *«aritmetica_base_tipo»* no le dice a nadie qué tiene que hacer.

> Los `[CRITERIO]` van aparte por algo que no es comodidad: **son las etiquetas
> que más valen del proyecto.** Son justo los casos donde el motor no puede
> decidir, así que aprender de ellas es lo único que mueve la frontera de lo
> automatizable. Perdidas dentro de un montón de «revisar», no se aprenden.

### 📋 B — Terminar el inventario (el trabajo principal de hoy)

Cuatro pasos, ya acordados:

1. Enlazar el código de empresa **entre carpetas** (regla dura: dentro de una
   misma carpeta, dos códigos distintos son dos empresas distintas, nunca se
   fusionan).
2. Explicar la caída de 2022–2023 **cruzando las altas y bajas**.
3. Clasificar los 9 contenedores sin ejercicio y los 28 `.cat`.
4. Asignar a cada par `(cliente, ejercicio)` uno de los cuatro estados y emitir
   `inventario_LOCAL.csv` + su agregado.
5. **Emitir `indice_clientes_LOCAL.json`** (`{NIF: "C07"}`) — el índice anónimo
   estable. ⚠️ **Esto es lo único que hay que acertar a la primera**: si sale
   como subproducto de usar y tirar, los modelos no se podrán enganchar después
   y habrá que rehacer las dos cosas. Ver `ARQUITECTURA_DATOS.md` §1-bis.

**Los cuatro estados** (`ARQUITECTURA_DATOS.md` §5):
`COMPLETO` · `PARCIAL_EXPLICADO` · `PARCIAL_SIN_EXPLICAR` · `INUTILIZABLE`

**Terminado = `PARCIAL_SIN_EXPLICAR` por debajo del 5%** y cada caso restante
listado uno a uno. Umbral fijado de antemano, no después de ver el resultado.

> **Lo ejecuta Diego, no Claude.** Claude escribe el script, Diego lo corre,
> Claude lee solo el agregado. Ningún NIF viaja a la API.

### 💳 C — Contratar API/Consola de Anthropic (una tarde, desbloquea el resto)

Poner la tarjeta en la Consola = cuenta comercial = **DPA incluido** al aceptar
los Términos Comerciales. Interruptor: `ANTHROPIC_API_KEY` puesta → va por API con
DPA; `unset ANTHROPIC_API_KEY` → vuelve al Pro de siempre. Comprobar con `/status`.

⚠️ **Solo funciona en sesión LOCAL.** Cloud/Web y Remote Control usan siempre la
suscripción, nunca la API key. Datos reales = sentado en el PC de la asesoría.

---

## 3-ter. ✅ Los cuatro puntos del techo: CERRADOS (20-08-2026)

| # | Punto | Estado |
|---|---|---|
| 1 | Triangulación de identidad (NIF del margen) | ✅ construida y cableada |
| 2 | Doble lectura de importes (total desde dos sitios) | ✅ construida y cableada |
| 3 | Confianza por campo | ✅ construida y cableada |
| 4 | Modelo de datos fiscal rígido (solo 4/10/21) | ✅ ampliado |

`test_adversarial.py`: **48/48 en verde**, familias J y K.

> ⚠️ **PERO el prompt v2 NO se ha probado nunca contra una factura real.** Los
> campos nuevos son aditivos —si el modelo no los devuelve, los guards son
> `NO_APLICA` y todo se comporta como antes— pero pedir más campos puede diluir
> la atención del modelo sobre los que ya funcionaban.
>
> **Las tres comprobaciones de la primera captura real** están escritas en la
> cabecera de `captura_orquestador.py`, justo debajo del prompt:
> 1. ¿Los campos de siempre se siguen leyendo igual de bien?
> 2. ¿En qué fracción de facturas aparece el total **dos veces** de verdad?
> 3. ¿El modelo **copia** el valor en `total_factura_2` en vez de dejarlo vacío?
>    Si lo copia, la comprobación es un espejo y no vale nada.

## 3-quinquies. 🔧 Lo que se cerró el 21-08 sin tocar el PC de la asesoría

Tres cosas, y las tres eran defectos reales del motor, no pulido:

**1. El guard de la cuenta de gasto no comparaba nada.** `guard_cuenta_gasto_
coherente` recibía solo la cuenta del proveedor, miraba si había patrón histórico
y devolvía `OK`. Su rama `FALLO -> AMBAR` llevaba semanas escrita en el veredicto
y era **código inalcanzable**. El guard que el propio proyecto describe como *"la
cuenta no casa con lo que dice el histórico"* era incapaz de detectar que no
casaba. Ahora compara por **grupo del PGC** (3 dígitos: 629000 y 629001 son la
misma decisión con distinto detalle; 600 y 621 no) y exige **3 asientos mínimo**
antes de acusar — "unánime" sobre un solo asiento es una anécdota, no diez años
de criterio.

> Y lo que más importa de este caso: **no lo tapaba la falta de test, lo tapaba
> el test**. Se conformaba con *"distinto de OK"*, y `NO_APLICA` es distinto de
> `OK`. Es exactamente el fallo de método que la FAMILIA G existe para cazar,
> cometido dentro de la propia suite.

**2. El motivo decía una cosa de seis.** Una factura con seis defectos reales
—NIF imposible, IVA que no es el 21%, total que no cuadra, fecha anterior al
alta, ejercicio equivocado, diferencia que no es ninguna retención— devolvía **un
solo motivo**. Arreglas ese, vuelves a pasar el motor, aparece el siguiente:
seis vueltas para una factura. Ahora salen todos, con el titular intacto para no
romper a quien lo lea. **Esto se nota directamente en la cola de revisión de las
91 facturas.**

**3. `secuencia_documental` era el único ÁMBAR sin etiqueta.** Salía sin
`[CRITERIO]` ni `[FALTA DATO]`, así que la cola no sabía en qué montón ponerlo.

### Y una lección de método que vale más que los tres arreglos

Al reestructurar los ÁMBAR en una tabla, `check_cableado` declaró **siete
huérfanos que no lo eran**: buscaba `guards.get("X"` con una expresión regular,
así que solo veía el cableado escrito de *una forma*. No había cambiado el
cableado — había cambiado su forma.

> Es la misma lección que `.claude/rules/datos.md` deja escrita sobre el escáner
> de privacidad (*"una barrera que decide por el **nombre** es de conveniencia;
> la que decide por el **contenido** es la real"*), pagada al revés: allí dejaba
> pasar lo peligroso, aquí acusaba a lo inocente. **Un auditor que grita cuando
> no toca acaba ignorándose, y entonces no avisa cuando sí toca.**

Reescrito sobre AST. La forma deja de importar.

### Y lo más importante que salió de todo esto, para mañana

**Los tres comandos de la sesión LOCAL están ensayados en seco.**
`ensayo_retro_semaforo.py` fabrica un corpus sintético con la forma exacta de
ContaPlus (`.DAT` que son ZIP, con `Diario.dbf` dentro, dBase III, cp1252) y
ejecuta la cadena entera en 0,4 s. Corre dentro de `audit_project.py`.

Hasta ayer **ninguno de los tres se había ejecutado nunca**, ni una vez. En la
primera ejecución aparecieron tres cosas que habrían quemado la sesión:

1. **`--emitir-cartera` no escribía nada. Nunca.** Aceptaba la ruta, gastaba
   memoria acumulando líneas, y `construir_mapeo_cartera` no se llamaba desde
   ahí. El fichero que `orquestador.py` espera en `--cartera-json` **no había
   forma de producirlo**: la cadena *"el criterio sale de los diez años"* estaba
   rota en el último eslabón, con las dos puntas hechas y probadas.

2. **`validar_captura_historica.py` mentía de dos formas.** Excel en español
   exporta con **punto y coma**, y con el separador equivocado `csv.DictReader`
   no falla: devuelve UNA columna con la línea entera dentro. El script seguía e
   imprimía *"TASA DE ACIERTO: 0.0%"* y *"FALSOS VERDES: 0"*. Un número que
   significaba "no he podido leer nada", presentado como medición — y cero
   falsos verdes **suena a perfecto**. Además solo detectaba solas las dos
   columnas de veredicto: una cabecera `NIF` en mayúsculas dejaba el campo
   MISSING y sacaba el 100% en ÁMBAR.

3. **Sin desglose por tipos, TODA factura salía ÁMBAR.** Y una captura de cámara
   normal no trae desglose: trae base, IVA y total. Las 91 facturas habrían
   salido las 91 en ÁMBAR y no se habría medido nada.

> El punto 3 es el que más cambia lo de mañana. Ahora una factura con base, IVA
> y total coherentes **al 21% o al 0%** llega a VERDE. **Solo esos dos**, y no
> por prudencia: son los únicos tipos que no se pueden fabricar mezclando.
>
> Lo aprendí por las malas en el mismo rato: mi primera versión aceptaba
> cualquier tipo legal, con un razonamiento que parecía sólido y estaba
> incompleto. La prueba de fuerza bruta que escribí después encontró 16 formas
> de colarse, y la más realista es una factura de supermercado: **100 € al 0% +
> 100 € al 10% dan un 5% efectivo clavado**, y el 5% es legal desde 2023.
> Habría salido VERDE afirmando una composición fiscal falsa.

**Qué esperar mañana con las 91 facturas**, para no confundir un resultado con
un fallo: si el fichero trae base/IVA/total, las del 21% y del 0% saldrán VERDE
o ROJO; las de tipos intermedios saldrán **ÁMBAR `[FALTA DATO]`** pidiendo el
desglose. Eso **no es el motor fallando**: es el motor negándose a afirmar una
composición que no puede comprobar. Si salen muchas ÁMBAR de esas, lo que dice
es que **la captura tiene que emitir `tramos_iva`**, que es justo lo que el
prompt v2 ya pide.

---

---

## 3-quater. 📐 El límite acordado — leer antes de decidir qué automatizar

`TECHO_Y_LIMITES.md`, sección final. En una frase:

> El motor alcanza **todo lo verificable** contra la factura, el histórico, la
> norma y los modelos presentados. **No alcanza** lo que depende de un hecho del
> mundo que no está en ningún dato — si aquella cena fue de trabajo, si ese
> ordenador se usa en la empresa o en casa.

Cada caso cae en **un cubo y solo uno**:

| Cubo | Quién decide |
|---|---|
| **1 · AUTOMATIZABLE** — verificable contra un dato | El motor; el humano audita por muestreo |
| **2 · ASISTIDO** — el motor trae la evidencia, no concluye | El humano, con la evidencia delante |
| **3 · HUMANO PERMANENTE** — depende de un hecho del mundo | El humano, siempre |

> ⚠️ **El cubo 3 se declara por adelantado y solo puede CRECER.** Un caso sale de
> ahí únicamente con evidencia nueva, **nunca porque convenga o porque "casi
> siempre acierta"**. Sin esa regla, los casos migran del 3 al 1 uno a uno, cada
> uno con su buena razón, y un día el sistema decide cosas que nadie decidió que
> decidiera.

**El techo está alcanzado cuando:** todo caso se clasifica sin ambigüedad, el
cubo 3 está *caracterizado* (se sabe qué tipos caen ahí, no solo cuántos), y la
tasa de falsos verdes **dentro del cubo 1** está medida y bajo el umbral fijado
de antemano.

## 4. La decisión que hay que tomar hoy, antes de seguir tocando el motor

**Acordado el 19-08:** primero se cierra bien el motor, después se valida. Decisión
de Diego y es defendible: medir la tasa de falsos verdes de un motor que va a
cambiar produce un número que caduca.

**Lo que falta y hay que escribir HOY:** la línea de meta. *"Cerrar bien el motor"*
sin criterio absorbe tiempo indefinido, igual que le pasaba a *"pulir el inventario
hasta fiarnos"* antes de fijar el 5%.

> **Escribir, antes de tocar un guard más: ¿qué tiene que ser cierto para decir
> que el motor está cerrado?**

Sugerencia de partida, para discutir, no para aceptar sin más:

- Las 25 pruebas adversariales en verde (ya lo están).
- Los guards que hoy dependen de datos que nadie produce, resueltos o declarados:
  `categoria_producto` (deuda ya anotada) y el estado `MEDIA` de
  `guard_confianza_captura`, hoy inalcanzable.
- El histórico conectado a la decisión de verdad: `guard_cuenta_gasto_coherente`
  ya está cableado, pero recibiendo el mapeo real, no `{}`.
- **Y un número de facturas reales pasadas de punta a punta.** Aunque sea 20.

---

## 5. Las dos columnas — cuesta cero y sin ellas no queda rastro

En cuanto empiecen a pasar facturas, la salida lleva **dos** veredictos:

```
VEREDICTO_MOTOR    VEREDICTO_HUMANO
VERDE              VERDE       -> coincide
VERDE              MAL         -> FALSO VERDE  <- este es el dato que decide todo
AMBAR              BIEN        -> falso ámbar, ruido
```

**"Un verde es verde" es una afirmación sobre el mundo y solo se comprueba así.**
No es trabajo aparte de fiarse de los verdes: es la única forma de poder fiarse.
Cada factura revisada sin anotar las dos columnas es una etiqueta perdida.

---

## 5-bis. Auditoría de inventario (20-08-2026, cerrada 26-08-2026)

> **Verificado el 26-08-2026 contra el código actual, no contra este texto
> (jerarquía de `CLAUDE.md`: Código → Tests → Git → documentación).** Los tres
> hallazgos de "piezas desconectadas" y los dos de "declarado y no usado" ya
> estaban resueltos en el código; solo faltaba confirmarlo aquí. Detalle en
> `PROJECT_STATUS.md`, entrada 26-08-2026. Lo único que seguía abierto de
> verdad — los ficheros de otro dominio — ya se quitó del repo ese mismo día.

Cerrado, ya no hace falta repasarlo:
- `triangulacion_identidad_v0.py` cableado (`motor_veredicto.py`,
  `guard_triangulacion_identidad`).
- `escribir_xdiario()` ya la llama `orquestador.py`.
- `captura_orquestador.py --proveedor` ya tiene default `"gemini"`, no
  `"claude"` — la migración a Gemini quedó completa.
- Los cuatro JSON del agrupamiento por huella invalidado
  (`fase0_huella*.json`, `fase0_reagrupa.json`, `fase0_umbral.json`) ya llevan
  `"INVALIDADO": true`.
- Los seis ficheros del módulo de cripto (FIFO, lotes, permutas, staking,
  Bitget) que ya habían confundido a un auditor externo —
  `guard_g7_ledger.py`, `DIA3_ESTADO_PARCIAL.md`, `DIA3_SPEC_C1_TACTICAS.md`,
  `MATRIZ_COBERTURA_v1.md`, `CATALOGO_EVENTOS_v1.md`,
  `TRIAJE_RONDA_2026-07-13.md` — **eliminados del repositorio.** Si hacen
  falta, viven fuera de este proyecto.

Sigue pendiente de verificar (no urgente, no bloquea nada): que el
identificador de modelo `modelo="claude-sonnet-4-6"` en la rama `--proveedor
claude` de `captura_orquestador.py` (opción secundaria, no la que se usa por
defecto) siga vigente si alguna vez se usa esa rama.

## 6. Lo que NO se hace hoy

- Guards nuevos sin un caso real que los pida (`CLAUDE.md`).
- Nada de laboral ni mercantil todavía.
- El cuadre del 303: necesita el corpus de modelos inventariado primero — el 390
  **no está** dentro de las copias (`FASE0_RESULTADOS.md` §11.1).
- Nada del menú de monetización (`DIRECCION_PRODUCTO.md`).
- Más auditorías estratégicas externas: ya dieron lo que tenían que dar.

---

## 7. Pendientes que no son código y siguen abiertos

1. **Cifrar el USB de copia.** 15 minutos. Es lo de mayor impacto por coste de
   toda la lista y lleva abierto desde el 12-08.
2. Clave de recuperación del cifrado, fuera del equipo.
3. Confirmar si la copia del USB incluye modelos, escrituras y DNIs, o solo
   contabilidad.

---

## 8. Los documentos, y para qué sirve cada uno

| Fichero | Cuándo se lee |
|---|---|
| **`EMPEZAR_AQUI.md`** | Este. Para arrancar |
| `PROJECT_STATUS.md` | Para consultar el estado detallado |
| `ARQUITECTURA_DATOS.md` | La espina `(cliente, periodo)`, el orden y las puertas |
| `DISENO_APRENDIZAJE.md` | Correcciones, telemetría por delta, caducidad de reglas |
| `DIRECCION_PRODUCTO.md` | Hacia dónde va, y qué queda descartado |
| `FASE0_RESULTADOS.md` | Los números medidos del histórico |
| `TECHO_Y_LIMITES.md` | Qué hay por encima del motor actual, medido |
| `.claude/rules/datos.md` | La frontera de datos. Manda sobre todo lo demás |
