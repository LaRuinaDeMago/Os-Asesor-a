#!/usr/bin/env python3
"""ensayo_cadena_captura.py — la cadena entera foto→JSON→CSV→motor, sin API.

LA COSTURA QUE FALTABA, Y EL DEFECTO REAL QUE ESCONDIA
--------------------------------------------------------
`ensayo_contrato_captura.py` ya comprobaba que los NOMBRES de campo que pide la
captura son los que usa el motor. Es necesario y no basta: comprueba las
etiquetas, no el viaje. **Nadie habia ejecutado nunca un JSON con la forma
exacta que pide el prompt y visto salir un veredicto por el otro extremo.**

Al hacerlo (16-09-2026) aparecio un defecto real y dormido:

    la captura escribe un CSV (csv.DictWriter) y el orquestador lo lee
    (csv.DictReader). En ese viaje los dos unicos campos ANIDADOS del prompt
    v2 -- `tramos_iva` y `confianza_campos` -- dejaban de ser lista/dict y
    pasaban a ser la cadena de su repr. Sus dos consumidores preguntan por el
    TIPO (isinstance), asi que los dos fallaban EN SILENCIO: los tramos se
    perdian y el guard de confianza se declaraba NO_APLICA para siempre.

Medido: una factura con un tramo al 5% -- el tipo que NO tiene campo plano
equivalente, y justo el caso para el que se anadio `tramos_iva` -- llegaba al
motor con `tramos: []`. No daba error: daba un veredicto peor. Arreglado en
`contrato_datos.parse_estructura`, que es la capa cuyo trabajo es que un dato
signifique lo mismo llegue como llegue.

QUE PRUEBA ESTE ENSAYO, Y POR QUE ASI
---------------------------------------
Recorre la MISMA serializacion que usa produccion, no una imitacion: escribe
con `csv.DictWriter` igual que `procesar_carpeta()` y lee con `csv.DictReader`
igual que `orquestador.py`. Si manana alguien cambia como se guarda el CSV, este
ensayo se entera; uno que construyera el dict a mano, no.

REGLA DE DATOS
----------------
Cero API y cero datos reales: el JSON es sintetico y el NIF es inventado con
checksum valido. No abre ninguna foto ni necesita ninguna clave.
"""
import csv
import io
import sys

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import contrato_datos
import motor_veredicto as motor
from contrato_datos import FacturaCanonica

resultados = []


def comprobar(nombre, condicion, detalle="", severidad="P1"):
    resultados.append((nombre, condicion, detalle, severidad))
    print(f"  [{'OK  ' if condicion else 'FALLA'}] {nombre}"
          + (f"\n           {detalle}" if not condicion and detalle else ""))


def capturado(**cambios):
    """Un JSON con la forma EXACTA que pide PROMPT_CAPTURA, campos v2 incluidos."""
    base = {
        "fecha_expedicion": "2026-03-26",
        "nº_documento": "A26/7612",
        "proveedor": "PROVEEDOR PILOTO SL",
        "nif": "B12345674",              # inventado, checksum valido
        "base_10": 0, "base_4": 0, "base_21": 100.0,
        "base_total": 100.0, "iva_total": 21.0,
        "irpf_retencion": 0, "total_factura": 121.0,
        "verificacion": "OK", "tipo_documento": "FACTURA_NORMAL",
        "naturaleza_operacion": "SUJETA",
        "tramos_iva": [{"tipo": 21, "base": 100.0, "cuota": 21.0}],
        "recargo_equivalencia": 0,
        "total_factura_2": 121.0,
        "nif_margen": "B12345674", "nombre_margen": "PROVEEDOR PILOTO SL",
        "confianza_campos": {"nif": "ALTA", "fecha_expedicion": "ALTA",
                             "nº_documento": "ALTA", "base_total": "ALTA",
                             "iva_total": "ALTA", "total_factura": "ALTA"},
        "foto_origen": "sintetica.jpg", "_lector": "ensayo",
    }
    base.update(cambios)
    return base


def por_el_csv(dic):
    """El viaje REAL: como lo escribe la captura y como lo lee el orquestador."""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(dic.keys()))
    w.writeheader()
    w.writerow(dic)
    return list(csv.DictReader(io.StringIO(buf.getvalue())))[0]


def veredicto_de(fila):
    """Se llama EXACTAMENTE como lo hace orquestador.py (linea 201).

    Copiar la llamada de produccion no es un detalle: un ensayo que la invente a
    su manera prueba una cadena que no existe. Esta misma funcion, en su primera
    version, pasaba `vistos_duplicado={}` (guard_anti_duplicado hace `.add`, o
    sea que es un SET) y llamaba aparte a `calcular_veredicto_v4`, cuando
    `evaluar_fila_v4` ya devuelve el veredicto. Las dos cosas las canto el
    ensayo al ejecutarse, que es para lo que sirve ejecutar en vez de leer."""
    return motor.evaluar_fila_v4(
        fila, vistos_duplicado=set(), historico_proveedor={}, formato_cache={},
        secuencia_cache={}, maestro_proveedores={}, alta_cliente_anio=1990)


