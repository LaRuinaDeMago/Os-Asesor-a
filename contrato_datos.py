#!/usr/bin/env python3
"""contrato_datos.py — la frontera entre la IA y el motor.

POR QUE EXISTE ESTE MODULO
--------------------------
El 19-08-2026, atacando el motor con `test_adversarial.py`, se confirmo que una
factura con TODOS los importes ausentes daba VERDE. La causa era una sola, y
estaba en una linea:

    _f(x, default=0.0)   ->   "" y None y "abc" acaban valiendo 0.0

Y 0 es un dato fiscal PERFECTAMENTE VALIDO. Asi que "no se que habia" y "habia
cero" eran indistinguibles para todos los guards aritmeticos. Con todo a cero,
0 + 0 + 0 = 0 cuadra, los tres guards aritmeticos dan OK, y sale VERDE.

Eso desmentia la invariante fundacional escrita en el propio motor:

    "si no hay dato para evaluar un guard, el estado es NO_COMPROBADO,
     nunca OK por omision."

QUE HACE ESTE MODULO
--------------------
Convierte un dict crudo (venga de Gemini, de un CSV o de la mano de alguien) en
una FACTURA CANONICA donde cada campo lleva, ademas de su valor, el ESTADO de
ese valor. El motor nunca vuelve a recibir un `dict` cualquiera.

    VALUE    hay un numero/fecha/texto util          125.40
    ZERO     hay un cero DECLARADO, que es un dato    0
    MISSING  no venia el campo, o venia vacio         "" / None / falta la clave
    INVALID  venia algo que no se puede interpretar   "abc" / "2026-02-30"

    MISSING != ZERO       INVALID != ZERO

Regla dura: un campo MISSING o INVALID **jamas** se entrega a un guard fiscal
como si fuera 0. El motor lo declara NO_COMPROBADO y el veredicto no puede ser
VERDE.

QUE NO HACE
-----------
No decide nada contable. No corrige datos. No adivina. Solo clasifica y
normaliza, y deja constancia de lo que no ha podido interpretar.

PRIVACIDAD
----------
Este modulo maneja valores reales en memoria, pero NUNCA los emite: los informes
de incidencia citan el NOMBRE DEL CAMPO y su estado, jamas su contenido. Es la
misma regla que ya siguen scripts/privacy_scan.py y los scripts de la Fase 0.
"""
import re
from datetime import date, datetime

# --- Estados posibles de un dato ------------------------------------------
VALUE = "VALUE"
ZERO = "ZERO"
MISSING = "MISSING"
INVALID = "INVALID"

#: Estados con los que un guard fiscal SI puede operar.
UTILIZABLES = (VALUE, ZERO)

#: Campos monetarios que el motor necesita para poder afirmar algo.
CAMPOS_MONETARIOS = ('base_10', 'base_4', 'base_21', 'base_total',
                     'iva_total', 'irpf_retencion', 'total_factura',
                     # anadido 20-08-2026, ver RECARGO_POR_TIPO mas abajo
                     'recargo_equivalencia',
                     # segunda lectura del total, desde otra ubicacion del papel
                     'total_factura_2')

# ---------------------------------------------------------------------------
# NATURALEZA DE LA OPERACION (anadido 20-08-2026)
#
# EL TECHO QUE CIERRA: el modelo de datos solo sabia representar 4/10/21. Medido
# el 20-08-2026 contra el motor real, SEIS categorias de facturas perfectamente
# LEGALES no podian llegar nunca a VERDE — se quedaban en AMBAR para siempre:
# exentas (art.20 LIVA), intracomunitarias, inversion del sujeto pasivo, tipo 0%
# (pan, leche, fruta desde 2023), no sujetas, y cualquier tipo distinto de
# 4/10/21 (el 5% de la electricidad existio en Espana).
#
# No era un falso verde —es seguro— pero condenaba esas facturas a revision
# manual permanente, o sea que ponia un techo a CUANTO se puede automatizar.
#
# En todas las de IVA cero el cero es CORRECTO, no un error. Y esa es justo la
# distincion que el motor no podia hacer: un iva_total=0 podia ser "exenta, y
# esta bien" o "se les olvido el IVA", y sin la naturaleza declarada no hay
# forma de saberlo. Por eso la naturaleza se DECLARA en la captura, no se
# adivina en el guard — mismo criterio que tipo_documento.
SUJETA = "SUJETA"                                  # el caso normal, con IVA
EXENTA = "EXENTA"                                  # art. 20 LIVA (medico, educacion, seguro...)
NO_SUJETA = "NO_SUJETA"                            # fuera del ambito del impuesto
INTRACOMUNITARIA = "INTRACOMUNITARIA"              # el IVA lo autorrepercute el destinatario
INVERSION_SUJETO_PASIVO = "INVERSION_SUJETO_PASIVO"  # art. 84.Uno.2 LIVA

