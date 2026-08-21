#!/usr/bin/env python3
"""ensayo_contrato_captura.py — que lo que PIDE la captura sea lo que USA el motor.

LA COSTURA QUE NADIE MIRA
-------------------------
`captura_orquestador.py` le pide a la IA un JSON con unos nombres de campo.
`motor_veredicto.py` y `contrato_datos.py` leen unos nombres de campo. Son dos
listas escritas en ficheros distintos, en momentos distintos, y **nada comprueba
que coincidan**.

Si dejan de coincidir no salta nada. El campo llega con otro nombre, el contrato
lo ve MISSING, el guard correspondiente se declara NO_COMPROBADO y la factura
sale AMBAR. Se lee como "la captura ha ido mal" cuando lo que ha pasado es que
una letra no cuadra entre dos ficheros. Es exactamente el tipo de fallo que se ha
repetido todo el proyecto: piezas correctas, costura sin revisar.

Y hay una asimetria que importa, por eso se comprueban las dos direcciones:

  PIDE Y NADIE USA   trabajo desperdiciado, y peor: cada campo de mas diluye la
                     atencion del modelo sobre los que si importan. Barato de
                     detectar, caro de no ver.
  USA Y NADIE PIDE   el guard nunca va a tener su dato. No es un fallo si esta
                     DECLARADO (hay campos que el motor acepta y hoy no se
                     capturan a proposito); lo es si nadie lo sabia.

Esto no llama a ninguna API ni necesita una factura: lee los dos ficheros.

Uso:  python3 ensayo_contrato_captura.py
"""
import ast
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import contrato_datos as cd

#: Campos que el motor sabe usar y que la captura NO pide a proposito, con el
#: motivo. Si uno deja de estar declarado, este ensayo avisa: una deuda que se
#: olvida deja de ser una deuda y pasa a ser un agujero.
NO_SE_CAPTURAN_A_PROPOSITO = {
    "categoria_producto":
        "lo pediria para guard_tipo_producto_iva_semantico, y hoy NO se pide: "
        "clasificar el producto es criterio, no lectura. El guard esta declarado "
        "EXENTO en el veredicto justo por esto (ver la lista `exentos`).",
    "fecha_vencimiento":
        "guard_vencimiento_coherente lo usaria, pero el vencimiento no siempre "
        "esta impreso y hoy no se pide. Su NO_COMPROBADO tambien esta exento.",
    "cuenta_proveedor": "lo resuelve el maestro del cliente, no la factura.",
    "cuenta_debe": "la propone el mapeo de cuenta de gasto, no la factura.",
    "motivo_semaforo": "lo escribe el propio motor, no viene de la captura.",
    "tipo_iva_declarado": "lo trae tramos_iva, que es mas completo y ya se pide.",
    "concepto": "hoy no se pide. guard_tipo_operacion_especial lo usaria para "
                "detectar 'amortizacion' o 'inmovilizado' en el texto; sin el, "
                "ese guard solo puede mirar la cuenta contable. DEUDA DECLARADA: "
                "se pide en cuanto se valide el prompt v2 contra papel real.",
}

#: Nombres que son el MISMO campo escrito distinto en los dos lados. Cada alias
#: es deuda: funciona, y el dia que alguien toque uno de los dos lados sin ver
#: esta tabla, se rompe en silencio.
#: Vacio hoy, y mejor asi. Se conserva la comprobacion porque el dia que alguien
#: escriba un nombre distinto en un lado, esto es lo que lo caza.
#: (La primera version declaraba un alias 'irpf' -> 'irpf_retencion' que NO
#: existia: el prompt ya pide 'irpf_retencion' con su nombre bueno. Una deuda
#: inventada es tan mala como una deuda olvidada.)
ALIAS_CONOCIDOS = {}

resultados = []


def comprobar(nombre, condicion, detalle=""):
    resultados.append((nombre, condicion))
    print(f"  [{'OK  ' if condicion else 'FALLA'}] {nombre}")
    if not condicion and detalle:
        print(f"           {detalle}")


def campos_que_pide_la_captura():
    """Los nombres de campo del prompt, y SOLO del prompt.

    Se acota al literal PROMPT_CAPTURA a proposito. La primera version escaneaba
    el fichero entero y colaba 'role' y 'content', que son del sobre de la
    llamada a la API y no campos de factura. Un instrumento que mide de mas
    acusa de mas, y eso lo acaba desactivando alguien."""
    fuente = open(os.path.join(AQUI, "captura_orquestador.py"), encoding="utf-8").read()
    arbol = ast.parse(fuente)
    prompt = None
    for nodo in ast.walk(arbol):
        if (isinstance(nodo, ast.Assign) and len(nodo.targets) == 1
                and isinstance(nodo.targets[0], ast.Name)
                and nodo.targets[0].id == "PROMPT_CAPTURA"
                and isinstance(nodo.value, ast.Constant)):
            prompt = nodo.value.value
    if prompt is None:
        raise SystemExit("No encuentro PROMPT_CAPTURA en captura_orquestador.py")
    # Solo el bloque JSON de campos, que va entre la primera llave y su cierre.
    bloque = prompt[prompt.index("{"):prompt.rindex("}") + 1]
    # Claves de primer nivel: van al principio de linea con dos espacios.
    return set(re.findall(r'^  "([^"]+)":', bloque, re.M))


