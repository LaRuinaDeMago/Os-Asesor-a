# CATÁLOGO DE EVENTOS v1.0 — vocabulario canónico (2026-07-14)
**Frontera de capas (oficial): el ADAPTADOR traduce y VALORA (tipos EUR, regla del mayor) · el SCHEMA lleva euros ya resueltos · el MOTOR solo imputa lotes y calcula. Tres responsabilidades, cero fugas.**

## Implementados (con tratamiento firmado)
| Evento | Tratamiento | CRIT |
|---|---|---|
| COMPRA | Alta de lote: coste = importe + gastos inherentes | 001, 003 |
| VENTA | Transmisión FIFO: VT = importe − gastos | 001, 003 |
| PERMUTA_OUT / PERMUTA_IN | Hecho imponible; valor = MAYOR de los dos mercados; encadenamiento del coste; fecha = ejecución | 002, 005 |

## Reservados (nombre hoy, implementación con el primer caso real — regla 7)
| Evento | Destino fiscal ya firmado | Nota |
|---|---|---|
| RECOMPENSA_STAKING | RCM en especie, base ahorro, devengo al disponer | CRIT-004a |
| PERMUTA_STAKING_LIQUIDO | Dos permutas (ida/vuelta) | CRIT-004b |
| AIRDROP | Ganancia sin transmisión, BASE GENERAL | CRIT-004c |
| TRANSFER_INTERNO | No imponible; exige coste de origen (flag si falta) | trazabilidad |
| RETIRADA_EXTERNA | No imponible en sí; abre trazabilidad a wallet | trazabilidad |
| FEE_BRIDGE | `sin_respaldo_firme` → advertencia + criterio conservador | CRIT-005 sub |
| PERDIDA_PLATAFORMA | Regla 14.2.k, base general | CRIT-006 |
| UNKNOWN | Cola de revisión humana obligatoria (confidence bajo) | regla 9 |
Fuera de alcance actual (clase de activo, no evento): NFT, derivados/futuros, margin — análisis específico si algún expediente los trae (CRIT-001 nota de alcance).
