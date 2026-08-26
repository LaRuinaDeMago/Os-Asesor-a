#!/usr/bin/env python3
"""diag_baseimpo.py — ¿cuantas veces viene relleno BASEIMPO de verdad?

DE DONDE SALE ESTA PREGUNTA
-----------------------------
`diag_coherencia_303.py` midio el 26-08-2026 que en `303_LOCAL.json`:

  - 536 de 787 celdas (68%) tienen CUOTA pero no tienen BASE.
  - las pocas bases que hay son de orden 10^7 y 10^8 (decenas y cientos de
    millones de euros), magnitudes imposibles para esta cartera.
  - las cuotas, en cambio, son sanas: 10^3-10^4, miles y decenas de miles.

Es decir: la cuota se lee bien y la base no. Y el mecanismo esta identificado
en `retro_semaforo.py:206`:

    def num(rec, c):
        s = _crudo(rec, c).strip()
        if not s:
            return 0.0          # un campo VACIO devuelve 0,0 en silencio

Es el MISMO fallo ya documentado el 25-08-2026 para el campo DOCUMENTO (ver
`numero_documento()` en retro_semaforo.py): el descriptor del campo existe
siempre en el esquema -- los 91 campos estan en las 1.287 copias -- asi que
`idx.get("BASEIMPO")` devuelve algo valido y nada salta, aunque el campo
venga vacio en la practica. DOCUMENTO estaba relleno el 0,05% de las veces.

Y viola el principio fundacional del proyecto, escrito en contrato_datos.py:
MISSING no es ZERO. La ausencia no vale 0. `reconstruir_303.py` suma esos
ceros a la base y presenta el total como si lo hubiera medido -- que es
exactamente el "falso verde de un 303" que su propia cabecera dice evitar.

QUE MIDE ESTE SCRIPT
----------------------
Sobre los apuntes de las cuentas de IVA (472 y 477), y sin emitir ni un
importe:

  1. Cuantas veces BASEIMPO viene VACIO, cuantas con un numero legible y
     cuantas con algo que no es un numero. Distingue las tres cosas, que es
     justo lo que `num()` no hace.
  2. Si la base se podria RECONSTRUIR desde el asiento: para cada apunte de
     IVA, si su asiento tiene lineas de contrapartida (cuentas 6xx/7xx) de
     las que sacar la base. Eso dice si el arreglo es viable antes de
     escribirlo.
  3. El orden de magnitud de los valores que SI trae, para ver si el problema
     es que esta vacio o que ademas esta mal leido.

REGLA DE DATOS (.claude/rules/datos.md — diseno de tres roles)
---------------------------------------------------------------
Lo ejecuta el titular. Por pantalla solo RECUENTOS y ordenes de magnitud:
ni un importe, ni un NIF, ni un nombre. Errores por TIPO de excepcion.

Uso:
    python diag_baseimpo.py "RUTA_DEL_CORPUS"
    python diag_baseimpo.py "RUTA_DEL_CORPUS" --limite 100
"""
import argparse
import math
import os
import sys
import zipfile
from collections import Counter, defaultdict

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retro_semaforo import (MAX_REGISTROS_POR_FICHERO, _crudo, cuenta,
                            parse_cabecera, num, txt)

PREF_IVA = ("472", "477")
#: Cuentas de las que saldria la base si hubiera que reconstruirla: compras y
#: gastos (6xx) y ventas e ingresos (7xx). No se tocan tesoreria (57x) ni
#: acreedores/deudores (4xx), que son la contrapartida del total, no la base.
PREF_BASE = ("6", "7")


