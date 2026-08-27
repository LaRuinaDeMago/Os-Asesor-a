# FASE 0 — Resultados medidos

**Fecha de ejecución:** 11-08-2026
**Corpus:** copias de seguridad de ContaPlus del despacho, 2016–2026. Carpeta local,
fuera del repositorio. Nunca sube nada de ella.
**Método:** los seis scripts `fase0_*.py` de este repositorio, ejecutados en local.
Ninguna fila de dato real llegó al modelo: todos los scripts están construidos para
emitir únicamente recuentos, porcentajes y estructura del PGC.

> Números medidos, no estimados. Donde algo no se ha medido, se dice.

---

## 1. Qué hay en el corpus

| Medida | Valor |
|---|---|
| Ficheros totales | 4.413 |
| Tamaño | 971,3 MB (1.018.463.150 bytes) |
| Carpetas | 157 (28 subcarpetas de primer nivel) |
| Errores de lectura | **0** |

| Extensión | n | MB |
|---|---|---|
| `.dat` | 3.857 | 788,9 |
| `.pdf` | 478 | 191,6 |
| `.cat` | 28 | 9,3 |
| resto | 50 | 28,6 |

## 2. Formato — resuelto

**Los `.DAT` son archivos ZIP** (firma `50 4B 03 04` = `PK\x03\x04`), no ficheros de
datos. Dentro hay bases de datos **dBase III+** con índices FoxPro.

| Medida | Valor |
|---|---|
| Contenedores `.DAT` | 3.857 |
| ZIP válidos | **3.857 (100%)** |
| ZIP corruptos | **0** |
| Entradas totales | 261.124 |
| Dato descomprimido | 7.794 MB |

Extensiones internas: `.dbf` 137.740 · `.cdx` 96.395 · `.asc` 10.280 · `.txt` 10.280 · `.rtf` 6.429

Tablas relevantes: `Diario.dbf` (1.287 copias, 866 MB) y `SubCta.dbf` (1.205 copias, 612 MB).

> **Consecuencia para la barrera de privacidad:** la regla "ningún `.zip` sube al
> repositorio" y el patrón `*.zip` del `.gitignore` están escritos sobre la
> **extensión**. Estos ficheros son ZIP con extensión `.dat` y pasarían por delante
> de ambos sin que salte nada. La regla debería mirar la **firma**, no el nombre.

## 3. Esquema — estable en diez años

`Diario.dbf`: **91 campos, 954 bytes por registro, dBase III+ sin memo.**

| Medida | Valor |
|---|---|
| Cabeceras leídas | 1.287 |
| Esquemas distintos | **1 — ESTABLE** |
| Longitud de registro | 954 en las 1.287 |
| Registros por copia | 0 – 9.133 |

**Ni un campo añadido, movido ni redimensionado entre 2016 y 2026.** El lector
necesita un solo formato, no una matriz de versiones por año.

## 4. TEST_ENCODING — resuelto, y corrige el plan

| Rango de bytes en campos de texto | Recuento |
|---|---|
| `A0–A5` (CP850/CP437) | **0** |
| `E0–FC` (CP1252/Latin-1) | **14.141** |
| `C3` (marca UTF-8) | **0** |

**Veredicto: `cp1252`.** Sin ambigüedad.

> ⚠️ **Corrige el supuesto del plan.** El flujo operativo (§3.6c, punto 8) afirma
> *"ContaPlus antiguo usa CP850/CP437"* y lo convierte en puerta bloqueante. **Es
> falso para este corpus.** Leer con CP850 corrompería todas las tildes y eñes.
>
> Cautela honesta: solo 14.141 bytes acentuados sobre ~23 millones de caracteres de
> concepto (0,06%), muy poco para ser castellano — probablemente porque los conceptos
> se teclean en mayúsculas sin tildes. La dirección del veredicto no cambia (0 contra
> 14.141), pero la muestra de acentos es escasa.

## 5. Volumen — S15 medido

### Por línea
| Medida | Valor |
|---|---|
| Líneas totales (todas las copias) | 948.486 |
| Marcadas como borradas (dBase) | 7.051 |
| Líneas vivas | 941.435 |
| **Líneas únicas** | **348.716** |
| Factor de duplicación | 2,70x |

### Por asiento
| Medida | Valor |
|---|---|
| Asientos totales | 275.566 |
| **Asientos únicos** | **101.122** |
| Factor de duplicación | 2,73x |
| Cuadran debe = haber | **98,42%** |

Líneas por asiento: **69,22% tienen exactamente 3** · 13,20% tienen 2 · 10,93% tienen 4.

## 6. ¿Se puede reejecutar el motor sobre el histórico? — S16 medido

**Sí: 68,26%.**

| Criterio | Resultado |
|---|---|
| Asientos con NIF de contraparte | 74,18% |
| Asientos con tipo de IVA | 72,52% |
| Asientos con ambos | 68,80% |
| **Reconstruibles (patrón completo + NIF + tipo)** | **188.089 — 68,26%** |

