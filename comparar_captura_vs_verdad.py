#!/usr/bin/env python3
"""comparar_captura_vs_verdad.py — que la comparacion sea una MEDICION, no una mirada.

QUE PROBLEMA RESUELVE
-----------------------
`PENDIENTE.md` lleva desde el 16-09-2026 diciendo, en el Paso 1: *"COMPARA campo
a campo contra la verdad que imprimio"*. Eso son quince campos, a ojo, en una
pantalla, con prisa y con ganas de que salga bien. Es el paso del que depende
todo el proyecto -- decide si la cadena foto -> IA -> motor funciona -- y es el
unico que se hacia sin herramienta.

Comparar a ojo tiene tres formas de equivocarse, y las tres son silenciosas:

  · Se da por bueno `1.420,00` frente a `1420.0` (bien) pero tambien `1.420,00`
    frente a `1420.50` de un vistazo (mal).
  · Se pasa por alto un campo que NO VINO. Un campo ausente no llama la
    atencion: simplemente no esta, y el ojo salta al siguiente.
  · Se "corrige" mentalmente lo que el modelo devolvio, porque uno ya sabe lo
    que deberia poner. Es el sesgo mas dificil de evitar leyendo.

Esto lo convierte en un comando con codigo de salida.

LO QUE MIDE, Y CON QUE CRITERIO
---------------------------------
No compara cadenas. Cada campo se lee con el PARSER DEL PROPIO CONTRATO
(`contrato_datos`), que es el mismo que usa el motor: asi `"1.420,00"` y
`1420.0` son el mismo dato --que es la verdad-- y no hace falta un segundo
parser que pueda divergir del primero. Este proyecto ya pago dos veces el mismo
bug en dos sitios (PENDIENTE.md 1.A).

  · **Importes** -> se leen como numero y se comparan con tolerancia de medio
    centimo. Una diferencia de 0,01 es una diferencia, no un redondeo.
  · **Fechas** -> se leen con los formatos que el contrato acepta, asi que
    `26/03/2026` y `2026-03-26` son la misma fecha.
  · **Numero de documento** -> se compara EN CRUDO y ademas normalizado. Si
    coinciden normalizados pero no en crudo, no es un fallo: es una diferencia
    de PUNTUACION, y se dice asi, porque no es lo mismo no saber leer el numero
    que escribirlo sin el punto.
  · **`tramos_iva`** -> por contenido y sin importar el orden. Que el modelo
    devuelva el 5% antes que el 21% no es un error.
  · **`nif_margen`** -> ⚠️ EN CRUDO, SIN NORMALIZAR NADA, y esto es deliberado:
    la puntuacion ES la medicion. La muestra `doble_lectura_letras` escribe el
    NIF del pie con guiones y el de la cabecera sin ellos, justo para poder
    distinguir si el modelo LEYO el pie o COPIO la cabecera. Normalizar los
    guiones aqui destruiria el experimento entero y ademas lo dejaria en verde.

UN CAMPO QUE NO VINO NUNCA ES UN APROBADO
-------------------------------------------
Si la captura no devolvio un campo, no cuenta como coincidencia ni como fallo:
cuenta como NO COMPROBADO, sale por su propia puerta y el codigo de salida lo
refleja. Es la regla del motor aplicada aqui -- si no se ha podido comprobar, no
es OK -- y es la que evita el peor resultado posible: un "todo bien" que
significa "no vino casi nada".

LA BARRERA DE DATOS, POR CONSTRUCCION Y NO POR CONFIANZA
---------------------------------------------------------
Esta herramienta IMPRIME VALORES DE CAMPOS. Sobre una muestra sintetica eso es
inofensivo. Sobre una factura real serian un NIF y una razon social reales en la
terminal -- y de ahi a un chat hay un copiar y pegar, que es exactamente lo que
`.claude/rules/datos.md` prohibe.

Asi que no se confia en que nadie se acuerde: se lee `_procedencia` del fichero
de verdad y **lo que no esta declarado SINTETICO se trata como REAL**, igual que
en `puerta_cloud.py`. Con un documento real la herramienta sigue funcionando y
sigue dando el veredicto, pero **no imprime ni un valor**: solo coincide / no
coincide / no vino. La medicion se conserva entera; lo que desaparece es el
dato. No hay opcion para desactivarlo.

USO
-----
    python captura_orquestador.py --imagen muestras_sinteticas/X_limpia.png \\
           --procedencia SINTETICO > captura.json

    python comparar_captura_vs_verdad.py captura.json

El fichero de verdad se busca solo a partir del nombre de la imagen, y se puede
forzar con `--verdad`. Tambien lee de la entrada estandar con `-`.

Codigos de salida, los mismos tres de `audit_project.py` porque son las mismas
tres cosas:
    0  todos los campos comprobados y coincidiendo
    1  algun campo NO coincide  -- hay una diferencia real
    2  nada discrepa, pero algo no se ha podido comprobar (un campo no vino)
"""
import argparse
import json
import os
import sys

