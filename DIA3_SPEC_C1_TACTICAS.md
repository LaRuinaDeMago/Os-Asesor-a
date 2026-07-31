# SPEC DÍA 3 + TÁCTICAS C1 — captura de specs verbales (2026-07-14)
**Origen: acuerdos de conversación 12-14 julio no recogidos aún en otros documentos. Con este archivo, el paquete captura el 100% de las decisiones del proyecto.**

## MENÚ COMPLETO DEL DÍA 3 (una sesión, ~2 tardes)
1. **Informe de dos capas** de EXP-0001: capa cliente en lenguaje de CRITERIOS_EN_LLANO + sección de confianza visible ("así reconstruimos su caso ante Hacienda en 3 años"; coincidencia 4/4 con extracto oficial) · anexo técnico: lotes consumidos, CRIT-XXX aplicados con versión, nota art. 89.1 LGT, metodología de tipos (W4).
2. **Manifest de auditoría**: manifest.json con SHA-256 de cada eslabón (fuentes → schema → resultado → informe).
3. **Guard G7 — reconciliación de ledger**: saldos teóricos del motor vs columna Available (tolerancia 1e-6). Capa de validación; suite en verde antes/después; entrada en bitácora. (Spec completa en ANATOMIA §2.)
4. **Catálogo de eventos v1.0** (1 página en 01_MOTOR): implementados (COMPRA, VENTA, PERMUTA_IN/OUT) con su CRIT · reservados con destino (RECOMPENSA_STAKING→CRIT-004a, PERMUTA_STAKING_LIQUIDO→004b, AIRDROP→004c base general, TRANSFER_INTERNO, FEE_BRIDGE→sin_respaldo_firme, UNKNOWN→cola humana). Frontera de capas escrita: adaptador traduce Y valora; schema lleva EUR resueltos; motor solo imputa y calcula.
5. **Matriz de cobertura v1.0**: situaciones cubiertas ✅ (compra simple, FIFO multilote, permuta, stablecoin, fee en moneda comprada, pérdida, multi-ejercicio, depósito con justificante) vs reservadas ⬜ (fee en 3ª moneda, transfer entre exchanges, staking×3, airdrop, fork, dust, retiradas). Sintéticos T7+ solo por prioridad de aparición real + gate regla 10; ground truth manual de Diego (= su escuela).
6. **Consolidación**: adaptador ya como módulo ejecutable ✓ (hecho en v3.4); queda: mover mapping a caché formal si procede.
7. **Registro de expedientes**: estrenar con EXP-0001 (métricas: tiempo, warnings, filas revisadas, independencia_ganada, origen=cartera propia).
8. **Checklist onboarding v1.0** (cierra el v0.9 de ANATOMIA §6) + consentimiento RGPD para uso anonimizado del caso.
9. **DECISIÓN RENTA 2025 de Diego**: ¿incluyó las 5 transmisiones (+44,93 €)? → correcta / complementaria (cuota ≈8,54 € + recargo). Se documenta con fundamento en el informe.

## TÁCTICAS C1 ACUMULADAS (activación: tras cierre Día 3)
- **Pitch de intersección** (triaje #11) como núcleo de landing: asesoría completa + cripto + rigor documental.
- **Anclaje físico-local como activo**: "sede real, 20 PYMES de toda la vida, y la máquina que los grandes no tienen".
- **Pieza estrella**: EXP-0001 anonimizado — "el sistema me pilló a mí primero" + coincidencia al 5º decimal con extracto oficial.
- **Vídeo-tutorial 2 min**: cómo exportar los CSVs (guion = ANATOMIA). Mata la fricción nº1 del onboarding.
- **Programa voluntarios**: cálculo gratis a cambio de caso anonimizado para la suite (casos + testimonios + captación). Condición: consentimiento expreso RGPD.
- **Canales día-1**: oferta activa a red personal/familiar de clientes (demografía <45 con cripto) + regularizaciones todo-el-año (avisos ola 1) + SLA <2h + petición de reseña post-primer-éxito.

## RADAR NORMATIVO — capturas verificadas pendientes de ciclo trimestral
- **VeriFactu APLAZADO** (RDL 15/2025, BOE 03/12/2025): 01/01/2027 sociedades IS · 01/07/2027 autónomos. 2026 = año de migración tranquila (ContaSol/FactuSol) + servicio facturable "migración VeriFactu" a cartera PYME (motor local de captación O1).
- **DAC8 dos olas**: ola 1 activa (exchanges españoles, 172/173, avisos ya) · ola 2 = datos 2026 declarados 2027 (extranjeros; Bitget aquí). Verificar orden ministerial de modelos antes de comunicar plazos a clientes.

## INPUTS QUE NINGÚN ZIP PUEDE CONTENER (viven en Diego)
1. Fase 0 registrada en Horizonte (texto listo en GUIA §5.2) — SIN HACER.
2. Horas reales/semana próximos 3 meses — SIN RESPONDER (se planifica C1 con supuesto de 5 h/sem hasta corrección).
3. Decisión Renta 2025 (punto 9 del menú).

## AMPLIACIÓN 2026-07-14 (noche V)
10. **Score de confianza** en el informe (checks reales: guards+G7+%auto+flags+versiones → confianza global derivada).
11. **Orquestador post-informe**: `ejecutar.py <expediente>` — extraer motor a módulo con suite verde antes/después; notebook queda para depuración.

## ⚡ CAMINO CRÍTICO (auditoría anti-sobreingeniería 2026-07-14, cierre)
El Día 3 se remata con SOLO estos 4 pasos, en orden: (1) resolver hallazgo SEI (re-export o excepción documentada) → (2) checklist onboarding v1.0 con cláusula de responsabilidad → (3) INFORME de dos capas (incluye score de confianza: 30 min dentro del propio informe) + hash al manifest → (4) decisión Renta 2025 de Diego + bitácora de cierre. TODO lo demás del menú (orquestador, ampliaciones de catálogo, G8, etc.) queda DETRÁS de esta línea: se evalúa después, con regla 10, sin excepciones.
