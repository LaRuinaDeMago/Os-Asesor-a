#!/usr/bin/env python3
"""reconstruir_303.py — cuadrar la contabilidad contra la UNICA verdad externa.

POR QUE ESTO ES DISTINTO DE TODO LO DEMAS DEL PROYECTO
------------------------------------------------------
Todo lo que valida este repositorio se valida contra si mismo: la aritmetica de
la factura contra la propia factura, el patron del proveedor contra el historico
del despacho, el veredicto contra lo que se contabilizo en su dia. Es coherencia
interna, y tiene un techo conocido y ya escrito en DISENO_APRENDIZAJE.md §1:

    el historico dice lo que se HIZO, no lo que era CORRECTO.

Hay una excepcion, y solo una. Los modelos 303 presentados en Hacienda son un
HECHO EXTERNO: los presento el despacho, los acepto la Agencia Tributaria, y
llevan diez anos en pie. No arrastran la ambiguedad de "lo que contabilizaste vs
lo que era correcto". Es la mejor verdad de referencia que este proyecto va a
tener nunca, y esta sin usar.

QUE HACE ESTE SCRIPT, Y QUE NO — LEER ANTES DE FIARSE DE UN NUMERO
-------------------------------------------------------------------
NO reconstruye un modelo 303. Decir eso seria falso, y conviene decir por que:
un 303 real lleva prorrata, bienes de inversion, operaciones intracomunitarias,
inversion del sujeto pasivo, compensacion de cuotas de periodos anteriores y
regimenes especiales. Nada de eso se deduce de las cuentas de IVA sin mas.

Lo que SI hace, que es comprobable y suficiente para lo que importa:

    agrega, por cliente y por trimestre, las BASES y CUOTAS de IVA por tipo,
    separando el repercutido (477) del soportado (472),

que es exactamente el contenido de las casillas 01-09 (devengado) y 28-29
(deducible) del modelo. Si esas casillas cuadran con el 303 presentado durante
cuarenta trimestres, lo que queda validado no es una factura: es la CADENA
ENTERA de lectura —el parseo del .DAT, la clasificacion de cuentas, la logica de
tramos— contra algo que Hacienda ya dio por bueno.

Y sigue la misma disciplina que el motor: lo que no se puede clasificar NO se
mete en ninguna casilla. Se cuenta aparte y se declara. Un importe metido en la
casilla equivocada para que cuadre el total es el falso verde de un 303.

COMO SE USA — ES UN TRABAJO DE DOS, Y LA SEGUNDA MITAD ES HUMANA
------------------------------------------------------------------
    1. Diego lo ejecuta en su maquina sobre el corpus de .DAT.
    2. Sale un fichero `_LOCAL` con las cifras por cliente y trimestre. Eso NO
       sube: son las ventas y las compras de clientes concretos.
    3. Diego abre el 303 presentado de ese trimestre y compara las casillas.
    4. Lo unico que sube es el RECUENTO: cuantos trimestres cuadran y cuantos no.

Ese recuento es el numero que este proyecto lleva un mes buscando, y ademas es
el que se le puede ensenar a alguien sin ensenar un solo dato de cliente.

REGLA DE DATOS (.claude/rules/datos.md — diseno de tres roles)
---------------------------------------------------------------
Lo ejecuta Diego, no Claude. El agregado que se emite son RECUENTOS. El detalle
va a `_LOCAL`, que Claude NO ABRE JAMAS. Los errores se agrupan por TIPO de
excepcion, nunca por su mensaje.

Uso:
    python reconstruir_303.py "RUTA_DEL_CORPUS"
    python reconstruir_303.py "RUTA_DEL_CORPUS" --detalle 303_LOCAL.json
"""
import argparse
import hashlib
import json
import os
import sys
import zipfile
from collections import Counter, defaultdict

