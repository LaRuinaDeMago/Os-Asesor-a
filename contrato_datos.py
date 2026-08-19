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
                     'iva_total', 'irpf_retencion', 'total_factura')

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

    s = s.replace('€', '').replace('EUR', '').replace(' ', '')
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
                  'verificacion', 'motivo_semaforo'):
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
