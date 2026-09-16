#!/usr/bin/env python3
"""test_puerta_cloud.py — la bateria que demuestra que la puerta bloquea.

POR QUE ESTA BATERIA, Y NO SOLO EL MODULO
-------------------------------------------
Una puerta que nadie ha intentado forzar no es una puerta: es una intencion.
Este proyecto ya tiene el precedente exacto -- el escaner de privacidad
respondia "sin hallazgos" sobre ficheros que no habia mirado, y nadie lo supo
durante ocho dias porque nadie le habia puesto delante un fichero trampa.

Aqui se le ponen delante todos los que se me han ocurrido, y ademas se
comprueba lo contrario: que con la puerta SABOTEADA esta bateria se pone roja.
Una bateria que pasa igual con el codigo roto no esta comprobando nada
(FAMILIA G de test_adversarial.py, misma leccion).

REGLA DE DATOS
----------------
Ni un dato real. Las rutas son inventadas y ni siquiera se crean en disco: la
puerta no abre documentos, solo decide y anota. El unico literal con forma de
identificador es un cebo fabricado para comprobar que NO aparece en el
registro.
"""
import importlib.util
import json
import os
import sys
import tempfile

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import puerta_cloud as pc

AQUI = os.path.dirname(os.path.abspath(__file__))

#: El patron de NIF se IMPORTA del escaner de verdad, no se copia. Copiarlo
#: seria crear la segunda definicion que este proyecto persigue con un barrido
#: AST -- y ademas esta bateria dejaria de beneficiarse de cada mejora del
#: patron (la R que se le añadio el 15-09-2026, por ejemplo).
_spec = importlib.util.spec_from_file_location(
    "privacy_scan", os.path.join(AQUI, "scripts", "privacy_scan.py"))
_privacy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_privacy)
PATRON_NIF = _privacy.PATRON_NIF

CERRADO = {}
SOLO_CLOUD = {pc.ENV_CLOUD: "1"}
TODO_ABIERTO = {pc.ENV_CLOUD: "1", pc.ENV_DATOS_REALES: "1"}

#: Token fabricado que va en la ruta del documento de prueba. Si aparece en el
#: registro, el registro esta filtrando el nombre del fichero -- que en un caso
#: real seria el nombre del proveedor y el mes.
TOKEN_RUTA = "TOKEN_QUE_NO_DEBE_SALIR"

resultados = []


def comprobar(nombre, condicion, detalle="", severidad="P1"):
    resultados.append((nombre, condicion, detalle, severidad))
    print(f"  [{'OK  ' if condicion else 'FALLA'}] {nombre}"
          + (f"\n           {detalle}" if not condicion and detalle else ""))


def bloquea(procedencia, entorno, confirmacion=None, n=1):
    """True si la puerta NIEGA la apertura del lote."""
    lote = pc.abrir_lote(n, procedencia, "gemini", entorno=entorno,
                         confirmacion=confirmacion, registro=None)
    return not lote.permitido


