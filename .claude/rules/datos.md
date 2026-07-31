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
`privacy.claude.com` y `code.claude.com/docs/en/data-usage`. Hasta que la
cuenta pase a Team y se firme el DPA, NINGÚN dato real de cliente se le pasa a
Claude en ninguna superficie — ni Local, ni Remote Control, ni Cloud.

Esta frontera es ARQUITECTÓNICA, no una revisión puntual. Nunca se cruza.

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
