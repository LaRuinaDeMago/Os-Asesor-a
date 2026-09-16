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

Uso (ACTUALIZADO 16-09-2026 — nada sale sin pasar por `puerta_cloud.py`):

    export GEMINI_API_KEY="tu-clave-real"     # proveedor por defecto
    export OS_ASESORIA_CLOUD=1                # ¿puede salir algo? Por defecto NO

    # Documentos FABRICADOS (probar la cadena entera; no hace falta DPA):
    python3 captura_orquestador.py --carpeta ./fotos_prueba/ \
        --procedencia SINTETICO --salida facturas.csv

    # Documentos REALES: ademas la llave legal y el RECUENTO EXACTO del lote
    export OS_ASESORIA_DATOS_REALES=1         # declara que existe el DPA
    python3 captura_orquestador.py --carpeta /ruta/con/fotos/ \
        --procedencia REAL --confirmo-envio 30 --salida facturas.csv

SIN `--procedencia` la puerta trata los documentos como REALES y bloquea: lo
que no se ha declarado no se da por comprobado. Para ver en que estado esta
todo ahora mismo:  `python3 puerta_cloud.py`  y  `python3 modo_trabajo.py`.
"""
import argparse
import base64
import csv
import json
import os
import sys

import puerta_cloud

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


def leer_factura_gemini(path_imagen, permiso, modelo="gemini-3.1-flash-lite"):
    """Igual que leer_factura() pero con Gemini - MISMO prompt, MISMO esquema
    de salida, para que comparar Claude vs Gemini con las mismas 91 facturas
    ya conocidas sea una comparacion justa (mismo experimento, un solo lector
    distinto cada vez).

    `permiso` es OBLIGATORIO y tiene que ser el de ESTE documento: lo concede
    `puerta_cloud.Lote.consumir()`. Sin el, esta funcion no envia nada. Ver
    puerta_cloud.py para por que la garantia vive aqui y no en una convencion
    de nombres.

    REQUIERE: variable de entorno GEMINI_API_KEY, de una cuenta de PAGO
    (no la capa gratis de AI Studio - esa entrena con tus datos, confirmado
    el 28-07-2026). La capa de pago SI trae DPA, sin necesidad de pasar por
    Vertex - confirmado con los propios terminos de Google.

    EL IDENTIFICADOR DE MODELO, verificado el 16-09-2026 contra la
    documentacion oficial: `gemini-3.1-flash-lite` existe y esta vigente. Se
    comprobo a proposito, y no por escrupulo: este proyecto ya se tropezo una
    vez con un identificador inventado (`claude-sonnet-4-6`, 27-08-2026), que
    no habria fallado hasta la primera llamada real.

    Y es justo el tipo de dato que CADUCA sin avisar: los modelos se retiran.
    Si manana la API contesta con un error de modelo no encontrado, eso es lo
    PRIMERO que hay que mirar, antes de sospechar del codigo."""
    puerta_cloud.exigir_permiso(permiso, path_imagen)
    try:
        from google import genai
        from google.genai import types
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

    # CORREGIDO 16-09-2026 (encontrado en el PASO 1 real, primera ejecucion
    # de esta funcion contra la API de verdad, con la factura sintetica en
    # PDF): la extension ".pdf" no estaba en el mapa y caia en el "por
    # defecto" de abajo, asi que se enviaba como si fuera un JPEG -- Gemini
    # lo rechazo con "Unable to process input image". Una extension que no
    # reconocemos NO puede adivinarse como imagen: es el mismo "OK por
    # omision" que este proyecto prohibe en el motor, aqui aplicado a un
    # mime_type en vez de a un veredicto.
    ext = os.path.splitext(path_imagen)[1].lower().lstrip(".")
    media_type = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "pdf": "application/pdf",
    }.get(ext)
    if media_type is None:
        raise ValueError(
            f"Extension de fichero no reconocida para enviar a Gemini: '.{ext}'. "
            "Anadir aqui su mime_type real antes de adivinar uno -- ver "
            "CORREGIDO 16-09-2026 en este mismo fichero."
        )

    client = genai.Client(api_key=api_key)
    # CORREGIDO 16-09-2026, contrastado con la documentacion oficial del SDK
    # antes de la primera llamada real. Antes iba un diccionario crudo
    # {"inline_data": {...}}. La documentacion dice que los parametros pueden
    # ser dicts, asi que probablemente funcionaba -- pero no aparece en ningun
    # ejemplo, y "probablemente" no es una respuesta aceptable para la UNICA
    # linea de la que depende que manana la cadena arranque. `Part.from_bytes`
    # es la forma documentada y con ejemplo.
    #
    # NO se ha podido EJECUTAR aqui (ni el SDK instalado ni clave, y esta
    # sesion es Cloud): su primera prueba real es el PASO 1 de PENDIENTE.md,
    # con la factura sintetica. Se declara asi en vez de darlo por bueno.
    respuesta = client.models.generate_content(
        model=modelo,
        contents=[
            types.Part.from_bytes(data=imagen_bytes, mime_type=media_type),
            PROMPT_CAPTURA,
        ],
    )

    texto = respuesta.text
    texto_limpio = texto.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        datos = json.loads(texto_limpio)
    except json.JSONDecodeError:
        # CORREGIDO 16-09-2026: este mensaje llevaba `texto[:300]` (la respuesta
        # CRUDA del modelo) y la ruta del fichero. Sobre una factura real eso es
        # el nombre del proveedor, su NIF y los importes, impresos por consola --
        # y en una sesion de Remote Control la consola acaba en la transcripcion.
        # Es exactamente el riesgo que `.claude/rules/datos.md` tiene tabulado
        # ("un script peta e imprime una fila en el mensaje de error") con su
        # mitigacion: solo el TIPO, nunca el contenido. Estaba dormido porque
        # ninguna factura real ha pasado aun por aqui; habria mordido el dia uno.
        raise RuntimeError(
            f"Gemini no devolvió JSON válido (documento "
            f"{puerta_cloud.referencia_documento(path_imagen)}). La respuesta "
            f"cruda NO se incluye a proposito. NO se inventa un dato de repuesto: "
            f"esta factura va a revision manual."
        )

    datos["foto_origen"] = os.path.basename(path_imagen)
    datos["_lector"] = "gemini"
    # AÑADIDO 16-09-2026: puerta_cloud.Lote.anotar_resultado() ya existia para
    # dejar constancia de tokens/coste, pero nadie la llamaba -- el registro
    # de la primera llamada real salio con tokens_entrada/tokens_salida en
    # null. Se guardan aqui, con prefijo "_", para que leer_factura() los
    # saque y se los pase al lote; nunca llegan al motor (evaluar_fila_v4 no
    # los espera). getattr con default None: si el SDK cambia de forma, un
    # None visible es mejor que un fallo silencioso o un 0 inventado.
    uso = getattr(respuesta, "usage_metadata", None)
    datos["_tokens_entrada"] = getattr(uso, "prompt_token_count", None)
    datos["_tokens_salida"] = getattr(uso, "candidates_token_count", None)
    return datos


def leer_factura(path_imagen, lote, modelo=None, proveedor="gemini"):
    """Punto de entrada unico: proveedor='claude' o 'gemini'. Mismo prompt,
    mismo esquema de salida en los dos casos - lo unico que cambia es quien lee.

    `lote` es la autorizacion de puerta_cloud. Se pide permiso para ESTE
    documento antes de tocar nada; si la puerta dice que no, se lanza
    SalidaBloqueada y no se envia un solo byte. `lote=None` tambien bloquea:
    el que se olvide de pasarlo no se salta la puerta, choca con ella."""
    if lote is None:
        raise puerta_cloud.SalidaBloqueada(
            "Falta el lote de puerta_cloud. Nada sale de aqui sin autorizacion: "
            "ver `python3 puerta_cloud.py` para el estado de la puerta."
        )
    permiso = lote.consumir(path_imagen)
    if proveedor == "gemini":
        datos = leer_factura_gemini(path_imagen, permiso)
    else:
        # modelo=None significa "el que tenga por defecto la rama de Claude", no None.
        datos = (_leer_factura_claude(path_imagen, permiso, modelo) if modelo
                 else _leer_factura_claude(path_imagen, permiso))
    # AÑADIDO 16-09-2026: hasta hoy nadie llamaba a anotar_resultado() -- el
    # registro de la primera llamada real salio con tokens/coste en null a
    # pesar de que el mecanismo ya existia. Los campos "_tokens_*" son un
    # canal interno entre las funciones de lectura y este punto unico: no
    # deben llegar nunca a evaluar_fila_v4 ni al CSV, por eso se sacan con
    # pop() antes de devolver `datos`.
    lote.anotar_resultado(
        path_imagen,
        tokens_entrada=datos.pop("_tokens_entrada", None),
        tokens_salida=datos.pop("_tokens_salida", None),
    )
    return datos


def _leer_factura_claude(path_imagen, permiso, modelo="claude-sonnet-5"):
    """Llama a la API de Claude con la imagen y devuelve un dict con los
    campos ya parseados, listos para evaluar_fila_v4(). Lanza una excepcion
    clara si la API no responde JSON valido - NUNCA devuelve datos a medias
    silenciosamente (mismo principio que el resto del motor: nunca ocultar
    un fallo de lectura como si fuera un dato bueno).

    `permiso` es OBLIGATORIO, igual que en la rama de Gemini."""
    puerta_cloud.exigir_permiso(permiso, path_imagen)
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

    # CORREGIDO 16-09-2026: mismo bug que en leer_factura_gemini() (misma
    # logica duplicada en dos ficheros -- ver diag_logica_duplicada.py), y el
    # mismo motivo. NO arregla el problema mas profundo de esta rama: el
    # bloque de contenido de abajo lleva "type": "image" fijo, y la API de
    # Claude exige "type": "document" para un PDF -- eso sigue sin tocar
    # porque esta ruta (4, ver modo_trabajo.py) es hoy inalcanzable sin
    # ANTHROPIC_API_KEY ni DPA. Si algun dia se activa, revisar esto primero.
    ext = os.path.splitext(path_imagen)[1].lower().lstrip(".")
    media_type = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "pdf": "application/pdf",
    }.get(ext)
    if media_type is None:
        raise ValueError(
            f"Extension de fichero no reconocida para enviar a Claude: '.{ext}'. "
            "Anadir aqui su mime_type real antes de adivinar uno -- ver "
            "CORREGIDO 16-09-2026 en este mismo fichero."
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
    except json.JSONDecodeError:
        # Misma correccion que en la rama de Gemini (16-09-2026), y el mismo
        # motivo: el mensaje llevaba la respuesta cruda y la ruta.
        raise RuntimeError(
            f"La API no devolvió JSON válido (documento "
            f"{puerta_cloud.referencia_documento(path_imagen)}). La respuesta "
            f"cruda NO se incluye a proposito. NO se inventa un dato de repuesto - "
            f"esta factura debe marcarse para revisión manual, no procesarse a ciegas."
        )

    datos["foto_origen"] = os.path.basename(path_imagen)
    datos["_lector"] = "claude"
    # AÑADIDO 16-09-2026: mismo enganche que en leer_factura_gemini() para que
    # anotar_resultado() reciba tokens reales en vez de null.
    uso = getattr(respuesta, "usage", None)
    datos["_tokens_entrada"] = getattr(uso, "input_tokens", None)
    datos["_tokens_salida"] = getattr(uso, "output_tokens", None)
    return datos


def procesar_carpeta(carpeta, path_salida, proveedor="gemini",
                     procedencia=None, confirmacion=None):
    """Lee todas las imagenes de una carpeta y escribe un CSV con los campos
    ya estructurados - listo para pasar directamente a orquestador.py.

    LO QUE SALE POR CONSOLA (corregido 16-09-2026): recuentos, huellas y el
    TIPO de cada error. Nunca el nombre del fichero, ni el del proveedor, ni un
    importe, ni el mensaje de una excepcion. Antes de hoy imprimia las cuatro
    cosas, y el CSV -- que si lleva todo eso -- se queda en el disco, que es
    donde debe estar."""
    extensiones = (".jpg", ".jpeg", ".png")
    archivos = sorted(f for f in os.listdir(carpeta) if f.lower().endswith(extensiones))
    print(f"Encontradas {len(archivos)} imagenes - leyendo con {proveedor}")

    lote = puerta_cloud.abrir_lote(len(archivos), procedencia, proveedor,
                                   confirmacion=confirmacion)
    if not lote.permitido:
        print(f"\nLA PUERTA HA BLOQUEADO ESTE LOTE: {lote.motivo}")
        print("Nada se ha enviado. `python3 puerta_cloud.py` explica el estado.")
        return 1

    filas = []
    errores = {}
    for i, nombre in enumerate(archivos, 1):
        path = os.path.join(carpeta, nombre)
        huella = puerta_cloud.referencia_documento(path)
        try:
            datos = leer_factura(path, lote, proveedor=proveedor)
            filas.append(datos)
            estado = datos.get("verificacion", "?")
            print(f"  OK ({estado}): {i}/{len(archivos)}  doc {huella}")
        except Exception as e:
            # Solo el TIPO de la excepcion, nunca str(e): el mensaje arrastra
            # datos (.claude/rules/datos.md, tabla de riesgos).
            tipo = type(e).__name__
            errores[tipo] = errores.get(tipo, 0) + 1
            print(f"  ERROR ({tipo}): {i}/{len(archivos)}  doc {huella}")

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
        print(f"\nEscrito {path_salida}: {len(filas)} facturas leídas, "
              f"{sum(errores.values())} errores")
    if errores:
        print("\nFacturas que necesitan revisión manual (no se procesaron),")
        print("por TIPO de error — el detalle esta en el CSV, que no sale de aqui:")
        for tipo, cuantas in sorted(errores.items()):
            print(f"  - {tipo}: {cuantas}")
    # Codigo de salida: 0 SOLO si no fallo ninguna. Antes de hoy devolvia
    # siempre exito, asi que una corrida en la que fallaron las 30 facturas
    # terminaba con codigo 0 -- un OK que significa "no he podido hacer nada",
    # que es el mismo falso verde que el motor tiene prohibido dar. Misma regla
    # que audit_project.py: si algo falla, se nota en el codigo de salida.
    return 1 if errores else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Captura automática de facturas (foto -> datos)")
    parser.add_argument("--imagen", help="Una sola imagen a procesar")
    parser.add_argument("--carpeta", help="Carpeta con varias imágenes a procesar")
    parser.add_argument("--salida", default="facturas_capturadas.csv")
    parser.add_argument("--proveedor", choices=["gemini", "claude"], default="gemini",
                         help="Qué modelo lee la factura (mismo prompt/esquema en los dos)")
    parser.add_argument("--procedencia", choices=[puerta_cloud.SINTETICO, puerta_cloud.REAL],
                         default=None,
                         help="Qué son estos documentos. Si no se declara, la puerta "
                              "los trata como REAL (lo no comprobado no es un OK)")
    parser.add_argument("--confirmo-envio", type=int, default=None, dest="confirmo_envio",
                         help="Solo para --procedencia REAL: el NUMERO EXACTO de "
                              "documentos que van a salir. Tiene que coincidir con los "
                              "que se encuentren; si no, se bloquea. Es un numero y no "
                              "un 'si' a proposito: obliga a mirar cuantos son")
    args = parser.parse_args()

    if args.imagen:
        lote = puerta_cloud.abrir_lote(1, args.procedencia, args.proveedor,
                                       confirmacion=args.confirmo_envio)
        if not lote.permitido:
            print(f"LA PUERTA HA BLOQUEADO ESTE ENVIO: {lote.motivo}")
            print("Nada se ha enviado. `python3 puerta_cloud.py` explica el estado.")
            sys.exit(1)
        datos = leer_factura(args.imagen, lote, proveedor=args.proveedor)
        print(json.dumps(datos, ensure_ascii=False, indent=2))
    elif args.carpeta:
        sys.exit(procesar_carpeta(args.carpeta, args.salida, proveedor=args.proveedor,
                                  procedencia=args.procedencia,
                                  confirmacion=args.confirmo_envio))
    else:
        parser.print_help()
