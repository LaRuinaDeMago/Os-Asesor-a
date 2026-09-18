"""
SUITE DE PRUEBAS — check_salida_unica_cloud() de audit_project.py

Hasta el 17-09-2026 este auditor -- el que garantiza que NINGUN dato sale
hacia una IA sin pasar por puerta_cloud.py -- no tenia NI UNA sola prueba
permanente, pese a que su propio docstring afirma "probado con el defecto
reintroducido a proposito". Esa prueba fue manual, una vez, y nunca quedo
capturada como regresion.

Se encontro ademas un hueco real (no hipotetico) mientras se revisaba el
proyecto a peticion de Diego: `_llamadas_api_ia()` solo reconocia
`generate_content` (Gemini) y `messages.create` (Anthropic) -- confirmado
por introspeccion directa de los dos SDK instalados, que exponen bastantes
mas metodos que de verdad envian contenido (`generate_content_stream`,
`count_tokens`, `embed_content` en Gemini; `stream`, `count_tokens`,
`parse`, `messages.batches.create` en Anthropic). El riesgo real: una
funcion NUEVA dentro del propio fichero autorizado (captura_orquestador.py)
que usara uno de esos metodos en vez de los dos reconocidos pasaria
invisible para la comprobacion de "toda funcion que envia pide permiso" --
ni siquiera se contaria como "funcion que envia algo".

Esta suite prueba `_llamadas_api_ia()` y `_es_messages_anthropic()` /
`_es_batches_anthropic()` directamente sobre codigo sintetico (nunca sobre
los ficheros reales del proyecto), y ademas ejecuta `check_salida_unica_cloud()`
de principio a fin sobre una copia sintetica en un directorio temporal, para
probar el auditor completo -- incluida la parte que decide que fichero esta
"fuera" de la puerta -- sin arriesgar un falso positivo/negativo contra el
propio repositorio real mientras se prueba.

Ejecutar con: python3 test_salida_unica_cloud.py
"""
import ast
import os
import sys
import tempfile

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from audit_project import (
    _llamadas_api_ia, _es_messages_anthropic, _es_batches_anthropic,
    _importa_sdk_ia, _referencia_host_ia_cruda,
)

FALLOS = []


def check(cond, nombre):
    if cond:
        print(f"  OK   {nombre}")
    else:
        print(f"  FALLO {nombre}")
        FALLOS.append(nombre)


def llamadas_en(codigo):
    return list(_llamadas_api_ia(ast.parse(codigo)))


# ---------------------------------------------------------------------------
# FAMILIA A -- lo que YA reconocia antes del 17-09-2026 sigue reconociendolo
# (control positivo: el fix no puede haber estrechado nada)
# ---------------------------------------------------------------------------

check(len(llamadas_en("cliente.generate_content(x)")) == 1,
      "Gemini generate_content: se sigue reconociendo (control positivo)")

check(len(llamadas_en("cliente.messages.create(x)")) == 1,
      "Anthropic messages.create: se sigue reconociendo (control positivo)")

check(len(llamadas_en("cliente.messages.create")) == 0,
      "Un atributo sin llamar (sin parentesis) no cuenta como envio")

check(len(llamadas_en("otra_cosa.create(x)")) == 0,
      "create() sobre algo que NO cuelga de .messages no es un falso positivo")


# ---------------------------------------------------------------------------
# FAMILIA B -- el hueco reproducido y cerrado el 17-09-2026: metodos reales
# de los SDK instalados que antes del fix pasaban invisibles
# ---------------------------------------------------------------------------

for metodo, motivo in [
    ("generate_content_stream", "Gemini: streaming, mismo envio que generate_content"),
    ("embed_content", "Gemini: tambien envia contenido al modelo"),
    ("count_tokens", "Gemini: cuenta tokens VIA la API, el contenido viaja igual"),
]:
    check(len(llamadas_en(f"cliente.{metodo}(x)")) == 1,
          f"Gemini {metodo}: reconocido tras el fix ({motivo})")

