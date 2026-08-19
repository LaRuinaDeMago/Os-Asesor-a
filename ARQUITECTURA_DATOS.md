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
