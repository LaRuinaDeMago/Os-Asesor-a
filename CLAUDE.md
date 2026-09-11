# La Fábrica — motor de validación de facturas

Este proyecto valida facturas de un despacho de asesoría fiscal contra guards de
reglas contables y fiscales reales (motor de veredicto: OK / FALLO / NO_APLICA /
NO_COMPROBADO, nunca OK por omisión). NO procesa facturas reales de clientes en
este entorno (Cloud/GitHub) bajo ninguna circunstancia.

## Al empezar cualquier sesión — en este orden, sin saltarse ninguno

**1. Ejecuta esto ANTES de leer nada.** Tarda segundos y no toca ningún dato:

```bash
python arranque.py          # en Linux/Mac puede ser python3
```

Imprime, midiéndolo en el momento y no citándolo de un texto: el entorno, si el
trabajo está en una rama que nadie va a clonar, si el hook de privacidad está
puesto, qué dependencias faltan y qué bloquea cada una, y **la lista de
pendientes** (`PENDIENTE.md`, que es la única que hay — si algo se termina se
tacha ahí).

**2. Después lee `EMPEZAR_AQUI.md`**, que es el punto de entrada narrativo: por
qué las cosas son como son.

**3. `PROJECT_STATUS.md` NO se lee entero.** Es un registro histórico que solo
crece (no se escribe aquí su tamaño exacto a propósito: derivaría, como ya le
pasó a este mismo párrafo — decía "140 KB" cuando ya iba por 257 KB):
se **consulta** buscando una fecha o un tema concreto. Hasta el 10-09-2026 este
mismo apartado ordenaba leerlo completo, lo cual sólo tenía dos desenlaces y los
dos malos — gastar media sesión en historia, o saltárselo y perder el estado.

**4. Antes de tocar el motor**, `python audit_project.py`. Códigos de salida:
`0` todo comprobado y en verde · `1` **hay un defecto real, y eso manda sobre
todo lo demás** · `2` nada falla pero algo no se ha podido comprobar (un ⚠️ no
es un aprobado).

No asumas el estado del proyecto por la conversación — confírmalo con los tests.
**Jerarquía de verdad: Código → Tests → Git → PROJECT_STATUS.md.** Si la
documentación y los tests no coinciden, mandan los tests.

> `FLUJO_CONTINUO_PLAN_DEFINITIVO.md` se cita en este archivo y en
> `.claude/rules/datos.md` como origen de varias reglas. **No está en el
> repositorio y no puede estar**: contiene apellidos reales de clientes, vive
> sólo en el PC de la asesoría y está bloqueado por nombre en
> `NUNCA_SUBE_FILENAMES.txt` y en `.gitignore`. No lo busques ni lo subas; las
> reglas que de él salen ya están recogidas aquí y en `.claude/rules/`.

## Qué NUNCA hacer
- Nunca subir, escribir, ejecutar un comando que imprima, o mostrar en el chat un
  NIF real, nombre de cliente/proveedor real, o cualquier dato identificable de
  una persona o empresa concreta. Ver `.claude/rules/datos.md`.
- Nunca subir un archivo `.zip` a este repositorio, revisado o no (ver incidente
  documentado en FLUJO_CONTINUO_PLAN_DEFINITIVO sección 1.4). Si algo dentro de un
  zip hace falta, se extrae, se audita el archivo individual, y solo ese archivo
  (ya auditado y, si hacía falta, anonimizado) se sube.
- Nunca añadir un guard nuevo, ni una fuente de referencia nueva, sin que haya un
  caso real y concreto que lo pida. Preguntar primero si no está claro.
- Nunca activar Auto-fix de pull requests en este repositorio (motor contable,
  cada cambio se revisa a mano).
- Nunca modificar motor_veredicto.py (ni layout_diario_contaplus.py, orquestador.py)
  sin ejecutar test_motor_veredicto.py antes y después del cambio, y confirmar
  100% en verde. Ver `.claude/rules/contabilidad.md` y `.claude/rules/testing.md`.
- Nunca ejecutar un comando que pueda imprimir claves de un diccionario/objeto si
  esas claves podrían ser NIF reales (ej. iterar sobre las claves de nivel
  superior de un JSON indexado por NIF). Solo contar, comprobar tipo, o listar
  nombres de campo — nunca claves ni valores — sin pedir aprobación explícita
  antes. Ver `.claude/rules/seguridad.md` y `.claude/rules/datos.md`.

## Convenciones del proyecto
- Python 3, sin frameworks pesados.
- Cada guard nuevo necesita: función con docstring que explique qué comprueba y
  por qué (es la práctica real seguida hasta hoy — no existe un `README.md` de
  catálogo de guards, ni ha existido nunca) + entrada en `evaluar_fila_v4` (si
  aplica al veredicto principal) + prueba en `test_motor_veredicto.py`.
- Los tests de `test_motor_veredicto.py` usan casos reales anonimizados (nombres
  y NIF sustituidos por placeholders con checksum matemáticamente válido, nunca
  el dato real) — mantener esa disciplina en cualquier test nuevo.
- Ver `.claude/rules/` para reglas detalladas por dominio.

## Entorno de este equipo
Este equipo no tenía Python instalado; se instaló una distribución portátil
(embeddable) en el directorio temporal de la sesión para poder ejecutar los
tests durante la auditoría inicial. En el PC real de la asesoría, usar la
instalación de Python de ese equipo.
