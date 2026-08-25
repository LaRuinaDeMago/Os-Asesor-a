#!/usr/bin/env python3
"""ensayo_corpus_roto.py — que un fichero corrupto NO se lleve la sesion.

POR QUE ESTO NO ES PARANOIA
---------------------------
El corpus real son 1.287 contenedores de diez anos de copias de seguridad de
ContaPlus. En diez anos de copias hay ficheros truncados, copias a medio
terminar, contenedores vacios y cabeceras que no dicen la verdad. Es lo normal en
un archivo historico, no la excepcion.

Y el 21-08-2026 se comprobo que UNO de esos bastaba para perder la sesion. No por
un error: por un CUELGUE. Si la cabecera dBase declara `len_reg = 0` —lo que pasa
con una cabecera truncada— el bucle de lectura no termina NUNCA: `fh.read(0)`
devuelve b'' indefinidamente y la condicion de salida `len(rec) < len_reg` es
`0 < 0`, o sea False, para siempre. Medido: 100.000 vueltas sin salir.

Es la peor forma de fallar que existe: no da error, no acaba, y el que lo mira
piensa que sigue trabajando. Un error se ve en un minuto; un cuelgue se descubre
a las dos horas.

LA REGLA QUE SE COMPRUEBA AQUI
-------------------------------
    Un fichero roto es UNA LINEA EN EL INFORME, nunca una parada.

Y la de al lado, que importa igual: las cifras que salgan tienen que ser de los
ficheros BUENOS. Si un contenedor roto se cuela a medias y aporta datos basura,
el numero final esta contaminado y nadie lo sabe. Por eso no basta con que el
script termine: tiene que terminar con los mismos numeros que sin la basura.

REGLA DE DATOS: todo fabricado, directorio temporal, borrado al terminar.

Uso:  python3 ensayo_corpus_roto.py
"""
import io
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from ensayo_retro_semaforo import escribir_dbf, generar_corpus

resultados = []


#: Segundos que se le dan a cada ejecucion. Un corpus de siete ficheros rotos
#: tarda milisegundos: si pasa de esto, no es lentitud, es el cuelgue.
TOPE_SEGUNDOS = 60


def correr(argumentos):
    """Ejecuta y trata el CUELGUE como un fallo con nombre, no como una
    excepcion que se lleva la bateria por delante. Es lo que se esta probando:
    un timeout aqui ES el hallazgo, y tiene que salir en el informe."""
    try:
        r = subprocess.run(argumentos, capture_output=True, text=True,
                           cwd=AQUI, timeout=TOPE_SEGUNDOS)
        return r.returncode, r.stdout + r.stderr, False
    except subprocess.TimeoutExpired:
        return -1, (f"NO HA TERMINADO en {TOPE_SEGUNDOS}s: esto es el CUELGUE, "
                    f"no lentitud. Un fichero corrupto esta parando la medicion."), True


def comprobar(nombre, condicion, detalle=""):
    resultados.append((nombre, condicion))
    print(f"  [{'OK  ' if condicion else 'FALLA'}] {nombre}")
    if not condicion and detalle:
        print(f"           {detalle}")


#: Los campos SE LLAMAN COMO LOS DE VERDAD a proposito. La primera version de
#: esta trampa declaraba un campo "CAMPO", y retro_semaforo la descartaba antes
#: de entrar en el bucle de lectura (`if not (cA and cS): continue`), asi que la
#: prueba pasaba sin haber llegado nunca al sitio donde esta el cuelgue.
#:
#: Una trampa que no alcanza lo que quiere probar da un verde tranquilizador y
#: no prueba nada. Es la leccion de la FAMILIA G otra vez, aqui: hay que
#: comprobar que el ataque LLEGA, no solo que el sistema sobrevive.
CAMPOS_REALISTAS = ((b"ASIEN", 6), (b"SUBCTA", 12), (b"EURODEBE", 14),
                    (b"EUROHABER", 14), (b"FECHA", 8))


def cabecera_falsa(len_cab, len_reg, campos=CAMPOS_REALISTAS):
    c = bytearray(32)
    c[0] = 0x03
    struct.pack_into("<H", c, 8, len_cab)
    struct.pack_into("<H", c, 10, len_reg)
    out = bytes(c)
    for nombre, ancho in campos:
        d = bytearray(32)
        d[0:11] = nombre.ljust(11, b"\x00")[:11]
        d[11] = ord("C")
        d[16] = ancho
        out += bytes(d)
    return out + b"\x0d" + b"basura" * 500


def largo_cabecera(campos=CAMPOS_REALISTAS):
    return 32 + 32 * len(campos) + 1


