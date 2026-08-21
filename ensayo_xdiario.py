#!/usr/bin/env python3
"""ensayo_xdiario.py — el ULTIMO paso, que es el que entra en la contabilidad real.

POR QUE ESTE ENSAYO IMPORTA MAS QUE NINGUNO
--------------------------------------------
Todo lo demas del proyecto produce un veredicto: un texto que una persona lee y
decide que hacer. Un fallo ahi cuesta tiempo.

`escribir_xdiario()` produce otra cosa: el fichero que se IMPORTA en ContaPlus.
Un fallo ahi no cuesta tiempo, cuesta contabilidad — entra en los libros de un
cliente real, con su modelo 303 detras, y hay que ir a sacarlo a mano.

Y hasta hoy esa funcion no se habia ejecutado nunca en ninguna prueba.

LA INVARIANTE QUE SE COMPRUEBA, Y QUE NO ESTABA
------------------------------------------------
Una sola, y es la que sostiene toda la partida doble:

    En cada asiento, la suma del DEBE tiene que ser igual a la del HABER.

Un asiento descuadrado es a la contabilidad lo que un falso verde es al motor:
algo que pasa por bueno sin serlo. Y se comprobo que pasaba de verdad — no en
teoria: una factura de captura de camara (base, IVA y total, sin desglose por
tipos) generaba UN asiento de UNA linea, el haber del proveedor, con cero en el
debe. Desde el 21-08-2026 esa factura ya puede ser VERDE, asi que el caso paso de
imposible a ser el normal.

QUE SI PRUEBA Y QUE NO
----------------------
  SI: que el fichero se escribe con el ancho de linea correcto, que se puede
      volver a leer con el lector del propio proyecto, que los importes y las
      cuentas sobreviven al viaje, y que ningun asiento sale descuadrado.
  NO: que ContaPlus lo acepte. Eso solo lo dice ContaPlus, en el PC de la
      asesoria, importando de verdad. Este ensayo quita todo lo que se puede
      quitar antes de llegar ahi.

REGLA DE DATOS: todo inventado, directorio temporal, borrado al terminar.

Uso:  python3 ensayo_xdiario.py
"""
import os
import shutil
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from layout_diario_contaplus import (ANCHO_LINEA, escribir_xdiario,
                                     leer_ascii_completo)

NIF = "B12345674"          # ya declarado como sintetico en el escaner
resultados = []


def comprobar(nombre, condicion, obtenido="", esperado="", sev="P1"):
    resultados.append((nombre, condicion, sev))
    print(f"  [{'OK  ' if condicion else 'FALLA'}] {nombre}")
    if not condicion:
        print(f"           obtenido: {obtenido}")
        print(f"           esperado: {esperado}   [{sev}]")


def factura(**kw):
    base = {'nif': NIF, 'proveedor': 'PROVEEDOR PILOTO SL',
            'nº_documento': 'FAC-2026-001', 'fecha_expedicion': '2026-03-15',
            'cuenta_debe': '600000', 'cuenta_haber': '400001'}
    base.update(kw)
    return base


def escribir_y_leer(tmp, facturas, nombre="x.txt"):
    p = os.path.join(tmp, nombre)
    n_lineas, n_asientos = escribir_xdiario(facturas, p)
    regs = leer_ascii_completo(p) if n_lineas else []
    return p, n_lineas, n_asientos, regs


def por_asiento(regs):
    grupos = {}
    for r in regs:
        grupos.setdefault(r.get('ASIEN'), []).append(r)
    return grupos


