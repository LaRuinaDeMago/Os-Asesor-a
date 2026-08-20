# Arquitectura de datos — la espina dorsal

Decisiones tomadas el 19-08-2026. Gobiernan **qué se construye y en qué orden**,
no cómo se implementa. Si algo de aquí choca con una medición, manda la medición
(jerarquía: Código → Tests → Git → documentos).

Este fichero existe porque el objetivo real del proyecto es más grande que el
motor de facturas: aprovechar los diez años de información del despacho como un
todo conectado. Sin una regla de montaje escrita, eso degenera en un pantano.

---

## 1. Una sola espina: `(cliente, periodo)`

Todo lo que el despacho tiene se engancha a dos ejes y solo dos: **qué cliente**
y **qué periodo**. Sobre esa espina cuelgan conjuntos de datos independientes:

| Conjunto | Qué contesta | Naturaleza |
|---|---|---|
| **Contabilidad** (`.DAT`) | Qué se registró | Interna |
| **Modelos presentados** (036, 303, 130, 111, 115, 390) | Qué se declaró ante Hacienda | **Externa** |
| **Altas y bajas** | Desde cuándo y hasta cuándo existe la relación | Externa |

Tres reglas de montaje, y son las que evitan el pantano:

1. **Cada conjunto sirve por sí solo.** Si solo se construye el inventario de
   contabilidad, ya vale para algo. Ninguno espera a los demás.
2. **Ninguno se diseña entero por adelantado.** Se añaden de uno en uno.
3. **El índice de cliente es estable y anónimo desde el primer día.** Es lo único
   que hay que acertar a la primera: si cambia después, hay que reenganchar todo
   lo demás. Nombre y NIF viven solo en los ficheros `_LOCAL`.

Cualquier motor que se construya después —contable, fiscal, el que sea— lee de
esta misma espina. Por eso el trabajo de ordenación no es de usar y tirar.

---

## 1-bis. Cómo se enganchan los modelos a los clientes SIN romper la frontera

Escrito el 20-08-2026. Es la pregunta operativa que faltaba: si los modelos
(303, 130, 111, 115, 036) tienen que cruzarse con la contabilidad, y ese cruce
necesita saber de quién es cada cosa, ¿cómo se hace sin que la identidad viaje?

**Respuesta corta: exactamente igual que la Fase 0. El cruce lo hace un script en
la máquina de Diego; a Claude le vuelven porcentajes.** No hace falta ninguna
arquitectura nueva. Pero sí tres piezas concretas que hoy no existen.

### El índice: un solo fichero donde identidad e índice se tocan

```
indice_clientes_LOCAL.json     { "<NIF>": "C07", ... }     ← NUNCA sale del disco
```

**Todo lo demás usa `C07` y nada más.** El inventario, los modelos, las altas y
bajas, los deltas de corrección: todos hablan de `C07`. La correspondencia
`C07 → NIF real` vive en ese único fichero y Claude no lo abre jamás.

> ⚠️ **Hoy ese índice NO existe todavía.** El que se usa sale de
> `fase0_huella_LOCAL.json`, y esa agrupación **está invalidada** (fusionaba
> clientes, ver `FASE0_RESULTADOS.md` §11.0). El inventario de mañana tiene que
> emitirlo con el método bueno —el código de empresa del nombre del fichero— y
> emitirlo **pensado para durar**, no como subproducto.
>
> Si el inventario produce un índice de usar y tirar, los modelos no se pueden
> enganchar y hay que rehacer las dos cosas. Es lo único de todo el diseño que
> hay que acertar a la primera.

### El flujo de los modelos, paso a paso

```
Ficheros de modelos (PDF/AEAT)
        │  script en la maquina de Diego
        ▼
   extrae: NIF, modelo, ejercicio, periodo, fecha presentacion, resultado
        │
        ├──► modelos_LOCAL.csv      con el NIF real. Se queda. Claude no lo abre
        └──► modelos_agregado.json  recuentos por ano y tipo. Ese si sube
```

