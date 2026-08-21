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
# Una sola definicion de 'que guard causo este veredicto', compartida
# con la cola de revision. Dos copias divergen y una acaba mintiendo.
from cola_revision import causas_de

TOL = 0.02
AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA_AGREGADA = os.path.join(AQUI, "retro_semaforo_agregado.json")
SALIDA_LOCAL = os.path.join(AQUI, "retro_semaforo_LOCAL.json")

# Prefijos de cuenta del PGC que definen el patron de compra
PREF_GASTO = "6"
CTA_IVA_SOPORTADO = "472"
CTAS_ACREEDOR = ("400", "401", "410", "411")

#: AMBAR que NO son de la factura, sino del INSTRUMENTO. Anadido 21-08-2026 tras
#: ver que la mitad del corpus salia AMBAR por dos causas que no tienen nada que
#: ver con la calidad de la factura:
#:
#:   sentido_compra_venta   necesita el NIF del cliente titular para decidir si
#:                          el emisor es el propio cliente (venta) o un proveedor
#:                          (gasto). El diario NO lo contiene: el titular no es
#:                          contraparte de si mismo. Aqui es NO_COMPROBADO
#:                          siempre, para todas las filas, por construccion.
#:
#:   nif_casa_historico     la PRIMERA factura de cada proveedor lo encuentra
#:                          fuera del maestro, porque el maestro se acumula sobre
#:                          la marcha (y eso esta bien: es lo que evita medirse
#:                          con la respuesta delante). En produccion ese AMBAR es
#:                          legitimo —un alta que decidir— pero aqui su volumen
#:                          depende del ORDEN de recorrido, no de las facturas.
#:
#: No se ocultan ni se descuentan en silencio: se cuentan aparte y se dicen. Un
#: 51% de AMBAR que en realidad es un 4% es tan enganoso como un falso verde.
AMBAR_DEL_INSTRUMENTO = {"sentido_compra_venta", "nif_casa_historico"}


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
    if not (gastos and acree):
        return None
    if not ivas:
        # Compra sin linea de IVA. PUEDE ser exenta, no sujeta,
        # intracomunitaria o con inversion del sujeto pasivo — pero el diario NO
        # dice cual, y adivinarlo seria inventar la naturaleza. Se marca para
        # contarla en su propio cubo y que no contamine la tasa de falsos rojos.
        return "SIN_IVA"
    

    fila = {}
    # Bases por tipo de IVA: cada linea de IVA trae su tipo en el campo IVA y su
    # base imponible en BASEIMPO. Si BASEIMPO viene vacio, se deriva de la cuota.
    #
    # AMPLIADO 20-08-2026: antes solo se recogian los tipos 4/10/21 y el resto se
    # DESCARTABA en silencio, asi que el instrumento tenia exactamente la misma
    # rigidez que se le acababa de quitar al motor — un 0% o un 5% se perdian y
    # la factura salia deformada. Ahora se recoge cualquier tipo y se entrega al
    # motor como tramos_iva, que ya sabe manejarlos.
    por_tipo = defaultdict(float)
    for l in ivas:
        tipo, cuota, base = l[3], l[1], l[5]
        if base <= 0 and tipo > 0:
            base = round(cuota / (tipo / 100.0), 2)
        por_tipo[int(tipo)] += base
    if por_tipo:
        fila["tramos_iva"] = [
            {"tipo": t, "base": round(b, 2), "cuota": round(b * t / 100.0, 2)}
            for t, b in sorted(por_tipo.items())
        ]
    # Se rellenan tambien los campos planos de los tres tipos clasicos, para que
    # cualquier consumidor antiguo siga funcionando.
    for t in (4, 10, 21):
        if por_tipo.get(t):
            fila[f"base_{t}"] = round(por_tipo[t], 2)

    # Recargo de equivalencia: ContaPlus lo lleva en su propio campo, al lado
    # del de IVA. Sin recogerlo, base+IVA no cuadra con el total y la factura
    # salia ROJO siendo correcta.
    recargo = round(sum(l[8] for l in ivas if len(l) > 8), 2)
    if recargo > 0:
        fila["recargo_equivalencia"] = recargo

    # CORREGIDO 20-08-2026: aqui habia un `if iva_total > 0` que DESCARTABA un
    # IVA de cero legitimo (tipo 0%: pan, leche, fruta) en vez de registrarlo.
    # Es exactamente el error MISSING-vs-ZERO que este proyecto arreglo en el
    # motor, cometido de nuevo en el instrumento que lo mide. Un cero calculado
    # es un DATO; solo se omite el campo cuando no se ha podido calcular.
    base_total = round(sum(por_tipo.values()), 2)
    if base_total <= 0:
        base_total = round(sum(l[1] for l in gastos), 2)
    fila["base_total"] = base_total

    fila["iva_total"] = round(sum(l[1] for l in ivas), 2)
    fila["total_factura"] = round(sum(l[2] for l in acree), 2)

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
    ap.add_argument("--emitir-cartera", metavar="RUTA",
                    help="Ademas de medir, emite el PATRON DE CARTERA (NIF -> cuenta de "
                         "gasto mas usada en toda la cartera) al fichero indicado. "
                         "Aprovecha que esta pasada ya recorre el corpus entero. "
                         "El fichero lleva NIF reales: usar un nombre con _LOCAL.")
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
    ambar_instrumento = Counter()
    ambar_factura = Counter()
    errores = Counter()
    n_asientos = n_compras = n_reconstruidas = n_sin_iva = 0
    vistos_dup = set()
    maestro_acumulado = {}     # crece segun se avanza: ver el comentario del bucle
    # Para el patron de cartera: lineas por cliente, indexadas por contenedor.
    # Solo se acumula si se ha pedido, para no gastar memoria de balde.
    lineas_cartera = defaultdict(list) if args.emitir_cartera else None
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
                    cREC = idx.get("RECEQUIV")
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
                            txt(rec, cFEC), txt(rec, cDOC), num(rec, cREC),
                        ))
                        del rec

                    if lineas_cartera is not None:
                        # La clave de cliente es la CARPETA del contenedor: dentro
                        # de una copia, un codigo de empresa es un cliente. Es la
                        # regla dura verificada en FASE0_RESULTADOS §12.
                        cliente_id = os.path.basename(os.path.dirname(ruta)) + "/" + \
                                     os.path.basename(ruta)[:7]
                        for _a, _ls in grupos.items():
                            for _l in _ls:
                                lineas_cartera[cliente_id].append(
                                    {'ASIEN': _a, 'SUBCTA': _l[0], 'TERNIF': _l[4]})
                    for _, lineas in sorted(grupos.items()):
                        n_asientos += 1
                        fila = reconstruir_compra(lineas)
                        if fila is None:
                            continue
                        if fila == "SIN_IVA":
                            n_sin_iva += 1
                            continue
                        n_compras += 1
                        if fila.get("nif") and len(nifs_pool) < 500:
                            nifs_pool.append(fila["nif"])

                        # CORREGIDO 20-08-2026 — fallo del instrumento, no del motor.
                        # Antes se construia aqui un maestro que contenia EXACTAMENTE
                        # el NIF que se estaba evaluando, asi que
                        # guard_nif_casa_historico pasaba SIEMPRE y el VERDE salia
                        # inflado. Era medirse con la respuesta delante.
                        #
                        # Ahora el maestro se ACUMULA segun se avanza: la primera
                        # factura de un proveedor lo encuentra vacio (proveedor
                        # nuevo, que es lo que pasaria en produccion) y las
                        # siguientes ya lo tienen. Es tambien la regla contra el
                        # data leakage que senalo la auditoria: el historico de una
                        # factura son SOLO los datos anteriores a ella.
                        #
                        # APROXIMACION DECLARADA: el orden es el de recorrido
                        # (contenedores ordenados, asientos por numero), que es
                        # aproximadamente cronologico pero no exactamente.
                        maestro = dict(maestro_acumulado)
                        if fila.get("nif"):
                            maestro_acumulado[fila["nif"]] = {
                                "titulo": fila.get("proveedor", ""), "cuenta": "400000"}
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
                            if estado not in ("OK", "NO_APLICA", "ALTA"):
                                guards_no_ok[f"{g}={estado}"] += 1
                        if v == "AMBAR":
                            # Las causas se sacan del MOTIVO, no de la lista de
                            # guards no benignos. Parece lo mismo y no lo es: hay
                            # guards que estan en NO_COMPROBADO de forma
                            # estructural y el veredicto los declara EXENTOS, asi
                            # que no han causado nada. La primera version de este
                            # recuento los contaba, y atribuia el AMBAR a
                            # importe_atipico y tipo_producto_iva_semantico —los
                            # dos exentos— en vez de a lo que de verdad lo causo.
                            # El motivo es lo que el propio veredicto declara.
                            causas = causas_de(motivo)
                            propias = [c for c in causas
                                       if c not in AMBAR_DEL_INSTRUMENTO]
                            if causas and not propias:
                                ambar_instrumento["+".join(sorted(causas))] += 1
                            else:
                                ambar_factura["; ".join(sorted(propias))[:70]] += 1
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
    print(f"  compras SIN linea de IVA : {n_sin_iva:,}  (exentas / no sujetas /")
    print(f"                             intracomunitarias / ISP: el diario no dice cual,")
    print(f"                             asi que NO se evaluan y NO cuentan como falsos rojos)")
    print()
    print("VEREDICTOS (estos asientos SE CONTABILIZARON Y SE PRESENTARON):")
    for v, n in veredictos.most_common():
        print(f"    {v:<8} {n:>8,}   {pct(n, n_reconstruidas):>6}%")
    n_ambar = veredictos.get("AMBAR", 0)
    n_inst = sum(ambar_instrumento.values())
    n_fact = sum(ambar_factura.values())
    if n_ambar:
        print()
        print("DE QUE SON LOS AMBAR — no todos hablan de la factura:")
        print(f"    del INSTRUMENTO  {n_inst:>8,}   {pct(n_inst, n_reconstruidas):>6}%"
              f"   (no dependen de la factura)")
        for k, n in ambar_instrumento.most_common(4):
            print(f"        {k:<44} {n:>8,}")
        print(f"    de la FACTURA    {n_fact:>8,}   {pct(n_fact, n_reconstruidas):>6}%"
              f"   <-- ESTE es el numero util")
        for k, n in ambar_factura.most_common(6):
            print(f"        {k[:44]:<44} {n:>8,}")
        print()
        print("    Los del instrumento son sentido_compra_venta (el diario no trae")
        print("    el NIF del titular, asi que NUNCA se puede decidir) y el proveedor")
        print("    visto por primera vez (el maestro se acumula sobre la marcha, que")
        print("    es lo que evita medirse con la respuesta delante). Se cuentan")
        print("    aparte, no se descuentan en silencio: un 51% de AMBAR que en")
        print("    realidad es un 4% engana igual que un falso verde.")

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
        "compras_sin_linea_iva_no_evaluadas": n_sin_iva,
        "evaluados": n_reconstruidas,
        "veredictos": dict(veredictos),
        "pct_veredictos": {v: pct(n, n_reconstruidas) for v, n in veredictos.items()},
        "pct_falsos_rojos_candidatos": pct(rojos, n_reconstruidas),
        "guards_no_ok": dict(guards_no_ok.most_common(25)),
        "ambar_del_instrumento": dict(ambar_instrumento.most_common(10)),
        "ambar_de_la_factura": dict(ambar_factura.most_common(15)),
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

    # --- El patron de cartera -------------------------------------------
    # CORREGIDO 21-08-2026, y lo destapo ensayo_retro_semaforo.py en su primera
    # ejecucion: --emitir-cartera aceptaba la ruta, gastaba memoria acumulando
    # lineas... y NO ESCRIBIA NADA. Nunca. construir_mapeo_cartera no se llamaba
    # desde aqui, asi que el fichero que orquestador.py espera en --cartera-json
    # no habia forma de producirlo. La cadena entera —"el criterio sale de los
    # diez anos"— estaba rota en el ultimo eslabon, con las dos puntas hechas.
    if args.emitir_cartera and lineas_cartera is not None:
        try:
            mapeo_cartera = mv.construir_mapeo_cartera(dict(lineas_cartera))
        except Exception as e:
            errores["cartera:" + type(e).__name__] += 1
            mapeo_cartera = {}
        ruta_cartera = os.path.abspath(args.emitir_cartera)
        with open(ruta_cartera, "w", encoding="utf-8") as f:
            json.dump(mapeo_cartera, f, ensure_ascii=False, indent=2)
        fuertes = sum(1 for d in mapeo_cartera.values() if d.get("n_clientes", 0) >= 2)
        if args.limite:
            print()
            print("    ⚠️  --limite CORTA tambien el patron de cartera. La parada")
            print("        ocurre a mitad del recorrido, asi que este fichero solo")
            print("        ha visto los primeros contenedores: n_clientes sale bajo")
            print("        y la senal fuerte no aparece. Sirve para ensayar el")
            print("        circuito, NO para usarlo. El patron de verdad se emite")
            print("        en una pasada SIN --limite.")
        print()
        print("PATRON DE CARTERA (indexado por NIF, cruza los clientes entre si):")
        print(f"    proveedores distintos          : {len(mapeo_cartera):,}")
        print(f"    vistos en 2+ clientes (fuerte) : {fuertes:,}")
        print(f"    escrito en                     : {ruta_cartera}")
        if "_LOCAL" not in os.path.basename(ruta_cartera):
            print("    ⚠️  ESTE FICHERO LLEVA NIF REALES y su nombre no dice _LOCAL.")
            print("        Renombrarlo antes de nada: .gitignore protege *_LOCAL.*,")
            print("        y con otro nombre puede acabar en un commit.")

    print()
    print(f"Agregado (se puede subir)  : {SALIDA_AGREGADA}")
    print(f"Detalle (NO sube, _LOCAL)  : {SALIDA_LOCAL}")


if __name__ == "__main__":
    main()
