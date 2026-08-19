# Dirección de producto — hacia dónde va esto

**Qué es este fichero:** la dirección declarada del proyecto a medio y largo plazo.
Nada de aquí está medido. **No manda sobre nada**: la jerarquía de verdad sigue
siendo Código → Tests → Git → documentos operativos. Si una medición contradice
algo de aquí, gana la medición y este fichero se corrige.

**De dónde sale:** de tres valoraciones estratégicas pedidas a otro modelo de IA
(19-08-2026) más la discusión posterior. Se recogen aquí **solo las partes que
resisten**; se descartan a propósito las tablas de puntuación ("4/10", "9,5/10")
y las cifras de impacto ilustrativas, por no tener derivación. En este proyecto
un número sin origen no entra en un documento.

---

## El destino, en una frase

> Una asesoría cuyo **funcionamiento interno** está diseñado alrededor de datos,
> normativa y automatización, y donde el asesor sigue tomando las decisiones
> profesionales.

No es "una asesoría que usa IA". La diferencia es la arquitectura, no la
herramienta.

---

## Los cuatro principios que se adoptan

1. **El cumplimiento es commodity; el valor está en la decisión.** Presentar
   modelos vale cada vez menos. Detectar qué debería decidirse *antes* de que el
   problema ocurra vale cada vez más.

2. **Se programa lo repetitivo, estructurado y verificable.** Queda humano el
   juicio profesional, la interpretación compleja, las decisiones de alto riesgo
   y la responsabilidad. Es la misma línea que ya sigue el motor al devolver
   `NO_COMPROBADO` en vez de un `OK` silencioso.

3. **El foso no es el código.** Es lo acumulado: datos + reglas + conocimiento
   fiscal + histórico de decisiones. El código es replicable en meses; diez años
   de casos con sus decisiones, no.

4. **Escalar por cliente, no por volumen.** El objetivo no es tener más clientes
   pagando poco por cumplimiento, sino generar más valor por cliente.

---

## El KPI

> **Que una persona pueda gestionar 3–5 veces más clientes manteniendo o
> aumentando la calidad.**

Medido en: **€/hora del asesor · valor generado al cliente · errores evitados.**

No en número de funcionalidades, ni de agentes, ni de líneas de Python.

---

## Las tres puertas que hay que cruzar

Ninguna es técnica. Las tres pueden bloquear el proyecto entero y ninguna se
resuelve programando.

### 1. Responsabilidad profesional — la más difícil, y la menos discutida

Un falso verde en una factura es un error de proceso. Un falso *"esto es
deducible"* es una sanción para el cliente y responsabilidad del despacho. La
asimetría es severa.

Un sistema que **propone** optimizaciones genera esa exposición aunque un humano
valide después, porque el humano valida sobre lo que el sistema le puso delante.

**Consecuencia práctica, ya aplicable hoy:** todo lo que el sistema proponga debe
llevar su base normativa citada y su nivel de confianza explícito. Una
recomendación sin fuente no sale. Es el mismo principio del motor, subido de
nivel.

### 2. Huella de datos y DPA — deja de ser un trámite

Validar una factura procesa un documento. Un análisis financiero continuo por
cliente procesa **todo**: tesorería, márgenes, patrimonio, decisiones, histórico.
Y todo eso pasa por la API del modelo.

> **En esta dirección, contratar API/Consola de Anthropic con DPA no es el punto
> 4 de una lista de pendientes: es el cimiento.** Sin eso, nada de lo descrito
> aquí se puede construir legalmente sobre datos reales.

Ver `.claude/rules/datos.md`. La frontera no se mueve por ser más ambicioso el
objetivo; al contrario, cuanto más ambicioso, más carga soporta.

### 3. Base de clientes

La cartera actual es de 33 clientes (14 S.L. + 19 autónomos). El salto que
describe la dirección supone otra composición de cartera. **De dónde salen esos
clientes es un problema sin resolver** y no se resuelve con producto.

Queda declarado como pendiente, no como detalle.

---

## Qué NO cambia del plan actual

Esto es lo importante para no desviarse: **la dirección no reordena el trabajo en
curso.**

El "gemelo financiero" que describe la visión —conocer de cada cliente ingresos,
gastos, impuestos, patrimonio, histórico, y buscar continuamente dónde está la
oportunidad— **no es un proyecto distinto que venga después.** Es exactamente la
espina `(cliente, periodo)` de `ARQUITECTURA_DATOS.md` con sus tres conjuntos
enganchados.

> El trabajo de ordenación del histórico no es un paso previo al producto. **Es
> el producto, en su capa de datos.**

Sigue vigente sin cambios:

- El orden **ordenar → situar modelos → validar** (`ARQUITECTURA_DATOS.md` §4).
- El criterio de "hecho" del inventario (§5).
- La medición de falsos verdes como métrica que decide el proyecto.
- Todo lo de `NO HACER TODAVÍA` en `PROJECT_STATUS.md`.

---

## Ideas concretas propuestas — qué se guarda y qué se descarta

Segunda tanda de valoraciones estratégicas (19-08-2026). Mismo criterio: se
guarda lo que resiste, se descartan las cifras sin derivación (retainers,
proyecciones de facturación, "% del ahorro generado") por el mismo motivo que la
primera tanda.

### Se guardan como candidatas — detrás de la puerta 3

Ninguna se construye hasta que exista una tasa de falsos verdes medida
(`ARQUITECTURA_DATOS.md` §4, tabla de puertas):