#: Naturalezas en las que un IVA de 0 es lo CORRECTO, no un descuadre.
SIN_IVA_REPERCUTIDO = (EXENTA, NO_SUJETA, INTRACOMUNITARIA, INVERSION_SUJETO_PASIVO)

NATURALEZAS = (SUJETA,) + SIN_IVA_REPERCUTIDO

#: Tipos de IVA espanoles vigentes o historicos. El 0% existe desde 2023 (pan,
#: leche, fruta) y el 5% se aplico a la electricidad: no son casos raros.
TIPOS_IVA_CONOCIDOS = (0, 4, 5, 10, 21)

#: RECARGO DE EQUIVALENCIA (art. 154 LIVA). Regimen OBLIGATORIO para el comercio
#: minorista persona fisica, o sea muy comun en una cartera con 19 autonomos.
#: El proveedor repercute IVA *y ademas* el recargo, asi que:
#:      total = base + IVA + RECARGO
#: Sin contemplarlo, base+IVA nunca cuadra con el total y la factura sale ROJO
#: siendo perfectamente correcta. ContaPlus ya lo tiene en cuenta: el diario
#: lleva un campo RECEQUIV al lado del de IVA.
RECARGO_POR_TIPO = {21: 5.2, 10: 1.4, 5: 0.62, 4: 0.5}

#: Campos sin los cuales NINGUN veredicto positivo es defendible.
CAMPOS_CRITICOS = ('nif', 'fecha_expedicion', 'nº_documento',
                   'base_total', 'iva_total', 'total_factura')

FORMATOS_FECHA = ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d')


class Dato:
    """Un valor y el estado de ese valor. Nunca se imprime el valor."""

    __slots__ = ('valor', 'estado')

    def __init__(self, valor, estado):
        self.valor = valor
        self.estado = estado

    @property
    def utilizable(self):
        return self.estado in UTILIZABLES

    def __repr__(self):
        # A PROPOSITO no incluye el valor: este repr puede acabar en un log.
        return f"<Dato {self.estado}>"


def parse_numero(x):
    """Texto/numero -> Dato. Distingue el cero real de la ausencia.

    Acepta el formato espanol ('1.234,56') y el anglosajon ('1,234.56'):
    cuando aparecen los dos separadores, manda el ULTIMO como decimal.
    """
    if x is None:
        return Dato(None, MISSING)
    if isinstance(x, bool):                      # True/False no son importes
        return Dato(None, INVALID)
    if isinstance(x, (int, float)):
        return _dato_numerico(float(x))

    s = str(x).strip()
    if s == '':
        return Dato(None, MISSING)

    # Se quitan tambien el espacio duro (\u00a0) y el fino (\u2009): la
    # extraccion de texto de un PDF mete uno u otro donde el documento
    # mostraba un separador de millar, y sin quitarlos "12 345,67" acababa
    # en INVALID por un espacio que el ojo humano ni distingue del normal.
    s = s.replace('\u20ac', '').replace('EUR', '')
    for _espacio in ('\u0020', '\u00a0', '\u2009'):
        s = s.replace(_espacio, '')
    ultimo_punto, ultima_coma = s.rfind('.'), s.rfind(',')
    if ultimo_punto != -1 and ultima_coma != -1:
        if ultima_coma > ultimo_punto:           # 1.234,56 -> espanol
            s = s.replace('.', '').replace(',', '.')
        else:                                    # 1,234.56 -> anglosajon
            s = s.replace(',', '')
    elif ultima_coma != -1 or ultimo_punto != -1:
        # UN SOLO separador: es ambiguo, y equivocarse aqui es un error de 1000x.
        # '1.200' en un importe espanol son MIL DOSCIENTOS, no uno coma dos.
        # Regla: si tras el separador hay EXACTAMENTE 3 digitos, es separador de
        # millares; si hay 1 o 2, es decimal. Los importes de factura llevan dos
        # decimales, asi que '125.40' es decimal y '1.200' son millares.
        # Supuesto declarado, no adivinado en silencio.
        pos = max(ultimo_punto, ultima_coma)
        decimales = len(s) - pos - 1
        if decimales == 3:
            s = s[:pos] + s[pos + 1:]            # millares: se quita
        else:
            s = s[:pos] + '.' + s[pos + 1:]      # decimal: se normaliza a punto

    try:
        v = float(s)
    except (TypeError, ValueError):
        return Dato(None, INVALID)
    return _dato_numerico(v)


