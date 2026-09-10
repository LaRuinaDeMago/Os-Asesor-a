#!/usr/bin/env python3
"""
CAPTURA — la pieza que faltaba: foto -> datos estructurados -> motor.

Llama a la API de vision (Gemini por defecto; Claude como alternativa
explicita con --proveedor claude) para leer una factura y devuelve exactamente
los campos que evaluar_fila_v4() espera, listos para pasar al motor sin
transformación intermedia.

REQUIERE: GEMINI_API_KEY (por defecto) o ANTHROPIC_API_KEY (--proveedor claude),
de una cuenta con DPA (no Free/Pro de consumo - ver la decision de
infraestructura documentada en .claude/rules/datos.md). Esta clave NUNCA se
pega en un chat - se configura en el propio entorno donde corra esto (Claude
Code, tu ordenador), nunca en una conversacion.

Uso:
    export GEMINI_API_KEY="tu-clave-real"     # proveedor por defecto
    # export ANTHROPIC_API_KEY="..."        # solo si se usa --proveedor claude
    python3 captura_orquestador.py --imagen factura.jpg
    python3 captura_orquestador.py --carpeta /ruta/con/fotos/ --salida facturas.csv
"""
import argparse
import base64
import csv
import json
import os
import sys

PROMPT_CAPTURA = """Eres un lector de facturas para un despacho de asesoria fiscal español.
Lee la imagen adjunta (una factura de un proveedor) y devuelve EXCLUSIVAMENTE
un objeto JSON con estos campos exactos, sin texto adicional antes ni despues:

{
  "fecha_expedicion": "YYYY-MM-DD",
  "nº_documento": "el numero de factura tal cual aparece impreso, sin inventar formato",
  "proveedor": "razon social del EMISOR de la factura, tal cual aparece",
  "nif": "NIF/CIF del emisor, sin espacios ni guiones",
  "base_10": "base imponible al tipo 10%, 0 si no aplica, como numero",
  "base_4": "base imponible al tipo 4%, 0 si no aplica, como numero",
  "base_21": "base imponible al tipo 21%, 0 si no aplica, como numero",
  "base_total": "suma de las 3 bases anteriores, como numero",
  "iva_total": "cuota total de IVA de la factura, como numero",
  "irpf_retencion": "retencion de IRPF si aparece, en NEGATIVO si existe, 0 si no aplica",
  "total_factura": "importe total de la factura, como numero (negativo si es un abono)",
  "verificacion": "OK si estas seguro de la lectura, DUDA si algun caracter critico (NIF o importe) era ambiguo",
  "tipo_documento": "FACTURA_NORMAL, ABONO, o ARRENDAMIENTO segun lo que indique el documento",

  "naturaleza_operacion": "SUJETA si la factura repercute IVA normal. EXENTA si dice exenta o cita el art. 20 LIVA. NO_SUJETA si lo indica. INTRACOMUNITARIA si es una operacion intracomunitaria sin IVA. INVERSION_SUJETO_PASIVO si menciona inversion del sujeto pasivo o el art. 84. Si no hay ninguna indicacion, SUJETA",
  "tramos_iva": "lista de los tramos tal como aparecen: [{\"tipo\": 21, \"base\": 100.0, \"cuota\": 21.0}]. Incluye CUALQUIER tipo que veas (0, 4, 5, 10, 21), no solo los tres habituales. Lista vacia si no hay desglose",
  "recargo_equivalencia": "importe del recargo de equivalencia si la factura lo desglosa, 0 si no aparece",

  "total_factura_2": "el importe total leido de una SEGUNDA ubicacion del documento distinta de la anterior (la casilla de 'total a pagar', el pie, el recuadro de pago). Si el total solo aparece una vez en todo el documento, deja este campo vacio - NO copies el mismo valor",
  "nif_margen": "NIF del emisor leido de OTRA ubicacion distinta de la cabecera (pie de pagina, lateral, sello). Vacio si solo aparece una vez - NO copies el de cabecera",
  "nombre_margen": "razon social del emisor leida de esa segunda ubicacion. Vacio si solo aparece una vez",

  "confianza_campos": "objeto con la confianza de CADA campo critico por separado: {\"nif\": \"ALTA\", \"fecha_expedicion\": \"ALTA\", \"n\u00ba_documento\": \"ALTA\", \"base_total\": \"ALTA\", \"iva_total\": \"ALTA\", \"total_factura\": \"ALTA\"}. Usa ALTA solo si el campo se lee sin ninguna ambiguedad; MEDIA si es legible pero con dudas; BAJA si has tenido que inferirlo"
}

IMPORTANTE: si algun campo no se puede leer con seguridad, pon el valor mas
probable Y marca "verificacion": "DUDA" - nunca inventes un valor sin
declarar la duda. No expliques tu razonamiento, solo el JSON.

CRITICO para los tres campos de SEGUNDA LECTURA (total_factura_2, nif_margen,
nombre_margen): su valor esta en que sean una lectura INDEPENDIENTE de otro
sitio del papel. Si copias ahi el mismo valor que ya pusiste arriba, destruyes
la comprobacion entera y es peor que dejarlo vacio. Vacio es una respuesta
correcta y esperada: muchas facturas solo traen el dato una vez."""

