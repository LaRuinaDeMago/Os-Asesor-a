#!/usr/bin/env python3
"""emparejar_carpetas.py — empareja las carpetas del corpus de ContaPlus con
las de \\PC01\\Documentos por SIMILITUD DE NOMBRE, sin estadistica de datos.

DE DONDE SALE ESTO
--------------------
El 27-08-2026 se intento resolver la identidad cliente<->carpeta con tres
tecnicas estadisticas indirectas (huella de NIF, similitud de proveedores,
cruce de importes) porque el modelo no puede leer un nombre de carpeta real.
Las tres fallaron o dieron resultados ambiguos, y con razon: intentaban
ADIVINAR por contenido contable algo que ya esta escrito, en texto plano,
en el nombre de las dos carpetas -- tu las llamaste igual, o casi igual, en
los dos sitios. Comparar CONTENIDO cuando el nombre ya lo dice es resolver
el problema por el camino mas dificil.

QUE HACE, Y SIGUE SIENDO DISEÑO DE TRES ROLES
-------------------------------------------------
Compara el nombre de cada carpeta del corpus de ContaPlus contra el nombre
de cada carpeta de \\PC01\\Documentos, con similitud de texto (no de datos:
nunca abre un .DAT ni un PDF). Para cada carpeta de ContaPlus, propone la
carpeta de Documentos mas parecida y una puntuacion.

La diferencia con todo lo de hoy: el detalle (los propios nombres,
emparejados) va a un fichero `_LOCAL` que Diego revisa el mismo, en su
pantalla. Por consola solo salen RECUENTOS: cuantas propuestas salieron con
confianza alta, media o baja -- nunca un nombre.

Uso:
    python emparejar_carpetas.py "RUTA_CONTAPLUS" "RUTA_DOCUMENTOS"
    python emparejar_carpetas.py "RUTA_CONTAPLUS" "RUTA_DOCUMENTOS" --detalle emparejado_LOCAL.txt

REGLA DE DATOS: lo ejecuta el titular. El fichero de detalle lleva nombres
reales de carpeta -- por eso su nombre por defecto lleva _LOCAL, protegido
por .gitignore. Por consola, solo tres numeros.
"""
import argparse
import difflib
import os
import re
import sys
import unicodedata

# INTENTO RETIRADO el 27-08-2026, tras la SEGUNDA ejecucion real: hubo aqui
# un filtro por palabras clave ("facturas", "general", "administracion"...)
# para descartar carpetas de Documentos que no fueran de cliente. RESULTADO:
# las coincidencias de confianza ALTA cayeron de 14 a 0. La unica explicacion
# es que el filtro descarto CANDIDATOS CORRECTOS -- un nombre de negocio real
# perfectamente puede contener "General" (una ferreteria), "Administracion"
# (una administracion de fincas) o "Varios" en su propio nombre. Adivinar por
# palabra clave sobre un nombre de negocio real es exactamente el tipo de
# atajo fragil que este proyecto lleva todo el dia demostrando que falla.
# Retirado sin sustituto: mejor mostrar mas candidatos y dejar que Diego
# decida, que ocultar el correcto por una coincidencia de palabra.


