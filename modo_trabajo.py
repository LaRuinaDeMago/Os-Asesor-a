#!/usr/bin/env python3
"""modo_trabajo.py — en que modo estamos, que puede salir, y que puedo ver yo.

POR QUE EXISTE (16-09-2026, peticion explicita de Diego)
---------------------------------------------------------
`puerta_cloud.py` decide si un documento puede salir. Esto contesta la pregunta
de al lado, que es la que se hace CONSTANTEMENTE mientras trabajamos:

    "¿en que modo estoy ahora mismo, que datos puede ver Claude, y para LO QUE
     quiero hacer a continuacion, que hay que encender?"

Hasta hoy eso se contestaba de memoria, mirando `.claude/rules/datos.md` y
recordando la conversacion. Es decir: era conocimiento, no mecanismo. Y este
proyecto ya sabe como acaba el conocimiento que vive solo en la cabeza o en una
conversacion -- es literalmente el hallazgo que se repite en los cinco ultimos
cierres de `PROJECT_STATUS.md`.

LO QUE HACE, Y COMO
---------------------
MIDE. Ni una linea de lo que imprime esta escrita de antemano: mira el
interprete, las variables de entorno, los paquetes instalados y las rutas, y
DERIVA de ahi que se puede hacer. Misma disciplina que `arranque.py`.

De las claves comprueba **solo si existen**, nunca su valor, y nunca las
imprime. Que una clave este presente es un hecho del entorno; su contenido es
un secreto (`.claude/rules/seguridad.md`).

LO QUE NO PUEDE MEDIR, Y LO DICE
----------------------------------
Que exista un DPA firmado con Google o con Anthropic **no es medible desde
aqui**: es un hecho legal, no del sistema de ficheros. `OS_ASESORIA_DATOS_REALES`
no "activa" un DPA -- es la DECLARACION de que existe, puesta a mano por quien
sabe que existe. Este modulo lo presenta asi y no como si lo hubiera
comprobado, por la misma razon de siempre: un OK que significa "no lo he
comprobado" es el falso verde que el motor tiene prohibido dar.
"""
import importlib.util
import os
import sys

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import puerta_cloud

#: La ruta del corpus tal como la documentan `PENDIENTE.md` y `EMPEZAR_AQUI.md`.
#: No es un dato de cliente (es la carpeta de la maquina de Diego) y ya vive en
#: el repositorio. Se usa como valor por defecto para que el informe acierte en
#: el PC de la asesoria sin configurar nada; `OS_ASESORIA_CORPUS` lo sobrescribe.
CORPUS_DOCUMENTADO = r"C:\Users\SERVILAB\Desktop\100% contabilidad"

#: Rutas por las que un dato puede llegar a un modelo. Estan ORDENADAS de menos
#: a mas exposicion, y ese orden es la politica: no se usa una ruta mas
#: expuesta si una anterior resuelve lo mismo. Es la version operativa de la
#: regla que `.claude/rules/datos.md` ya tiene escrita ("¿el modelo necesita
#: VER el dato, o basta con que un script lo cuente?").
RUTAS = (
    ("1. TRES ROLES",
     "Claude escribe el script SIN ver datos -> Diego lo ejecuta en su maquina "
     "-> Claude lee solo el agregado (recuentos, porcentajes).",
     "Nada. Funciona hoy, en cualquier superficie.",
     "0 EUR. Es la ruta preferida, y lo sigue siendo aunque haya DPA: no "
     "viajar es mas fuerte que viajar con contrato."),
    ("2. SENSOR",
     "La foto la ve GEMINI, devuelve JSON, y el motor local decide. Claude NO "
     "ve la foto: trabaja sobre el codigo y sobre recuentos.",
     "Gemini de PAGO (facturacion activa) + puerta abierta + procedencia "
     "declarada. Para documentos REALES, ademas la llave legal y la "
     "confirmacion con el recuento.",
     "Centimos por factura. Es la ruta del dia a dia."),
    ("3. PROYECCION MINIMA",
     "De lo que Gemini extrajo se construye EN LOCAL una proyeccion sin "
     "identidad (sin NIF, sin razon social, sin ruta) y ESO es lo que Claude "
     "ve para analizar un caso concreto.",
     "Que la ruta 2 se haya ejecutado. La herramienta de proyeccion TODAVIA NO "
     "EXISTE: se construira con el primer CSV real delante, no antes.",
     "0 EUR de API. AVISO: pseudonimizar NO es anonimizar -- si hay tabla "
     "local para volver atras, sigue siendo dato confidencial."),
    ("4. CLAUDE VE EL DOCUMENTO",
     "Excepcional: Claude mira la factura original porque el extractor produjo "
     "algo que no se entiende.",
     "DPA con Anthropic Y sesion LOCAL con ANTHROPIC_API_KEY. IMPOSIBLE en "
     "Cloud/Web y en Remote Control: esas superficies usan siempre la "
     "suscripcion, nunca la clave.",
     "Por tokens. Es la ultima opcion, no la primera."),
)


