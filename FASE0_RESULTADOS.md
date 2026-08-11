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

---

## Actualización del registro de supuestos

| # | Estado anterior | Estado ahora |
|---|---|---|
| **S15** — nº de líneas únicas | ☐ sin medir | ✅ **medido 11-08-2026**: 348.716 líneas / 101.122 asientos |
| **S16** — % con campos suficientes | ☐ supuesto | ✅ **medido 11-08-2026**: 68,26% por asiento |
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
