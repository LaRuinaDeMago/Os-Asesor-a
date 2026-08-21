#!/usr/bin/env python3
"""barrido_falsos_verdes.py — atacar TODOS los VERDE, en TODAS las formas mecanicas.

POR QUE ESTO NO ES MAS DE LO MISMO
-----------------------------------
`test_adversarial.py` son 87 ataques ESCRITOS A MANO. Cada uno vale, y varios
cazaron defectos reales. Pero tienen un techo estructural que conviene decir en
voz alta: **solo cubren los ataques que se me ocurrieron.** Un falso verde que
nadie imagino no aparece ahi por definicion.

Esto es lo contrario: no elige los ataques, los enumera. Coge una factura que da
VERDE y le aplica TODAS las mutaciones mecanicas de UN SOLO CAMPO que se pueden
generar —borrarlo, vaciarlo, moverle la coma, cambiarle un digito, negarlo,
escalarlo, cambiar cada caracter del NIF, mover la fecha— y cuenta cuantas
sobreviven como VERDE.

LA REGLA QUE LO HACE VALIDO: UN CAMPO CADA VEZ
-----------------------------------------------
Una factura espanola lleva redundancia: base x tipo = cuota, base + cuota =
total. Tocar UN campo rompe esa redundancia por fuerza, asi que el motor DEBE
enterarse. Tocar tres a la vez de forma coherente produce otra factura valida y
mas pequena — eso no es un falso verde, es un limite fisico ya declarado
(FAMILIA Q), y por eso no se prueba aqui.

    Cada VERDE que sobrevive a una mutacion de un solo campo es un
    FALSO VERDE o una excepcion que hay que poder EXPLICAR.

No hay tercera opcion. Una mutacion que sobrevive sin explicacion es un defecto,
por raro que parezca el caso: los errores de captura no eligen ser tipicos.

QUE HACE CON LO QUE ENCUENTRA
-----------------------------
Lo clasifica en tres cubos, y solo el tercero es un problema:

  EQUIVALENTE   la mutacion produce una factura que sigue siendo correcta
                (redondeos por debajo de la tolerancia contable, un campo
                opcional que se vacia). No es un escape.
  DECLARADO     escapa, y esta escrito por que, con su razon. Se revisa que la
                razon siga siendo cierta; si deja de serlo, salta.
  ESCAPE        escapa y nadie lo ha explicado. Esto es el hallazgo.

Uso:  python3 barrido_falsos_verdes.py [--verboso]
"""
import itertools
import sys

import motor_veredicto as mv

TOL = 0.02

# --- Semillas: facturas que HOY dan VERDE, de tipos distintos ----------------
# NIF inventados con digito de control valido (se comprueba al arrancar).
# Los dos vienen de NIF_SINTETICOS_CONOCIDOS de scripts/privacy_scan.py, y eso
# es deliberado: inventar uno nuevo obligaba a AMPLIAR esa lista blanca, y la
# lista blanca de la barrera de privacidad no se toca por comodidad de un test.
# Reutilizar los que ya estan declarados como sinteticos no cuesta nada.
#
# (El escaner cazo el DNI nuevo que puse al escribir esto. Funciona.)
NIF_A = "B12345674"
NIF_B = "12345678Z"
MAESTRO = {NIF_A: {"titulo": "PROVEEDOR PILOTO SL", "cuenta": "400001"},
           NIF_B: {"titulo": "PROFESIONAL PILOTO", "cuenta": "410007"}}

SEMILLAS = {
    "21% con desglose": {
        'nif': NIF_A, 'proveedor': 'PROVEEDOR PILOTO SL',
        'nº_documento': 'FAC-2026-0117', 'fecha_expedicion': '2026-03-15',
        'base_21': '1000.00', 'base_total': '1000.00', 'iva_total': '210.00',
        'total_factura': '1210.00', 'verificacion': 'OK',
    },
    "21% sin desglose (captura de camara)": {
        'nif': NIF_A, 'proveedor': 'PROVEEDOR PILOTO SL',
        'nº_documento': 'FAC-2026-0118', 'fecha_expedicion': '2026-03-15',
        'base_total': '340.50', 'iva_total': '71.51', 'total_factura': '412.01',
        'verificacion': 'OK',
    },
    "0% (alimentacion basica)": {
        'nif': NIF_A, 'proveedor': 'PROVEEDOR PILOTO SL',
        'nº_documento': 'FAC-2026-0119', 'fecha_expedicion': '2026-03-15',
        'base_total': '87.30', 'iva_total': '0.00', 'total_factura': '87.30',
        'verificacion': 'OK',
    },
    "dos tipos (21% y 10%) con desglose": {
        'nif': NIF_A, 'proveedor': 'PROVEEDOR PILOTO SL',
        'nº_documento': 'FAC-2026-0120', 'fecha_expedicion': '2026-03-15',
        'base_21': '1000.00', 'base_10': '500.00', 'base_total': '1500.00',
        'iva_total': '260.00', 'total_factura': '1760.00', 'verificacion': 'OK',
    },
    "profesional con retencion 15%": {
        'nif': NIF_B, 'proveedor': 'PROFESIONAL PILOTO',
        'nº_documento': 'A-2026-44', 'fecha_expedicion': '2026-02-01',
        'base_21': '2000.00', 'base_total': '2000.00', 'iva_total': '420.00',
        'irpf_retencion': '-300.00', 'total_factura': '2120.00',
        'verificacion': 'OK',
    },
}

