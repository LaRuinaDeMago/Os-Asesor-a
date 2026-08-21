> ## ✅ CERRADO EL 20-08-2026 — §1 ya no describe el estado actual
>
> El modelo de datos fiscal **se ha ampliado** y las facturas que abajo se
> declaran imposibles **ahora pueden llegar a VERDE**. Lo que sigue se conserva
> como registro de cómo era y por qué se cambió, no como estado.
>
> **Lo que ahora sí se representa:**
> `naturaleza_operacion` (SUJETA · EXENTA · NO_SUJETA · INTRACOMUNITARIA ·
> INVERSION_SUJETO_PASIVO), `tramos_iva` con **cualquier** tipo (0, 4, 5, 10, 21)
> y **recargo de equivalencia** (5,2 · 1,4 · 0,62 · 0,5).
>
> Verificado en `test_adversarial.py` familia J: **10 categorías de facturas
> legales que antes eran AMBAR o ROJO permanente ahora dan VERDE**, y las cuatro
> formas de abusar de esa apertura siguen dando ROJO.
>
> **Lo que NO cambia:** declarar una naturaleza no es una puerta trasera. Una
> exenta que repercute IVA es ROJO; una naturaleza inventada es ROJO; un recargo
> que no corresponde a los tramos es ROJO.

# El techo — qué hay por encima de lo que hay hoy

Escrito el 20-08-2026, con el motor en 21/21 de regresión y 25/25 de ataque.
**Nada de aquí es opinión: todo está medido ejecutando el motor.**

Este fichero existe porque "el motor está cerrado" y "el motor está en su techo"
son cosas distintas, y conviene no confundirlas al llegar a la sesión local.

---

## 1. 🔴 El techo duro: hay facturas LEGALES que el motor rechaza

Medido el 20-08-2026 pasando cinco facturas por `evaluar_fila_v4`. **Tres de las
cinco son perfectamente legales y salen ROJO.**

| Caso real | Veredicto | Motivo que da el motor |
|---|---|---|
| Sujeta y no exenta (control) | ✅ VERDE | correcto |
| **Exenta** art. 20 LIVA (médico, seguro, alquiler de vivienda) | 🟠 AMBAR | `NO_COMPROBADO: aritmetica_base_tipo, suma_tramos` |
| **Intracomunitaria** (inversión del sujeto pasivo) | 🔴 **ROJO** | `nif_digito_control: DESCONOCIDO invalido: formato no reconocido` |
| **Tipo 0%** | 🔴 **ROJO** | `suma_tramos: suma tramos=0.0 != base_total=100.0` |
| **Recargo de equivalencia 5,2%** | 🔴 **ROJO** | `cuadre_total: total_calc=121.0 decl=126.2 DESCUADRE` |

**El de recargo de equivalencia no es un caso de laboratorio: es cotidiano en
autónomos de comercio, y 19 de los 33 clientes de la cartera son autónomos.**

### Por qué pasa, causa a causa

- **Recargo de equivalencia:** el modelo de datos no tiene campo para el RE, así
  que `cuadre_total` calcula `base + IVA - IRPF` y le falta el recargo. La
  factura cuadra en la realidad y no cuadra en el motor. *(El diario de ContaPlus
  sí tiene campo `RECEQUIV` — el dato existe, no se está usando.)*
- **Tipo 0%:** con base declarada y ningún tramo, `suma_tramos` compara 0 contra
  la base y canta descuadre. No distingue "no hay tramos porque el tipo es 0" de
  "faltan los tramos".
- **Intracomunitaria:** un NIF con prefijo de país (`DE…`) no pasa el dígito de
  control español, y `nif_digito_control` es **crítico**, así que dispara ROJO.
  Hay un detalle fino aquí: `guard_tipo_operacion_especial` **sí** detecta el
  prefijo extranjero y devuelve AMBAR — pero nunca llega a contar, porque el
  guard más estricto de más arriba ya cerró el veredicto. **Un guard bueno
  anulado por el orden de evaluación.**
- **Exenta:** sale AMBAR, no ROJO. Aceptable —no es un falso rojo— pero significa
  que ninguna factura exenta se automatiza jamás.