El cruce con la contabilidad —obligaciones del 036 → presentaciones esperadas →
lo que hay archivado → **huecos**— se calcula en local. Lo que vuelve a Claude es
*"cobertura del 94%, 12 huecos, concentrados en 2022"*. Nunca la lista.

### Dos riesgos NUEVOS que el corpus de contabilidad no tenía

**1. Los modelos son PDF, no dBase.** Un `.DAT` se lee campo a campo con un script
y sin modelo de por medio. Un PDF solo si **tiene capa de texto**. Si están
escaneados haría falta OCR, y un OCR en la nube **sí hace viajar el dato** — eso
cae del lado del DPA (`.claude/rules/datos.md`).

> **Primera comprobación, antes de diseñar nada:** ¿tienen capa de texto los
> modelos? Ya estaba pendiente en `FASE0_RESULTADOS.md` ("prueba real de capa de
> texto en los PDF") y ahora está en el camino crítico. Los modelos descargados
> de la AEAT normalmente sí la tienen, por ser generados y no escaneados — pero
> eso se comprueba, no se supone.

**2. Un agregado con una fila POR CLIENTE es reidentificable.** Con 33 clientes en
un mercado local, *"C07: hostelería, 4 modelos en 2024, 1.284 asientos"* lo
identifica cualquiera que conozca el pueblo, aunque no lleve nombre ni NIF.

> **Regla:** los agregados que salen del despacho van **por año o por estado,
> nunca por cliente**. Es el mismo criterio del n mínimo de
> `.claude/rules/datos.md`. El agregado actual del inventario ya lo cumple:
> recuentos y distribuciones, ninguna fila por cliente.

### Y una advertencia sobre el 036

El 036 lleva **más cosas que contabilidad**: datos personales del administrador,
domicilios, representantes. De ahí se extraen **solo las obligaciones y sus
fechas** —qué modelos, desde cuándo, en qué régimen— y nada más. El resto del
documento no entra en ningún pipeline, igual que los DNI y las escrituras
(`PROJECT_STATUS.md`, "Frontera de alcance").

## 1-ter. El "cerebro" fluido — de dónde viene la fricción de verdad

El objetivo declarado es tenerlo todo conectado y consultable sin fricción:
histórico, motor contable, fiscal, normativa. La preocupación razonable es que la
disciplina de privacidad lo vuelva incómodo de usar.

> **Diagnóstico: la fricción no viene de la seguridad. Viene de que el histórico
> no está indexado.**

Hoy, responder a *"¿a qué cuenta suele ir este proveedor?"* obliga a abrir y
parsear **1.287 contenedores ZIP** otra vez. Los `fase0_*.py` tardan minutos por
pasada, y son de solo lectura. Esa es la fricción real, y **no tiene nada que ver
con el RGPD**: la tendrías igual sin ninguna regla de privacidad.

### La pieza que lo arregla: un índice local

Una base local (SQLite basta) con el histórico ya extraído: asientos, líneas,
terceros por índice anónimo, cuentas, periodos. En el disco cifrado de la
máquina, construida una vez y actualizada cuando entren copias nuevas.

Con eso, una consulta pasa de **minutos a milisegundos**, y de repente sí se
puede preguntar cualquier cosa cuando haga falta.

> **Esto NO contradice el "no migrar cachés a SQLite" de `PROJECT_STATUS.md`.**
> Aquello era sobre las **cachés** del motor, que pesan MB y se leen en
> milisegundos: ahí SQLite era sobreingeniería y sigue siéndolo. El **histórico**
> es otro problema: 348.716 líneas repartidas en 1.287 ZIP. Son cosas distintas
> con la misma herramienta.

### Los dos modos, y por qué el 90% no tiene fricción

La clave para que esto sea fluido **y** seguro es que no es un solo modo:

| | **Modo consulta** (el 90% del día) | **Modo documento** |
|---|---|---|
| Qué se pregunta | *"¿cuántas?", "¿a qué cuenta?", "¿cuánto?"* | *"lee esta factura"* |
| Qué necesita el modelo | **Contar**, no ver | **Ver** el dato |
| Dónde corre | Índice local, instantáneo | API con DPA, sesión local |
| Qué vuelve a Claude | Recuentos y porcentajes | El documento viaja |
| Fricción | **Ninguna** | La de una decisión deliberada |

**Casi todo lo que se quiere preguntar a diario cae en la primera columna.**
*"¿Qué proveedores nuevos hay este trimestre?"*, *"¿a qué cuenta va este NIF
normalmente?"*, *"¿cómo va el margen frente al año pasado?"* — todas son cuentas,
y todas pueden volver enteras sin romper nada.

> La fricción no se elimina fusionando los dos modos. Se elimina haciendo el
> primero tan rápido y tan completo que rara vez haga falta el segundo.

### La normativa no tiene NINGUNA restricción

Punto que conviene no arrastrar por inercia: **el BOE, la LIVA, la LIRPF y las
consultas de la DGT son públicos.** Un índice normativo local no contiene ni un
dato de cliente.

**Ahí no hay frontera que respetar, ni DPA que necesitar, ni tres roles que
aplicar.** Es la pieza del "cerebro" con más libertad de todas y se puede
construir tan fluida como se quiera, hoy mismo, sin esperar a nada.

La única disciplina que sí aplica ahí es otra, y ya está escrita
(`DISENO_APRENDIZAJE.md` §9.1): sin cita textual de la fuente, no hay respuesta.

## 2. La dirección de la validación: de fuera hacia dentro

Los modelos presentados y el 036 son **hechos externos**: fechados, presentados
ante Hacienda, inmutables. La contabilidad es **interna**: es lo que nosotros
escribimos.

> **La validación va siempre de lo externo a lo interno. Nunca al revés, nunca en
> círculo.**

Si la contabilidad se valida contra los modelos y los modelos se comprueban
contra la contabilidad, se acaba confirmando un error consigo mismo.

Distinción que hay que mantener limpia:

- **Retroalimentación para aprender** (el motor aprende del histórico): sí, toda.
- **Retroalimentación para validar** (A valida B valida A): nunca.

---

## 3. El 036 es la única fuente que dice lo que TENDRÍA que haber

Todo lo demás dice **lo que hay**. El 036 declara las obligaciones de cada
cliente: qué modelos está obligado a presentar, desde cuándo, en qué régimen,
hasta cuándo.

Eso convierte "faltan cosas" de una sensación en una **resta**:

```
obligaciones declaradas en el 036  −  presentaciones archivadas  =  huecos
```

Esa lista de huecos es un entregable con valor propio, aunque el motor no llegue
nunca a producción: un modelo no presentado son recargos y requerimientos.

---

## 4. Orden de construcción

1. **Ordenar** el 100% de lo que hay — identidad de cliente entre carpetas, qué
   ejercicio cubre cada copia, cuál es la copia buena de cada par, y por qué una
   cobertura parcial es parcial (cruzando altas y bajas).
2. **Situar los modelos** de cada cliente sobre esa línea de tiempo ya ordenada.
3. **Validar** contra lo presentado, y medir.

**Por qué este orden y no "validar primero":** el módulo del 390 dentro de las
copias está en blanco (`FASE0_RESULTADOS.md` §11.1 — 1.268 de 1.287 copias
enteramente a cero). La validación fiscal necesita el corpus de modelos
presentados, que vive **fuera** de las copias de contabilidad. Para cruzarlo hay
que tenerlo inventariado y situado en el tiempo antes.

No es una preferencia de método: es el único orden que funciona.

### Las puertas — no se pasa a la siguiente sin cruzar la anterior

Recuperado de la autocorrección del 11-08-2026, que sigue vigente y nombra el
error que este proyecto **ya ha cometido tres veces** (versiones v3, v4 y v5 del
plan): **construir a lo ancho antes de medir.**

| # | Puerta | No se pasa hasta que… |
|---|---|---|
| 0 | **Fase 0** — medir si el histórico es consistente | Los agregados estén medidos, no supuestos |
| 1 | **Corte vertical** — un solo tipo de caso, de punta a punta | Ese caso funcione completo y reproducible |
| 2 | **Memoria por par** — poblada cliente a cliente | El corte vertical lo justifique con números |
| 3 | **Producto** — informes, detección de oportunidades | Exista una tasa de falsos verdes medida |

El fallo característico es saltar directo a la puerta 2 o 3 porque son las
visibles y las que ilusionan. **Generalizar a los 33 clientes antes de que el
corte vertical funcione es exactamente el error de v3/v4/v5.**

Señal de alarma concreta: si alguien —persona o modelo— propone "poblar la
memoria de todos los clientes" o "generar el informe para el primer cliente
piloto" y las puertas anteriores no están cruzadas, la respuesta es no.

---

## 5. Criterio de "hecho" del inventario

El motor ya tiene su criterio de terminado (`.claude/rules/testing.md`). El
inventario no lo tenía, y sin él "pulir hasta fiarse" no tiene final.

Cada par `(cliente, ejercicio)` recibe **un estado y solo uno**:

| Estado | Significado |
|---|---|
| `COMPLETO` | El diario cubre todo el periodo en que el cliente estuvo de alta |
| `PARCIAL_EXPLICADO` | Cubre menos, y hay razón con fuente: alta, baja, cese, cambio de asesoría |
| `PARCIAL_SIN_EXPLICAR` | Cubre menos y no se sabe por qué |
| `INUTILIZABLE` | No se puede leer, o no cuadra |

> **El inventario está "de fiar" cuando `PARCIAL_SIN_EXPLICAR` baja del 5% y cada
> caso que quede dentro está listado uno a uno, no agregado.**

El umbral se fija **antes** de medir, no después de ver el resultado.

---

## 6. Lo que el cuadre interno NO demuestra

El 98,42% de asientos que cuadran debe = haber (`FASE0_RESULTADOS.md` §5)
demuestra que **lo que hay está bien escrito**. No demuestra que esté todo.

> Un asiento que falta, falta con sus dos patas. El cuadre sigue perfecto.

Por eso la completitud necesita un ancla externa y no se puede deducir de la
propia contabilidad. Mismo motivo que el §2.

---

## 7. Cuando un cuadre falle, hay tres causas — y al principio domina la tercera

1. La contabilidad está mal.
2. La presentación estuvo mal.
3. **Nuestra reconstrucción está mal** (mapeo de casillas, criterio, periodo).

Al empezar, la tercera domina con diferencia. **No se concluye "aquí hay un error
contable" hasta que la reconstrucción esté probada sobre casos que se sabe
buenos.** Primero se calibra el instrumento, después se creen sus lecturas.

Es el mismo problema de los falsos verdes del motor, vestido de otra cosa.

### Por dónde se empieza el cuadre del 303

- **El IVA devengado del trimestre** (base y cuota repercutida contra las casillas
  de régimen general) es limpio y casi aritmético. **Se empieza por ahí.**
- **El resultado final a ingresar o devolver no lo es**, y no por poco: entra la
  compensación de cuotas de periodos anteriores (que arrastra de un trimestre al
  siguiente), deducciones, prorrata, inversión del sujeto pasivo,
  intracomunitarias, y el desfase entre fecha de registro y fecha de devengo.
  **Se deja para cuando lo anterior esté calibrado.**

---

## 8. Un motor, dos usos

El mismo cuadre contabilidad ↔ modelos presentados se usa en dos direcciones:

- **Hacia atrás**, sobre diez años: valida el histórico y mide en qué se puede
  confiar.
- **Hacia delante**, cada trimestre: asegura que lo que hay en el programa de
  contabilidad es real antes de presentar.

Se construye una vez y se usa dos. La segunda es funcionalidad de producto, no
trabajo de arqueología.

---

## Frontera de datos (recordatorio, no negociable)

Nada de esto cambia `.claude/rules/datos.md`. Los conjuntos nuevos (modelos,
altas y bajas) contienen NIF y datos identificables: se tratan igual que la
contabilidad — identidad en `_LOCAL`, agregados en porcentajes al repositorio, y
los scripts los ejecuta Diego, no Claude.

Los DNI y las escrituras siguen **fuera de todo pipeline**, sin excepción.
