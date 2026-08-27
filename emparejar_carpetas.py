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

ANADIDO 28-08-2026 (sesion Cloud): la comparacion ya no es solo por texto
seguido (difflib.SequenceMatcher). Las razones sociales espanolas cambian de
orden con frecuencia -- 'Hermanos Perez SL' en ContaPlus y 'Perez Hermanos'
en Documentos es el mismo cliente, pero por texto seguido solo puntuaban
0.57 (MEDIA, exige revision manual); por CONJUNTO de palabras (ignora el
orden) puntuan 1.00. Ahora se usa el MAXIMO de las dos senales para elegir,
ordenar y clasificar los candidatos -- nunca un promedio que pueda bajar lo
que ya funcionaba, y nunca puede hacer que un candidato desaparezca del
top-3: solo puede rescatar uno que el orden de palabras escondia. Tambien
nuevo: deteccion de COLISIONES (dos carpetas de ContaPlus distintas con el
mismo candidato principal) -- antes no se detectaba, y siempre merece
revision (puede ser normal o un error, nunca se resuelve solo).

Uso:
    python emparejar_carpetas.py "RUTA_CONTAPLUS" "RUTA_DOCUMENTOS"
    python emparejar_carpetas.py "RUTA_CONTAPLUS" "RUTA_DOCUMENTOS" --detalle emparejado_LOCAL.txt

