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
- [ ] Qué son los 2.570 contenedores que **no** llevan `Diario.dbf`.

**Nota metodológica pendiente y no trivial:** el propio titular confirma que hay copias
tomadas a mitad de ejercicio y años incompletos. Eso significa que **"quedarse con la
copia más reciente de cada empresa-ejercicio" truncaría datos en silencio**, y que una
cobertura parcial hace que un par parezca menos consistente de lo que es. Hay que
modelarlo antes de calcular el punto 1, o el número saldrá pesimista sin que se note.