# Sin esto, una consola de Windows en cp1252 revienta al imprimir el aviso de
# privacidad (⚠️). Mismo patron que scripts/privacy_scan.py. hasattr() porque
# sys.stdout no siempre es un TextIOWrapper real (ver test_motor_veredicto.py:
# StringIO no tiene .reconfigure()).
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from retro_semaforo import (MAX_REGISTROS_POR_FICHERO, cuenta,
                            num, parse_cabecera, txt)

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA_AGREGADA = os.path.join(AQUI, "reconstruccion_303_agregado.json")

#: Cuentas de IVA del PGC y el tipo que representa cada subcuenta habitual.
#: El tipo NO se adivina por el nombre de la cuenta: se lee del campo IVA del
#: propio apunte, que es donde ContaPlus lo guarda. La cuenta solo dice si es
#: repercutido o soportado.
PREF_REPERCUTIDO = "477"
PREF_SOPORTADO = "472"

#: Prefijo de las cuentas de INGRESO (ventas). Ya NO se usa para derivar la
#: base (ver derivar_bases_por_tipo, reescrito el 27-08-2026) -- se conserva
#: porque diag_rescalado_multitipo.py la importa de aqui para su propio
#: diagnostico, que sigue midiendo cuanto diverge el ingreso contable de lo
#: que implica la cuota, aunque esa cifra ya no se use para reconstruir.
PREF_INGRESO = "7"

#: Tipos vigentes en Espana en el periodo que cubre el corpus. Un tipo fuera de
#: esta lista no se descarta: se cuenta aparte, porque puede ser un tipo antiguo
#: (el 16% y el 18% existieron) o un error de contabilizacion, y las dos cosas
#: interesan.
TIPOS_CONOCIDOS = (0, 4, 5, 7, 8, 10, 16, 18, 21)


def trimestre_de(fecha_aaaammdd):
    """'20260315' -> (2026, 1). None si la fecha no es utilizable."""
    if len(fecha_aaaammdd) != 8 or not fecha_aaaammdd.isdigit():
        return None
    anio, mes = int(fecha_aaaammdd[:4]), int(fecha_aaaammdd[4:6])
    if not (1 <= mes <= 12) or not (1990 <= anio <= 2100):
        return None
    return anio, (mes - 1) // 3 + 1


def clave_cliente(ruta):
    """El cliente es la carpeta de NIVEL 1 bajo la raiz del corpus -- la que
    Diego organizo el uno por cliente, con todas sus copias de ContaPlus a
    lo largo de los anios dentro.

    CORREGIDO 25-08-2026 (ver diag_profundidad_carpetas.py y
    diag_verificar_carpeta_cliente.py). La version anterior usaba la carpeta
    INMEDIATA del contenedor mas los 7 primeros caracteres del nombre del
    fichero (el "codigo" que ContaPlus le pone a cada copia de seguridad).
    Eso fragmentaba: measured 977 "clientes" cuando solo hay 33 reales, uno
    por cada codigo distinto que ContaPlus asigna en cada copia -- el mismo
    cliente puede tener 15-40 codigos distintos a lo largo de una decada de
    copias, todos dentro de SU MISMA carpeta.

    Verificado antes de cambiarlo: la carpeta de nivel 1 da 28 carpetas
    distintas (el numero real conocido es 33), y dentro de cada una, el
    codigo mejor conectado con los demas de la misma carpeta contiene el
    90-100% de sus contrapartes en el resto -- coherente con "misma empresa,
    copias distintas", no con dos empresas compartiendo carpeta. Solo el
    codigo PEOR conectado de cada carpeta suele salir a cero, compatible con
    plantillas casi vacias o un asiento de apertura suelto, no con una
    segunda empresa real escondida.

    LO QUE ESTO NO CIERRA DEL TODO: no hay garantia formal de que ninguna de
    las 28 carpetas mezcle dos empresas reales. Si al comparar un trimestre
    contra el 303 presentado el numero no cuadra sin explicacion, esa
    carpeta concreta es la primera sospechosa a revisar."""
    return os.path.basename(os.path.dirname(ruta))