def main():
    print("=" * 72)
    print("ENSAYO DEL xDiario — el fichero que entra en ContaPlus")
    print("=" * 72)
    tmp = tempfile.mkdtemp(prefix="ensayo_xdiario_")
    try:
        # --- 1. ida y vuelta con desglose --------------------------------
        print("\nIDA Y VUELTA (se escribe y se vuelve a leer):")
        f1 = factura(base_21='1000.00', base_total='1000.00',
                     iva_total='210.00', total_factura='1210.00')
        p, nl, na, regs = escribir_y_leer(tmp, [f1])
        comprobar("una factura con desglose genera su asiento", na == 1 and nl == 3,
                  f"{na} asientos, {nl} lineas", "1 asiento, 3 lineas", "P0")
        comprobar("cada linea mide exactamente lo que espera ContaPlus",
                  all(len(l) == ANCHO_LINEA for l in
                      open(p, 'rb').read().decode('latin1').split('\r\n') if l.strip()),
                  "alguna linea con otra longitud", f"{ANCHO_LINEA} bytes", "P0")
        comprobar("el lector del proyecto puede releer lo que el escritor escribio",
                  len(regs) == 3, f"{len(regs)} registros", "3", "P0")
        cuentas = [r['SUBCTA'].strip() for r in regs]
        comprobar("las cuentas sobreviven al viaje (gasto, IVA soportado, proveedor)",
                  cuentas == ['600000', '472021', '400001'], cuentas,
                  "['600000', '472021', '400001']", "P0")
        comprobar("el NIF del tercero sobrevive al viaje",
                  any(r.get('TERNIF', '').strip() == NIF for r in regs),
                  "no aparece", NIF, "P1")
        comprobar("la fecha sobrevive al viaje",
                  all(str(r['FECHA']) == '2026-03-15' for r in regs if r.get('FECHA')),
                  "otra fecha", "2026-03-15", "P1")

        # --- 2. LA INVARIANTE --------------------------------------------
        print("\nLA INVARIANTE DE LA PARTIDA DOBLE (debe = haber en cada asiento):")
        casos = {
            "con desglose al 21%": factura(base_21='1000.00', base_total='1000.00',
                                           iva_total='210.00', total_factura='1210.00'),
            "captura de camara, sin desglose": factura(
                nº_documento='F2', base_total='340.50', iva_total='71.51',
                total_factura='412.01'),
            "al 0% (alimentacion basica)": factura(
                nº_documento='F3', base_total='87.30', iva_total='0.00',
                total_factura='87.30'),
            "dos tipos (21% y 10%)": factura(
                nº_documento='F4', base_21='1000.00', base_10='500.00',
                base_total='1500.00', iva_total='260.00', total_factura='1760.00'),
            "profesional con retencion": factura(
                nº_documento='F5', base_21='2000.00', base_total='2000.00',
                iva_total='420.00', irpf_retencion='-300.00', total_factura='2120.00'),
            "fecha en formato espanol": factura(
                nº_documento='F6', fecha_expedicion='15/03/2026', base_21='100.00',
                base_total='100.00', iva_total='21.00', total_factura='121.00'),
        }
        for nombre, f in casos.items():
            _, nl, na, regs = escribir_y_leer(tmp, [f], f"caso.txt")
            if na != 1:
                comprobar(f"{nombre}: se exporta", False, f"{na} asientos", "1", "P0")
                continue
            for asien, lineas in por_asiento(regs).items():
                debe = round(sum(l.get('EURODEBE') or 0 for l in lineas), 2)
                haber = round(sum(l.get('EUROHABER') or 0 for l in lineas), 2)
                comprobar(f"{nombre}: debe = haber",
                          abs(debe - haber) < 0.01,
                          f"debe={debe} haber={haber}", "iguales", "P0")

        # --- 3. lo que NO se exporta, y no se inventa ---------------------
        print("\nLO QUE NO SE PUEDE EXPORTAR SE QUEDA FUERA (nunca se inventa):")
        malas = {
            "sin cuenta de proveedor": factura(base_21='100.00', base_total='100.00',
                                               iva_total='21.00', total_factura='121.00',
                                               cuenta_haber=None),
            "sin cuenta de gasto": factura(base_21='100.00', base_total='100.00',
                                           iva_total='21.00', total_factura='121.00',
                                           cuenta_debe=None),
            "con un tipo de IVA imposible de deducir": factura(
                base_total='200.00', iva_total='31.00', total_factura='231.00'),
            "con la fecha ilegible": factura(fecha_expedicion='30/02/2026',
                                             base_21='100.00', base_total='100.00',
                                             iva_total='21.00', total_factura='121.00'),
        }
        for nombre, f in malas.items():
            _, nl, na, _ = escribir_y_leer(tmp, [f], "mala.txt")
            comprobar(f"{nombre}: no genera asiento", na == 0 and nl == 0,
                      f"{na} asientos, {nl} lineas", "0 y 0", "P0")

        # --- 4. una tanda mezclada: las buenas salen, las malas no --------
        print("\nUNA TANDA MEZCLADA (una factura mala no se lleva por delante la tanda):")
        tanda = list(casos.values()) + list(malas.values())
        _, nl, na, regs = escribir_y_leer(tmp, tanda, "tanda.txt")
        comprobar("salen las 6 buenas y ninguna de las 4 malas", na == 6,
                  f"{na} asientos", "6", "P0")
        descuadrados = [a for a, ls in por_asiento(regs).items()
                        if abs(round(sum(l.get('EURODEBE') or 0 for l in ls), 2)
                               - round(sum(l.get('EUROHABER') or 0 for l in ls), 2)) > 0.01]
        comprobar("ningun asiento de la tanda sale descuadrado", not descuadrados,
                  f"descuadrados: {descuadrados}", "ninguno", "P0")

        # --- 4-bis. codificacion ------------------------------------------
        # ContaPlus corre en Windows y escribe cp1252, no latin-1. Se escribia y
        # leia en latin-1, asi que un nombre con "€" o con comillas curvas —lo
        # que produce Word, Excel y cualquier transcripcion por IA— reventaba con
        # UnicodeEncodeError y se llevaba la EXPORTACION ENTERA, no una factura.
        print("\nCODIFICACION (nombres reales de proveedor, no de laboratorio):")
        for _caso, _nombre in (("ene y acentos", "MU\u00d1OZ Y ASOCIADOS S.L."),
                               ("el simbolo del euro", "SUMINISTROS \u20ac GLOBAL"),
                               ("comillas tipograficas", "GESTORIA \u201cEL FARO\u201d"),
                               ("raya larga", "SERVICIOS \u2014 INTEGRALES"),
                               ("caracteres imposibles", "PROVEEDOR \u682a\u5f0f\u4f1a\u793e")):
            _f = factura(nº_documento='FC', proveedor=_nombre, base_21='100.00',
                         base_total='100.00', iva_total='21.00', total_factura='121.00')
            try:
                _p, _nl, _na, _regs = escribir_y_leer(tmp, [_f], "cod.txt")
                _ok = _na == 1
            except Exception as e:
                _ok, _na = False, type(e).__name__
            comprobar(f"un proveedor con {_caso} se exporta", _ok, str(_na), "1 asiento", "P0")
            if _ok:
                _crudo = open(_p, 'rb').read().decode('cp1252', errors='replace')
                _anchos = {len(l) for l in _crudo.split('\r\n') if l.strip()}
                comprobar(f"   ...y la linea sigue midiendo {ANCHO_LINEA}",
                          _anchos == {ANCHO_LINEA}, str(_anchos), f"{{{ANCHO_LINEA}}}", "P0")

        # --- 5. la doble comprobacion, y el control positivo -------------
        print("\nEL ULTIMO PASO NO SE FIA DEL MOTOR, COMPRUEBA POR SU CUENTA:")
        rota = factura(nº_documento='F9', base_21='1000.00', base_total='1000.00',
                       iva_total='210.00', total_factura='9999.00')
        _, nl, na, _ = escribir_y_leer(tmp, [rota], "rota.txt")
        comprobar("una factura cuyo total no cuadra NO se exporta", na == 0,
                  f"{na} asientos", "0", "P0")
        print("           (el motor no la habria dado por VERDE. Pero el fichero que")
        print("            entra en la contabilidad no puede fiarse de eso.)")

        print("\nCONTROL POSITIVO (.sabria este ensayo ver un descuadre si se colara?):")
        # Se quita la invariante del escritor a proposito y se comprueba que la
        # comprobacion de este ensayo lo detecta. Sin esto, los 'debe = haber' de
        # arriba podrian estar en verde por no mirar, que es el fallo que este
        # proyecto persigue en todas partes.
        import layout_diario_contaplus as ldc
        fuente_original = ldc.escribir_xdiario

        def sin_invariante(facturas, path, asien_inicial=1):
            lineas, asien = [], asien_inicial
            for f in facturas:
                ap = ldc.generar_asiento_desde_factura(
                    f, asien, f.get('cuenta_debe'), f.get('cuenta_haber'))
                lineas += [ldc.construir_linea(a) for a in ap]
                asien += 1
            with open(path, 'wb') as fh:
                for l in lineas:
                    fh.write((l + "\r\n").encode("latin1"))
            return len(lineas), asien - asien_inicial

        ldc.escribir_xdiario = sin_invariante
        try:
            p2 = os.path.join(tmp, "descuadrada.txt")
            sin_invariante([rota], p2)
            regs2 = leer_ascii_completo(p2)
            visto = [a for a, ls in por_asiento(regs2).items()
                     if abs(round(sum(l.get('EURODEBE') or 0 for l in ls), 2)
                            - round(sum(l.get('EUROHABER') or 0 for l in ls), 2)) > 0.01]
            comprobar("sin la invariante, el ensayo SI ve el asiento descuadrado",
                      len(visto) == 1, f"{len(visto)} detectados", "1", "P0")
        finally:
            ldc.escribir_xdiario = fuente_original
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    fallos = [r for r in resultados if not r[1]]
    p0 = [r for r in fallos if r[2] == "P0"]
    print()
    print("=" * 72)
    print(f"Pruebas: {len(resultados)}   en verde: {len(resultados)-len(fallos)}   "
          f"FALLAN: {len(fallos)}  (de ellas P0: {len(p0)})")
    if fallos:
        print("\nEL ULTIMO PASO TIENE DEFECTOS (esto entra en la contabilidad real):")
        for nombre, _, sev in fallos:
            print(f"  [{sev}] {nombre}")
        return 1
    print("\nEl fichero que entra en ContaPlus se escribe, se relee, y ningun")
    print("asiento sale descuadrado. Lo que no se puede cuadrar, no se exporta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
