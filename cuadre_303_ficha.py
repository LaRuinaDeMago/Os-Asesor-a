#!/usr/bin/env python3
"""cuadre_303_ficha.py -- ficha de comparacion para el cuadre manual del 303.

QUE HACE Y QUE NO HACE
-----------------------
NO lee ningun PDF. NO extrae nada de Hacienda. NO intenta adivinar de que
cliente es cada contabilidad. Solo da FORMATO a las cifras que ya estan en
`303_LOCAL.json` (que produce reconstruir_303.py) para que compararlas contra
el 303 presentado sea abrir un PDF y mirar dos totales, en vez de sumar a
mano dentro de un JSON.

EL PROBLEMA QUE RESUELVE, Y POR QUE SE RESUELVE ASI
----------------------------------------------------
`303_LOCAL.json` viene indexado por el nombre de la CARPETA que contiene cada
contenedor .DAT, porque no hay nada mejor: esta medido y descartado en
`fase0_huella_cliente.py` que una copia de ContaPlus NO contiene la identidad
de la empresa (el nombre y el NIF viven en el registro global de la
instalacion, no en la copia; datempre.dbf viene vacio, DATOS.ASC a cero,
M390A.dbf en blanco).

Consecuencia practica, confirmada con un caso real: algunas de esas carpetas
SI son un cliente ("carpeta de Fulanito"), pero otras estan organizadas por
EQUIPO o por COPIA ("Contabilidad ordenador de Jose") y mezclan varios
clientes reales dentro. Las cifras de esas ultimas son una SUMA DE VARIAS
EMPRESAS y no se pueden comparar contra el 303 de ninguna: cuadrarlas seria
imposible, y peor, podrian cuadrar por casualidad y dar un falso verde.

No se intenta resolver eso automaticamente. Las carpetas las nombro el
titular, asi que la forma fiable de separarlas es que las MIRE:

    Paso 1:  python cuadre_303_ficha.py --listar
             -> escribe una lista numerada de las carpetas a un fichero _LOCAL

    Paso 2:  el titular la abre y elige los numeros de las que SI son un
             cliente concreto y reconocible

    Paso 3:  python cuadre_303_ficha.py --elegir 2,5,9
             -> escribe las fichas solo de esas, listas para comparar

El script marca con (?) las carpetas cuyo nombre suena a equipo/copia, pero
es solo una PISTA: no descarta nada por su cuenta. Una barrera que decide por
el nombre es de conveniencia; aqui quien decide es quien conoce los datos.

REGLA DE DATOS (.claude/rules/datos.md -- diseno de tres roles)
-----------------------------------------------------------------
Lo ejecuta el titular, no Claude. Toda la salida (nombres de carpeta e
importes) va a ficheros con sufijo _LOCAL, que .gitignore protege y que
Claude no abre jamas. Por pantalla solo se imprimen recuentos. Lo unico que
se comparte al terminar son los tres numeros del resumen final.

Uso:
    python cuadre_303_ficha.py --listar
    python cuadre_303_ficha.py --elegir 2,5,9
    python cuadre_303_ficha.py --elegir 2,5,9 --json 303_LOCAL.json
"""
import argparse
import json
import os
import sys

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Orden de presentacion de los tipos de IVA. Los tipos que no esten aqui se
#: muestran igualmente al final: no se pierde nada por no estar en la lista.
TIPOS_ORDEN = ("21", "10", "8", "7", "5", "4", "0", "16", "18",
               "tipo_no_catalogado")

#: Palabras que sugieren que una carpeta agrupa por EQUIPO o por COPIA en vez
#: de por cliente. Solo se usa para poner un (?) en la lista -- NUNCA para
#: descartar. Ver el comentario largo de la cabecera.
PISTAS_NO_CLIENTE = ("ordenador", "disco", "copia", "copias", "backup",
                     "servidor", "portatil", "escritorio", "equipo", "usb",
                     "pc0", "pc1", "pc2")


def suena_a_equipo(nombre):
    bajo = nombre.lower()
    return any(pista in bajo for pista in PISTAS_NO_CLIENTE)


def formato(v):
    """1234.5 -> '1.234,50' (formato espanol, para comparar contra el PDF)."""
    return f"{v:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def cargar(ruta):
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def resumen_carpeta(trimestres):
    """Recuentos de una carpeta, sin mirar importes de ningun trimestre suelto."""
    anios = set()
    apuntes = 0
    con_datos = 0
    for trimestre, lados in trimestres.items():
        n = sum(celda.get("apuntes", 0)
                for lado in ("devengado", "deducible")
                for celda in lados.get(lado, {}).values())
        if n > 0:
            con_datos += 1
            apuntes += n
            anios.add(trimestre[:4])
    return con_datos, sorted(anios), apuntes


def carpetas_ordenadas(datos):
    """Orden estable: los numeros de --elegir deben significar lo mismo hoy y
    manana, mientras el JSON no cambie."""
    return sorted(datos.keys())