for metodo in ("stream", "count_tokens", "parse"):
    check(len(llamadas_en(f"cliente.messages.{metodo}(x)")) == 1,
          f"Anthropic messages.{metodo}: reconocido tras el fix")

check(len(llamadas_en("cliente.messages.batches.create(x)")) == 1,
      "Anthropic messages.batches.create (envio en lote): reconocido tras el fix")

check(len(llamadas_en("cliente.messages.batches.retrieve(x)")) == 0,
      "messages.batches.retrieve (solo consulta, no envia) no se marca como envio")


# ---------------------------------------------------------------------------
# FAMILIA C -- el caso real que motivo el fix: una funcion NUEVA en el propio
# fichero autorizado, usando un metodo no reconocido antes, se detecta como
# "envia sin pedir permiso" si le falta exigir_permiso()
# ---------------------------------------------------------------------------

CAPTURA_CON_FUNCION_SIN_PERMISO = '''
import anthropic
import puerta_cloud

def leer_factura_ok(cliente, path, lote):
    permiso = lote.consumir(path)
    puerta_cloud.exigir_permiso(permiso, path)
    return cliente.messages.create(model="x", messages=[])

def leer_algo_nuevo_sin_permiso(cliente, path):
    return cliente.messages.stream(model="x", messages=[{"role": "user", "content": path}])
'''


def funciones_sin_permiso(codigo):
    arbol = ast.parse(codigo)
    sin_permiso = []
    for fn in ast.walk(arbol):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        envia = list(_llamadas_api_ia(fn))
        if not envia:
            continue
        permisos = [n.lineno for n in ast.walk(fn) if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute) and n.func.attr == "exigir_permiso"]
        if not permisos or min(permisos) > min(n.lineno for n in envia):
            sin_permiso.append(fn.name)
    return sin_permiso


resultado = funciones_sin_permiso(CAPTURA_CON_FUNCION_SIN_PERMISO)
check(resultado == ["leer_algo_nuevo_sin_permiso"],
      f"Funcion que usa .messages.stream() sin exigir_permiso se detecta "
      f"(reproduccion exacta del hueco cerrado 17-09-2026; obtenido: {resultado})")

resultado_control = funciones_sin_permiso('''
import anthropic
import puerta_cloud

def leer_factura_ok(cliente, path, lote):
    permiso = lote.consumir(path)
    puerta_cloud.exigir_permiso(permiso, path)
    return cliente.messages.stream(model="x", messages=[])
''')
check(resultado_control == [],
      "Control positivo: la MISMA llamada (.messages.stream) con exigir_permiso "
      "presente no se marca como problema")


# ---------------------------------------------------------------------------
# FAMILIA C-ter -- el hueco cerrado el 18-09-2026: exigir_permiso() se
# comprobaba SOLO por presencia en la funcion, nunca por ORDEN. Una funcion
# que envia primero y pide permiso despues pasaba como correcta.
# ---------------------------------------------------------------------------

resultado_orden_mal = funciones_sin_permiso('''
import puerta_cloud

def leer_mal_orden(cliente, path, lote):
    resultado = cliente.messages.create(model="x", messages=[{"content": path}])
    permiso = lote.consumir(path)
    puerta_cloud.exigir_permiso(permiso, path)
    return resultado
''')
check(resultado_orden_mal == ["leer_mal_orden"],
      f"Funcion que envia ANTES de pedir permiso se detecta, aunque "
      f"exigir_permiso este presente en la funcion (obtenido: {resultado_orden_mal})")

resultado_orden_bien = funciones_sin_permiso('''
import puerta_cloud

def leer_bien(cliente, path, lote):
    permiso = lote.consumir(path)
    puerta_cloud.exigir_permiso(permiso, path)
    return cliente.messages.create(model="x", messages=[{"content": path}])
''')
check(resultado_orden_bien == [],
      "Control positivo: el mismo envio, con exigir_permiso ANTES (el orden "
      "real de captura_orquestador.py), no se marca como problema")


