# Regla de datos — la más importante de todo el proyecto

Cloud (GitHub, Claude Code Web): SOLO código, tests, datos sintéticos/anonimizados,
documentación, arquitectura.

Local (PC de la asesoría): facturas reales, ContaPlus, contabilidades reales,
NIF reales, históricos identificables — pero SOLO para lo que nunca pasa por
Claude (ContaPlus/ContaSol en sí, archivos que Claude no llega a leer). En
cuanto Claude lee o procesa un archivo real, da igual que sea en modo Local:
ese contenido se envía a la API de Anthropic para poder procesarlo — "Local"
solo describe dónde se ejecutan las herramientas (archivos, git, bash), no
dónde vive el modelo, que siempre corre en la nube de Anthropic.

CORRECCIÓN 31-07-2026: por eso, antes de pedirle a Claude que procese CUALQUIER
dato real de cliente (factura, NIF, contabilidad), aunque sea en Local, hace
falta tener un DPA (Adenda de Procesamiento de Datos) con Anthropic — y eso
solo existe en cuentas COMERCIALES (Team/Enterprise/API), no en Pro/Max/Free
(regidas por "Consumer Terms", sin marco de DPA). Confirmado en
`privacy.claude.com` y `code.claude.com/docs/en/data-usage`.

MECANISMO CONCRETO (revisado 31-07-2026, `code.claude.com/docs/en/authentication.md`):
NO hace falta pasar toda la cuenta de Diego a Team. Se combina Pro (para el
canal código de siempre — Remote Control, Cloud, este repositorio) con
API/Consola de Anthropic (comercial, DPA incluido, sin el mínimo de 2 asientos
de Team) SOLO para sesiones con datos reales. El interruptor es la variable de
entorno `ANTHROPIC_API_KEY`: puesta → prioriza la API/DPA sobre la suscripción
(una vez aprobada); `unset ANTHROPIC_API_KEY` → vuelve a la suscripción
Pro/Remote Control. Comprobar con `/status` cuál está activa. LÍMITE REAL:
Claude Code on the Web SIEMPRE usa la suscripción, nunca la API key — así que
el modo "datos reales" solo puede darse en sesión LOCAL, nunca en Remote
Control ni en Cloud/Web. Hasta que la API/Consola esté contratada y
`ANTHROPIC_API_KEY` configurada, NINGÚN dato real de cliente se le pasa a
Claude en ninguna superficie.

Esta frontera es ARQUITECTÓNICA, no una revisión puntual. Nunca se cruza.

## PRECISIÓN 19-08-2026 — el DPA hace falta cuando el dato LLEGA al modelo

Esto afina lo de arriba, no lo contradice, y evita dos errores opuestos: creerse
libre porque "se ejecuta en local", y bloquearse creyendo que sin DPA no se puede
tocar nada real.

> **Lo que exige DPA es que el dato REALICE el viaje a Anthropic. Si no viaja, no
> hace falta.**

El **diseño de tres roles** que ya se usa en la Fase 0 evita ese viaje, y por eso
funciona con Pro:

1. **Claude escribe el script** — sin ver datos, solo el esquema.
2. **Diego lo ejecuta en su máquina** — el NIF vive en la memoria del proceso, se
   usa para agrupar, y la identidad se escribe únicamente en el fichero `_LOCAL`,
   que se queda en el disco.
3. **Claude lee solo el agregado** — recuentos y porcentajes.

El NIF nunca entra en una petición a la API. Con ese diseño, medir el histórico
completo es legítimo hoy, sin contratar nada.

**Las tres formas de romperlo, y cómo está tapada cada una:**

| Riesgo | Mitigación (ya aplicada) |
|---|---|
| Un script peta e imprime una fila en el mensaje de error | Los scripts capturan por registro y reportan **solo el tipo** de excepción: `errores[type(e).__name__] += 1`. Nunca el mensaje, que arrastra datos |
| Claude abre un fichero `_LOCAL` | **Regla dura: no se abre un `_LOCAL` jamás.** Si hace falta algo de ahí, se le pide a Diego |
| Se pega la salida en el chat | Prohibido explícitamente (ver corrección 29-07-2026 arriba) |