def normalizar(nombre):
    """Nombre de carpeta -> forma comparable: sin acentos, minusculas, sin
    sufijos societarios ni puntuacion. 'Garcia e Hijos, S.L.' y 'GARCIA E
    HIJOS SL' deben normalizar igual."""
    s = unicodedata.normalize("NFKD", nombre)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r'\b(s\.?l\.?u?\.?|s\.?a\.?|c\.?b\.?|s\.?c\.?p\.?)\b', ' ', s)
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def carpetas_de_nivel1(raiz):
    return sorted(n for n in os.listdir(raiz)
                  if os.path.isdir(os.path.join(raiz, n)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("contaplus", help="Raiz del corpus de ContaPlus")
    ap.add_argument("documentos", help="Raiz del archivo de documentos (\\\\PC01\\Documentos)")
    ap.add_argument("--detalle", default="emparejado_LOCAL.txt",
                    help="Fichero con el detalle (nombres reales). DEBE llevar "
                         "_LOCAL en el nombre.")
    ap.add_argument("--umbral-alto", type=float, default=0.75)
    ap.add_argument("--umbral-medio", type=float, default=0.45)
    args = ap.parse_args()

    if "_LOCAL" not in os.path.basename(args.detalle):
        print("ERROR: --detalle debe contener _LOCAL en el nombre: lleva "
              "nombres de carpeta reales.", file=sys.stderr)
        sys.exit(1)

    for etiqueta, ruta in (("ContaPlus", args.contaplus), ("Documentos", args.documentos)):
        if not os.path.isdir(ruta):
            print(f"ERROR: la ruta de {etiqueta} no existe: comprueba el argumento.",
                  file=sys.stderr)
            sys.exit(2)

    carpetas_cp = carpetas_de_nivel1(args.contaplus)
    carpetas_doc = carpetas_de_nivel1(args.documentos)
    if not carpetas_cp or not carpetas_doc:
        print("ERROR: una de las dos raices no tiene subcarpetas.", file=sys.stderr)
        sys.exit(2)

    print(f"ContaPlus: {len(carpetas_cp)} carpetas.  "
          f"Documentos: {len(carpetas_doc)} carpetas.")
    print("Comparando nombres (no contenido)...")

    norm_doc = [(n, normalizar(n)) for n in carpetas_doc]

    # Se guardan los 3 mejores candidatos, no solo 2 -- sin filtro de
    # genericas, con 140 candidatos hace falta mas contexto para que Diego
    # decida el mismo, en vez de intentar adivinarlo por palabra clave.
    resultados = []   # (carpeta_cp, [(doc, score), (doc, score), (doc, score)])
    for cp in carpetas_cp:
        n_cp = normalizar(cp)
        puntuados = sorted(
            ((difflib.SequenceMatcher(None, n_cp, n_doc).ratio(), doc)
             for doc, n_doc in norm_doc),
            reverse=True)[:3]
        top3 = [(doc, score) for score, doc in puntuados]
        while len(top3) < 3:
            top3.append(("", 0.0))
        resultados.append((cp, top3))

    def mejor(top3):
        return top3[0]

    altos = sum(1 for _c, t in resultados if mejor(t)[1] >= args.umbral_alto)
    medios = sum(1 for _c, t in resultados
                if args.umbral_medio <= mejor(t)[1] < args.umbral_alto)
    bajos = sum(1 for _c, t in resultados if mejor(t)[1] < args.umbral_medio)
    # CORREGIDO tras la primera ejecucion real: un candidato YA casi perfecto
    # (>= umbral_seguro) no es ambiguo aunque el segundo tambien puntue alto
    # -- eso pasa cuando el mismo cliente tiene dos carpetas legitimas en
    # Documentos (actual + historica), no cuando el emparejamiento es
    # dudoso. Antes esto marcaba 37 de 37 como "ambiguas" sin distinguir.
    UMBRAL_SEGURO = 0.90

    def es_ambiguo(score, score2):
        if score < args.umbral_medio:
            return False
        if score >= UMBRAL_SEGURO:
            return False
        return (score - score2) < 0.10

    ambiguos = sum(1 for _c, t in resultados if es_ambiguo(t[0][1], t[1][1]))

    print()
    print("=" * 60)
    print("RESULTADO DEL EMPAREJAMIENTO POR NOMBRE")
    print("=" * 60)
    print(f"  confianza ALTA  (>= {args.umbral_alto:.2f}): {altos}")
    print(f"  confianza MEDIA ({args.umbral_medio:.2f}-{args.umbral_alto:.2f}): {medios}")
    print(f"  confianza BAJA  (< {args.umbral_medio:.2f}): {bajos}")
    print(f"  de esas, AMBIGUAS (el segundo candidato casi igual de bueno): {ambiguos}")

    ruta_detalle = os.path.abspath(args.detalle)
    with open(ruta_detalle, "w", encoding="utf-8") as f:
        f.write("EMPAREJAMIENTO CONTAPLUS <-> DOCUMENTOS, POR NOMBRE\n")
        f.write("=" * 78 + "\n\n")
        f.write("Revisa cada linea. Si el emparejamiento es correcto, no hace\n")
        f.write("falta anotar nada mas -- ya sabes que esa carpeta de ContaPlus\n")
        f.write("es ese cliente. Si esta mal o es ambiguo, mira el 2o y 3er\n")
        f.write("candidato: no se ha filtrado nada, asi que el correcto puede\n")
        f.write("estar ahi en vez de en el primer puesto.\n\n")
        for cp, top3 in sorted(resultados, key=lambda r: -r[1][0][1]):
            score = top3[0][1]
            marca = "ALTA " if score >= args.umbral_alto else (
                     "MEDIA" if score >= args.umbral_medio else "BAJA ")
            amb = "  <- AMBIGUO, revisar" if es_ambiguo(top3[0][1], top3[1][1]) else ""
            f.write(f"[{marca}] ContaPlus: {cp!r}\n")
            for puesto, (doc, s) in enumerate(top3, start=1):
                if not doc:
                    continue
                f.write(f"    puesto {puesto} ({s:.2f}) -> {doc!r}"
                        f"{amb if puesto == 1 else ''}\n")
            f.write("\n")

    print()
    print(f"Detalle con los nombres (LOCAL, no lo pegues en el chat): {ruta_detalle}")
    print()
    print("COMO SE LEE:")
    print("  - ALTA: casi seguro que es el mismo cliente en los dos sitios.")
    print("  - MEDIA/BAJA/AMBIGUA: hay que mirarlo a mano -- el fichero de detalle")
    print("    trae el 2o y 3er candidato tambien, por si el correcto no es el")
    print("    primero. No se ha descartado ninguna carpeta de antemano.")
    print("  Trae solo los TRES NUMEROS de arriba, no el fichero de detalle.")


if __name__ == "__main__":
    main()