class Tarea:
    """Una cosa que de verdad se hace en este proyecto, y que necesita.

    `necesita` son claves de CAPACIDADES. La tarea se puede hacer AHORA si
    todas estan en verde. No hay valoraciones: se comprueba."""

    def __init__(self, nombre, necesita, coste, nota=""):
        self.nombre = nombre
        self.necesita = necesita
        self.coste = coste
        self.nota = nota


TAREAS = (
    Tarea("Tests, auditoria, guards, vigilancia del BOE", (), "0 EUR"),
    Tarea("Retro-semaforo sobre el corpus de ContaPlus", ("dbfread", "corpus"),
          "0 EUR", "Sesion LOCAL: el corpus vive en el PC de la asesoria"),
    Tarea("Cuadre del 303 contra los PDF presentados", ("pdfplumber", "corpus"),
          "0 EUR", "Sesion LOCAL, misma razon"),
    Tarea("Leer una factura SINTETICA (probar la cadena entera)",
          ("google-genai", "clave_gemini", "puerta_cloud"), "Centimos",
          "Esto se puede hacer SIN DPA: es lo mas lejos que llega hoy la "
          "cadena foto -> JSON -> motor"),
    Tarea("Leer una factura REAL",
          ("google-genai", "clave_gemini", "puerta_cloud", "puerta_datos_reales"),
          "Centimos",
          "Ademas hay que confirmar con el RECUENTO EXACTO del lote"),
    Tarea("Que Claude analice un caso concreto sin ver la factura",
          ("proyeccion_minima",), "0 EUR de API",
          "Ruta 3. La herramienta no existe todavia: se construye con el "
          "primer CSV real delante"),
    Tarea("Que Claude VEA una factura real",
          ("clave_anthropic", "sesion_local"), "Por tokens",
          "Ruta 4, excepcional. En Cloud/Web es imposible por diseño"),
)


def _instalado(modulo):
    try:
        return importlib.util.find_spec(modulo) is not None
    except (ImportError, ValueError):
        return False


def medir(entorno=None, ruta_corpus=None):
    """Todo lo que se puede comprobar AHORA. Ninguna clave se lee ni se imprime:
    solo si esta puesta."""
    env = os.environ if entorno is None else entorno
    # La ruta documentada del corpus se prueba TAMBIEN por defecto: si solo se
    # mirara la variable de entorno, en el PC de la asesoria —donde el corpus
    # esta ahi mismo— este informe diria "no" y seria un falso negativo. Una
    # herramienta que se equivoca en lo obvio deja de mirarse.
    corpus = ruta_corpus if ruta_corpus is not None else (
        env.get("OS_ASESORIA_CORPUS") or CORPUS_DOCUMENTADO)
    return {
        # Superficie: senales medidas, no una etiqueta. El PC de la asesoria es
        # Windows (documentado: cp1252, `python` y no `python3`), asi que un
        # interprete linux es una señal solida de que esto NO es esa maquina.
        "sesion_local": sys.platform == "win32",
        "corpus": bool(corpus) and os.path.isdir(corpus),
        # Claves: solo presencia. Nunca el valor.
        "clave_gemini": bool(env.get("GEMINI_API_KEY")),
        "clave_anthropic": bool(env.get("ANTHROPIC_API_KEY")),
        # Las dos llaves de la puerta.
        "puerta_cloud": puerta_cloud.permiso_cloud(env),
        "puerta_datos_reales": puerta_cloud.permiso_datos_reales(env),
        # Paquetes.
        "google-genai": _instalado("google.genai"),
        "anthropic": _instalado("anthropic"),
        "dbfread": _instalado("dbfread"),
        "pdfplumber": _instalado("pdfplumber"),
        # Herramientas del proyecto que aun no existen se miden igual que todo
        # lo demas: por si el fichero esta, no por si alguien se acuerda.
        "proyeccion_minima": os.path.exists(
            os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "proyeccion_minima.py")),
    }