# --- Escapes DECLARADOS, con su razon ---------------------------------------
# La clave es (campo, familia_de_mutacion). Si uno deja de escapar, tambien
# salta: una declaracion que se queda obsoleta es basura que engana al que lee.
#: Se declara por CAMPO, no por (campo, mutacion): que un campo no tenga con que
#: contrastarse no depende de como se le estropee. Declarar mutacion a mutacion
#: obligaria a ampliar la lista cada vez que se anade una forma de romper, y
#: acabaria tapando escapes nuevos por inercia.
ESCAPES_DECLARADOS = {
    "nº_documento":
        "NO tiene redundancia interna contra la que contrastarlo: ningun otro "
        "campo de la factura permite deducir si el numero esta bien. Solo el "
        "historico del proveedor puede juzgarlo (guard_secuencia_documental_"
        "proveedor y guard_estructura_reconocida), y una semilla suelta no lo "
        "tiene. Ya medido: 0% de deteccion sin historico (prueba_digito_ocr.py). "
        "CONSECUENCIA PRACTICA: hasta que las caches de secuencia y formato esten "
        "pobladas, un numero de factura mal leido NO se detecta. Es el argumento "
        "mas fuerte para poblarlas desde el historico de diez anos.",
    "proveedor":
        "el NOMBRE no es un hecho fiscal: la identidad se juzga por NIF, que si "
        "tiene digito de control. Hasta el 21-08-2026 esto era ademas PELIGROSO, "
        "porque las cuatro caches se consultaban por nombre y un nombre mal leido "
        "apagaba cuatro guards en silencio. Corregido: ahora se busca primero por "
        "NIF (ver _entrada_de_proveedor y FAMILIA R). Con eso, cambiar el nombre "
        "ya no altera ninguna comprobacion, y por eso escapa legitimamente.",
}

# --- Mutaciones --------------------------------------------------------------
def mutaciones_numericas(valor):
    """Todas las formas mecanicas de estropear UN numero. Devuelve (familia, nuevo)."""
    try:
        x = float(valor)
    except (TypeError, ValueError):
        return []
    fuera = [
        ("centimo", f"{x + 0.01:.2f}"),
        ("tres_centimos", f"{x + 0.03:.2f}"),
        ("un_euro", f"{x + 1:.2f}"),
        ("diez_euros", f"{x + 10:.2f}"),
        ("coma_derecha", f"{x * 10:.2f}"),
        ("coma_izquierda", f"{x / 10:.2f}"),
        ("negado", f"{-x:.2f}"),
        ("cero", "0.00"),
        ("duplicado", f"{x * 2:.2f}"),
    ]
    # Mutacion de UN digito, que es el error de OCR real (un 5 leido como 8)
    texto = f"{x:.2f}"
    for i, c in enumerate(texto):
        if not c.isdigit():
            continue
        for d in "0123456789":
            if d == c:
                continue
            fuera.append((f"digito_{i}", texto[:i] + d + texto[i + 1:]))
    return fuera


def mutaciones_nif(valor):
    fuera = []
    for i, c in enumerate(valor):
        alfabeto = "0123456789" if c.isdigit() else "ABCDEFGHIJKLMNPQRSTVWXYZ"
        for d in alfabeto:
            if d == c:
                continue
            fuera.append((f"nif_pos_{i}", valor[:i] + d + valor[i + 1:]))
    return fuera


def mutaciones_fecha(valor):
    return [("fecha", v) for v in
            ("2026-03-16", "2026-04-15", "2025-03-15", "2019-03-15",
             "2026-13-15", "2026-02-30", "2026-03-32", "15/03/2026", "")]


def mutaciones_texto(valor):
    return [("texto", v) for v in
            (str(valor) + "X", str(valor)[:-1] if len(str(valor)) > 1 else "Z",
             "OTRA COSA")]