- **Módulo de detección de oportunidades.** Reglas sobre el histórico ya
  estructurado: amortizaciones no aplicadas, activos sin amortización asociada
  (cuentas 21x sin 28x), tratamiento de intracomunitarias. Es una extensión
  natural del motor de guards, con la misma disciplina: nunca un `OK` por
  omisión, y toda propuesta con su base normativa citada.
- **Informe de control de gestión** por cliente: rentabilidad, márgenes,
  previsión de tesorería, cuadro de mando. Se apoya en la misma espina.
- **Planificación plurianual y simulación de escenarios.** El de mayor valor y
  el de mayor exposición a responsabilidad profesional. No antes que el resto.

### Se descarta: "Nivel 3 — Datos como activo"

La propuesta de explotar el histórico como producto para terceros —informes
sectoriales a la venta, predicción de insolvencia, cesión de indicadores a
bancos, detección de oportunidades de inversión sobre empresas— **queda
descartada, no aplazada.**

Motivo en `.claude/rules/datos.md`, sección "Uso secundario de los datos de
cliente". Resumen: la anonimización no es viable con 33 clientes en un mercado
local, no hay base legal para ese tratamiento, y el secreto profesional aplica al
margen del RGPD. Los datos están en el despacho por una relación de servicio; no
son un activo comercializable.

**La línea:** analizar los datos de un cliente **para ese mismo cliente** es el
servicio. Compararlos para beneficio de un tercero, no.

### Nota sobre el SaaS para otras asesorías

Vender la herramienta a otros despachos es **un negocio distinto**, no una fase
del actual: exige soporte, multi-tenant, facturación, y traslada al despacho una
responsabilidad sobre presentaciones ajenas que hoy no tiene. Se deja anotado
como opción, sin evaluar.

---

## El objetivo, reformulado (19-08-2026) — la mejor frase del proyecto

De la tercera tanda de valoraciones estratégicas sale una formulación que sustituye
a todas las anteriores y que conviene no perder:

> **No construir una IA que sustituya al asesor. Construir una IA que fabrique un
> mejor asesor.**

Y su consecuencia, que es la que cambia el KPI de sitio: el tiempo que la
automatización libera **no debe desaparecer en más volumen del mismo trabajo**.
Se reinvierte en casos complejos, normativa y especialización. La máquina no te
hace menos necesario: te sube de nivel.

La pregunta de control dentro de cinco años, entonces, no es *"¿cuánto hemos
automatizado?"* sino:

> **"¿Cuánto más sabe esta asesoría que hace cinco años?"**

Su implementación concreta y sin fricción está en `DISENO_APRENDIZAJE.md` §8
(telemetría pasiva por delta entre `veredicto_maquina` y `veredicto_humano`).

## Menú de expansión — aparcado a propósito, no es un plan

La tercera tanda incluye ~26 vías de expansión: controller externo, auditoría
interna continua, informe de salud contable, compra de carteras, back-office para
otras asesorías, migración de despachos, due diligence, concursal, pericial,
auditoría ROAC, VERI\*FACTU como puerta de entrada.

**Se archiva como menú, no se adopta como plan.** Valoración honesta: hay ideas
buenas ahí dentro, pero son 26 opciones para un proyecto que necesita una, y
ninguna está respaldada por evidencia de cuál encaja con la cartera real.

Tres cosas sí merecen quedar anotadas:

- **VERI\*FACTU es contexto de mercado real**, con plazos regulatorios de verdad.
  No es una línea de producto: es la razón por la que los clientes van a aceptar
  cambios de proceso que antes no aceptaban. Puerta de entrada, no producto.
- **Back-office para otras asesorías necesita su propio análisis legal antes de
  ser considerado**: procesar los datos de los clientes de otro despacho te
  convierte en encargado del tratamiento de terceros, con las obligaciones que
  eso arrastra. No es la línea roja de `.claude/rules/datos.md` (que es sobre
  ceder lo derivado), pero es adyacente y no está resuelto.
- **Concursal, pericial y auditoría son actividades reguladas.** La única forma
  defendible que plantean los propios textos es la correcta: *infraestructura de
  análisis para el profesional habilitado*, nunca el sistema ejerciendo.

### ⛔ Y un consejo de esos textos que se rechaza explícitamente

Proponen: *"antes de escribir prácticamente una línea más de código, dibujar el
Mapa de Explotación con 20–30 vías de monetización"*.

**No.** El 19-08-2026 se confirmaron **8 falsos verdes P0** ejecutando el motor
(`test_adversarial.py`): una factura sin ningún importe legible sale VERDE.
Dibujar un mapa de monetización de 26 ramas mientras el motor da por buena una
factura vacía es, literalmente, *construir a lo ancho antes de medir* — el error
que este proyecto ya ha cometido tres veces (`ARQUITECTURA_DATOS.md` §4).

El orden no cambia: **primero el contrato de datos, después las 14 pruebas
adversariales en verde, después la medición. El mapa de monetización, cuando haya
algo medido que monetizar.**

## Qué queda sin decidir (a propósito)

- El modelo de precio (cuota, valor generado, mixto).
- Si el producto llega a venderse a otros despachos o se queda como ventaja
  interna. Son dos negocios distintos con dos exigencias de calidad distintas.
- Qué líneas de alto valor se atacan primero. La dirección propone varias
  —planificación fiscal, CFO externo, subvenciones, compraventa,
  internacionalización, due diligence— **sin ninguna evidencia de cuál encaja
  mejor con la cartera real.** Esa evidencia existe en el histórico y todavía no
  se ha mirado.

**Nada de esto se decide hasta que haya un número de falsos verdes.** Antes de
eso, cualquier elección sería preferencia, no criterio.
