# Diseño del aprendizaje — cómo el sistema aprende sin sustituir el criterio

Decisiones de diseño del 19-08-2026. Ninguna está construida todavía salvo lo que
se indica como ya existente. No manda sobre las mediciones (jerarquía Código →
Tests → Git → documentos).

---

## 1. Por qué esto importa más de lo que parece

El histórico de diez años dice **lo que se contabilizó**. No dice **lo que era
correcto**. Son cosas distintas.

Y todo el proyecto depende de la segunda: medir falsos verdes exige etiquetas
—"esto estaba bien", "esto estaba mal"— y **no hay ninguna otra fuente de esas
etiquetas que un profesional diciéndolo**.

Estado actual: 101.122 asientos sin etiquetar, **cero ejemplos etiquetados**.

> **Cada corrección del asesor es un ejemplo etiquetado y verificado. El sistema
> de correcciones no es una comodidad para no editar a mano: es la fábrica de
> etiquetas que hace medible la métrica que decide el proyecto.**

Consecuencia práctica: cada corrección hecha a mano hoy, sin registrar, es una
etiqueta que se pierde para siempre. Por eso esta pieza es **instrumento de
medición**, no funcionalidad de producto, y va antes de lo que su aspecto sugiere
— no detrás de la puerta 3 de `ARQUITECTURA_DATOS.md`, sino junto al corte
vertical, que es lo que hay que poder medir.

---

## 2. Lo que YA existe (y funciona)

`motor_veredicto.py :: aprender_cuenta_gasto()` implementa ya el ciclo básico, y
mejor de lo que suele recordarse:

- Distingue `CONFIRMADA_ASESOR` de `ALTA` — es decir, separa **lo que decidió una
  persona** de **lo que dedujo el sistema** por mayoría histórica. Esa distinción
  de procedencia es la pieza difícil y está hecha.
- Registra `revisado_por` y `fecha_revision` (añadido el 28-07-2026 por el hueco
  de auditoría RGPD).
- Persiste a disco, así que sobrevive a la sesión.

El ciclo `NO_APLICA → decisión del asesor → persistencia` está cubierto por
`test_motor_veredicto.py` y pasa.

---

## 3. Los tres huecos que tiene — el segundo es un bug

### 3.1 Guarda el QUÉ, no el PORQUÉ

`{'cuenta_gasto': '629000', 'confianza': 'CONFIRMADA_ASESOR', ...}` registra la
decisión, no su motivo.

- *"Cambié a 629"* → una entrada de log.
- *"Cambié a 629 porque este proveedor factura dos cosas distintas y esta línea es
  la de mantenimiento"* → una regla que generaliza a casos nuevos.

**Decisión inicial, CORREGIDA el 19-08-2026:** primero se escribió aquí que el
motivo sería *campo obligatorio* en cada corrección. **Estaba mal**, y la objeción
que lo tumba es correcta: pedir una justificación en cada corrección es fricción
que garantiza que no se haga. Un asesor saturado no escribe el porqué de 12
correcciones al día, y un sistema que depende de eso no recoge nada.

> *"Un verdadero mentor observa, no pregunta."*

**Decisión corregida — el motivo se pide poco y donde paga:**

- La **corrección en sí** se captura siempre y de forma **pasiva** (§8), sin pedir
  nada al asesor.
- El **motivo** se pregunta solo cuando el **mismo guard** se ha corregido **3 o
  más veces** en poco tiempo. Entonces la pregunta no explica un caso: explica un
  **patrón**, y una sola respuesta cubre las N correcciones anteriores.
- Sin motivo, la corrección sigue siendo válida como etiqueta (dice *qué* era
  correcto). Simplemente no genera regla.

Así se conserva lo que hacía falta del porqué sin la fricción que lo mataba.

### 3.2 Sobrescribe sin historia — bug real

```python
mapeo_cuenta_gasto[cuenta_proveedor] = { ... }   # machaca lo anterior
```

Una corrección equivocada **reemplaza en silencio** a una correcta, y el valor
anterior desaparece. No hay versiones ni forma de saber que hubo un cambio.

