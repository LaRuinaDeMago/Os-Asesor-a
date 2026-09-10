#!/usr/bin/env python3
"""diag_carpetas_multiempresa.py — ¿alguna de las 24 carpetas mezcla varias
empresas reales?

DE DONDE SALE ESTA PREGUNTA
-----------------------------
Medido el 27-08-2026: con la base ya arreglada (coherencia interna 99,1%),
el cruce contra los 1.043 modelos 303 presentados en el archivo sigue dando
un resultado plano (2,7% exacto, no mejora al aflojar la tolerancia) --
exactamente la firma de un problema de IDENTIDAD, no de precision. Y hay
52 carpetas de cliente en el archivo de documentos frente a solo 24 cubos en
la contabilidad, mas 43 celdas con bases de 10^7-10^8 (imposibles para esta
cartera). Los tres datos apuntan a lo mismo: alguna carpeta del corpus de
ContaPlus mezcla varias empresas reales -- el caso ya confirmado a mano de
"Contabilidad ordenador de Jose".

QUE MIDE, Y COMO SE DISTINGUE DE enlazador_clientes_303.py
-------------------------------------------------------------
`enlazador_clientes_303.py` mide si hay que FUSIONAR cubos (carpeta+codigo)
de carpetas DISTINTAS -- resuelve la fragmentacion (una empresa con muchos
codigos). Esta pregunta es la contraria: dentro de UNA MISMA carpeta, sus
codigos internos, ¿forman UN grupo bien conectado (misma empresa, copias
distintas -- lo esperable) o se separan en DOS O MAS grupos que casi no
comparten proveedores (dos empresas reales compartiendo carpeta)?

Se usa la misma tecnica ya validada el 12-08-2026 (huella de NIF de
contrapartes, similitud de Jaccard, mirar si la distribucion es bimodal) pero
aplicada DENTRO de cada carpeta, no entre carpetas.

REGLA DE DATOS: cada NIF se hashea nada mas leerlo, nunca vive en texto
plano. Por consola las carpetas se identifican por NUMERO DE ORDEN (Carpeta
#1, #2...), nunca por su nombre real -- ni siquiera en la salida estandar,
por si el nombre fuera identificable. Solo se imprimen recuentos y el
histograma de similitud.

ANADIDO 27-08-2026 (consolidacion de senales): `--detalle` es opcional y NO
cambia lo de arriba -- la consola sigue sin nombres. Si se pasa, escribe
ademas que CARPETAS (nombre real) salieron sospechosas de mezclar empresas,
a un fichero que DEBE llevar _LOCAL en el nombre (mismo guardia que
`emparejar_carpetas.py`, `cuadre_303_ficha.py` y ahora tambien
`enlazador_clientes_303.py`). Solo AHI vive el nombre real. Pensado para que
`consolidar_identidad.py` lo cruce con las otras dos senales sin que el
modelo vea ningun nombre.

Uso:
    python diag_carpetas_multiempresa.py "RUTA_DEL_CORPUS"
    python diag_carpetas_multiempresa.py "RUTA_DEL_CORPUS" --detalle multiempresa_LOCAL.txt
"""
import argparse
import hashlib
import os
import sys
import zipfile
from collections import Counter, defaultdict

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retro_semaforo import parse_cabecera, num, txt, cuenta

UMBRAL = 0.30          # el borde inferior de la meseta ya validada el 12-08 (0,30-0,60)


def _h(valor):
    return hashlib.blake2b(valor.encode("utf-8"), digest_size=10).digest()


def carpeta_de(ruta, raiz):
    rel = os.path.relpath(ruta, raiz)
    partes = rel.split(os.sep)
    return partes[0] if len(partes) > 1 else "(raiz)"


def codigo_de(ruta):
    return os.path.basename(ruta)[:7]