# ------------------------------------------------------------------------
# NOTA DE ESTADO (20-08-2026) — el prompt de arriba es la v2 y NO se ha
# probado nunca contra una factura real, porque hasta hoy no habia forma de
# hacerlo (falta el DPA). Los campos anadidos son ADITIVOS: si el modelo no los
# devuelve, el contrato los marca MISSING y los tres guards que los consumen se
# declaran NO_APLICA, o sea que el comportamiento es identico al de la v1.
#
# QUE HAY QUE COMPROBAR EN LA PRIMERA CAPTURA REAL, en este orden:
#   1. Que los campos de SIEMPRE se siguen leyendo igual de bien. Pedir mas
#      campos puede diluir la atencion del modelo sobre los que ya funcionaban:
#      eso se llama dilucion de prompt y es el riesgo real de este cambio.
#   2. En que FRACCION de facturas reales aparece de verdad el total dos veces.
#      Si es baja, la doble lectura protege menos de lo que promete.
#   3. Si el modelo copia el mismo valor en total_factura_2 en vez de dejarlo
#      vacio. Si lo hace, la comprobacion es un espejo y no vale nada.
# ------------------------------------------------------------------------


def leer_factura_gemini(path_imagen, modelo="gemini-3.1-flash-lite"):
    """Igual que leer_factura() pero con Gemini - MISMO prompt, MISMO esquema
    de salida, para que comparar Claude vs Gemini con las mismas 91 facturas
    ya conocidas sea una comparacion justa (mismo experimento, un solo lector
    distinto cada vez).

    REQUIERE: variable de entorno GEMINI_API_KEY, de una cuenta de PAGO
    (no la capa gratis de AI Studio - esa entrena con tus datos, confirmado
    el 28-07-2026). La capa de pago SI trae DPA, sin necesidad de pasar por
    Vertex - confirmado con los propios terminos de Google."""
    try:
        from google import genai
    except ImportError:
        raise RuntimeError(
            "Falta el paquete 'google-genai' (pip install google-genai --break-system-packages). "
            "No se ha instalado ni probado en este entorno - falta hacerlo en el "
            "entorno real donde esto vaya a correr."
        )

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY no está configurada. Igual que con Anthropic: se pone "
            "como variable de entorno en TU máquina - nunca se escribe en este "
            "script ni se pega en una conversación de chat. Y confirma que la "
            "cuenta es de PAGO (con facturación activada), no la capa gratis."
        )

    with open(path_imagen, "rb") as f:
        imagen_bytes = f.read()

    ext = os.path.splitext(path_imagen)[1].lower()
    media_type = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}.get(
        ext.lstrip("."), "image/jpeg"
    )

    client = genai.Client(api_key=api_key)
    respuesta = client.models.generate_content(
        model=modelo,
        contents=[
            {"inline_data": {"mime_type": media_type, "data": imagen_bytes}},
            PROMPT_CAPTURA,
        ],
    )

    texto = respuesta.text
    texto_limpio = texto.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        datos = json.loads(texto_limpio)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Gemini no devolvió JSON válido para {path_imagen}. Respuesta cruda: "
            f"{texto[:300]}... Error: {e}. NO se inventa un dato de repuesto."
        )

    datos["foto_origen"] = os.path.basename(path_imagen)
    datos["_lector"] = "gemini"
    return datos


def leer_factura(path_imagen, modelo=None, proveedor="gemini"):
    """Punto de entrada unico: proveedor='claude' o 'gemini'. Mismo prompt,
    mismo esquema de salida en los dos casos - lo unico que cambia es quien lee."""
    if proveedor == "gemini":
        return leer_factura_gemini(path_imagen)
    # modelo=None significa "el que tenga por defecto la rama de Claude", no None.
    return _leer_factura_claude(path_imagen, modelo) if modelo else _leer_factura_claude(path_imagen)