def magnitud(v):
    v = abs(v)
    if v < 1:
        return -1
    return int(math.floor(math.log10(v)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("carpeta", help="Raiz del corpus con los contenedores .DAT")
    ap.add_argument("--limite", type=int, default=0,
                    help="Procesar solo los N primeros contenedores")
    args = ap.parse_args()

    raiz = os.path.abspath(args.carpeta)

    # Un informe con todo a cero NO es un informe: es "no he mirado nada"
    # disfrazado de medicion. Es el mismo falso verde que el escaner de
    # privacidad dio una vez ("sin hallazgos" sobre ficheros que no habia
    # sabido abrir) y que el motor tiene prohibido por diseno. Si no hay nada
    # que medir, se para aqui y se dice por que.
    if not os.path.isdir(raiz):
        print(f"ERROR: esa carpeta no existe o no se puede abrir.\n"
              f"       Recibido: {args.carpeta!r}\n"
              f"       Si has copiado el comando tal cual, sustituye "
              f"RUTA_DEL_CORPUS por la ruta de verdad\n"
              f"       (la misma que le diste a reconstruir_303.py).",
              file=sys.stderr)
        sys.exit(2)

    dats = sorted(os.path.join(dp, n)
                  for dp, _, fns in os.walk(raiz) for n in fns
                  if os.path.splitext(n)[1].lower() == ".dat")
    if not dats:
        print(f"ERROR: la carpeta existe pero no tiene ningun fichero .DAT "
              f"dentro (ni en sus subcarpetas).\n"
              f"       No se ha medido nada, asi que no se emite ningun "
              f"informe: un cero medido y un cero\n"
              f"       por no haber mirado no son lo mismo.",
              file=sys.stderr)
        sys.exit(2)

    if args.limite and args.limite < len(dats):
        # Repartido entre carpetas, no los N primeros. Es la tercera vez hoy
        # (26-08-2026) que aparece el mismo error de muestreo: coger "los
        # primeros" de una lista ordenada es coger las primeras carpetas por
        # orden alfabetico, no una muestra. Aqui importa porque si todas las
        # copias de la muestra salen del mismo cliente, lo que se mida de
        # BASEIMPO describe a ese cliente y no al corpus.
        por_carpeta = defaultdict(list)
        for ruta in dats:
            por_carpeta[os.path.dirname(ruta)].append(ruta)
        repartidos = []
        vuelta = 0
        while len(repartidos) < args.limite:
            quedan = False
            for carpeta in sorted(por_carpeta):
                grupo = por_carpeta[carpeta]
                if vuelta < len(grupo):
                    quedan = True
                    repartidos.append(grupo[vuelta])
                    if len(repartidos) >= args.limite:
                        break
            if not quedan:
                break
            vuelta += 1
        dats = repartidos
        print(f"--limite {args.limite}: {len(dats):,} contenedores repartidos "
              f"entre {len(por_carpeta):,} carpetas.")
    print(f"{len(dats):,} contenedores a revisar.")

    estado_base = Counter()
    magnitudes = Counter()
    contrapartida = Counter()
    esquema = Counter()
    incidencias = Counter()
    #: (base, tipo, cuota) de los apuntes cuya BASEIMPO no es cero. Sirve para
    #: saber si esas pocas cifras estan en EUROS o en CENTIMOS: si la cuota es
    #: el tipo% de la base, estan en euros; si sale 100 veces menor, en
    #: centimos. Nunca se imprime ninguno de los tres valores.
    coherencia_no_cero = []
    paso = max(1, len(dats) // 20)

    for i, ruta in enumerate(dats, start=1):
        # El avance va en `finally`: antes estaba al final del cuerpo y
        # cualquiera de los `continue` de dentro se lo saltaba. Con 95 de 150
        # contenedores sin Diario.dbf, el contador daba saltos (18% -> 60%) y
        # no llegaba a imprimir el 100%, que se parece demasiado a un cuelgue.
        try:
            if not zipfile.is_zipfile(ruta):
                incidencias["fichero .DAT que no es un contenedor"] += 1
                continue
            with zipfile.ZipFile(ruta) as z:
                nombre = next((it.filename for it in z.infolist()
                               if not it.is_dir()
                               and os.path.basename(it.filename).lower()
                               == "diario.dbf"), None)
                if nombre is None:
                    incidencias["contenedor sin Diario.dbf"] += 1
                    continue
                with z.open(nombre) as fh:
                    len_reg, campos = parse_cabecera(fh)
                    idx = {c["nombre"]: c for c in campos}
                    esquema["BASEIMPO en el esquema" if "BASEIMPO" in idx
                            else "BASEIMPO AUSENTE del esquema"] += 1
                    cS, cBASE = idx.get("SUBCTA"), idx.get("BASEIMPO")
                    cA, cIVA = idx.get("ASIEN"), idx.get("IVA")
                    cED, cEH = idx.get("EURODEBE"), idx.get("EUROHABER")
                    if not (cS and cA):
                        incidencias["Diario.dbf sin SUBCTA o ASIEN"] += 1
                        continue

                    # Primera pasada: agrupar por asiento para saber si hay
                    # contrapartida de la que sacar la base.
                    lineas_por_asiento = defaultdict(list)
                    leidos = 0
                    while True:
                        rec = fh.read(len_reg)
                        if len(rec) < len_reg or rec[:1] == b"\x1a":
                            break
                        leidos += 1
                        if leidos > MAX_REGISTROS_POR_FICHERO:
                            raise ValueError("demasiados registros")
                        if rec[:1] == b"*":
                            continue
                        pref3 = cuenta(rec, cS)
                        crudo = _crudo(rec, cBASE).strip() if cBASE else b""
                        lineas_por_asiento[int(num(rec, cA))].append(
                            (pref3, crudo,
                             num(rec, cED) - num(rec, cEH),
                             num(rec, cIVA) if cIVA else 0.0))
                        del rec

                    for _asiento, lineas in lineas_por_asiento.items():
                        tiene_base_propia = any(
                            l[0][:1] in PREF_BASE for l in lineas)
                        for pref3, crudo, importe, tipo_iva in lineas:
                            if pref3 not in PREF_IVA:
                                continue
                            if not crudo:
                                estado_base["VACIO (num() lo convierte en 0,0)"] += 1
                            else:
                                try:
                                    v = float(crudo)
                                except ValueError:
                                    estado_base["NO es un numero "
                                                "(num() tambien da 0,0)"] += 1
                                    continue
                                # CORREGIDO 26-08-2026: la version anterior
                                # contaba solo "numero legible" y salio
                                # 100,0%, que se lee como "todo correcto".
                                # Pero el 99,4% de esos numeros legibles eran
                                # el CERO. Un informe que no separa "cero" de
                                # "cifra con contenido" comete el mismo error
                                # que MISSING != ZERO existe para impedir, y
                                # casi tapa el hallazgo que venia a buscar.
                                if v:
                                    estado_base["cifra CON CONTENIDO"] += 1
                                    magnitudes[magnitud(v)] += 1
                                    coherencia_no_cero.append((v, tipo_iva,
                                                               abs(importe)))
                                else:
                                    estado_base["CERO literal (legible, pero "
                                                "no es una base)"] += 1
                            contrapartida[
                                "el asiento SI tiene linea 6xx/7xx"
                                if tiene_base_propia
                                else "el asiento NO tiene linea 6xx/7xx"] += 1
        except Exception as e:
            incidencias["contenedor:" + type(e).__name__] += 1
        finally:
            if i % paso == 0 or i == len(dats):
                print(f"    {i * 100 // len(dats):>3}%  ({i:,}/{len(dats):,})")

    total = sum(estado_base.values())
    print()
    print("=" * 70)
    print("BASEIMPO EN LOS APUNTES DE IVA (cuentas 472 y 477)")
    print("=" * 70)
    print(f"  apuntes de IVA examinados: {total:,}")
    print()
    for k, n in estado_base.most_common():
        pct = n * 100.0 / total if total else 0
        print(f"    {k:<44} {n:>9,}  {pct:>5.1f}%")
    print()
    print("EL CAMPO EN EL ESQUEMA DEL .DBF (contenedores):")
    for k, n in esquema.most_common():
        print(f"    {k:<44} {n:>9,}")
    print()
    print("SE PODRIA RECONSTRUIR LA BASE DESDE EL ASIENTO?")
    for k, n in contrapartida.most_common():
        pct = n * 100.0 / sum(contrapartida.values()) if contrapartida else 0
        print(f"    {k:<44} {n:>9,}  {pct:>5.1f}%")
    if magnitudes:
        print()
        print("ORDEN DE MAGNITUD DE LAS BASES QUE SI TRAEN VALOR:")
        for m, n in sorted(magnitudes.items()):
            etiqueta = "menos de 1" if m < 0 else f"10^{m}"
            print(f"    {etiqueta:<12} {'#' * min(45, n):<45} {n:,}")
    if coherencia_no_cero:
        print()
        print("LAS BASES CON CONTENIDO, ¿ESTAN EN EUROS O EN CENTIMOS?")
        print("  (se compara cuota/base con el tipo que declara el propio apunte)")
        escala = Counter()
        for base, tipo, cuota in coherencia_no_cero:
            if not tipo or not base:
                escala["sin tipo con el que comparar"] += 1
                continue
            efectivo = cuota / base * 100.0
            objetivo = tipo
            if abs(efectivo - objetivo) <= 0.5:
                escala["EUROS (la cuota es el tipo% de la base)"] += 1
            elif abs(efectivo * 100 - objetivo) <= 0.5:
                escala["CENTIMOS (la base esta x100)"] += 1
            elif abs(efectivo / 100 - objetivo) <= 0.5:
                escala["la base esta /100"] += 1
            else:
                escala["ni una cosa ni otra: no cuadra con ninguna escala"] += 1
        for k, n in escala.most_common():
            print(f"    {k:<50} {n:>7,}")

    if incidencias:
        print()
        print("INCIDENCIAS:")
        for k, n in incidencias.most_common():
            print(f"    {k:<44} {n:>9,}")
    print()
    print("COMO SE LEE:")
    print("  - Si domina 'CERO literal' (o 'VACIO'), la base NUNCA se midio:")
    print("    reconstruir_303.py lleva sumando ceros y llamandolos base. El")
    print("    cruce contra el 303 no podia funcionar, y el fallo no estaba")
    print("    en los PDF. Ojo: un cero legible NO es un dato; es la ausencia")
    print("    del dato escrita con un digito.")
    print("  - Si ademas 'el asiento SI tiene linea 6xx/7xx' es alto, el")
    print("    arreglo es viable: la base se saca de la contrapartida, igual")
    print("    que ya hace reconstruir_compra() en retro_semaforo.py.")
    print()
    print("Todo lo de arriba son recuentos: se puede pegar en el chat entero.")


if __name__ == "__main__":
    main()
