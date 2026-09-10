#!/usr/bin/env python3
"""ensayo_cuadre_ficha.py — ensayo en seco de cuadre_303_ficha.py.

POR QUE HACE FALTA
-------------------
`cuadre_303_ficha.py` es la via de REVISION HUMANA al cuadre contra el 303
presentado, y ese cuadre es —en palabras de `SIGUIENTES_PASOS.md` §3.3— "la
unica verdad externa que este proyecto va a tener nunca". Todo lo demas se
valida contra si mismo.

Estaba construido desde el 26-08-2026, documentado como "probado con datos
ficticios", declarado "lo primero de manana" en la entrada del 27-08... y
**sin un solo ensayo**: no lo ejercitaba ningun fichero del repositorio ni
corria dentro de `audit_project.py`. Iba a llegar a su ejecucion real en la
misma situacion que el 21-08-2026 produjo tres defectos en la primera pasada
de los comandos LOCAL.

LA PROPIEDAD QUE MAS DANO HARIA SI SE ROMPE
--------------------------------------------
El flujo son dos pasos separados por una decision humana:

    paso 1: --listar        -> una lista NUMERADA de carpetas
    paso 2: --elegir 2,5,9  -> las fichas de esas

**Si el numero 5 de la lista no es la misma carpeta que el numero 5 de
`--elegir`, Diego compara la contabilidad de un cliente contra el 303 de
otro.** El resultado no es un error visible: es un descuadre inexplicable, o
peor, un cuadre por casualidad anotado como bueno. Es la familia A, y va
primera.

El riesgo es real y no teorico: la lista SE SALTA las carpetas sin datos al
imprimirlas, pero la numeracion tiene que seguir siendo la del indice
completo. Dos criterios distintos en dos funciones distintas.

TODO LO DE AQUI ES SINTETICO. Nombres `*_SINTETICA`, importes inventados,
ningun `.DAT` ni PDF. No hace falta el corpus para correrlo.

Uso:
    python ensayo_cuadre_ficha.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AQUI = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(AQUI, "cuadre_303_ficha.py")

FALLOS = []


def comprobar(titulo, condicion, detalle=""):
    if condicion:
        print(f"  OK  {titulo}")
    else:
        print(f"  FALLA  {titulo}   {detalle}")
        FALLOS.append(titulo)


def celda(base, cuota, apuntes):
    return {"base": base, "cuota": cuota, "apuntes": apuntes}


def correr(*args):
    r = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=AQUI)
    return r.returncode, r.stdout, r.stderr


def main():
    print("=" * 70)
    print("ENSAYO EN SECO: cuadre_303_ficha.py")
    print("(todo sintetico — ni un .DAT, ni un PDF, ni un dato real)")
    print("=" * 70)

    tmp = tempfile.mkdtemp(prefix="ensayo_ficha_")
    try:
        # Corpus sintetico. Claves a proposito en orden NO alfabetico, con una
        # carpeta VACIA intercalada: es lo que separa "numerar lo que se
        # imprime" de "numerar el indice completo".
        datos = {
            "ZETA_SINTETICA": {
                "2021T1": {"devengado": {"21": celda(1000.0, 210.0, 4)},
                           "deducible": {"21": celda(400.0, 84.0, 2)}}},
            "ALFA_SINTETICA": {
                "2021T1": {"devengado": {"21": celda(2000.0, 420.0, 8)},
                           "deducible": {"10": celda(100.0, 10.0, 1)}},
                "2022T2": {"devengado": {"21": celda(50.0, 10.5, 1)},
                           "deducible": {}}},
            "VACIA_SINTETICA": {
                "2021T1": {"devengado": {}, "deducible": {}}},
            "MEDIA_SINTETICA": {
                "2022T3": {"devengado": {"21": celda(500.0, 105.0, 2),
                                         "tipo_no_catalogado": celda(300.0, 45.0, 3)},
                           "deducible": {"21": celda(-250.0, -52.5, 2)}}},
        }
        ruta_json = os.path.join(tmp, "303_sintetico.json")
        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False)

        lista = os.path.join(tmp, "lista_LOCAL.txt")
        ficha = os.path.join(tmp, "ficha_LOCAL.txt")

        # Los numeros salen del MISMO criterio que usa el script (orden
        # alfabetico de las claves), nunca escritos a mano. La primera version
        # de este ensayo los puso a ojo y fallo cinco comprobaciones: creia que
        # MEDIA era la 3 cuando es la 2. El ensayo se equivocaba, no el script
        # — exactamente el error que este proyecto lleva evitando en el codigo,
        # cometido en la prueba.
        orden = sorted(datos)
        N = {nombre: i for i, nombre in enumerate(orden, start=1)}

        # === FAMILIA A — el numero significa la misma carpeta en los dos pasos
        print("\n=== FAMILIA A — la numeracion no se descoloca entre --listar y --elegir ===")
        rc, out, err = correr("--json", ruta_json, "--listar", "--salida-lista", lista)
        comprobar("--listar termina bien", rc == 0, err[-300:])
        texto_lista = open(lista, encoding="utf-8").read()

        # Se lee la lista como la leeria Diego: numero -> nombre.
        numerado = {}
        for linea in texto_lista.splitlines():
            trozo = linea.strip()
            if trozo[:1].isdigit() and "." in trozo:
                num, resto = trozo.split(".", 1)
                if num.strip().isdigit():
                    numerado[int(num)] = resto.replace("(?)", "").strip()

        comprobar("la carpeta sin datos NO aparece en la lista",
                  "VACIA_SINTETICA" not in numerado.values(),
                  f"numerado={numerado}")
        comprobar("pero su numero SE RESERVA: los demas no se corren un puesto",
                  sorted(numerado) == [1, 2, 4],
                  f"numeros impresos={sorted(numerado)} (se espera 1,2,4)")

        # Y ahora la prueba de verdad: pedir cada numero y comprobar que sale
        # el nombre que la lista prometia. Si esto falla, se compara la
        # contabilidad de un cliente contra el 303 de otro.
        for numero, nombre_prometido in sorted(numerado.items()):
            rc_i, _, err_i = correr("--json", ruta_json, "--elegir", str(numero),
                                    "--salida", ficha)
            contenido = open(ficha, encoding="utf-8").read() if rc_i == 0 else ""
            comprobar(f"--elegir {numero} devuelve la carpeta que la lista dice ({nombre_prometido})",
                      rc_i == 0 and f"CARPETA: {nombre_prometido}" in contenido,
                      f"rc={rc_i} {err_i[-160:]}")

        # === FAMILIA B — los totales son la suma de sus celdas ==============
        print("\n=== FAMILIA B — los totales suman lo que hay, en formato espanol ===")
        # MEDIA_SINTETICA: devengado 500 + 300 = 800; deducible -250.
        rc, out, err = correr("--json", ruta_json, "--elegir",
                              str(N["MEDIA_SINTETICA"]), "--salida", ficha)
        f_media = open(ficha, encoding="utf-8").read()
        comprobar("el TOTAL devengado es 800,00 (500 + 300), no una celda suelta",
                  "TOTAL casillas 01-09 base          800,00" in f_media,
                  [l for l in f_media.splitlines() if "TOTAL casillas 01-09" in l])
        comprobar("la cuota devengada es 150,00 (105 + 45)",
                  "cuota        150,00" in f_media,
                  [l for l in f_media.splitlines() if "TOTAL casillas 01-09" in l])
        comprobar("un importe negativo (rectificativa) sale como negativo, no en absoluto",
                  "-250,00" in f_media,
                  [l for l in f_media.splitlines() if "28-29" in l])
        correr("--json", ruta_json, "--elegir", str(N["ALFA_SINTETICA"]),
               "--salida", ficha)
        f_alfa_fmt = open(ficha, encoding="utf-8").read()
        comprobar("y el formato es el espanol del PDF (miles con punto, decimal con coma)",
                  "2.000,00" in f_alfa_fmt,
                  [l for l in f_alfa_fmt.splitlines() if "TOTAL" in l])
        # Se vuelve a dejar la ficha de MEDIA para las comprobaciones de abajo.
        correr("--json", ruta_json, "--elegir", str(N["MEDIA_SINTETICA"]),
               "--salida", ficha)
        f_media = open(ficha, encoding="utf-8").read()

        # === FAMILIA C — el total mixto se declara (arreglo del 09-09-2026) ==
        print("\n=== FAMILIA C — un total que incluye tipo desconocido lo dice ===")
        comprobar("avisa de que parte del total es de tipo DESCONOCIDO",
                  "DESCONOCIDO" in f_media and "NO es limpia" in f_media,
                  f_media[:600])
        comprobar("y dice CUANTO es (base 300,00 / cuota 45,00, 3 apuntes)",
                  "base 300,00" in f_media and "cuota 45,00" in f_media
                  and "(3 apuntes)" in f_media,
                  [l for l in f_media.splitlines() if "OJO" in l])
        # ALFA no tiene tipo desconocido: no debe salir el aviso, o dejaria de
        # significar algo por aparecer siempre.
        correr("--json", ruta_json, "--elegir", str(N["ALFA_SINTETICA"]),
               "--salida", ficha)
        f_alfa = open(ficha, encoding="utf-8").read()
        comprobar("y NO avisa cuando todos los tipos estan catalogados",
                  "DESCONOCIDO" not in f_alfa, f_alfa[:400])

        # === FAMILIA D — la barrera de datos ================================
        # Regla de tres roles: la salida lleva nombres de carpeta e importes de
        # clientes concretos. Solo puede ir a un fichero _LOCAL, y por pantalla
        # solo salen recuentos.
        print("\n=== FAMILIA D — barrera de datos (.claude/rules/datos.md) ===")
        publico = os.path.join(tmp, "fichas_publicas.txt")
        rc, out, err = correr("--json", ruta_json, "--elegir",
                              str(N["ALFA_SINTETICA"]), "--salida", publico)
        comprobar("se niega a escribir a un fichero sin _LOCAL en el nombre",
                  rc != 0, f"rc={rc}")
        comprobar("y NO lo crea (no basta con avisar despues de escribirlo)",
                  not os.path.exists(publico), f"existe={os.path.exists(publico)}")
        rc, out, err = correr("--json", ruta_json, "--listar",
                              "--salida-lista", os.path.join(tmp, "lista_publica.txt"))
        comprobar("la misma barrera protege la lista del paso 1",
                  rc != 0 and not os.path.exists(os.path.join(tmp, "lista_publica.txt")),
                  f"rc={rc}")

        rc, out, err = correr("--json", ruta_json, "--elegir",
                              f"{N['ALFA_SINTETICA']},{N['MEDIA_SINTETICA']}",
                              "--salida", ficha)
        salida_pantalla = out + err
        comprobar("por pantalla NO se imprime ningun nombre de carpeta",
                  "SINTETICA" not in salida_pantalla, salida_pantalla[:300])
        comprobar("ni ningun importe",
                  "800" not in salida_pantalla and "2.000" not in salida_pantalla
                  and "500" not in salida_pantalla,
                  salida_pantalla[:300])
        rc, out, err = correr("--json", ruta_json, "--listar", "--salida-lista", lista)
        comprobar("tampoco en el paso 1: solo recuentos y la ruta",
                  "SINTETICA" not in (out + err), (out + err)[:300])

        # === FAMILIA E — entradas malas no producen una ficha ================
        # Una ficha es algo que Diego va a comparar contra Hacienda. Producir
        # una a partir de una entrada que no se ha entendido es el falso verde
        # de siempre con otra ropa.
        print("\n=== FAMILIA E — con una entrada mala no sale ninguna ficha ===")
        roto = os.path.join(tmp, "roto.json")
        with open(roto, "w", encoding="utf-8") as f:
            f.write("{esto no es json valido")
        rc, out, err = correr("--json", roto, "--listar", "--salida-lista", lista)
        comprobar("un JSON invalido se rechaza con codigo != 0",
                  rc != 0, f"rc={rc}")

        vacio = os.path.join(tmp, "vacio.json")
        with open(vacio, "w", encoding="utf-8") as f:
            f.write("{}")
        rc, out, err = correr("--json", vacio, "--listar", "--salida-lista", lista)
        comprobar("un JSON vacio se rechaza en vez de escribir una lista vacia",
                  rc != 0, f"rc={rc}")

        rc, out, err = correr("--json", os.path.join(tmp, "no_existe.json"),
                              "--listar", "--salida-lista", lista)
        comprobar("un fichero que no existe se rechaza diciendo como generarlo",
                  rc != 0 and "reconstruir_303.py" in (out + err), (out + err)[:200])

        rc, out, err = correr("--json", ruta_json, "--elegir", "99", "--salida", ficha)
        comprobar("un numero fuera de rango se rechaza, no se recorta al maximo",
                  rc != 0, f"rc={rc}")

        rc, out, err = correr("--json", ruta_json, "--elegir", "dos", "--salida", ficha)
        comprobar("un --elegir que no es un numero se rechaza",
                  rc != 0, f"rc={rc}")

        rc, out, err = correr("--json", ruta_json)
        comprobar("sin --listar ni --elegir no hace nada y lo explica",
                  rc != 0, f"rc={rc}")

        # === FAMILIA F — una ejecucion fallida no destruye la ficha anterior
        # Regresion del defecto encontrado el 09-09-2026 al escribir este
        # ensayo. La ficha es el documento de TRABAJO: se va marcando a mano,
        # trimestre a trimestre, contra los 303 presentados. Se escribia
        # primero y se comprobaba despues, asi que un --elegir sobre una
        # carpeta sin datos salia con codigo 1 habiendo machacado ya la ficha
        # buena con una vacia.
        print("\n=== FAMILIA F — un fallo no se lleva por delante la ficha anterior ===")
        rc, _, _ = correr("--json", ruta_json, "--elegir", str(N["ALFA_SINTETICA"]),
                          "--salida", ficha)
        bueno = open(ficha, encoding="utf-8").read()
        comprobar("primero, una ejecucion buena deja su ficha",
                  rc == 0 and "ALFA_SINTETICA" in bueno, f"rc={rc}")

        rc_v, _, err_v = correr("--json", ruta_json,
                                "--elegir", str(N["VACIA_SINTETICA"]),
                                "--salida", ficha)
        comprobar("elegir solo una carpeta sin datos avisa en vez de dar una ficha vacia",
                  rc_v != 0, f"rc={rc_v} (carpeta vacia = numero {N['VACIA_SINTETICA']})")
        despues = open(ficha, encoding="utf-8").read() if os.path.exists(ficha) else ""
        comprobar("y la ficha buena SIGUE INTACTA tras el fallo",
                  despues == bueno,
                  f"antes={len(bueno)} bytes, despues={len(despues)} bytes")
        comprobar("sin dejar ningun fichero .parcial suelto",
                  not os.path.exists(ficha + ".parcial"),
                  f"existe={os.path.exists(ficha + '.parcial')}")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("=" * 70)
    if FALLOS:
        print(f"FALLAN {len(FALLOS)} comprobaciones:")
        for f in FALLOS:
            print(f"  - {f}")
        print("\nLa primera familia es la grave: si la numeracion se descoloca,")
        print("se compara la contabilidad de un cliente contra el 303 de otro.")
        return 1
    print("El ensayo pasa. El numero elegido es la carpeta prometida, los")
    print("totales suman lo que hay, y nada sale de un fichero _LOCAL.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
