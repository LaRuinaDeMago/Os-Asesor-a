#!/usr/bin/env python3
"""validar_captura_historica.py — el primer numero real, con las facturas que YA
pasaron por una camara.

POR QUE ESTO IMPORTA MAS QUE NADA DE LO QUE HAY EN ESTE REPOSITORIO
-------------------------------------------------------------------
El motor se probo en su dia con ~91-95 facturas REALES fotografiadas. Si ese
fichero sigue en el disco, es lo unico del proyecto que ha recorrido la cadena
entera —papel, camara, lectura, motor— con datos de verdad.

Y hay algo mas: desde entonces el motor ha cambiado ENTERO. Contrato de datos,
25 guards, modelo fiscal ampliado, ocho falsos verdes cerrados. Asi que este
script no compara una cosa, compara TRES:

    lo que dijo el motor ANTIGUO   (la columna que ya trae el fichero)
    lo que dice el motor de HOY    (se recalcula aqui)
    lo que resulto ser CORRECTO    (si alguien lo anoto)

De ahi salen tres respuestas distintas, y las tres valen:

  1. Si hay veredicto humano  -> LA TASA DE ACIERTO REAL. El numero que decide
     el proyecto, con facturas de verdad. Es lo que se busca.

  2. Si NO hay veredicto humano -> sigue habiendo premio: las facturas donde el
     motor de hoy dice algo DISTINTO al de entonces. Esas son las que hay que
     mirar a mano, y son pocas. Convierte "revisar 95 facturas" en "revisar las
     12 que han cambiado", que es una tarde en vez de una semana.

  3. En los dos casos -> si el trabajo de estos dias ha mejorado algo o no.
     Un motor que cambia mucho y no mueve ningun veredicto no ha mejorado nada.

QUE HACE FALTA
--------------
Un CSV con las facturas capturadas. NO hace falta que tenga un formato concreto:
el script detecta las columnas solo y dice lo que ha encontrado antes de nada.
Si falta algo, lo dice; no adivina.

    python validar_captura_historica.py "ruta/al/fichero.csv"
    python validar_captura_historica.py "ruta.csv" --columna-humano CORRECTO

REGLA DE DATOS
--------------
El CSV tiene NIF y nombres reales. Este script:
  - se ejecuta en la maquina de Diego, no aqui;
  - emite RECUENTOS y PORCENTAJES en el agregado, que si puede subir;
  - manda el detalle a un fichero `_LOCAL` que Claude no abre jamas;
  - agrupa los errores por TIPO de excepcion, nunca por su mensaje.
"""
import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict

import motor_veredicto as mv

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA_AGREGADA = os.path.join(AQUI, "validacion_captura_agregado.json")
SALIDA_LOCAL = os.path.join(AQUI, "validacion_captura_LOCAL.csv")

VEREDICTOS = ("VERDE", "AMBAR", "ROJO")

# Nombres que suele tener cada cosa, para detectarlos sin preguntar.
PISTAS_MOTOR = ("veredicto", "semaforo", "semáforo", "color", "resultado_motor")
PISTAS_HUMANO = ("humano", "correcto", "real", "revisado", "validado", "diego",
                 "veredicto_final", "ok_asesor", "corregido")


#: Como se llama de verdad cada campo en un CSV que no ha hecho este proyecto.
#: ANADIDO 21-08-2026: el script decia "detecta las columnas solo" y solo lo
#: hacia con las dos columnas de veredicto. Los campos que el MOTOR consume se
#: buscaban con su nombre canonico exacto, asi que un fichero con la cabecera
#: "NIF" —en mayusculas, como lo escribe cualquiera— dejaba el campo MISSING y
#: sacaba el 100% de las facturas en AMBAR. El numero final no medía el motor:
#: medía que no se habian encontrado las columnas.
ALIAS_CAMPOS = {
    "nif": ("nif", "cif", "nif_proveedor", "nifproveedor", "dni", "nif/cif", "cif/nif"),
    "proveedor": ("proveedor", "nombre", "razon social", "razón social", "emisor",
                  "acreedor", "tercero"),
    "nº_documento": ("nº_documento", "n_documento", "num factura", "nº factura",
                     "numero factura", "num_factura", "documento", "factura",
                     "n factura", "nro factura"),
    "fecha_expedicion": ("fecha_expedicion", "fecha expedicion", "fecha expedición",
                         "fecha", "fecha factura", "f. factura"),
    "base_total": ("base_total", "base", "base imponible", "baseimpo", "b.imponible"),
    "iva_total": ("iva_total", "iva", "cuota iva", "cuota", "importe iva"),
    "total_factura": ("total_factura", "total", "importe total", "total factura",
                      "importe", "total_doc"),
    "irpf": ("irpf", "retencion", "retención", "ret."),
    "recargo_equivalencia": ("recargo_equivalencia", "recargo", "rec. equiv",
                             "recequiv", "recargo equivalencia"),
}


