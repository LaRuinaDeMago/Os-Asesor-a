#!/usr/bin/env python3
"""ensayo_emparejar_carpetas.py — ensayo en seco de emparejar_carpetas.py.

POR QUE HACE FALTA
--------------------
`emparejar_carpetas.py` se escribio el 27-08-2026 para resolver por nombre lo
que tres tecnicas estadisticas (huella de NIF, similitud de proveedores,
cruce de importes) no consiguieron resolver por contenido contable. En el
camino tuvo un defecto real, encontrado contra el corpus real, no en un
ensayo: un filtro de "carpetas genericas" por palabra clave (descartar
nombres con "general", "administracion", "varios"...) hizo caer las
coincidencias de confianza ALTA de 14 a 0, porque esas palabras aparecen
tambien en nombres de negocio REALES ("Ferreteria General",
"Administracion de Fincas X"). Retirado sin sustituto ese mismo dia.

Este ensayo fija en codigo los cuatro comportamientos que hoy se probaron a
mano, para que un cambio futuro no pueda reintroducir ese error sin que algo
se ponga rojo.

REGLA DE DATOS: todo inventado, en directorios temporales, borrado al
terminar. Ningun nombre real de cliente en ningun sitio de este fichero.

Uso:
    python ensayo_emparejar_carpetas.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AQUI = os.path.dirname(os.path.abspath(__file__))
FALLOS = []


def comprobar(titulo, condicion, detalle=""):
    if condicion:
        print(f"  OK  {titulo}")
    else:
        print(f"  FALLA  {titulo}   {detalle}")
        FALLOS.append(titulo)


def crear(raiz, nombres):
    for n in nombres:
        os.makedirs(os.path.join(raiz, n), exist_ok=True)


def ejecutar(cp, doc, detalle):
    r = subprocess.run(
        [sys.executable, os.path.join(AQUI, "emparejar_carpetas.py"),
         cp, doc, "--detalle", detalle],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r


def leer_detalle(ruta):
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def bloque_de(texto, nombre_cp):
    """El parrafo completo de una carpeta de ContaPlus en el detalle,
    incluida su marca [ALTA/MEDIA/BAJA] al principio de la linea -- sin
    depender de contar caracteres hacia atras, que es fragil si el formato
    de la linea cambia."""
    marcador = f"ContaPlus: '{nombre_cp}'"
    inicio_linea = texto.rindex("\n", 0, texto.index(marcador)) + 1
    fin = texto.find("\n\n", inicio_linea)
    return texto[inicio_linea:fin if fin != -1 else None]


def main():
    print("ENSAYO EN SECO: emparejar_carpetas.py")
    print("=" * 70)

    tmp = tempfile.mkdtemp(prefix="ensayo_emparejar_")
    try:
        cp = os.path.join(tmp, "contaplus")
        doc = os.path.join(tmp, "documentos")
        detalle = os.path.join(tmp, "detalle_LOCAL.txt")

        # CASO 1: variantes de escritura del MISMO nombre (mayusculas,
        # puntuacion, sufijo societario) deben emparejar con confianza alta.
        # CASO 2 (REGRESION del bug del 27-08): un nombre real que CONTIENE
        # una palabra "generica" (general, administracion) no debe perderse.
        # CASO 3: una carpeta de equipo/backup, sin ningun cliente parecido,
        # debe quedar en confianza baja, nunca emparejada con seguridad.
        # CASO 4: el mismo cliente con DOS carpetas legitimas en Documentos
        # (actual + historica) no debe marcarse como "ambiguo".
        # CASO 5 (28-08-2026, senal nueva): el MISMO nombre con las palabras
        # en OTRO orden ('Hermanos Perez SL' / 'Perez Hermanos') debe
        # rescatarse a confianza ALTA por coincidencia de palabras, aunque
        # por texto seguido solo de 0.57 (MEDIA). Caso real, no inventado
        # para que cuadre: es justo el ejemplo con el que se detecto el hueco.
        # CASO 6 (28-08-2026, deteccion nueva): dos carpetas de ContaPlus que
        # normalizan IGUAL (con/sin sufijo societario escrito distinto) deben
        # marcarse como COLISION al competir por la misma carpeta de
        # Documentos -- antes no se detectaba nada.
        crear(cp, [
            "GARCIA E HIJOS SL",
            "FERRETERIA GENERAL SL",
            "Contabilidad ordenador de Pepe",
            "TALLERES LOPEZ CB",
            "HERMANOS PEREZ SL",
            "TALLERES MARTINEZ SL",
            "TALLERES MARTINEZ, SL",
        ])
        crear(doc, [
            "Garcia e Hijos, S.L.",
            "Ferreteria General, S.L.",
            "Talleres Lopez C.B.",
            "Talleres Lopez CB - HISTORICO",
            "Restaurante Fernandez",
            "Facturas generales",
            "Administracion de Fincas Ruiz",
            "Perez Hermanos",
            "Talleres Martinez, S.L.",
        ])

        r = ejecutar(cp, doc, detalle)
        comprobar("el script corre sin error", r.returncode == 0, r.stderr[-500:])
        salida = r.stdout
        texto = leer_detalle(detalle) if os.path.exists(detalle) else ""

        comprobar("escribe el fichero de detalle", os.path.exists(detalle))
        comprobar("por consola NO aparece ningun nombre de carpeta real",
                  "Garcia" not in salida and "Ferreteria" not in salida
                  and "Lopez" not in salida and "Perez" not in salida
                  and "Martinez" not in salida,
                  "un nombre real se ha colado en la salida de consola")

        # --- Caso 1: variantes de escritura ---------------------------------
        comprobar("caso 1: 'GARCIA E HIJOS SL' empareja con 'Garcia e Hijos, S.L.'",
                  "ContaPlus: 'GARCIA E HIJOS SL'" in texto
                  and "puesto 1 (1.00) -> 'Garcia e Hijos, S.L" in texto)

        # --- Caso 2: REGRESION del filtro de palabras genericas -------------
        comprobar("caso 2 (REGRESION): 'FERRETERIA GENERAL SL' NO se pierde "
                  "por contener 'general'",
                  "ContaPlus: 'FERRETERIA GENERAL SL'" in texto
                  and "puesto 1 (1.00) -> 'Ferreteria General, S.L" in texto,
                  "si esto falla, alguien ha vuelto a filtrar por palabra clave")

        # --- Caso 3: carpeta de equipo, sin pareja real ----------------------
        bloque_pepe = bloque_de(texto, "Contabilidad ordenador de Pepe")
        comprobar("caso 3: la carpeta de equipo NO sale en confianza ALTA",
                  bloque_pepe.startswith("[MEDIA]") or bloque_pepe.startswith("[BAJA "),
                  bloque_pepe[:20])

        # --- Caso 4: dos carpetas legitimas del mismo cliente ----------------
        bloque_talleres = bloque_de(texto, "TALLERES LOPEZ CB")
        comprobar("caso 4: dos carpetas legitimas del mismo cliente -> "
                  "el puesto 1 NO se marca ambiguo",
                  "puesto 1 (1.00) -> 'Talleres Lopez C.B" in bloque_talleres
                  and "AMBIGUO" not in bloque_talleres.split("puesto 2")[0],
                  bloque_talleres[:150])
        comprobar("caso 4: la segunda carpeta del mismo cliente SI aparece "
                  "como puesto 2 (informativo, no es un error)",
                  "puesto 2" in bloque_talleres and "HISTORICO" in bloque_talleres)

        # --- Caso 5: rescate por palabras (orden invertido) -------------------
        bloque_perez = bloque_de(texto, "HERMANOS PEREZ SL")
        comprobar("caso 5: 'HERMANOS PEREZ SL' / 'Perez Hermanos' (orden "
                  "invertido) sube a confianza ALTA por palabras, no se queda "
                  "en 0.57 de texto seguido",
                  bloque_perez.startswith("[ALTA ]")
                  and "puesto 1 (1.00) -> 'Perez Hermanos'" in bloque_perez,
                  bloque_perez[:150])
        comprobar("caso 5: el detalle explica que el rescate fue por palabras",
                  "[por palabras]" in bloque_perez.split("\n")[1],
                  bloque_perez[:200])

        # --- Caso 6: colision (dos carpetas de ContaPlus, un solo candidato) --
        bloque_mart1 = bloque_de(texto, "TALLERES MARTINEZ SL")
        bloque_mart2 = bloque_de(texto, "TALLERES MARTINEZ, SL")
        comprobar("caso 6: las dos variantes de 'Talleres Martinez' se marcan "
                  "COLISION (compiten por la misma carpeta de Documentos)",
                  "COLISION" in bloque_mart1 and "COLISION" in bloque_mart2,
                  bloque_mart1[:200])
        comprobar("caso 6: el resumen de consola cuenta al menos 1 colision",
                  "COLISIONES" in salida and "COLISIONES (2+ carpetas de ContaPlus "
                  "con el mismo candidato principal): 1" in salida,
                  [l for l in salida.splitlines() if "COLISIONES" in l])

        # --- Recuento agregado: consistencia interna -------------------------
        comprobar("el recuento de consola declara 7 carpetas de ContaPlus",
                  "ContaPlus: 7 carpetas" in salida, salida[:120])

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("=" * 70)
    if FALLOS:
        print(f"FALLAN {len(FALLOS)}:")
        for f in FALLOS:
            print(f"  - {f}")
        sys.exit(1)
    print("El ensayo pasa. El emparejamiento por nombre hace lo que dice, "
          "y el bug del filtro de palabras genericas sigue sin volver.")


if __name__ == "__main__":
    main()