def que_puede_ver_claude(cap):
    """Derivado de lo medido, no declarado. Devuelve (lineas, puede_ver_real)."""
    lineas = []
    lineas.append("codigo, tests, documentacion y datos sinteticos: SIEMPRE")
    lineas.append("agregados y recuentos de un script que corre en local: SIEMPRE "
                  "(ruta 1, y es la preferida)")
    if cap["proyeccion_minima"]:
        lineas.append("proyecciones sin identidad de facturas ya extraidas: SI")
    else:
        lineas.append("proyecciones sin identidad de facturas ya extraidas: NO, "
                      "la herramienta no esta construida todavia (ruta 3)")
    if cap["sesion_local"] and cap["clave_anthropic"]:
        lineas.append("el documento original: solo si hay DPA con Anthropic "
                      "(esto NO se puede comprobar desde aqui)")
    else:
        lineas.append("el documento original: NO. " + (
            "Esta superficie usa la suscripcion, nunca la clave"
            if not cap["sesion_local"] else "No hay ANTHROPIC_API_KEY puesta"))
    return lineas, cap["sesion_local"] and cap["clave_anthropic"]


def _si_no(v):
    return "SI" if v else "no"


def main():
    cap = medir()
    print("=" * 70)
    print("MODO DE TRABAJO — medido ahora mismo, no recordado")
    print("=" * 70)

    print("\n--- 1. Donde estamos (señales medidas) -------------------------")
    print(f"  interprete           : {sys.platform}")
    print(f"  ¿PC de la asesoria?  : {_si_no(cap['sesion_local'])}"
          f"{'' if cap['sesion_local'] else '  (linux: esto es Cloud o un contenedor)'}")
    print(f"  corpus real alcanzable: {_si_no(cap['corpus'])}"
          f"{'' if cap['corpus'] else '  (declararlo con OS_ASESORIA_CORPUS)'}")

    print("\n--- 2. Las llaves (solo si estan puestas, nunca su valor) ------")
    print(f"  GEMINI_API_KEY           {_si_no(cap['clave_gemini'])}")
    print(f"  ANTHROPIC_API_KEY        {_si_no(cap['clave_anthropic'])}")
    print(f"  {puerta_cloud.ENV_CLOUD:24s} {_si_no(cap['puerta_cloud'])}"
          f"   <- ¿puede salir algo?")
    print(f"  {puerta_cloud.ENV_DATOS_REALES:24s} {_si_no(cap['puerta_datos_reales'])}"
          f"   <- DECLARACION de que hay DPA, no comprobacion")

    print("\n--- 3. Que puede ver Claude ------------------------------------")
    for linea in que_puede_ver_claude(cap)[0]:
        print(f"  - {linea}")

    print("\n--- 4. Que se puede hacer AHORA, y que hay que encender --------")
    for t in TAREAS:
        faltan = [n for n in t.necesita if not cap.get(n)]
        marca = "✅" if not faltan else "⛔"
        print(f"  {marca} {t.nombre}   [{t.coste}]")
        if faltan:
            print(f"       falta: {', '.join(faltan)}")
        if t.nota:
            print(f"       {t.nota}")

    print("\n--- 5. Las cuatro rutas, de menos a mas exposicion -------------")
    for nombre, que_es, necesita, coste in RUTAS:
        print(f"\n  {nombre}")
        print(f"      {que_es}")
        print(f"      necesita: {necesita}")
        print(f"      {coste}")

    print("\n" + "=" * 70)
    print("La puerta la decide puerta_cloud.py; esto solo la explica.")
    print("Nada de lo de arriba esta escrito de antemano: todo se ha medido.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