def _leer_factura_claude(path_imagen, modelo="claude-sonnet-5"):
    """Llama a la API de Claude con la imagen y devuelve un dict con los
    campos ya parseados, listos para evaluar_fila_v4(). Lanza una excepcion
    clara si la API no responde JSON valido - NUNCA devuelve datos a medias
    silenciosamente (mismo principio que el resto del motor: nunca ocultar
    un fallo de lectura como si fuera un dato bueno)."""
    try:
        import anthropic
    except ImportError:
        raise RuntimeError(
            "Falta el paquete 'anthropic' (pip install anthropic --break-system-packages). "
            "No se ha instalado ni probado en este entorno - falta hacerlo en el "
            "entorno real donde esto vaya a correr."
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY no está configurada. Esta clave se pone como variable "
            "de entorno en TU máquina/Claude Code - nunca se escribe dentro de este "
            "script ni se pega en una conversación de chat."
        )

    with open(path_imagen, "rb") as f:
        imagen_b64 = base64.standard_b64encode(f.read()).decode("utf-8")

    ext = os.path.splitext(path_imagen)[1].lower()
    media_type = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}.get(
        ext.lstrip("."), "image/jpeg"
    )

    client = anthropic.Anthropic(api_key=api_key)
    respuesta = client.messages.create(
        model=modelo,
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": imagen_b64}},
                    {"type": "text", "text": PROMPT_CAPTURA},
                ],
            }
        ],
    )

    texto = "".join(b.text for b in respuesta.content if b.type == "text")
    texto_limpio = texto.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        datos = json.loads(texto_limpio)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"La API no devolvió JSON válido para {path_imagen}. Respuesta cruda: "
            f"{texto[:300]}... Error: {e}. NO se inventa un dato de repuesto - "
            f"esta factura debe marcarse para revisión manual, no procesarse a ciegas."
        )

    datos["foto_origen"] = os.path.basename(path_imagen)
    datos["_lector"] = "claude"
    return datos


def procesar_carpeta(carpeta, path_salida, proveedor="gemini"):
    """Lee todas las imagenes de una carpeta y escribe un CSV con los campos
    ya estructurados - listo para pasar directamente a orquestador.py."""
    extensiones = (".jpg", ".jpeg", ".png")
    archivos = sorted(f for f in os.listdir(carpeta) if f.lower().endswith(extensiones))
    print(f"Encontradas {len(archivos)} imagenes en {carpeta} - leyendo con {proveedor}")

    filas = []
    errores = []
    for nombre in archivos:
        path = os.path.join(carpeta, nombre)
        try:
            datos = leer_factura(path, proveedor=proveedor)
            filas.append(datos)
            estado = datos.get("verificacion", "?")
            print(f"  OK ({estado}): {nombre} -> {datos.get('proveedor','?')} / {datos.get('total_factura','?')}")
        except Exception as e:
            errores.append((nombre, str(e)))
            print(f"  ERROR: {nombre} -> {e}")

    if filas:
        # CORREGIDO 26-08-2026 (auditoria propia). Usaba solo las claves de la
        # PRIMERA factura como cabecera. El modelo no siempre devuelve el
        # mismo conjunto de claves (un campo opcional que unas veces omite y
        # otras no, ej. tramos_iva o confianza_campos): en cuanto una factura
        # posterior traia una clave que la primera no tenia, csv.DictWriter
        # reventaba con ValueError y se perdia el CSV de TODA la carpeta -
        # incluidas las facturas ya leidas bien. Union de claves de todas las
        # filas, en orden de aparicion, para que una factura distinta no se
        # lleve por delante a las demas.
        campos = []
        vistos = set()
        for fila in filas:
            for clave in fila.keys():
                if clave not in vistos:
                    vistos.add(clave)
                    campos.append(clave)
        with open(path_salida, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=campos)
            w.writeheader()
            w.writerows(filas)
        print(f"\nEscrito {path_salida}: {len(filas)} facturas leídas, {len(errores)} errores")
    if errores:
        print("\nFacturas que necesitan revisión manual (no se procesaron):")
        for nombre, err in errores:
            print(f"  - {nombre}: {err}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Captura automática de facturas (foto -> datos)")
    parser.add_argument("--imagen", help="Una sola imagen a procesar")
    parser.add_argument("--carpeta", help="Carpeta con varias imágenes a procesar")
    parser.add_argument("--salida", default="facturas_capturadas.csv")
    parser.add_argument("--proveedor", choices=["gemini", "claude"], default="gemini",
                         help="Qué modelo lee la factura (mismo prompt/esquema en los dos)")
    args = parser.parse_args()

    if args.imagen:
        datos = leer_factura(args.imagen, proveedor=args.proveedor)
        print(json.dumps(datos, ensure_ascii=False, indent=2))
    elif args.carpeta:
        procesar_carpeta(args.carpeta, args.salida, proveedor=args.proveedor)
    else:
        parser.print_help()
