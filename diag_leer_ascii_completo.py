#!/usr/bin/env python3
"""diag_leer_ascii_completo.py — mide, sin cambiar nada, si el fallback a
0.0 de leer_ascii_completo() esconde algun dato real.

POR QUE ESTE SCRIPT Y NO UN PARCHE DIRECTO
---------------------------------------------
`layout_diario_contaplus.py::leer_ascii_completo()` convierte un campo
numerico vacio Y uno ilegible en el MISMO valor: 0.0. La auditoria externa
del 17-09-2026 lo senalo como la misma familia de bug que MISSING != ZERO
(ya resuelto en la captura, ver contrato_datos.py) -- pero esta funcion
alimenta el analisis del historico REAL (retro_semaforo.py,
reconstruir_303.py, cuadre_303_ficha.py...), y cambiar su comportamiento a
ciegas podria romper cualquiera de ellos sin que nadie lo supiera hasta mas
tarde.

Por eso, siguiendo la misma regla que ya aplica el resto del proyecto
("medir antes de construir", ver MIN_NIFS en PENDIENTE.md 1.E): este script
NO TOCA layout_diario_contaplus.py. Solo MIDE, sobre tu histórico real, si
el problema es teorico o real, y cuanto pesa, antes de decidir si cambiar
0.0 por None/INVALID compensa el riesgo.

LAS CUATRO FASES (pedidas por la segunda revision del auditor externo)
--------------------------------------------------------------------------
1. FRECUENCIA: cuantos campos numericos, en total, no se pudieron parsear
   (cayeron en el `except ValueError` que hoy da 0.0)?
2. DISTRIBUCION: en que campos concretos ocurre? (BASEIMPO, IVA, EURODEBE...)
3. VACIO vs ILEGIBLE: un campo vacio en el ASCII de ContaPlus SI puede
   significar cero de verdad (el propio PROJECT_STATUS.md ya lo declara).
   Un campo con BASURA que no es un numero es una cosa distinta. Este script
   cuenta las dos por separado, nunca las mezcla.
4. VERDAD EXTERNA (si tienes tambien el .dbf de la MISMA contabilidad): un
   campo vacio o ilegible en el ASCII que en realidad tenia un valor
   DISTINTO DE CERO en el DBF es la prueba mas fuerte de que 0.0 esconde
   algo real -- mas fuerte que solo contar cuantas veces salta la excepcion,
   porque un dato corrupto puede decodificar como un numero PLAUSIBLE pero
   incorrecto sin disparar ningun error.

LO QUE NUNCA IMPRIME
-----------------------
Ni una fila, ni un ASIEN, ni un importe, ni una fecha, ni un nombre. Solo
recuentos agregados por CAMPO (nombre de columna del layout, no un dato de
cliente) y por TIPO de discrepancia. Mismo diseño de tres roles que
`medir_estructura_capturas.py`: este script lo escribo yo sin ver ningun
dato; lo ejecutas tu, en tu maquina, sobre tus ficheros reales; a mi solo
me llega lo que imprime.

USO
----
    python diag_leer_ascii_completo.py "ruta\\al\\diario.txt"
    python diag_leer_ascii_completo.py "ruta\\al\\diario.txt" --dbf "ruta\\al\\diario.dbf"

Diego: esto lo ejecutas TU, en tu terminal — no se lo pidas a Claude que lo
corra por ti aunque el script solo imprima agregados (regla ya fijada:
comandos sobre ficheros reales, siempre en tu maquina). Lo que imprime al
final SI es seguro de pegar en el chat, letra por letra.
"""
import argparse
import sys

from layout_diario_contaplus import CAMPOS, ANCHO_LINEA, CODIFICACION, decodificar_linea

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CAMPOS_NUMERICOS = [(n, a, t, d) for n, a, t, d in CAMPOS if t == "N"]

#: Tolerancia para comparar un valor ASCII (via el mismo fallback 0.0 que usa
#: hoy leer_ascii_completo) contra el mismo campo leido del DBF. Igual a la
#: del motor (TOL=0.02): no inventamos una tolerancia nueva para esto.
TOL = 0.02