import contrato_datos

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Medio centimo. Por debajo de esto dos importes son el mismo importe; por
#: encima, son dos. No se usa una tolerancia mas ancha a proposito: el objeto de
#: esta medicion es justamente cazar el digito que el OCR cambia.
TOL = 0.005

#: Resultados de comparar un campo.
COINCIDE = "COINCIDE"
DIFIERE = "DIFIERE"
NO_VINO = "NO_VINO"
SOLO_PUNTUACION = "SOLO_PUNTUACION"

#: Campos que la captura anade y que la verdad conocida no tiene por que llevar:
#: no son un fallo, son metadatos de la lectura. `verificacion` es la confianza
#: que el modelo declara sobre SU PROPIA lectura, y por eso no es una propiedad
#: del documento (ver PENDIENTE.md: por eso la verdad sola da AMBAR).
CAMPOS_DE_LA_LECTURA = ("verificacion", "motivo_semaforo", "confianza_campos",
                        "tipo_documento", "_tokens_entrada", "_tokens_salida",
                        "_modelo", "_proveedor", "_coste")


# ---------------------------------------------------------------------------
# Comparar un campo, con el criterio que ese campo merece
# ---------------------------------------------------------------------------
def _solo_alfanumerico(s):
    return "".join(c for c in str(s).upper() if c.isalnum())


def comparar_importe(esperado, obtenido):
    """Numericamente, no como cadena. `"1.420,00"` y `1420.0` son lo mismo."""
    d_esp = contrato_datos.parse_numero(esperado)
    d_obt = contrato_datos.parse_numero(obtenido)
    if d_obt.estado not in contrato_datos.UTILIZABLES:
        return NO_VINO, f"la captura no trajo un importe legible ({d_obt.estado})"
    if d_esp.estado not in contrato_datos.UTILIZABLES:
        # La verdad conocida deberia traerlo siempre; si no, se declara, no se
        # da por bueno.
        return NO_VINO, f"la VERDAD no trae un importe legible ({d_esp.estado})"
    if abs(d_esp.valor - d_obt.valor) < TOL:
        return COINCIDE, ""
    return DIFIERE, f"esperado {d_esp.valor} / leido {d_obt.valor}"


def comparar_fecha(esperado, obtenido):
    d_esp = contrato_datos.parse_fecha(esperado)
    d_obt = contrato_datos.parse_fecha(obtenido)
    if d_obt.estado not in contrato_datos.UTILIZABLES:
        return NO_VINO, f"la captura no trajo una fecha legible ({d_obt.estado})"
    if d_esp.valor == d_obt.valor:
        return COINCIDE, ""
    return DIFIERE, f"esperada {d_esp.valor} / leida {d_obt.valor}"


def comparar_texto(esperado, obtenido, normalizable=True):
    """En crudo primero. Si solo difiere la puntuacion, se DICE, no se aprueba.

    `normalizable=False` para `nif_margen`: ahi la puntuacion no es ruido, es la
    medicion (ver la cabecera del modulo)."""
    if obtenido is None or str(obtenido).strip() == "":
        return NO_VINO, "la captura no trajo este campo"
    e, o = str(esperado).strip(), str(obtenido).strip()
    if e == o:
        return COINCIDE, ""
    if normalizable and _solo_alfanumerico(e) == _solo_alfanumerico(o):
        return SOLO_PUNTUACION, f"esperado {e!r} / leido {o!r}"
    return DIFIERE, f"esperado {e!r} / leido {o!r}"


