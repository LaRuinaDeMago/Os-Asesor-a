#!/usr/bin/env python3
"""consolidar_identidad.py — cruza las tres senales de identidad
cliente<->carpeta ya construidas el 27-08-2026, en una sola vista para la
revision manual de Diego.

DE DONDE SALE ESTO
--------------------
La tercera entrada de sesion del 27-08-2026 (PROJECT_STATUS.md) concluyo, tras
tres intentos estadisticos fallidos, que este problema NO tiene la forma de
uno que la estadistica sola resuelva: no existe ningun conjunto de referencia
limpio en ninguno de los dos lados (ContaPlus <-> \\PC01\\Documentos). La
conclusion fue revision humana, con `cuadre_303_ficha.py --listar`. Ese
resultado sigue en pie: este script NO lo contradice ni reintenta resolverlo
solo.

Lo que SI faltaba: las tres senales construidas ese mismo dia (similitud de
nombre en `emparejar_carpetas.py`, agrupacion por proveedor en
`enlazador_clientes_303.py`, homogeneidad interna en
`diag_carpetas_multiempresa.py`) nunca se habian cruzado. Cada una vivia en
su propio informe. Este script las combina en una sola vista por carpeta de
ContaPlus, con corroboracion cruzada, para que la revision de las carpetas
ambiguas sea mas rapida y mejor informada -- no reemplaza el criterio de
Diego, se lo facilita.

QUE ANADE, CONCRETAMENTE, QUE NINGUNA DE LAS TRES POR SEPARADO TENIA
------------------------------------------------------------------------
- Si dos o mas carpetas de ContaPlus se agrupan como la MISMA empresa (por
  proveedores compartidos), pero su candidato de Documentos por NOMBRE no
  coincide entre ellas, es una discrepancia real que merece mirarse dos
  veces -- ninguno de los dos scripts por separado la puede ver, porque cada
  uno solo mira su propia senal.
- Si una carpeta de ContaPlus esta marcada como sospechosa de mezclar varias
  empresas reales, cualquier emparejamiento por nombre que se le proponga es
  sospechoso por construccion: puede que ni siquiera exista un "el cliente"
  singular al que emparejar.

ANADIDO 27-08-2026 (calibracion, tras la primera ejecucion real): la senal
SOSPECHOSA de `diag_carpetas_multiempresa.py` dio 27 de 27 (100%) contra el
corpus real -- una cifra que no se acepta sin comprobar, porque coincide con
un fallo "imposible" ya documentado en la cabecera de ese script. Puede ser
real (hay carpetas ya confirmadas que agrupan por equipo/copia) o el
artefacto de "sin continuidad temporal entre copias" que la tercera entrada
de hoy ya reprodujo con datos sinteticos (ver `diag_calibracion_sospechosa.py`
para la investigacion completa). Mientras esa pregunta se resuelve con datos
agregados, cada fila de AQUI ya lleva su propia calibracion barata: se cruza
SOSPECHOSA contra `suena_a_equipo()` (la misma pista de nombre que ya usa
`cuadre_303_ficha.py`) para distinguir, carpeta a carpeta, "corroborado por
nombre" de "posible artefacto, revisar con mas cautela".

CONFIRMADO 27-08-2026 (primera ejecucion real, corpus completo): la tasa de
sospechosas fue 100% TAMBIEN entre las carpetas que NO suenan a equipo (3 de
3) -- la firma exacta del artefacto, no de mezcla real (ver
`diag_calibracion_sospechosa.py`). Este script ahora llama a
`calcular_contingencia()` en cada ejecucion y, si el veredicto es
NO INFORMATIVA para ESE corpus concreto, deja de usar SOSPECHOSA para
priorizar la revision -- se sigue mostrando (transparencia), pero no compite
por la atencion de Diego con el mismo peso que una discrepancia real.

DISENO DE TRES ROLES, SIN EXCEPCION
--------------------------------------
Este script IMPORTA las funciones ya escritas y probadas de los otros tres
(nunca las duplica) y las ejecuta sobre las rutas reales que da Diego. Por
consola SOLO salen recuentos. El detalle completo -- con nombres reales de
carpeta -- va a un fichero que DEBE llevar _LOCAL en el nombre, igual que
`emparejar_carpetas.py`, `enlazador_clientes_303.py` y
`diag_carpetas_multiempresa.py`. Claude no lo abre nunca.

Uso:
    python consolidar_identidad.py "RUTA_CONTAPLUS" "RUTA_DOCUMENTOS"
    python consolidar_identidad.py "RUTA_CONTAPLUS" "RUTA_DOCUMENTOS" --detalle consolidado_LOCAL.txt
"""
import argparse
import difflib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from emparejar_carpetas import normalizar, jaccard_palabras, combinado, carpetas_de_nivel1
from enlazador_clientes_303 import calcular_grupos
from diag_carpetas_multiempresa import calcular_sospechosas
from diag_calibracion_sospechosa import calcular_contingencia
from cuadre_303_ficha import suena_a_equipo


