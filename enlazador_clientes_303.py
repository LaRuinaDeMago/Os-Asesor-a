#!/usr/bin/env python3
"""enlazador_clientes_303.py — agrupa los cubos (carpeta+codigo) de
reconstruir_303.py en clientes reales, usando el solape de NIF de
contrapartes: la misma tecnica de "huella dactilar" ya validada en este
proyecto (PROJECT_STATUS.md, 12-08-2026: histograma bimodal, meseta estable
de 35 grupos, verificado a mano) -- reaplicada aqui a grano mas fino, cubo a
cubo en vez de carpeta a carpeta en bruto.

POR QUE HACE FALTA: diag_forma_clientes_303.py midio que el 96,6% de los
cubos (carpeta+codigo) tienen un SOLO contenedor .DAT -- cada copia de
seguridad crea su propio codigo, casi sin excepcion. Con ~33 empresas reales
repartidas en 500+ cubos, comparar el 303 a mano contra ese detalle no es
viable: una empresa real puede estar partida en 15-40 entradas.

QUE HACE, Y QUE NO HACE TODAVIA (FASE 1 de 2)
----------------------------------------------
Esta fase SOLO agrupa y mide la calidad del agrupamiento. NO toca
reconstruir_303.py ni genera ningun 303_LOCAL.json corregido. La razon es la
misma que en todo el proyecto: un agrupamiento automatico que fusione dos
empresas reales distintas corromperia el 303 en silencio, y eso es peor que
no agrupar nada. Se mide la calidad ANTES de confiarse.

REGLA DE DATOS: cada NIF se hashea nada mas leerlo -- nunca vive como texto
plano en ninguna variable de este script, ni siquiera de forma transitoria.
Solo se cuentan e imprimen numeros: tamanos de grupo, distribucion de
similitud, anios cubiertos. Ningun nombre de carpeta ni NIF real se imprime
en ningun momento.

Uso:
    python enlazador_clientes_303.py "RUTA_DEL_CORPUS"
"""
import hashlib
import os
import sys
import zipfile
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retro_semaforo import parse_cabecera, num, txt, cuenta
from reconstruir_303 import clave_cliente, trimestre_de

MIN_NIFS = 3  # cubos con menos contrapartes que esto no tienen senal fiable


def _h(valor):
    return hashlib.blake2b(valor.encode("utf-8"), digest_size=10).digest()