# ---------------------------------------------------------------------------
# FAMILIA C-bis -- el hueco cerrado el 18-09-2026: una llamada HTTP cruda al
# mismo host de la API, sin SDK y sin metodo reconocido, era invisible del
# todo (ni siquiera contaba el fichero como revisado)
#
# NOTA: las cadenas de ejemplo se montan con .join()/variables, nunca como
# literal directo dentro de ast.parse(...) -- porque un literal directo AHI
# es, para _referencia_host_ia_cruda, exactamente la misma forma que un
# `requests.post("https://api.anthropic.com/...")` real, y este propio
# fichero de test se acusaria a si mismo (el mismo fallo, encontrado en
# audit_project.py, que motivo que la funcion exija que sea un ARGUMENTO DE
# LLAMADA y no cualquier cadena -- ver su docstring).
# ---------------------------------------------------------------------------

_HOST_ANTHROPIC = "https://" + "api.anthropic.com" + "/v1/messages"
_HOST_GEMINI = "https://" + "generativelanguage.googleapis.com" + "/v1/x"
_HOST_AJENO = "https://otra-cosa.com/x"

codigo_http_anthropic = "requests.post(URL, json={})".replace("URL", repr(_HOST_ANTHROPIC))
codigo_http_gemini = "requests.post(URL, json={})".replace("URL", repr(_HOST_GEMINI))
codigo_http_ajeno = "requests.post(URL)".replace("URL", repr(_HOST_AJENO))

check(_referencia_host_ia_cruda(ast.parse(codigo_http_anthropic)),
    "HTTP crudo al host real de Anthropic: detectado por el dominio, sin SDK ni metodo reconocido")

check(_referencia_host_ia_cruda(ast.parse(codigo_http_gemini)),
    "HTTP crudo al host real de Gemini: detectado igual")

check(not _referencia_host_ia_cruda(ast.parse(codigo_http_ajeno)),
      "Una URL que NO es ninguna de las dos APIs no dispara un falso positivo")

check(not list(_llamadas_api_ia(ast.parse(codigo_http_anthropic))),
    "El HTTP crudo, tal cual, sigue sin contar como 'llamada reconocida' -- "
    "por eso hace falta la senal de host aparte, no basta con _llamadas_api_ia")


# ---------------------------------------------------------------------------
# FAMILIA D -- check_salida_unica_cloud() de principio a fin, sobre una copia
# sintetica en disco (nunca sobre el repositorio real mientras se prueba)
# ---------------------------------------------------------------------------

def ejecutar_auditoria_en(ficheros):
    """Escribe `ficheros` (dict nombre -> contenido) en un directorio temporal
    y llama a la funcion REAL check_salida_unica_cloud() -- no una copia
    paralela de su logica. Una copia mantenida a mano se desincroniza cada
    vez que la funcion real cambia (pasó tres veces mientras se escribia
    esta suite: el metodo nuevo, el host crudo, el orden de exigir_permiso
    fueron cada uno un fix a la funcion real que esta copia no habria
    reflejado). Devuelve (ok, detalle) leyendo el RESULTADO global que deja
    check(), en vez de imprimir."""
    import audit_project as ap
    with tempfile.TemporaryDirectory() as tmp:
        cwd_previo = os.getcwd()
        try:
            os.chdir(tmp)
            for nombre, contenido in ficheros.items():
                with open(nombre, "w", encoding="utf-8") as fh:
                    fh.write(contenido)
            ap.check_salida_unica_cloud()
            resultado = ap.RESULTADO["checks"]["Salida a IA: una sola puerta, y pide permiso"]
            return resultado["ok"], resultado["detalle"]
        finally:
            os.chdir(cwd_previo)


