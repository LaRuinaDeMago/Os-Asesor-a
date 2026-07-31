# PROJECT_STATUS — estado operativo, no documentación

Este archivo se actualiza cada vez que algo cambia de verdad. Al abrir Claude Code
después de días sin tocar el proyecto, léelo primero — dice exactamente dónde
retomar, sin tener que releer toda la conversación. Si algo aquí no coincide con
lo que demuestran los tests o el código, mandan los tests, no este texto.
Jerarquía de verdad: Código → Tests → Git → este archivo.

## FASE ACTUAL
FASE 0 — Auditoría de privacidad: CERRADA (31-07-2026).
FASE 1 — GitHub como columna vertebral del código: CERRADA (31-07-2026, ver
más abajo). Repo privado: `https://github.com/LaRuinaDeMago/Os-Asesor-a`.
FASE 2 — PoC Gemini: siguiente, sin empezar todavía.

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
GitHub ya está montado y verificado (ver más abajo). Lo siguiente: activar
facturación en Google AI Studio, configurar `GEMINI_API_KEY`, ejecutar
`captura_orquestador.py --imagen [una factura] --proveedor gemini` una sola vez.
En paralelo, sin bloquear lo anterior: confirmar con Diego el mecanismo técnico
concreto de consulta de la Fase 5 de v2 (RAG / conector MCP de Drive / adjunto
manual) antes de contratar Google Workspace — ver nota en la sección de
auditoría de privacidad.

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
4. Seguir con Fase 2/PoC Gemini (activar facturación, `GEMINI_API_KEY`,
   primera factura real por `captura_orquestador.py`).

### Nota técnica de entorno

Este equipo no tenía Python instalado. Se instaló una distribución portátil
("embeddable") de Python 3.12 en el directorio temporal de la sesión para poder
ejecutar `test_motor_veredicto.py` y el escáner de privacidad durante la
auditoría — no queda instalada de forma persistente en este equipo. En el PC
real de la asesoría, verificar qué versión de Python hay disponible, y ejecutar
`scripts/install_hooks.sh` tras clonar el repo ahí (el hook no viaja solo con
`git clone`).
