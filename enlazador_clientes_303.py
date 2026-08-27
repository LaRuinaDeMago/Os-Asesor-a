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

BUG REAL cazado el 27-08-2026, no preventivo: el script NO filtraba
proveedores DEMASIADO COMUNES (banco, electrica, telefonica, Hacienda como
contraparte...) antes de calcular la similitud. Probado sobre el corpus real:
5 carpetas fabricadas a proposito como empresas DISTINTAS, cada una con
proveedores propios pero compartiendo 4 "genericos", se fusionaron en UN
SOLO grupo -- la similitud por los genericos (0,67) bastaba para saltar el
umbral, sin que importara que cada una tuviera proveedores propios y
distintos. Es la MISMA familia de fallo que `cruzar_303_importes.py` ya
resolvio el 26-08 para los importes ("un importe presente en el 40% de las
carpetas no distingue a nadie"), aqui aplicada a NIF de proveedores. Sin
esto, el resultado real del 27-08 fue "6 grupos" para 27 folders -- muy por
debajo de las 33 empresas conocidas, sobre-fusionando por culpa de
proveedores compartidos que no dicen nada de identidad.

QUE HACE, Y QUE NO HACE TODAVIA (FASE 1 de 2)
----------------------------------------------
Esta fase SOLO agrupa y mide la calidad del agrupamiento. NO toca
reconstruir_303.py ni genera ningun 303_LOCAL.json corregido. La razon es la
misma que en todo el proyecto: un agrupamiento automatico que fusione dos
empresas reales distintas corromperia el 303 en silencio, y eso es peor que
no agrupar nada. Se mide la calidad ANTES de confiarse.

REGLA DE DATOS: cada NIF se hashea nada mas leerlo -- nunca vive como texto
plano en ninguna variable de este script, ni siquiera de forma transitoria.
Por consola SOLO se cuentan e imprimen numeros: tamanos de grupo, distribucion
de similitud, anios cubiertos -- nunca un nombre de carpeta ni un NIF real.

ANADIDO 27-08-2026 (consolidacion de senales): `--detalle` es opcional y NO
cambia lo de arriba -- sigue sin imprimirse nada por consola. Si se pasa,
escribe ademas que CARPETAS (nombre real) quedaron agrupadas como la misma
empresa, a un fichero que DEBE llevar _LOCAL en el nombre (mismo guardia que
`emparejar_carpetas.py` y `cuadre_303_ficha.py`). Solo AHI vive el nombre real,
nunca en stdout. Pensado para que `consolidar_identidad.py` lo cruce con la
similitud de nombre de `emparejar_carpetas.py` sin que el modelo vea ninguno
de los dos.

Uso:
    python enlazador_clientes_303.py "RUTA_DEL_CORPUS"
    python enlazador_clientes_303.py "RUTA_DEL_CORPUS" --max-difusion 0.2
    python enlazador_clientes_303.py "RUTA_DEL_CORPUS" --detalle enlazado_LOCAL.txt
"""
import argparse
import hashlib
import os
import sys
import zipfile
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retro_semaforo import parse_cabecera, num, txt, cuenta
from reconstruir_303 import trimestre_de

MIN_NIFS = 3  # cubos con menos contrapartes que esto no tienen senal fiable


def _h(valor):
    return hashlib.blake2b(valor.encode("utf-8"), digest_size=10).digest()


def carpeta_y_codigo(ruta):
    """(carpeta, carpeta/codigo) -- el mismo patron ya usado en
    retro_semaforo.py:686 para `cliente_id` en --emitir-cartera.

    SEGUNDO BUG REAL cazado el 27-08-2026, mas grave que el de la difusion:
    esta funcion usaba `clave_cliente(ruta)`, importada de reconstruir_303.py.
    Esa funcion se cambio el 25-08-2026 para devolver SOLO la carpeta (el
    arreglo que paso 507 "clientes" a 24). Como este fichero solo IMPORTABA
    la funcion por nombre, el cambio del 25-08 le cambio el significado a
    "cubo" en SILENCIO: paso de ser "carpeta+codigo" (lo que dice su propia
    cabecera, "cubo a cubo en vez de carpeta a carpeta en bruto") a ser
    exactamente "carpeta a carpeta en bruto" -- la MISMA granularidad que se
    supone que venia a refinar. El script llevaba desde el 25-08 sin poder
    hacer lo que dice que hace, y nadie se entero hasta hoy, comparando el
    numero de cubos obtenido (igual al numero de carpetas) contra lo
    esperado."""
    carpeta = os.path.basename(os.path.dirname(ruta))
    codigo = os.path.basename(ruta)[:7]
    return carpeta, f"{carpeta}/{codigo}"


def calcular_grupos(raiz, max_difusion=0.30):
    """Toda la logica de agrupamiento, sin imprimir nada. Devuelve un dict con
    los contadores que main() imprime (identicos a los de siempre) MAS
    `grupos_reales`: {lider_hash: {nombre_de_carpeta_real, ...}} SOLO para
    quien pida --detalle -- main() no lo imprime por consola en ningun caso,
    unicamente lo escribe a un fichero _LOCAL si se lo piden.

    Extraido de main() el 27-08-2026 para poder reutilizar este calculo desde
    `consolidar_identidad.py` sin duplicar la logica (la misma disciplina que
    ya obligo a centralizar el patron de importes en `contrato_datos.py` el
    26-08). El comportamiento por consola no cambia ni un caracter."""
    dats = sorted(os.path.join(dp, n)
                  for dp, _, fns in os.walk(raiz) for n in fns
                  if os.path.splitext(n)[1].lower() == ".dat")

    nifs_por_cubo = defaultdict(set)     # cubo_hash -> {nif_hash, ...}
    carpeta_por_cubo = {}                # cubo_hash -> carpeta_hash (para el veto)
    anios_por_cubo = defaultdict(set)
    # nombre_real_por_cubo vive SOLO en memoria de este proceso. Nunca se
    # imprime por consola -- solo se usa si --detalle pide escribir el
    # fichero _LOCAL. Es el mismo dato que ya pasaba por una variable local
    # (`carpeta`) en el bucle de siempre; antes se descartaba tras hashear,
    # ahora se conserva para ese unico uso opcional.
    nombre_real_por_cubo = {}
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

                    carpeta, cubo_txt = carpeta_y_codigo(ruta)
                    cubo_h = _h(cubo_txt)
                    carpeta_por_cubo[cubo_h] = _h(carpeta)
                    nombre_real_por_cubo[cubo_h] = carpeta

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

    # --- Filtro de DIFUSION, anadido el 27-08-2026 --------------------------
    # Un NIF presente en casi todos los cubos (banco, electrica, telefonica,
    # Hacienda como contraparte...) no distingue nada: infla la similitud
    # entre empresas REALMENTE distintas que comparten proveedores genericos.
    # Probado: 5 empresas fabricadas con proveedores propios + 4 genericos se
    # fusionaban en 1 solo grupo antes de este filtro. Misma tecnica que
    # cruzar_303_importes.py ya aplica a importes desde el 26-08.
    cubos_por_nif = defaultdict(set)
    for c in cubos:
        for nif in nifs_por_cubo[c]:
            cubos_por_nif[nif].add(c)
    tope = max(2, int(len(cubos) * max_difusion))
    difusos = {nif for nif, cs in cubos_por_nif.items() if len(cs) > tope}
    del cubos_por_nif

    nifs_filtrados = {c: (nifs_por_cubo[c] - difusos) for c in cubos}
    # Quitar los NIF difusos puede dejar algun cubo por debajo del minimo:
    # se reevalua el filtro de senal DESPUES de limpiar, no antes.
    cubos = [c for c in cubos if len(nifs_filtrados[c]) >= MIN_NIFS]

    # --- Histograma de similitud de Jaccard entre TODOS los pares -----------
    # No decide el umbral de antemano: lo mide, igual que hizo el trabajo de
    # huella original el 12-08-2026 ("histograma bimodal, meseta estable").
    hist = Counter()
    pares_altos = []  # (sim, cubo_a, cubo_b) para sim >= 0.30, para clustering
    n = len(cubos)
    for i in range(n):
        a = cubos[i]
        set_a = nifs_filtrados[a]
        for j in range(i + 1, n):
            b = cubos[j]
            set_b = nifs_filtrados[b]
            inter = len(set_a & set_b)
            if inter == 0:
                continue
            union = len(set_a | set_b)
            sim = inter / union
            bucket = round(sim, 1)
            hist[bucket] += 1
            if sim >= 0.30:
                pares_altos.append((sim, a, b))

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

    # grupos_reales: SOLO para --detalle. Nombre real de cada carpeta
    # distinta que aporto al menos un cubo a ese grupo -- lo que le interesa
    # a Diego no es cuantos cubos hay, es cuantas CARPETAS DISTINTAS resultan
    # ser, segun esta senal, la misma empresa.
    grupos_reales = defaultdict(set)
    for lider, miembros in grupos.items():
        for m in miembros:
            nombre = nombre_real_por_cubo.get(m)
            if nombre:
                grupos_reales[lider].add(nombre)

    return {
        "n_dats": len(dats),
        "cubos_con_senal_inicial": len(nifs_por_cubo),
        "descartados_por_poca_senal": descartados,
        "difusos": len(difusos),
        "cubos_tras_filtro": len(cubos),
        "hist": hist,
        "grupos": grupos,
        "tamanos": tamanos,
        "vetados": vetados,
        "grupos_multi": grupos_multi,
        "grupos_con_solape": grupos_con_solape,
        "errores": errores,
        "grupos_reales": grupos_reales,
    }


def escribir_detalle_grupos(grupos_reales, ruta_salida):
    """Escribe SOLO los grupos que agrupan 2+ carpetas REALES distintas --
    un grupo de una sola carpeta no dice nada nuevo (ya se sabe que una
    carpeta es ella misma). Ese es exactamente el caso que le interesa a
    Diego: "estas N carpetas de ContaPlus son, segun el NIF de sus
    proveedores, la misma empresa fragmentada en varias copias"."""
    multi = {lider: sorted(nombres) for lider, nombres in grupos_reales.items()
             if len(nombres) >= 2}
    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write("CARPETAS DE CONTAPLUS AGRUPADAS COMO LA MISMA EMPRESA (por NIF "
                "de proveedores)\n")
        f.write("=" * 78 + "\n\n")
        f.write("Cada grupo de abajo son 2+ carpetas que, segun sus proveedores en\n")
        f.write("comun, probablemente son la MISMA empresa repartida en varias\n")
        f.write("copias de seguridad. Es una senal de apoyo, no una fusion\n")
        f.write("automatica -- decide tu si tiene sentido con lo que sabes.\n\n")
        if not multi:
            f.write("(Ningun grupo con 2+ carpetas distintas en esta ejecucion.)\n")
        for i, (_lider, nombres) in enumerate(sorted(multi.items(), key=lambda kv: kv[0]), start=1):
            f.write(f"Grupo {i}: {len(nombres)} carpetas\n")
            for nombre in nombres:
                f.write(f"    - {nombre!r}\n")
            f.write("\n")
    return len(multi)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("carpeta", help="Raiz del corpus con los contenedores .DAT")
    ap.add_argument("--max-difusion", type=float, default=0.30,
                    help="Ignorar NIF presentes en mas de esta fraccion de "
                         "cubos (no distinguen identidad). Por defecto 0,30, "
                         "igual que cruzar_303_importes.py")
    ap.add_argument("--detalle",
                    help="Fichero _LOCAL con los nombres reales de las carpetas "
                         "agrupadas (2+ carpetas por grupo). Opcional -- sin "
                         "esto el script se comporta exactamente igual que "
                         "siempre, solo numeros por consola.")
    args = ap.parse_args()

    if args.detalle and "_LOCAL" not in os.path.basename(args.detalle):
        print("ERROR: --detalle debe contener _LOCAL en el nombre: lleva "
              "nombres de carpeta reales.", file=sys.stderr)
        sys.exit(1)

    raiz = os.path.abspath(args.carpeta)
    r = calcular_grupos(raiz, args.max_difusion)

    print(f"{r['n_dats']} contenedores.")
    print("")
    print(f"  cubos con senal suficiente (>= {MIN_NIFS} contrapartes): "
          f"{r['cubos_con_senal_inicial'] - r['descartados_por_poca_senal']:,}")
    print(f"  cubos descartados por poca senal: {r['descartados_por_poca_senal']:,}")
    print(f"  NIF descartados por demasiado comunes (en mas del "
          f"{args.max_difusion:.0%} de los cubos): {r['difusos']:,}")
    print(f"  cubos con senal DESPUES de filtrar difusos: {r['cubos_tras_filtro']:,}")

    print("")
    print("DISTRIBUCION DE SIMILITUD (solo pares con algo de solape):")
    for bucket in sorted(r["hist"]):
        print(f"    {bucket:>4.1f}  {'#' * min(60, r['hist'][bucket]):<60} {r['hist'][bucket]:,}")

    print("")
    print("=" * 66)
    print(f"  GRUPOS FORMADOS (umbral Jaccard >= 0.5): {len(r['grupos']):,}")
    print(f"  (el numero real de empresas conocido es 33 -- comparar con esto)")
    print("=" * 66)
    print(f"  fusiones vetadas por regla de 'misma carpeta, codigo distinto': {r['vetados']:,}")
    print("")
    print("TAMANO DE GRUPO (cuantos cubos por grupo, y cuantos grupos de ese tamano):")
    for tam in sorted(r["tamanos"]):
        print(f"    {tam:>3} cubo(s)  ->  {r['tamanos'][tam]:>4,} grupos")

    print("")
    print(f"  grupos con 2+ cubos: {r['grupos_multi']:,}")
    print(f"  de esos, con anios solapados entre miembros (senal de alarma): "
          f"{r['grupos_con_solape']:,}")

    if r["errores"]:
        print(f"\nErrores: {dict(r['errores'])}")

    if args.detalle:
        ruta_detalle = os.path.abspath(args.detalle)
        n_multi = escribir_detalle_grupos(r["grupos_reales"], ruta_detalle)
        print("")
        print(f"Detalle con nombres reales (LOCAL, no lo pegues en el chat): {ruta_detalle}")
        print(f"({n_multi} grupos con 2+ carpetas distintas)")

    print("")
    print("Esto es SOLO la medicion (fase 1). No se ha tocado ningun fichero")
    print("de reconstruir_303.py. Si los grupos con solape son pocos y el")
    print("numero de grupos se acerca a 33, vale la pena la fase 2. Si no,")
    print("hay que revisar el umbral o el metodo antes de fiarse.")


if __name__ == "__main__":
    main()
