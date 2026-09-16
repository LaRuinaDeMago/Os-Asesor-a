#!/usr/bin/env python3
"""crear_factura_sintetica.py — una factura FABRICADA para ensayar la cadena real.

PARA QUE SIRVE, Y POR QUE VALE LA PENA
----------------------------------------
Desde el 16-09-2026 la cadena foto -> Gemini -> JSON -> motor se puede ejercitar
ENTERA sin DPA y sin riesgo legal, siempre que el documento sea SINTETICO
declarado (`puerta_cloud.py`). Lo que faltaba era el documento.

Esto lo fabrica. Y lo importante no es que exista una imagen: es que se conoce
la VERDAD de antemano. Al pasarla por Gemini se puede comparar campo a campo lo
que devuelve contra lo que la factura dice de verdad -- que es una medicion, no
un "parece que ha ido bien". Con una factura real eso no se puede hacer sin
teclear los datos a mano.

LOS CASOS QUE LLEVA DENTRO, ELEGIDOS A PROPOSITO
--------------------------------------------------
No es una factura cualquiera: cada rasgo ejercita algo que HOY no esta probado
contra un modelo real.

  · Un tramo al 5% Y otro al 21% (factura mixta). El 5% es el tipo que NO tiene
    campo plano equivalente: si `tramos_iva` no llega bien, desaparece. Es
    exactamente el defecto que se encontro y arreglo el 16-09-2026 -- este
    documento es su prueba contra un modelo de verdad.
  · El TOTAL impreso DOS veces, en sitios distintos (cuadro de importes y pie).
    Ejercita `total_factura_2` y el guard de doble lectura, que nunca ha visto
    un documento real.
  · El NIF del emisor en la cabecera Y en el pie. Ejercita `nif_margen` y la
    triangulacion de identidad, igual de virgen.
  · Un numero de documento con barra y punto (`A26/7.612`), que es donde los
    OCR se equivocan.

QUE NO LLEVA, Y ES DELIBERADO
-------------------------------
Ni un dato real. La razon social es inventada y el NIF se COMPONE aqui con su
digito de control calculado, no se escribe como literal: un literal con forma de
NIF en el codigo haria saltar `scripts/privacy_scan.py`, y engordar su lista
blanca para un fichero de pruebas seria debilitar la barrera por comodidad
(mismo razonamiento que ya esta escrito en `test_privacidad.py`).

Por eso el HTML que genera NO se versiona (`.gitignore`): se crea cuando hace
falta. Lo que vive en el repositorio es la receta, que no contiene ningun NIF.

USO
-----
    python crear_factura_sintetica.py

Escribe `factura_sintetica_01.html` y imprime la verdad conocida. Abrelo en el
navegador y guardalo como PDF o hazle una captura de pantalla: eso es lo que se
le pasa a la captura, con `--procedencia SINTETICO`.
"""
import os
import sys

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SALIDA = "factura_sintetica_01.html"

#: Los numeros de la factura. Cuadran a proposito: base x tipo = cuota, y la
#: suma da el total. Si el motor dijera ROJO sobre esto, el problema seria del
#: motor o de la lectura, nunca del documento.
BASE_5, TIPO_5 = 200.00, 5
BASE_21, TIPO_21 = 1000.00, 21
CUOTA_5 = round(BASE_5 * TIPO_5 / 100, 2)       # 10,00
CUOTA_21 = round(BASE_21 * TIPO_21 / 100, 2)    # 210,00
BASE_TOTAL = round(BASE_5 + BASE_21, 2)         # 1.200,00
IVA_TOTAL = round(CUOTA_5 + CUOTA_21, 2)        # 220,00
TOTAL = round(BASE_TOTAL + IVA_TOTAL, 2)        # 1.420,00

NUM_DOCUMENTO = "A26/7.612"
FECHA = "26/03/2026"
EMISOR = "SUMINISTROS EJEMPLO FICTICIO SL"
DIRECCION = "Calle Inventada 00, 00000 Ciudad Ejemplo"