def clasificar_ascii(path):
    """FASES 1-3. Devuelve (total_lineas, lineas_truncadas, vacios,
    parseables, no_parseables) -- los tres ultimos son dict campo->recuento."""
    vacios = {n: 0 for n, *_ in CAMPOS_NUMERICOS}
    parseables = {n: 0 for n, *_ in CAMPOS_NUMERICOS}
    no_parseables = {n: 0 for n, *_ in CAMPOS_NUMERICOS}
    total_lineas = 0
    lineas_truncadas = 0
    with open(path, "rb") as f:
        data = f.read()
    lineas = data.decode(CODIFICACION, errors="replace").split("\r\n")
    for linea in lineas:
        linea = linea.replace("\x1a", "").rstrip()
        if not linea.strip():
            continue
        total_lineas += 1
        if len(linea) < ANCHO_LINEA:
            lineas_truncadas += 1
            linea = linea.ljust(ANCHO_LINEA)
        crudo = decodificar_linea(linea)
        for nombre, _ancho, _tipo, _dec in CAMPOS_NUMERICOS:
            v = crudo[nombre].strip()
            if not v:
                vacios[nombre] += 1
                continue
            try:
                float(v)
                parseables[nombre] += 1
            except ValueError:
                no_parseables[nombre] += 1
    return total_lineas, lineas_truncadas, vacios, parseables, no_parseables


def _valor_ascii_hoy(crudo, nombre):
    """Reproduce EXACTAMENTE el fallback actual de leer_ascii_completo():
    vacio o ilegible -> 0.0. A proposito igual de permisivo que la produccion
    de hoy, para que la comparacion contra el DBF mida el riesgo REAL tal
    como esta ahora, no una version ya mejorada."""
    v = crudo[nombre].strip()
    if not v:
        return 0.0
    try:
        return float(v)
    except ValueError:
        return 0.0


def comparar_con_dbf(path_ascii, path_dbf):
    """FASE 4. Compara, POR POSICION (mismo indice de registro en los dos
    ficheros), el valor que el ASCII da HOY (con su fallback a 0.0) contra el
    valor real del DBF. Asume que los dos son exportaciones de la MISMA
    contabilidad y por tanto tienen el mismo orden -- si el recuento de
    registros no coincide, lo declara y no compara nada (no empareja a
    ciegas)."""
    from dbfread import DBF

    with open(path_ascii, "rb") as f:
        data = f.read()
    lineas = [l.replace("\x1a", "").rstrip()
              for l in data.decode(CODIFICACION, errors="replace").split("\r\n")]
    lineas = [l for l in lineas if l.strip()]
    lineas = [l.ljust(ANCHO_LINEA) if len(l) < ANCHO_LINEA else l for l in lineas]

    registros_dbf = list(DBF(path_dbf, encoding="latin1"))

    if len(lineas) != len(registros_dbf):
        return None, (f"recuento distinto: {len(lineas)} lineas en el ASCII, "
                      f"{len(registros_dbf)} registros en el DBF -- no se "
                      f"puede emparejar por posicion con seguridad")

    # campo_ascii -> nombre del campo en el DBF, cuando no coinciden
    # literalmente. Si tu DBF usa otros nombres, ajusta este mapeo -- no se
    # adivina.
    ALIAS_DBF = {}

    # COMPROBACION DE ALINEACION, anadida el 17-09-2026 tras la primera
    # medicion real: comparar "linea i del ASCII" contra "registro i del DBF"
    # solo tiene sentido si las dos exportaciones traen el MISMO orden.
    # Mismo recuento de lineas no prueba mismo orden. Se verifica con ASIEN
    # (el numero de asiento, que deberia identificar la misma fila en las
    # dos exportaciones si van alineadas) ANTES de fiarse de ninguna otra
    # comparacion -- si ASIEN no coincide casi siempre, todo lo demas que
    # este script diga sobre otros campos es ruido de desalineacion, no un
    # hallazgo real sobre el fallback 0.0.
    alineados = 0
    for linea, reg_dbf in zip(lineas, registros_dbf):
        crudo = decodificar_linea(linea)
        try:
            asien_ascii = float(crudo["ASIEN"].strip() or "nan")
            asien_dbf = float(reg_dbf.get("ASIEN")) if reg_dbf.get("ASIEN") is not None else float("nan")
        except (ValueError, TypeError):
            continue
        if asien_ascii == asien_dbf:
            alineados += 1
    frac_alineados = alineados / len(lineas) if lineas else 0.0

    coincide = {n: 0 for n, *_ in CAMPOS_NUMERICOS}
    discrepancia = {n: 0 for n, *_ in CAMPOS_NUMERICOS}
    # El caso mas grave: ASCII dio 0.0 (vacio o ilegible) pero el DBF tiene
    # un valor real DISTINTO de cero para ese mismo campo.
    ascii_cero_dbf_no_cero = {n: 0 for n, *_ in CAMPOS_NUMERICOS}
    campo_no_en_dbf = set()

    for linea, reg_dbf in zip(lineas, registros_dbf):
        crudo = decodificar_linea(linea)
        for nombre, _a, _t, _d in CAMPOS_NUMERICOS:
            campo_dbf = ALIAS_DBF.get(nombre, nombre)
            if campo_dbf not in reg_dbf:
                campo_no_en_dbf.add(nombre)
                continue
            v_ascii = _valor_ascii_hoy(crudo, nombre)
            v_dbf = reg_dbf[campo_dbf]
            try:
                v_dbf = float(v_dbf) if v_dbf is not None else 0.0
            except (TypeError, ValueError):
                continue  # el propio DBF no da un numero utilizable aqui
            if v_ascii == 0.0 and abs(v_dbf) >= TOL:
                ascii_cero_dbf_no_cero[nombre] += 1
            elif abs(v_ascii - v_dbf) < TOL:
                coincide[nombre] += 1
            else:
                discrepancia[nombre] += 1

    return (len(lineas), frac_alineados, coincide, discrepancia,
            ascii_cero_dbf_no_cero, campo_no_en_dbf), None


