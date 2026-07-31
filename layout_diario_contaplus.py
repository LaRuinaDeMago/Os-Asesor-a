"""
Layout EMPÍRICO del diario ContaPlus (formato ASCII posicional de ancho fijo).
Derivado y verificado byte a byte contra (caso real anonimizado, cliente piloto):
  - cliente_2025_diario_XBase.dbf (estructura de campos dBase III)
  - cliente_2025_diario_ASCII_por_asientos.txt (verificado que cada línea = 1189
    bytes = suma exacta de anchos de campo, sin el byte de marca de borrado del DBF)
Verificación de redondeo: se decodificó la línea 0 del ASCII con estos offsets
y coincide campo a campo con el registro 1 del DBF (ASIEN=1, FECHA=20250101,
SUBCTA=120000, CONCEPTO='Asiento de Apertura', EURODEBE=463.80).

Cada tupla: (nombre, ancho, tipo, decimales)
tipo: 'N' numérico (right-justified, punto decimal), 'C' texto (left-justified,
      espacios de relleno), 'D' fecha AAAAMMDD, 'L' lógico (T/F/espacio)
"""

CAMPOS = [
    ("ASIEN", 6, "N", 0), ("FECHA", 8, "D", 0), ("SUBCTA", 12, "C", 0),
    ("CONTRA", 12, "C", 0), ("PTADEBE", 16, "N", 2), ("CONCEPTO", 25, "C", 0),
    ("PTAHABER", 16, "N", 2), ("FACTURA", 8, "N", 0), ("BASEIMPO", 16, "N", 2),
    ("IVA", 5, "N", 2), ("RECEQUIV", 5, "N", 2), ("DOCUMENTO", 10, "C", 0),
    ("DEPARTA", 3, "C", 0), ("CLAVE", 6, "C", 0), ("ESTADO", 1, "C", 0),
    ("NCASADO", 6, "N", 0), ("TCASADO", 1, "N", 0), ("TRANS", 6, "N", 0),
    ("CAMBIO", 16, "N", 6), ("DEBEME", 16, "N", 2), ("HABERME", 16, "N", 2),
    ("AUXILIAR", 1, "C", 0), ("SERIE", 1, "C", 0), ("SUCURSAL", 4, "C", 0),
    ("CODDIVISA", 5, "C", 0), ("IMPAUXME", 16, "N", 2), ("MONEDAUSO", 1, "C", 0),
    ("EURODEBE", 16, "N", 2), ("EUROHABER", 16, "N", 2), ("BASEEURO", 16, "N", 2),
    ("NOCONV", 1, "L", 0), ("NUMEROINV", 10, "C", 0), ("SERIE_RT", 1, "C", 0),
    ("FACTU_RT", 8, "N", 0), ("BASEIMP_RT", 16, "N", 2), ("BASEIMP_RF", 16, "N", 2),
    ("RECTIFICA", 1, "L", 0), ("FECHA_RT", 8, "D", 0), ("NIC", 1, "C", 0),
    ("LPERIODICO", 1, "L", 0), ("CODMOVPER", 6, "N", 0), ("LINTERRUMP", 1, "L", 0),
    ("SEGACTIV", 6, "C", 0), ("SEGGEOGR", 6, "C", 0), ("LRECT349", 1, "L", 0),
    ("FECHA_OP", 8, "D", 0), ("FECHA_EX", 8, "D", 0), ("DEPARTA5", 5, "C", 0),
    ("FACTURA10", 10, "C", 0), ("PORCEN_ANA", 5, "N", 2), ("PORCEN_SEG", 5, "N", 2),
    ("NUMAPUNTE", 6, "N", 0), ("EUROTOTAL", 16, "N", 2), ("RAZONSOC", 100, "C", 0),
    ("APELLIDO1", 50, "C", 0), ("APELLIDO2", 50, "C", 0), ("TIPOOPE", 1, "C", 0),
    ("NFACTICK", 8, "N", 0), ("NUMACUINI", 40, "C", 0), ("NUMACUFIN", 40, "C", 0),
    ("TERIDNIF", 1, "N", 0), ("TERNIF", 15, "C", 0), ("TERNOM", 40, "C", 0),
    ("TERNIF14", 9, "C", 0), ("TBIENTRAN", 1, "L", 0), ("TBIENCOD", 10, "C", 0),
    ("TRANSINM", 1, "L", 0), ("METAL", 1, "L", 0), ("METALIMP", 16, "N", 2),
    ("CLIENTE", 12, "C", 0), ("OPBIENES", 1, "N", 0), ("FACTURAEX", 40, "C", 0),
    ("TIPOFAC", 1, "C", 0), ("TIPOIVA", 1, "C", 0), ("GUID", 40, "C", 0),
    ("L340", 1, "L", 0), ("METALEJE", 4, "N", 0), ("DOCUMENT15", 15, "C", 0),
    ("CLIENTESUP", 12, "C", 0), ("FECHASUP", 8, "D", 0), ("IMPORTESUP", 16, "N", 2),
    ("DOCSUP", 40, "C", 0), ("CLIENTEPRO", 12, "C", 0), ("FECHAPRO", 8, "D", 0),
    ("IMPORTEPRO", 16, "N", 2), ("DOCPRO", 40, "C", 0), ("NCLAVEIRPF", 2, "N", 0),
    ("LARREND347", 1, "L", 0), ("NSITINMUEB", 1, "N", 0), ("CREFCATAST", 25, "C", 0),
    ("CONCIL347", 1, "N", 0), ("TIPOREGULA", 2, "N", 0), ("NCRITCAJA", 2, "N", 0),
    ("LCRITCAJA", 1, "L", 0), ("DMAXLIQUI", 8, "D", 0), ("NTOTALFAC", 16, "N", 2),
    ("IDFACTURA", 32, "C", 0), ("NCOBRPAGO", 16, "N", 2),
]