def main():
    print("=" * 72)
    print("PUERTA CLOUD — control positivo")
    print("=" * 72)

    print("\nA. Cerrada por defecto: sin entorno no sale NADA")
    comprobar("un documento SINTETICO no sale si no hay permiso de cloud",
              bloquea(pc.SINTETICO, CERRADO), severidad="P0")
    comprobar("un documento REAL tampoco",
              bloquea(pc.REAL, CERRADO), severidad="P0")
    comprobar("y con el entorno REAL de esta maquina (os.environ) tampoco",
              bloquea(pc.REAL, None), severidad="P0")

    print("\nB. Lo que no se declara es REAL (fail closed)")
    # El bug del .DAT, en su version de procedencia: quien etiqueta mal, o no
    # etiqueta, no puede abrir la puerta.
    for valor, etiqueta in ((None, "None"), ("", "cadena vacia"),
                            ("sintetico", "minusculas (typo)"),
                            ("SINTETIC0", "typo con cero"),
                            ("ANONIMIZADO", "un nivel que no existe"),
                            (0, "un cero"), (True, "un booleano"),
                            (["SINTETICO"], "una lista")):
        proc, declarada = pc.normalizar_procedencia(valor)
        comprobar(f"procedencia {etiqueta} -> REAL y no declarada",
                  proc == pc.REAL and declarada is False,
                  f"dio {proc}/{declarada}", "P0")
    comprobar("y por tanto NO sale con permiso de cloud pero sin datos reales",
              bloquea("sintetico", SOLO_CLOUD), severidad="P0")

    print("\nC. El camino SINTETICO: util hoy, sin DPA y sin riesgo")
    lote = pc.abrir_lote(3, pc.SINTETICO, "gemini", entorno=SOLO_CLOUD,
                         registro=None)
    comprobar("un SINTETICO declarado sale con solo el permiso de cloud",
              lote.permitido and lote.motivo == pc.OK)
    comprobar("...y queda anotado como procedencia declarada",
              lote.procedencia == pc.SINTETICO and lote.declarada is True)
    comprobar("pero con ese mismo entorno un REAL sigue bloqueado",
              bloquea(pc.REAL, SOLO_CLOUD), severidad="P0")

    print("\nD. El camino REAL: dos llaves y un recuento que hay que mirar")
    comprobar("sin la llave legal (DPA) no sale",
              bloquea(pc.REAL, SOLO_CLOUD, confirmacion=1), severidad="P0")
    comprobar("con las dos llaves pero SIN confirmacion, no sale",
              bloquea(pc.REAL, TODO_ABIERTO), severidad="P0")
    comprobar("con una confirmacion que no coincide con el recuento, no sale",
              bloquea(pc.REAL, TODO_ABIERTO, confirmacion=5, n=3), severidad="P0")
    comprobar("confirmacion=True NO vale como confirmacion (isinstance(True, int))",
              bloquea(pc.REAL, TODO_ABIERTO, confirmacion=True, n=1), severidad="P0")
    comprobar("con las dos llaves y el recuento exacto, sale",
              not bloquea(pc.REAL, TODO_ABIERTO, confirmacion=3, n=3))
    comprobar("un recuento absurdo (0) no abre lote",
              bloquea(pc.SINTETICO, SOLO_CLOUD, n=0), severidad="P0")
    comprobar("un recuento negativo tampoco",
              bloquea(pc.SINTETICO, SOLO_CLOUD, n=-4), severidad="P0")

    print("\nE. El lote esta ACOTADO: la confirmacion es ejecutable")
    lote = pc.abrir_lote(2, pc.SINTETICO, "gemini", entorno=SOLO_CLOUD,
                         registro=None)
    r = [lote.consumir(f"/inventado/{i}.jpg") for i in range(3)]
    comprobar("los 2 autorizados pasan",
              r[0][0] is True and r[1][0] is True)
    comprobar("el 3o se bloquea: un bucle descontrolado no manda 500",
              r[2][0] is False and r[2][1] == pc.LOTE_AGOTADO, severidad="P0")
    lote_no = pc.abrir_lote(5, pc.REAL, "gemini", entorno=CERRADO, registro=None)
    negado = lote_no.consumir("/inventado/x.jpg")
    comprobar("un lote NO autorizado bloquea cada documento, uno por uno",
              negado.permitido is False and negado.motivo == pc.LOTE_NO_AUTORIZADO,
              severidad="P0")

    print("\nE-bis. El permiso vale para UN documento, no para 'algo'")
    # Sin esto, la garantia dependeria de que nadie llame por dentro a la
    # funcion de bajo nivel saltandose el punto de entrada: una convencion.
    lote = pc.abrir_lote(2, pc.SINTETICO, "gemini", entorno=SOLO_CLOUD,
                         registro=None)
    permiso = lote.consumir("/inventado/a.jpg")
    comprobar("un permiso concedido pasa exigir_permiso para SU documento",
              pc.exigir_permiso(permiso, "/inventado/a.jpg") is None)
    for descripcion, prueba in (
            ("otro documento", lambda: pc.exigir_permiso(permiso, "/inventado/b.jpg")),
            ("un permiso bloqueado", lambda: pc.exigir_permiso(
                pc.abrir_lote(1, pc.REAL, "gemini", entorno=CERRADO,
                              registro=None).consumir("/inventado/a.jpg"),
                "/inventado/a.jpg")),
            ("None en lugar de permiso", lambda: pc.exigir_permiso(None, "/inventado/a.jpg")),
            ("una tupla falsificada a mano", lambda: pc.exigir_permiso(
                (True, "OK", "0" * 12), "/inventado/a.jpg")),
            ("un True pelado", lambda: pc.exigir_permiso(True, "/inventado/a.jpg"))):
        try:
            prueba()
            cazado = False
        except pc.SalidaBloqueada:
            cazado = True
        comprobar(f"...y NO pasa con {descripcion}", cazado, severidad="P0")

    try:
        pc.exigir_permiso(permiso, "/inventado/b.jpg")
    except pc.SalidaBloqueada as e:
        comprobar("el mensaje del bloqueo no lleva la ruta, solo huellas",
                  "/inventado/" not in str(e), str(e), "P0")

    print("\nF. El registro: anota lo que pasa, nunca lo que dice el documento")
    tmp = tempfile.mkdtemp(prefix="puerta_")
    reg = os.path.join(tmp, "registro.jsonl")
    ruta_cebo = f"/facturas/{TOKEN_RUTA}/12345678Z_factura.jpg"

    lote = pc.abrir_lote(1, pc.SINTETICO, "gemini", modelo="gemini-3.1-flash-lite",
                         entorno=SOLO_CLOUD, registro=reg)
    lote.consumir(ruta_cebo)
    lote.consumir(ruta_cebo)          # este se bloquea: lote agotado
    lote.anotar_resultado(ruta_cebo, tokens_entrada=1200, tokens_salida=310,
                          coste_eur=0.00041)
    bloqueado = pc.abrir_lote(1, pc.REAL, "gemini", entorno=CERRADO, registro=reg)
    bloqueado.consumir(ruta_cebo)

    with open(reg, encoding="utf-8") as f:
        crudo = f.read()
    lineas = [json.loads(l) for l in crudo.splitlines() if l.strip()]

    comprobar("se anota una linea por intento, permitido Y bloqueado",
              len(lineas) == 6, f"hubo {len(lineas)}")
    comprobar("un intento BLOQUEADO deja rastro (es lo que mas interesa auditar)",
              any(l["estado"] == pc.BLOQUEADO for l in lineas), severidad="P0")
    # El hueco que aparecio al ejecutar esto de verdad la primera vez: la puerta
    # se cerraba, el proceso terminaba, y no quedaba constancia de que alguien
    # habia intentado sacar N documentos. Ahora el LOTE bloqueado se anota, con
    # cuantos documentos se pretendia enviar.
    lotes = [l for l in lineas if l["tipo"] == pc.LOTE]
    comprobar("un LOTE que la puerta NO abre tambien deja linea propia",
              any(l["estado"] == pc.BLOQUEADO for l in lotes), severidad="P0")
    comprobar("...y esa linea dice cuantos documentos se pretendia enviar",
              all(l["n_documentos"] is not None for l in lotes))
    comprobar("ningun campo fuera de la lista cerrada CAMPOS_REGISTRO",
              all(set(l) == set(pc.CAMPOS_REGISTRO) for l in lineas),
              str([sorted(set(l) - set(pc.CAMPOS_REGISTRO)) for l in lineas]),
              "P0")
    comprobar("ningun motivo fuera del conjunto cerrado MOTIVOS",
              all(l["motivo"] in pc.MOTIVOS for l in lineas), severidad="P0")
    comprobar("la ruta del documento NO aparece en el registro",
              TOKEN_RUTA not in crudo, severidad="P0")
    comprobar("ni el nombre del fichero",
              "factura.jpg" not in crudo, severidad="P0")
    comprobar("ni nada con forma de NIF/DNI/CIF (patron del escaner real)",
              PATRON_NIF.search(crudo) is None, severidad="P0")
    con_doc = [l for l in lineas if l["doc"] is not None]
    comprobar("el documento se identifica por huella, no por nombre",
              con_doc and all(len(l["doc"]) == 12 for l in con_doc))
    comprobar("misma ruta -> misma huella (se puede seguir la pista)",
              len({l["doc"] for l in con_doc}) == 1)

    res = [l for l in lineas if l["tipo"] == pc.RESULTADO]
    comprobar("el coste se anota cuando se conoce",
              len(res) == 1 and res[0]["coste_eur"] == 0.00041)
    permisos = [l for l in lineas if l["tipo"] == pc.PERMISO]
    comprobar("y cuando no se conoce va a None, NUNCA a 0 (no_comprobado)",
              all(l["coste_eur"] is None for l in permisos), severidad="P0")

    # La lista cerrada tiene que MORDER, no solo estar escrita.
    lote_malo = pc.abrir_lote(1, pc.SINTETICO, "gemini", entorno=SOLO_CLOUD,
                              registro=reg)
    try:
        lote_malo._escribir({"ts": "x", "proveedor_nombre": "algo"})
        cazado = False
    except ValueError:
        cazado = True
    comprobar("añadir un campo no declarado revienta en el acto",
              cazado, "CAMPOS_REGISTRO no se defiende sola", "P0")

    print("\nG. CONTROL NEGATIVO: ¿sabria esta bateria ponerse roja?")

    original = pc.normalizar_procedencia
    try:
        # El sabotaje exacto que importa: que lo no declarado pase por sintetico.
        pc.normalizar_procedencia = lambda v: (
            (v, True) if v in pc.PROCEDENCIAS else (pc.SINTETICO, False))
        colado = not bloquea("sintetico", SOLO_CLOUD)
        comprobar("con 'lo desconocido = SINTETICO', un documento sin declarar SE COLA",
                  colado, "el sabotaje no cambio nada: la comprobacion B no vigila", "P0")
    finally:
        pc.normalizar_procedencia = original
    comprobar("y al deshacer el sabotaje vuelve a bloquearse",
              bloquea("sintetico", SOLO_CLOUD), severidad="P0")

    original_abrir = pc.abrir_lote
    try:
        def sin_confirmacion(n, procedencia, proveedor, modelo=None,
                             confirmacion=None, entorno=None, registro=None):
            return original_abrir(n, procedencia, proveedor, modelo=modelo,
                                  confirmacion=n, entorno=entorno,
                                  registro=registro)
        pc.abrir_lote = sin_confirmacion
        colado = not bloquea(pc.REAL, TODO_ABIERTO, n=7)
        comprobar("con la confirmacion ignorada, un lote real SE COLA sin que nadie lo mire",
                  colado, "el sabotaje no cambio nada: la comprobacion D no vigila", "P0")
    finally:
        pc.abrir_lote = original_abrir
    comprobar("y al deshacerlo vuelve a exigir el recuento",
              bloquea(pc.REAL, TODO_ABIERTO, n=7), severidad="P0")

    fallan = [r for r in resultados if not r[1]]
    p0 = [r for r in fallan if r[3] == "P0"]
    print("\n" + "=" * 72)
    print(f"Pruebas: {len(resultados)}   en verde: {len(resultados) - len(fallan)}   "
          f"FALLAN: {len(fallan)}  (de ellas P0: {len(p0)})")
    if fallan:
        print("\nLo que falla:")
        for nombre, _, detalle, sev in fallan:
            print(f"  [{sev}] {nombre}" + (f" — {detalle}" if detalle else ""))
        return 1
    print("\nLa puerta esta cerrada por defecto, lo no declarado se trata como")
    print("real, el lote esta acotado, el registro no filtra nada, y esta")
    print("bateria ha demostrado que sabria ponerse roja si dejara de ser cierto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