def comparar_num_documento(esperado, obtenido):
    """Con el normalizador del propio proyecto, no con uno nuevo."""
    if obtenido is None or str(obtenido).strip() == "":
        return NO_VINO, "la captura no trajo el numero de documento"
    e, o = str(esperado).strip(), str(obtenido).strip()
    if e == o:
        return COINCIDE, ""
    if (contrato_datos.normalizar_num_documento(e)
            == contrato_datos.normalizar_num_documento(o)):
        return SOLO_PUNTUACION, f"esperado {e!r} / leido {o!r}"
    return DIFIERE, f"esperado {e!r} / leido {o!r}"


def comparar_tramos(esperado, obtenido):
    """Por contenido y SIN importar el orden: que venga antes el 5% no es error.

    Es el campo que mas importa de todos y el que mas facil es dar por bueno de
    un vistazo: el tramo al 5% no tiene campo plano equivalente, asi que si no
    llega por aqui desaparece entero y los totales siguen cuadrando."""
    tramos_obt = contrato_datos.parse_estructura(obtenido)
    obtenido_vacio = not isinstance(tramos_obt, (list, tuple)) or not tramos_obt

    # VACIA CONTRA VACIA ES UNA COINCIDENCIA, no un "no vino". En una operacion
    # sin IVA repercutido -- inversion del sujeto pasivo, exenta,
    # intracomunitaria -- lo correcto es que NO haya desglose, y el prompt lo
    # pide asi ("Lista vacia si no hay desglose"). Leerlo como "no vino" dejaria
    # la muestra de ISP condenada a codigo 2 para siempre, por acertar.
    if not esperado:
        if obtenido_vacio:
            forma = ("la captura devolvio la lista vacia"
                     if isinstance(tramos_obt, (list, tuple))
                     else "la captura no trajo el campo")
            return COINCIDE, (f"sin desglose de IVA en los dos, que es lo "
                              f"correcto en este regimen ({forma})")
        return DIFIERE, (f"la verdad no declara tramos -- no deberia haber "
                         f"desglose -- y la captura ha leido {len(tramos_obt)}")

    if obtenido_vacio:
        return NO_VINO, "la captura no trajo tramos_iva (o no son una lista)"

    def clave(t):
        if not isinstance(t, dict):
            return None
        tipo = contrato_datos.parse_numero(t.get("tipo"))
        base = contrato_datos.parse_numero(t.get("base"))
        cuota = contrato_datos.parse_numero(t.get("cuota"))
        if any(d.estado not in contrato_datos.UTILIZABLES
               for d in (tipo, base, cuota)):
            return None
        return (round(tipo.valor, 2), round(base.valor, 2), round(cuota.valor, 2))

    esp = {clave(t) for t in esperado}
    obt = {clave(t) for t in tramos_obt}
    if None in obt:
        return NO_VINO, "algun tramo de la captura viene incompleto o ilegible"
    if esp == obt:
        return COINCIDE, ""
    faltan = esp - obt
    sobran = obt - esp
    partes = []
    if faltan:
        partes.append("NO ha leido (tipo, base, cuota): "
                      + ", ".join(str(t) for t in sorted(faltan)))
    if sobran:
        partes.append("ha leido de mas: "
                      + ", ".join(str(t) for t in sorted(sobran)))
    return DIFIERE, " | ".join(partes)


def comparar_campo(nombre, esperado, obtenido):
    """Elige el criterio segun QUE campo es. No todos se comparan igual."""
    if nombre == "tramos_iva":
        return comparar_tramos(esperado, obtenido)
    if nombre in contrato_datos.CAMPOS_MONETARIOS:
        return comparar_importe(esperado, obtenido)
    if nombre in ("fecha_expedicion", "fecha_vencimiento"):
        return comparar_fecha(esperado, obtenido)
    if nombre == "nº_documento":
        return comparar_num_documento(esperado, obtenido)
    if nombre == "nif_margen":
        # SIN normalizar. La puntuacion es el marcador del experimento.
        return comparar_texto(esperado, obtenido, normalizable=False)
    return comparar_texto(esperado, obtenido)