### Predicción comprobable para mañana

> Cuando corra `retro_semaforo.py` sobre el histórico real, **una parte de los
> falsos rojos van a ser exactamente estos cuatro casos.** Si al desglosar los
> ROJO por motivo dominan `cuadre_total`, `suma_tramos` y `nif_digito_control`,
> el problema no es el motor: es el modelo de datos fiscal.

Esa predicción es falsable y se comprueba en la misma ejecución. Es la forma
correcta de saber si esto es urgente o marginal **antes** de rediseñar nada.

### El arreglo, cuando toque

De `base_10 / base_4 / base_21` a una lista de tramos con su naturaleza:

```
tramos_iva: [ {tipo: 21, base: 100.00, cuota: 21.00, recargo: 5.20}, … ]
naturaleza: SUJETA | EXENTA | NO_SUJETA | TIPO_CERO | INTRACOMUNITARIA | IMPORTACION
```

Con eso, el motor puede seguir teniendo guards especializados, pero **la
representación deja de impedir que existan casos que el motor debería conocer**.

**Condición previa:** medir primero cuántas facturas reales caen en cada
naturaleza. Rediseñar el modelo de datos por casos que aparecen el 0,1% de las
veces sería el mismo error de los siete casos especiales de la spec v1.4, que
resultaron aparecer **0,00% de las veces en 941.435 líneas**
(`FASE0_RESULTADOS.md` §8). El histórico puede contestar esto.

---

## 2. 🟠 Las tres mejoras bloqueadas por lo mismo: el prompt de captura

| Pieza | Estado hoy | Qué le falta |
|---|---|---|
| **Triangulación de identidad** (`triangulacion_identidad_v0.py`) | Escrita, probada, **desconectada** | El prompt no pide `nif_margen` ni `nombre_margen` |
| **Doble lectura de importes** | Solo diseñada | El prompt no pide el total desde dos ubicaciones |
| **Confianza por campo** | Solo diseñada; el estado `MEDIA` es hoy inalcanzable | El prompt pide un `verificacion` global, no uno por campo |

> **Las tres se desbloquean con UN cambio: el prompt de `captura_orquestador.py`.**
> Ese es el cuello de botella real del siguiente nivel de calidad, no el motor.

**La triangulación está desconectada por dependencia, no por descuido.** Cablearla
hoy produciría un guard permanentemente `NO_APLICA`: peor que la desconexión
honesta, porque *parecería* conectado. El arreglo es aguas arriba.

**No se toca el prompt sin una factura real delante.** Cambiarlo a ciegas
significa que la primera captura de verdad usaría un prompt nunca probado.

---

## 3. Los dos techos, que no son el mismo

Conviene tener clara la distinción, porque decide dónde merece la pena invertir:

**El techo de COMPROBAR CORRECCIÓN — prácticamente alcanzado, y está bien.**
Un motor determinista no puede hacer más que verificar coherencia. La
alternativa —dejar que un modelo decida qué es correcto— es exactamente lo que
este proyecto rechaza, y con razón. Lo que queda por encima aquí es estrecho:
que el modelo de datos represente todos los casos legales (§1) y que la
evidencia sobre los importes sea independiente (§2).

**El techo de CUÁNTO SE AUTOMATIZA — muy por debajo, y ahí está el recorrido.**
Depende de dos cosas y ninguna es el motor:
1. La calidad de la captura (cuántas facturas se leen bien).
2. Cuánto del histórico llega de verdad a informar la decisión.

De la segunda hay una parte ya hecha ayer —`guard_cuenta_gasto_coherente` está
cableado— pero **recibe `{}` salvo que el orquestador cargue un diario real**.
La tubería existe; por dentro no ha pasado agua todavía.

---

## 4. Lo que NO hay que hacer con esta lista

- **No rediseñar el modelo fiscal mañana.** Primero el retro-semáforo dice si
  estos casos son el 1% o el 20% de la cartera.
- **No tocar el prompt sin facturas reales.**
- **No cablear la triangulación** hasta que el prompt emita sus entradas.
- **No añadir guards nuevos** por ninguno de estos casos (`CLAUDE.md`): lo que
  falta es representación, no vigilancia.

