#!/usr/bin/env python3
"""diff_comportamiento_motor.py — que ha cambiado DE VERDAD en los veredictos
del motor entre dos versiones, medido factura a factura.

POR QUE EXISTE
----------------
El 27-08-2026 el motor recibio SEIS cambios en un solo dia (dos funciones
nuevas, guard_importe_atipico reescrito, _forma, secuencia_documental,
nif_check). Cada uno se probo por separado y con su sabotaje, y toda la
bateria quedo en verde. Pero eso responde a "¿sigue pasando lo que ya
probabamos?", no a la pregunta que de verdad importa despues de un dia asi:

    ¿QUE factura cambia de veredicto, y es un cambio que queriamos?

Un cambio intencionado y uno accidental se parecen mucho en un test en verde:
los dos pasan. La unica forma de distinguirlos es coger las MISMAS facturas,
pasarlas por las DOS versiones y enumerar las diferencias.

COMO LO HACE, Y POR QUE EN SUBPROCESOS
----------------------------------------
Las dos versiones se llaman igual (`motor_veredicto`), y la vieja importa
`nif_check` por nombre. Cargarlas en el mismo proceso mezclaria las dos
implementaciones sin avisar — justo el tipo de falso resultado que este
proyecto persigue. Cada version corre en su PROPIO subproceso, con su
directorio al principio de sys.path, y solo se comparan los veredictos que
escriben. `contrato_datos.py` se copia desde el arbol actual a proposito:
lo que se quiere aislar es el cambio del MOTOR, no el del contrato.

REGLA DE DATOS: el corpus es sintetico y determinista (semilla fija). Ni un
NIF ni un nombre real en ninguna parte — los NIF llevan digito de control
calculado, como exige `.claude/rules/datos.md` para que sean utilizables sin
ser de nadie.

USO, Y CUAL ES LA PREGUNTA REUTILIZABLE
-----------------------------------------
Por defecto compara el arbol de trabajo contra HEAD, que es la pregunta que
vuelve cada vez que se toca el motor:

    python diff_comportamiento_motor.py

    -> "el cambio que acabo de escribir y aun no he subido, ¿que factura
        mueve, y es la que yo queria mover?"

Con el arbol limpio no encuentra nada, y eso tambien es informacion: confirma
que lo subido no ha movido nada por accidente.

Para mirar hacia atras, se le da la referencia:

    python diff_comportamiento_motor.py --ref 408952f   # todo el 27-08-2026
    python diff_comportamiento_motor.py --ref HEAD~5

NO esta cableado a `audit_project.py`, y es deliberado: con el arbol limpio
siempre diria "sin cambios", asi que en la auditoria diaria seria una linea
en verde que no comprueba nada — justo el tipo de falso verde que este
proyecto persigue. Es una herramienta para cuando se toca el motor, no un
vigilante permanente.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AQUI = os.path.dirname(os.path.abspath(__file__))

#: Ficheros que forman "el motor" a efectos de esta comparacion.
FICHEROS_MOTOR = ("motor_veredicto.py", "nif_check.py")
#: Se toma del arbol ACTUAL, no de la referencia: aislamos el motor, no el
#: contrato de datos. Si algun dia cambia el contrato, esta linea hay que
#: revisarla y decirlo, no dejarla pasar en silencio.
FICHEROS_COMPARTIDOS = ("contrato_datos.py",)

LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE"


def dni_valido(n):
    """DNI inventado con letra de control correcta (nunca uno real)."""
    return f"{n:08d}{LETRAS_DNI[n % 23]}"


def cif_valido(letra, n):
    """CIF inventado con digito de control correcto."""
    d = f"{n:07d}"
    par = sum(int(d[i]) for i in (1, 3, 5))
    impar = 0
    for i in (0, 2, 4, 6):
        x = int(d[i]) * 2
        impar += x // 10 + x % 10
    control = (10 - (par + impar) % 10) % 10
    return f"{letra}{d}{'JABCDEFGHI'[control] if letra in 'PQSW' else control}"


def cif_con_control_incorrecto(letra, n):
    """El mismo CIF de cif_valido() pero con el digito de control CAMBIADO, para
    probar que el guard lo detecta.

    Se DERIVA en vez de escribirlo a mano a proposito: un literal con forma de
    NIF en el codigo hace saltar scripts/privacy_scan.py, y la alternativa
    —anadirlo a su lista blanca— seria hacer crecer una lista escrita a mano,
    que es justo lo que este proyecto ha tenido que limpiar dos veces el
    27-08-2026 por haber derivado. Asi el fichero no contiene ni una cadena
    con forma de NIF, y no hace falta ninguna excepcion."""
    bueno = cif_valido(letra, n)
    ultimo = bueno[-1]
    otro = "1" if ultimo == "0" else "0"
    if ultimo.isalpha():
        otro = "A" if ultimo != "A" else "B"
    return bueno[:-1] + otro


def corpus():
    """Facturas sinteticas elegidas para TOCAR cada cambio del dia, mas un
    bloque de control que no deberia moverse. Cada una lleva su etiqueta para
    que el informe diga QUE se estaba probando, no solo que cambio."""
    NIF = cif_valido("B", 1234567)
    base = {
        'nif': NIF, 'proveedor': 'PROVEEDOR SINTETICO SL',
        'fecha_expedicion': '2026-03-15', 'verificacion': 'OK',
    }

    def factura(total, doc, **extra):
        b = round(total / 1.21, 2)
        f = {**base, 'nº_documento': doc, 'base_21': f"{b:.2f}",
             'base_total': f"{b:.2f}", 'iva_total': f"{total - b:.2f}",
             'total_factura': f"{total:.2f}"}
        f.update(extra)
        return f

    # Historicos que se pasan a AMBAS versiones exactamente iguales.
    hist_fijo = {NIF: {'n_facturas_normales': 4, 'media': 121.00, 'desv': 0}}
    hist_var = {NIF: {'n_facturas_normales': 6, 'media': 121.00, 'desv': 2.07}}
    fmt = {NIF: {'ejemplos': ['FAC-97', 'FAC-98', 'FAC-99'], 'n_facturas_vistas': 3}}
    sec_plano = {NIF: {'numeros_vistos': ['A-100', 'B-100']}}
    sec_real = {NIF: {'numeros_vistos': ['F-100', 'F-110', 'F-120']}}

    return [
        # --- Los cambios que SI se querian -------------------------------
        ("importe_atipico: cuota fija y un 10x",
         factura(1210.00, 'FAC-100'), hist_fijo, {}, {}),
        ("importe_atipico: cuota fija y un 825x",
         factura(99999.00, 'FAC-100'), hist_fijo, {}, {}),
        ("importe_atipico: variacion normal, desviacion del 2,5% (era ruido)",
         factura(124.00, 'FAC-100'), hist_var, {}, {}),
        ("estructura_reconocida: cruzar de FAC-99 a FAC-100",
         factura(121.00, 'FAC-100'), {}, fmt, {}),
        ("secuencia_documental: previos identicos (100 y 100)",
         factura(121.00, 'C-500'), {}, {}, sec_plano),
        ("nif_check: DNI con el 0 inicial perdido",
         {**factura(121.00, 'FAC-100'), 'nif': dni_valido(1234567)[1:]}, {}, {}, {}),

        # --- CONTROL: nada de esto deberia moverse ------------------------
        ("control: factura normal, sin historico",
         factura(121.00, 'FAC-100'), {}, {}, {}),
        ("control: importe dentro de patron con variacion normal",
         factura(121.50, 'FAC-100'), hist_var, {}, {}),
        ("control: forma de documento ya conocida",
         factura(121.00, 'FAC-98'), {}, fmt, {}),
        ("control: secuencia real y numero razonable",
         factura(121.00, 'F-130'), {}, {}, sec_real),
        ("control: secuencia real y numero absurdo",
         factura(121.00, 'F-99000'), {}, {}, sec_real),
        ("control: DNI completo y valido",
         {**factura(121.00, 'FAC-100'), 'nif': dni_valido(1234567)}, {}, {}, {}),
        ("control: CIF con digito de control incorrecto",
         {**factura(121.00, 'FAC-100'),
          'nif': cif_con_control_incorrecto("B", 1234567)}, {}, {}, {}),
        ("control: aritmetica rota (base y cuota no cuadran)",
         {**factura(121.00, 'FAC-100'), 'iva_total': '50.00'}, {}, {}, {}),
        ("control: sin ningun importe legible",
         {**base, 'nº_documento': 'FAC-100'}, {}, {}, {}),
        ("control: total en formato espanol",
         {**factura(121.00, 'FAC-100'), 'total_factura': '1.328,90',
          'base_total': '1098,26', 'base_21': '1098,26', 'iva_total': '230,64'},
         {}, {}, {}),
    ]


#: Se ejecuta DENTRO de cada subproceso, con su motor al principio del path.
RUNNER = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
import motor_veredicto as mv
casos = json.load(open(sys.argv[2], encoding="utf-8"))
salida = []
for etiqueta, fila, hist, fmt, sec in casos:
    try:
        v, motivo, guards = mv.evaluar_fila_v4(
            fila, set(), hist, fmt, sec,
            {fila.get("nif", ""): {"titulo": "PROVEEDOR SINTETICO SL",
                                    "cuenta": "400001"}},
            2020, None, 2026)
        salida.append({"etiqueta": etiqueta, "veredicto": v,
                       "motivo": motivo[:160],
                       "guards": {g: e for g, (e, _d) in guards.items()}})
    except Exception as e:
        salida.append({"etiqueta": etiqueta, "veredicto": "EXCEPCION",
                       "motivo": type(e).__name__, "guards": {}})
json.dump(salida, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False)
'''


def montar_version(destino, ref):
    """Deja en `destino` el motor tal y como estaba en `ref` (o el actual si
    ref es None), con el contrato de datos del arbol de hoy."""
    os.makedirs(destino, exist_ok=True)
    for fichero in FICHEROS_MOTOR:
        if ref is None:
            shutil.copy(os.path.join(AQUI, fichero), destino)
        else:
            r = subprocess.run(["git", "show", f"{ref}:{fichero}"],
                               cwd=AQUI, capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            if r.returncode != 0:
                raise RuntimeError(f"no se pudo leer {fichero} de {ref}: {r.stderr[:200]}")
            with open(os.path.join(destino, fichero), "w", encoding="utf-8") as f:
                f.write(r.stdout)
    for fichero in FICHEROS_COMPARTIDOS:
        shutil.copy(os.path.join(AQUI, fichero), destino)


def ejecutar(directorio, ruta_casos, ruta_salida, ruta_runner):
    r = subprocess.run([sys.executable, ruta_runner, directorio, ruta_casos, ruta_salida],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"el motor de {directorio} no pudo evaluar: {r.stderr[-400:]}")
    with open(ruta_salida, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ref", default="HEAD",
                    help="Referencia contra la que comparar el arbol de trabajo. "
                         "Por defecto HEAD: 'que hace el cambio que acabo de "
                         "escribir'. Para mirar atras: --ref 408952f (todo el "
                         "27-08-2026), --ref HEAD~5, etc.")
    args = ap.parse_args()

    casos = corpus()
    tmp = tempfile.mkdtemp(prefix="diff_motor_")
    try:
        ruta_casos = os.path.join(tmp, "casos.json")
        with open(ruta_casos, "w", encoding="utf-8") as f:
            json.dump(casos, f, ensure_ascii=False)
        ruta_runner = os.path.join(tmp, "runner.py")
        with open(ruta_runner, "w", encoding="utf-8") as f:
            f.write(RUNNER)

        dir_antes, dir_ahora = os.path.join(tmp, "antes"), os.path.join(tmp, "ahora")
        try:
            montar_version(dir_antes, args.ref)
        except RuntimeError as e:
            print(f"ERROR: no se pudo montar el motor de '{args.ref}'.\n  {e}",
                  file=sys.stderr)
            sys.exit(2)
        montar_version(dir_ahora, None)
        antes = ejecutar(dir_antes, ruta_casos, os.path.join(tmp, "a.json"), ruta_runner)
        ahora = ejecutar(dir_ahora, ruta_casos, os.path.join(tmp, "b.json"), ruta_runner)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if len(antes) != len(ahora) or len(antes) != len(casos):
        print(f"ERROR: las dos versiones no han evaluado lo mismo "
              f"(casos={len(casos)}, antes={len(antes)}, ahora={len(ahora)}). "
              f"Sin eso, comparar seria inventar.", file=sys.stderr)
        sys.exit(2)

    print("=" * 74)
    print(f"DIFERENCIA DE COMPORTAMIENTO DEL MOTOR   ({args.ref}  ->  arbol actual)")
    print("=" * 74)
    print(f"  Facturas sinteticas evaluadas: {len(casos)}")
    print()

    def guards_movidos(a, b):
        todos = set(a["guards"]) | set(b["guards"])
        return [(g, a["guards"].get(g), b["guards"].get(g)) for g in sorted(todos)
                if a["guards"].get(g) != b["guards"].get(g)]

    cambios, iguales, controles_movidos = [], 0, []
    # ANADIDO tras la primera ejecucion, que destapo un hueco en esta misma
    # herramienta: un guard puede cambiar de respuesta SIN que el veredicto se
    # mueva, y eso sigue siendo un cambio de comportamiento que hay que ver.
    # Paso justo con secuencia_documental_proveedor, que fue de un OK falso a
    # un NO_COMPROBADO honesto: como el guard esta en `exentos`, el veredicto
    # es VERDE en las dos versiones y el informe se lo tragaba entero.
    solo_guard = []
    for a, b in zip(antes, ahora):
        if a["veredicto"] == b["veredicto"]:
            iguales += 1
            if guards_movidos(a, b):
                solo_guard.append((a, b))
            continue
        cambios.append((a, b))
        if a["etiqueta"].startswith("control:"):
            controles_movidos.append((a, b))
    # Un control que cambia SOLO a nivel de guard tambien es un efecto
    # colateral, y la primera version no lo hacia fallar: solo miraba el
    # veredicto. Se anade aqui para que las dos formas de moverse cuenten.
    controles_movidos += [(a, b) for a, b in solo_guard
                          if a["etiqueta"].startswith("control:")]

    if cambios:
        print(f"  CAMBIAN DE VEREDICTO: {len(cambios)}")
        print()
        for a, b in cambios:
            marca = "  ⚠️ " if a["etiqueta"].startswith("control:") else "  •  "
            print(f"{marca}{a['etiqueta']}")
            print(f"       antes: {a['veredicto']:<7} ahora: {b['veredicto']}")
            for g, va, vb in guards_movidos(a, b):
                print(f"         {g}: {va} -> {vb}")
            print()
    else:
        print("  Ningun veredicto cambia.")

    # Un guard que cambia sin mover el veredicto NO es ruido: los guards
    # `exentos` no bajan a AMBAR por si solos, asi que un falso OK suyo es
    # invisible en el veredicto y visible solo aqui.
    if solo_guard:
        print(f"  CAMBIAN DE GUARD SIN CAMBIAR EL VEREDICTO: {len(solo_guard)}")
        print("  (guards exentos: no mueven el veredicto por si solos, pero su")
        print("   respuesta importa — un OK falso suyo se ve aqui y en ningun")
        print("   otro sitio)")
        print()
        for a, b in solo_guard:
            marca = "  ⚠️ " if a["etiqueta"].startswith("control:") else "  •  "
            print(f"{marca}{a['etiqueta']}   (veredicto {a['veredicto']} en las dos)")
            for g, va, vb in guards_movidos(a, b):
                print(f"         {g}: {va} -> {vb}")
            print()

    print(f"  Identicas en veredicto y en guards: "
          f"{iguales - len(solo_guard)} de {len(casos)}")
    print()
    print("-" * 74)
    if controles_movidos:
        print("❌ UN CASO DE CONTROL SE HA MOVIDO.")
        print("   Los 'control:' son los que NO debian cambiar. Si uno se mueve,")
        print("   es un efecto colateral, no el cambio que se buscaba: hay que")
        print("   entenderlo antes de dar la sesion por buena.")
        sys.exit(1)
    if not cambios and not solo_guard:
        print("✅ El motor se comporta EXACTAMENTE igual: ni un veredicto ni un")
        print("   estado de guard se mueve en las 16 facturas. Si esperabas un")
        print("   cambio, tu cambio no esta llegando al motor.")
        return
    print("✅ Todo lo que se mueve esta en casos que SI se querian cambiar.")
    print("   Ningun caso de control se ha movido, ni en veredicto ni en el")
    print("   estado de sus guards: los cambios hacen lo que dicen y nada mas.")


if __name__ == "__main__":
    main()