def derivar_bases_por_tipo(ivas):
    """Para cada tipo de IVA presente en un lado de un asiento, calcula la
    base que DEBE aparecer en la casilla del 303.

    REESCRITO EL 27-08-2026, EL MISMO DIA DEL PRIMER ARREGLO -- error de
    diseno propio, no de retro_semaforo.py. La version anterior copiaba la
    logica de `retro_semaforo.reconstruir_compra()`: derivar la base del
    GASTO/INGRESO contable del asiento cuando BASEIMPO no sirve. Esa logica
    es correcta PARA LO QUE HACE retro_semaforo.py -- sus guards comparan una
    factura nueva contra el patron HISTORICO de la cuenta, y les interesa lo
    que de verdad se llevo a gasto. El propio fichero documenta que eso
    diverge de cuota/tipo en el 41,31% de los casos (recargo de equivalencia,
    retenciones u otros conceptos mezclados en la misma cuenta).

    Pero un modelo 303 NO se rige por lo que se contabilizo: se rige por una
    formula fija, base * tipo = cuota -- es la definicion misma de la
    casilla. Medido sobre el corpus real tras el primer arreglo: coherencia
    64,9% global, y EMPEORANDO con el tamano de la celda (72,9% en celdas
    pequenas -> 43,9% en celdas de 200+ apuntes) -- la firma de un sesgo
    sistematico que se acumula, no de ruido. La hipotesis del reescalado
    multi-tipo se descarto con diag_rescalado_multitipo.py: el 88,6% de los
    asientos multi-tipo tiene factor 0,95-1,05, y multi-tipo es solo el
    10,7% del volumen -- no basta para explicarlo.

    La causa real: para RECONSTRUIR una casilla del 303, la fuente correcta
    es invertir la propia formula (base = cuota / tipo), no el gasto
    contable. Esto ademas arregla SOLO el caso ISP sin necesitar detectarlo:
    una linea 477 de autorrepercusion no tiene venta detras, asi que ya no
    hace falta buscarla -- se deriva de su propia cuota, como cualquier otra.

    `ivas` = lista de (tipo, cuota, base_directa) de un mismo lado de UN
    asiento. Ya no hace falta el importe de gasto/ingreso: por eso
    PREF_GASTO/PREF_INGRESO dejan de usarse aqui (se conservan como
    constantes, las sigue usando diag_rescalado_multitipo.py)."""
    por_tipo = defaultdict(float)
    for tipo, cuota, base_directa in ivas:
        tipo_i = int(tipo)
        if base_directa > 0:
            por_tipo[tipo_i] += base_directa
        elif tipo > 0:
            por_tipo[tipo_i] += round(cuota / (tipo / 100.0), 2)
        # tipo == 0 sin BASEIMPO: no hay formula que invertir (cuota es
        # siempre 0 a ese tipo). Se queda sin base, y es lo correcto: no se
        # inventa un numero que no se puede derivar de nada.
    return {t: round(b, 2) for t, b in por_tipo.items()}


