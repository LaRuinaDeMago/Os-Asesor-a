#!/usr/bin/env python3
"""
CAPTURA — la pieza que faltaba: foto -> datos estructurados -> motor.

Llama a la API de Claude (vision) para leer una factura y devuelve exactamente
los campos que evaluar_fila_v4() espera, listos para pasar al motor sin
transformación intermedia.

REQUIERE: variable de entorno ANTHROPIC_API_KEY con una clave de API real,
de una cuenta con DPA (no Free/Pro de consumo - ver la decision de
infraestructura documentada en README.md). Esta clave NUNCA se pega en un
chat - se configura en el propio entorno donde corra esto (Claude Code,
tu ordenador), nunca en una conversacion.

Uso:
    export ANTHROPIC_API_KEY="tu-clave-real"
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
  "tipo_documento": "FACTURA_NORMAL, ABONO, o ARRENDAMIENTO segun lo que indique el documento"
}

IMPORTANTE: si algun campo no se puede leer con seguridad, pon el valor mas
probable Y marca "verificacion": "DUDA" - nunca inventes un valor sin
declarar la duda. No expliques tu razonamiento, solo el JSON."""


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


def leer_factura(path_imagen, modelo="claude-sonnet-4-6", proveedor="claude"):
    """Punto de entrada unico: proveedor='claude' o 'gemini'. Mismo prompt,
    mismo esquema de salida en los dos casos - lo unico que cambia es quien lee."""
    if proveedor == "gemini":
        return leer_factura_gemini(path_imagen)
    return _leer_factura_claude(path_imagen, modelo)


def _leer_factura_claude(path_imagen, modelo="claude-sonnet-4-6"):
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


def procesar_carpeta(carpeta, path_salida, proveedor="claude"):
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
        campos = list(filas[0].keys())
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
    parser.add_argument("--proveedor", choices=["claude", "gemini"], default="claude",
                         help="Qué modelo lee la factura (mismo prompt/esquema en los dos)")
    args = parser.parse_args()

    if args.imagen:
        datos = leer_factura(args.imagen, proveedor=args.proveedor)
        print(json.dumps(datos, ensure_ascii=False, indent=2))
    elif args.carpeta:
        procesar_carpeta(args.carpeta, args.salida, proveedor=args.proveedor)
    else:
        parser.print_help()