def main():
    parser = argparse.ArgumentParser(
        description="Mide (no cambia nada) el fallback 0.0 de leer_ascii_completo() contra tu histórico real.")
    parser.add_argument("ascii", help="Ruta al diario ASCII (.txt) de ContaPlus")
    parser.add_argument("--dbf", help="Ruta al .dbf de la MISMA contabilidad, si existe, para la Fase 4")
    args = parser.parse_args()

    print("=" * 72)
    print("FASES 1-3 — frecuencia, distribucion y vacio-vs-ilegible")
    print("=" * 72)
    total, truncadas, vacios, parseables, no_parseables = clasificar_ascii(args.ascii)
    total_campos = total * len(CAMPOS_NUMERICOS)
    total_no_parseables = sum(no_parseables.values())
    total_vacios = sum(vacios.values())

    print(f"\nLineas de datos: {total}   (truncadas al final del fichero: {truncadas})")
    print(f"Campos numericos por linea: {len(CAMPOS_NUMERICOS)}   "
          f"(total de instancias campo x linea: {total_campos})")
    print(f"\nVACIOS (pueden ser cero de verdad, ver docstring): {total_vacios}")
    print(f"NO PARSEABLES (caen en el fallback a 0.0 ilegitimamente): {total_no_parseables}")

    if total_no_parseables:
        print("\nDistribucion de NO PARSEABLES por campo (solo los que tienen alguno):")
        for nombre, n in sorted(no_parseables.items(), key=lambda kv: -kv[1]):
            if n:
                print(f"  {nombre}: {n}")
    else:
        print("\nNinguna instancia de ValueError en todo el fichero.")

    if args.dbf:
        print()
        print("=" * 72)
        print("FASE 4 — verdad externa: ASCII (con el fallback de hoy) vs DBF")
        print("=" * 72)
        resultado, error = comparar_con_dbf(args.ascii, args.dbf)
        if error:
            print(f"\nNO COMPARADO: {error}")
        else:
            n_reg, frac_alineados, coincide, discrepancia, ascii_cero_dbf_no_cero, sin_campo = resultado
            print(f"\n{n_reg} registros comparados por posicion.")

            print(f"\nCOMPROBACION DE ALINEACION (mirar ESTO primero): de los "
                  f"{n_reg} registros, el numero de ASIEN coincide en la misma "
                  f"posicion en un {frac_alineados:.1%} de los casos.")
            if frac_alineados < 0.95:
                print("  AVISO SERIO: por debajo del 95%, todo lo que sigue no es")
                print("  fiable -- lo mas probable es que las dos exportaciones NO")
                print("  vengan en el mismo orden, y comparar 'linea i contra i'")
                print("  esta emparejando asientos que no son el mismo. Los")
                print("  numeros de mas abajo pueden ser ruido de desalineacion,")
                print("  no un hallazgo real sobre el fallback 0.0.")
            else:
                print("  Alineacion confirmada: las comparaciones de abajo emparejan")
                print("  el mismo asiento en los dos ficheros.")

            if sin_campo:
                print(f"\nCampos que el DBF no trae con ese nombre (no comparados): {sorted(sin_campo)}")
            total_grave = sum(ascii_cero_dbf_no_cero.values())
            print(f"\nEL CASO GRAVE -- ASCII dio 0.0 (vacio o ilegible) pero el DBF "
                  f"tiene un valor real distinto de cero: {total_grave}")
            if total_grave:
                print("Distribucion por campo (solo los que tienen alguno):")
                for nombre, n in sorted(ascii_cero_dbf_no_cero.items(), key=lambda kv: -kv[1]):
                    if n:
                        print(f"  {nombre}: {n}")
            total_discrepancia = sum(discrepancia.values())
            print(f"\nDiscrepancias donde los dos parsearon pero no coinciden "
                  f"(redondeo/conversion, no necesariamente un fallo): {total_discrepancia}")
    else:
        print("\n(Sin --dbf: la Fase 4 no se ha podido hacer. Si tienes el .dbf de "
              "la MISMA contabilidad, vuelve a ejecutar con --dbf para la prueba "
              "mas fuerte.)")


if __name__ == "__main__":
    main()
