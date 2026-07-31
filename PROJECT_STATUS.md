# PROJECT_STATUS — estado operativo, no documentación

Este archivo se actualiza cada vez que algo cambia de verdad. Al abrir Claude Code
después de días sin tocar el proyecto, léelo primero — dice exactamente dónde
retomar, sin tener que releer toda la conversación. Si algo aquí no coincide con
lo que demuestran los tests o el código, mandan los tests, no este texto.
Jerarquía de verdad: Código → Tests → Git → este archivo.

## FASE ACTUAL
FASE 0 — Auditoría de privacidad y puesta en marcha de GitHub (en curso).
FASE 1 — PoC Gemini: sin empezar todavía, es la siguiente tras cerrar la Fase 0.

## OBJETIVO DE LA FASE 1 (siguiente)
Una factura real → Gemini API → JSON estructurado → motor → veredicto.
Criterio de aprobación: funcionamiento técnico reproducible (no precisión todavía).

## ÚLTIMO RESULTADO
(vacío — se rellena la primera vez que se ejecute `captura_orquestador.py --proveedor gemini` de verdad)

## MOTOR — estado verificado el 30-07-2026 (re-verificado tras limpieza de privacidad)
- 19 funciones de guard, 16 activas en el veredicto principal (`evaluar_fila_v4`).
- `test_motor_veredicto.py`: 100% de comprobaciones en verde (17 checks),
  ejecutado en esta sesión con Python 3.12 portátil tras genericar los datos de
  prueba (ver sección de auditoría más abajo).
- Probado en su día con 91 facturas reales de clientes piloto anonimizados + 1
  factura nueva en vivo → VERDE correcto (cifras conservadas, nombres reales ya
  no viven en el código ni en este archivo).
- Orquestador (`orquestador.py`) probado de punta a punta, reproducible.

## FALSOS VERDES CONOCIDOS
Ninguno todavía — no se ha ejecutado la Fase 1/2 con datos reales de Gemini.
**Esta es la métrica más importante de todo el proyecto. Cuando aparezca el primer
número real aquí, es la señal de que el proyecto ha empezado de verdad.**

## SIGUIENTE ACCIÓN CONCRETA
Cerrar la Fase 0 (ver checklist de auditoría abajo: crear repo, subir solo
`SUBE_A_GITHUB.md`, verificar en limpio). Después: activar facturación en Google
AI Studio, configurar `GEMINI_API_KEY`, ejecutar
`captura_orquestador.py --imagen [una factura] --proveedor gemini` una sola vez.

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

### Pendiente (primer mensaje al retomar)

1. **Crear el repositorio en GitHub** (Fase 1 del plan, sección 2.1): privado,
   vacío, sin README ni .gitignore automáticos.
2. Subir SOLO lo que lista `SUBE_A_GITHUB.md` — no la carpeta entera, no arrastre
   masivo.
3. Clonar en limpio y repetir el grep de verificación (sección 2.3 del plan) —
   cero resultados es el único criterio de éxito válido.
4. Repasar a mano los archivos marcados como "verificación parcial" en
   `SUBE_A_GITHUB.md` (`criterios_fiscales_v1_0_historico.json`,
   `suite_regresion.json`, y 5 `.md` de gobierno sin coincidencias de grep pero
   no leídos línea a línea) antes de subirlos, o dejarlos fuera si hay duda.
5. Decidir si se quiere intentar extraer/filtrar la ficha real que contamina
   `DIRECTORIO_NACIONAL_PROVEEDORES.json` (ver `NUNCA_SUBE.md`) para poder subir
   el resto del directorio, o dejarlo entero fuera.
6. Instalar Desktop app y probar Local + Cloud (Fase 3, prueba de fuego 5.1).

### Nota técnica de entorno

Este equipo no tenía Python instalado. Se instaló una distribución portátil
("embeddable") de Python 3.12 en el directorio temporal de la sesión para poder
ejecutar `test_motor_veredicto.py` durante la auditoría — no queda instalada de
forma persistente en este equipo. En el PC real de la asesoría, verificar qué
versión de Python hay disponible antes de asumir que los tests corren igual.