# ---------------------------------------------------------------------------
# Cargar las dos mitades
# ---------------------------------------------------------------------------
def cargar_json(ruta):
    if ruta == "-":
        return json.load(sys.stdin)
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def buscar_verdad(captura, ruta_captura):
    """Encuentra el `_verdad.json` que corresponde, sin obligar a teclearlo.

    Se prueba, en este orden: el nombre de la imagen que la captura declara, y
    el nombre del propio fichero de captura. Si no aparece, se dice cual se ha
    buscado -- nunca se elige "el que mas se parezca", que es como se acaba
    comparando una muestra contra la verdad de otra."""
    candidatos = []
    for pista in (captura.get("_imagen"), captura.get("imagen"), ruta_captura):
        if not pista or pista == "-":
            continue
        base = os.path.basename(str(pista))
        raiz = os.path.splitext(base)[0]
        for sufijo in ("_limpia", "_degradada", "_captura", ""):
            if sufijo and raiz.endswith(sufijo):
                raiz = raiz[: -len(sufijo)]
                break
        candidatos.append(os.path.join("muestras_sinteticas",
                                       f"{raiz}_verdad.json"))
    for c in candidatos:
        if os.path.exists(c):
            return c
    return None


def es_sintetico(verdad):
    """Lo que NO esta declarado SINTETICO se trata como REAL.

    Misma regla que `puerta_cloud.py`, y por el mismo motivo: un typo, un None o
    una clave que falta caen del lado seguro. Decidir por una etiqueta optimista
    seria repetir el fallo del `.DAT` (ver .claude/rules/datos.md)."""
    return str(verdad.get("_procedencia", "")).strip().upper() == "SINTETICO"


# ---------------------------------------------------------------------------
# El informe
# ---------------------------------------------------------------------------
#: Las cuatro preguntas del Paso 1, y de que campo sale la respuesta de cada
#: una. Estan aqui y no en un comentario porque el informe las contesta SOLO:
#: eran el motivo de existir de las muestras, y contestarlas a mano es
#: exactamente lo que esta herramienta viene a quitar.
PREGUNTAS = (
    ("tramos_iva",
     "¿Vienen TODOS los tramos de IVA, incluido el 5%? El 5% no tiene campo "
     "plano: si no llega por aqui, se pierde entero y los totales siguen "
     "cuadrando."),
    ("total_factura_2",
     "¿`total_factura_2` trae el total del PIE, o ha copiado el del cuadro? "
     "Si lo copia, la doble lectura es un espejo y no vale nada."),
    ("nif_margen",
     "¿`nif_margen` trae el NIF del PIE, con su puntuacion? Si vuelve como el "
     "de la cabecera, lo ha copiado."),
    ("nº_documento",
     "¿El numero de documento sale con su puntuacion (barras y puntos)?"),
)


def informar(verdad, captura, mostrar_valores):
    """Devuelve (resultados, hay_diferencia, hay_sin_comprobar)."""
    campos = [k for k in verdad if not k.startswith("_")]
    resultados = []
    for nombre in campos:
        estado, detalle = comparar_campo(nombre, verdad[nombre],
                                         captura.get(nombre))
        if not mostrar_valores:
            # Con un documento REAL el veredicto se conserva entero; lo que
            # desaparece es el dato. Ver la cabecera del modulo.
            detalle = "(valores ocultos: documento no declarado SINTETICO)" \
                if detalle else ""
        resultados.append((nombre, estado, detalle))

    ancho = max(len(n) for n in campos) if campos else 10
    simbolos = {COINCIDE: "OK  ", DIFIERE: "MAL ", NO_VINO: "??  ",
                SOLO_PUNTUACION: "~   "}
    print("-" * 72)
    print("CAMPO A CAMPO")
    print("-" * 72)
    for nombre, estado, detalle in resultados:
        print(f"  {simbolos[estado]} {nombre:<{ancho}}  {estado}"
              + (f"  — {detalle}" if detalle else ""))

    extras = [k for k in captura
              if k not in verdad and k not in CAMPOS_DE_LA_LECTURA
              and not k.startswith("_")]
    if extras:
        print()
        print("  La captura trae ademas estos campos, que la verdad conocida no")
        print("  declara. No es un fallo -- se listan por si alguno deberia estar:")
        print("    " + ", ".join(sorted(extras)))

    hay_dif = any(e == DIFIERE for _n, e, _d in resultados)
    hay_sin = any(e == NO_VINO for _n, e, _d in resultados)
    return resultados, hay_dif, hay_sin