Con lo documentado en `FASE0_RESULTADOS.md` §10.3 —el cuadro de cuentas se
arrastra de un ejercicio al siguiente— ese es exactamente el mecanismo por el que
un error se vuelve permanente **y además invisible**.

**Decisión:** el mapeo pasa a guardar una **lista de versiones** por clave, no un
valor. La vigente es la última no revocada. Las anteriores se conservan siempre.

### 3.3 No se puede revocar

Si una corrección resulta estar mal, hoy solo se puede sobrescribir, y el rastro
del error se pierde. Pero **el rastro de los errores es justo lo que hay que
medir**: sin él no se puede saber cuántas veces el asesor se equivocó al corregir,
que es un número tan importante como el de falsos verdes del motor.

**Decisión:** revocar es una operación explícita que marca la versión como
`REVOCADA`, con motivo y fecha, y nunca borra.

---

## 4. Nivel 1 y nivel 2 — dónde está la línea y cómo se sostiene

**Nivel 1:** el sistema señala que algo no cuadra y pide criterio. Es el AMBAR
actual.

**Nivel 2:** el sistema razona **con** el asesor: *"esto en el pasado fue así por
esto y por esto, encaja con aquello, ¿tú qué ves?"*.

La distinción entre razonar-con y recomendar es **real**: presentar evidencia y
dejar que concluya la persona preserva el juicio; proponer la respuesta lo
sustituye. Pero es **frágil** y se desliza sola. Tres salvaguardas concretas, que
son requisitos de construcción, no principios:

### 4.1 El sistema nunca rellena la casilla

Puede mostrar todo lo que sabe. **No puede preseleccionar, prerrellenar ni ordenar
por probabilidad.** En cuanto hay un desplegable con su apuesta ya puesta, el
juicio profesional se acabó, se llame como se llame la funcionalidad.

### 4.2 La evidencia corta en las dos direcciones

> *"18 de tus 20 clientes usan la 621"* — recomendación disfrazada de dato.
>
> *"18 de 20 usan la 621; este cliente usó la 629 dos veces, las dos en el cuarto
> trimestre"* — material para pensar.

Si solo se muestra la evidencia que apoya la respuesta más probable, se ha
construido el nivel 2 sin querer. **Mostrar la evidencia que contradice es
obligatorio, no cortesía.**

### 4.3 El sesgo de automatización se mide, no se confía en evitarlo

Se registra la **tasa de coincidencia** entre la decisión del asesor y lo que
apuntaba el patrón agregado.

> Si esa tasa se acerca al 100%, el asesor ha dejado de razonar y **el dato lo
> dice**. El sesgo deja de ser un riesgo que se espera evitar y pasa a ser un
> número que se vigila.

Es casi gratis de implementar y es la salvaguarda más fuerte de las tres, porque
las otras dos dependen de que el diseño se respete y esta lo detecta cuando no.

---

## 5. El patrón agregado entre clientes

Señal disponible y hoy sin usar: un proveedor que va a la misma cuenta en **20
clientes distintos** es evidencia fuerte; uno que solo aparece en un cliente, y
encima arrastrado de ejercicios anteriores, es evidencia débil.

Ataca directamente la debilidad documentada en §10.3: el histórico individual
puede estar viciado por el arrastre; el agregado entre clientes, mucho menos.

