# Flujo de trabajo real — cuánto tarda cada cosa, y por qué importa

**Qué es este fichero, y por qué existe.** El 15-09-2026, en la misma sesión
local del cuadre 303, una revisión externa del proyecto señaló un hueco real:
*"¿qué fracción de tus horas facturables se va en lo que el motor sí puede
hacer? Si la aritmética y la identidad de facturas son el 8% de tu tiempo, un
motor perfecto tiene un techo del 8%. Ese dato no está en ningún sitio del
repositorio y es el único que decide si todo esto merece la pena."*

Diego respondió con una descripción detallada de su flujo real, incluida una
medición que ya había hecho **al principio del proyecto** sobre un lote de 30
facturas — y que nunca había quedado escrita en ningún fichero. Se buscó antes
de escribir esto (`grep` sobre todo el repositorio, "18,5 minutos", "4
minutos", "30 facturas", "albaranes": ningún resultado) para confirmar que de
verdad no estaba, no por costumbre.

**Lo que SÍ ya estaba resuelto en el diseño**, y por eso no aparece como hueco
aquí: la captura de varios tipos de IVA en una misma factura (`tramos_iva`,
ya en `captura_orquestador.py` y `contrato_datos.py`).

---

## 1. El único lote cronometrado hasta hoy: 30 facturas

| Paso | Tiempo | Nota |
|---|---|---|
| Ordenar por proveedor (mesa física) | ~3 min | Depende del nº de proveedores distintos en el paquete |
| Fotografiar (para OCR) | ~4 min | — |
| Contabilizar en ContaPlus | ~18,5 min | La parte más pesada, con diferencia |
| **Total** | **~25,5 min / 30 facturas** | **≈ 51 segundos por factura**, de media |

Dentro de los ~18,5 minutos de contabilizar, sin desglose por sub-tarea
todavía, viven estas otras:

- **Cliente o proveedor nuevo** (~2 min, solo cuando aparece uno): detectar el
  tipo (cliente / proveedor / acreedor) y decidir la cuenta contable.
- **Identificar el tipo de gasto** (tiempo variable, no cronometrado aparte):
  suministro, comisión bancaria, compra de mercaderías, conservación y
  reparación, servicios profesionales independientes, mobiliario... cruzado
  con el PGC. Con un proveedor ya conocido es casi automático por
  experiencia; con uno nuevo o un gasto atípico, no.
- **Sumar bases con varios tipos de IVA a mano**, cuando la factura no trae
  el desglose ya hecho — para poner el total en el asiento y luego
  desglosarlo dentro del programa de facturación. (Hay fotos de ejemplo de
  esto compartidas en su momento fuera de este repositorio; no se han vuelto
  a localizar. Si aparecen, añadir aquí como referencia.)

> ⚠️ **Este es un solo lote, de un momento concreto.** No se generaliza a
> "51 segundos por factura siempre" — varía por cliente, por volumen de
> proveedores, por cuánto desglose trae ya la factura. Sirve como primer
> punto de referencia real, no como promedio del despacho.

---

## 2. Todo lo que rodea esa cronometración, sin medir todavía

### 2.1 La recogida de la factura — el paso más variable, y el menos medible

No hay un único canal. Según el cliente:

- Diego va personalmente a por ella.
- El cliente se la trae en persona.
- Se la manda por correo electrónico.
- Se descarga de alguna plataforma.
- **Un caso distinto de verdad:** algunos clientes son empresas que llevan
  su propia contabilidad y facturación, y solo le pasan a Diego los balances
  trimestrales para presentar los impuestos — aquí no hay factura que
  contabilizar en absoluto, es otro tipo de servicio.
- Otro caso distinto: clientes que mandan sus gastos y Diego confecciona
  él mismo las facturas de venta antes de contabilizarlas.

Ninguno de estos canales tiene un tiempo fijo, y ninguno es algo que un
motor de validación pueda acortar — es logística humana, no un dato que
verificar. Encaja en el **cubo 3** de `TECHO_Y_LIMITES.md` (depende de un
hecho del mundo, no de un dato disponible).

### 2.2 Separar el albarán de la factura

Depende del volumen de documentos que trae cada cliente cada trimestre, y no
todos incluyen el albarán junto a la factura. Diego señala que, la mayoría de
las veces, ya se detecta solo con hacer la foto (para el OCR) sin coste extra
de tiempo — así que probablemente no sea el cuello de botella que parecía.

**Candidato técnico, discutido y probado con datos inventados el mismo día
(no construido todavía):** un albarán casi siempre imprime la palabra
"ALBARÁN" y no "FACTURA" en el título. Probado con seis casos sintéticos
(`albaran puro`, `factura pura`, `combinado`, `ni uno ni otro`...): la regla
"si dice albarán y no dice factura → es un albarán" distingue bien los casos
normales.

> ⚠️ **Un matiz real que salió de la propia prueba, y es decisión de Diego,
> no técnica:** el **"albarán valorado"** (un albarán que SÍ lleva precios)
> a veces hace de factura informal. Diría "albarán" en el título pero podría
> necesitar tratarse como una factura real. **Sin resolver — pendiente de que
> Diego confirme si esto pasa con sus clientes y con qué frecuencia**, antes
> de construir nada sobre la regla simple.

No se ha añadido ningún guard todavía: es un candidato validado a nivel de
hipótesis, no una decisión de construir. Sigue la misma regla que el resto
del proyecto — no se añade sin un caso real que lo pida, y este SÍ lo tiene,
pero falta cerrar el matiz del albarán valorado primero.

### 2.3 Ordenar por proveedor antes de contabilizar

Ya cronometrado en el lote de 30 (~3 min) — se hace en una mesa física,
agrupando por proveedor, para poder usar siempre la misma cuenta contable de
cada uno al contabilizar. Depende del número de proveedores distintos que
traiga el paquete de ese cliente ese trimestre.

### 2.4 Detectar cliente/proveedor nuevo

Ya cronometrado dentro del lote (~2 min, solo cuando aparece uno nuevo).
Ocurre de dos formas: se detecta al ordenar el montón de facturas, o al
buscarlo en ContaPlus y descubrir que no está dado de alta.

### 2.5 Identificar el tipo de gasto

Sin cronometrar aparte todavía. Cruza con el PGC (suministros, comisiones
bancarias, compras de mercaderías, conservación y reparación, servicios
profesionales, mobiliario...). Con proveedores ya conocidos, casi intuitivo
por la experiencia acumulada; con uno nuevo o un gasto atípico, no.

**Esto es exactamente lo que `guard_cuenta_gasto_coherente` ya hace, como
validador** — aprende por cliente y por proveedor a qué cuenta va cada uno,
según el histórico. Convertirlo de "avisa si te desvías" a "te lo propone
cuando no lo sabes" es la extensión natural de algo que ya existe, no una
idea nueva que haya que diseñar desde cero.

---

## 3. Qué cubre el motor tal como está pensado, y qué no cubrirá nunca

| Tarea | ¿La cubre el motor/la cadena OCR→motor→importar? | Por qué |
|---|---|---|
| Sumar bases con varios tipos de IVA | Sí, ya diseñado (`tramos_iva`) | Dato estructurado, verificable |
| Identificar tipo de gasto (proveedor conocido) | Sí — extensión de `guard_cuenta_gasto_coherente` | Ya existe como validador, falta como proponente |
| Detectar cliente/proveedor nuevo | Parcialmente — el guard puede avisar de que no hay patrón histórico | La decisión de qué cuenta usar la primera vez sigue siendo del asesor |
| Separar albarán de factura | Probablemente sí, barato — candidato validado, con un matiz por resolver | Ver §2.2 |
| Recoger la factura (cualquier canal) | No, nunca | Cubo 3 — logística humana, no un dato |
| Clientes que solo pasan el balance trimestral | No aplica — no hay factura que contabilizar | Es otro tipo de servicio, no esta cadena |

---

## 4. Cómo seguir midiendo, sin pedir algo que no es sostenible

Un parte de horas de una semana completa se descartó explícitamente: varía
demasiado entre semanas, meses y trimestres para ser representativo.

**Lo que sí es sostenible, decidido el mismo día:** cronometrar 2-3 lotes más,
ya organizados como siempre (sin ningún trabajo extra, solo mirar el reloj al
empezar y al terminar cada paso), eligiendo lotes distintos entre sí:

- Un autónomo con pocos proveedores.
- Una S.L. con más volumen.
- Un lote con varias facturas de IVA mixto (varios tipos en una misma
  factura), si se puede identificar uno así de antemano.

Con eso, y no con una semana entera, se tiene la unidad económica real
(minutos por factura, por tipo de cliente, por tipo de factura) que decide si
el techo del motor es del 8% o del 40% — sin depender de que una semana
concreta sea representativa de todas.

**No es una tarea con fecha.** Se añade la próxima vez que Diego organice un
lote, de forma natural, sin agendar nada aparte.