> ⚠️ **Error metodológico corregido durante la sesión.** La primera medición se hizo
> **por línea** y dio **0,0%**. Era la pregunta equivocada: en ContaPlus una factura se
> reparte entre varias líneas del mismo asiento (`6xx` base, `472` cuota y tipo,
> `400` contraparte), así que ninguna línea puede tener todos los campos. La unidad de
> análisis es el **asiento**. Medido bien, pasa de 0% a 68,26%.

### El misterio de `BASEIMPO`, resuelto

`BASEIMPO` está relleno solo en el **0,78%** de las líneas. No importa: **la base se
deriva del propio asiento.**

Sobre 105.307 compras simples de 3 líneas:

| Comprobación | Resultado |
|---|---|
| `base + cuota = total` | 102.431 — **97,27%** |
| además `base × tipo = cuota` | 101.557 — **96,44%** |

## 7. Patrón de los asientos — el corte vertical, elegido por los datos

| Patrón | n | % |
|---|---|---|
| Compra completa (`6xx` + `472` + acreedor) | 131.756 | **47,81%** |
| Venta completa (`7xx` + `477` + deudor) | 80.917 | **29,36%** |
| Otros | 41.688 | 15,13% |
| Gasto/ingreso sin patrón | 21.205 | 7,70% |

**Los dos ciclos estándar son el 77,17% del histórico.** El primer corte vertical
(§3.6b) es la factura de compra: `600 → 472 → 400`.

### Distribución del PGC (120 grupos distintos)

| Cuenta | % de líneas |
|---|---|
| 472 IVA soportado | 16,37% |
| 400 proveedores | 12,59% |
| 430 clientes | 11,81% |
| 600 compras | 10,50% |
| 477 IVA repercutido | 9,40% |
| 700 ventas | 8,72% |
| 572 bancos | 6,06% |
| 410 acreedores | 5,70% |

**Las seis primeras son el 69% de todas las líneas.**

## 8. Los siete casos especiales de la spec v1.4 — frecuencia CERO

| Campo | Relleno |
|---|---|
| `RECTIFICA` (rectificativas) | 0,00% |
| `LCRITCAJA` / `NCRITCAJA` (criterio de caja) | 0,00% |
| `LRECT349` (modelo 349) | 0,00% |
| `LARREND347` (modelo 347) | 0,00% |
| `METAL` (pagos en metálico) | 0,00% |
| `NIRPF` (retenciones) | 0,00% |
| `TBIENTRAN` (bienes de inversión) | 0,00% |

**Ni una sola aparición en 941.435 líneas.** Dos lecturas posibles, y hay que decidir
cuál antes de construir nada sobre ellas:

1. Esas situaciones no se dan en esta cartera de clientes, o
2. ContaPlus las registra en el módulo de facturas, no en el diario.

En cualquiera de los dos casos: **el motor tiene guards construidos para casos que el
histórico no respalda**, lo que contradice la regla del proyecto de no añadir un guard
sin un caso real que lo pida. Pendiente de decidir.

## 9. PDFs — pendiente de prueba real

478 PDF, 191,6 MB, ≥8.917 páginas (cota inferior). Son los diarios y el informe que se
presentan al Registro Mercantil, generados desde ContaPlus.

Clasificación **heurística, no concluyente**: 426 con capa de texto probable, 45 con
aspecto de escaneado, 7 indeterminados. De los 40 analizados descomprimiendo streams,
**ninguno tenía cero texto** (media 506 operadores).

> ⚠️ **No dar por buena esta cifra.** El detector busca la marca `/Font` en bytes
> crudos y no la ve cuando va dentro de un flujo comprimido (PDF 1.5+), así que
> infravalora. Hace falta una prueba de extracción real. **Sin medir.**

## 10. Restricciones del dominio — confirmadas por el titular (11-08-2026)

Tres hechos sobre cómo se ha trabajado estos diez años. **No son detalles: cada uno
invalida un diseño que parecía razonable.** Hay que tenerlos delante antes de calcular
la consistencia por par.

### 10.1 El código de subcuenta NO identifica a un tercero

El mismo proveedor puede ser la `400001` en un cliente y la `400035` en otro. Y al
revés: el mismo código en dos clientes puede ser dos proveedores distintos. Ocurre
porque, entre clientes de actividad parecida (p. ej. dos bares), **se copia buena parte
del cuadro de cuentas al dar de alta**, para ahorrar trabajo — así que hay códigos
heredados que apuntan a cosas distintas o que nunca se usaron. Lo mismo aplica a los
clientes (cuentas 430).

> **Consecuencia de diseño:** la identidad del tercero sale del **NIF** (`TERNIF`,
> relleno en el 74,18% de los asientos), **nunca del código de subcuenta**. Agrupar por
> código produciría un resultado con toda la apariencia de ser correcto y sin ningún
> valor.

### 10.2 El código de empresa de ContaPlus varía de un año a otro