def contenedor(ruta, contenido_dbf, nombre_interno="Diario.dbf"):
    with zipfile.ZipFile(ruta, "w") as z:
        z.writestr(nombre_interno, contenido_dbf)


def sembrar_basura(raiz):
    """Los ficheros rotos que de verdad aparecen en un archivo de diez anos."""
    mala = os.path.join(raiz, "CONTENEDORES_ROTOS")
    os.makedirs(mala, exist_ok=True)
    casos = {}

    # 1. EL CUELGUE: cabecera que declara longitud de registro cero.
    p = os.path.join(mala, "SP_C_R1A.DAT")
    contenedor(p, cabecera_falsa(largo_cabecera(), 0))
    casos["cabecera con len_reg = 0 (el cuelgue)"] = p

    # 2. Cabecera que miente: los anchos no suman la longitud de registro.
    #    Este es el peligroso de verdad: NO da error, lee campos desplazados y
    #    devuelve importes de una columna como si fueran de otra.
    p = os.path.join(mala, "SP_C_R2A.DAT")
    contenedor(p, cabecera_falsa(largo_cabecera(), 400))
    casos["cabecera que miente sobre los anchos"] = p

    # 3. Fichero truncado a mitad de cabecera.
    p = os.path.join(mala, "SP_C_R3A.DAT")
    contenedor(p, b"\x03\x00\x00\x00\x0a")
    casos["Diario.dbf truncado"] = p

    # 4. Contenedor sin Diario.dbf dentro.
    p = os.path.join(mala, "SP_C_R4A.DAT")
    contenedor(p, b"cualquier cosa", nombre_interno="Otro.dbf")
    casos["contenedor sin Diario.dbf"] = p

    # 5. Un .DAT que no es ni un ZIP.
    p = os.path.join(mala, "SP_C_R5A.DAT")
    with open(p, "wb") as f:
        f.write(b"esto no es un contenedor, es texto suelto\n" * 20)
    casos[".DAT que no es un contenedor"] = p

    # 6. ZIP vacio.
    p = os.path.join(mala, "SP_C_R6A.DAT")
    with zipfile.ZipFile(p, "w"):
        pass
    casos["contenedor vacio"] = p

    # 7. Diario.dbf de cero bytes.
    p = os.path.join(mala, "SP_C_R7A.DAT")
    contenedor(p, b"")
    casos["Diario.dbf de cero bytes"] = p
    return casos


def numeros_de(salida):
    """Extrae las cifras del informe para poder compararlas."""
    fuera = {}
    for linea in salida.splitlines():
        # Solo las lineas del INFORME, que empiezan por la etiqueta. Las de avance
        # ("... 5/7 contenedores (120 asientos leidos)") tambien contienen el
        # texto y colaban aqui: el helper reventaba con IndexError en cuanto se
        # anadio el indicador de progreso.
        limpia = linea.strip()
        for clave, etiqueta in (("asientos leidos", "asientos"),
                                ("evaluados por el motor", "evaluados")):
            if limpia.startswith(clave) and ":" in limpia:
                fuera[etiqueta] = int(limpia.split(":")[1].strip().replace(",", ""))
        if linea.strip().startswith(("VERDE", "AMBAR", "ROJO")):
            partes = linea.split()
            if len(partes) >= 2:
                fuera[partes[0]] = int(partes[1].replace(",", ""))
    return fuera