**Aclaración necesaria sobre la línea roja** de `.claude/rules/datos.md` ("uso
secundario de los datos de cliente"), para que no bloquee esto por error:

> Cruzar datos **entre tus clientes para servir a esos mismos clientes** es tu
> propia experiencia profesional sistematizada, y es legítimo. Lo descartado es
> vender o ceder lo derivado a **terceros**.
>
> La diferencia no está en el cruce de datos. Está en **quién se beneficia**.

---

## 9. Escepticismo estructural — que el sistema no aprenda tus errores

El riesgo más silencioso del proyecto: si el sistema aprende de las decisiones del
asesor, **aprende también sus sesgos**, y los aplica diez mil veces. Un criterio
equivocado sostenido durante años deja de parecer un error y pasa a parecer *la
forma en que se hacen las cosas aquí*.

La respuesta correcta no es hacer el sistema más listo. Es hacerlo **más
desconfiado** — de la máquina y del asesor por igual. Cuatro capas, adoptadas con
un matiz en la última:

### 9.1 Grounding asimétrico — el histórico clasifica, la norma decide

> El histórico puede decir **qué se hizo**. Solo la norma puede decir **qué es
> correcto**.

- Las correcciones del asesor son **etiquetas y evidencia**, nunca cambian una
  regla por sí solas.
- Una regla del motor solo se modifica contra **fuente externa** (BOE, LIVA,
  LIRPF, consultas vinculantes de la DGT).
- Si una corrección **contradice** la fuente, el sistema no la absorbe: avisa.
  *"Has corregido esto, pero la norma dice X."*

Es la misma invariante que ya está en `ARQUITECTURA_DATOS.md` §2 (la validación va
de fuera hacia dentro), aplicada al aprendizaje.

### 9.2 Detector de disonancia — cuando te desvías de ti mismo

Cálculo de desviación estándar, sin IA: si un criterio se aplica en un cliente y
en ningún otro de la cartera con el mismo perfil, se señala. No dice que esté mal;
pide una segunda mirada.

### 9.3 ⭐ Caducidad de reglas — la mejor idea de todo el bloque

**Toda regla aprendida caduca a los 12 meses.** Al caducar no se borra: su estado
pasa de `OK` a `NO_COMPROBADO — regla caducada, revisar`.

Por qué es tan buena, y por qué encaja exactamente aquí:

- Cuesta **un campo de fecha**. Es la relación coste/impacto más alta de todo lo
  que se ha propuesto en esta sesión.
- Ataca de frente el mecanismo documentado en `FASE0_RESULTADOS.md` §10.3 —el
  arrastre del cuadro de cuentas de un ejercicio al siguiente— que es justo cómo
  un error se vuelve permanente.
- Y es la pareja natural del versionado de §3.2: el versionado conserva el
  historial de un cambio; la caducidad **fuerza a que haya una revisión**.
- Fricción real: revisar unas pocas reglas al año.

> Una regla que nadie ha vuelto a mirar en un año no es conocimiento consolidado.
> Es una suposición con antigüedad.

### 9.4 Casos adversariales — adoptado, pero NO en el flujo real

La cuarta capa propone inyectar facturas sintéticas en el trabajo diario para
probar los sesgos del asesor. La técnica es correcta (exposición forzada a
contraejemplos), pero **la implementación propuesta es peligrosa aquí**: este
sistema produce asientos contables. Una factura falsa suelta en el flujo real
puede acabar contabilizada, y el daño de eso supera al beneficio del ejercicio.

**Adoptado con cambio:** los casos adversariales viven en un **modo de
entrenamiento separado**, marcados de forma inequívoca, que **nunca** escribe en
la contabilidad real. Jamás se mezclan con facturas de clientes.

### 9.5 Vigilancia normativa — la bomba de relojería

Un guard codifica una regla fiscal del momento en que se escribió. Cuando la norma
cambia, el guard **sigue diciendo OK y ahora está mal**, en silencio. No hay
ninguna señal interna que lo delate: los tests siguen verdes, porque los tests
codifican la misma regla vieja.

**Requisito de mantenimiento, no funcionalidad:** cada guard con base normativa
declara **qué norma aplica y de qué fecha**. Sin eso, el proyecto acumula deuda
fiscal invisible.

### ⚠️ Corrección técnica a la "confianza 0–1 por campo"

Se propone que la IA devuelva un valor de confianza numérico por campo y rechazar
por debajo de 0,95. **La idea de confianza por campo es buena (§4 y §10). El
número no.**

Un valor de confianza que devuelve un modelo de lenguaje **no es una probabilidad
calibrada**: es más texto generado. Un `0.97` no significa que acierte 97 de cada
100 veces; significa que el modelo ha escrito "0.97".

Y contradice algo que este proyecto ya tiene medido: `verificacion=OK` es una
afirmación del propio modelo, no evidencia independiente — por eso existe
`triangulacion_identidad_v0.py`. Un umbral de 0,95 sobre un número no calibrado
es la misma fe, con más decimales.

**La confianza real se construye con evidencia independiente:** checksum, cruce
con el histórico, coherencia documental, y medidas deterministas de la imagen
(§7). El dato que dé el modelo entra como **una señal más**, nunca como el umbral.

---

## 6. El techo: no se persigue el cero

Ningún guard puede detectar un error que no deja **ninguna huella estadística ni
estructural**: proveedor conocido, concepto que ya facturó otras veces, importe en
rango normal, y mal clasificado por una razón que solo conoce quien conoce el
negocio del cliente. Ese error es indistinguible de un acierto usando solo datos.
No es un fallo del sistema: es el límite de lo que la información permite inferir.

**Diseño maduro, entonces:**

- No perseguir el cero con más ingeniería.
- Reducir el volumen de casos en la zona ciega hasta que sea pequeño **y quede
  circunscrito a un patrón identificable**.
- Y entonces tratar ese patrón como **zona de revisión humana permanente**, no
  como bug pendiente de arreglar.

El P4 con test adversarial no solo dirá cuántos falsos verdes hay: dirá **de qué
tipo son**. Si los que quedan son todos "sin huella", ese es el techo real.

---

## 8. Telemetría pasiva — cómo se captura sin fricción

La mecánica que hace posible todo lo anterior, y no cuesta ni un clic extra:

1. El motor emite su veredicto y se guarda en **`veredicto_maquina`**.
2. El asesor revisa y emite el suyo — **cosa que ya hace hoy, porque el
   responsable legal es él**. Se guarda en **`veredicto_humano`**.
3. Un proceso posterior calcula el **delta** entre ambos.

El asesor no hace nada nuevo. El sistema escucha.

### Corrección importante: se registra TODO, también los aciertos

La propuesta original decía guardar solo las discrepancias, *"por ahorro de
espacio"*. **Eso hay que rechazarlo**, y por dos motivos que no son de estilo:

- **Sin los aciertos no hay tasa de acierto.** Se pierde el denominador, que es
  justo el número que decide el proyecto.
- **Se destruye la medición del sesgo de automatización** (§4.3). La señal de que
  el asesor ha dejado de razonar es que la tasa de coincidencia sube al 100%, y
  eso solo se ve si se registran las coincidencias.

El coste real del "ahorro": unos cientos de bytes por factura. A 50.000 facturas
al año son unos pocos MB. **Es una falsa economía que cuesta la métrica central.**

### Dos salidas, ninguna intrusiva

**A — Aviso justo a tiempo, no bloqueante.** Cuando un mismo guard acumula 3+
correcciones en poco tiempo, la siguiente factura de ese tipo muestra un aviso de
una línea. No interrumpe, no obliga, no propone la respuesta (§4.1).

**B — Resumen semanal de tres líneas, no un cuadro de mando.** Texto plano:

```
Esta semana: 12 correcciones sobre 150 facturas (92% de coincidencia).
  7 en VENTA   (guard dominante: base imponible)
  3 en COMPRA  (guard dominante: fecha de devengo)
```

Un cuadro de mando se mira una vez al mes y no cambia nada. Diez líneas los
viernes, sí.

### Por qué esto es exactamente el bucle B

Esto es lo que convierte el sistema en las dos cosas a la vez:

```
El sistema aprende  ->  las correcciones son etiquetas (§1)
El asesor aprende   ->  el delta le enseña dónde está corrigiendo siempre lo mismo
```

Y responde a la pregunta que de verdad importa dentro de cinco años, que no es
*"¿cuánto hemos automatizado?"* sino **"¿cuánto más sabe esta asesoría que hace
cinco años?"**.

### Deriva de esquema — riesgo real, acotado con lo ya medido

Los formatos de exportación de bancos y aplicaciones cambian cada 6–12 meses, y
un motor que no lo detecta muere en silencio. Es una objeción válida, con un
matiz medido: **para ContaPlus el esquema lleva diez años estable** —91 campos,
un solo esquema en las 1.287 copias de 2016 a 2026 (`FASE0_RESULTADOS.md` §3)—.
Así que el riesgo es bajo en la fuente principal y alto en las auxiliares.

**Regla:** toda entrada lleva una huella de su esquema, y un cambio de huella
**para el proceso con un aviso**, nunca lo deja pasar adaptándose solo. Es la
misma regla que el escáner de privacidad aprendió por las malas: *no comprobado
no es OK*.

---

## 7. Filtro de calidad de imagen — el hueco de la cadena de captura

La cadena es: captura → **(hueco)** → lectura del modelo → triangulación → guards
→ semáforo.

La triangulación de identidad y `guard_confianza_captura` actúan sobre **lo que
devuelve el modelo**. Ninguno mide **la imagen de entrada**: dependen de que el
modelo declare honestamente su propia incertidumbre. Falta la única capa que actúa
antes, de forma determinista y sin depender del modelo.

**Lo que falta es menos de lo que parece.** Comprobado en el código: como
`guard_confianza_captura` devuelve `BAJA` para cualquier valor de `verificacion`
distinto de `OK` y `OK_INFERIDO`, un `CALIDAD_BAJA` **ya baja la confianza
correctamente sin tocar el guard**. La tercera categoría ya funciona.

Solo falta la pieza de arriba: un filtro técnico **antes** de llamar a la API
—resolución mínima y, opcionalmente, una medida barata de nitidez— que marque la
imagen como `CALIDAD_BAJA` sin gastar una llamada.

**Condición para construirlo** (`CLAUDE.md`: ningún guard nuevo sin caso real que
lo pida): no se construye hasta que haya una factura real que se haya leído mal
por calidad de imagen. Hoy no existe ese caso porque no se ha capturado ninguna
factura real todavía.

### 7.1 Los dos tipos de error de captura, que no se defienden igual

**Error incoherente.** El modelo lee 125,40 como 12.540, o se come un dígito. La
aritmética deja de cuadrar y los guards lo cazan. **Esto está bien cubierto**, y
es el grueso de los errores de lectura.

**Error internamente coherente.** El modelo lee la factura entera de forma
consistente pero equivocada: un ticket con dos totales y coge el que no es, una
factura de dos páginas y lee la segunda, confunde vencimiento con expedición, o
un NIF mal leído que da checksum válido *y* resulta ser el de otro proveedor real.
**Aquí la aritmética cuadra perfectamente y ningún guard aritmético tiene nada que
decir.** Es donde viven los falsos verdes de captura.

Y hay una asimetría estructural que conviene ver:

> Contra el error coherente, la única defensa es **evidencia independiente**: otra
> fuente que diga lo mismo. Lo que el propio modelo declare sobre su confianza
> (`verificacion: OK/DUDA`) **no es evidencia independiente** — es su opinión
> sobre sí mismo.

### 7.2 La doble lectura YA EXISTE — para la identidad

`triangulacion_identidad_v0.py :: triangula()` recibe **`nif_cabecera` y
`nif_margen`** y exige que coincidan. Eso ya es doble lectura, y en la versión
buena: **dos sitios del mismo papel, no dos llamadas al modelo**. Sale gratis
—una petición, dos campos— y una discrepancia salta a ALERTA sin que el modelo
tenga que declarar ninguna duda.

Cruza cuatro fuentes: NIF de cabecera (checksum), NIF de margen (coincidencia),
tabla del cliente (histórico) y similitud del nombre. Es un diseño correcto.

### 7.3 Lo que falta: el mismo principio, aplicado a los importes

La identidad tiene evidencia independiente. **Los importes no.** Su única defensa
hoy es la coherencia aritmética interna, que por definición no ve el error
coherente.

**Extensión propuesta, misma técnica:** pedir el total desde **dos ubicaciones**
del documento —la línea de total y el "total a pagar" / casilla de pago, que en la
mayoría de facturas y tickets aparecen por separado— y exigir que coincidan.
Discrepancia → AMBAR. Sin llamada extra, sin autodeclaración.

Redes aguas abajo que ya están previstas y ayudan, pero llegan más tarde:
`guard_importe_atipico` contra el histórico del proveedor, y el cuadre trimestral
contra el 303 presentado.

**No se construye hasta tener el DPA y facturas reales delante.** Sin poder
probarlo contra papel de verdad sería otra pieza levantada sobre suposiciones —
y no se sabe todavía en qué fracción de las facturas reales el total aparece
efectivamente dos veces. Eso es lo primero que hay que medir cuando se llegue.