def todas_las_mutaciones(campo, valor):
    if campo == "nif":
        return mutaciones_nif(valor)
    if campo == "fecha_expedicion":
        return mutaciones_fecha(valor)
    fuera = [("borrar", None), ("vaciar", ""), ("basura", "abc"),
             ("espacios", "   ")]
    try:
        float(valor)
    except (TypeError, ValueError):
        return fuera + mutaciones_texto(valor)
    return fuera + mutaciones_numericas(valor)


def es_equivalente(campo, familia, original, nuevo, fila_base):
    """.La factura mutada sigue siendo una factura CORRECTA?

    Es la pregunta honesta, y hay que hacersela antes de acusar: si la mutacion
    produce algo que tambien es valido, no hay nada que detectar, y contarlo como
    escape seria reprocharle al motor que no caza lo que no esta mal.

    Los tres casos, y los dos ultimos se me pasaron en la primera version del
    barrido, que por eso acusaba de 40 escapes cuando habia 0.
    """
    # 1. Quitar el desglose de una factura de UN SOLO tipo no pierde informacion
    #    fiscal: la comprobacion global vuelve a deducir el tipo desde cuota/base
    #    y el asiento sale identico. Es la factura de camara, que es correcta.
    #
    #    Solo vale si lo que queda del desglose no contradice la base total. En
    #    una factura de DOS tipos, quitar uno deja el otro sin sumar la base, y
    #    eso si es detectable — y se detecta: en la semilla de dos tipos estas
    #    mismas mutaciones NO escapan. Para eso esta esa semilla.
    #
    #    Va lo PRIMERO a proposito: trata mutaciones cuyo valor nuevo es None o
    #    "", asi que puesto detras del guard de mas abajo no se alcanzaria nunca.
    if campo in ("base_10", "base_4", "base_21") and familia in ("borrar", "vaciar", "espacios"):
        try:
            restantes = sum(float(fila_base[c]) for c in ("base_10", "base_4", "base_21")
                            if c in fila_base and c != campo)
            return (abs(restantes) <= TOL
                    and abs(float(fila_base['base_total']) - float(fila_base[campo])) <= TOL)
        except (KeyError, TypeError, ValueError):
            return False
    if nuevo is None or nuevo == "":
        return False
    # 2. Una fecha REAL distinta, dentro del mismo ejercicio, produce una factura
    #    igual de valida. Conte como escape que una factura del 15 de marzo
    #    siguiera siendo VERDE con fecha del 16. Lo es: es otra factura correcta.
    if campo == "fecha_expedicion":
        import contrato_datos as cd
        d = cd.parse_fecha(nuevo)
        return d.estado == cd.VALUE and d.valor.year == 2026
    # 3. Por debajo de la tolerancia contable no hay error que detectar. Es una
    #    decision declarada del proyecto (TOL=0.02), no un descuido.
    try:
        a, b = float(original), float(nuevo)
    except (TypeError, ValueError):
        return False
    return abs(a - b) <= TOL


def evaluar(fila):
    v, motivo, _ = mv.evaluar_fila_v4(fila, set(), {}, {}, {}, MAESTRO,
                                      alta_cliente_anio=2015,
                                      nif_cliente_titular=None,
                                      ejercicio_tanda=2026)
    return v, motivo