def emparejar_por_nombre(carpetas_cp, carpetas_doc):
    """Top-3 candidatos de Documentos por carpeta de ContaPlus, reutilizando
    EXACTAMENTE la misma matematica de puntuacion que emparejar_carpetas.py
    (importada, no reescrita, para que las dos herramientas nunca puedan
    divergir en silencio). Devuelve {carpeta_cp: [(doc, comb), ...] x3}."""
    norm_doc = [(n, normalizar(n)) for n in carpetas_doc]
    resultado = {}
    for cp in carpetas_cp:
        n_cp = normalizar(cp)
        puntuados = []
        for doc, n_doc in norm_doc:
            char_r = difflib.SequenceMatcher(None, n_cp, n_doc).ratio()
            jac = jaccard_palabras(n_cp, n_doc)
            puntuados.append((combinado(char_r, jac), doc))
        puntuados.sort(reverse=True)
        top3 = puntuados[:3]
        while len(top3) < 3:
            top3.append((0.0, ""))
        resultado[cp] = top3
    return resultado


def consolidar(raiz_contaplus, raiz_documentos, max_difusion=0.30, min_nifs=3):
    """Ejecuta las tres senales y las cruza. Devuelve (stats, filas) donde
    stats son los recuentos para consola y filas es la lista completa (con
    nombres reales) SOLO para quien escriba el fichero _LOCAL."""
    carpetas_cp = carpetas_de_nivel1(raiz_contaplus)
    carpetas_doc = carpetas_de_nivel1(raiz_documentos)

    nombres = emparejar_por_nombre(carpetas_cp, carpetas_doc)
    r_grupos = calcular_grupos(raiz_contaplus, max_difusion)
    r_sosp = calcular_sospechosas(raiz_contaplus, min_nifs, max_difusion)

    # carpeta_real -> nombre de su grupo hermano (si esta en un grupo de 2+)
    hermanas_de = {}
    for _lider, miembros in r_grupos["grupos_reales"].items():
        if len(miembros) >= 2:
            for m in miembros:
                hermanas_de[m] = sorted(n for n in miembros if n != m)

    sospechosas = set()
    calibracion = {"informativa": None, "tasa_equipo": None, "tasa_no_equipo": None,
                   "n_equipo": 0, "n_no_equipo": 0}
    if r_sosp:
        detalle_sosp = r_sosp["n_grupos_por_carpeta_real"]
        sospechosas = {n for n, g in detalle_sosp.items() if g >= 2}
        calibracion = calcular_contingencia(detalle_sosp)

    filas = []
    n_con_hermanas = 0
    n_discrepancia = 0
    n_sospechosa_corroborada = 0
    n_sospechosa_sin_corroborar = 0
    n_alta_sin_aviso = 0

    for cp in carpetas_cp:
        top3 = nombres.get(cp, [(0.0, "")] * 3)
        candidato_top1 = top3[0][1]
        hermanas = hermanas_de.get(cp, [])
        es_sospechosa = cp in sospechosas
        # Calibracion barata, carpeta a carpeta: la misma pista de nombre que
        # ya usa cuadre_303_ficha.py para saber si una carpeta agrupa por
        # equipo/copia en vez de por cliente. No decide nada por si sola --
        # solo distingue "sospechosa corroborada por el nombre" de
        # "sospechosa sin corroborar, posible artefacto de continuidad
        # temporal" (ver diag_calibracion_sospechosa.py para el porque).
        equipo = suena_a_equipo(cp)

        discrepancia = False
        if hermanas:
            n_con_hermanas += 1
            for h in hermanas:
                candidato_hermana = nombres.get(h, [(0.0, "")])[0][1]
                if candidato_hermana and candidato_top1 and candidato_hermana != candidato_top1:
                    discrepancia = True
        if discrepancia:
            n_discrepancia += 1
        if es_sospechosa:
            if equipo:
                n_sospechosa_corroborada += 1
            else:
                n_sospechosa_sin_corroborar += 1
        if not hermanas and not es_sospechosa and top3[0][0] >= 0.75:
            n_alta_sin_aviso += 1

        filas.append({
            "carpeta": cp,
            "top3": top3,
            "hermanas": hermanas,
            "discrepancia": discrepancia,
            "sospechosa": es_sospechosa,
            "nombre_sugiere_equipo": equipo,
        })

    stats = {
        "n_carpetas_cp": len(carpetas_cp),
        "n_carpetas_doc": len(carpetas_doc),
        "n_con_hermanas": n_con_hermanas,
        "n_discrepancia": n_discrepancia,
        "n_sospechosa_corroborada": n_sospechosa_corroborada,
        "n_sospechosa_sin_corroborar": n_sospechosa_sin_corroborar,
        "n_alta_sin_aviso": n_alta_sin_aviso,
        "calibracion_sospechosa": calibracion,
    }
    return stats, filas