def main():
    raiz = os.path.abspath(sys.argv[1])
    dats = sorted(os.path.join(dp, n)
                  for dp, _, fns in os.walk(raiz) for n in fns
                  if os.path.splitext(n)[1].lower() == ".dat")
    print(f"{len(dats)} contenedores.")

    nifs_por_cubo = defaultdict(set)     # cubo_hash -> {nif_hash, ...}
    carpeta_por_cubo = {}                # cubo_hash -> carpeta_hash (para el veto)
    anios_por_cubo = defaultdict(set)
    errores = Counter()

    for ruta in dats:
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
                    cNIF, cFEC = idx.get("TERNIF"), idx.get("FECHA")
                    if not cNIF:
                        continue

                    cubo_h = _h(clave_cliente(ruta))
                    carpeta_por_cubo[cubo_h] = _h(os.path.basename(os.path.dirname(ruta)))

                    while True:
                        rec = fh.read(len_reg)
                        if len(rec) < len_reg or rec[:1] == b"\x1a":
                            break
                        if rec[:1] == b"*":
                            continue
                        nif = txt(rec, cNIF)
                        if nif:
                            nifs_por_cubo[cubo_h].add(_h(nif))
                        if cFEC:
                            tri = trimestre_de(txt(rec, cFEC))
                            if tri:
                                anios_por_cubo[cubo_h].add(tri[0])
                        del rec
        except Exception as e:
            errores[type(e).__name__] += 1

    cubos = [c for c in nifs_por_cubo if len(nifs_por_cubo[c]) >= MIN_NIFS]
    descartados = len(nifs_por_cubo) - len(cubos)
    print("")
    print(f"  cubos con senal suficiente (>= {MIN_NIFS} contrapartes): {len(cubos):,}")
    print(f"  cubos descartados por poca senal: {descartados:,}")

    # --- Histograma de similitud de Jaccard entre TODOS los pares -----------
    # No decide el umbral de antemano: lo mide, igual que hizo el trabajo de
    # huella original el 12-08-2026 ("histograma bimodal, meseta estable").
    print("")
    print("Calculando similitud entre pares (puede tardar un minuto)...")
    hist = Counter()
    pares_altos = []  # (sim, cubo_a, cubo_b) para sim >= 0.30, para clustering
    n = len(cubos)
    for i in range(n):
        a = cubos[i]
        set_a = nifs_por_cubo[a]
        for j in range(i + 1, n):
            b = cubos[j]
            set_b = nifs_por_cubo[b]
            inter = len(set_a & set_b)
            if inter == 0:
                continue
            union = len(set_a | set_b)
            sim = inter / union
            bucket = round(sim, 1)
            hist[bucket] += 1
            if sim >= 0.30:
                pares_altos.append((sim, a, b))

    print("")
    print("DISTRIBUCION DE SIMILITUD (solo pares con algo de solape):")
    for bucket in sorted(hist):
        print(f"    {bucket:>4.1f}  {'#' * min(60, hist[bucket]):<60} {hist[bucket]:,}")

    # --- Clustering por union-find, con el veto de "misma carpeta" ----------
    padre = {c: c for c in cubos}

    def encontrar(x):
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x

    def unir(x, y):
        rx, ry = encontrar(x), encontrar(y)
        if rx != ry:
            padre[rx] = ry

    UMBRAL = 0.5  # punto medio de la meseta ya validada en el proyecto (0,30-0,60)
    vetados = 0
    for sim, a, b in sorted(pares_altos, reverse=True):
        if sim < UMBRAL:
            break
        if carpeta_por_cubo.get(a) == carpeta_por_cubo.get(b):
            # Regla dura ya establecida: dentro de la misma carpeta, dos
            # codigos distintos son dos empresas distintas. Nunca se fusionan,
            # por alta que salga la similitud.
            vetados += 1
            continue
        unir(a, b)

    grupos = defaultdict(list)
    for c in cubos:
        grupos[encontrar(c)].append(c)

    tamanos = Counter(len(miembros) for miembros in grupos.values())
    print("")
    print("=" * 66)
    print(f"  GRUPOS FORMADOS (umbral Jaccard >= {UMBRAL}): {len(grupos):,}")
    print(f"  (el numero real de empresas conocido es 33 -- comparar con esto)")
    print("=" * 66)
    print(f"  fusiones vetadas por regla de 'misma carpeta, codigo distinto': {vetados:,}")
    print("")
    print("TAMANO DE GRUPO (cuantos cubos por grupo, y cuantos grupos de ese tamano):")
    for tam in sorted(tamanos):
        print(f"    {tam:>3} cubo(s)  ->  {tamanos[tam]:>4,} grupos")

    # --- Sanity check: solapamiento de anios DENTRO de un grupo -------------
    # Tras la deduplicacion de reconstruir_303.py, dos cubos de la MISMA
    # empresa real no deberian compartir el mismo anio con contenido vivo
    # (uno cubriria el historico hasta esa fecha, el otro solo lo nuevo desde
    # entonces). Si un grupo tiene anios repetidos entre sus miembros, es una
    # senal de que puede estar fusionando dos empresas distintas.
    grupos_con_solape = 0
    for lider, miembros in grupos.items():
        if len(miembros) < 2:
            continue
        vistos = set()
        solapa = False
        for m in miembros:
            for anio in anios_por_cubo.get(m, ()):
                if anio in vistos:
                    solapa = True
                vistos.add(anio)
        if solapa:
            grupos_con_solape += 1

    grupos_multi = sum(1 for m in grupos.values() if len(m) >= 2)
    print("")
    print(f"  grupos con 2+ cubos: {grupos_multi:,}")
    print(f"  de esos, con anios solapados entre miembros (senal de alarma): "
          f"{grupos_con_solape:,}")

    if errores:
        print(f"\nErrores: {dict(errores)}")

    print("")
    print("Esto es SOLO la medicion (fase 1). No se ha tocado ningun fichero")
    print("de reconstruir_303.py. Si los grupos con solape son pocos y el")
    print("numero de grupos se acerca a 33, vale la pena la fase 2. Si no,")
    print("hay que revisar el umbral o el metodo antes de fiarse.")


if __name__ == "__main__":
    main()