---

## 5. Orden propuesto, cuando llegue el momento

1. **Medir** (retro-semáforo): ¿qué fracción de los ROJO son estos cuatro casos?
2. Si es alta → **modelo de datos fiscal** (§1). Es lo que más automatización
   desbloquea de golpe, y sin tocar el prompt ni la captura.
3. **Una factura real** de punta a punta, con el DPA ya contratado.
4. Con esa factura delante → **el prompt** (§2), y las tres mejoras a la vez.
5. Conectar el histórico real al orquestador (`--diario`) para que
   `guard_cuenta_gasto_coherente` e `importe_atipico` dejen de recibir `{}`.

---

## 🎯 QUÉ SIGNIFICA UN VERDE — el techo real, y no es el que parecía

Escrito el 20-08-2026, y es la sección más importante de este documento.

Durante semanas el proyecto ha dado por hecho que el riesgo estaba en la captura:
el 5 confundido con un 8, la foto borrosa, el OCR que se equivoca. **Eso está
medido y resuelto:** de 99 mutaciones de un dígito en los euros de un importe,
el motor caza las 99 (`prueba_digito_ocr.py`). El NIF, también al 100%, por su
dígito de control. La redundancia aritmética de una factura —`base × tipo =
cuota`, `base + cuota = total`— la convierte, sin habérselo buscado, en un código
detector de errores.

**Pero hay una categoría entera de error que ningún guard puede ver, y no tiene
nada que ver con la captura.**

> **Una factura puede estar capturada PERFECTAMENTE y la contabilidad estar mal.**

El motor comprueba que la factura es **coherente consigo misma** y que está bien
**identificada**. No comprueba —no puede— nada de esto:

| Pregunta | ¿La ve el motor? |
|---|---|
| ¿Cuadra la aritmética? | ✅ sí |
| ¿El NIF es válido y del proveedor que dice? | ✅ sí |
| ¿Está duplicada? | ✅ sí |
| ¿Las fechas son válidas y del ejercicio? | ✅ sí |
| **¿Este gasto es deducible?** | ❌ **no** |
| **¿Va a la cuenta contable correcta?** | ❌ **no** |
| **¿El IVA es deducible al 100%, al 50% o al 0%?** (vehículos, restauración) | ❌ **no** |
| **¿Corresponde a este ejercicio por devengo?** | ❌ **no** |
| **¿Es un gasto de la empresa o personal?** | ❌ **no** |

Una comida personal cargada a la empresa, fotografiada con nitidez y
aritméticamente impecable, **sale VERDE**. Y hace bien: la factura es correcta.
Lo que está mal es la decisión de contabilizarla.

### La consecuencia práctica

**Ahí es donde viven los falsos verdes de verdad. No en el OCR.**

Por eso el veredicto ahora lo dice de su propia boca:

```
VERDE: coherencia formal verificada (aritmética, identidad, fechas, duplicados,
       régimen de IVA); NO comprueba deducibilidad ni cuenta contable
```

No es prudencia ni letra pequeña: es lo que evita la **sobreconfianza**, que es
el mecanismo real por el que un sistema así hace daño. Un asesor que lee "VERDE"
y entiende "esto está bien contabilizado" deja de mirar, y ahí empieza el
problema.

### Y hacia dónde sí queda recorrido

Las únicas dos piezas que empiezan a asomarse a la decisión contable —no a la
forma— ya existen y son las más diferenciales del proyecto:

- **`guard_cuenta_gasto_coherente`**: ¿a qué cuenta suele ir este proveedor según
  los diez años de histórico? Cableado, pero recibiendo `{}` hasta que el
  orquestador apunte a los `.DAT` reales.
- **`guard_tipo_operacion_especial`**: detecta por estructura que esto no es una
  compra normal (inmovilizado, intracomunitaria, amortización) y frena a ÁMBAR.

> **El techo de "comprobar la forma" está tocado. El techo de "acertar la
> decisión contable" está mucho más abajo, y el camino hacia él es el histórico
> conectado al motor, no más guards aritméticos.**
