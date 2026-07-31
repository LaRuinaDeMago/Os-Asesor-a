# La Fábrica — motor de validación de facturas

Este proyecto valida facturas de un despacho de asesoría fiscal contra guards de
reglas contables y fiscales reales (motor de veredicto: OK / FALLO / NO_APLICA /
NO_COMPROBADO, nunca OK por omisión). NO procesa facturas reales de clientes en
este entorno (Cloud/GitHub) bajo ninguna circunstancia.

## Al empezar cualquier sesión
Lee PROJECT_STATUS.md completo antes de hacer ningún cambio. No asumas el estado
del proyecto por esta conversación — confírmalo ahí y con los tests. Si
PROJECT_STATUS.md y el código/tests no coinciden, mandan los tests, no el texto
(ver `PARTE 3.3` de FLUJO_CONTINUO_PLAN_DEFINITIVO — jerarquía: Código → Tests →
Git → PROJECT_STATUS.md).

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
- Cada guard nuevo necesita: función + entrada en `evaluar_fila_v4` (si aplica al
  veredicto principal) + prueba en `test_motor_veredicto.py` + entrada en README.md.
- Los tests de `test_motor_veredicto.py` usan casos reales anonimizados (nombres
  y NIF sustituidos por placeholders con checksum matemáticamente válido, nunca
  el dato real) — mantener esa disciplina en cualquier test nuevo.
- Ver `.claude/rules/` para reglas detalladas por dominio.

## Entorno de este equipo
Este equipo no tenía Python instalado; se instaló una distribución portátil
(embeddable) en el directorio temporal de la sesión para poder ejecutar los
tests durante la auditoría inicial. En el PC real de la asesoría, usar la
instalación de Python de ese equipo.
