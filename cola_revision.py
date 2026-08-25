#!/usr/bin/env python3
"""cola_revision.py — convertir "91 facturas" en "una tarde de trabajo".

EL HUECO QUE CIERRA
-------------------
El motor separa los AMBAR en dos clases desde el 20-08-2026, y su propio codigo
explica para que sirve la distincion:

    "La cola de revision se ordena por TIPO DE TRABAJO, no por orden de llegada.
     Buscar un dato y aplicar criterio no se hacen igual ni seguidos."

Esa cola no existia. La clasificacion la produce `motor_veredicto.py` y no la lee
NADIE: ni el orquestador, ni el retro-semaforo, ni la validacion historica
(comprobado con grep el 21-08-2026). Es la cuarta vez en el proyecto que aparece
el mismo patron —una pieza correcta, probada y sin conectar— y por eso este
script es pequeno: lo que faltaba no era la idea, era el cable.

LA IDEA, QUE NO ES ORDENAR UNA HOJA DE CALCULO
-----------------------------------------------
Ordenar el CSV por veredicto se hace en Excel en diez segundos y no sirve de
mucho. Lo que cambia el dia es agrupar por CAUSA:

    "23 facturas: falta el desglose por tipos de IVA"

no son 23 tareas, es UNA: cambiar lo que pide la captura y volver a pasarlas. Una
cola ordenada por factura esconde eso; una ordenada por causa lo pone delante.

Por eso el orden no es por gravedad, es por CUANTAS FACTURAS DESBLOQUEA CADA
ACCION. La causa que aparece 23 veces va antes que la que aparece una, aunque la
de una sea mas grave: arreglar la primera son 23 facturas menos en la cola.

LOS TRES MONTONES, QUE SON TRES TRABAJOS DISTINTOS
---------------------------------------------------
    ROJO           CORREGIR. Hay un error localizado. Se arregla y se repasa.
    [FALTA DATO]   BUSCAR o VERIFICAR. Falta algo o algo se contradice. Casi
                   siempre son lotes: la misma carencia en muchas facturas.
    [CRITERIO]     DECIDIR. Todo cuadra y hace falta un juicio profesional que
                   el motor no puede tomar.

Y hay un motivo para no mezclarlos que va mas alla de la comodidad: las
decisiones de [CRITERIO] son las etiquetas que mas valen del proyecto. Son justo
los casos donde el motor no puede decidir, asi que aprender de ellas es lo unico
que mueve la frontera de lo automatizable (DISENO_APRENDIZAJE.md). Perdidas
dentro de un monton de "revisar", no se aprenden.

REGLA DE DATOS
--------------
El agregado son RECUENTOS y NOMBRES DE GUARD: se puede subir y se puede ensenar.
El detalle —que facturas concretas— va a un `_LOCAL` que Claude no abre jamas.
Los motivos llevan importes, asi que solo aparecen en el detalle, nunca en el
agregado.

Uso:
    python cola_revision.py veredicto.csv
    python cola_revision.py veredicto.csv --detalle cola_LOCAL.csv
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict

# Sin esto, una consola de Windows en cp1252 revienta al imprimir el aviso de
# privacidad (⚠️). Mismo patron que scripts/privacy_scan.py. hasattr() porque
# sys.stdout no siempre es un TextIOWrapper real (ver test_motor_veredicto.py:
# StringIO no tiene .reconfigure()).
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA_AGREGADA = os.path.join(AQUI, "cola_revision_agregado.json")

#: Que hacer con cada causa, en el idioma del que va a hacer el trabajo. No es
#: cosmetica: "aritmetica_base_tipo" no le dice a nadie que tiene que hacer.
QUE_HACER = {
    "integridad_datos": "Volver a capturar: hay campos criticos ilegibles o ausentes",
    "aritmetica_base_tipo": "Conseguir el DESGLOSE por tipos de IVA de la factura",
    "suma_tramos": "Conseguir el DESGLOSE por tipos de IVA de la factura",
    "cuadre_total": "Revisar los importes: base + IVA no da el total declarado",
    "naturaleza_operacion": "Revisar el regimen de IVA declarado (exenta, ISP, intracomunitaria)",
    "recargo_equivalencia": "Revisar el recargo de equivalencia",
    "nif_digito_control": "Corregir el NIF: el digito de control no es valido",
    "nif_casa_historico": "DAR DE ALTA al proveedor en el maestro (o confirmar que es nuevo)",
    "anti_duplicado": "Comprobar si la factura ya estaba contabilizada",
    "fecha_posterior_alta": "Revisar la fecha: es anterior al alta del cliente",
    "ejercicio_coherente": "Decidir que hacer con una factura de otro ejercicio",
    "vencimiento_coherente": "Revisar el vencimiento contra el plazo habitual del proveedor",
    "estructura_reconocida": "Comprobar el nº de documento: no se parece a los de este proveedor",
    "secuencia_documental_proveedor": "Comprobar el nº de documento: se sale de la serie del proveedor",
    "importe_atipico": "Comprobar el importe: se sale de lo habitual de este proveedor",
    "sentido_compra_venta": "DECIDIR si es compra o venta (el emisor podria ser el propio cliente)",
    "signo_efectivo": "Comprobar si es un abono o una rectificativa",
    "retencion_vs_error": "Revisar la retencion de IRPF",
    "cuenta_gasto_coherente": "DECIDIR la cuenta de gasto: no es la habitual de este proveedor",
    "tipo_operacion_especial": "DECIDIR: inmovilizado, amortizacion u operacion intracomunitaria",
    "tipo_producto_iva_semantico": "Informar la categoria de producto para poder validar el tipo",
    "confianza_por_campo": "Volver a capturar: la lectura de algun campo critico es dudosa",
    "confianza_captura": "Volver a capturar: la lectura de la factura es dudosa",
    "triangulacion_identidad": "Comprobar la identidad del emisor (NIF del cuerpo vs NIF del margen)",
    "doble_lectura_total": "Comprobar el total: las dos lecturas del documento no coinciden",
    "patron_cartera": "Consultar el patron de la cartera para este proveedor",
}

MONTONES = (
    ("ROJO", "CORREGIR — hay un error localizado"),
    ("[FALTA DATO]", "BUSCAR o VERIFICAR — falta un dato o algo se contradice"),
    ("[CRITERIO]", "DECIDIR — todo cuadra y hace falta criterio profesional"),
)

#: Separadores con los que el motor encadena varias causas en un mismo motivo.
#: Ver calcular_veredicto_v4: el ROJO usa " | y N mas: " y luego "; ", y el
#: barrido de NO_COMPROBADO usa "; " a secas.
SEPARADORES = re.compile(r'\s*\|\s*y \d+ mas:\s*|;\s*')
PATRON_GUARD = re.compile(r'^([a-z_][a-z0-9_]*):')


def monton_de(veredicto, motivo):
    if veredicto == "ROJO":
        return "ROJO"
    if veredicto != "AMBAR":
        return None
    if motivo.startswith("[CRITERIO]"):
        return "[CRITERIO]"
    if motivo.startswith("[FALTA DATO]"):
        return "[FALTA DATO]"
    # Un AMBAR sin etiqueta es un hueco del motor, no de la factura. Se declara
    # en vez de repartirlo a ojo en un monton cualquiera.
    return "AMBAR SIN CLASIFICAR"


def causas_de(motivo):
    """Los guards que han saltado, SIN el detalle. El detalle lleva importes.

    Se hace quitando primero la etiqueta de clase y partiendo por los
    separadores, en vez de con una sola expresion regular que lo intente todo a
    la vez. La primera version era esa expresion, y fallaba justo en el caso mas
    comun —el guard va pegado a "[FALTA DATO] "— asi que TODOS los AMBAR salian
    como "sin causa identificable" y la cola no agrupaba nada. Un fallo silencioso
    y comodo: el script terminaba en verde y su salida no servia."""
    texto = (motivo or "").strip()
    for etiqueta in ("[CRITERIO]", "[FALTA DATO]"):
        if texto.startswith(etiqueta):
            texto = texto[len(etiqueta):].strip()
            break
    causas = []
    for parte in SEPARADORES.split(texto):
        m = PATRON_GUARD.match(parte.strip())
        if m:
            causas.append(m.group(1))
    return causas or ["(sin causa identificable)"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="Salida del orquestador (veredicto.csv)")
    ap.add_argument("--columna-veredicto", default="VEREDICTO")
    ap.add_argument("--columna-motivo", default="MOTIVO")
    ap.add_argument("--detalle", metavar="RUTA",
                    help="CSV con QUE facturas caen en cada causa. Lleva datos de "
                         "facturas concretas: usar un nombre con _LOCAL.")
    args = ap.parse_args()

    if not os.path.exists(args.csv):
        print(f"No encuentro el fichero: {args.csv}")
        return 2
    with open(args.csv, encoding="utf-8-sig", newline="") as f:
        cabecera = f.readline()
    sep = max((";", ",", "\t", "|"), key=lambda c: cabecera.count(c))
    with open(args.csv, encoding="utf-8-sig", newline="") as f:
        filas = list(csv.DictReader(f, delimiter=sep))
    if not filas:
        print("El CSV esta vacio.")
        return 2
    if args.columna_veredicto not in filas[0]:
        print(f"No hay columna '{args.columna_veredicto}'. Columnas: {list(filas[0])[:8]}")
        return 2

    por_monton = defaultdict(Counter)
    detalle = defaultdict(list)
    veredictos = Counter()
    for i, fila in enumerate(filas, start=2):     # 2 = primera fila de datos
        v = (fila.get(args.columna_veredicto) or "").strip().upper()
        motivo = fila.get(args.columna_motivo) or ""
        veredictos[v] += 1
        monton = monton_de(v, motivo)
        if monton is None:
            continue
        for causa in causas_de(motivo):
            por_monton[monton][causa] += 1
            detalle[(monton, causa)].append((i, fila))

    total = sum(veredictos.values())
    print("=" * 70)
    print("COLA DE REVISION — ordenada por TRABAJO, no por orden de llegada")
    print("=" * 70)
    print(f"  facturas               : {total:,}")
    for v, n in veredictos.most_common():
        print(f"    {v or '(sin veredicto)':<22} {n:>6,}   {n*100.0/total:>5.1f}%")
    print()

    # EMPIEZA POR AQUI. Los tres montones se imprimen en orden fijo porque son
    # tres trabajos distintos y no se hacen entremezclados — pero eso escondia la
    # respuesta a la pregunta practica: .por cual empiezo? La accion que mas
    # facturas quita de la cola puede estar en cualquiera de los tres, y con
    # frecuencia esta en [FALTA DATO], que es el que va en medio.
    todas = [(n, causa, monton) for monton, causas in por_monton.items()
             for causa, n in causas.items()]
    if todas:
        n, causa, monton = max(todas, key=lambda x: x[0])
        print("=" * 70)
        print("EMPIEZA POR AQUI — la accion que mas facturas quita de la cola:")
        print(f"    {n} facturas  ·  {QUE_HACER.get(causa, causa)}")
        print(f"    (monton: {monton};  causa: {causa})")
        if n > 1:
            print(f"    No son {n} tareas: es UNA. Se arregla una vez y se repasan.")
        print("=" * 70)
        print()

    acciones = 0
    for monton, titulo in MONTONES:
        causas = por_monton.get(monton)
        if not causas:
            continue
        n_fact = sum(causas.values())
        print("-" * 70)
        print(f"{titulo}   ({n_fact} apariciones, {len(causas)} acciones distintas)")
        print("-" * 70)
        # Por CUANTAS FACTURAS DESBLOQUEA, no por gravedad: la causa que sale 23
        # veces se arregla una vez y quita 23 de la cola.
        for causa, n in causas.most_common():
            acciones += 1
            que = QUE_HACER.get(causa, f"(causa sin traducir: {causa})")
            print(f"  {n:>5} facturas  ·  {que}")
            print(f"                    ({causa})")
        print()

    sin_clasificar = por_monton.get("AMBAR SIN CLASIFICAR")
    if sin_clasificar:
        print("-" * 70)
        print("AMBAR SIN ETIQUETA — hueco del MOTOR, no de la factura")
        print("-" * 70)
        for causa, n in sin_clasificar.most_common():
            print(f"  {n:>5} facturas  ·  {causa}")
        print("  Estos AMBAR salen sin [CRITERIO] ni [FALTA DATO]. No se reparten")
        print("  a ojo en un monton: se declaran, y se arregla el motor.")
        print()

    print(f"  >> {acciones} acciones distintas para {total} facturas.")
    print("     Ese es el numero que dice si la cola es una tarde o una semana.")

    agregado = {
        "version": "1.0",
        "facturas": total,
        "veredictos": dict(veredictos),
        # Solo nombres de guard y recuentos: ningun motivo, que llevan importes.
        "por_monton": {m: dict(c) for m, c in por_monton.items()},
        "acciones_distintas": acciones,
    }
    with open(SALIDA_AGREGADA, "w", encoding="utf-8") as f:
        json.dump(agregado, f, ensure_ascii=False, indent=2)
    print()
    print(f"Agregado (se puede subir)  : {SALIDA_AGREGADA}")

    if args.detalle:
        ruta = os.path.abspath(args.detalle)
        campos = ["MONTON", "ACCION", "CAUSA", "FILA_CSV"] + list(filas[0].keys())
        with open(ruta, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=campos)
            w.writeheader()
            for (monton, causa), items in sorted(
                    detalle.items(), key=lambda kv: -len(kv[1])):
                for n_fila, fila in items:
                    w.writerow({"MONTON": monton, "CAUSA": causa,
                                "ACCION": QUE_HACER.get(causa, ""),
                                "FILA_CSV": n_fila, **fila})
        print(f"Detalle (NO sube, _LOCAL)  : {ruta}")
        if "_LOCAL" not in os.path.basename(ruta):
            print("    ⚠️  Lleva datos de facturas concretas y su nombre no dice")
            print("        _LOCAL. Renombrarlo: .gitignore protege *_LOCAL.*")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