def _dato_numerico(v):
    """Clasifica un float ya obtenido. NaN e infinito NO son importes."""
    if v != v or v in (float('inf'), float('-inf')):
        return Dato(None, INVALID)
    return Dato(v, ZERO if v == 0 else VALUE)


#: Separadores de millar que puede traer un importe extraido de un PDF: punto,
#: espacio normal, espacio duro (\u00a0) y espacio fino (\u2009). Escritos como
#: escapes a proposito: un caracter de espacio invisible dentro del fuente es
#: imposible de revisar en un diff.
_SEP_MILLAR = '[.\u0020\u00a0\u2009]'

#: Patron para ENCONTRAR importes dentro de un texto libre (una pagina de PDF,
#: un OCR, un correo). Es un trabajo distinto del de parse_numero(), que
#: convierte un texto que YA se sabe que es un numero; aqui hay que localizarlos
#: primero, entre palabras.
#:
#: BUG REAL cazado el 26-08-2026, y la razon de que esto viva AQUI y no en cada
#: script: habia TRES copias del patron (extraer_303_pdf.py, reconocer_303_pdf.py
#: y el cruce nuevo), las tres escritas como
#:
#:      r'-?\d{1,3}(?:\.\d{3})*,\d{2}'
#:
#: que EXIGE el punto de millar. Con "12345,67" ese patron no falla: encuentra
#: "345,67". Devuelve un numero distinto, en silencio, sin error. Medido sobre
#: el archivo real del despacho: el 47% de los importes vienen SIN separador de
#: millar, asi que casi la mitad se leian mal.
#:
#: El patron arreglado en un solo sitio y copiado a mano en los otros dos es
#: exactamente como nacen los bugs de esta familia — el mismo patron que el
#: proyecto ya documento dos veces (float() a pelo tras el motor, BASEIMPO sin
#: alternativa). Por eso hay una sola definicion y los tres la importan.
RE_IMPORTE_EN_TEXTO = re.compile(
    r'-?(?:\d{1,3}(?:' + _SEP_MILLAR + r'\d{3})+|\d+),\d{2}')


def importes_en_texto(texto):
    """Todos los importes con dos decimales que aparecen en un texto libre.

    Localiza con RE_IMPORTE_EN_TEXTO y convierte con parse_numero(), que es la
    unica regla de conversion del proyecto: asi no hay dos formas distintas de
    interpretar "1.234,56" segun quien lo lea.

    Devuelve una lista de floats. Lo que no se pueda convertir se descarta en
    silencio A PROPOSITO: en un texto libre hay cadenas con forma de numero que
    no lo son, y aqui eso no es un dato perdido, es ruido descartado.
    """
    valores = []
    for trozo in RE_IMPORTE_EN_TEXTO.findall(texto):
        dato = parse_numero(trozo)
        if dato.estado in UTILIZABLES:
            valores.append(dato.valor)
    return valores


