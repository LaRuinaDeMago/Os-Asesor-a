#!/usr/bin/env python3
"""prueba_digito_ocr.py — ¿caza el motor el 5 confundido con un 8?

LA PREGUNTA, PLANTEADA POR EL TITULAR EL 20-08-2026
---------------------------------------------------
    "el tipico ejemplo de confundir un 5 con un 8, pero para el sistema eso
     esta bien y lo va a dar por bueno porque para el esta bien, aunque en
     realidad se esta equivocando"

Es la preocupacion correcta y es la que decide el proyecto. Pero es medible, y
medirla es mejor que opinar sobre ella.

EL METODO
---------
Se coge una factura CORRECTA y se le cambia UN SOLO DIGITO, en un solo campo,
por cada uno de los otros nueve digitos posibles. Cada mutacion es una factura
que YA NO es correcta. Se cuenta cuantas caza el motor.

Es exhaustivo: no es una muestra, son TODAS las mutaciones de un digito.

POR QUE LA REDUNDANCIA ARITMETICA DE UNA FACTURA ES TAN FUERTE
---------------------------------------------------------------
Una factura no lleva tres numeros sueltos: lleva tres numeros con DOS
restricciones que tienen que cumplirse a la vez.

    base x tipo = cuota          base + cuota = total

Cambiar un digito en cualquiera de los tres rompe las dos ecuaciones casi
siempre. Es, sin haberlo buscado, un codigo detector de errores.

Uso:  python3 prueba_digito_ocr.py
"""
import sys
from collections import defaultdict

import motor_veredicto as mv

NIF = "B12345674"          # CIF inventado con checksum valido
MAESTRO = {NIF: {'titulo': 'PROVEEDOR PILOTO SL', 'cuenta': '400001'}}

FACTURA = {
    'nif': NIF,
    'proveedor': 'PROVEEDOR PILOTO SL',
    'nº_documento': 'FAC-2026-0158',
    'fecha_expedicion': '2026-03-15',
    'verificacion': 'OK',
    'base_21': '458.00',
    'base_total': '458.00',
    'iva_total': '96.18',
    'total_factura': '554.18',
}

CAMPOS = ('base_21', 'base_total', 'iva_total', 'total_factura',
          'nif', 'fecha_expedicion', 'nº_documento')

#: Campos monetarios: aqui es donde un 5 por un 8 cambia el asiento.
MONETARIOS = ('base_21', 'base_total', 'iva_total', 'total_factura')


def evaluar(fila):
    try:
        v, _, _ = mv.evaluar_fila_v4(fila, set(), {}, {}, {}, MAESTRO,
                                     alta_cliente_anio=2020,
                                     nif_cliente_titular="B99999999",
                                     ejercicio_tanda=2026)
        return v
    except Exception as e:
        return "EXCEPCION:" + type(e).__name__


def posicion_decimal(texto, i):
    """¿El digito de la posicion i son CENTIMOS? Distinguirlo importa: un error
    en los centimos es de redondeo; uno en los euros cambia el asiento."""
    punto = texto.rfind('.')
    return punto != -1 and i > punto


def main():
    if evaluar(dict(FACTURA)) != "VERDE":
        print("La factura de partida no da VERDE. La prueba no vale; revisar.")
        return 1

    res = defaultdict(lambda: {'n': 0, 'cazados': 0, 'colados': []})
    euros = {'n': 0, 'cazados': 0, 'colados': []}
    centimos = {'n': 0, 'cazados': 0, 'colados': []}

    for campo in CAMPOS:
        original = FACTURA[campo]
        for i, ch in enumerate(original):
            if not ch.isdigit():
                continue
            for nuevo in '0123456789':
                if nuevo == ch:
                    continue
                fila = dict(FACTURA)
                fila[campo] = original[:i] + nuevo + original[i + 1:]
                cazado = evaluar(fila) != "VERDE"

                r = res[campo]
                r['n'] += 1
                r['cazados'] += cazado
                if not cazado:
                    r['colados'].append(f"{original} -> {fila[campo]}")

                if campo in MONETARIOS:
                    cubo = centimos if posicion_decimal(original, i) else euros
                    cubo['n'] += 1
                    cubo['cazados'] += cazado
                    if not cazado:
                        cubo['colados'].append(f"{campo}: {original} -> {fila[campo]}")

    def pct(c, n):
        return round(c * 100.0 / n, 1) if n else 0.0

    print("=" * 66)
    print("ERROR DE UN SOLO DIGITO — todas las mutaciones posibles")
    print("=" * 66)
    print(f"  {'campo':<18}{'mutaciones':>11}{'cazadas':>9}{'tasa':>8}")
    tn = tc = 0
    for campo in CAMPOS:
        r = res[campo]
        tn += r['n']
        tc += r['cazados']
        print(f"  {campo:<18}{r['n']:>11}{r['cazados']:>9}{pct(r['cazados'], r['n']):>7}%")
    print(f"  {'TOTAL':<18}{tn:>11}{tc:>9}{pct(tc, tn):>7}%")

    print("\n" + "=" * 66)
    print("LO QUE DE VERDAD IMPORTA: los digitos de EUROS de un importe")
    print("=" * 66)
    print(f"  euros    : {euros['cazados']}/{euros['n']}  -> {pct(euros['cazados'], euros['n'])}% cazados")
    print(f"  centimos : {centimos['cazados']}/{centimos['n']}  -> {pct(centimos['cazados'], centimos['n'])}% cazados")
    if euros['colados']:
        print(f"\n  ⚠ SE COLARON EN LOS EUROS: {euros['colados']}")
    else:
        print("\n  >> NINGUN error de un digito en los EUROS se cuela. Ni uno.")
        print("     El 5 confundido con un 8 en un importe: SIEMPRE detectado.")
    if centimos['colados']:
        print(f"\n  Los que se cuelan son de CENTIMOS, dentro de la tolerancia de")
        print(f"  redondeo del motor (TOL={mv.TOL}): {len(centimos['colados'])} casos.")
        print("  Un error de 1-2 centimos no cambia un asiento ni un modelo fiscal.")

    print("\n" + "=" * 66)
    print("DONDE SI HAY UN AGUJERO REAL")
    print("=" * 66)
    for campo in CAMPOS:
        r = res[campo]
        if r['colados'] and campo not in MONETARIOS:
            print(f"  {campo}: {len(r['colados'])} de {r['n']} se cuelan "
                  f"({pct(r['n'] - r['cazados'], r['n'])}%)")
    print("""
  El numero de documento no tiene NADA que lo compruebe desde la propia
  factura: no participa en ninguna ecuacion. Su unica defensa posible es el
  HISTORICO del proveedor (guard_secuencia_documental_proveedor), que hoy
  llega vacio. Es exactamente lo que arregla conectar el historico al motor.

  La fecha se cuela cuando el cambio cae dentro del mismo ejercicio y sigue
  siendo una fecha valida. Impacto bajo: el asiento va al mismo trimestre en
  la mayoria de los casos, y al mismo ejercicio siempre.""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
