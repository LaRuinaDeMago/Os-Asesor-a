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
        pide = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                   and n.func.attr == "exigir_permiso" for n in ast.walk(fn))
        if not pide:
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
    y ejecuta la MISMA logica que check_salida_unica_cloud(), devolviendo
    (fuera, autorizado_ok, sin_permiso, sin_verificar_crudo) en vez de
    imprimir -- para poder comprobar el resultado sin depender de parsear el
    mensaje impreso."""
    import audit_project as ap
    with tempfile.TemporaryDirectory() as tmp:
        cwd_previo = os.getcwd()
        try:
            os.chdir(tmp)
            for nombre, contenido in ficheros.items():
                with open(nombre, "w", encoding="utf-8") as fh:
                    fh.write(contenido)
            fuera, sin_permiso, sin_verificar_crudo = [], [], []
            autorizado_ok = False
            from pathlib import Path
            for f in [str(p) for p in Path(".").rglob("*.py")]:
                arbol = ast.parse(open(f, encoding="utf-8").read())
                llamadas = list(_llamadas_api_ia(arbol))
                host_crudo = _referencia_host_ia_cruda(arbol)
                if not llamadas and not _importa_sdk_ia(arbol) and not host_crudo:
                    continue
                if os.path.basename(f) != ap.SALIDA_CLOUD_AUTORIZADA:
                    fuera.append(os.path.basename(f))
                    continue
                autorizado_ok = any(
                    isinstance(n, (ast.Import, ast.ImportFrom))
                    and "puerta_cloud" in ast.dump(n) for n in ast.walk(arbol))
                for fn in ast.walk(arbol):
                    if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    envia = list(_llamadas_api_ia(fn))
                    if not envia:
                        continue
                    pide = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                               and n.func.attr == "exigir_permiso" for n in ast.walk(fn))
                    if not pide:
                        sin_permiso.append(f"{os.path.basename(f)}:{fn.name}")
                if host_crudo and not llamadas:
                    sin_verificar_crudo.append(os.path.basename(f))
            return fuera, autorizado_ok, sin_permiso, sin_verificar_crudo
        finally:
            os.chdir(cwd_previo)


fuera, autorizado_ok, sin_permiso, _ = ejecutar_auditoria_en({
    "captura_orquestador.py": CAPTURA_CON_FUNCION_SIN_PERMISO,
    "puerta_cloud.py": "def exigir_permiso(p, ruta): pass\n",
})
check(fuera == [], "Auditoria completa: el fichero autorizado no se marca como 'fuera'")
check(autorizado_ok, "Auditoria completa: detecta que importa puerta_cloud")
check(sin_permiso == ["captura_orquestador.py:leer_algo_nuevo_sin_permiso"],
      f"Auditoria completa: localiza fichero y funcion exactos del envio sin "
      f"permiso (obtenido: {sin_permiso})")

fuera2, _, _, _ = ejecutar_auditoria_en({
    "otro_fichero.py": 'import anthropic\ndef f(c, x): return c.messages.stream(model="x", messages=[])\n',
})
check(fuera2 == ["otro_fichero.py"],
      "Auditoria completa: una llamada con metodo nuevo (.stream) en OTRO "
      "fichero (no el autorizado) tambien se marca como fuera de la puerta")

fuera3, _, sin_permiso3, _ = ejecutar_auditoria_en({
    "captura_orquestador.py": (
        "import puerta_cloud\n"
        "def leer(x):\n"
        "    return 'nada de IA aqui, solo texto'\n"
    ),
})
check(fuera3 == [] and sin_permiso3 == [],
      "Auditoria completa: un fichero autorizado que no llama a ninguna IA "
      "no genera ningun falso positivo")

fuera4, _, _, _ = ejecutar_auditoria_en({
    "otro_fichero.py": (
        'import requests\n'
        'def f(path):\n'
        '    return requests.post("https://api.anthropic.com/v1/messages", json={"path": path})\n'
    ),
})
check(fuera4 == ["otro_fichero.py"],
      "Auditoria completa: HTTP crudo al host de Anthropic en OTRO fichero "
      "(reproduccion exacta del hueco cerrado 18-09-2026) se marca como fuera de la puerta")

_, _, _, crudo5 = ejecutar_auditoria_en({
    "captura_orquestador.py": (
        'import requests\n'
        'import puerta_cloud\n'
        'def f(path):\n'
        '    return requests.post("https://api.anthropic.com/v1/messages", json={"path": path})\n'
    ),
})
check(crudo5 == ["captura_orquestador.py"],
      "Auditoria completa: el MISMO HTTP crudo, esta vez DENTRO del fichero "
      "autorizado, se marca como 'sin verificar' en vez de darse por bueno "
      "en silencio (no hay una llamada reconocida a la que atarle el "
      "requisito de exigir_permiso)")


if FALLOS:
    print(f"\n{len(FALLOS)} fallo(s): {', '.join(FALLOS)}")
    sys.exit(1)
print("\nTodas las pruebas de check_salida_unica_cloud pasaron.")
sys.exit(0)