REGLA DE DATOS: lo ejecuta el titular. El fichero de detalle lleva nombres
reales de carpeta -- por eso su nombre por defecto lleva _LOCAL, protegido
por .gitignore. Por consola, solo los numeros del resumen.
"""
import argparse
import difflib
import os
import re
import sys
import unicodedata
from collections import defaultdict

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


def jaccard_palabras(n1, n2):
    """Coincidencia por CONJUNTO de palabras, no por texto seguido. Anadido
    28-08-2026: el emparejamiento original solo usaba difflib.SequenceMatcher
    (similitud de caracteres en el MISMO orden), y las razones sociales
    espanolas cambian de orden con mucha frecuencia -- 'Hermanos Perez SL' en
    ContaPlus y 'Perez Hermanos' en Documentos es el mismo cliente, pero
    SequenceMatcher solo les da 0.57 (cae en MEDIA, exige revision manual)
    porque compara caracter a caracter en orden. Por palabras, coinciden al
    100%. No sustituye a la similitud de caracteres -- la complementa: ver
    combinado() mas abajo, que nunca hace bajar una puntuacion, solo puede
    rescatar un caso que el orden de palabras esconde."""
    t1, t2 = set(n1.split()), set(n2.split())
    if not t1 or not t2:
        return 0.0
    return len(t1 & t2) / len(t1 | t2)


def combinado(char_ratio, jaccard):
    """El maximo de las dos senales, nunca un promedio que pueda bajar lo que
    ya funcionaba. Coherente con la regla ya aprendida el 27-08 con el filtro
    de palabras clave retirado: mejor rescatar un candidato de mas que
    esconder el correcto."""
    return max(char_ratio, jaccard)


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
    #
    # ANADIDO 28-08-2026: la seleccion y el orden de los 3 candidatos ya usan
    # combinado() (texto seguido + palabras), no solo texto seguido. Antes,
    # un candidato correcto con las palabras en otro orden podia quedar FUERA
    # del top-3 por su char_ratio bajo, y Diego nunca llegaba a verlo -- el
    # mismo problema de fondo que el filtro de palabras clave retirado el
    # 27-08 (esconder el correcto), solo que por omision en vez de filtro
    # explicito.
    resultados = []   # (carpeta_cp, [(doc, char, jaccard, combinado), ...] x3)
    for cp in carpetas_cp:
        n_cp = normalizar(cp)
        puntuados = []
        for doc, n_doc in norm_doc:
            char_r = difflib.SequenceMatcher(None, n_cp, n_doc).ratio()
            jac = jaccard_palabras(n_cp, n_doc)
            puntuados.append((combinado(char_r, jac), char_r, jac, doc))
        puntuados.sort(reverse=True)
        top3 = [(doc, char_r, jac, comb) for comb, char_r, jac, doc in puntuados[:3]]
        while len(top3) < 3:
            top3.append(("", 0.0, 0.0, 0.0))
        resultados.append((cp, top3))

    def mejor(top3):
        doc, char_r, jac, comb = top3[0]
        return doc, comb

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

    ambiguos = sum(1 for _c, t in resultados if es_ambiguo(t[0][3], t[1][3]))

    # ANADIDO 28-08-2026: colisiones -- dos carpetas de ContaPlus DISTINTAS
    # eligiendo la MISMA carpeta de Documentos como su candidato principal.
    # No lo detectaba nada antes. No es necesariamente un error (puede ser
    # una empresa con dos altas en ContaPlus, o una carpeta que agrupa a
    # varios clientes en Documentos) pero SIEMPRE merece que Diego lo mire
    # dos veces -- por eso se cuenta y se marca, nunca se resuelve solo.
    top1_por_doc = defaultdict(list)
    for cp, top3 in resultados:
        doc_top1 = top3[0][0]
        if doc_top1:
            top1_por_doc[doc_top1].append(cp)
    colisiones = {doc: cps for doc, cps in top1_por_doc.items() if len(cps) > 1}

    print()
    print("=" * 60)
    print("RESULTADO DEL EMPAREJAMIENTO POR NOMBRE")
    print("=" * 60)
    print(f"  confianza ALTA  (>= {args.umbral_alto:.2f}): {altos}")
    print(f"  confianza MEDIA ({args.umbral_medio:.2f}-{args.umbral_alto:.2f}): {medios}")
    print(f"  confianza BAJA  (< {args.umbral_medio:.2f}): {bajos}")
    print(f"  de esas, AMBIGUAS (el segundo candidato casi igual de bueno): {ambiguos}")
    print(f"  COLISIONES (2+ carpetas de ContaPlus con el mismo candidato principal): "
          f"{len(colisiones)}")

    ruta_detalle = os.path.abspath(args.detalle)
    with open(ruta_detalle, "w", encoding="utf-8") as f:
        f.write("EMPAREJAMIENTO CONTAPLUS <-> DOCUMENTOS, POR NOMBRE\n")
        f.write("=" * 78 + "\n\n")
        f.write("Revisa cada linea. Si el emparejamiento es correcto, no hace\n")
        f.write("falta anotar nada mas -- ya sabes que esa carpeta de ContaPlus\n")
        f.write("es ese cliente. Si esta mal o es ambiguo, mira el 2o y 3er\n")
        f.write("candidato: no se ha filtrado nada, asi que el correcto puede\n")
        f.write("estar ahi en vez de en el primer puesto.\n\n")
        f.write("La puntuacion es el MAXIMO de dos senales: similitud de texto\n")
        f.write("seguido y similitud por conjunto de palabras (ignora el orden).\n")
        f.write("Si ves '[por palabras]', el texto seguido solo no llegaba: el\n")
        f.write("nombre esta escrito con las palabras en otro orden.\n\n")
        for cp, top3 in sorted(resultados, key=lambda r: -r[1][0][3]):
            comb1 = top3[0][3]
            marca = "ALTA " if comb1 >= args.umbral_alto else (
                     "MEDIA" if comb1 >= args.umbral_medio else "BAJA ")
            amb = "  <- AMBIGUO, revisar" if es_ambiguo(top3[0][3], top3[1][3]) else ""
            colision = top3[0][0] in colisiones
            f.write(f"[{marca}] ContaPlus: {cp!r}\n")
            for puesto, (doc, char_r, jac, comb) in enumerate(top3, start=1):
                if not doc:
                    continue
                nota_palabras = "  [por palabras]" if jac > char_r + 0.15 else ""
                nota_amb = amb if puesto == 1 else ""
                nota_colision = ""
                if puesto == 1 and colision:
                    otras = [c for c in colisiones[doc] if c != cp]
                    nota_colision = ("  <- COLISION: tambien es el candidato "
                                      f"principal de: {otras!r}")
                f.write(f"    puesto {puesto} ({comb:.2f}) -> {doc!r}"
                        f"{nota_palabras}{nota_amb}{nota_colision}\n")
            f.write("\n")

    print()
    print(f"Detalle con los nombres (LOCAL, no lo pegues en el chat): {ruta_detalle}")
    print()
    print("COMO SE LEE:")
    print("  - ALTA: casi seguro que es el mismo cliente en los dos sitios.")
    print("  - MEDIA/BAJA/AMBIGUA: hay que mirarlo a mano -- el fichero de detalle")
    print("    trae el 2o y 3er candidato tambien, por si el correcto no es el")
    print("    primero. No se ha descartado ninguna carpeta de antemano.")
    print("  - COLISION: dos carpetas de ContaPlus distintas compiten por el mismo")
    print("    candidato -- puede ser normal (misma empresa dos altas) o un error,")
    print("    revisar siempre a mano, nunca se resuelve solo.")
    print("  Trae solo los NUMEROS de arriba, no el fichero de detalle.")


if __name__ == "__main__":
    main()