def escribir_consolidado(filas, ruta_salida, sospechosa_informativa=None):
    """sospechosa_informativa: el veredicto de calcular_contingencia() para
    ESTE corpus (True/False/None). Si es False -- probado que SOSPECHOSA no
    distingue nada aqui -- la marca se sigue mostrando (transparencia,
    ninguna informacion se descarta) pero deja de competir por prioridad con
    una discrepancia real o incluso con la confianza normal del nombre."""
    sospechosa_pesa = sospechosa_informativa is not False

    def prioridad(fila):
        # Primero lo que mas merece revision. Dentro de "sospechosa", la
        # corroborada por nombre (probable mezcla real) va antes que la que
        # no -- salvo que la calibracion de ESTE corpus ya haya demostrado
        # que SOSPECHOSA no informa nada, en cuyo caso no se le da prioridad
        # sobre la confianza normal del nombre.
        sospechosa_corroborada = (fila["sospechosa"] and fila["nombre_sugiere_equipo"]
                                   and sospechosa_pesa)
        sospechosa_sin_corroborar = (fila["sospechosa"] and not fila["nombre_sugiere_equipo"]
                                      and sospechosa_pesa)
        return (not fila["discrepancia"], not sospechosa_corroborada,
                not sospechosa_sin_corroborar, -fila["top3"][0][0])

    orden = sorted(filas, key=prioridad)
    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write("IDENTIDAD CONSOLIDADA: NOMBRE + GRUPO POR PROVEEDOR + AVISO DE MEZCLA\n")
        f.write("=" * 78 + "\n\n")
        if sospechosa_informativa is False:
            f.write("AVISO: en este corpus se comprobo que SOSPECHOSA no distingue\n")
            f.write("nada (ver diag_calibracion_sospechosa.py) -- se sigue marcando\n")
            f.write("por transparencia, pero NO se usa para ordenar la prioridad.\n\n")
        f.write("Orden: primero lo que mas merece revision (discrepancia entre\n")
        f.write("carpetas hermanas")
        if sospechosa_pesa:
            f.write(", despues mezcla corroborada por el nombre,\n")
            f.write("despues mezcla SIN corroborar -- esta ultima puede ser un\n")
            f.write("artefacto de medicion, ver diag_calibracion_sospechosa.py),\n")
        else:
            f.write("),\n")
        f.write("despues por confianza del nombre (baja primero). Si una carpeta\n")
        f.write("no tiene ningun aviso y el candidato principal es ALTA, no hace\n")
        f.write("falta revisarla con calma.\n\n")
        f.write("-" * 78 + "\n")
        for fila in orden:
            avisos = []
            if fila["discrepancia"]:
                avisos.append("DISCREPANCIA: sus hermanas (mismo proveedor) no "
                               "eligen el mismo candidato de nombre")
            if fila["sospechosa"]:
                sufijo_calibracion = ("" if sospechosa_pesa else
                                       " [NO INFORMATIVA en este corpus, no "
                                       "usada para priorizar]")
                if fila["nombre_sugiere_equipo"]:
                    avisos.append("SOSPECHOSA de mezclar varias empresas reales, "
                                   "CORROBORADA por el nombre (suena a equipo/copia)"
                                   + sufijo_calibracion)
                else:
                    avisos.append("SOSPECHOSA de mezclar varias empresas reales, "
                                   "SIN corroborar por el nombre -- posible "
                                   "artefacto de continuidad temporal, revisar "
                                   "con mas cautela antes de descartar la carpeta"
                                   + sufijo_calibracion)
            marca_avisos = ("  <<< " + " | ".join(avisos)) if avisos else ""
            f.write(f"\nContaPlus: {fila['carpeta']!r}{marca_avisos}\n")
            if fila["hermanas"]:
                f.write(f"    agrupada por proveedor con: "
                        f"{fila['hermanas']!r} (misma empresa, segun NIF)\n")
            for puesto, (comb, doc) in enumerate(fila["top3"], start=1):
                if not doc:
                    continue
                f.write(f"    puesto {puesto} ({comb:.2f}) -> {doc!r}\n")
        f.write("\n" + "-" * 78 + "\n")
    return orden


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("contaplus", help="Raiz del corpus de ContaPlus")
    ap.add_argument("documentos", help="Raiz del archivo de documentos (\\\\PC01\\Documentos)")
    ap.add_argument("--detalle", default="consolidado_LOCAL.txt",
                    help="Fichero con el detalle (nombres reales). DEBE llevar "
                         "_LOCAL en el nombre.")
    ap.add_argument("--max-difusion", type=float, default=0.30)
    ap.add_argument("--min-nifs", type=int, default=3)
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

    print("Cruzando las tres senales (nombre, proveedor compartido, "
          "homogeneidad interna)...")
    print("Esto puede tardar: recorre el corpus de ContaPlus dos veces "
          "(enlazador + diagnostico de mezcla) ademas de comparar nombres.")

    stats, filas = consolidar(args.contaplus, args.documentos,
                               args.max_difusion, args.min_nifs)

    print()
    print("=" * 60)
    print("RESULTADO DE LA CONSOLIDACION")
    print("=" * 60)
    print(f"  ContaPlus: {stats['n_carpetas_cp']} carpetas.  "
          f"Documentos: {stats['n_carpetas_doc']} carpetas.")
    print(f"  carpetas en un grupo multi-carpeta (misma empresa, por "
          f"proveedor): {stats['n_con_hermanas']}")
    print(f"  de esas, con DISCREPANCIA de candidato de nombre entre "
          f"hermanas (revisar primero): {stats['n_discrepancia']}")

    calib = stats["calibracion_sospechosa"]
    informativa = calib["informativa"]
    if informativa is None:
        print("  calibracion de SOSPECHOSA: NO_COMPROBADO (sin carpetas de "
              "nombre 'cliente concreto' con las que contrastar)")
    elif informativa:
        print(f"  calibracion de SOSPECHOSA: INFORMATIVA (tasa entre las que "
              f"no suenan a equipo: {calib['tasa_no_equipo']:.0%}) -- se usa "
              f"para priorizar")
    else:
        print(f"  calibracion de SOSPECHOSA: NO INFORMATIVA (tasa entre las "
              f"que no suenan a equipo: {calib['tasa_no_equipo']:.0%}, "
              f"tambien alta) -- NO se usa para priorizar, ver "
              f"diag_calibracion_sospechosa.py")
    print(f"  carpetas SOSPECHOSAS de mezclar empresas, CORROBORADO por el "
          f"nombre: {stats['n_sospechosa_corroborada']}")
    print(f"  carpetas SOSPECHOSAS SIN corroborar por el nombre: "
          f"{stats['n_sospechosa_sin_corroborar']}")
    print(f"  carpetas SIN ningun aviso y con nombre en confianza ALTA "
          f"(no hace falta revisar con calma): {stats['n_alta_sin_aviso']}")

    ruta_detalle = os.path.abspath(args.detalle)
    escribir_consolidado(filas, ruta_detalle, informativa)

    print()
    print(f"Detalle con los nombres (LOCAL, no lo pegues en el chat): {ruta_detalle}")
    print()
    print("COMO SE LEE:")
    print("  El fichero esta ordenado por prioridad de revision: primero las")
    print("  discrepancias y los avisos de mezcla, despues por confianza del")
    print("  nombre (baja primero). Lo de mas abajo del todo es lo que ya")
    print("  esta claro y no necesita que lo mires con calma.")
    print("  Esto NO sustituye tu criterio -- solo lo ordena para que no")
    print("  pierdas tiempo repasando 24 carpetas en el mismo orden cada vez.")
    print("  Trae solo los NUMEROS de arriba, nunca el fichero de detalle.")


if __name__ == "__main__":
    main()
