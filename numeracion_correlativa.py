#!/usr/bin/env python3
"""numeracion_correlativa.py — motor de numeración correlativa para el módulo
de facturas EMITIDAS (distinto del motor de veredicto, que valida facturas
RECIBIDAS). Primera pieza de ese módulo, construida en Cloud, sin datos
reales, mientras se resuelve el resto (ver PROJECT_STATUS.md, entrada del
27-08-2026 sobre este módulo).

DE DONDE SALE ESTO
--------------------
Hoy (a mano, en Excel, a partir de lo que el cliente manda por WhatsApp) el
despacho emite facturas de venta con numeración correlativa por serie, para
poder exportarlas después a FactuSOL. VeriFactu exige que esa numeración sea
correlativa y SIN HUECOS por serie — es uno de los pilares de la integridad
que el hash encadenado está diseñado para detectar si se rompe. Un hueco o
un duplicado no es un detalle estético: es un fallo de cumplimiento real.

QUE HACE ESTE MODULO, Y QUE NO HACE (todavía)
------------------------------------------------
SÍ: decide, dado el histórico de números ya usados en una serie, cuál es el
próximo número válido, y detecta huecos o duplicados antes de que lleguen a
FactuSOL. Es lógica pura, sin ningún dato de cliente real -- funciona igual
de bien con un histórico sintético que con uno real.

NO hace (y no es descuido, es la frontera de datos, ver .claude/rules/datos.md):
- No lee mensajes de WhatsApp. Interpretar el mensaje de un cliente real para
  extraer importe/concepto es trabajo que el modelo tiene que VER para hacer
  -- eso está detrás de la puerta del DPA, igual que leer una foto de factura.
- No conoce el formato exacto de exportación de FactuSOL. Se ha intentado
  documentar por fuentes públicas y no ha sido posible verificarlo con
  suficiente confianza (páginas bloqueadas o en PDF de imagen, sin texto
  extraíble) -- la regla de este proyecto es no adivinar un formato de datos,
  así que el escritor de exportación se construye cuando haya una plantilla
  real de FactuSOL (vacía, sin datos de cliente) para verificar contra ella.
- No implementa el hash encadenado, el QR ni el envío a AEAT de VeriFactu.
  Si FactuSOL es el software certificado VeriFactu del despacho (pendiente de
  confirmar con Diego), esa parte la hace FactuSOL: nuestro trabajo es
  entregarle datos correctos, no reimplementar su certificación.

REGLA DE DATOS: este módulo no toca nunca un NIF, nombre o importe real. Los
números de serie y las cantidades son enteros sin identidad — es "el sitio
3 de la serie A", no "la factura de tal cliente".
"""


def siguiente_numero(numeros_usados, numero_inicial=1):
    """Dado el conjunto de números ya usados en UNA serie, devuelve el
    próximo número correlativo válido. numero_inicial es configurable porque
    no todas las series empiezan en 1 (una serie puede arrancar donde lo
    dejó un sistema anterior) -- no se supone 1 sin que alguien lo confirme."""
    if not numeros_usados:
        return numero_inicial
    return max(numeros_usados) + 1


def detectar_huecos(numeros_usados, numero_inicial=1):
    """Devuelve la lista de números que FALTAN entre numero_inicial y el
    máximo usado -- una serie correlativa sin huecos no debe tener ninguno.
    Si aparece uno, es exactamente el tipo de fallo que VeriFactu penaliza:
    una factura que se saltó, o que se anuló borrando el número en vez de
    emitir una rectificativa."""
    if not numeros_usados:
        return []
    return sorted(set(range(numero_inicial, max(numeros_usados) + 1)) - set(numeros_usados))


def validar_numero_nuevo(numero_propuesto, numeros_usados, numero_inicial=1):
    """Veredicto sobre un número que se propone usar A CONTINUACIÓN, con el
    mismo principio que el motor de veredicto: nunca un OK que no se ha
    comprobado. Tres formas de fallar, cada una con su motivo explícito:
    - ya se usó ese número en esta serie (duplicado)
    - es menor que el siguiente correlativo esperado, pero no está usado
      (hueco hacia atrás: alguien se salta un número que no llegó a emitirse)
    - es mayor que el siguiente correlativo esperado (hueco hacia adelante:
      salta números que deberían emitirse antes)
    """
    esperado = siguiente_numero(numeros_usados, numero_inicial)
    if numero_propuesto in numeros_usados:
        return ("FALLO", f"el numero {numero_propuesto} ya esta usado en esta serie "
                          "-- no se puede repetir, es un duplicado")
    if numero_propuesto < esperado:
        return ("FALLO", f"el numero {numero_propuesto} deja un hueco hacia atras: "
                          f"el correlativo esperado es {esperado}, y {numero_propuesto} "
                          "no esta entre los ya usados")
    if numero_propuesto > esperado:
        return ("FALLO", f"el numero {numero_propuesto} salta por delante del correlativo "
                          f"esperado ({esperado}) -- deja un hueco que VeriFactu no permite")
    return ("OK", f"{numero_propuesto} es exactamente el siguiente correlativo de la serie")


def validar_ledger(facturas, numero_inicial=1):
    """Recorre una lista de facturas ya registradas -- cada una un dict con
    'serie' y 'numero' -- y devuelve, por serie, los huecos y duplicados que
    tenga. Es el chequeo de salud del histórico completo antes de dar por
    buena una serie, no solo del último número emitido.

    facturas: lista de {'serie': str, 'numero': int}. Nunca un dato de
    cliente -- esta función no sabe ni necesita saber a quién se le
    facturó."""
    from collections import defaultdict, Counter

    numeros_por_serie = defaultdict(list)
    for f in facturas:
        numeros_por_serie[f['serie']].append(f['numero'])

    informe = {}
    for serie, numeros in numeros_por_serie.items():
        conteo = Counter(numeros)
        duplicados = sorted(n for n, veces in conteo.items() if veces > 1)
        huecos = detectar_huecos(set(numeros), numero_inicial)
        informe[serie] = {
            'n_facturas': len(numeros),
            'huecos': huecos,
            'duplicados': duplicados,
            'sano': not huecos and not duplicados,
        }
    return informe
