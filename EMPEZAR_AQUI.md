# EMPEZAR AQUÍ — 20-08-2026

Punto de entrada único. Corto a propósito: `PROJECT_STATUS.md` tiene 700 líneas y
sirve para consultar, no para arrancar. Esto sirve para arrancar.

---

## 1. Primer comando, antes de leer nada

```bash
python3 audit_project.py
```

Debe salir esto. Si no sale, algo se rompió y eso manda sobre todo lo demás:

```
✅ Sintaxis de todos los .py
✅ Cableado de guards (sin huérfanos): 20 guards, todos consultados
✅ Suite de pruebas (test_motor_veredicto.py): 21/21 checks en verde
✅ Bateria adversarial (test_adversarial.py): 25 en verde, 0 fallan
❌ Dependencias: faltan dbfread, anthropic, google-genai   <- NORMAL, son de captura
```

---

## 2. Dónde quedó todo (19-08-2026)

| | |
|---|---|
| **Motor** | 20 guards cableados. Los 8 falsos verdes P0 **cerrados**. Resiste 25 ataques + controles positivos |
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
los `.DAT`, que ya se sabe hacer. Probado aquí contra un corpus sintético: 400
asientos correctos → 100% VERDE, 0% falsos rojos; 307 errores inyectados → 100%
detectados. Esos números son de datos inventados y no valen como medición: solo
demuestran que el mecanismo funciona.

> **Lo ejecuta Diego.** Salida agregada = recuentos, se puede subir.
> `retro_semaforo_LOCAL.json` se queda en el disco y Claude no lo abre.

### 📋 B — Terminar el inventario (el trabajo principal de hoy)

Cuatro pasos, ya acordados:

1. Enlazar el código de empresa **entre carpetas** (regla dura: dentro de una
   misma carpeta, dos códigos distintos son dos empresas distintas, nunca se
   fusionan).
2. Explicar la caída de 2022–2023 **cruzando las altas y bajas**.
3. Clasificar los 9 contenedores sin ejercicio y los 28 `.cat`.
4. Asignar a cada par `(cliente, ejercicio)` uno de los cuatro estados y emitir
   `inventario_LOCAL.csv` + su agregado.

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

## 3-bis. 🔴 Antes de dar el motor por cerrado: lee `TECHO_Y_LIMITES.md`

Medido el 20-08-2026: **tres de cada cuatro tipos de factura legal que se
probaron dan ROJO.** No es un fallo del motor, es el modelo de datos, que solo
sabe representar 4/10/21.

| Caso | Hoy |
|---|---|
| Recargo de equivalencia 5,2% — **cotidiano en autónomos de comercio** | 🔴 ROJO |
| Intracomunitaria (inversión del sujeto pasivo) | 🔴 ROJO |
| Tipo 0% | 🔴 ROJO |
| Exenta art. 20 (médico, seguro, alquiler de vivienda) | 🟠 AMBAR |

19 de los 33 clientes son autónomos. Esto no es un caso de laboratorio.

**Predicción que se comprueba en la misma ejecución del retro-semáforo:** si al
desglosar los ROJO por motivo dominan `cuadre_total`, `suma_tramos` y
`nif_digito_control`, el problema es el modelo de datos y no el motor.

`test_adversarial.py` imprime estos cuatro casos en cada ejecución, bajo
"TECHO CONOCIDO", para que no se olviden.

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

## 5-bis. Auditoría de inventario (20-08-2026) — lo que falta y lo que sobra

### 🔴 Piezas construidas que NO están conectadas a nada

**Es el fallo que más se repite en este proyecto: construir, probar aislado, no
conectar.** Van cuatro veces. `audit_project.py` ya avisa de las dos primeras.

| Pieza | Estado |
|---|---|
| `triangulacion_identidad_v0.py` | **Nadie la importa.** Es la defensa contra el error de captura más peligroso (NIF con checksum válido que resulta ser de otro proveedor real). Está muerta |
| `escribir_xdiario()` en `layout_diario_contaplus.py` | **Nadie la llama.** Es el ÚLTIMO TRAMO del objetivo (`… → fichero importable → ContaPlus`). El orquestador solo importa la parte de lectura y escribe un CSV de veredictos |
| `guard_g7_ledger.py` | Nadie lo importa — y además es de cripto, no de contabilidad |
| 3 guards del motor | ✅ ya cableados el 19-08 |

> `escribir_xdiario` es el más grave: **el objetivo declarado del producto es
> llegar a ContaPlus, y ese paso está escrito y desconectado.**

### 🟠 Declarado y no usado

- `cache_maestro_proveedores` y `cache_iva_por_concepto`: en `config.example.json`
  y el orquestador no las carga. Se ejecuta sin maestro y sin caché de IVA.
- `salida_csv_veredicto`: declarada, se usa `--salida` en su lugar.
- `google-genai` está en `requirements.txt` y `captura_orquestador.py` lo importa
  dentro de una función, así que el chequeo de dependencias no lo veía.

### 🟠 La migración a Gemini está a medias, y es peligroso en silencio

La decisión cerrada es **Gemini primero**. Pero `captura_orquestador.py`:
- La cabecera dice *"Llama a la API de Claude"* y pide `ANTHROPIC_API_KEY`.
- `leer_factura(..., proveedor="claude")` y `--proveedor` tiene `default="claude"`.

Quien ejecute el script sin argumentos usa el proveedor equivocado sin enterarse.
Conviene además **verificar que el identificador de modelo sigue vigente**
(`modelo="claude-sonnet-4-6"`), que no se ha comprobado.

### 🗑️ Lo que sobra: cinco ficheros de un dominio distinto

`guard_g7_ledger.py`, `DIA3_ESTADO_PARCIAL.md`, `MATRIZ_COBERTURA_v1.md`,
`CATALOGO_EVENTOS_v1.md` y `TRIAJE_RONDA_2026-07-13.md` son del **módulo de
cripto** (FIFO, lotes, permutas, staking, Bitget). No es que no valgan: están en
el sitio equivocado, y **ya han confundido a un auditor externo**, que leyó
`MATRIZ_COBERTURA_v1.md` como si fuera la matriz de cobertura del motor de
facturas.

### 🗑️ Y cuatro JSON con recuentos que el propio repo declara falsos

`fase0_huella.json`, `fase0_huella_v2.json`, `fase0_reagrupa.json` y
`fase0_umbral.json` vienen del agrupamiento por huella, **invalidado** el 12-08
(`PROJECT_STATUS.md`). Se conservan "como registro del proceso", pero son una
trampa: una sesión futura puede leerlos como datos. Si se quedan, deben llevar
`"INVALIDADO": true` dentro. Los scripts que los produjeron
(`fase0_huella_cliente`, `fase0_huella_v2`, `fase0_reagrupa`,
`fase0_umbral_correcto`, `fase0_localiza_identidad`) están superados por el
hallazgo del patrón `SP_C_04A`.

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
