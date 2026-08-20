#!/usr/bin/env python3
"""retro_semaforo.py — pasar el semaforo por la contabilidad YA HECHA.

LA IDEA, Y POR QUE ES BUENA
---------------------------
Correr el motor en paralelo a la contabilidad del dia a dia acumula casos al
ritmo al que entran facturas: tres meses de datos tardan tres meses. Es lo unico
del proyecto que corre a velocidad de calendario.

Pero la contabilidad de los ultimos anos YA ESTA HECHA. Cada asiento de compra
del historico es una factura que en su dia se leyo, se contabilizo y se presento.
No hacen falta las fotos: el asiento contiene los mismos campos que el motor
consume (base, IVA, total, NIF, fecha, numero de documento).

    Se reconstruye la fila desde el asiento -> se pasa por el motor -> se compara

Eso convierte "esperar tres meses" en "ejecutar un script", y con miles de casos
en vez de veinte.

QUE MIDE DE VERDAD, Y QUE NO
----------------------------
Hay que ser honesto con lo que este metodo puede y no puede decir:

  SI mide (y muy bien):
    - FALSOS ROJOS. Estos asientos se contabilizaron y se presentaron. Si el
      motor marca ROJO a un 40% de ellos, es inservible en produccion, y eso se
      sabe hoy. Es la medicion mas util que el proyecto puede hacer ahora mismo.
    - La distribucion real de veredictos sobre datos reales, no inventados.
    - Que guards saltan mas, y por tanto donde esta el ruido.

  MODO --inyectar SI mide:
    - La TASA DE DETECCION: se cogen asientos correctos, se les mete un error
      realista (tipo de IVA cambiado, decimal desplazado, NIF de otro proveedor)
      y se cuenta cuantos caza el motor. Es mejor que las pruebas sinteticas
      porque la base es real: proveedores reales, importes reales, patrones
      reales, con el error encima.

  NO mide:
    - LOS FALSOS VERDES REALES. Que un asiento se contabilizara asi no demuestra
      que fuera correcto: demuestra que se hizo asi. El historico dice lo que se
      hizo, no lo que era correcto (ver DISENO_APRENDIZAJE.md §1). Para eso hace
      falta criterio humano sobre facturas concretas, y no hay atajo.

  Dicho de otra forma: esto mide si el motor MOLESTA (falsos rojos) y si SIRVE
  (deteccion). Que sea de FIAR (falsos verdes) sigue necesitando a una persona.

REGLA DE DATOS (.claude/rules/datos.md — diseno de tres roles)
--------------------------------------------------------------
Este script lee datos reales EN LA MAQUINA DE DIEGO y no los emite nunca:
  - La salida agregada son RECUENTOS y PORCENTAJES. Se puede subir al repo.
  - El detalle por asiento va a un fichero `_LOCAL`, que se queda en el disco y
    que Claude NO ABRE JAMAS.
  - Los errores se agrupan por TIPO de excepcion, nunca por su mensaje: los
    mensajes arrastran datos (`invalid literal for int(): '12345678Z'`).
  - No aborta al primer fallo. Un contenedor roto no para la medicion.

LO EJECUTA DIEGO, NO CLAUDE.

Uso:
    python retro_semaforo.py "RUTA_DEL_CORPUS"
    python retro_semaforo.py "RUTA_DEL_CORPUS" --inyectar
    python retro_semaforo.py "RUTA_DEL_CORPUS" --limite 5000
"""
import argparse
import hashlib
import json
import os
import random
import struct
import zipfile
from collections import Counter, defaultdict

import motor_veredicto as mv

TOL = 0.02
AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA_AGREGADA = os.path.join(AQUI, "retro_semaforo_agregado.json")
SALIDA_LOCAL = os.path.join(AQUI, "retro_semaforo_LOCAL.json")

# Prefijos de cuenta del PGC que definen el patron de compra
PREF_GASTO = "6"
CTA_IVA_SOPORTADO = "472"
CTAS_ACREEDOR = ("400", "401", "410", "411")


# --------------------------------------------------------------------------
# Lectura de dBase (misma tecnica que los fase0_*.py: solo cabecera + registros)
# --------------------------------------------------------------------------
def parse_cabecera(stream):
    cab = stream.read(32)
    if len(cab) < 32:
        raise ValueError("cabecera corta")
    len_cab = struct.unpack("<H", cab[8:10])[0]
    len_reg = struct.unpack("<H", cab[10:12])[0]
    campos, pos = [], 1
    leidos = 32
    while leidos < len_cab - 1:
        d = stream.read(32)
        if len(d) < 32 or d[:1] == b"\r":
            break
        leidos += 32
        nombre = d[:11].split(b"\x00")[0].decode("cp1252", "replace").strip()
        tam = d[16]
        campos.append({"nombre": nombre, "pos": pos, "tam": tam,
                       "tipo": chr(d[11])})
        pos += tam
    stream.read(max(0, len_cab - leidos))
    return len_reg, campos