ok1, detalle1 = ejecutar_auditoria_en({
    "captura_orquestador.py": CAPTURA_CON_FUNCION_SIN_PERMISO,
    "puerta_cloud.py": "def exigir_permiso(p, ruta): pass\n",
})
check(not ok1 and "leer_algo_nuevo_sin_permiso" in detalle1,
      f"Auditoria completa: localiza fichero y funcion exactos del envio sin "
      f"permiso (obtenido: {detalle1})")

ok2, detalle2 = ejecutar_auditoria_en({
    "otro_fichero.py": 'import anthropic\ndef f(c, x): return c.messages.stream(model="x", messages=[])\n',
})
check(not ok2 and "otro_fichero.py" in detalle2,
      f"Auditoria completa: una llamada con metodo nuevo (.stream) en OTRO "
      f"fichero (no el autorizado) tambien se marca como fuera de la puerta (obtenido: {detalle2})")

ok3, detalle3 = ejecutar_auditoria_en({
    "captura_orquestador.py": (
        "import puerta_cloud\n"
        "def leer(x):\n"
        "    return 'nada de IA aqui, solo texto'\n"
    ),
})
check(ok3,
      f"Auditoria completa: un fichero autorizado que no llama a ninguna IA "
      f"no genera ningun falso positivo (obtenido: {detalle3})")

ok4, detalle4 = ejecutar_auditoria_en({
    "otro_fichero.py": (
        'import requests\n'
        'def f(path):\n'
        '    return requests.post("https://api.anthropic.com/v1/messages", json={"path": path})\n'
    ),
})
check(not ok4 and "otro_fichero.py" in detalle4,
      f"Auditoria completa: HTTP crudo al host de Anthropic en OTRO fichero "
      f"(reproduccion exacta del hueco cerrado 18-09-2026) se marca como fuera de la puerta (obtenido: {detalle4})")

ok5, detalle5 = ejecutar_auditoria_en({
    "captura_orquestador.py": (
        'import requests\n'
        'import puerta_cloud\n'
        'def f(path):\n'
        '    return requests.post("https://api.anthropic.com/v1/messages", json={"path": path})\n'
    ),
})
check(not ok5 and "captura_orquestador.py" in detalle5,
      f"Auditoria completa: el MISMO HTTP crudo, esta vez DENTRO del fichero "
      f"autorizado, se marca como 'sin verificar' en vez de darse por bueno "
      f"en silencio (obtenido: {detalle5})")

ok6, detalle6 = ejecutar_auditoria_en({
    "captura_orquestador.py": (
        "import puerta_cloud\n"
        "def leer_mal_orden(cliente, path, lote):\n"
        "    resultado = cliente.messages.create(model='x', messages=[{'content': path}])\n"
        "    permiso = lote.consumir(path)\n"
        "    puerta_cloud.exigir_permiso(permiso, path)\n"
        "    return resultado\n"
    ),
})
check(not ok6 and "leer_mal_orden" in detalle6,
      f"Auditoria completa: funcion que envia antes de pedir permiso (orden "
      f"invertido) se detecta aunque exigir_permiso este presente (obtenido: {detalle6})")

ok7, detalle7 = ejecutar_auditoria_en({
    "captura_orquestador.py": (
        "import puerta_cloud\n"
        "def leer_bien(cliente, path, lote):\n"
        "    permiso = lote.consumir(path)\n"
        "    puerta_cloud.exigir_permiso(permiso, path)\n"
        "    return cliente.messages.create(model='x', messages=[{'content': path}])\n"
    ),
})
check(ok7,
      f"Auditoria completa, control positivo: el mismo envio con "
      f"exigir_permiso ANTES no genera ningun falso positivo (obtenido: {detalle7})")


if FALLOS:
    print(f"\n{len(FALLOS)} fallo(s): {', '.join(FALLOS)}")
    sys.exit(1)
print("\nTodas las pruebas de check_salida_unica_cloud pasaron.")
sys.exit(0)