**Dónde el diseño de tres roles NO sirve, y ahí sí hace falta el DPA sin
excepción:** cualquier funcionalidad en la que **el propio modelo** tenga que leer
el dato del cliente para hacer su trabajo — leer una factura, redactar un informe
sobre una empresa concreta, analizar su tesorería, proponerle una optimización.
Ahí el dato viaja por definición y no hay diseño que lo evite. Es decir: **toda la
dirección de producto de `DIRECCION_PRODUCTO.md` está al otro lado de esa puerta.**

Regla práctica para saber en qué lado estás:

> ¿El modelo necesita **ver** el dato para producir el resultado, o le basta con
> **contarlo** un script? Si necesita verlo → DPA. Si basta contarlo → tres roles.

## Uso secundario de los datos de cliente — LÍNEA ROJA

Los datos contables de los clientes están en el despacho por una relación de
servicio profesional, con secreto profesional de por medio. **No son un activo
comercializable del despacho.**

Queda **descartado, no aplazado**, cualquier uso que convierta esos datos en
producto para terceros. En concreto, y porque se ha propuesto explícitamente
(valoraciones estratégicas del 19-08-2026, "Nivel 3 — Datos como activo"):

- ❌ Vender informes o estudios sectoriales derivados de las contabilidades.
- ❌ Modelos de predicción de insolvencia sobre empresas, ofrecidos a terceros.
- ❌ Ceder o compartir indicadores de salud financiera con bancos, aseguradoras,
  inversores o asociaciones.
- ❌ Detección de "oportunidades de inversión" en empresas a partir de sus libros.

**"Con anonimización" no lo arregla**, por tres motivos independientes y cada uno
suficiente: con una cartera de 33 clientes en un mercado local la reidentificación
es trivial; no existe base legal para ese tratamiento (los clientes contrataron
asesoría, no cesión de datos); y el secreto profesional aplica al margen del RGPD.

**Dónde sí está la línea:** analizar los datos de un cliente **para ese mismo
cliente** es exactamente el servicio que se le presta. Ese es todo el margen que
hay, y es amplio. Comparar clientes entre sí para beneficio de un tercero, no.

CORRECCIÓN 29-07-2026: ni siquiera con Remote Control (ejecución local) se debe
pegar, escribir o mostrar en el chat un NIF real o nombre de cliente real — la
transcripción de Remote Control se guarda en servidores de Anthropic, aunque la
ejecución sea local. Ejecución local ≠ conversación local.

Un repositorio "privado" de GitHub NO es suficiente frontera por sí solo — una
sesión Cloud puede acceder a cualquier repositorio que vea la cuenta de GitHub
conectada, así que la barrera real es el CONTENIDO, no el candado del repo.

## Los .zip nunca se suben

Ningún archivo `.zip` sube a este repositorio bajo ninguna circunstancia, revisado
o no — su formato impide inspeccionar el contenido fácilmente antes de subir, lo
que los hace estructuralmente peligrosos. Si algo de dentro de un zip hace falta,
se extrae, se audita el archivo individual, y solo ese archivo (ya auditado) se
sube — nunca el zip completo. (Incidente real que originó esta regla: 29-07-2026,
ver FLUJO_CONTINUO_PLAN_DEFINITIVO sección 1.4.)

## Comandos que muestran contenido real necesitan aprobación explícita

Antes de ejecutar cualquier comando que pueda imprimir, mostrar o escribir el
contenido real de un archivo con datos potencialmente identificables:
- Comandos que solo cuentan o comprueban tipo (`len()`, `.Count`, `isinstance`,
  tamaño de archivo, número de líneas) → seguros de ejecutar sin preguntar.
- Comandos que muestran contenido, líneas completas, o claves de un objeto/dict
  que podrían ser NIF o nombres reales (ej. iterar las claves de nivel superior
  de un JSON indexado por NIF) → SIEMPRE pedir aprobación explícita antes,
  explicando qué parte del comando preocupa y por qué.

## Comentarios y docstrings de código

El código que va a GitHub no debe citar nombres de cliente/proveedor reales ni
en la lógica ni en comentarios/docstrings/mensajes de test, aunque el dato
numérico o la lógica en sí sean genéricos y útiles. Sustituir por "cliente
piloto" / "caso real anonimizado", manteniendo intactos los números y la lógica.
Si un dato de prueba necesita parecer un NIF/DNI real (para probar el dígito de
control), usar un NIF/DNI inventado con checksum matemáticamente válido —
nunca el real.