def _crudo(rec, c):
    if not c:
        return b""
    return rec[c["pos"]:c["pos"] + c["tam"]]


def num(rec, c):
    s = _crudo(rec, c).strip()
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def txt(rec, c):
    return _crudo(rec, c).decode("cp1252", "replace").strip()


def cuenta(rec, c):
    return txt(rec, c)[:3]


# --------------------------------------------------------------------------
# Reconstruccion: asiento contable -> fila que el motor entiende
# --------------------------------------------------------------------------
def reconstruir_compra(lineas):
    """Devuelve la fila para el motor, o None si el asiento no es una compra
    reconstruible. `lineas` = [(subcta, debe, haber, iva, nif, base, fecha, doc)].

    NO inventa nada: si un campo no esta en el asiento, no se rellena, y el
    contrato de datos lo marcara MISSING. Esa es justamente la gracia.
    """
    gastos = [l for l in lineas if l[0].startswith(PREF_GASTO)]
    ivas = [l for l in lineas if l[0] == CTA_IVA_SOPORTADO]
    acree = [l for l in lineas if l[0] in CTAS_ACREEDOR]
    if not (gastos and ivas and acree):
        return None

    fila = {}
    # Bases por tipo de IVA: cada linea de IVA trae su tipo en el campo IVA y su
    # base imponible en BASEIMPO. Si BASEIMPO viene vacio, se deriva de la cuota.
    por_tipo = defaultdict(float)
    for l in ivas:
        tipo, cuota, base = l[3], l[1], l[5]
        if base <= 0 and tipo > 0:
            base = round(cuota / (tipo / 100.0), 2)
        if tipo in (4, 10, 21):
            por_tipo[int(tipo)] += base
    for t in (4, 10, 21):
        if por_tipo.get(t):
            fila[f"base_{t}"] = round(por_tipo[t], 2)

    base_total = round(sum(por_tipo.values()), 2)
    if base_total <= 0:
        base_total = round(sum(l[1] for l in gastos), 2)
    if base_total > 0:
        fila["base_total"] = base_total

    iva_total = round(sum(l[1] for l in ivas), 2)
    if iva_total > 0:
        fila["iva_total"] = iva_total

    total = round(sum(l[2] for l in acree), 2)
    if total > 0:
        fila["total_factura"] = total

    nif = next((l[4] for l in lineas if l[4]), "")
    if nif:
        fila["nif"] = nif
        # El motor usa 'proveedor' como clave de cache. Se usa un indice ANONIMO
        # derivado del NIF, no el nombre: el nombre real no hace falta para medir.
        fila["proveedor"] = "PROV_" + hashlib.blake2b(
            nif.encode("cp1252", "replace"), digest_size=4).hexdigest()

    fecha = next((l[6] for l in lineas if l[6]), "")
    if len(fecha) == 8 and fecha.isdigit():
        fila["fecha_expedicion"] = f"{fecha[:4]}-{fecha[4:6]}-{fecha[6:]}"

    doc = next((l[7] for l in lineas if l[7]), "")
    if doc:
        fila["nº_documento"] = doc

    # Estos asientos NO vienen de una captura por IA: vienen del diario ya
    # contabilizado. Se declara OK porque no hubo lectura ambigua de por medio.
    fila["verificacion"] = "OK"
    return fila


# --------------------------------------------------------------------------
# Inyeccion de errores realistas (modo --inyectar)
# --------------------------------------------------------------------------
ERRORES = ("tipo_iva_cambiado", "decimal_desplazado", "total_alterado",
           "nif_de_otro", "fecha_de_otro_ejercicio")