def _matices(campo, estado, verdad):
    """Lo que una coincidencia NO demuestra en ESTA muestra concreta.

    Sin esto el informe caia en su propio falso verde. Dos casos reales, vistos
    al usarlo sobre las muestras nuevas:

      · Contestaba "SI" a la pregunta del tramo al 5% sobre una muestra que NO
        TIENE ningun tramo al 5%. Quien leyera el informe se llevaria la
        impresion de que ese caso esta probado, y no lo esta.
      · Daba por buena la lectura del pie en las muestras donde el pie y la
        cabecera llevan EXACTAMENTE lo mismo. Ahi una coincidencia no distingue
        haber leido de haber copiado -- que es justo el defecto de diseno por el
        que existen estas muestras (PENDIENTE.md, Paso 1).
    """
    avisos = []
    if campo == "tramos_iva":
        tramos = verdad.get("tramos_iva") or []
        if not tramos:
            avisos.append("OJO: esta muestra NO lleva desglose de IVA a "
                          "proposito, asi que la pregunta del 5% NO se contesta "
                          "aqui. Lo que se comprueba es que no se invente uno.")
        elif not any(int(t.get("tipo", -1)) == 5 for t in tramos):
            avisos.append("OJO: esta muestra no lleva ningun tramo al 5%, asi "
                          "que del 5% no dice nada. Usa `doble_lectura_letras`.")
    if campo == "total_factura_2" and estado == COINCIDE:
        if verdad.get("total_factura_2") == verdad.get("total_factura"):
            avisos.append("OJO: en esta muestra el pie lleva el MISMO importe "
                          "que el cuadro, asi que coincidir NO distingue haber "
                          "leido de haber copiado. Quien contesta esto de "
                          "verdad es `doble_lectura_descuadre`.")
    if campo == "nif_margen":
        if estado == SOLO_PUNTUACION:
            avisos.append("OJO: coincide salvo puntuacion. En esta muestra la "
                          "puntuacion ERA la medicion, asi que esto NO confirma "
                          "que haya leido el pie.")
        elif estado == COINCIDE and verdad.get("nif_margen") == verdad.get("nif"):
            avisos.append("OJO: en esta muestra el NIF del pie se escribe IGUAL "
                          "que el de la cabecera, asi que coincidir no prueba "
                          "que lo haya leido del pie. Quien lo prueba es "
                          "`doble_lectura_letras`, con guiones.")
    return avisos


def contestar_preguntas(resultados, verdad):
    """Las cuatro preguntas del Paso 1, contestadas con lo medido arriba."""
    por_campo = {n: (e, d) for n, e, d in resultados}
    print()
    print("-" * 72)
    print("LAS CUATRO PREGUNTAS DEL PASO 1, CONTESTADAS")
    print("-" * 72)
    for campo, pregunta in PREGUNTAS:
        if campo not in por_campo:
            print(f"  ??  {campo}: esta muestra no lo declara, no se puede "
                  f"contestar aqui.")
            continue
        estado, detalle = por_campo[campo]
        veredicto = {
            COINCIDE: "SI",
            SOLO_PUNTUACION: "SI, pero con otra puntuacion",
            DIFIERE: "NO",
            NO_VINO: "NO SE HA PODIDO COMPROBAR: el campo no vino",
        }[estado]
        print(f"  {campo}: {veredicto}")
        print(f"      {pregunta}")
        if detalle:
            print(f"      {detalle}")
        for aviso in _matices(campo, estado, verdad):
            for linea in _envolver(aviso, 64):
                print(f"      {linea}")
        print()


def _envolver(texto, ancho):
    """Parte un texto en lineas de como mucho `ancho`, sin cortar palabras."""
    lineas, actual = [], ""
    for palabra in texto.split():
        if actual and len(actual) + 1 + len(palabra) > ancho:
            lineas.append(actual)
            actual = palabra
        else:
            actual = f"{actual} {palabra}".strip()
    if actual:
        lineas.append(actual)
    return lineas