def mapear_campos(campos):
    """Devuelve {columna_del_fichero: campo_del_motor} y los criticos que faltan.

    No renombra a ciegas: si la columna YA se llama como el motor la espera, se
    respeta y no se toca. Solo traduce lo que haga falta, y lo declara por
    pantalla para que se vea de donde ha salido cada dato."""
    bajos = {c: c.lower().strip() for c in campos}
    traduccion, ya_usados = {}, set()
    for canonico, alias in ALIAS_CAMPOS.items():
        if canonico in campos:
            ya_usados.add(canonico)
            continue
        for col, bajo in bajos.items():
            if col in traduccion or col in ya_usados:
                continue
            if bajo in alias:
                traduccion[col] = canonico
                ya_usados.add(canonico)
                break
    return traduccion


def detectar_columna(campos, pistas, excluir=()):
    """Devuelve la primera columna cuyo nombre contenga alguna pista."""
    for c in campos:
        bajo = c.lower().strip()
        if c in excluir:
            continue
        if any(p in bajo for p in pistas):
            return c
    return None


def normalizar_veredicto(v):
    """'verde', 'VERDE ', 'ok', 'bien' -> VERDE. Devuelve None si no se reconoce."""
    if v is None:
        return None
    s = str(v).strip().upper()
    if not s:
        return None
    if s in VEREDICTOS:
        return s
    if s in ("OK", "BIEN", "CORRECTO", "SI", "SÍ", "V", "G", "GREEN"):
        return "VERDE"
    if s in ("MAL", "ERROR", "INCORRECTO", "NO", "R", "RED"):
        return "ROJO"
    if s in ("REVISAR", "DUDA", "A", "AMARILLO", "AMBER"):
        return "AMBAR"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="CSV de las facturas ya capturadas")
    ap.add_argument("--columna-motor", help="Columna con el veredicto que dio el motor entonces")
    ap.add_argument("--columna-humano", help="Columna con lo que resulto ser correcto")
    ap.add_argument("--maestro-json", help="Maestro de proveedores (NIF -> {titulo, cuenta})")
    ap.add_argument("--alta-anio", type=int, default=1990,
                    help="Ano de alta del cliente. Por defecto uno muy antiguo, para que "
                         "el guard de fecha no penalice por falta de dato de configuracion")
    args = ap.parse_args()

    if not os.path.exists(args.csv):
        print(f"No encuentro el fichero: {args.csv}")
        return 2

    # SEPARADOR — arreglado el 21-08-2026, lo destapo ensayo_retro_semaforo.py.
    # Excel en espanol exporta con PUNTO Y COMA, no con coma, asi que el fichero
    # de las 91 facturas tiene todas las papeletas de venir asi. Con el separador
    # equivocado, csv.DictReader no falla: devuelve UNA columna con la linea
    # entera dentro, y el script seguia adelante tan tranquilo hasta imprimir
    # "TASA DE ACIERTO: 0.0%" y "FALSOS VERDES: 0". Un numero que en realidad
    # significaba "no he podido leer nada", presentado como medicion.
    #
    # Es el falso verde por omision de siempre, cometido por el instrumento que
    # tiene que medirlo. Se elige el separador por el que MAS columnas produce en
    # la cabecera, que es como lo hace cualquiera a ojo.
    with open(args.csv, encoding="utf-8-sig", newline="") as f:
        cabecera = f.readline()
    sep = max((";", ",", "\t", "|"), key=lambda c: cabecera.count(c))
    if cabecera.count(sep) == 0:
        sep = ","
    with open(args.csv, encoding="utf-8-sig", newline="") as f:
        filas = list(csv.DictReader(f, delimiter=sep))
    if not filas:
        print("El CSV esta vacio.")
        return 2

    campos = list(filas[0].keys())
    if len(campos) < 2:
        print(f"El fichero se ha leido como UNA sola columna (separador probado: "
              f"'{sep}'). Eso no es un CSV que este script pueda usar, y seguir "
              f"daria numeros que solo miden que no se ha leido nada.")
        print(f"  cabecera encontrada: {cabecera[:120].strip()!r}")
        print("  Comprobar el separador real del fichero y volver a exportarlo.")
        return 2
    col_motor = args.columna_motor or detectar_columna(campos, PISTAS_MOTOR)
    col_humano = args.columna_humano or detectar_columna(
        campos, PISTAS_HUMANO, excluir={col_motor} if col_motor else ())

    # ---- Lo primero: decir lo que se ha encontrado. Sin adivinar nada. ----
    print("=" * 68)
    print("VALIDACION CON FACTURAS QUE YA PASARON POR UNA CAMARA")
    print("=" * 68)
    print(f"  filas leidas             : {len(filas)}")
    print(f"  columnas                 : {len(campos)}  (separador '{sep}')")
    print(f"  veredicto del motor      : {col_motor or '*** NO ENCONTRADO ***'}")
    print(f"  veredicto humano         : {col_humano or 'no hay (ver mas abajo, sigue habiendo premio)'}")
    traduccion = mapear_campos(campos)
    if traduccion:
        print("  columnas traducidas al nombre que usa el motor:")
        for col, canonico in sorted(traduccion.items(), key=lambda kv: kv[1]):
            print(f"      {col!r:<22} -> {canonico}")
    disponibles = set(campos) | set(traduccion.values())
    faltan = [c for c in ("nif", "total_factura", "fecha_expedicion") if c not in disponibles]
    if faltan:
        print(f"  ⚠ campos que el motor necesita y NO estan: {faltan}")
        print("    (se evaluara igual; el contrato de datos los marcara MISSING —")
        print("     pero OJO: con criticos ausentes, lo que se mida NO mide el")
        print("     motor, mide que no se han encontrado las columnas)")
    print()

    maestro = {}
    if args.maestro_json and os.path.exists(args.maestro_json):
        try:
            maestro = json.load(open(args.maestro_json, encoding="utf-8"))
            print(f"  maestro de proveedores   : {len(maestro)} entradas")
        except Exception as e:
            print(f"  maestro no cargado ({type(e).__name__})")

    # ---- Reevaluar con el motor de HOY ----
    vistos = set()
    hoy = Counter()
    antes = Counter()
    cambios = Counter()
    guards_no_ok = Counter()
    errores = Counter()
    detalle = []
    aciertos_hoy = fallos_hoy = 0
    aciertos_antes = fallos_antes = 0
    falsos_verdes_hoy = []
    matriz = defaultdict(Counter)
    # ANADIDO 27-08-2026 (hallazgo verificado de Diego): igual que
    # retro_semaforo.py, este script pasaba {}, {}, {} para las tres caches
    # de historial en CADA factura -- nunca se acumulaban entre filas, asi
    # que guard_importe_atipico, guard_estructura_reconocida y guard_
    # secuencia_documental_proveedor nunca podian activarse de verdad.
    # Crecen segun se avanza, se actualizan DESPUES de evaluar cada fila
    # (nunca antes: el historico de una factura son solo las anteriores).
    historico_acumulado = {}
    formato_acumulado = {}
    secuencia_acumulada = {}

    for i, fila_cruda in enumerate(filas):
        v_antes = normalizar_veredicto(fila_cruda.get(col_motor)) if col_motor else None
        v_humano = normalizar_veredicto(fila_cruda.get(col_humano)) if col_humano else None
        # La traduccion AÑADE la clave canonica, no borra la original: si el
        # fichero trae algo mas, sigue estando y nadie pierde informacion.
        fila = dict(fila_cruda)
        for col, canonico in traduccion.items():
            if fila.get(col) not in (None, ""):
                fila[canonico] = fila_cruda[col]
        try:
            v_hoy, motivo, guards = mv.evaluar_fila_v4(
                fila, vistos, historico_acumulado, formato_acumulado,
                secuencia_acumulada, maestro,
                alta_cliente_anio=args.alta_anio,
                nif_cliente_titular=None,
                ejercicio_tanda=None)
        except Exception as e:
            errores[type(e).__name__] += 1
            continue
        finally:
            mv.actualizar_caches_historicas(
                historico_acumulado, formato_acumulado,
                secuencia_acumulada, fila)

        hoy[v_hoy] += 1
        for g, (estado, _) in guards.items():
            if estado not in ("OK", "NO_APLICA"):
                guards_no_ok[f"{g}={estado}"] += 1

        if v_antes:
            antes[v_antes] += 1
            if v_antes != v_hoy:
                cambios[f"{v_antes} -> {v_hoy}"] += 1

        if v_humano:
            matriz[v_hoy][v_humano] += 1
            if v_hoy == v_humano:
                aciertos_hoy += 1
            else:
                fallos_hoy += 1
                # El caso que decide el proyecto: el motor dijo VERDE y estaba mal.
                if v_hoy == "VERDE":
                    falsos_verdes_hoy.append(i)
            if v_antes:
                if v_antes == v_humano:
                    aciertos_antes += 1
                else:
                    fallos_antes += 1

        detalle.append({"fila": i, "antes": v_antes or "", "hoy": v_hoy,
                        "humano": v_humano or "", "motivo": motivo[:160],
                        "cambio": "SI" if (v_antes and v_antes != v_hoy) else ""})

    def pct(n, d):
        return round(n * 100.0 / d, 2) if d else 0.0

    n = sum(hoy.values())
    print("VEREDICTOS CON EL MOTOR DE HOY:")
    for v in VEREDICTOS:
        if hoy.get(v):
            print(f"    {v:<8} {hoy[v]:>5}   {pct(hoy[v], n):>6}%")

    if col_motor:
        print("\nQUE HA CAMBIADO RESPECTO AL MOTOR DE ENTONCES:")
        if not cambios:
            print("    NADA. Ningun veredicto ha cambiado.")
            print("    Eso significa que todo el trabajo de estos dias no ha movido")
            print("    ni un caso real. Es un resultado, y hay que tomarselo en serio.")
        else:
            for k, c in cambios.most_common():
                print(f"    {k:<22} {c:>5}")
            print(f"    -> {sum(cambios.values())} facturas de {n} cambian de veredicto")
            print("    ESTAS son las que hay que mirar a mano. Son pocas y valen mucho.")

    if col_humano:
        total_juzgadas = aciertos_hoy + fallos_hoy
        print("\n" + "=" * 68)
        print("EL NUMERO QUE DECIDE EL PROYECTO")
        print("=" * 68)
        print(f"  facturas con veredicto humano : {total_juzgadas}")
        if total_juzgadas == 0:
            # ANADIDO 21-08-2026. Antes imprimia "TASA DE ACIERTO: 0.0%" y
            # "FALSOS VERDES: 0" con cero facturas juzgadas. Los dos numeros son
            # falsos y ademas tranquilizadores: cero falsos verdes suena a
            # perfecto y significa que no se ha mirado ni uno. Es exactamente el
            # OK-por-omision que el motor tiene prohibido, en la herramienta que
            # deberia detectarlo.
            print("  >> NO SE PUEDE CALCULAR NINGUNA TASA.")
            print("     La columna de veredicto humano existe, pero ninguna fila")
            print("     trae un valor reconocible (VERDE/AMBAR/ROJO, OK/MAL,")
            print("     BIEN/REVISAR...). Sin eso no hay con que comparar.")
            print("     CERO no es el resultado: es la ausencia de resultado.")
        elif faltan:
            print(f"  >> LA TASA NO SE PUBLICA: faltaban campos criticos {faltan}.")
            print("     Saldria un numero, y ese numero mediria la lectura del")
            print("     fichero, no el motor. Publicarlo seria peor que no tenerlo.")
            print(f"     (para referencia interna: {pct(aciertos_hoy, total_juzgadas)}% "
                  f"sobre {total_juzgadas} facturas mal leidas)")
        else:
            print(f"  >> TASA DE ACIERTO (hoy)      : {pct(aciertos_hoy, total_juzgadas)}%")
            if aciertos_antes or fallos_antes:
                print(f"     tasa de acierto (entonces) : {pct(aciertos_antes, aciertos_antes + fallos_antes)}%")
            print(f"  >> FALSOS VERDES              : {len(falsos_verdes_hoy)}"
                  f"   ({pct(len(falsos_verdes_hoy), total_juzgadas)}%)")
            print("     (el motor dijo VERDE y el humano dijo que estaba mal)")
        print("\n  matriz motor(hoy) x humano:")
        print(f"    {'':10}" + "".join(f"{h:>10}" for h in VEREDICTOS))
        for m in VEREDICTOS:
            if matriz.get(m):
                print(f"    {m:<10}" + "".join(f"{matriz[m].get(h, 0):>10}" for h in VEREDICTOS))
    else:
        print("\n" + "-" * 68)
        print("NO hay columna de veredicto humano, asi que la tasa de acierto no se")
        print("puede calcular: el fichero dice lo que el motor opino, no lo que era")
        print("correcto. Para tenerla, anade una columna con el veredicto real y")
        print("vuelve a ejecutar con --columna-humano.")
        print("Mientras tanto, la lista de cambios de arriba ya es la cola de")
        print("revision prioritaria, y es mucho mas corta que el fichero entero.")

    if guards_no_ok:
        print("\nGUARDS QUE MAS SALTAN (donde esta el ruido):")
        for g, c in guards_no_ok.most_common(10):
            print(f"    {g:<45} {c:>5}")

    if errores:
        print("\nINCIDENCIAS (por tipo de excepcion, nunca por mensaje):")
        for k, c in errores.most_common():
            print(f"    {k:<40} {c:>5}")

    agregado = {
        "version": "validacion_captura v1 (20-08-2026)",
        "filas": len(filas),
        "evaluadas": n,
        "columna_motor_detectada": col_motor,
        "columna_humano_detectada": col_humano,
        "veredictos_hoy": dict(hoy),
        "veredictos_entonces": dict(antes),
        "cambios": dict(cambios),
        "guards_no_ok": dict(guards_no_ok.most_common(20)),
        "errores_por_tipo": dict(errores),
    }
    if col_humano:
        total_juzgadas = aciertos_hoy + fallos_hoy
        agregado["acierto"] = {
            "juzgadas": total_juzgadas,
            "pct_acierto_hoy": pct(aciertos_hoy, total_juzgadas),
            "pct_acierto_entonces": pct(aciertos_antes, aciertos_antes + fallos_antes),
            "falsos_verdes": len(falsos_verdes_hoy),
            "pct_falsos_verdes": pct(len(falsos_verdes_hoy), total_juzgadas),
            "matriz": {m: dict(c) for m, c in matriz.items()},
        }

    with open(SALIDA_AGREGADA, "w", encoding="utf-8") as f:
        json.dump(agregado, f, ensure_ascii=False, indent=2)
    # El detalle lleva el numero de fila, no el contenido: sirve para localizar
    # la factura en el CSV original sin duplicar ni un dato identificable.
    with open(SALIDA_LOCAL, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["fila", "antes", "hoy", "humano", "cambio", "motivo"])
        w.writeheader()
        w.writerows(detalle)

    print(f"\nAgregado (se puede subir) : {SALIDA_AGREGADA}")
    print(f"Detalle (NO sube, _LOCAL) : {SALIDA_LOCAL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
