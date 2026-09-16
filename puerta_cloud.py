#!/usr/bin/env python3
"""puerta_cloud.py — la unica salida autorizada de datos hacia una API externa.

POR QUE EXISTE (16-09-2026)
-----------------------------
Hasta hoy, la regla "el modelo solo ve lo que necesita" vivia en
`.claude/rules/datos.md` y en la disciplina de quien la lee. Eso es una barrera
DOCUMENTAL. Este proyecto ya aprendio, pagandolo, que una barrera que depende
de que alguien se acuerde es una barrera de conveniencia: el ZIP con extension
`.DAT` paso por delante del escaner de privacidad ocho dias, y el escaner
ademas respondia "sin hallazgos" sobre un fichero que no habia mirado.

Esta puerta convierte esa regla en MECANISMO. Es un chokepoint: para que un
byte de un documento salga hacia Gemini o hacia Anthropic tiene que pasar por
aqui, y aqui la respuesta por defecto es NO.

LO QUE DECIDE, Y LO QUE DELIBERADAMENTE NO DECIDE
---------------------------------------------------
Decide **permiso** y deja **constancia**. Nada mas.

NO decide politica: ni presupuesto, ni que modelo usar, ni cuantos reintentos,
ni si conviene OCR local antes que la API. Esa capa (el "router") se
construira cuando existan numeros reales con los que fijar sus constantes --
hoy no existen, y fijarlas ahora seria elegirlas a ojo, que es el error que
este proyecto tiene documentado al menos tres veces (el `5` de
`fase0_huella_cliente.py`, el `MIN_NIFS=3` que sigue abierto, el `1 sigma` de
`importe_atipico`). Primero se mide, despues se decide.

LAS CUATRO PREGUNTAS, Y POR QUE SON CUATRO
--------------------------------------------
Cada una es un hecho distinto del mundo, y colapsarlas perderia informacion:

  1. ¿Puede esta maquina hablar con una API?      OS_ASESORIA_CLOUD=1
     Decision OPERATIVA. Por defecto, no.
  2. ¿Pueden salir documentos REALES?             OS_ASESORIA_DATOS_REALES=1
     Decision LEGAL (DPA/condiciones del proveedor). Por defecto, no.
  3. ¿Que es este documento?                      procedencia
     SINTETICO o REAL. Lo no declarado es REAL (ver abajo).
  4. ¿Ha visto un humano cuantos van a salir?     confirmacion
     Solo para REAL. Es un numero que tiene que COINCIDIR con el recuento.

Un documento SINTETICO solo necesita (1). Eso es deliberado y util: permite
ejercitar la cadena entera foto -> JSON -> motor con facturas fabricadas HOY,
sin DPA y sin riesgo legal, y con la propia puerta certificando que lo que
salio era fabricado.

POR QUE LA CONFIRMACION ES UN NUMERO Y NO UN "SI"
---------------------------------------------------
Un `--confirmo` booleano se escribe una vez en un script y ya nunca vuelve a
mirarse. Y una confirmacion por DOCUMENTO sobre un lote de 30 facturas produce
fatiga de alarma: quien confirma treinta veces seguidas deja de leer a la
tercera. Rigor que produce fatiga produce sellos de goma.

Por eso la confirmacion es por LOTE y es el recuento exacto: quien la escribe
ha tenido que mirar cuantos documentos hay. Si el recuento cambia, la
confirmacion deja de valer sola.

POR QUE LO DESCONOCIDO ES REAL (fail closed)
----------------------------------------------
La tentacion es decidir con una etiqueta: `documento.es_real = False`. Eso es
una barrera que decide por el NOMBRE, y es exactamente el bug del `.DAT`: quien
etiquete mal (o quien no etiquete) abre la puerta.

Aqui lo no declarado se trata como REAL. "No se de donde viene esto" bloquea,
igual que el escaner de privacidad bloquea un binario que no ha podido mirar.
Es la misma regla que el motor: si no se ha podido comprobar, no es OK.

EL LIMITE QUE ESTA PUERTA NO PUEDE CRUZAR, DECLARADO
------------------------------------------------------
Para un fichero de TEXTO, el contenido se puede comprobar (lo hace
`scripts/privacy_scan.py`, por bytes y por patron). Para una IMAGEN, no: una
foto de una factura fabricada y una foto de una factura real son, para un
programa, dos imagenes. La procedencia de una imagen es una DECLARACION, no una
medicion.

Eso no se disimula: se declara aqui, queda en el registro (`declarada`), y por
eso el camino REAL exige ademas las dos llaves y la confirmacion humana. La
puerta no finge saber lo que no puede saber.

LO QUE NO SE HA CONSTRUIDO, Y POR QUE
---------------------------------------
No hay un nivel `ANONIMIZADO` entre SINTETICO y REAL. Un documento anonimizado
DERIVA de uno real, y ademas pseudonimizar no es anonimizar: si existe una
tabla local que devuelve de `PROVEEDOR_271` a una empresa concreta, sigue
siendo dato confidencial. Añadir ese nivel sin un caso real concreto que lo
pida seria justo lo que `CLAUDE.md` prohibe. Cuando aparezca el caso, se añade
con el caso detras.

REGLA DE DATOS
----------------
Este modulo NO abre ningun documento, NO lee su contenido y NO lo envia: solo
autoriza o bloquea, y anota. Lo que escribe en el registro es una lista CERRADA
de campos no identificables (`CAMPOS_REGISTRO`), y `test_puerta_cloud.py`
comprueba que ningun campo nuevo se cuela: nunca una ruta, un nombre de fichero
ni un importe.
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from typing import NamedTuple

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Procedencia de un documento. Dos valores, no tres (ver docstring).
SINTETICO = "SINTETICO"
REAL = "REAL"
PROCEDENCIAS = (SINTETICO, REAL)

#: Variables de entorno. Son condiciones NECESARIAS, nunca suficientes: la
#: barrera es el chokepoint, no la bandera. Una bandera solo protege si alguien
#: la consulta; por eso ademas existe el auditor de audit_project.py que
#: comprueba por AST que nadie llama a una API sin pasar por aqui.
ENV_CLOUD = "OS_ASESORIA_CLOUD"
ENV_DATOS_REALES = "OS_ASESORIA_DATOS_REALES"

#: Motivos: conjunto CERRADO. Nunca texto libre, porque el texto libre es por
#: donde se escapa un dato (mismo motivo por el que los scripts de la Fase 0
#: reportan `type(e).__name__` y nunca `str(e)`).
OK = "OK"
SIN_PERMISO_CLOUD = "SIN_PERMISO_CLOUD"
SIN_AUTORIZACION_DATOS_REALES = "SIN_AUTORIZACION_DATOS_REALES"
CONFIRMACION_NO_COINCIDE = "CONFIRMACION_NO_COINCIDE"
LOTE_NO_AUTORIZADO = "LOTE_NO_AUTORIZADO"
LOTE_AGOTADO = "LOTE_AGOTADO"
RECUENTO_INVALIDO = "RECUENTO_INVALIDO"
MOTIVOS = (OK, SIN_PERMISO_CLOUD, SIN_AUTORIZACION_DATOS_REALES,
           CONFIRMACION_NO_COINCIDE, LOTE_NO_AUTORIZADO, LOTE_AGOTADO,
           RECUENTO_INVALIDO)

#: Tipos de linea del registro.
#:
#: LOTE existe porque al ejecutar esto de verdad la primera vez se vio que un
#: lote BLOQUEADO no dejaba ni una linea: la puerta se cerraba, el proceso
#: terminaba, y no quedaba rastro de que alguien habia intentado sacar 30
#: documentos reales sin DPA. Justo el evento que mas interesa poder auditar
#: despues era el unico que no se anotaba.
LOTE = "LOTE"
PERMISO = "PERMISO"
RESULTADO = "RESULTADO"

#: Lista CERRADA de campos que pueden aparecer en el registro. Cualquier campo
#: fuera de esta lista es un fallo, y test_puerta_cloud.py lo comprueba. No es
#: burocracia: es lo que impide que dentro de seis meses alguien añada
#: "proveedor_nombre" para depurar y convierta el registro en una fuga.
CAMPOS_REGISTRO = (
    "ts", "tipo", "lote", "doc", "n_documentos", "procedencia", "declarada",
    "proveedor", "modelo", "estado", "motivo",
    "tokens_entrada", "tokens_salida", "coste_eur",
)

REGISTRO_POR_DEFECTO = "registro_cloud.jsonl"

PERMITIDO = "PERMITIDO"
BLOQUEADO = "BLOQUEADO"


class SalidaBloqueada(RuntimeError):
    """La puerta ha dicho que no. Su mensaje lleva el motivo (de la lista
    cerrada) y la huella del documento -- nunca la ruta ni el contenido, que es
    justo lo que no puede acabar en la consola de una sesion."""


class Permiso(NamedTuple):
    """El salvoconducto de UN documento concreto.

    Es una NamedTuple a proposito: sigue comportandose como la tupla
    (permitido, motivo) que es comoda de leer, pero ademas lleva la huella del
    documento para el que se concedio. Eso permite que la funcion que de verdad
    toca la API exija un permiso QUE CORRESPONDA a la ruta que va a enviar
    (`exigir_permiso`), y no simplemente "algun" permiso.

    Sin esto, la garantia dependeria de que nadie llame por dentro a la funcion
    de bajo nivel saltandose el punto de entrada -- es decir, de una convencion.
    Con esto, la funcion no puede ejecutarse sin el salvoconducto correcto."""
    permitido: bool
    motivo: str
    doc: str


def exigir_permiso(permiso, ruta):
    """Se llama JUSTO ANTES de enviar. Lanza si el permiso no vale para esta
    ruta. Es la ultima linea de defensa, y es local: quien lea la funcion que
    llama a la API ve en la linea de arriba que no puede saltarsela."""
    if not isinstance(permiso, Permiso) or not permiso.permitido:
        motivo = permiso.motivo if isinstance(permiso, Permiso) else LOTE_NO_AUTORIZADO
        raise SalidaBloqueada(
            f"La puerta ha bloqueado esta salida (motivo: {motivo}). "
            f"Ver puerta_cloud.py y `python3 puerta_cloud.py` para el estado."
        )
    esperado = referencia_documento(ruta)
    if permiso.doc != esperado:
        raise SalidaBloqueada(
            f"El permiso no corresponde a este documento "
            f"(permiso para {permiso.doc}, se iba a enviar {esperado})."
        )


def normalizar_procedencia(valor):
    """Devuelve (procedencia, declarada).

    Lo que no sea exactamente SINTETICO o REAL se trata como REAL y se marca
    como NO declarada. None, "", "sintetico?" , un typo, un valor que venga de
    un JSON de configuracion mal escrito: todos caen del lado seguro. No hay
    forma de que un valor inesperado abra la puerta."""
    if valor in PROCEDENCIAS:
        return valor, True
    return REAL, False


def referencia_documento(ruta):
    """Identificador no reversible de un documento, para el registro.

    Se hashea la ruta ABSOLUTA. Importa que sea un hash y no el nombre: un
    nombre de fichero real dice cosas como el nombre del proveedor y el mes.
    Doce caracteres bastan para seguir la pista de un documento dentro de un
    lote sin poder reconstruir de donde salio."""
    ruta_abs = os.path.abspath(str(ruta))
    return hashlib.sha256(ruta_abs.encode("utf-8")).hexdigest()[:12]


def _ahora():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def permiso_cloud(entorno=None):
    """¿Puede esta maquina hablar con una API? Decision operativa."""
    env = os.environ if entorno is None else entorno
    return env.get(ENV_CLOUD) == "1"


def permiso_datos_reales(entorno=None):
    """¿Pueden salir documentos REALES? Decision legal (DPA/condiciones)."""
    env = os.environ if entorno is None else entorno
    return env.get(ENV_DATOS_REALES) == "1"


class Lote:
    """Una autorizacion ACOTADA: N documentos, una procedencia, un proveedor.

    Siempre se devuelve un Lote, tambien cuando la puerta ha dicho que no: asi
    quien llama no puede recibir por error algo que parezca verdadero. Un lote
    no autorizado bloquea cada documento, uno por uno, y lo deja registrado.

    Esta acotado a proposito. Sin el tope, un bucle que se descontrola manda
    500 documentos con una sola autorizacion; con el, la confirmacion que
    escribio el humano ("30") es EJECUTABLE, no un gesto."""

    def __init__(self, permitido, motivo, n_documentos, procedencia, declarada,
                 proveedor, modelo, registro):
        self.permitido = permitido
        self.motivo = motivo
        self.n_documentos = n_documentos
        self.procedencia = procedencia
        self.declarada = declarada
        self.proveedor = proveedor
        self.modelo = modelo
        self.registro = registro
        self.consumidos = 0
        self.id = hashlib.sha256(
            f"{_ahora()}|{n_documentos}|{procedencia}|{proveedor}".encode("utf-8")
        ).hexdigest()[:8]

    @property
    def restantes(self):
        if not self.permitido or self.n_documentos is None:
            return 0
        return max(0, self.n_documentos - self.consumidos)

    def consumir(self, ruta):
        """Pide permiso para UN documento concreto. Devuelve un `Permiso`.

        Registra SIEMPRE, permita o bloquee: un intento bloqueado es
        exactamente lo que interesa poder auditar despues."""
        doc = referencia_documento(ruta)
        if not self.permitido:
            return self._anotar(doc, BLOQUEADO, LOTE_NO_AUTORIZADO)
        if self.consumidos >= self.n_documentos:
            return self._anotar(doc, BLOQUEADO, LOTE_AGOTADO)
        self.consumidos += 1
        return self._anotar(doc, PERMITIDO, OK)

    def anotar_resultado(self, ruta, tokens_entrada=None, tokens_salida=None,
                         coste_eur=None):
        """Segunda linea del registro, ya con lo que costo la llamada.

        Los tres campos van a None si el SDK no los expone donde se espera. Es
        deliberado: un coste inventado es peor que un coste ausente, y un None
        en el registro se ve a simple vista la primera vez que se mira. Mismo
        principio que NO_COMPROBADO en el motor."""
        doc = referencia_documento(ruta)
        self._escribir({
            "ts": _ahora(), "tipo": RESULTADO, "lote": self.id, "doc": doc,
            "n_documentos": self.n_documentos,
            "procedencia": self.procedencia, "declarada": self.declarada,
            "proveedor": self.proveedor, "modelo": self.modelo,
            "estado": PERMITIDO, "motivo": OK,
            "tokens_entrada": tokens_entrada, "tokens_salida": tokens_salida,
            "coste_eur": coste_eur,
        })

    def anotar_apertura(self):
        """Deja constancia de la decision del LOTE, se haya abierto o no.

        La llama `abrir_lote()` en los dos caminos. Un lote bloqueado que no
        deja rastro es un intento invisible."""
        self._escribir({
            "ts": _ahora(), "tipo": LOTE, "lote": self.id, "doc": None,
            "n_documentos": self.n_documentos,
            "procedencia": self.procedencia, "declarada": self.declarada,
            "proveedor": self.proveedor, "modelo": self.modelo,
            "estado": PERMITIDO if self.permitido else BLOQUEADO,
            "motivo": self.motivo,
            "tokens_entrada": None, "tokens_salida": None, "coste_eur": None,
        })
        return self

    def _anotar(self, doc, estado, motivo):
        self._escribir({
            "ts": _ahora(), "tipo": PERMISO, "lote": self.id, "doc": doc,
            "n_documentos": self.n_documentos,
            "procedencia": self.procedencia, "declarada": self.declarada,
            "proveedor": self.proveedor, "modelo": self.modelo,
            "estado": estado, "motivo": motivo,
            "tokens_entrada": None, "tokens_salida": None, "coste_eur": None,
        })
        return Permiso(estado == PERMITIDO, motivo, doc)

    def _escribir(self, fila):
        # Igualdad EXACTA, no subconjunto: un campo de mas es una fuga en
        # potencia, y uno de menos rompe en silencio a quien lea el fichero
        # despues. Se comprobo al añadir `n_documentos`: la linea de RESULTADO
        # se quedo sin el y solo lo canto esta comprobacion.
        sobran = set(fila) - set(CAMPOS_REGISTRO)
        faltan = set(CAMPOS_REGISTRO) - set(fila)
        if sobran or faltan:
            raise ValueError(
                f"El registro admite EXACTAMENTE los campos de CAMPOS_REGISTRO. "
                f"Sobran: {sorted(sobran)}. Faltan: {sorted(faltan)}."
            )
        if self.registro is None:
            return
        with open(self.registro, "a", encoding="utf-8") as f:
            f.write(json.dumps(fila, ensure_ascii=False, sort_keys=True) + "\n")


def abrir_lote(n_documentos, procedencia, proveedor, modelo=None,
               confirmacion=None, entorno=None, registro=REGISTRO_POR_DEFECTO):
    """La puerta. Devuelve un Lote, autorizado o no.

    n_documentos : cuantos documentos van a salir. Es el tope real del lote.
    procedencia  : SINTETICO o REAL. Cualquier otra cosa se trata como REAL.
    confirmacion : solo para REAL. Tiene que ser el entero n_documentos.

    El orden de las comprobaciones importa: se mira primero lo que bloquea a
    todo el mundo (permiso de cloud) y despues lo especifico de los datos
    reales, para que el motivo registrado sea el primero que de verdad
    impide la salida, y no uno accesorio."""
    procedencia, declarada = normalizar_procedencia(procedencia)

    def no(motivo):
        n = n_documentos if isinstance(n_documentos, int) and not isinstance(n_documentos, bool) else None
        return Lote(False, motivo, n, procedencia, declarada,
                    proveedor, modelo, registro).anotar_apertura()

    if not isinstance(n_documentos, int) or isinstance(n_documentos, bool) or n_documentos <= 0:
        return no(RECUENTO_INVALIDO)
    if not permiso_cloud(entorno):
        return no(SIN_PERMISO_CLOUD)
    if procedencia == REAL:
        if not permiso_datos_reales(entorno):
            return no(SIN_AUTORIZACION_DATOS_REALES)
        # `is True` no vale como confirmacion, y un bool tampoco: tiene que ser
        # el numero. isinstance(True, int) es True en Python, de ahi el segundo
        # filtro -- sin el, `confirmacion=True` colaria en un lote de 1.
        if isinstance(confirmacion, bool) or confirmacion != n_documentos:
            return no(CONFIRMACION_NO_COINCIDE)
    return Lote(True, OK, n_documentos, procedencia, declarada, proveedor,
                modelo, registro).anotar_apertura()


def estado_actual(entorno=None):
    """Lo que la puerta permitiria ahora mismo. No toca ningun dato."""
    return {
        "cloud": permiso_cloud(entorno),
        "datos_reales": permiso_datos_reales(entorno),
    }


def main():
    est = estado_actual()
    print("=" * 66)
    print("PUERTA CLOUD — que se permitiria ahora mismo")
    print("=" * 66)
    print("Esto no envia nada ni abre ningun documento: solo mira el entorno.")
    print()
    print(f"  {ENV_CLOUD:28s} {'SI' if est['cloud'] else 'NO'}")
    print(f"  {ENV_DATOS_REALES:28s} {'SI' if est['datos_reales'] else 'NO'}")
    print()
    if not est["cloud"]:
        print("  => NADA sale. Ni sintetico ni real. Puerta cerrada.")
    elif not est["datos_reales"]:
        print("  => Solo documentos SINTETICOS declarados.")
        print("     Un documento real (o sin declarar) se bloquea.")
    else:
        print("  => Documentos reales permitidos SI ademas la llamada trae la")
        print("     confirmacion con el recuento exacto del lote.")
    print()
    print("Lo no declarado se trata como REAL, siempre. Ver el docstring de")
    print("este fichero para por que, y que limite no puede cruzar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