def parse_fecha(x):
    """Texto -> Dato con un datetime.date real.

    Rechaza lo que NO es una fecha de calendario. Antes bastaba con que los
    cuatro primeros caracteres fueran un ano, asi que '2026-99-99' pasaba.
    """
    if x is None:
        return Dato(None, MISSING)
    if isinstance(x, date):
        return Dato(x, VALUE)
    s = str(x).strip()
    if s == '':
        return Dato(None, MISSING)
    for fmt in FORMATOS_FECHA:
        try:
            return Dato(datetime.strptime(s, fmt).date(), VALUE)
        except ValueError:
            continue
    return Dato(None, INVALID)


def parse_texto(x):
    """Texto -> Dato. Un texto vacio es MISSING, no cadena vacia utilizable."""
    if x is None:
        return Dato(None, MISSING)
    s = str(x).strip()
    return Dato(s, VALUE) if s else Dato(None, MISSING)


class FacturaCanonica:
    """Lo unico que el motor deberia aceptar.

    Expone los valores ya normalizados y, por separado, el estado de cada campo.
    `incidencias()` devuelve solo NOMBRES de campo y estados, nunca contenido.
    """

    def __init__(self, cruda):
        self.cruda = cruda if isinstance(cruda, dict) else {}
        self.campos = {}

        for c in CAMPOS_MONETARIOS:
            self.campos[c] = parse_numero(self.cruda.get(c))
        self.campos['fecha_expedicion'] = parse_fecha(self.cruda.get('fecha_expedicion'))
        self.campos['fecha_vencimiento'] = parse_fecha(self.cruda.get('fecha_vencimiento'))
        for c in ('nif', 'proveedor', 'nº_documento', 'tipo_documento',
                  'verificacion', 'motivo_semaforo',
                  # datos del margen, para la triangulacion de identidad
                  'nif_margen', 'nombre_margen'):
            self.campos[c] = parse_texto(self.cruda.get(c))

    # -- acceso comodo ------------------------------------------------------
    def estado(self, campo):
        d = self.campos.get(campo)
        return d.estado if d else MISSING

    def num(self, campo):
        """Valor numerico SOLO si es utilizable. None si MISSING/INVALID.

        Devolver None a proposito: si un guard intenta operar con esto y
        revienta, es un fallo visible, no un cero silencioso.
        """
        d = self.campos.get(campo)
        return d.valor if (d and d.utilizable) else None

    def texto(self, campo, por_defecto=''):
        d = self.campos.get(campo)
        return d.valor if (d and d.utilizable) else por_defecto

    def fecha(self, campo):
        d = self.campos.get(campo)
        return d.valor if (d and d.estado == VALUE) else None

    # -- naturaleza y tramos de IVA (20-08-2026) ---------------------------
    def naturaleza(self):
        """SUJETA / EXENTA / NO_SUJETA / INTRACOMUNITARIA / INVERSION_SUJETO_PASIVO.

        Si no viene declarada se asume SUJETA, que es el caso normal. Si viene
        pero no se reconoce, se devuelve tal cual para que el guard la rechace:
        una naturaleza inventada NO puede pasar por la de por defecto.
        """
        v = (self.cruda.get('naturaleza_operacion') or '').strip().upper()
        return v if v else SUJETA

    def tramos(self):
        """Lista [{'tipo': n, 'base': x, 'cuota': y}], de cualquier tipo de IVA.

        Acepta las dos formas y por eso no rompe nada de lo anterior:
          - NUEVA: 'tramos_iva': [{'tipo':21,'base':100,'cuota':21}, ...]
          - LEGADA: los campos planos base_10 / base_4 / base_21

        Devuelve [] si no hay ninguno declarado — que no es lo mismo que un
        tramo a cero, y el motor los distingue.
        """
        crudos = self.cruda.get('tramos_iva')
        salida = []
        if isinstance(crudos, (list, tuple)):
            for t in crudos:
                if not isinstance(t, dict):
                    continue
                tipo = parse_numero(t.get('tipo'))
                base = parse_numero(t.get('base'))
                if not (tipo.utilizable and base.utilizable):
                    continue
                cuota = parse_numero(t.get('cuota'))
                salida.append({
                    'tipo': tipo.valor,
                    'base': base.valor,
                    # Si no declaran cuota se deriva del tipo. No es inventar:
                    # es la definicion del impuesto.
                    'cuota': cuota.valor if cuota.utilizable
                             else round(base.valor * tipo.valor / 100.0, 2),
                })
            if salida:
                return salida

        for tipo, campo in ((10, 'base_10'), (4, 'base_4'), (21, 'base_21')):
            d = self.campos.get(campo)
            if d and d.estado == VALUE and d.valor:      # ZERO no es un tramo
                salida.append({'tipo': float(tipo), 'base': d.valor,
                               'cuota': round(d.valor * tipo / 100.0, 2)})
        return salida

    def declara_desglose(self):
        """.La factura DICE algo sobre su desglose por tipos, aunque sea un cero?

        ANADIDO 21-08-2026 (barrido_falsos_verdes.py). No es lo mismo que
        `tramos()`, y la diferencia es justo donde se colaba un falso verde:

            base_21 AUSENTE            -> no dice nada. Es la captura de camara.
            base_21 = 0 con base 1000  -> SI dice algo, y se contradice.

        `tramos()` devuelve [] en los dos casos, porque un cero no es un tramo.
        Correcto para sumar, y peligroso para decidir: hace que una base_21
        corrompida a cero sea indistinguible de una factura sin desglose, y por
        esa puerta el motor absolvia la contradiccion con la comprobacion global.

        Es el MISSING-vs-ZERO de siempre, que este proyecto ya arreglo dos veces
        (en el motor y en el retro-semaforo) y se habia vuelto a colar aqui.
        """
        if isinstance(self.cruda.get('tramos_iva'), (list, tuple)) and self.cruda['tramos_iva']:
            return True
        for campo in ('base_10', 'base_4', 'base_21'):
            d = self.campos.get(campo)
            # VALUE / ZERO / INVALID = hay algo escrito en ese hueco. MISSING no:
            # una columna vacia de un CSV no es una afirmacion.
            if d and d.estado != MISSING:
                return True
        return False

    # -- integridad ---------------------------------------------------------
    def incidencias(self, campos=CAMPOS_CRITICOS):
        """[(campo, estado)] de los criticos que no son utilizables.

        Solo nombres de campo y estados. Nunca el contenido.
        """
        return [(c, self.estado(c)) for c in campos
                if self.estado(c) not in UTILIZABLES]

    def integra(self, campos=CAMPOS_CRITICOS):
        return not self.incidencias(campos)

    def clave_documental(self):
        """Clave normalizada para el anti-duplicado.

        Antes se construia con acceso directo (`fila['nif']`) y `.strip()`, de
        modo que una clave ausente daba KeyError y un numero JSON daba
        AttributeError: el motor ni siquiera llegaba a emitir veredicto. Ademas,
        '1.200' y '1200.00' generaban claves distintas para la misma factura.
        """
        total = self.num('total_factura')
        f = self.fecha('fecha_expedicion')
        return (
            self.texto('nif').upper(),
            normalizar_num_documento(self.texto('nº_documento')),
            f.isoformat() if f else '',
            f"{total:.2f}" if total is not None else '',
        )


def normalizar_num_documento(s):
    """'FAC-001', 'FAC 001' y 'fac/001' son el mismo documento.

    Se normaliza en la direccion PRUDENTE a proposito. En el anti-duplicado los
    dos errores no cuestan lo mismo:
      - no detectar un duplicado  -> el mismo asiento entra dos veces (error real)
      - detectar uno de mas       -> un humano lo mira y lo descarta (molestia)
    Asi que conviene agrupar de mas, no de menos. Aun asi no se quita TODA la
    puntuacion: 'Factura 001' y 'FAC-001' siguen siendo distintos, porque
    normalizar hasta ahi empezaria a juntar documentos que no tienen por que
    serlo, y un ROJO falso repetido acaba con la confianza en el guard.
    """
    for ch in (' ', '-', '/', '.', '_'):
        s = s.replace(ch, '')
    return s.upper()


def canonizar(fila):
    """Punto de entrada unico: dict crudo -> FacturaCanonica."""
    return fila if isinstance(fila, FacturaCanonica) else FacturaCanonica(fila)