def inyectar(fila, rng, nifs_pool):
    """Mete UN error realista en una fila correcta. Devuelve (fila, etiqueta).

    No son errores absurdos: son los que de verdad se cometen al contabilizar.
    """
    f = dict(fila)
    tipo = rng.choice(ERRORES)
    try:
        if tipo == "tipo_iva_cambiado" and f.get("base_21"):
            # Se aplica 10% donde tocaba 21%: la cuota deja de cuadrar
            f["iva_total"] = round(float(f["base_21"]) * 0.10, 2)
        elif tipo == "decimal_desplazado" and f.get("total_factura"):
            f["total_factura"] = round(float(f["total_factura"]) * 10, 2)
        elif tipo == "total_alterado" and f.get("total_factura"):
            f["total_factura"] = round(float(f["total_factura"]) + 100.0, 2)
        elif tipo == "nif_de_otro" and nifs_pool:
            otro = rng.choice(nifs_pool)
            if otro == f.get("nif"):
                return None, None
            f["nif"] = otro
        elif tipo == "fecha_de_otro_ejercicio" and f.get("fecha_expedicion"):
            anio = int(f["fecha_expedicion"][:4])
            f["fecha_expedicion"] = f"{anio - 3}{f['fecha_expedicion'][4:]}"
        else:
            return None, None
    except (TypeError, ValueError):
        return None, None
    return f, tipo


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta", help="Raiz del corpus con los contenedores .DAT")
    ap.add_argument("--inyectar", action="store_true",
                    help="Ademas, mide la tasa de deteccion metiendo errores realistas")
    ap.add_argument("--limite", type=int, default=0,
                    help="Parar tras N asientos (0 = todos). Util para una primera pasada")
    ap.add_argument("--semilla", type=int, default=20260820,
                    help="Semilla del generador, para que la inyeccion sea reproducible")
    args = ap.parse_args()

    raiz = os.path.abspath(args.carpeta)
    rng = random.Random(args.semilla)

    dats = []
    for dp, _, fns in os.walk(raiz):
        for n in fns:
            if os.path.splitext(n)[1].lower() == ".dat":
                dats.append(os.path.join(dp, n))
    dats.sort()

    print(f"{len(dats)} contenedores encontrados.")
    print("Reconstruyendo asientos de compra y pasandolos por el motor...\n")

    veredictos = Counter()
    motivos = Counter()
    guards_no_ok = Counter()
    errores = Counter()
    n_asientos = n_compras = n_reconstruidas = 0
    vistos_dup = set()
    detalle_local = []
    nifs_pool = []
    parar = False

    det_veredictos = Counter()
    det_por_tipo = defaultdict(Counter)

    for ruta in dats:
        if parar:
            break
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
                    cA, cS = idx.get("ASIEN"), idx.get("SUBCTA")
                    cED, cEH = idx.get("EURODEBE"), idx.get("EUROHABER")
                    cIVA, cNIF = idx.get("IVA"), idx.get("TERNIF")
                    cBASE, cFEC = idx.get("BASEIMPO"), idx.get("FECHA")
                    cDOC = idx.get("DOCUMENTO") or idx.get("FACTURA")
                    if not (cA and cS):
                        continue

                    grupos = defaultdict(list)
                    while True:
                        rec = fh.read(len_reg)
                        if len(rec) < len_reg or rec[:1] == b"\x1a":
                            break
                        if rec[:1] == b"*":
                            continue
                        grupos[int(num(rec, cA))].append((
                            cuenta(rec, cS), num(rec, cED), num(rec, cEH),
                            num(rec, cIVA), txt(rec, cNIF), num(rec, cBASE),
                            txt(rec, cFEC), txt(rec, cDOC),
                        ))
                        del rec

                    for _, lineas in grupos.items():
                        n_asientos += 1
                        fila = reconstruir_compra(lineas)
                        if fila is None:
                            continue
                        n_compras += 1
                        if fila.get("nif") and len(nifs_pool) < 500:
                            nifs_pool.append(fila["nif"])

                        maestro = {fila["nif"]: {"titulo": fila.get("proveedor", ""),
                                                 "cuenta": "400000"}} if fila.get("nif") else {}
                        anio = int(fila["fecha_expedicion"][:4]) if fila.get("fecha_expedicion") else None

                        try:
                            v, motivo, guards = mv.evaluar_fila_v4(
                                fila, vistos_dup, {}, {}, {}, maestro,
                                alta_cliente_anio=1990,
                                nif_cliente_titular=None,
                                ejercicio_tanda=anio)
                        except Exception as e:
                            errores["motor:" + type(e).__name__] += 1
                            continue

                        n_reconstruidas += 1
                        veredictos[v] += 1
                        motivos[motivo.split(":")[0][:60]] += 1
                        for g, (estado, _) in guards.items():
                            if estado not in ("OK", "NO_APLICA"):
                                guards_no_ok[f"{g}={estado}"] += 1
                        # El detalle LOCAL guarda el veredicto y el motivo, nunca
                        # el NIF ni los importes: ni siquiera el fichero local
                        # necesita la identidad para que Diego revise casos.
                        detalle_local.append({"veredicto": v, "motivo": motivo[:200],
                                              "ejercicio": anio})

                        if args.inyectar and v == "VERDE":
                            fila_mala, etiqueta = inyectar(fila, rng, nifs_pool)
                            if fila_mala is not None:
                                try:
                                    v2, _, _ = mv.evaluar_fila_v4(
                                        fila_mala, set(), {}, {}, {}, maestro,
                                        alta_cliente_anio=1990,
                                        nif_cliente_titular=None,
                                        ejercicio_tanda=anio)
                                    det_veredictos[v2] += 1
                                    det_por_tipo[etiqueta][v2] += 1
                                except Exception as e:
                                    errores["inyeccion:" + type(e).__name__] += 1

                        if args.limite and n_reconstruidas >= args.limite:
                            parar = True
                            break
                    del grupos
        except Exception as e:
            errores["contenedor:" + type(e).__name__] += 1
            continue

    # ---------------- Informe ----------------
    def pct(n, d):
        return round(n * 100.0 / d, 2) if d else 0.0

    print("=" * 66)
    print("RETRO-SEMAFORO — el motor sobre contabilidad YA CONTABILIZADA")
    print("=" * 66)
    print(f"  asientos leidos          : {n_asientos:,}")
    print(f"  patron de compra         : {n_compras:,} ({pct(n_compras, n_asientos)}%)")
    print(f"  evaluados por el motor   : {n_reconstruidas:,}")
    print()
    print("VEREDICTOS (estos asientos SE CONTABILIZARON Y SE PRESENTARON):")
    for v, n in veredictos.most_common():
        print(f"    {v:<8} {n:>8,}   {pct(n, n_reconstruidas):>6}%")
    rojos = veredictos.get("ROJO", 0)
    print()
    print(f"  >> TASA DE FALSOS ROJOS (candidatos): {pct(rojos, n_reconstruidas)}%")
    print("     Cada ROJO aqui es un asiento que en su dia se dio por bueno.")
    print("     Si esta cifra es alta, el motor molesta mas de lo que ayuda.")
    print()
    print("GUARDS QUE MAS SALTAN (donde esta el ruido):")
    for g, n in guards_no_ok.most_common(12):
        print(f"    {g:<45} {n:>8,}")

    if args.inyectar:
        total_iny = sum(det_veredictos.values())
        cazados = total_iny - det_veredictos.get("VERDE", 0)
        print()
        print("=" * 66)
        print("DETECCION — errores realistas metidos en asientos correctos")
        print("=" * 66)
        print(f"  errores inyectados       : {total_iny:,}")
        print(f"  >> TASA DE DETECCION     : {pct(cazados, total_iny)}%")
        print(f"     se colaron como VERDE : {det_veredictos.get('VERDE', 0):,}")
        print()
        print("  por tipo de error:")
        for tipo, c in det_por_tipo.items():
            t = sum(c.values())
            colados = c.get("VERDE", 0)
            print(f"    {tipo:<28} detectado {pct(t - colados, t):>6}%  "
                  f"({colados:,} colados de {t:,})")

    if errores:
        print()
        print("INCIDENCIAS (por tipo de excepcion, nunca por mensaje):")
        for k, n in errores.most_common():
            print(f"    {k:<40} {n:>6,}")

    agregado = {
        "version": "retro_semaforo v1 (20-08-2026)",
        "asientos_leidos": n_asientos,
        "patron_compra": n_compras,
        "evaluados": n_reconstruidas,
        "veredictos": dict(veredictos),
        "pct_veredictos": {v: pct(n, n_reconstruidas) for v, n in veredictos.items()},
        "pct_falsos_rojos_candidatos": pct(rojos, n_reconstruidas),
        "guards_no_ok": dict(guards_no_ok.most_common(25)),
        "motivos": dict(motivos.most_common(20)),
        "errores_por_tipo": dict(errores),
        "nota": ("Mide falsos ROJOS y ruido sobre datos reales. NO mide falsos "
                 "verdes: que un asiento se contabilizara asi demuestra que se "
                 "hizo asi, no que fuera correcto."),
    }
    if args.inyectar:
        total_iny = sum(det_veredictos.values())
        agregado["deteccion"] = {
            "inyectados": total_iny,
            "pct_detectados": pct(total_iny - det_veredictos.get("VERDE", 0), total_iny),
            "colados_como_verde": det_veredictos.get("VERDE", 0),
            "por_tipo": {t: dict(c) for t, c in det_por_tipo.items()},
        }

    with open(SALIDA_AGREGADA, "w", encoding="utf-8") as f:
        json.dump(agregado, f, ensure_ascii=False, indent=2)
    with open(SALIDA_LOCAL, "w", encoding="utf-8") as f:
        json.dump(detalle_local, f, ensure_ascii=False, indent=2)

    print()
    print(f"Agregado (se puede subir)  : {SALIDA_AGREGADA}")
    print(f"Detalle (NO sube, _LOCAL)  : {SALIDA_LOCAL}")


if __name__ == "__main__":
    main()