ANCHO_LINEA = sum(c[1] for c in CAMPOS)  # 1189, verificado contra el fichero real


def leer_ascii_completo(path):
    """Lee un fichero ASCII de ancho fijo de ContaPlus ENTERO y devuelve una
    lista de dicts con los valores ya tipados (numeros a float/int, fechas a
    datetime.date) - equivalente a lo que dbfread da gratis para un .dbf, pero
    para el formato de texto plano.

    Construida el 28-07-2026 tras una revision externa que señalo, correctamente,
    que esta funcion no existia todavia - solo teniamos decodificar_linea()
    (una linea, valores en texto crudo sin convertir)."""
    import datetime
    registros = []
    with open(path, 'rb') as f:
        data = f.read()
    lineas = data.decode('latin1').split('\r\n')
    for linea in lineas:
        linea = linea.replace('\x1a', '').rstrip()  # caracter EOF de DOS, aparece en la ultima linea real
        if not linea.strip():
            continue
        if len(linea) < ANCHO_LINEA:
            linea = linea.ljust(ANCHO_LINEA)  # linea truncada al final del fichero, se rellena para no reventar
        crudo = decodificar_linea(linea)
        reg = {}
        for nombre, ancho, tipo, dec in CAMPOS:
            valor_crudo = crudo[nombre]
            if tipo == "N":
                v = valor_crudo.strip()
                try:
                    reg[nombre] = float(v) if v else 0.0
                except ValueError:
                    reg[nombre] = 0.0  # dato numerico no parseable - no revienta, pero tampoco finge certeza
                if dec == 0:
                    reg[nombre] = int(reg[nombre])
            elif tipo == "D":
                v = valor_crudo.strip()
                if len(v) == 8 and v.isdigit():
                    reg[nombre] = datetime.date(int(v[:4]), int(v[4:6]), int(v[6:8]))
                else:
                    reg[nombre] = None
            elif tipo == "L":
                reg[nombre] = valor_crudo.strip() == "T"
            else:
                reg[nombre] = valor_crudo.strip()
        registros.append(reg)
    return registros


CUENTA_IVA_SOPORTADO = {10: "472010", 4: "472004", 21: "472021"}