El número del nombre de contenedor (`SP_C_04.DAT`) es el código de empresa de
ContaPlus, pero **no apunta al mismo cliente todos los años**. No sirve para seguir a un
cliente a lo largo del histórico.

> **Consecuencia de diseño:** la identidad del cliente hay que sacarla de la tabla de
> empresas de dentro del ZIP (nombre y NIF), mantenerla **solo en local**, y sustituirla
> por un índice anónimo estable antes de cualquier agregado.

### 10.3 ⚠️ El cuadro de cuentas se arrastra de un ejercicio al siguiente

Al cerrar un año y abrir el siguiente, se mantienen todos los proveedores y clientes en
las mismas cuentas que tenían. Es la práctica normal del oficio y el programa lo ofrece.

**Pero tiene una consecuencia que condiciona toda la medición de consistencia:** si la
cuenta del año pasado ya viene puesta, la consistencia observada es **en parte
mecánica** — refleja el arrastre del programa, no una decisión repetida cada año.

Esto convierte el aviso del §3.2 del flujo (*"un par que lleva diez años yendo a la
cuenta equivocada tiene consistencia del 100%, y el sistema automatiza el error a
escala"*) en **estructural para este corpus, no hipotético**. Tres consecuencias:

1. **Una consistencia alta era de esperar y no prueba corrección.** Un 95% no significa
   95% de acierto: significa que el arrastre funcionó.
2. **La señal valiosa está donde la consistencia SE ROMPE.** Un cambio de cuenta, con el
   arrastre en contra, es una decisión consciente. Eso sí es información.
3. **La mitigación del §3.2 pasa de recomendable a obligatoria:** memoria y árbol en
   desacuerdo → excepción de prioridad máxima, nunca verde.

### 10.4 El concepto es necesario en la clave — S14 confirmado con caso real

Un mismo proveedor puede ir legítimamente a cuentas distintas según qué facture. Caso
aportado por el titular: una operadora de telefonía factura el servicio mensual (cuenta
de gasto) y algún día un terminal (inmovilizado material). Mirando solo el par
(cliente, tercero) parece incoherencia, y no lo es.

> **Consecuencia:** la clave `(cliente, tercero)` se queda corta. Hace falta el concepto
> o tipo de gasto como tercera dimensión. **S14 deja de ser un supuesto abierto.**

### 10.5 Sobre los guards del motor sin caso histórico

Los siete casos especiales aparecen 0,00% de las veces (§8). El titular confirma que se
construyeron previendo casos futuros y horizontes a los que el despacho pueda llegar.
**Decisión: se quedan.** Matiz que sí hay que registrar: **no están mal, están sin
validar.** Un guard nunca ejercitado contra un caso real se disparará por primera vez en
producción sin evidencia de que acierta, así que **no cuentan como "motor probado"**.
Pendiente marcarlos `NO_VALIDADO`.

## 11. Identidad del cliente e inventario (12-08-2026)

### 11.1 La identidad NO está en las copias — cuatro vías descartadas con número

Una copia de ContaPlus no dice de qué empresa es: el nombre y el NIF viven en el
registro global de la instalación, no en la copia (por eso al restaurar el programa
pregunta a qué empresa meterla).

| Vía | Medición | Veredicto |
|---|---|---|
| Nombre de subcarpeta | Van por fecha de copia, no por cliente | Descartada |
| Código de empresa (`SP_C_04`) | El mismo cliente aparece como `SP_C_07`, `_32`, `_71`, `_76`, `_82` | Descartada |
| `datempre.dbf` | Tiene `CNIFEMP` y `CNOMEMP` pero **0 registros** en los 97 contenedores que lo llevan | Descartada |
| `DATOS.ASC` | 1 fichero distinto, **tamaño 0 bytes** en los 2.570 | Descartada |
| `LegalC.dbf` | 15 valores distintos, 0% constante: es el catálogo fijo de libros | Descartada |
| `M390A.dbf` | **1.268 de 1.287 copias enteramente a cero** | Descartada |
| `TelDat` / `Datnic` | Sin campos de texto con valor | Descartadas |

**Por qué el código varía:** ContaPlus crea **una "empresa" nueva por cada ejercicio**.
No reasigna códigos al azar: cada año es una empresa distinta para el programa.

**`M390A.dbf` en blanco cierra también el corte vertical propuesto el 11-08:** no se
puede cuadrar el 303 contra esa tabla. La validación fiscal necesita las carpetas de
modelos presentados, que están **fuera** de `100% contabilidad`.

### 11.2 La huella dactilar por contrapartes — funciona

Si la copia no dice de quién es, se deduce de su contenido: el **conjunto de NIF de
contrapartes** de `SubCta.dbf` es una huella de la empresa. Nunca hace falta saber
quién es nadie; salen grupos anónimos.

**Evidencia de que la separación es real, no fabricada por el umbral:**

| Prueba | Resultado |
|---|---|
| Histograma de similitud (696.790 pares) | **Bimodal**: 95,4% por debajo de 0,1; valle en 0,3–0,4 (466 pares); 3,3% por encima de 0,4 |
| Estabilidad del nº de grupos | **35 → 35 → 36 → 38** entre umbrales 0,30 y 0,60. Meseta plana |
| Grupos en varias subcarpetas | **34 de 35** (uno en 27 subcarpetas) → no agrupa por fecha |
| Validación manual del grupo mayor (73 copias) | **89,2%–100%** de contrapartes en común en 12 copias muestreadas → **un solo cliente** |

Herramienta de validación manual: `fase0_ver_grupo.py` (local, imprime nombres reales
en pantalla, no escribe fichero; su salida nunca se pega en el chat).

### 11.3 Inventario — el mapa del histórico

| Medida | Valor |
|---|---|
| Contenedores con diario | 1.287 |
| **Sin diario ni subcuentas** | **2.570 — sin examinar** |
| Sin cliente asignado (huella < 5 NIF) | 106 |
| **Clientes detectados** | **35** |
| Pares cliente-ejercicio | 206 |
| **Ejercicios completos hasta diciembre** | **163 (79,1%)** |
| Coherencia con la fecha del nombre de carpeta | 935 correctas, 18 anómalas, 334 sin fecha |

**El mapa tiene tramos continuos, no agujeros interiores.** Los huecos están al principio
(altas) o al final (bajas). Un archivo con copias perdidas tendría agujeros aleatorios en
medio de un tramo; este no los tiene.

> ⚠️ **Corrige la premisa del proyecto: el corpus contable es 2018–2026, no 2016–2026.**
> Los ejercicios presentes son 2011 (un caso suelto), 2018, 2019, 2020, 2021, 2022, 2023,
> 2024, 2025 y 2026. **No hay 2016 ni 2017** en esta carpeta.

### 11.0 ⛔ AVISO: LOS RECUENTOS DE CLIENTE DE §11.2, §11.3 Y §11.4 SON FALSOS

Resuelto el 12-08-2026 por la tarde. **La huella dactilar fusionaba clientes** y todos
los recuentos que produjo están mal. Se conservan como registro del proceso, no como
resultado. La sección **§12** tiene los números verificados.

| Dato publicado antes | Realidad |
|---|---|
| 35 / 38 / 39 / 40 "clientes" | Fusionados. Ninguno es correcto |
| 23–24 clientes activos en 2025 | **Son 33** |
| Mapa de cobertura, 78,9% completos | Invalidado: se agrupó sobre clientes fusionados |

Ficheros con recuentos de cliente erróneos: `fase0_huella.json`, `fase0_reagrupa.json`,
`fase0_huella_v2.json`, `fase0_umbral.json`, `inventario_agregado.json`.

**Lo que NO se invalida** (no depende del agrupamiento): formato, esquema, codificación,
348.716 líneas únicas, 101.122 asientos, 68,26% reconstruibles, y el recuento de
sociedades presentadas por año.

### 11.4 ⚠️ ABIERTO: 35 grupos frente a 43 clientes reales en 2025

El titular confirma **43 clientes solo en 2025**; el mapa detecta **23 activos ese año** y
**35 en total**. La discrepancia no está explicada. Cinco candidatas, ninguna descartada:

1. **Los 2.570 contenedores sin diario están sin examinar.** Es un 67% del corpus y podría
   contener contabilidades de otros clientes en otro formato. **La más probable, y es un
   error de orden de trabajo: el inventario se construyó sobre un tercio del corpus sin
   averiguar antes qué era el resto.**
2. El umbral `MIN_NIFS = 5` de `fase0_huella_cliente.py` es una elección arbitraria sin
   medir; descartó 106 contenedores. Un cliente con pocos proveedores se cae del mapa.
3. La huella podría estar fusionando clientes parecidos (solo se validó 1 grupo de 35).
4. Puede que muchos clientes sean **autónomos sin contabilidad en ContaPlus** (solo libros
   registro). Eso lo confirma el titular, no un script.
5. Puede que no se hicieran copias de todos.

**Pista sin explotar:** varios nombres de carpeta contienen "ORDENADOR JOSE", lo que apunta
a otro equipo con contabilidades. Si faltan clientes y faltan 2016–2017, pueden no estar en
esta carpeta.

**Nada de la Fase 0 avanza hasta cerrar esto**: un inventario que dice 35 clientes cuando
hay 43 no es un mapa, es un mapa equivocado.

## 12. La estructura real del backup — verificada (12-08-2026, tarde)

Todos los intentos de identificar al cliente por el contenido fallaban porque **la
identidad estaba en el nombre del fichero y nadie lo había leído entero**. El patrón real
no es `SP_C_04` sino `SP_C_04A`: hay una **letra final** que se estaba ignorando.

```
AA_A_##A   →  SP_C_04A, SP_C_04B, SP_C_04C
              prefijo · CÓDIGO DE EMPRESA · parte
```

- El **número** es el código de empresa dentro de esa copia.
- La **letra final** es la parte del backup de esa misma empresa.

**Consecuencia:** dentro de una carpeta de copia, contar códigos distintos da el número
exacto de empresas. Sin huellas, sin umbrales, sin inferencia.

### Auditoría independiente — 5 de 5 en verde

| Prueba | Resultado |
|---|---|
| **V6** suma de ficheros por carpeta == total de `.DAT` | ✅ 3.857 = 3.857 |
| **V1** códigos de empresa == contenedores con `Diario.dbf` | ✅ **1.287 = 1.287** |
| **V2** cada código tiene exactamente un fichero con datos | ✅ reparto `{1: 1287}` |
| **V3** todos los ficheros vacíos pesan lo mismo | ✅ `[1384]` |
| **V4** la copia de 2026 tiene 33 empresas | ✅ `{2026: 33}` |

> **Cada copia de empresa son 3 ficheros `.DAT`: uno con datos y dos plantillas vacías de
> 1.384 bytes exactos.** Eso explica los 2.570 "contenedores misteriosos": no eran
> contenedores, eran las dos plantillas de cada copia. `3.857 = 1.287 × 3`.

### El número que cierra el bloqueante

```
COPIAS CONTABILIDADES 2025 COMPLETO    →  ejercicios {2025: 33, ...}
COPIA CONTABILIDADES 2026 HASTA 20-07  →  ejercicios {2026: 33}
```

**33 empresas con ejercicio 2025 y 33 con ejercicio 2026**, confirmado en dos carpetas
independientes. Coincide exactamente con lo declarado por el titular: **14 S.L. + 19
autónomos = 33**.

> **Las copias de seguridad están completas. No falta ningún cliente.** El déficit que
> mostraba el mapa (23–24 en vez de 33) era un artefacto del agrupamiento por huella.

*(Las 38 empresas de "2025 COMPLETO" son esas 33 más cinco rezagadas de otros ejercicios
—2011, 2022, 2023, 2024, 2026, una de cada— que quedaron abiertas.)*

### Vías descartadas por el camino, con su medición

| Hipótesis | Resultado |
|---|---|
| Comentario del ZIP lleva la empresa | **0 de 400** contenedores tienen comentario |
| Las rutas internas del ZIP llevan carpeta de empresa | **0 entradas** con directorio (5.704 sin él) |
| Huella por nombre mejor que por NIF | **Peor**: 24 clientes vs 23, y el grupo mayor sube a 180 con umbral 0,30 |
| Umbral elegido por restricción "una empresa por carpeta y ejercicio" | **La restricción era falsa** (nunca baja de 51 violaciones): varias partes del mismo backup comparten código |

### Lo que queda para cerrar la Fase 0

Enlazar el **código 04 de una carpeta** con el **código 12 de otra** (el mismo cliente en
copias distintas). Ahora es un problema acotado, y con una regla dura verdadera que antes
no existía:

> **Dentro de una misma carpeta, dos códigos distintos son dos empresas distintas.
> Nunca se pueden fusionar.**

Metida esa restricción en el agrupamiento, la huella puede enlazar entre carpetas pero no
pegar clientes dentro de una.

## 13. Cobertura real del corpus — la respuesta definitiva (12-08-2026)

Medida con el método verificado del §12 (dentro de una carpeta, el número del nombre es
el código de empresa). La cota inferior por ejercicio es el número de empresas de la
carpeta más completa que contenga ese año: no depende del enlace entre carpetas, que
sigue pendiente.

| Ejercicio | Clientes (mínimo) | Copias | Carpetas | Estado |
|---|---|---|---|---|
| 2016 | — | — | — | ❌ **No existe en `.DAT`** |
| 2017 | — | — | — | ❌ **No existe en `.DAT`** |
| 2018 | **1** | 3 | 3 | ❌ Prácticamente inexistente |
| 2019 | 32 | 95 | 3 | ✅ |
| 2020 | 34 | 246 | 13 | ✅ |
| 2021 | 37 | 372 | 12 | ✅ |
| 2022 | 30 | 216 | 14 | ⚠️ ¿bajas o falta? |
| 2023 | 29 | 89 | 6 | ⚠️ ¿bajas o falta? |
| 2024 | 31 | 116 | 6 | ✅ |
| 2025 | **33** | 91 | 4 | ✅ |
| 2026 | **33** | 34 | 2 | ✅ |
| 2011 | 1 | 16 | 16 | Anomalía suelta |

> **Corrige de nuevo la premisa: el corpus detallado empieza en 2019, no en 2018.** El
> ejercicio 2018 tiene una sola empresa. (Antes se dijo 2018–2026; antes de eso,
> 2016–2026. Este es el número medido con el método correcto.)

**Causa del hueco 2016–2018, confirmada por el titular:** de esos años solo existen las
contabilidades enviadas al Registro. Una copia de ContaPlus solo guarda las empresas
abiertas en ese momento, y la carpeta de copia más antigua se hizo en 2019/2020: los
ejercicios anteriores ya estaban cerrados y nunca entraron en una copia.

**Esto NO bloquea el proyecto.** Para poblar la memoria, calibrar el semáforo y medir
falsos verdes bastan de sobra los 101.122 asientos de 2019–2026. Y para 2016–2018 las
cuentas depositadas **son** el registro oficial: falta el detalle diario, no la verdad
contable de esos ejercicios.

### Ficheros del árbol que siguen sin clasificar

| Extensión | n | MB |
|---|---|---|
| `.cat` | 28 | 8,89 |
| `.wma` | 5 | 26,13 |
| `.xlsx` | 9 | 1,05 |
| `.txt` | 28 | 0,07 |
| `.jpg` | 4 | 0,02 |
| `.ini` / `.json` / `.py` | 4 | ~0 |

Más **9 contenedores sin ejercicio detectable** (diario vacío o con fechas fuera de rango).

**Criterio acordado para decidir qué merece pulirse:** *¿lo consume el motor?* El mapa
cliente-año sí (decide qué se usa para entrenar y qué para validar). Los `.wma` y `.jpg`
no. Los `.cat` están sin determinar y por eso se miran.

---

## 14. El motor sobre el histórico real: retro-semáforo (25-08-2026)

**Qué mide y qué no.** `retro_semaforo.py` reconstruye cada asiento de compra ya
contabilizado y lo pasa por el motor real (`evaluar_fila_v4`). Como esos asientos
**ya se presentaron**, un ROJO aquí es candidato a **falso rojo** (el motor
molestaría con una factura que en su día se dio por buena). **No mide falsos
verdes** — que se contabilizara así demuestra que se hizo así, no que fuera
correcto (ver §1 de `DISENO_APRENDIZAJE.md`). Es la métrica de "¿el motor
molesta?", no la de "¿el motor se fía de más de la cuenta?".

**Base de esta sección**, distinta de la de §6 (que usaba "campos suficientes"
como criterio): 275.566 asientos vistos → 101.122 únicos tras deduplicar copias
de seguridad solapadas → 45.944 con patrón de compra (gasto+IVA+acreedor) → 30.013
evaluados por el motor tras excluir exentas/no-sujetas (452) e inversión del
sujeto pasivo (1.104, ver arreglo 9).

### Progresión de la sesión (25-08-2026), diez arreglos, cero cambios en `motor_veredicto.py`

| # | Arreglo | Dónde | Medido |
|---|---|---|---|
| 1 | Cabecera del `.DAT`: el parser se desplazaba 32 bytes por un byte de relleno no previsto | `retro_semaforo.py` | 1.326 asientos leídos → 275.566 |
| 2 | Deduplicación entre copias de seguridad (cada copia repite el histórico completo) | `retro_semaforo.py` | ROJO 77,36% → dominado por `anti_duplicado` |
| 3 | `nº_documento`: el `or` entre candidatos nunca caía al segundo (`.get()` de esquema, no de dato) | `retro_semaforo.py` | presencia 0,06% → 100% |
| 4 | Base de compras de un solo tipo de IVA: derivarla de cuota/tipo metía ruido de redondeo que no hacía falta | `retro_semaforo.py` | `retencion_vs_error` FALLO 41,9% → 8,0% residual |
| 5 | Deduplicación semántica (misma factura, otra copia, campo técnico distinto) | `retro_semaforo.py` | `anti_duplicado` FALLO 16.383 → 0 |
| 6 | `base_total` generalizado a cualquier número de tipos de IVA (antes solo el caso de 1 tipo) | `retro_semaforo.py` | `cuadre_total` FALLO 6.458 → 4.298 |
| 7 | Reescalado del reparto por tipo para que sume exacto con `base_total` (consecuencia directa del 6, no revisada al hacerlo) | `retro_semaforo.py` | `suma_tramos` FALLO 2.171 → 32 |
| 8 | Cuota por tipo dejó de derivarse de la base reescalada del 7; se suma directa (nunca falta, a diferencia de la base) | `retro_semaforo.py` | `aritmetica_base_tipo` FALLO 983 → 0 |
| 9 | Retención de IRPF (cuenta 475) e inversión del sujeto pasivo (cuenta 477) sin capturar | `retro_semaforo.py` | `cuadre_total` FALLO 2.228 → 805 |
| 10 | `nif_check.py`: NIE validado con el algoritmo de CIF (misma forma, checksum distinto); NIF-IVA extranjero sin rama; campo de 1-2 caracteres tratado como NIF inválido en vez de sin dato | `nif_check.py` | `nif_digito_control` FALLO 513 → 94 |
| 11 | `nif_check.py`: NIF/CIF de longitud 8 (falta solo el dígito de control) tratado como inválido en vez de sin dato suficiente para verificar | `nif_check.py` | `nif_digito_control` FALLO 94 → 60; ROJO 3,15% → 3,03% |

Cada arreglo verificado por separado contra el corpus real antes de darlo por
bueno (nunca solo contra el corpus sintético del ensayo en seco), y los arreglos
6→7→8 son el mismo patrón repetido dos veces: **corregir una fuente sin revisar
qué otro guard consumía la fuente vieja crea un fallo nuevo.** Cazado las dos
veces por auto-revisión antes de pasárselo a Diego, no por él.

### El resultado final de la sesión

| | RUN 4 (tras arreglo 3) | RUN 10 (tras arreglo 10) | RUN 11 (tras arreglo 11) |
|---|---|---|---|
| VERDE | 49,19% | 87,71% | **87,71%** |
| ROJO | 45,97% | 3,15% | **3,03%** |
| AMBAR | 4,84% | 9,15% | 9,26% |
| Tasa de detección (`--inyectar`) | — | 78,99% | 78,99% (100% en 4 de 5 tipos de error; el punto débil declarado es `nif_de_otro`, 0,4% — un NIF ajeno pero con checksum válido no tiene por qué distinguirse sin el patrón de cartera) |

### La predicción de `TECHO_Y_LIMITES.md`, confirmada

Escrito el 20-08-2026, cinco días antes de esta sesión:

> *"Si al desglosar los ROJO por motivo dominan `cuadre_total`, `suma_tramos` y
> `nif_digito_control`, el problema no es el motor: es el modelo de datos
> fiscal."*

Se cumplió exactamente. **Ninguno de los diez arreglos tocó `motor_veredicto.py`.**
Los diez estaban en cómo `retro_semaforo.py` traduce un asiento contable real al
contrato que el motor espera — el mismo síntoma que el documento ya había
reproducido a mano con cinco facturas de laboratorio antes de tener el histórico
delante.

### Lo que queda sin explicar (abierto, no urgente)

- `cuadre_total`/`retencion_vs_error`, ~800 casos (2,7% de los evaluados): ya no
  tiene un patrón dominante tras separar retención e ISP (prefijos de cuenta
  residuales, ninguno por encima del 2%). Puede ser ruido real de captura
  histórica (tecleo) más que un defecto del instrumento.
- `nif_digito_control`, 60 casos tras el arreglo 11 (0,2%): 46 CIF con
  checksum genuinamente incorrecto (verificado contra fuentes externas antes
  de tocar código — sin evidencia de bug, no se cambia nada) + 14 valores
  cortos sin patrón reconocible (longitud 7 y 10, y 2 de longitud 8 que no
  encajaban en ninguna forma). Misma lectura que el resto: parece señal real
  del histórico, no ceguera del instrumento.

  > **Arreglo 12, sesión Cloud 27-08-2026, sobre los "2 de longitud 8 que no
  > encajaban en ninguna forma".** Hipótesis concreta, verificada con
  > aritmética sintética antes de tocar código: `nif_check.py` cubría dos
  > formas de longitud 8 (8 dígitos sin letra; letra+7 dígitos) pero no una
  > tercera — **7 dígitos + letra al final**, la forma exacta de un DNI de 9
  > caracteres al que se le perdió el **cero inicial** al leerlo como número
  > (típico de una hoja de cálculo). A diferencia de las otras dos formas,
  > esta SÍ es verificable del todo: `int('01234567') == int('1234567')`, el
  > cero inicial no cambia `num % 23`, así que la letra de control se calcula
  > exactamente igual que en un DNI completo — no se declara `SIN_DATO`, se
  > verifica de verdad. Implementado y probado con DNI sintéticos (checksum
  > matemáticamente válido, ningún dato real) en `test_motor_veredicto.py`;
  > probado con sabotaje (rama desactivada a propósito) — falla exactamente
  > en las 2 comprobaciones nuevas, ninguna otra. **Pendiente de confirmar
  > contra el residuo real:** la próxima vez que se ejecute
  > `diag_nif_otro_residual.py` en local, el bucket `longitud 8 / otra_mezcla`
  > debería bajar (idealmente a 0, si la hipótesis es correcta) — si no baja,
  > la hipótesis queda refutada y no hay que darla por buena solo porque la
  > aritmética cuadre en sintético.

### 14-bis. El 303 presentado: identidad de cliente corregida, cuadre pendiente

**`reconstruir_303.py` tenía el mismo bug de deduplicación que el primero de
retro-semáforo**, en un script distinto: sin deduplicar entre copias de
seguridad, cada apunte de IVA se contaba una vez por copia en la que
aparecía. Corregido con la misma técnica (huella por registro): apuntes de
IVA agregados 242.617 → **88.932** (153.685 duplicados, 63,3% exacto — la
misma cifra que ya se conocía para el corpus entero, por una vía
totalmente distinta).

**Identidad de cliente: 507 → 24.** `clave_cliente()` usaba carpeta+código,
y el código de una misma empresa cambia entre copias de distintos años —
la carpeta de nivel 1 (una por cliente, confirmado por Diego y verificado
sin ver ningún nombre real: `diag_profundidad_carpetas.py` midió 28
carpetas de nivel 1, cerca de las 33 empresas reales conocidas) es la
identidad fiable. Con el cambio: 24 clientes, 138 trimestres, apuntes de
IVA idénticos antes y después (88.932 = 88.932) — confirma que
deduplicación e identidad de cliente son correcciones independientes.

**Intento de automatizar la lectura de los 303 ya presentados (PDF con
texto seleccionable, en `\\PC01\Documentos`): fase 1 prometedora, fase 2
falló.** `reconocer_303_pdf.py` (solo cuenta patrones, nunca extrae):
1.168 PDF del modelo 303 de 14.386 totales, "Casilla NN" presente en el
98-99% de los documentos. `extraer_303_pdf.py` (extrae el número más
cercano a cada etiqueta y se auto-valida por consistencia interna —
base≥cuota, tipo efectivo legal — sin que ningún valor salga nunca del
script): **1,2% de consistencia**, prácticamente ruido. La proximidad en
texto plano no localiza el valor correcto en un formulario tabular.
Decisión: no seguir invirtiendo en el extractor sin tener antes el número
real (comparación manual de una muestra de trimestres) — construir mejor
tubería alrededor de un objetivo aún no confirmado sería trabajo
prematuro. **Pendiente: la muestra manual, y decidir después si merece la
pena un extractor consciente de tabla/posición.**

### Lo que esta sección NO responde

Sigue sin tocar el **Punto 1** (§ siguiente): la consistencia por par
cliente-tercero. Retro-semáforo mide si el motor **molesta** con el histórico
(falsos rojos) y si **detecta** errores inyectados; no mide si las cuentas
elegidas en su día eran las correctas. Son preguntas independientes.

---

## Actualización del registro de supuestos

| # | Estado anterior | Estado ahora |
|---|---|---|
| **S15** — nº de líneas únicas | ☐ sin medir | ✅ **medido 11-08-2026**: 348.716 líneas / 101.122 asientos |
| **S16** — % con campos suficientes | ☐ supuesto | ✅ **medido 11-08-2026**: 68,26% por asiento |
| **S14** — clave de agrupación `(cliente, tercero)` | ☐ supuesto | ✅ **confirmado insuficiente 11-08-2026**: hace falta el concepto como tercera dimensión (§10.4, caso real aportado) |
| **S18** — Remote Control hereda el volumen | ☐ sin verificar | ✅ **confirmado por fuente oficial**: sí, acceso completo al sistema de ficheros local. Además, Remote Control **no arranca con `ANTHROPIC_API_KEY` puesta** — control estructural, no procedimental |
| **§3.6c p.8** — codificación CP850 | dado por hecho | ❌ **falso**: es cp1252 |
| **§11.2** — OneDrive | ☐ sin comprobar | ✅ **limpio**: Escritorio y Documentos sin redirigir, OneDrive no corriendo, ni Dropbox/Drive/iCloud |
| **Falsos rojos del motor sobre histórico real** | ☐ sin medir | ✅ **medido 25-08-2026** (§14): 3,15% tras diez arreglos, ninguno en `motor_veredicto.py` |

---

## Lo que la Fase 0 todavía NO ha medido

Se ha resuelto el trabajo previo que el plan daba por hecho (formato, esquema,
codificación, volumen) más los puntos 3, 4 y 5. **Queda pendiente el núcleo:**

- [ ] **Punto 1 — la medición que lo decide todo:** para cada par (cliente, tercero)
      con 3+ apariciones, qué fracción fue siempre a la misma cuenta. Sin ponderar y
      ponderada, con la distribución completa. **Es la pregunta central de la Fase 0 y
      sigue sin responder.**
- [ ] **Punto 1b — el contador clave:** de los pares que alternan, cuántos se explican
      al añadir el concepto como tercera dimensión de la clave (supuesto S14).
- [ ] **Punto 6 — rectificaciones:** líneas que cambiaron de cuenta entre copias
      sucesivas. El factor de duplicación de 2,73x dice que hay material para esto.
- [ ] **Punto 7 — ventanas de cambio.**
- [ ] **Prueba real de capa de texto en los PDF.**
- [x] ~~Qué son los 2.570 contenedores que **no** llevan `Diario.dbf`.~~
      **RESUELTO** (verificado 19-08-2026 sobre `fase0_diagnostico.json`, que ya
      lo contenía): son las **plantillas vacías** del backup. Los 2.570 pesan
      1.384 bytes exactos, traen 8 entradas cada uno (`ACCIONES.ASC`,
      `DATOS.ASC`, `CERTIF.ASC`, `FICHERO.TXT`, `GESTION.TXT`…) y **ninguna
      supera los 4 KB descomprimidos: todas a cero**. Concuerda con §12:
      `3.857 = 1.287 × 3` — un fichero con datos y dos plantillas por empresa.

**Nota metodológica pendiente y no trivial:** el propio titular confirma que hay copias
tomadas a mitad de ejercicio y años incompletos. Eso significa que **"quedarse con la
copia más reciente de cada empresa-ejercicio" truncaría datos en silencio**, y que una
cobertura parcial hace que un par parezca menos consistente de lo que es. Hay que
modelarlo antes de calcular el punto 1, o el número saldrá pesimista sin que se note.