#: Letras de organizacion cuyo digito de control es NUMERICO. Las que lo
#: tienen alfabetico (P, Q, S, K, N, R, W) se rechazan abajo en vez de
#: componerse mal en silencio: un NIF sintetico invalido haria que el motor
#: diera ROJO por el documento y no por lo que se quiere medir.
LETRAS_CONTROL_NUMERICO = "ABEH"


def nif_sintetico(digitos="9876543", letra="B"):
    """CIF inventado, con digito de control CORRECTO, compuesto en ejecucion.

    Compuesto y no escrito como literal: ver el docstring del modulo. Por
    defecto devuelve el mismo CIF de siempre (letra B, sociedad limitada), asi
    que quien ya lo llamaba sin argumentos sigue recibiendo lo mismo.

    Parametrizado el 16-09-2026 para que `crear_muestras_sinteticas.py` pueda
    fabricar VARIOS emisores distintos sin copiar aqui el algoritmo del digito
    de control -- que es justo la clase de duplicado que este proyecto ya ha
    pagado dos veces (mismo bug en dos sitios, PENDIENTE.md 1.A).

    El resultado se verifica contra `nif_check.valida_nif`, el validador del
    propio proyecto: si algun dia cambia uno de los dos, salta aqui y no en
    una comparacion de campos donde pareceria un fallo del modelo.
    """
    letra = letra.upper()
    if letra not in LETRAS_CONTROL_NUMERICO:
        raise ValueError(
            f"letra de organizacion {letra!r}: esta funcion solo compone las "
            f"de control NUMERICO ({LETRAS_CONTROL_NUMERICO}). Con control "
            f"alfabetico el digito se calcula distinto y saldria un NIF falso.")
    if len(digitos) != 7 or not digitos.isdigit():
        raise ValueError(f"se esperan 7 digitos, recibido {digitos!r}")

    pares = sum(int(digitos[i]) for i in (1, 3, 5))
    impares = sum((lambda x: x // 10 + x % 10)(int(digitos[i]) * 2)
                  for i in (0, 2, 4, 6))
    control = (10 - (pares + impares) % 10) % 10
    nif = letra + digitos + str(control)

    import nif_check
    ok, _tipo, motivo = nif_check.valida_nif(nif)
    if not ok:
        raise AssertionError(
            f"el CIF compuesto no pasa el validador del proyecto: {motivo}. "
            f"O el algoritmo de aqui o el de nif_check.py ha cambiado.")
    return nif


def num_es(x):
    """Formato espanol SIN moneda: 1.234,56 — como lo imprime una factura.

    Separado de `eur()` el 16-09-2026 porque en un cuadro de importes el simbolo
    va en la cabecera de la columna, no en cada celda. Tener las dos formas
    evita que `crear_muestras_sinteticas.py` reescriba el mismo formateo."""
    entero, dec = f"{x:.2f}".split(".")
    miles = ""
    while len(entero) > 3:
        miles = "." + entero[-3:] + miles
        entero = entero[:-3]
    return f"{entero}{miles},{dec}"


def eur(x):
    """Formato espanol con moneda: 1.234,56 EUR."""
    return num_es(x) + " EUR"


HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><title>Factura {num}</title>
<style>
 body {{ font-family: Arial, Helvetica, sans-serif; margin: 40px; color: #111; }}
 .aviso {{ background: #ffe9e9; border: 2px solid #c00; color: #900;
           padding: 10px; font-weight: bold; margin-bottom: 26px; }}
 .cab {{ display: flex; justify-content: space-between; align-items: flex-start; }}
 h1 {{ font-size: 20px; margin: 0 0 4px 0; }}
 table {{ border-collapse: collapse; width: 100%; margin-top: 26px; }}
 th, td {{ border: 1px solid #999; padding: 7px 10px; font-size: 14px; }}
 th {{ background: #eee; text-align: left; }}
 td.n {{ text-align: right; }}
 .totales {{ margin-top: 22px; width: 340px; margin-left: auto; }}
 .totales td {{ border: none; padding: 4px 8px; }}
 .grantotal td {{ border-top: 2px solid #111; font-weight: bold; font-size: 16px; }}
 .pie {{ margin-top: 48px; border-top: 1px solid #999; padding-top: 10px;
         font-size: 12px; color: #444; }}
</style></head><body>

<div class="aviso">DOCUMENTO FABRICADO PARA PRUEBAS — no corresponde a ninguna
empresa ni operacion real. Datos inventados.</div>

<div class="cab">
  <div>
    <h1>{emisor}</h1>
    <div>NIF: {nif}</div>
    <div>{direccion}</div>
  </div>
  <div style="text-align:right">
    <div><strong>FACTURA</strong></div>
    <div>Numero: {num}</div>
    <div>Fecha: {fecha}</div>
  </div>
</div>

<table>
  <tr><th>Concepto</th><th>Base imponible</th><th>% IVA</th><th>Cuota IVA</th></tr>
  <tr><td>Material de oficina</td><td class="n">{b21}</td>
      <td class="n">21%</td><td class="n">{c21}</td></tr>
  <tr><td>Producto a tipo reducido</td><td class="n">{b5}</td>
      <td class="n">5%</td><td class="n">{c5}</td></tr>
</table>

<table class="totales">
  <tr><td>Base imponible total</td><td class="n">{btot}</td></tr>
  <tr><td>Total IVA</td><td class="n">{ivatot}</td></tr>
  <tr class="grantotal"><td>TOTAL FACTURA</td><td class="n">{total}</td></tr>
</table>

<div class="pie">
  {emisor} &nbsp;·&nbsp; NIF {nif} &nbsp;·&nbsp; {direccion}<br>
  Total a pagar: {total} &nbsp;·&nbsp; Forma de pago: transferencia
</div>

</body></html>
"""


def main():
    nif = nif_sintetico()
    destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), SALIDA)
    with open(destino, "w", encoding="utf-8") as f:
        f.write(HTML.format(
            emisor=EMISOR, nif=nif, direccion=DIRECCION, num=NUM_DOCUMENTO,
            fecha=FECHA, b21=eur(BASE_21), c21=eur(CUOTA_21),
            b5=eur(BASE_5), c5=eur(CUOTA_5), btot=eur(BASE_TOTAL),
            ivatot=eur(IVA_TOTAL), total=eur(TOTAL)))

    print("=" * 68)
    print("FACTURA SINTETICA CREADA")
    print("=" * 68)
    print(f"  fichero: {SALIDA}")
    print("  Abrelo en el navegador y guardalo como PDF o hazle una captura.")
    print()
    print("  VERDAD CONOCIDA — esto es lo que la factura dice de verdad, para")
    print("  comparar campo a campo contra lo que devuelva el modelo:")
    print(f"    nº_documento    {NUM_DOCUMENTO}")
    print(f"    fecha           2026-03-26")
    print(f"    nif             {nif}   (inventado, digito de control valido)")
    print(f"    tramos_iva      [{{tipo:21, base:{BASE_21}, cuota:{CUOTA_21}}},")
    print(f"                     {{tipo:5,  base:{BASE_5},  cuota:{CUOTA_5}}}]")
    print(f"    base_total      {BASE_TOTAL}")
    print(f"    iva_total       {IVA_TOTAL}")
    print(f"    total_factura   {TOTAL}")
    print()
    print("  LO QUE HAY QUE MIRAR EN LA RESPUESTA, y por que:")
    print("    1. ¿Viene `tramos_iva` con los DOS tramos, y el de 5% entre")
    print("       ellos? El 5% no tiene campo plano: si no llega por ahi, se")
    print("       pierde. Es el defecto que se arreglo el 16-09.")
    print("    2. ¿`total_factura_2` trae el total del PIE, o lo ha copiado")
    print("       del cuadro? Si lo copia, la doble lectura es un espejo y no")
    print("       vale nada.")
    print("    3. ¿`nif_margen` trae el NIF del pie? Misma pregunta.")
    print("    4. ¿El numero sale como A26/7.612, con la barra y el punto?")
    print()
    print("  Y como pasarla por la cadena (la puerta la deja salir por ser")
    print("  SINTETICA declarada, sin necesidad de DPA):")
    print("      set OS_ASESORIA_CLOUD=1        (Windows)")
    print("      python captura_orquestador.py --imagen factura.png \\")
    print("             --procedencia SINTETICO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