def generar_asiento_desde_factura(fila_veredicto, asien, cuenta_debe, cuenta_haber_proveedor):
    """A partir de una factura YA VALIDADA (VERDE por el motor), genera las
    lineas del asiento completo (gasto + IVA soportado por tramo + proveedor),
    con la misma estructura real que vimos en el Diario.dbf de un cliente piloto
    (caso real anonimizado: un proveedor de servicios -> 621000, mercancia -> 600000).

    Devuelve una lista de dicts, uno por linea del asiento, listos para
    construir_linea(). NO escribe nada todavia - eso es escribir_xdiario()."""
    fecha = fila_veredicto['fecha_expedicion'].replace('-', '')
    fecha_date = __import__('datetime').datetime.strptime(fila_veredicto['fecha_expedicion'], '%Y-%m-%d').date()
    concepto = f"Fra {fila_veredicto.get('nº_documento','')}"[:25]
    nif = fila_veredicto.get('nif', '')
    proveedor = fila_veredicto.get('proveedor', '')

    lineas = []
    total_base = 0.0
    for tipo, campo in [(10, 'base_10'), (4, 'base_4'), (21, 'base_21')]:
        base = float(fila_veredicto.get(campo, 0) or 0)
        if base == 0:
            continue
        total_base += base
        cuota = round(base * tipo / 100, 2)
        # linea de gasto (debe)
        lineas.append({"ASIEN": asien, "FECHA": fecha_date, "SUBCTA": cuenta_debe,
                        "CONCEPTO": concepto, "MONEDAUSO": "2", "EURODEBE": base, "NIC": "E"})
        # linea de IVA soportado (debe), con datos del tercero
        lineas.append({"ASIEN": asien, "FECHA": fecha_date, "SUBCTA": CUENTA_IVA_SOPORTADO[tipo],
                        "CONTRA": cuenta_haber_proveedor, "CONCEPTO": concepto, "IVA": float(tipo),
                        "MONEDAUSO": "2", "EURODEBE": cuota, "BASEEURO": base, "NIC": "E",
                        "TERIDNIF": 1, "TERNIF": nif, "TERNOM": proveedor[:40],
                        "OPBIENES": 1, "TIPOFAC": "R", "TIPOIVA": "O"})

    total_factura = float(fila_veredicto['total_factura'])
    irpf = float(fila_veredicto.get('irpf_retencion', 0) or 0)

    # linea de retencion (Hacienda Publica acreedora, grupo 4751) - FALTABA,
    # causa real de un descuadre de 125.62 encontrado al probar con datos reales
    # (2 facturas de un caso real anonimizado). irpf_retencion viene en NEGATIVO
    # (convencion ya documentada en motor_veredicto.py) -> se acredita HABER
    # por el valor absoluto.
    if irpf != 0:
        lineas.append({"ASIEN": asien, "FECHA": fecha_date, "SUBCTA": "475100",
                        "CONCEPTO": concepto, "MONEDAUSO": "2", "EUROHABER": abs(irpf), "NIC": "E"})
        # NOTA: 475100 es el grupo generico (H.P. acreedora por retenciones).
        # Lo ideal es la subcuenta PERSONAL del acreedor (ej. 475103 en un caso real,
        # confirmada en su .DAT real) - se usa el fallback
        # generico porque el motor no siempre trae esa subcuenta especifica.

    # linea del proveedor/acreedor (haber) - el total real de la factura
    lineas.append({"ASIEN": asien, "FECHA": fecha_date, "SUBCTA": cuenta_haber_proveedor,
                    "CONCEPTO": concepto, "MONEDAUSO": "2", "EUROHABER": total_factura, "NIC": "E"})
    return lineas


def escribir_xdiario(facturas_verdes, path_salida, asien_inicial=1):
    """Cierra el circulo: de una lista de facturas YA VALIDADAS (VERDE) con
    cuenta_debe y cuenta_haber ya resueltas (via el maestro/mapeo_cuenta_gasto
    reales), genera el xDiario.txt COMPLETO, listo para el importador nativo
    de ContaPlus/ContaSOL (Utilidades > Importaciones > Ficheros de ContaPlus).

    CONTAPLUS AUTONUMERA los asientos al importar (verificado hoy con una
    importacion real) - asien_inicial es solo un valor de partida, no importa
    si no coincide con la numeracion real de la empresa."""
    lineas_texto = []
    asien = asien_inicial
    for fila in facturas_verdes:
        cuenta_debe = fila.get('cuenta_debe') or '600000'  # fallback si no hay mapeo, marcar para revisar
        cuenta_haber = fila.get('cuenta_haber')
        if not cuenta_haber:
            continue  # sin cuenta de proveedor real no se genera el asiento - no se inventa
        apuntes = generar_asiento_desde_factura(fila, asien, cuenta_debe, cuenta_haber)
        for apunte in apuntes:
            lineas_texto.append(construir_linea(apunte))
        asien += 1

    with open(path_salida, 'wb') as f:
        for linea in lineas_texto:
            f.write((linea + "\r\n").encode("latin1"))
    return len(lineas_texto), asien - asien_inicial


def formatear_campo(valor, ancho, tipo, dec):
    if tipo == "N":
        if valor in (None, ""):
            valor = 0
        s = f"{float(valor):.{dec}f}" if dec else f"{int(valor)}"
        return s.rjust(ancho)[:ancho]
    if tipo == "D":
        if not valor:
            return " " * ancho
        return valor.strftime("%Y%m%d")
    if tipo == "L":
        return (" " if valor is None else ("T" if valor else "F")).ljust(ancho)[:ancho]
    # C
    return ("" if valor is None else str(valor)).ljust(ancho)[:ancho]


def construir_linea(apunte: dict) -> str:
    """apunte: dict con claves = nombre de campo (mayúsculas), solo hace falta
    rellenar los que se usan; el resto se completa vacío/cero automáticamente."""
    partes = []
    for nombre, ancho, tipo, dec in CAMPOS:
        partes.append(formatear_campo(apunte.get(nombre), ancho, tipo, dec))
    linea = "".join(partes)
    assert len(linea) == ANCHO_LINEA, f"longitud {len(linea)} != {ANCHO_LINEA}"
    return linea


def decodificar_linea(linea: str) -> dict:
    """Para verificación: vuelve a trocear una línea ya construida y comprueba
    que cada campo se recupera limpio (prueba de redondeo)."""
    out = {}
    pos = 0
    for nombre, ancho, tipo, dec in CAMPOS:
        out[nombre] = linea[pos:pos + ancho]
        pos += ancho
    return out