def veredicto_del_motor(captura, verdad):
    """Lo que el motor dice de lo que el modelo LEYO, no de la verdad.

    Es el cierre del circulo, y la pregunta que de verdad importa: no "¿ha
    leido bien?" sino "¿con lo que ha leido, el motor acierta?". Una lectura con
    un fallo que el motor caza es un caso controlado; una con un fallo que el
    motor deja pasar es el problema entero del proyecto."""
    try:
        from motor_veredicto import evaluar_fila_v4
    except ImportError as e:
        print(f"  No se ha podido cargar el motor ({e}). Sin veredicto.")
        return
    fila = {k: v for k, v in captura.items() if not k.startswith("_")}
    try:
        v, motivo, guards = evaluar_fila_v4(fila, set(), {}, {}, {}, {},
                                            2020, None, None)
    except Exception as e:
        print(f"  El motor no ha podido evaluar la captura: {type(e).__name__}")
        return
    print(f"  Con lo que el modelo leyo, el motor dice: {v}")
    print(f"  motivo: {motivo}")
    fallos = [(k, est[1]) for k, est in guards.items() if est[0] == "FALLO"]
    if fallos:
        print("  guards en FALLO:")
        for k, d in fallos:
            print(f"      {k}: {d}")


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Compara lo que la captura leyo contra la verdad conocida "
                    "de una muestra sintetica.")
    p.add_argument("captura", help="JSON de captura_orquestador.py, o '-' para "
                                   "leer de la entrada estandar")
    p.add_argument("--verdad", help="Fichero _verdad.json (por defecto se busca "
                                    "por el nombre de la imagen)")
    p.add_argument("--sin-motor", action="store_true",
                   help="No pasar la captura por el motor al final")
    args = p.parse_args(argv)

    captura = cargar_json(args.captura)
    ruta_verdad = args.verdad or buscar_verdad(captura, args.captura)
    if not ruta_verdad or not os.path.exists(ruta_verdad):
        print("No encuentro el fichero de verdad conocida.")
        print("Pasalo a mano con --verdad, por ejemplo:")
        print("    --verdad muestras_sinteticas/doble_lectura_letras_verdad.json")
        print()
        print("No se elige 'el que mas se parezca' a proposito: comparar una")
        print("muestra contra la verdad de OTRA daria un informe entero y falso.")
        return 2
    verdad = cargar_json(ruta_verdad)

    sintetico = es_sintetico(verdad)
    print("=" * 72)
    print("CAPTURA vs VERDAD CONOCIDA")
    print("=" * 72)
    if sintetico:
        print(f"  muestra  : {verdad.get('_muestra', '(sin nombre)')}")
        print(f"  verdad   : {ruta_verdad}")
        if verdad.get("_que_mide"):
            print()
            print(f"  Esta muestra mide: {verdad['_que_mide']}")
    else:
        # Ni el nombre de la muestra ni la RUTA del fichero se imprimen. Los dos
        # los elige una persona y los dos pueden llevar el nombre de un cliente
        # ("ACME_SL_verdad.json"). `puerta_cloud.py` ya tiene esa regla escrita
        # para su registro -- huellas y recuentos, nunca una ruta ni un nombre --
        # y aqui vale igual. Esto no se vio hasta escribir la prueba de la
        # barrera: la primera version imprimia las dos cosas.
        print("  muestra  : (oculta: documento no declarado SINTETICO)")
        print("  verdad   : (ruta oculta por el mismo motivo)")
        print()
        print("  ⚠️  Este documento NO esta declarado SINTETICO, asi que se")
        print("      trata como REAL: el informe da el veredicto de cada campo")
        print("      pero NO imprime ningun valor, ni el nombre, ni la ruta.")
        print("      Ver .claude/rules/datos.md.")
    print()

    resultados, hay_dif, hay_sin = informar(verdad, captura, sintetico)
    if sintetico:
        contestar_preguntas(resultados, verdad)

    if not args.sin_motor:
        print("-" * 72)
        print("Y EL MOTOR, SOBRE LO QUE EL MODELO LEYO")
        print("-" * 72)
        veredicto_del_motor(captura, verdad)
        print()

    n = len(resultados)
    coinciden = sum(1 for _c, e, _d in resultados if e == COINCIDE)
    puntuacion = sum(1 for _c, e, _d in resultados if e == SOLO_PUNTUACION)
    difieren = sum(1 for _c, e, _d in resultados if e == DIFIERE)
    sin = sum(1 for _c, e, _d in resultados if e == NO_VINO)

    print("=" * 72)
    print(f"  campos comparados : {n}")
    print(f"  coinciden         : {coinciden}")
    print(f"  solo puntuacion   : {puntuacion}")
    print(f"  DIFIEREN          : {difieren}")
    print(f"  no vinieron       : {sin}")
    print("=" * 72)

    if hay_dif:
        print("  Hay al menos una diferencia REAL. Codigo de salida 1.")
        return 1
    if hay_sin:
        print("  Nada discrepa, pero algun campo no vino: NO es un aprobado.")
        print("  Un 'todo bien' que significa 'no vino casi nada' es el peor")
        print("  resultado posible. Codigo de salida 2.")
        return 2
    print("  Todos los campos comprobados y coincidiendo. Codigo de salida 0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