def acumular(ruta, acumulado, incidencias, vistos_contenido):
    """Suma las bases y cuotas de IVA de un contenedor. No devuelve nada del
    contenido: escribe en las estructuras que recibe.

    REESCRITO EL 27-08-2026 -- BUG REAL, no preventivo, y de los gordos:
    hasta esta version, la base se leia de BASEIMPO directamente. Medido con
    diag_baseimpo.py el 26-08-2026 sobre el corpus real (44.522 apuntes de
    IVA): BASEIMPO es un CERO LITERAL en el 99,4% de los casos. Este script
    llevaba desde el 21-08-2026 sumando esos ceros y llamando "base
    imponible" al resultado -- `303_LOCAL.json` no describia ninguna
    contabilidad.

    PRIMER ARREGLO (mismo dia): copiar la tecnica de
    `retro_semaforo.reconstruir_compra()` -- derivar la base del gasto/ingreso
    contable del asiento. Mejoro el problema (base ya no era cero) pero no lo
    resolvio: medido despues, coherencia 64,9% y EMPEORANDO con el tamano de
    la celda, la firma de un sesgo sistematico. Investigado con
    `diag_rescalado_multitipo.py` sobre el corpus real: el reescalado
    multi-tipo NO era la causa (88,6% de esos asientos sin sesgo, y solo el
    10,7% del volumen). La causa real: un 303 se rige por `base * tipo =
    cuota`, no por lo que se contabilizo a gasto -- esa es la logica correcta
    para lo que hace `retro_semaforo.py` (comparar contra el patron
    historico), no para reconstruir una casilla fiscal. Ver
    `derivar_bases_por_tipo()` para el arreglo definitivo: invierte la propia
    formula del 303 en vez de mirar la contabilidad.

    Para derivar la base hace falta saber que OTRAS lineas de IVA viven en el
    MISMO asiento (para separar tipos y sumar cuotas correctamente) -- ya no
    basta con mirar una linea suelta. Por eso se lee el contenedor ENTERO
    primero (agrupando por ASIEN, igual que
    `retro_semaforo.reconstruir_compra()`) y se procesa asiento a asiento.

    DEDUPLICACION, cambiada de granularidad A PROPOSITO: antes se
    deduplicaba por LINEA (huella de los 954 bytes de un registro suelto).
    Ahora se deduplica por ASIENTO COMPLETO (huella de las huellas de sus
    lineas, ordenadas -- exactamente la tecnica ya validada en
    `retro_semaforo.py`), porque derivar la base exige mirar el asiento
    entero de todas formas, y una copia de seguridad repite el asiento
    COMPLETO, nunca una linea suelta. Sigue siendo necesaria: cada copia de
    ContaPlus contiene el HISTORICO COMPLETO hasta esa fecha, así que sin
    deduplicar las bases y cuotas saldrian infladas por el numero de copias.

    `vistos_contenido` es del RUN ENTERO, no del contenedor: por eso viaja
    como parametro en vez de crearse aqui dentro."""
    with zipfile.ZipFile(ruta) as z:
        nombre = next((i.filename for i in z.infolist()
                       if not i.is_dir()
                       and os.path.basename(i.filename).lower() == "diario.dbf"), None)
        if nombre is None:
            incidencias["contenedor sin Diario.dbf"] += 1
            return
        with z.open(nombre) as fh:
            len_reg, campos = parse_cabecera(fh)
            idx = {c["nombre"]: c for c in campos}
            cS, cED, cEH = idx.get("SUBCTA"), idx.get("EURODEBE"), idx.get("EUROHABER")
            cIVA, cBASE, cFEC = idx.get("IVA"), idx.get("BASEIMPO"), idx.get("FECHA")
            cA = idx.get("ASIEN")
            if not (cS and cFEC and cA):
                incidencias["Diario.dbf sin SUBCTA, FECHA o ASIEN"] += 1
                return
            cliente = clave_cliente(ruta)
            # Primera pasada: agrupar TODO el contenedor por asiento. Misma
            # red de seguridad que antes: parse_cabecera ya rechaza una
            # longitud de registro imposible, pero un bucle que no termina
            # es el fallo mas caro que hay -- no da error y no acaba.
            lineas_por_asiento = defaultdict(list)
            leidos_aqui = 0
            while True:
                rec = fh.read(len_reg)
                if len(rec) < len_reg or rec[:1] == b"\x1a":
                    break
                leidos_aqui += 1
                if leidos_aqui > MAX_REGISTROS_POR_FICHERO:
                    raise ValueError("demasiados registros: fichero corrupto")
                if rec[:1] == b"*":            # registro borrado en dBase
                    continue
                pref = cuenta(rec, cS)
                huella_linea = hashlib.blake2b(rec, digest_size=8).digest()
                lineas_por_asiento[int(num(rec, cA))].append((
                    pref, num(rec, cED), num(rec, cEH),
                    num(rec, cIVA) if cIVA else 0.0,
                    num(rec, cBASE) if cBASE else 0.0,
                    txt(rec, cFEC), huella_linea))
                del rec

            for _asien, lineas in lineas_por_asiento.items():
                huella_asiento = hashlib.blake2b(
                    b"".join(sorted(l[6] for l in lineas)), digest_size=16).digest()
                if huella_asiento in vistos_contenido:
                    incidencias["duplicado entre copias de seguridad"] += (
                        sum(1 for l in lineas if l[0] in (PREF_REPERCUTIDO, PREF_SOPORTADO)))
                    continue
                vistos_contenido.add(huella_asiento)

                ivas_soportado = [(l[3], l[1] - l[2], l[4]) for l in lineas
                                  if l[0] == PREF_SOPORTADO]
                ivas_repercutido = [(l[3], l[2] - l[1], l[4]) for l in lineas
                                    if l[0] == PREF_REPERCUTIDO]
                if not (ivas_soportado or ivas_repercutido):
                    continue

                # La fecha del asiento: se toma de la primera linea de IVA
                # que la traiga. En un asiento real todas comparten fecha.
                fecha_txt = next((l[5] for l in lineas
                                  if l[0] in (PREF_SOPORTADO, PREF_REPERCUTIDO) and l[5]), "")
                tri = trimestre_de(fecha_txt)
                if tri is None:
                    incidencias["apunte de IVA con fecha inutilizable"] += (
                        len(ivas_soportado) + len(ivas_repercutido))
                    continue

                for ivas, lado in ((ivas_soportado, "deducible"),
                                   (ivas_repercutido, "devengado")):
                    if not ivas:
                        continue
                    por_tipo = derivar_bases_por_tipo(ivas)
                    cuota_por_tipo = defaultdict(float)
                    apuntes_por_tipo = Counter()
                    for tipo, cuota, _base in ivas:
                        cuota_por_tipo[int(tipo)] += cuota
                        apuntes_por_tipo[int(tipo)] += 1
                    for tipo_int in sorted(set(por_tipo) | set(cuota_por_tipo)):
                        if tipo_int not in TIPOS_CONOCIDOS:
                            incidencias["apunte de IVA con tipo fuera de la lista"] += \
                                apuntes_por_tipo[tipo_int]
                            clave_tipo = "tipo_no_catalogado"
                        else:
                            clave_tipo = str(tipo_int)
                        celda = acumulado[cliente][tri][lado][clave_tipo]
                        celda["base"] = round(celda["base"] + por_tipo.get(tipo_int, 0.0), 2)
                        celda["cuota"] = round(celda["cuota"] + cuota_por_tipo[tipo_int], 2)
                        celda["apuntes"] += apuntes_por_tipo[tipo_int]


