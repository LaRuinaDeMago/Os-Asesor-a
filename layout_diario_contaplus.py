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
    lineas = data.decode(CODIFICACION, errors='replace').split('\r\n')
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


#: AMPLIADO 21-08-2026: faltaban el 5% y el 0%, que existen desde 2023 y que el
#: motor ya sabe validar. Sin ellos, una factura legitima a esos tipos reventaba
#: aqui con un KeyError, en el ultimo paso de todos.
CUENTA_IVA_SOPORTADO = {0: "472000", 4: "472004", 5: "472005",
                        10: "472010", 21: "472021"}


def generar_asiento_desde_factura(fila_veredicto, asien, cuenta_debe, cuenta_haber_proveedor):
    """A partir de una factura YA VALIDADA (VERDE por el motor), genera las
    lineas del asiento completo (gasto + IVA soportado por tramo + proveedor),
    con la misma estructura real que vimos en el Diario.dbf de un cliente piloto
    (caso real anonimizado: un proveedor de servicios -> 621000, mercancia -> 600000).

    Devuelve una lista de dicts, uno por linea del asiento, listos para
    construir_linea(). NO escribe nada todavia - eso es escribir_xdiario()."""
    # CORREGIDO 21-08-2026 (ensayo_xdiario.py). Aqui habia un strptime con el
    # formato ISO fijo, el MISMO fallo que se acababa de corregir en los tres
    # guards de fecha del motor: con '15/03/2026' —el formato normal en Espana—
    # saltaba ValueError, y como nadie lo capturaba se llevaba por delante la
    # exportacion ENTERA, no una factura. Se entra por el contrato, que acepta
    # los cuatro formatos desde el primer dia.
    import contrato_datos
    _f = contrato_datos.parse_fecha(fila_veredicto.get('fecha_expedicion'))
    if _f.estado != contrato_datos.VALUE:
        raise ValueError("fecha de expedicion no interpretable")
    fecha_date = _f.valor
    concepto = f"Fra {fila_veredicto.get('nº_documento','')}"[:25]
    nif = fila_veredicto.get('nif', '')
    proveedor = fila_veredicto.get('proveedor', '')

    def _num(x):
        """Como float(), pero acepta el formato espanol ('132,90') igual que
        contrato_datos.parse_numero() - que es quien ya decidio que esta
        factura era VERDE.

        CORREGIDO 26-08-2026 (auditoria propia). Antes esta funcion hacia
        float(x) a pelo sobre los mismos campos que el motor lee en formato
        espanol (ver test_adversarial.py FAMILIA G, '1.328,90' -> VERDE). Una
        factura VERDE con importes en formato espanol pasaba el motor entero
        y reventaba aqui con ValueError, en el ULTIMO paso -> ContaPlus. El
        try/except de escribir_xdiario() la descartaba en silencio como un
        'ValueError' generico, sin que nadie viera nunca la causa real: el
        objetivo declarado del producto ('foto de la factura -> motor ->
        fichero importable -> ContaPlus') se rompia justo en el ultimo tramo,
        y ningun ensayo lo cazaba porque ensayo_xdiario.py solo probaba el
        formato espanol en la FECHA, no en los importes."""
        d = contrato_datos.parse_numero(x)
        return d.valor if d.utilizable else 0.0

    lineas = []
    total_base = 0.0
    tramos = [(tipo, _num(fila_veredicto.get(campo, 0)))
              for tipo, campo in ((10, 'base_10'), (4, 'base_4'), (21, 'base_21'))]
    # ANADIDO 21-08-2026, y era el defecto mas peligroso de todo el dia: una
    # factura de captura de camara —base, IVA y total, SIN desglose por tipos—
    # no entraba en este bucle, asi que el asiento salia con UNA sola linea: el
    # haber del proveedor, y cero en el debe. Un asiento descuadrado entrando en
    # la contabilidad real de un cliente.
    #
    # Y desde el 21-08 esa factura ya puede ser VERDE, asi que el caso paso de
    # imposible a ser el NORMAL. Se deduce el tramo del mismo sitio del que lo
    # deduce el motor: cuota/base, y solo si cae clavado en un tipo legal. Si no
    # se puede deducir, no se emite un asiento roto — se levanta y quien llama lo
    # cuenta. Inventar un tramo seria peor que no exportar la factura.
    if not any(b for _t, b in tramos):
        base_total = _num(fila_veredicto.get('base_total', 0))
        iva_total = _num(fila_veredicto.get('iva_total', 0))
        deducido = None
        if base_total:
            for tipo in sorted(CUENTA_IVA_SOPORTADO):
                if abs(iva_total - base_total * tipo / 100.0) <= 0.02:
                    deducido = tipo
                    break
        if deducido is None:
            raise ValueError("sin desglose por tipos y el tipo efectivo no es "
                             "deducible: no se puede generar un asiento cuadrado")
        tramos = [(deducido, base_total)]
    for tipo, base in tramos:
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

    _total_dato = contrato_datos.parse_numero(fila_veredicto.get('total_factura'))
    if not _total_dato.utilizable:
        raise ValueError("total_factura no interpretable")
    total_factura = _total_dato.valor
    irpf = _num(fila_veredicto.get('irpf_retencion', 0))

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
    de ContaPlus (Utilidades > Importaciones > Ficheros de ContaPlus).

    CONTAPLUS AUTONUMERA los asientos al importar (verificado hoy con una
    importacion real) - asien_inicial es solo un valor de partida, no importa
    si no coincide con la numeracion real de la empresa.

    SOBRE CONTASOL (revisado 27-08-2026, sesion Cloud): este docstring decia
    antes "listo para ContaPlus/ContaSOL" sin que nadie lo hubiera comprobado
    -- ni un test, ni una entrada de PROJECT_STATUS.md que dijera "verificado".
    Es exactamente la clase de afirmacion sin comprobar que este proyecto
    existe para cazar en otros sitios. Estado real:
    - El layout de CAMPOS de este fichero (arriba) esta verificado BYTE A BYTE
      contra un Diario.dbf real de ContaPlus (docstring del modulo). Eso sigue
      siendo cierto solo para ContaPlus.
    - Para ContaSOL, varias fuentes publicas independientes (no verificadas
      contra una instalacion real) coinciden en que ContaSOL tiene un modo de
      importacion dedicado y compatible: Utilidades > Importaciones >
      ContaPlus > Ficheros de ContaPlus, que acepta los mismos xSubcta.txt/
      xDiario.txt. Es plausible y esta bien respaldado, pero NO es lo mismo
      que haberlo comprobado -- la regla de este proyecto (aplicada al `.DAT`
      de ContaPlus, ahora aqui tambien) es no dar un formato por bueno sin
      verificarlo contra algo real.
    - VERIFICACION PENDIENTE, concreta: importar un xDiario.txt sintetico (el
      que genera ensayo_xdiario.py, sin ningun dato real) en una empresa de
      pruebas de ContaSOL y confirmar que entra limpio. Es la misma disciplina
      que ya se aplico para ContaPlus el 21-08-2026 ("verificado hoy con una
      importacion real"), pendiente de repetir para ContaSOL."""
    lineas_texto = []
    asien = asien_inicial
    descartadas = {}
    for fila in facturas_verdes:
        # CORREGIDO 21-08-2026: aqui habia un `or '600000'`, con el comentario
        # "fallback si no hay mapeo, marcar para revisar". No marcaba nada: metia
        # el gasto en Compras de mercaderias y seguia. Es inventarse una cuenta
        # contable, justo lo que el orquestador declara que no hace dos lineas
        # mas abajo con la del proveedor. Ahora se descarta y se cuenta.
        cuenta_debe = fila.get('cuenta_debe')
        cuenta_haber = fila.get('cuenta_haber')
        if not cuenta_haber or not cuenta_debe:
            que = 'sin cuenta de proveedor' if not cuenta_haber else 'sin cuenta de gasto'
            descartadas[que] = descartadas.get(que, 0) + 1
            continue
        try:
            apuntes = generar_asiento_desde_factura(fila, asien, cuenta_debe, cuenta_haber)
        except (ValueError, KeyError, TypeError) as e:
            # Una factura mala no puede llevarse por delante la tanda entera.
            descartadas[type(e).__name__] = descartadas.get(type(e).__name__, 0) + 1
            continue
        # LA INVARIANTE DEL ULTIMO PASO, y no estaba: un asiento que no cuadra no
        # se escribe. Es el equivalente contable de "nunca OK por omision" — mas
        # vale una factura sin exportar que un descuadre entrando en los libros
        # de un cliente, que ademas hay que ir a buscar a mano despues.
        debe = round(sum(float(a.get('EURODEBE', 0) or 0) for a in apuntes), 2)
        haber = round(sum(float(a.get('EUROHABER', 0) or 0) for a in apuntes), 2)
        if abs(debe - haber) > 0.01:
            descartadas['asiento descuadrado'] = descartadas.get('asiento descuadrado', 0) + 1
            continue
        for apunte in apuntes:
            lineas_texto.append(construir_linea(apunte))
        asien += 1

    with open(path_salida, 'wb') as f:
        for linea in lineas_texto:
            f.write((linea + "\r\n").encode(CODIFICACION, errors="replace"))
    if descartadas:
        print("  xDiario — facturas NO exportadas (no se inventa nada):")
        for motivo, n in sorted(descartadas.items()):
            print(f"      {n:>5}  {motivo}")
    return len(lineas_texto), asien - asien_inicial


#: Codificacion del fichero. ContaPlus corre en Windows y escribe cp1252, que es
#: latin-1 MAS el tramo 0x80-0x9F: el euro, las comillas tipograficas y las rayas.
#: Se leia y escribia en latin-1, y por eso un nombre de proveedor con un "€" o
#: unas comillas curvas —lo que produce Word, Excel y cualquier transcripcion por
#: IA— reventaba con UnicodeEncodeError y se llevaba por delante la EXPORTACION
#: ENTERA, no una factura. Encontrado el 21-08-2026 probando nombres realistas.
CODIFICACION = "cp1252"

#: Lo que cp1252 tampoco tiene y aun asi puede llegar de una captura por IA.
#: Se sustituye por su equivalente de una sola posicion, para no mover el ancho
#: fijo del registro, que es lo unico que ContaPlus no perdona.
EQUIVALENCIAS_ASCII = {
    '\u2018': "'", '\u2019': "'", '\u201a': "'", '\u201b': "'",
    '\u201c': '"', '\u201d': '"', '\u201e': '"',
    '\u2013': '-', '\u2014': '-', '\u2212': '-', '\u00ad': '-',
    '\u00a0': ' ', '\u2007': ' ', '\u202f': ' ',
    '\u2026': '.', '\u2022': '.', '\u00b7': '.',
}


def normalizar_texto(s):
    """Deja un texto que cp1252 pueda escribir, SIN cambiar su longitud.

    El ancho fijo es lo unico que ContaPlus no perdona: si una linea mide un byte
    de mas o de menos, el fichero entero deja de ser importable. Por eso cada
    sustitucion es de UNA posicion por UNA posicion, nunca "—" -> "--".

    Lo que no tenga equivalente se convierte en '?'. Es feo a proposito: se ve en
    el concepto y avisa de que ahi hubo algo raro. Y solo puede pasar en campos
    de TEXTO — ningun importe, cuenta ni fecha pasa por aqui."""
    if not s:
        return s
    s = ''.join(EQUIVALENCIAS_ASCII.get(c, c) for c in str(s))
    return s.encode(CODIFICACION, errors='replace').decode(CODIFICACION)


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
    # C — se normaliza ANTES de rellenar, para que el ancho lo calcule sobre el
    # texto que de verdad se va a escribir.
    return normalizar_texto("" if valor is None else str(valor)).ljust(ancho)[:ancho]


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