def main():
    print("=" * 72)
    print("CORPUS ROTO — un fichero corrupto no puede parar la medicion")
    print("=" * 72)
    tmp = tempfile.mkdtemp(prefix="corpus_roto_")
    try:
        # --- 1. cada fichero roto, por separado -------------------------
        print("\nCADA TIPO DE FICHERO ROTO, POR SEPARADO:")
        solo = tempfile.mkdtemp(prefix="solo_roto_", dir=tmp)
        casos = sembrar_basura(solo)
        for nombre, ruta in casos.items():
            suelto = tempfile.mkdtemp(dir=tmp)
            shutil.copy(ruta, os.path.join(suelto, os.path.basename(ruta)))
            codigo, salida_r, colgado = correr(
                [sys.executable, os.path.join(AQUI, "retro_semaforo.py"), suelto])
            comprobar(f"{nombre}: termina y no cuelga",
                      codigo == 0 and not colgado, salida_r[-300:])

        # .LLEGA la trampa a donde tiene que llegar? Sin esto, el verde de
        # arriba podria ser "el fichero se descarto antes" en vez de "el fichero
        # se leyo y no colgo". Son cosas muy distintas y solo una prueba algo.
        print("\n.LA TRAMPA ALCANZA EL SITIO DEL CUELGUE?")
        from retro_semaforo import parse_cabecera as _pc
        cabecera_ok = cabecera_falsa(largo_cabecera(), 1 + sum(a for _n, a in CAMPOS_REALISTAS))
        _lr, _cs = _pc(io.BytesIO(cabecera_ok))
        nombres = {c["nombre"] for c in _cs}
        comprobar("la trampa declara ASIEN y SUBCTA (si no, se descarta antes)",
                  {"ASIEN", "SUBCTA"} <= nombres, f"campos: {sorted(nombres)}")

        # --- 2. mezclado con un corpus bueno ----------------------------
        print("\nMEZCLADO CON UN CORPUS BUENO (lo que va a pasar de verdad):")
        limpio = os.path.join(tmp, "limpio")
        os.makedirs(limpio, exist_ok=True)
        generar_corpus(limpio, n_clientes=2, asientos_por_cliente=40)
        _c, salida_limpia, _t = correr(
            [sys.executable, os.path.join(AQUI, "retro_semaforo.py"), limpio])
        n_limpio = numeros_de(salida_limpia)

        sembrar_basura(limpio)
        codigo_s, salida, colgado_s = correr(
            [sys.executable, os.path.join(AQUI, "retro_semaforo.py"), limpio])
        n_sucio = numeros_de(salida)

        comprobar("el corpus mezclado termina", codigo_s == 0 and not colgado_s,
                  salida[-300:])
        comprobar("y DECLARA los ficheros que no ha podido leer",
                  "no se han podido" in salida.lower() or "incidencia" in salida.lower()
                  or "contenedor:" in salida or "fichero .DAT" in salida,
                  salida[-700:])
        # LA COMPROBACION QUE DE VERDAD IMPORTA: la basura no contamina.
        comprobar("las cifras son IDENTICAS a las del corpus limpio",
                  n_limpio == n_sucio and bool(n_limpio),
                  f"limpio={n_limpio}  con basura={n_sucio}")
        comprobar("ningun error se reporta con su mensaje (arrastran datos)",
                  "invalid literal" not in salida and "Traceback" not in salida,
                  salida[-400:])

        # --- 3. lo mismo para el agregador de IVA -----------------------
        print("\nEL AGREGADOR DE IVA, CON EL MISMO CORPUS SUCIO:")
        codigo_3, salida_3, colgado_3 = correr(
            [sys.executable, os.path.join(AQUI, "reconstruir_303.py"), limpio])
        comprobar("reconstruir_303.py termina con el corpus sucio",
                  codigo_3 == 0 and not colgado_3, salida_3[-300:])
        comprobar("y tambien declara lo que no ha podido clasificar",
                  "NO SE HA PODIDO CLASIFICAR" in salida_3.upper()
                  or "no es un contenedor" in salida_3, salida_3[-500:])

        # --- 4. control positivo ----------------------------------------
        print("\nCONTROL POSITIVO (.esta bateria sabria ver el cuelgue?):")
        # Se comprueba que la cabecera imposible SIGUE siendo rechazada por
        # parse_cabecera. Si alguien relaja esa comprobacion, el cuelgue vuelve
        # y esta bateria tiene que ser la que lo diga.
        from retro_semaforo import parse_cabecera
        colgaria = False
        try:
            len_reg, _ = parse_cabecera(io.BytesIO(cabecera_falsa(largo_cabecera(), 0)))
            colgaria = (len_reg == 0)
        except ValueError:
            colgaria = False
        comprobar("una cabecera con len_reg=0 sigue siendo RECHAZADA",
                  not colgaria,
                  "parse_cabecera la ha aceptado: el bucle de lectura no "
                  "terminaria nunca. Es el cuelgue del 21-08 otra vez.")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        for f in ("retro_semaforo_agregado.json", "retro_semaforo_LOCAL.json",
                  "reconstruccion_303_agregado.json"):
            ruta = os.path.join(AQUI, f)
            if os.path.exists(ruta):
                os.remove(ruta)

    fallos = [r for r in resultados if not r[1]]
    print()
    print("=" * 72)
    print(f"Pruebas: {len(resultados)}   en verde: {len(resultados)-len(fallos)}   "
          f"FALLAN: {len(fallos)}")
    if fallos:
        print("\nUN FICHERO ROTO PUEDE PARAR O CONTAMINAR LA MEDICION:")
        for nombre, _ in fallos:
            print(f"  · {nombre}")
        return 1
    print("\nUn fichero roto es una linea en el informe, no una parada — y las")
    print("cifras salen de los ficheros buenos, sin contaminar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