def main():
    verboso = "--verboso" in sys.argv
    from motor_veredicto import valida_nif
    for n in (NIF_A, NIF_B):
        if not valida_nif(n)[0]:
            print(f"El NIF de prueba {n} no es valido. El barrido no mediria nada.")
            return 2

    print("=" * 72)
    print("BARRIDO DE FALSOS VERDES — todas las mutaciones de UN SOLO CAMPO")
    print("=" * 72)

    total = equivalentes = cazadas = n_declarados = 0
    escapes = []
    declarados_vistos = set()

    for nombre, semilla in SEMILLAS.items():
        v0, _ = evaluar(dict(semilla))
        if v0 != "VERDE":
            print(f"\n  ⚠ La semilla '{nombre}' no da VERDE, da {v0}.")
            print("    Sin punto de partida VERDE no hay nada que atacar. Se salta.")
            continue

        n_mut = n_esc = 0
        for campo in sorted(semilla):
            if campo == "verificacion":
                continue          # su mutacion es el propio guard de confianza
            for familia, nuevo in todas_las_mutaciones(campo, semilla[campo]):
                fila = dict(semilla)
                if nuevo is None:
                    fila.pop(campo, None)
                else:
                    fila[campo] = nuevo
                total += 1
                n_mut += 1
                if es_equivalente(campo, familia, semilla[campo], nuevo, semilla):
                    equivalentes += 1
                    continue
                v, motivo = evaluar(fila)
                if v != "VERDE":
                    cazadas += 1
                    continue
                if campo in ESCAPES_DECLARADOS:
                    declarados_vistos.add(campo)
                    n_declarados += 1
                    continue
                n_esc += 1
                escapes.append((nombre, campo, familia, nuevo))
        print(f"\n  {nombre}")
        print(f"    mutaciones probadas : {n_mut}")
        print(f"    escapan sin explicar: {n_esc}")

    print()
    print("=" * 72)
    print(f"  mutaciones totales            : {total:,}")
    print(f"  equivalentes (nada que cazar) : {equivalentes:,}")
    print(f"  CAZADAS por el motor          : {cazadas:,}")
    print(f"  escapes DECLARADOS (campos sin redundancia): {n_declarados:,} "
          f"en {len(declarados_vistos)} campos")
    print(f"  ESCAPES SIN EXPLICAR          : {len(escapes)}")
    # El porcentaje se calcula sobre lo que ES DETECTABLE: se descuentan las
    # mutaciones equivalentes (no hay error que cazar) y las de campos declarados
    # sin redundancia (nadie puede cazarlas sin historico). Meterlas en el
    # denominador daria un numero mas feo y menos cierto; dejarlas fuera sin
    # decirlo daria uno mas bonito y tramposo. Se dicen las tres cifras.
    detectables = total - equivalentes - n_declarados
    if detectables:
        print(f"  deteccion sobre lo DETECTABLE : {cazadas * 100.0 / detectables:.2f}%")
        print(f"     (detectable = total - equivalentes - campos sin redundancia)")

    obsoletos = set(ESCAPES_DECLARADOS) - declarados_vistos
    if obsoletos:
        print()
        print("DECLARACIONES OBSOLETAS — se dijo que escapaban y ya no escapan:")
        for c in sorted(obsoletos):
            print(f"  ! {c}  -> ya no escapa; quitar de ESCAPES_DECLARADOS")

    if escapes:
        print()
        print("ESCAPES SIN EXPLICAR — cada uno es un falso verde o una excepcion")
        print("que hay que poder razonar. No hay tercera opcion:")
        vistos = set()
        for semilla, campo, familia, nuevo in escapes:
            clave = (campo, familia)
            if clave in vistos and not verboso:
                continue
            vistos.add(clave)
            print(f"  ✗ [{semilla}] campo '{campo}', mutacion '{familia}' -> sigue VERDE")
        if not verboso:
            print(f"  ({len(escapes)} escapes en total, agrupados; --verboso para verlos todos)")

    # --- CONTROL POSITIVO -------------------------------------------------
    # Un barrido que sale a cero no prueba nada si no se ha comprobado que sabe
    # dar distinto de cero. Es la leccion de la FAMILIA G y aqui aplica igual.
    #
    # El primer control que escribi NO servia, y merece la pena contarlo: anulaba
    # guard_cuadre_total y esperaba escapes. No aparecio ninguno... porque el
    # motor tiene REDUNDANCIA REAL: con cuadre_total anulado, un total alterado
    # lo sigue cazando guard_retencion_vs_error, que mira el mismo hecho por otro
    # lado. Buena noticia sobre el motor, control inutil: media la redundancia,
    # no el barrido.
    #
    # El control bueno rompe el veredicto ENTERO. Si con un motor que dice VERDE
    # a todo el barrido no encuentra nada, es que esta ciego de verdad.
    original = mv.calcular_veredicto_v4
    mv.calcular_veredicto_v4 = lambda guards: ("VERDE", "motor saboteado a proposito")
    try:
        semilla = SEMILLAS["21% con desglose"]
        ciegos = efectivas_control = 0
        for campo in ("total_factura", "iva_total", "base_total"):
            for familia, nuevo in mutaciones_numericas(semilla[campo]):
                if es_equivalente(campo, familia, semilla[campo], nuevo, semilla):
                    continue
                efectivas_control += 1
                f = dict(semilla)
                f[campo] = nuevo
                if evaluar(f)[0] == "VERDE":
                    ciegos += 1
    finally:
        mv.calcular_veredicto_v4 = original

    print()
    print(f"  control positivo (motor saboteado): detecta {ciegos} de "
          f"{efectivas_control} escapes que deberia ver")
    if ciegos != efectivas_control:
        print("  ✗ EL BARRIDO ESTA CIEGO: con un motor que dice VERDE a todo, no ve")
        print("    todos los escapes. Su cero de arriba no significa lo que parece.")
        return 1

    print()
    if escapes or obsoletos:
        return 1
    print("Ninguna mutacion de un solo campo se cuela como VERDE sin explicacion,")
    print("y el barrido ha demostrado que sabria verlo si se colara.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