def main():
    print("=" * 72)
    print("ENSAYO: la cadena entera captura -> CSV -> motor (sin API)")
    print("=" * 72)

    print("\nA. Un JSON como el que pide el prompt llega al motor y sale veredicto")
    fila = por_el_csv(capturado())
    vered, _motivo, guards = veredicto_de(fila)
    comprobar("la cadena completa produce un veredicto, no una excepcion",
              vered in ("VERDE", "AMBAR", "ROJO"), str(vered), "P0")
    comprobar("y con una factura coherente al 21% ese veredicto no es ROJO",
              vered != "ROJO", str(vered))

    print("\nB. EL DEFECTO DEL 16-09: los campos anidados sobreviven al CSV")
    # El 5% es el caso decisivo: NO tiene campo plano (no existe base_5), asi
    # que si `tramos_iva` no sobrevive, el tramo desaparece entero y la factura
    # se evalua como si no declarara desglose.
    cinco = capturado(base_21=0, base_total=200.0, iva_total=10.0,
                      total_factura=210.0, total_factura_2=210.0,
                      tramos_iva=[{"tipo": 5, "base": 200.0, "cuota": 10.0}])
    canon_mem = FacturaCanonica(dict(cinco))
    canon_csv = FacturaCanonica(por_el_csv(cinco))
    comprobar("en memoria el tramo del 5% se ve",
              len(canon_mem.tramos()) == 1 and canon_mem.tramos()[0]["tipo"] == 5.0)
    comprobar("y DESPUES del CSV se sigue viendo (era el bug)",
              len(canon_csv.tramos()) == 1 and canon_csv.tramos()[0]["tipo"] == 5.0,
              str(canon_csv.tramos()), "P0")
    comprobar("los tramos son IDENTICOS antes y despues de serializar",
              canon_mem.tramos() == canon_csv.tramos(), severidad="P0")

    flojo = capturado(confianza_campos={"nif": "ALTA", "fecha_expedicion": "ALTA",
                                        "nº_documento": "ALTA", "base_total": "ALTA",
                                        "iva_total": "ALTA", "total_factura": "BAJA"})
    estado_mem = motor.guard_confianza_por_campo(FacturaCanonica(dict(flojo)))[0]
    estado_csv = motor.guard_confianza_por_campo(FacturaCanonica(por_el_csv(flojo)))[0]
    comprobar("una confianza BAJA se detecta en memoria",
              estado_mem == "NO_COMPROBADO", estado_mem)
    comprobar("y DESPUES del CSV tambien (antes quedaba NO_APLICA en silencio)",
              estado_csv == "NO_COMPROBADO", estado_csv, "P0")

    print("\nC. Lo que no se puede interpretar NO se inventa")
    roto = FacturaCanonica({"tramos_iva": "[{'tipo': 5, y aqui se corta"})
    comprobar("una estructura rota deja tramos vacios, no un tramo inventado",
              roto.tramos() == [], str(roto.tramos()), "P0")
    comprobar("...y conserva el valor original para que se pueda mirar",
              isinstance(roto.cruda["tramos_iva"], str))
    comprobar("una cadena que NO es estructura se queda como estaba",
              FacturaCanonica({"confianza_campos": "ALTA"}).cruda["confianza_campos"] == "ALTA")
    comprobar("un campo estructurado ausente no se inventa",
              "tramos_iva" not in FacturaCanonica({"nif": "B12345674"}).cruda)

    print("\nD. CONTROL NEGATIVO: ¿sabria este ensayo ponerse rojo?")
    original = contrato_datos.parse_estructura
    try:
        # El bug exacto, reintroducido: no interpretar el texto.
        contrato_datos.parse_estructura = lambda x: x
        perdido = FacturaCanonica(por_el_csv(cinco)).tramos()
        comprobar("sin parse_estructura, el tramo del 5% SE PIERDE otra vez",
                  perdido == [], f"devolvio {perdido}", "P0")
        conf_perdida = motor.guard_confianza_por_campo(
            FacturaCanonica(por_el_csv(flojo)))[0]
        comprobar("...y el guard de confianza vuelve a callarse (NO_APLICA)",
                  conf_perdida == "NO_APLICA", conf_perdida, "P0")
    finally:
        contrato_datos.parse_estructura = original
    comprobar("y al deshacer el sabotaje vuelve a verse",
              len(FacturaCanonica(por_el_csv(cinco)).tramos()) == 1, severidad="P0")

    fallan = [r for r in resultados if not r[1]]
    p0 = [r for r in fallan if r[3] == "P0"]
    print("\n" + "=" * 72)
    print(f"Pruebas: {len(resultados)}   en verde: {len(resultados) - len(fallan)}   "
          f"FALLAN: {len(fallan)}  (de ellas P0: {len(p0)})")
    if fallan:
        for nombre, _, detalle, sev in fallan:
            print(f"  [{sev}] {nombre}" + (f" — {detalle}" if detalle else ""))
        return 1
    print("\nLa cadena entera corre sin API, los campos anidados del prompt v2")
    print("sobreviven a la serializacion, y este ensayo sabe ponerse rojo si")
    print("dejaran de sobrevivir.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
