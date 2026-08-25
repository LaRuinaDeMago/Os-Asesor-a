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
import sys
import zipfile
from collections import Counter, defaultdict

# Sin esto, una consola de Windows en cp1252 revienta al imprimir el aviso de
# ⚠️  --limite / el de privacidad. Mismo patron que scripts/privacy_scan.py.
# hasattr() porque reconstruir_303.py IMPORTA este modulo (from retro_semaforo
# import ...), y sys.stdout no siempre es un TextIOWrapper real en ese momento
# (ver test_motor_veredicto.py: StringIO no tiene .reconfigure()).
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import motor_veredicto as mv
import contrato_datos
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
    # BUG REAL cazado el 25-08-2026, no teorico: la version anterior leia los
    # descriptores de campo de 32 en 32 bytes y paraba por CONTADOR
    # (leidos < len_cab - 1). Los ficheros reales de ContaPlus llevan un byte
    # de relleno extra tras el terminador (0x0D) que esa cuenta no preveia: al
    # detectar el terminador, el bloque de 32 bytes que lo contenia YA se habia
    # consumido del stream, y la limpieza final leia de mas encima. El cursor
    # quedaba 32 bytes dentro del primer registro real, y ese desplazamiento
    # se arrastraba a TODOS los registros siguientes. Con eso, lo que el script
    # creia que era SUBCTA (byte 15) caia en mitad de PTADEBE (byte 47) — casi
    # siempre a cero. Resultado antes del fix: 1.326 asientos leidos sobre un
    # corpus que fase0_asientos.py habia medido esta misma manana en 275.566,
    # 0% de patron de compra cuando el dato real es 47,81%.
    #
    # El arreglo: leer de UN GOLPE exactamente `len_cab - 32` bytes. Asi el
    # cursor del stream queda en `len_cab` SIEMPRE, sin importar donde caiga el
    # terminador dentro de ese bloque ni cuanto relleno haya. Es la misma
    # tecnica ya probada todo el dia en los fase0_*.py contra este mismo
    # corpus real. No fallaba porque adivinara bien las cabeceras: fallaba
    # porque nunca dependia de adivinarlas.
    resto = stream.read(len_cab - 32)
    campos, off, pos = [], 0, 1
    while off + 32 <= len(resto):
        if resto[off] == 0x0D:
            break
        d = resto[off:off + 32]
        nombre = d[:11].split(b"\x00")[0].decode("cp1252", "replace").strip()
        tam = d[16]
        campos.append({"nombre": nombre, "pos": pos, "tam": tam,
                       "tipo": chr(d[11])})
        pos += tam
        off += 32
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


