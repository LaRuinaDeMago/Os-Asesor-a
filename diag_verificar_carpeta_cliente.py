#!/usr/bin/env python3
"""diag_verificar_carpeta_cliente.py — dentro de cada carpeta de nivel 1,
?los distintos codigos son la MISMA empresa a lo largo del tiempo, o hay
mas de una empresa real compartiendo carpeta?

Pregunta que decide si clave_cliente() puede simplificarse a "solo la
carpeta" (28 carpetas ~ 33 clientes, ver diag_profundidad_carpetas.py) o si
hace falta seguir distinguiendo por codigo dentro de algunas carpetas.

Metodo: para cada carpeta de nivel 1, se agrupan sus ficheros por el codigo
de 7 caracteres (el que ya usa clave_cliente). Si una carpeta tiene mas de
un codigo, se mide el solape de NIF de contrapartes ENTRE esos codigos. Alta
similitud sostenida = misma empresa en distintas copias. Una caida clara a
mitad de la lista = posible cambio de empresa real dentro de la carpeta.

Cada NIF se hashea nada mas leerlo. Nunca se imprime ni se guarda un nombre
de carpeta ni un NIF real, en ningun momento.

Uso:
    python diag_verificar_carpeta_cliente.py "RUTA_DEL_CORPUS"
"""
import hashlib
import os
import sys
import zipfile
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retro_semaforo import parse_cabecera, txt

MIN_NIFS = 3


def _h(valor):
    return hashlib.blake2b(valor.encode("utf-8", "replace"), digest_size=10).digest()


def main():
    raiz = os.path.abspath(sys.argv[1])

    # carpeta_hash -> codigo -> set(nif_hash)
    datos = defaultdict(lambda: defaultdict(set))
    errores = Counter()

    for dp, _, fns in os.walk(raiz):
        for n in fns:
            if os.path.splitext(n)[1].lower() != ".dat":
                continue
            ruta = os.path.join(dp, n)
            rel = os.path.relpath(ruta, raiz)
            partes = rel.split(os.sep)
            if len(partes) < 2:
                continue
            carpeta_h = _h(partes[0])
            codigo = n[:7]
            try:
                if not zipfile.is_zipfile(ruta):
                    continue
                with zipfile.ZipFile(ruta) as z:
                    nombre = next((i.filename for i in z.infolist()
                                   if not i.is_dir()
                                   and os.path.basename(i.filename).lower() == "diario.dbf"), None)
                    if nombre is None:
                        continue
                    with z.open(nombre) as fh:
                        len_reg, campos = parse_cabecera(fh)
                        idx = {c["nombre"]: c for c in campos}
                        cNIF = idx.get("TERNIF")
                        if not cNIF:
                            continue
                        while True:
                            rec = fh.read(len_reg)
                            if len(rec) < len_reg or rec[:1] == b"\x1a":
                                break
                            if rec[:1] == b"*":
                                continue
                            nif = txt(rec, cNIF)
                            if nif:
                                datos[carpeta_h][codigo].add(_h(nif))
                            del rec
            except Exception as e:
                errores[type(e).__name__] += 1

    print(f"{len(datos):,} carpetas de nivel 1 analizadas.")
    print("")

    n_un_codigo = 0
    n_multi_codigo_coherente = 0
    n_multi_codigo_sospechoso = 0
    detalle_sospechosos = []

    for carpeta_h, por_codigo in datos.items():
        codigos_utiles = {c: nifs for c, nifs in por_codigo.items() if len(nifs) >= MIN_NIFS}
        if len(codigos_utiles) <= 1:
            n_un_codigo += 1
            continue

        # Similitud de cada codigo contra la UNION de todos los DEMAS codigos
        # de la misma carpeta -- si un codigo esta muy alejado del resto,
        # puede ser una empresa real distinta compartiendo la carpeta.
        #
        # BUG REAL cazado en este mismo diagnostico: la primera version hacia
        # `nifs & (todos_juntos - nifs)`, que resta nifs de la union ANTES de
        # cruzarlo con nifs -- eso da SIEMPRE vacio (X contra NO-X), no mide
        # nada. El "max=0.0 en todas las carpetas" era la pista: con senal
        # real, el maximo no puede ser cero en TODAS a la vez. Corregido
        # construyendo "el resto" como la union de los OTROS codigos, sin
        # restar del total.
        # SEGUNDO bug del mismo diagnostico, distinto del primero: Jaccard
        # (interseccion/UNION) castiga fuerte cuando los dos conjuntos tienen
        # tamanos muy distintos -- que es EXACTAMENTE lo esperable aqui, si
        # las copias son acumulativas: la primera copia de una empresa tiene
        # pocas contrapartes (negocio joven), la ultima acumula una decada.
        # Aunque la pequena este ENTERAMENTE dentro de la grande, Jaccard sale
        # bajo solo por el tamano del denominador. La metrica correcta para
        # "es esto un subconjunto de aquello" es el coeficiente de solapamiento
        # (interseccion entre el MENOR de los dos, no la union).
        similitudes = []
        for c, nifs in codigos_utiles.items():
            resto = set()
            for c2, nifs2 in codigos_utiles.items():
                if c2 != c:
                    resto |= nifs2
            inter = len(nifs & resto)
            denominador = min(len(nifs), len(resto))
            sim = inter / denominador if denominador else 0.0
            similitudes.append(sim)

        similitudes.sort()
        # Sospechoso: el codigo peor conectado tiene una similitud muy baja
        # con el resto Y aun asi tiene señal propia suficiente (no es solo
        # ruido de pocos NIF).
        if similitudes and similitudes[0] < 0.05:
            n_multi_codigo_sospechoso += 1
            detalle_sospechosos.append((len(codigos_utiles), round(similitudes[0], 3), round(similitudes[-1], 3)))
        else:
            n_multi_codigo_coherente += 1

    print("=" * 66)
    print("RESULTADO, POR CARPETA:")
    print("=" * 66)
    print(f"  1 solo codigo util (nada que verificar)      : {n_un_codigo:,}")
    print(f"  2+ codigos, similitud sostenida (misma empresa): {n_multi_codigo_coherente:,}")
    print(f"  2+ codigos, con un codigo mal conectado (revisar): {n_multi_codigo_sospechoso:,}")

    if detalle_sospechosos:
        print("")
        print("  DETALLE de las sospechosas (nº codigos, similitud minima, maxima):")
        for n_cod, sim_min, sim_max in sorted(detalle_sospechosos):
            print(f"    {n_cod} codigos  ->  min={sim_min}  max={sim_max}")

    if errores:
        print(f"\nErrores: {dict(errores)}")

    print("")
    print("Si 'con un codigo mal conectado' es 0 o casi 0, la carpeta de nivel 1")
    print("SI es una identidad de cliente fiable, sin necesitar el codigo para")
    print("nada mas que informacion. Si hay varias, esas carpetas concretas")
    print("necesitan seguir distinguiendo por codigo (la regla dura del 12-08")
    print("sigue viva ahi, no en general).")


if __name__ == "__main__":
    main()