def nuevo_acumulado():
    return defaultdict(
        lambda: defaultdict(
            lambda: {"devengado": defaultdict(lambda: {"base": 0.0, "cuota": 0.0, "apuntes": 0}),
                     "deducible": defaultdict(lambda: {"base": 0.0, "cuota": 0.0, "apuntes": 0})}))


def a_json(acumulado):
    salida = {}
    for cliente, trimestres in acumulado.items():
        salida[cliente] = {}
        for (anio, tri), lados in sorted(trimestres.items()):
            salida[cliente][f"{anio}T{tri}"] = {
                lado: {t: dict(v) for t, v in sorted(celdas.items())}
                for lado, celdas in lados.items()
            }
    return salida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta", help="Raiz del corpus con los contenedores .DAT")
    ap.add_argument("--detalle", metavar="RUTA",
                    help="Fichero donde escribir las cifras por cliente y trimestre. "
                         "LLEVA IMPORTES DE CLIENTES CONCRETOS: usar un nombre con "
                         "_LOCAL para que .gitignore lo proteja. Sin esta opcion "
                         "solo se emite el recuento agregado.")
    args = ap.parse_args()

    raiz = os.path.abspath(args.carpeta)
    dats = sorted(os.path.join(dp, n)
                  for dp, _, fns in os.walk(raiz) for n in fns
                  if os.path.splitext(n)[1].lower() == ".dat")
    print(f"{len(dats)} contenedores encontrados.")

    acumulado = nuevo_acumulado()
    incidencias = Counter()
    vistos_contenido = set()
    for ruta in dats:
        try:
            if not zipfile.is_zipfile(ruta):
                incidencias["fichero .DAT que no es un contenedor"] += 1
                continue
            acumular(ruta, acumulado, incidencias, vistos_contenido)
        except Exception as e:
            # Por TIPO de excepcion, nunca el mensaje: los mensajes arrastran datos.
            incidencias["contenedor:" + type(e).__name__] += 1

    n_clientes = len(acumulado)
    trimestres = [(c, t) for c, ts in acumulado.items() for t in ts]
    tipos_vistos = Counter()
    apuntes = 0
    for _c, ts in acumulado.items():
        for _t, lados in ts.items():
            for lado, celdas in lados.items():
                for tipo, v in celdas.items():
                    tipos_vistos[f"{lado} {tipo}%"] += v["apuntes"]
                    apuntes += v["apuntes"]

    print()
    print("=" * 68)
    print("BASES Y CUOTAS DE IVA POR TRIMESTRE (casillas 01-09 y 28-29)")
    print("=" * 68)
    print(f"  clientes (carpetas)      : {n_clientes:,}")
    print(f"  trimestres reconstruidos : {len(trimestres):,}")
    print(f"  apuntes de IVA agregados : {apuntes:,}")
    print()
    print("APUNTES POR LADO Y TIPO (donde esta el volumen):")
    for k, n in tipos_vistos.most_common(14):
        print(f"    {k:<28} {n:>9,}")
    if incidencias:
        print()
        print("LO QUE NO SE HA PODIDO CLASIFICAR (no se mete en ninguna casilla):")
        for k, n in incidencias.most_common():
            print(f"    {k:<44} {n:>7,}")
        print("    Un importe metido en la casilla equivocada para que cuadre el")
        print("    total es el falso verde de un 303. Se quedan fuera y se cuentan.")

    agregado = {
        "version": "1.0",
        "clientes": n_clientes,
        "trimestres": len(trimestres),
        "apuntes_iva": apuntes,
        "por_lado_y_tipo": dict(tipos_vistos),
        "incidencias": dict(incidencias),
        "aviso": ("Esto NO es un modelo 303 reconstruido: no incluye prorrata, "
                  "bienes de inversion, intracomunitarias, inversion del sujeto "
                  "pasivo ni compensacion de cuotas. Son las bases y cuotas por "
                  "tipo, que es el contenido de las casillas 01-09 y 28-29."),
    }
    with open(SALIDA_AGREGADA, "w", encoding="utf-8") as f:
        json.dump(agregado, f, ensure_ascii=False, indent=2)
    print()
    print(f"Agregado (se puede subir)  : {SALIDA_AGREGADA}")

    if args.detalle:
        ruta = os.path.abspath(args.detalle)
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(a_json(acumulado), f, ensure_ascii=False, indent=2)
        print(f"Detalle por trimestre      : {ruta}")
        if "_LOCAL" not in os.path.basename(ruta):
            print("    ⚠️  ESTE FICHERO LLEVA LAS VENTAS Y COMPRAS DE CLIENTES")
            print("        CONCRETOS y su nombre no dice _LOCAL. Renombrarlo antes")
            print("        de nada: .gitignore protege *_LOCAL.*, y con otro nombre")
            print("        puede acabar en un commit.")
        print()
        print("  SIGUIENTE PASO, Y ES HUMANO: abrir el 303 presentado de un")
        print("  trimestre y comparar sus casillas con las de ese fichero. Lo unico")
        print("  que sube despues es el recuento de cuantos cuadran.")


if __name__ == "__main__":
    main()