def numero_documento(rec, cNFACTICK, cDOCUMENTO, cFACTURA):
    """Numero de documento/factura de una linea, probando varios campos.

    BUG REAL cazado el 25-08-2026 (diag_campos_criticos.py): la version
    anterior resolvia el campo con `idx.get("DOCUMENTO") or idx.get("FACTURA")`
    UNA VEZ POR CONTENEDOR. Pero `.get()` sobre el diccionario de esquema
    devuelve el DESCRIPTOR del campo, que existe siempre (los 91 campos estan
    en las 1.287 copias) — asi que ese `or` nunca caia al segundo candidato,
    aunque el primero estuviera vacio en la practica. Con eso, y con DOCUMENTO
    relleno solo el 0,05% de las veces, nº_documento (uno de los seis
    CAMPOS_CRITICOS) faltaba en el 99,94% de los asientos de compra reales, y
    eso tumbaba datos_integros en cascada: aritmetica_base_tipo, cuadre_total
    y suma_tramos salian NO_COMPROBADO no porque la factura fuera dudosa, sino
    porque el reconstructor nunca encontraba el numero.

    Medido el mismo dia sobre 154.130 lineas de IVA soportado (472): DOCUMENTO
    0,05%, FACTURA 0,07% (numerico, cero no cuenta como relleno), NFACTICK
    99,98%. Nadie miraba NFACTICK.

    Se prueba POR LINEA, no una vez por contenedor: el campo que trae el dato
    puede variar entre lineas del mismo asiento. NFACTICK y FACTURA son
    numericos: cero significa vacio, igual que en cualquier otro campo del
    proyecto — nunca se trata un cero como si fuera el numero de documento.
    """
    if cNFACTICK:
        v = num(rec, cNFACTICK)
        if v != 0.0:
            return str(int(v)) if v == int(v) else str(v)
    if cDOCUMENTO:
        t = txt(rec, cDOCUMENTO)
        if t:
            return t
    if cFACTURA:
        v = num(rec, cFACTURA)
        if v != 0.0:
            return str(int(v)) if v == int(v) else str(v)
    return ""


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

    # NOVENO ARREGLO del dia (25-08-2026), encontrado con diag_retencion.py
    # tras revisar por que cuadre_total seguia siendo el mayor bloque de ROJO.
    # Inversion del sujeto pasivo (ISP): ademas del 472 (IVA soportado,
    # deducible), el asiento lleva una linea en 477 (Hacienda Publica, IVA
    # repercutido) — el comprador se autorrepercute el IVA que el proveedor NO
    # le ha cobrado (construccion en subcontrata, ciertos residuos/metales,
    # telefonos/microprocesadores, algunas operaciones intracomunitarias...).
    # El total de la factura, en estos casos, NO INCLUYE el IVA por diseno: no
    # es una compra descuadrada, es una factura de otra forma que el patron de
    # tres cuentas de este reconstructor no representa.
    #
    # Medido: 644 de los 2.228 cuadre_total=FALLO (29,0%) llevan una linea 477
    # cuyo HABER explica la diferencia al centimo en el 99,7% de los casos
    # (desvio mediano 0.0 — por el DEBE no explica nada, mediana 96,85 EUR).
    # Disjunto de la retencion (475): solo 2 asientos llevan ambas. Se cuenta
    # aparte, igual que SIN_IVA — el diario dice lo que se contabilizo, no
    # puede fingir el total que la factura de verdad llevaba escrito.
    if any(l[0].startswith("477") for l in lineas):
        return "ISP"

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
    if len(ivas) == 1:
        # UN SOLO TIPO DE IVA (el caso dominante: 37.798 de 47.048 compras son
        # asi). La base es la suma de lo llevado a la cuenta de gasto — SIN
        # ninguna division de por medio.
        #
        # BUG REAL cazado el 25-08-2026, no preventivo: guard_retencion_vs_error
        # fallaba al 41,9% sobre datos reales. Investigado hasta el final:
        # sobre 38.527 asientos simples de 3 lineas, el propio asiento cuadra
        # DEBE=HABER al 100% -- pero derivar la base como cuota/tipo (la unica
        # via cuando BASEIMPO esta vacio, que es el 99,2% de las veces) solo
        # coincidia con lo que de verdad se llevo a la cuenta de gasto en el
        # 58,69% de los casos. Diferencia mediana: 0,01 EUR -- el redondeo de
        # invertir por division lo que ContaPlus obtuvo por multiplicacion al
        # contabilizar. El asiento estaba bien; el instrumento lo desconfiaba
        # por un centimo que el ni siquiera necesitaba inventar.
        #
        # BASEIMPO sigue teniendo prioridad cuando esta genuinamente relleno
        # (es el dato mas directo que existe), pero eso es solo el 0,78% de
        # las lineas — la practica totalidad de los casos pasa por el gasto.
        tipo = int(ivas[0][3])
        base_directa = ivas[0][5]
        base = base_directa if base_directa > 0 else round(sum(l[1] for l in gastos), 2)
        por_tipo[tipo] += base
    else:
        # Varios tipos de IVA en el mismo asiento: no hay forma directa de
        # saber que parte del gasto corresponde a cada tipo por separado, asi
        # que se deriva la PROPORCION por la via de siempre (cuota/tipo) y
        # LUEGO se reescala el conjunto para que la suma cuadre EXACTA con
        # base_total (que ya es exacto, viene del gasto, ver mas abajo).
        #
        # SEPTIMO ARREglo del dia (25-08-2026), consecuencia directa del
        # sexto: al hacer base_total exacto sin tocar este reparto por tipo,
        # suma_tramos paso a comparar una fuente exacta contra una con el
        # ruido de siempre — y se convirtio en el guard que mas ROJO causaba,
        # un fallo NUEVO introducido al arreglar el anterior sin revisar esta
        # consecuencia. Sin el reescalado, cuadre_total y suma_tramos se
        # contradicen entre si sobre el MISMO asiento: uno exige que la base
        # sea la del gasto, el otro que sume lo que dice cada linea de IVA.
        # No pueden ser ciertas las dos con dos fuentes distintas.
        #
        # El reparto POR TIPO sigue siendo una estimacion (no hay atribucion
        # exacta sin mas informacion) pero la SUMA ya no lo es: se ajusta el
        # tramo mayor con el resto del redondeo para que sea exacta, no solo
        # aproximada.
        derivado = {}
        for l in ivas:
            tipo, cuota, base = l[3], l[1], l[5]
            if base <= 0 and tipo > 0:
                base = round(cuota / (tipo / 100.0), 2)
            derivado[int(tipo)] = derivado.get(int(tipo), 0.0) + base
        suma_derivada = sum(derivado.values())
        gasto_total_bruto = round(sum(l[1] for l in gastos), 2)
        if suma_derivada > 0 and gasto_total_bruto > 0:
            factor = gasto_total_bruto / suma_derivada
            for t, b in derivado.items():
                por_tipo[t] = round(b * factor, 2)
            diff = round(gasto_total_bruto - sum(por_tipo.values()), 2)
            if diff:
                t_mayor = max(por_tipo, key=por_tipo.get)
                por_tipo[t_mayor] = round(por_tipo[t_mayor] + diff, 2)
        else:
            por_tipo.update(derivado)

    # CUOTA por tipo: NUNCA derivada de la base, a diferencia de esta. La
    # cuota de cada linea de IVA (EURODEBE de la cuenta 472) es un dato
    # DIRECTO y siempre presente -- no como BASEIMPO, que falta el 99,2% de
    # las veces y obliga a estimar la base. No hay nada que estimar aqui:
    # se suma tal cual, agrupado por tipo.
    #
    # OCTAVO ARREGLO del dia (25-08-2026), encontrado por auto-revision tras
    # el septimo: antes esta misma cuota se recalculaba como `base * tipo/100`
    # usando la base YA REESCALADA por el arreglo 7 para cuadrar con
    # base_total -- una base pensada para cuadrar SUMA_TRAMOS, reutilizada
    # para alimentar el guard de CUOTA (aritmetica_base_tipo), que compara
    # contra iva_total, una tercera cifra exacta distinta de base_total.
    # Mismo patron que el septimo arreglo, un nivel mas abajo: dos guards
    # exigiendole cifras distintas a una unica fuente derivada, y solo una
    # de las dos podia cuadrar. Medido con diag_aritmetica_tipo.py sobre el
    # corpus real: aritmetica_base_tipo=FALLO subia con el numero de tramos
    # (1 tramo 1,69%, 2 tramos 12,84%, 3 tramos 27,17%, 4 tramos 95,83%,
    # 5 tramos 100%) -- la misma firma que tenia suma_tramos antes del
    # septimo arreglo. Al sumar la cuota real en vez de derivarla, ambos
    # guards pueden cuadrar a la vez porque cada uno compara contra la
    # cifra de la que de verdad viene: base contra base_total, cuota contra
    # iva_total.
    cuota_por_tipo = defaultdict(float)
    for l in ivas:
        cuota_por_tipo[int(l[3])] += l[1]

    if por_tipo:
        fila["tramos_iva"] = [
            {"tipo": t, "base": round(por_tipo.get(t, 0.0), 2),
             "cuota": round(cuota_por_tipo.get(t, 0.0), 2)}
            for t in sorted(set(por_tipo) | set(cuota_por_tipo))
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

    # Retencion de IRPF (mismo arreglo del 25-08-2026 que ISP, mas arriba).
    # La cuenta 475xxx (Hacienda Publica, acreedora por conceptos fiscales)
    # recoge lo retenido a un proveedor con retencion (servicios
    # profesionales, alquileres de local...). Sin capturarla, irpf_retencion
    # nunca se rellena, "irpf or 0.0" cae siempre a 0.0 en el motor, y
    # cuadre_total exige base+iva=total en facturas donde eso NUNCA fue
    # cierto por diseno: el total pagado es neto de retencion.
    #
    # Medido: 784 de los 2.228 cuadre_total=FALLO (35,2%) llevan una linea
    # 475 cuyo HABER explica la diferencia al centimo en el 99,1% de los
    # casos (desvio mediano 0.0). CONVENCION DEL CONTRATO (ver
    # motor_veredicto.py linea 24): irpf_retencion se guarda en NEGATIVO.
    retenciones = [l for l in lineas if l[0].startswith("475")]
    if retenciones:
        fila["irpf_retencion"] = -round(sum(l[2] for l in retenciones), 2)

    # CORREGIDO 20-08-2026: aqui habia un `if iva_total > 0` que DESCARTABA un
    # IVA de cero legitimo (tipo 0%: pan, leche, fruta) en vez de registrarlo.
    # Es exactamente el error MISSING-vs-ZERO que este proyecto arreglo en el
    # motor, cometido de nuevo en el instrumento que lo mide. Un cero calculado
    # es un DATO; solo se omite el campo cuando no se ha podido calcular.
    # BASE_TOTAL: SIEMPRE la suma de lo llevado a la cuenta de gasto, NUNCA
    # derivada de las lineas de IVA. Sexto arreglo del dia (25-08-2026),
    # extiende el del punto anterior a CUALQUIER numero de tipos de IVA en el
    # mismo asiento — antes solo se corregia el caso de un tipo unico y el de
    # 2+ tipos seguia con el ruido viejo. Medido tras el primer arreglo:
    # con 1 tipo, 8,0% de FALLO (residuo plausible); con 2 tipos, 65,5%; con
    # 3, 84,3%; con 4+, 100,0% — la misma derivacion por cuota/tipo, sin
    # cerrar del todo.
    #
    # La suma de gasto NO NECESITA saber que porcion corresponde a que tipo:
    # por partida doble, gasto(DEBE) + iva(DEBE) = acreedor(HABER) siempre,
    # asi que la suma TOTAL de gasto es la base total sea cual sea el reparto
    # entre tipos. Ese reparto (por_tipo, mas arriba) sigue haciendo falta
    # para el desglose fiscal tramos_iva —ahi si hace falta derivar, porque
    # no hay otra fuente por tipo— pero ya no decide base_total.
    base_total = round(sum(l[1] for l in gastos), 2)
    if base_total <= 0:
        base_total = round(sum(por_tipo.values()), 2)
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
    n_asientos = n_compras = n_reconstruidas = n_sin_iva = n_isp = 0
    vistos_dup = set()
    # DEDUPLICACION ENTRE COPIAS DE SEGURIDAD (25-08-2026, bug real, no
    # preventivo). Una copia de ContaPlus contiene el HISTORICO COMPLETO hasta
    # esa fecha, asi que el mismo asiento aparece en todas las copias
    # posteriores. Medido esta misma manana con fase0_asientos.py sobre este
    # mismo corpus: 275.566 asientos totales, 101.122 UNICOS (factor 2,73x).
    #
    # Sin esto, guard_anti_duplicado (que compara NIF+documento+fecha+total,
    # ver contrato_datos.clave_documental) marca FALLO cada vez que vuelve a
    # ver el MISMO asiento en la siguiente copia — no porque este duplicado de
    # verdad, sino porque el corpus lo repite. La primera ejecucion contra el
    # corpus real dio 77,36% de ROJO, con anti_duplicado=FALLO en el 76,7% de
    # los casos: casi calcaba la tasa de duplicacion ya conocida, no la
    # calidad de las facturas. Es la misma trampa de "medir frecuencia de
    # copia de seguridad, no practica contable" que FASE0_RESULTADOS.md avisa
    # desde el primer dia — caida aqui, en otra fase del proyecto.
    #
    # vistos_contenido es DISTINTO de vistos_dup a proposito: este filtra
    # ANTES de llegar al motor (repeticion de copia, no error); vistos_dup
    # sigue siendo del guard, y ahora si detecta duplicados REALES dentro del
    # conjunto ya deduplicado (la misma factura tecleada dos veces de verdad).
    vistos_contenido = set()
    n_duplicados_entre_copias = 0

    # SEGUNDA CAPA, mas fina (25-08-2026, bug real). La huella de bytes de
    # arriba coincidia exacta con fase0_asientos.py (101.122 unicos) y aun asi
    # anti_duplicado=FALLO seguia siendo el guard que mas ROJO causaba
    # (16.383, el 75,8% del ROJO total). Investigado hasta el final: de esos
    # 16.383, el 94,9% son la MISMA factura en OTRA carpeta de backup, con la
    # MISMA cuenta contable (99,5%) y el MISMO importe (99,8%) — no cambia
    # nada que importe, cambia algun campo tecnico (posiblemente CTIMESTAMP)
    # que la huella de bytes SI ve pero que no tiene ningun significado
    # contable. anti_duplicado estaba acertando; lo que fallaba era no
    # filtrar ANTES estas repeticiones, igual que ya se filtran las
    # byte-identicas.
    #
    # Se deduplica por la MISMA clave que ya usa el guard (NIF+documento+
    # fecha+total, ver contrato_datos.clave_documental) — la clave semantica
    # de "es esta la misma factura", no la clave byte a byte de "es este el
    # mismo registro". Con esto, anti_duplicado solo puede disparar sobre lo
    # que de verdad es nuevo para el: una factura tecleada dos veces DE
    # VERDAD, que es exactamente para lo que existe.
    vistos_clave_documental = set()
    n_duplicados_semanticos = 0
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
                    # Tres candidatos, probados POR LINEA (ver numero_documento):
                    # nunca "el primero que exista en el esquema", que era el bug.
                    cNFACTICK = idx.get("NFACTICK")
                    cDOCUMENTO = idx.get("DOCUMENTO")
                    cFACTURA = idx.get("FACTURA")
                    if not (cA and cS):
                        continue

                    grupos = defaultdict(list)
                    while True:
                        rec = fh.read(len_reg)
                        if len(rec) < len_reg or rec[:1] == b"\x1a":
                            break
                        if rec[:1] == b"*":
                            continue
                        # Huella de la LINEA (bytes crudos, misma tecnica que
                        # fase0_asientos.py). Se usa solo para deduplicar
                        # asientos entre copias; nunca se publica el hash.
                        h_linea = hashlib.blake2b(rec, digest_size=8).digest()
                        grupos[int(num(rec, cA))].append((
                            cuenta(rec, cS), num(rec, cED), num(rec, cEH),
                            num(rec, cIVA), txt(rec, cNIF), num(rec, cBASE),
                            txt(rec, cFEC),
                            numero_documento(rec, cNFACTICK, cDOCUMENTO, cFACTURA),
                            num(rec, cREC),
                            h_linea,
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
                        # Huella del ASIENTO completo: hash de las huellas de
                        # sus lineas, ordenadas para que el orden de lectura
                        # no importe. Si ya se ha visto este contenido exacto
                        # en una copia anterior, es la MISMA factura repetida
                        # por solaparse los backups, no un asiento nuevo.
                        huella = hashlib.blake2b(
                            b"".join(sorted(l[9] for l in lineas)),
                            digest_size=16).digest()
                        if huella in vistos_contenido:
                            n_duplicados_entre_copias += 1
                            continue
                        vistos_contenido.add(huella)

                        n_asientos += 1
                        fila = reconstruir_compra(lineas)
                        if fila is None:
                            continue
                        if fila == "SIN_IVA":
                            n_sin_iva += 1
                            continue
                        if fila == "ISP":
                            n_isp += 1
                            continue
                        n_compras += 1

                        # Filtro semantico: misma factura, otra copia (ver el
                        # comentario largo mas arriba). Se calcula la clave
                        # ANTES de gastar un ciclo del motor en ella.
                        clave_doc = contrato_datos.canonizar(fila).clave_documental()
                        clave_h = hashlib.blake2b(
                            repr(clave_doc).encode("utf-8"), digest_size=12).digest()
                        if clave_h in vistos_clave_documental:
                            n_duplicados_semanticos += 1
                            continue
                        vistos_clave_documental.add(clave_h)

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

    total_visto = n_asientos + n_duplicados_entre_copias
    print("=" * 66)
    print("RETRO-SEMAFORO — el motor sobre contabilidad YA CONTABILIZADA")
    print("=" * 66)
    print(f"  asientos vistos (con duplicados entre copias) : {total_visto:,}")
    print(f"  duplicados entre copias (mismo asiento, otra copia de seguridad)"
          f" : {n_duplicados_entre_copias:,} ({pct(n_duplicados_entre_copias, total_visto)}%)")
    print(f"  asientos UNICOS evaluados (deduplicados)       : {n_asientos:,}")
    print(f"  patron de compra         : {n_compras:,} ({pct(n_compras, n_asientos)}%)")
    print(f"  duplicados semanticos (misma factura, otra copia, campo tecnico"
          f" distinto) : {n_duplicados_semanticos:,} ({pct(n_duplicados_semanticos, n_compras)}%)")
    print(f"  evaluados por el motor   : {n_reconstruidas:,}")
    print(f"  compras SIN linea de IVA : {n_sin_iva:,}  (exentas / no sujetas /")
    print(f"                             intracomunitarias: el diario no dice cual,")
    print(f"                             asi que NO se evaluan y NO cuentan como falsos rojos)")
    print(f"  compras con INVERSION DEL SUJETO PASIVO (472+477 a la vez): {n_isp:,}")
    print(f"                             el proveedor no cobra IVA, el comprador se lo")
    print(f"                             autorrepercute: el total no incluye IVA por diseno,")
    print(f"                             asi que tampoco se evaluan ni cuentan como falsos rojos)")
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
        "version": "retro_semaforo v2 (25-08-2026, deduplicado entre copias)",
        "asientos_vistos_con_duplicados": total_visto,
        "duplicados_entre_copias": n_duplicados_entre_copias,
        "pct_duplicados_entre_copias": pct(n_duplicados_entre_copias, total_visto),
        "asientos_leidos": n_asientos,
        "patron_compra": n_compras,
        "duplicados_semanticos": n_duplicados_semanticos,
        "pct_duplicados_semanticos": pct(n_duplicados_semanticos, n_compras),
        "compras_sin_linea_iva_no_evaluadas": n_sin_iva,
        "compras_isp_no_evaluadas": n_isp,
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