def calcular_sospechosas(raiz, min_nifs=3, max_difusion=0.30, progreso=False):
    """Toda la logica de deteccion, sin imprimir nombres. Devuelve un dict
    con los contadores que main() imprime (identicos a los de siempre) MAS
    `n_grupos_por_carpeta_real`: {nombre_real: n_grupos} SOLO para quien pida
    --detalle -- main() no lo imprime por consola en ningun caso.

    Extraido de main() el 27-08-2026, misma razon que en
    `enlazador_clientes_303.py`: reutilizar desde `consolidar_identidad.py`
    sin duplicar la logica ni cambiar el comportamiento por consola."""
    dats = sorted(os.path.join(dp, n) for dp, _, fns in os.walk(raiz)
                  for n in fns if n.lower().endswith(".dat"))
    if not dats:
        return None

    nifs_por_cubo = defaultdict(set)   # (carpeta_idx, codigo) -> {nif_hash, ...}
    errores = Counter()
    carpetas_vistas = {}   # nombre_real -> indice (nunca se imprime el nombre)

    paso = max(1, len(dats) // 20)
    for i, ruta in enumerate(dats, start=1):
        try:
            if not zipfile.is_zipfile(ruta):
                continue
            carpeta_real = carpeta_de(ruta, raiz)
            if carpeta_real not in carpetas_vistas:
                carpetas_vistas[carpeta_real] = len(carpetas_vistas) + 1
            idx = carpetas_vistas[carpeta_real]
            cod = codigo_de(ruta)

            with zipfile.ZipFile(ruta) as z:
                nombre = next((it.filename for it in z.infolist()
                               if not it.is_dir()
                               and os.path.basename(it.filename).lower()
                               == "diario.dbf"), None)
                if nombre is None:
                    continue
                with z.open(nombre) as fh:
                    len_reg, campos = parse_cabecera(fh)
                    campos_idx = {c["nombre"]: c for c in campos}
                    cNIF = campos_idx.get("TERNIF")
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
                            nifs_por_cubo[(idx, cod)].add(_h(nif))
                        del rec
        except Exception as e:
            errores["contenedor:" + type(e).__name__] += 1
        if progreso and (i % paso == 0 or i == len(dats)):
            print(f"    {i * 100 // len(dats):>3}%  ({i:,}/{len(dats):,})")

    # DIAGNOSTICO PREVIO, antes de agrupar nada: cuantos proveedores distintos
    # trae cada codigo. Si la mayoria son "delgados" (pocos NIFs), la
    # similitud de Jaccard entre ellos sera baja aunque sean la MISMA
    # empresa -- simplemente no hay suficiente solapamiento posible con
    # conjuntos pequenos. Esto decide si el resultado de mas abajo es de
    # fiar o es un artefacto del tamano de la muestra.
    tamanos = Counter()
    for nifs in nifs_por_cubo.values():
        n = len(nifs)
        if n == 0:
            tamanos["0"] += 1
        elif n < 3:
            tamanos["1-2"] += 1
        elif n < min_nifs:
            tamanos[f"3-{min_nifs - 1}"] += 1
        elif n < 10:
            tamanos[f"{min_nifs}-9"] += 1
        elif n < 30:
            tamanos["10-29"] += 1
        else:
            tamanos["30+"] += 1

    # FILTRO DE DIFUSION, anadido el 27-08-2026 tras probar el script contra
    # el corpus real y obtener un resultado imposible (27 de 28 carpetas
    # "sospechosas", que implicaria cientos de empresas ocultas). Reproducido
    # a proposito: UNA sola empresa sintetica, con sus 40 codigos viendo cada
    # uno una muestra aleatoria de un pool de proveedores, salio como "29
    # grupos" -- proveedores compartidos (o simplemente coincidencias de
    # muestreo entre codigos "delgados") bastan para desconectar codigos de
    # la MISMA empresa. Misma tecnica que cruzar_303_importes.py aplica a
    # importes desde el 26-08 y que enlazador_clientes_303.py gano hoy mismo:
    # un NIF presente en casi todos los codigos del CORPUS ENTERO no
    # distingue nada, se descarta antes de comparar.
    todos_los_cubos = [c for c, nifs in nifs_por_cubo.items() if len(nifs) >= min_nifs]
    cubos_por_nif = defaultdict(set)
    for c in todos_los_cubos:
        for nif in nifs_por_cubo[c]:
            cubos_por_nif[nif].add(c)
    tope = max(2, int(len(todos_los_cubos) * max_difusion))
    difusos = {nif for nif, cs in cubos_por_nif.items() if len(cs) > tope}
    del cubos_por_nif

    # Agrupar cubos por carpeta, con los NIF difusos ya quitados. Un codigo
    # puede perder senal suficiente tras el filtro: se reevalua el minimo
    # DESPUES de limpiar, no antes.
    cubos_por_carpeta = defaultdict(list)
    for (idx, cod), nifs in nifs_por_cubo.items():
        limpio = nifs - difusos
        if len(limpio) >= min_nifs:
            cubos_por_carpeta[idx].append((cod, limpio))

    resultado = Counter()   # "1 grupo" / "2+ grupos (posible mezcla)" / "solo 1 codigo"
    detalle_grupos = []
    n_grupos_por_idx = {}

    for idx, cubos in sorted(cubos_por_carpeta.items()):
        if len(cubos) < 2:
            resultado["solo 1 codigo con senal"] += 1
            continue

        padre = {c[0]: c[0] for c in cubos}

        def encontrar(x):
            while padre[x] != x:
                padre[x] = padre[padre[x]]
                x = padre[x]
            return x

        def unir(x, y):
            rx, ry = encontrar(x), encontrar(y)
            if rx != ry:
                padre[rx] = ry

        n = len(cubos)
        for i in range(n):
            cod_a, nifs_a = cubos[i]
            for j in range(i + 1, n):
                cod_b, nifs_b = cubos[j]
                inter = len(nifs_a & nifs_b)
                if inter == 0:
                    continue
                sim = inter / len(nifs_a | nifs_b)
                if sim >= UMBRAL:
                    unir(cod_a, cod_b)

        grupos = defaultdict(list)
        for cod, _n in cubos:
            grupos[encontrar(cod)].append(cod)

        n_grupos = len(grupos)
        detalle_grupos.append(n_grupos)
        n_grupos_por_idx[idx] = n_grupos
        if n_grupos == 1:
            resultado["1 grupo (misma empresa, copias distintas)"] += 1
        else:
            resultado[f"{n_grupos}+ grupos (POSIBLE MEZCLA de empresas)"] += 1

    sospechosas = sum(1 for n in detalle_grupos if n >= 2)

    # n_grupos_por_carpeta_real: SOLO para --detalle. Invierte carpetas_vistas
    # (nombre_real -> idx) para poder escribir el nombre real, nunca el
    # indice, en el fichero _LOCAL que Diego revisa.
    idx_a_nombre = {idx: nombre for nombre, idx in carpetas_vistas.items()}
    n_grupos_por_carpeta_real = {idx_a_nombre[idx]: n
                                  for idx, n in n_grupos_por_idx.items()}

    return {
        "n_dats": len(dats),
        "n_carpetas": len(carpetas_vistas),
        "n_carpetas_con_senal": len(cubos_por_carpeta),
        "min_nifs": min_nifs,
        "max_difusion": max_difusion,
        "tamanos": tamanos,
        "difusos": len(difusos),
        "resultado": resultado,
        "detalle_grupos": detalle_grupos,
        "sospechosas": sospechosas,
        "errores": errores,
        "n_grupos_por_carpeta_real": n_grupos_por_carpeta_real,
    }


def escribir_detalle_multiempresa(n_grupos_por_carpeta_real, ruta_salida):
    """Escribe, por nombre real, que carpetas salieron sospechosas de
    mezclar empresas y cuales no -- es una PISTA para revisar, nunca una
    sentencia: el propio diseno del script (ver cabecera) ya avisa que esto
    puede ser ruido de codigos con pocos proveedores."""
    con_datos = sorted(n_grupos_por_carpeta_real.items())
    n_sospechosas = sum(1 for _n, g in con_datos if g >= 2)
    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write("CARPETAS SOSPECHOSAS DE MEZCLAR VARIAS EMPRESAS (por NIF de "
                "proveedores, dentro de la carpeta)\n")
        f.write("=" * 78 + "\n\n")
        f.write("Es una PISTA, no una sentencia: puede ser ruido si los codigos\n")
        f.write("de esa carpeta traen pocos proveedores cada uno. Revisa a mano\n")
        f.write("las marcadas SOSPECHOSA antes de darlas por buenas o por malas.\n\n")
        for nombre, n_grupos in con_datos:
            marca = "SOSPECHOSA" if n_grupos >= 2 else "sana      "
            f.write(f"[{marca}] {n_grupos} grupo(s)  ->  {nombre!r}\n")
        if not con_datos:
            f.write("(Ninguna carpeta con senal suficiente para medir en esta "
                     "ejecucion.)\n")
    return n_sospechosas


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("carpeta")
    ap.add_argument("--min-nifs", type=int, default=3,
                    help="Contrapartes minimas para que un codigo cuente "
                         "(por defecto 3, igual que enlazador_clientes_303.py)")
    ap.add_argument("--max-difusion", type=float, default=0.30,
                    help="Ignorar NIF presentes en mas de esta fraccion de "
                         "codigos del corpus entero (por defecto 0,30)")
    ap.add_argument("--detalle",
                    help="Fichero _LOCAL con los nombres reales de carpetas "
                         "sospechosas. Opcional -- sin esto el script se "
                         "comporta exactamente igual que siempre.")
    args = ap.parse_args()
    min_nifs = args.min_nifs
    max_difusion = args.max_difusion

    if args.detalle and "_LOCAL" not in os.path.basename(args.detalle):
        print("ERROR: --detalle debe contener _LOCAL en el nombre: lleva "
              "nombres de carpeta reales.", file=sys.stderr)
        sys.exit(1)

    raiz = os.path.abspath(args.carpeta)
    if not os.path.isdir(raiz):
        print("ERROR: esa carpeta no existe.", file=sys.stderr)
        sys.exit(2)

    r = calcular_sospechosas(raiz, min_nifs, max_difusion, progreso=True)
    if r is None:
        print("ERROR: no hay ningun .DAT ahi dentro.", file=sys.stderr)
        sys.exit(2)

    print(f"{r['n_dats']:,} contenedores a revisar.")
    print()
    print("=" * 70)
    print(f"TAMAÑO DE CADA CODIGO (numero de proveedores distintos que trae)")
    print("=" * 70)
    print(f"  total de codigos vistos (con al menos 1 NIF): "
          f"{sum(r['tamanos'].values()):,}")
    for etiqueta in ("0", "1-2", f"3-{min_nifs-1}", f"{min_nifs}-9", "10-29", "30+"):
        n = r["tamanos"].get(etiqueta, 0)
        print(f"    {etiqueta:<10} {'#' * min(50, n):<50} {n:,}")
    print("  Si la mayoria cae en '1-2' o en el tramo justo por debajo del")
    print(f"  minimo ({min_nifs}), la fragmentacion de abajo es RUIDO de codigos")
    print("  delgados, no empresas distintas -- sube --min-nifs y repite.")

    print()
    print(f"NIF descartados por demasiado comunes en TODO el corpus "
          f"(en mas del {max_difusion:.0%} de los codigos): {r['difusos']:,}")

    print()
    print("=" * 70)
    print(f"CARPETAS ANALIZADAS: {r['n_carpetas']}  "
          f"(con senal suficiente para medir: {r['n_carpetas_con_senal']})")
    print(f"(usando --min-nifs {min_nifs})")
    print("=" * 70)

    print()
    print("RESULTADO POR CARPETA:")
    for k, v in r["resultado"].most_common():
        print(f"    {k:<52} {v:>4}")

    detalle_grupos = r["detalle_grupos"]
    print()
    print(f"CARPETAS SOSPECHOSAS DE MEZCLAR EMPRESAS: {r['sospechosas']} de "
          f"{len(detalle_grupos)} con mas de un codigo analizable")
    if detalle_grupos:
        print("DISTRIBUCION DE GRUPOS POR CARPETA (1 = sano):")
        for n, c in sorted(Counter(detalle_grupos).items()):
            print(f"    {n} grupo(s): {'#' * min(50, c)} {c}")

    if r["errores"]:
        print()
        print("INCIDENCIAS:", dict(r["errores"]))

    if args.detalle:
        ruta_detalle = os.path.abspath(args.detalle)
        n_sosp = escribir_detalle_multiempresa(r["n_grupos_por_carpeta_real"], ruta_detalle)
        print()
        print(f"Detalle con nombres reales (LOCAL, no lo pegues en el chat): {ruta_detalle}")
        print(f"({n_sosp} carpetas marcadas SOSPECHOSA)")

    print()
    print("COMO SE LEE:")
    print("  - 'sospechosas' es el numero de carpetas que probablemente mezclan")
    print("    dos o mas empresas reales, como el caso ya confirmado a mano.")
    print("  - Si esa cifra es baja (1-3), el arreglo es puntual: identificar esas")
    print("    carpetas concretas (tu las reconoces por el nombre) y separarlas.")
    print("  - Si es alta, el problema es mas extendido de lo que parecia y hace")
    print("    falta repensar como se agrupa 'cliente' en todo el corpus.")


if __name__ == "__main__":
    main()