def escribir_listado(datos, ruta_salida):
    orden = carpetas_ordenadas(datos)
    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write("CARPETAS ENCONTRADAS EN EL DETALLE DEL 303\n")
        f.write("=" * 78 + "\n\n")
        f.write("Elige los NUMEROS de las carpetas que sean UN CLIENTE concreto\n")
        f.write("y reconocible. Descarta las que agrupen por ordenador o por copia:\n")
        f.write("esas mezclan varios clientes y sus cifras no cuadran con ningun 303.\n\n")
        f.write("El (?) es solo una pista por el nombre. Manda tu criterio.\n\n")
        f.write("Despues ejecuta, por ejemplo:   python cuadre_303_ficha.py --elegir 2,5,9\n\n")
        f.write("-" * 78 + "\n")
        usables = 0
        for i, carpeta in enumerate(orden, start=1):
            n_tri, anios, apuntes = resumen_carpeta(datos[carpeta])
            if n_tri == 0:
                continue
            usables += 1
            marca = " (?)" if suena_a_equipo(carpeta) else "    "
            rango = f"{anios[0]}-{anios[-1]}" if anios else "sin fecha"
            f.write(f"{i:>3}.{marca} {carpeta}\n")
            # Solo ASCII en el fichero de salida: se abre en el Bloc de notas,
            # en Notepad++ o en lo que haya, y un guion bajo de codificacion
            # convierte la lista en algo ilegible justo cuando mas molesta.
            f.write(f"      {n_tri} trimestres con datos  |  {rango}  |  "
                    f"{apuntes:,} apuntes de IVA\n")
        f.write("-" * 78 + "\n")
        f.write(f"\n{usables} carpetas con datos.\n")
    return len(orden), usables


def bloque_lado(celdas, etiqueta_casillas):
    if not celdas:
        return "    (sin apuntes en este lado)\n"
    conocidos = [t for t in TIPOS_ORDEN if t in celdas]
    otros = sorted(t for t in celdas if t not in TIPOS_ORDEN)
    lineas = []
    total_base = 0.0
    total_cuota = 0.0
    for tipo in conocidos + otros:
        c = celdas[tipo]
        etiqueta = "SIN TIPO CLARO" if tipo == "tipo_no_catalogado" else f"{tipo}%"
        lineas.append(
            f"    tipo {etiqueta:<15} base {formato(c['base']):>15}   "
            f"cuota {formato(c['cuota']):>13}   ({c['apuntes']} apuntes)")
        total_base += c["base"]
        total_cuota += c["cuota"]
    lineas.append("    " + "-" * 70)
    lineas.append(
        f"    {'TOTAL ' + etiqueta_casillas:<20} base {formato(total_base):>15}   "
        f"cuota {formato(total_cuota):>13}")
    return "\n".join(lineas) + "\n"


def escribir_ficha(f, carpeta, trimestre, lados):
    f.write("=" * 78 + "\n")
    f.write(f"CARPETA: {carpeta}\n")
    f.write(f"TRIMESTRE: {trimestre}\n")
    f.write("=" * 78 + "\n")
    f.write("\nDEVENGADO (ventas / IVA repercutido) -> casillas 01-09 del 303\n")
    f.write(bloque_lado(lados.get("devengado", {}), "casillas 01-09"))
    f.write("\nDEDUCIBLE (compras / IVA soportado) -> casillas 28-29 del 303\n")
    f.write(bloque_lado(lados.get("deducible", {}), "casillas 28-29"))
    f.write("\n  Abre el 303 presentado de este cliente y trimestre y compara\n")
    f.write("  los dos TOTAL contra las casillas correspondientes.\n\n")
    f.write("  Veredicto (marca uno):\n")
    f.write("    [ ] Cuadra exacto\n")
    f.write("    [ ] Cuadra con diferencia EXPLICABLE (ISP / intracomunitaria /\n")
    f.write("        prorrata / compensacion de cuotas) -> anota cual:\n")
    f.write("    [ ] No cuadra y no se por que\n")
    f.write("\n\n")


def escribir_fichas(datos, elegidas, ruta_salida):
    orden = carpetas_ordenadas(datos)
    pares = []
    for numero in elegidas:
        carpeta = orden[numero - 1]
        for trimestre, lados in sorted(datos[carpeta].items()):
            n = sum(celda.get("apuntes", 0)
                    for lado in ("devengado", "deducible")
                    for celda in lados.get(lado, {}).values())
            if n > 0:
                pares.append((carpeta, trimestre, lados))

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write("FICHA DE CUADRE MANUAL CONTRA EL 303 PRESENTADO\n")
        f.write(f"Carpetas elegidas: {len(elegidas)}   "
                f"Trimestres con datos: {len(pares)}\n\n")
        f.write("No hace falta comparar los ")
        f.write(f"{len(pares)} trimestres: con 5-10 repartidos entre\n")
        f.write("varios clientes y varios anios ya se contesta la pregunta.\n\n")
        for carpeta, trimestre, lados in pares:
            escribir_ficha(f, carpeta, trimestre, lados)
        f.write("=" * 78 + "\n")
        f.write("RESUMEN AL TERMINAR (esto es lo UNICO que se comparte):\n\n")
        f.write("  Trimestres comparados en total:        ___\n")
        f.write("  De ellos, cuadran exacto:              ___\n")
        f.write("  Cuadran con diferencia explicable:     ___\n")
        f.write("  No cuadran / sin explicacion:          ___\n")
    return len(pares)


