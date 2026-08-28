# PROJECT_STATUS — estado operativo, no documentación

> **Para ARRANCAR una sesión, lee `EMPEZAR_AQUI.md`.** Este fichero es la
> referencia detallada: sirve para consultar, no para empezar.

Este archivo se actualiza cada vez que algo cambia de verdad. Si algo aquí no
coincide con lo que demuestran los tests o el código, mandan los tests, no este
texto. Jerarquía de verdad: Código → Tests → Git → este archivo.

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