#: De donde puede salir un campo de FACTURA. Cualquier otro `.get(...)` del motor
#: es una cache, un maestro o un diccionario interno, y meterlo aqui fue el
#: segundo fallo del instrumento: acusaba a 'plazos_vistos', 'grupo_pgc' o
#: 'titulo' de ser campos de factura sin capturar.
RECEPTORES_DE_FILA = {"fila", "fila_veredicto", "fila_corregida", "canon", "cruda"}


def campos_que_usa_el_motor():
    """Los nombres que el motor y el contrato leen DE LA FILA de la factura."""
    usados = set(cd.CAMPOS_MONETARIOS) | set(cd.CAMPOS_CRITICOS)
    for fichero in ("motor_veredicto.py", "contrato_datos.py"):
        arbol = ast.parse(open(os.path.join(AQUI, fichero), encoding="utf-8").read())
        for nodo in ast.walk(arbol):
            if not (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute)
                    and nodo.func.attr in ("get", "texto", "num", "fecha")
                    and nodo.args and isinstance(nodo.args[0], ast.Constant)
                    and isinstance(nodo.args[0].value, str)):
                continue
            receptor = nodo.func.value
            nombre_receptor = None
            if isinstance(receptor, ast.Name):
                nombre_receptor = receptor.id
            elif isinstance(receptor, ast.Attribute):
                nombre_receptor = receptor.attr        # self.cruda -> 'cruda'
            if nombre_receptor in RECEPTORES_DE_FILA:
                usados.add(nodo.args[0].value)
    return usados


def main():
    print("=" * 72)
    print("CONTRATO CAPTURA <-> MOTOR: .piden y usan los mismos campos?")
    print("=" * 72)
    pide = campos_que_pide_la_captura()
    usa = campos_que_usa_el_motor()
    pide_norm = {ALIAS_CONOCIDOS.get(c, c) for c in pide}

    print(f"\n  campos que pide la captura : {len(pide)}")
    print(f"  campos que lee el motor    : {len(usa)}")

    print("\nLO QUE LA CAPTURA PIDE, .LO USA ALGUIEN?")
    huerfanos = sorted(c for c in pide_norm if c not in usa)
    comprobar("ningun campo se pide para nada",
              not huerfanos,
              f"se piden y nadie los lee: {huerfanos}\n"
              f"           Cada campo de mas diluye la atencion del modelo sobre\n"
              f"           los que si importan. O se usa, o se quita del prompt.")

    print("\nLO QUE EL MOTOR USA, .LO PIDE ALGUIEN?")
    # Solo interesan los campos que podrian venir de una factura: los que el motor
    # calcula o recibe de otro sitio ya estan declarados arriba.
    sin_pedir = sorted(c for c in usa
                       if c not in pide_norm
                       and c not in NO_SE_CAPTURAN_A_PROPOSITO
                       and not c.startswith(('cache_', 'ejemplos', 'numeros_', 'n_')))
    comprobar("todo lo que el motor lee, o se pide o esta declarado",
              not sin_pedir,
              f"el motor los lee y nadie los pide ni los declara: {sin_pedir}\n"
              f"           Esos guards NUNCA van a tener su dato, y nadie lo sabia.")

    print("\nDECLARACIONES QUE SE HAYAN QUEDADO OBSOLETAS:")
    revividos = sorted(c for c in NO_SE_CAPTURAN_A_PROPOSITO if c in pide_norm)
    comprobar("ningun campo declarado 'no se captura' se captura ya",
              not revividos,
              f"ya se piden, quitar de NO_SE_CAPTURAN_A_PROPOSITO: {revividos}")
    muertos = sorted(c for c in NO_SE_CAPTURAN_A_PROPOSITO if c not in usa)
    comprobar("ningun campo declarado sigue declarado sin que el motor lo lea",
              not muertos,
              f"ya no los lee el motor, sobran de la lista: {muertos}")

    print("\nALIAS (cada uno es deuda: funciona hasta que alguien toca un lado):")
    for origen, destino in sorted(ALIAS_CONOCIDOS.items()):
        vivo = origen in pide and destino in usa
        print(f"    {origen!r} (captura) -> {destino!r} (motor)   "
              f"{'vivo' if vivo else 'YA NO APLICA, revisar'}")
        comprobar(f"el alias {origen} -> {destino} sigue siendo necesario", vivo)

    fallos = [r for r in resultados if not r[1]]
    print()
    print("=" * 72)
    print(f"Pruebas: {len(resultados)}   en verde: {len(resultados)-len(fallos)}   "
          f"FALLAN: {len(fallos)}")
    if fallos:
        print("\nLA COSTURA ENTRE CAPTURA Y MOTOR NO CUADRA:")
        for nombre, _ in fallos:
            print(f"  · {nombre}")
        return 1
    print("\nLo que la captura pide es lo que el motor usa, y lo que no se pide")
    print("esta declarado con su motivo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