def parsear_eleccion(texto, maximo):
    numeros = []
    for trozo in texto.replace(" ", "").split(","):
        if not trozo:
            continue
        if not trozo.isdigit():
            raise ValueError(f"'{trozo}' no es un numero")
        n = int(trozo)
        if not (1 <= n <= maximo):
            raise ValueError(f"el numero {n} esta fuera de rango (hay {maximo})")
        if n not in numeros:
            numeros.append(n)
    if not numeros:
        raise ValueError("no has indicado ningun numero")
    return numeros


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", default="303_LOCAL.json",
                    help="Detalle producido por reconstruir_303.py "
                         "(por defecto 303_LOCAL.json en esta carpeta)")
    ap.add_argument("--listar", action="store_true",
                    help="PASO 1: escribe la lista numerada de carpetas para elegir")
    ap.add_argument("--elegir", metavar="N,N,N",
                    help="PASO 2: numeros de las carpetas elegidas, separados por comas")
    ap.add_argument("--salida-lista", default="cuadre_303_carpetas_LOCAL.txt",
                    help="Fichero de la lista del paso 1 (debe llevar _LOCAL)")
    ap.add_argument("--salida", default="cuadre_303_ficha_LOCAL.txt",
                    help="Fichero de las fichas del paso 2 (debe llevar _LOCAL)")
    args = ap.parse_args()

    if not args.listar and not args.elegir:
        ap.error("indica --listar (paso 1) o --elegir N,N,N (paso 2). "
                 "Empieza por --listar.")

    for nombre_arg, valor in (("--salida-lista", args.salida_lista),
                              ("--salida", args.salida)):
        if "_LOCAL" not in os.path.basename(valor):
            print(f"ERROR: {nombre_arg} debe contener _LOCAL en el nombre: la "
                  f"salida lleva nombres de carpeta e importes de clientes "
                  f"concretos, y .gitignore solo protege *_LOCAL.*",
                  file=sys.stderr)
            sys.exit(1)

    if not os.path.exists(args.json):
        print(f"ERROR: no encuentro {args.json}.\n"
              f"Generalo antes con:\n"
              f"  python reconstruir_303.py \"RUTA_DEL_CORPUS\" "
              f"--detalle 303_LOCAL.json", file=sys.stderr)
        sys.exit(1)

    try:
        datos = cargar(args.json)
    except json.JSONDecodeError:
        print(f"ERROR: {args.json} no es un JSON valido. Vuelve a generarlo "
              f"con reconstruir_303.py.", file=sys.stderr)
        sys.exit(1)

    if not isinstance(datos, dict) or not datos:
        print(f"ERROR: {args.json} esta vacio o no tiene la forma esperada.",
              file=sys.stderr)
        sys.exit(1)

    if args.listar:
        ruta = os.path.abspath(args.salida_lista)
        total, usables = escribir_listado(datos, ruta)
        print(f"Lista escrita en: {ruta}")
        print(f"({usables} carpetas con datos, de {total} en el fichero).")
        print()
        print("PASO 1: abrela y mira que numeros son un CLIENTE concreto.")
        print("        Descarta las que agrupen por ordenador o por copia.")
        print("PASO 2: python cuadre_303_ficha.py --elegir 2,5,9")
        return

    orden = carpetas_ordenadas(datos)
    try:
        elegidas = parsear_eleccion(args.elegir, len(orden))
    except ValueError as e:
        print(f"ERROR en --elegir: {e}", file=sys.stderr)
        print("Ejecuta primero: python cuadre_303_ficha.py --listar",
              file=sys.stderr)
        sys.exit(1)

    ruta = os.path.abspath(args.salida)
    n_pares = escribir_fichas(datos, elegidas, ruta)
    if n_pares == 0:
        print("Ninguna de las carpetas elegidas tiene trimestres con datos.",
              file=sys.stderr)
        sys.exit(1)
    print(f"Fichas escritas en: {ruta}")
    print(f"({len(elegidas)} carpetas, {n_pares} trimestres con datos).")
    print()
    print("Abrelo y compara contra los 303 presentados. Con 5-10 trimestres basta.")
    print("No pegues el contenido en el chat: solo el resumen final de numeros.")


if __name__ == "__main__":
    main()
