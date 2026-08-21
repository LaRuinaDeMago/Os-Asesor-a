#!/usr/bin/env python3
"""test_privacidad.py — control positivo de la barrera mas importante del proyecto.

POR QUE ESTO FALTABA, Y POR QUE IMPORTA MAS QUE CUALQUIER TEST DEL MOTOR
------------------------------------------------------------------------
`.claude/rules/datos.md` empieza diciendo "la regla mas importante de todo el
proyecto". El unico mecanismo que la hace cumplir es `scripts/privacy_scan.py`.
Y hasta hoy ese mecanismo NO TENIA NI UNA SOLA PRUEBA.

No es una hipotesis de que podria fallar: ya fallo. El 19-08-2026, un ZIP llamado
`SP_C_04A.DAT` —el formato real de los contenedores de ContaPlus— devolvia
`Escaner de privacidad: sin hallazgos` y codigo de salida 0. No solo se colaba:
ademas se declaraba limpio. El agujero estuvo abierto ocho dias y se encontro a
mano, con un fichero trampa hecho a proposito.

Un "sin hallazgos" que significa "no lo he mirado" es exactamente el falso verde
que este motor tiene prohibido dar, cometido por la barrera que protege los datos
de los clientes. Esa comprobacion a mano se convierte aqui en algo que corre solo.

QUE COMPRUEBA
-------------
Que la barrera BLOQUEA lo que tiene que bloquear (control positivo, el que de
verdad importa) y que DEJA PASAR lo que tiene que dejar pasar (control negativo:
una barrera que bloquea todo tampoco sirve, porque se acaba desactivando).

Y se comprueba a si mismo: si se sabotea el escaner, esta bateria tiene que
ponerse roja. Si no, no esta probando nada.

REGLA DE DATOS
--------------
Ni un solo dato real. Los NIF son los ya declarados como sinteticos en el propio
escaner. Todo se escribe en un directorio TEMPORAL y se borra al terminar: ningun
fichero trampa toca este repositorio, que seria justo lo que la regla prohibe.

Uso:  python3 test_privacidad.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
ESCANER = os.path.join(AQUI, "scripts", "privacy_scan.py")

resultados = []


def comprobar(nombre, condicion, detalle="", severidad="P1"):
    resultados.append((nombre, condicion, detalle, severidad))
    print(f"  [{'OK  ' if condicion else 'FALLA'}] {nombre}"
          + (f"\n           {detalle}" if not condicion and detalle else ""))


def escanea(path):
    """Devuelve True si la barrera BLOQUEA ese fichero."""
    r = subprocess.run([sys.executable, ESCANER, path],
                       capture_output=True, text=True, cwd=AQUI)
    return r.returncode != 0


def escribir(tmp, nombre, contenido, binario=False):
    p = os.path.join(tmp, nombre)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb" if binario else "w", encoding=None if binario else "utf-8") as f:
        f.write(contenido)
    return p


def zip_bytes():
    import io, zipfile
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("Diario.dbf", "contenido cualquiera")
    return b.getvalue()


def main():
    print("=" * 72)
    print("BARRERA DE PRIVACIDAD — control positivo")
    print("=" * 72)
    tmp = tempfile.mkdtemp(prefix="trampa_privacidad_")
    try:
        # --- Lo que TIENE que bloquear ------------------------------------
        print("\nDEBE BLOQUEAR:")

        # El incidente real del 19-08: ZIP con extension .DAT
        comprobar("un ZIP disfrazado de .DAT (el caso real de ContaPlus)",
                  escanea(escribir(tmp, "SP_C_04A.DAT", zip_bytes(), binario=True)),
                  "es EL agujero que estuvo abierto ocho dias", "P0")
        comprobar("un ZIP disfrazado de .txt",
                  escanea(escribir(tmp, "parece_texto.txt", zip_bytes(), binario=True)),
                  severidad="P0")
        comprobar("un .zip por extension, aunque este vacio",
                  escanea(escribir(tmp, "cualquiera.zip", b"", binario=True)),
                  "regla fija: ningun zip sube NUNCA, revisado o no", "P0")
        comprobar("un PDF disfrazado de .md",
                  escanea(escribir(tmp, "informe.md", b"%PDF-1.7\nbasura", binario=True)),
                  severidad="P0")
        comprobar("un documento Office antiguo disfrazado de .py",
                  escanea(escribir(tmp, "modulo.py", b"\xd0\xcf\x11\xe0algo", binario=True)),
                  severidad="P0")
        comprobar("un binario NO reconocido (no se declara limpio lo no mirado)",
                  escanea(escribir(tmp, "raro.bin", b"\x00\x01\x02\x03" * 40, binario=True)),
                  "un 'sin hallazgos' que significa 'no lo he mirado' es el falso "
                  "verde de la barrera", "P0")

        # Contenido sensible en ficheros de texto
        comprobar("un DNI en un .py",
                  escanea(escribir(tmp, "codigo.py", "cliente = '87654321X'\n")),
                  severidad="P0")
        comprobar("un CIF en un .md",
                  escanea(escribir(tmp, "notas.md", "El proveedor B87654321 factura...\n")),
                  severidad="P0")
        comprobar("un DNI en un .sh (agujero encontrado el 19-08)",
                  escanea(escribir(tmp, "script.sh", "#!/bin/sh\necho 87654321X\n")),
                  "los .sh nunca se habian escaneado", "P0")
        comprobar("un DNI en .gitignore (mismo agujero)",
                  escanea(escribir(tmp, "punto_gitignore", "# 87654321X\n")),
                  severidad="P0")
        comprobar("un IBAN",
                  escanea(escribir(tmp, "pagos.txt", "ES9121000418450200051332\n")),
                  severidad="P0")
        comprobar("un email",
                  escanea(escribir(tmp, "contacto.txt", "correo: alguien@ejemplo.com\n")),
                  severidad="P1")
        # Prefijo conocido: lo cubria ya.
        comprobar("una clave de API con prefijo conocido",
                  escanea(escribir(tmp, "conf.py",
                                   "K = 'sk-ant-api03-" + "A" * 40 + "'\n")),
                  severidad="P0")
        # Y la FORMA del descuido, que es lo que la regla prohibe de verdad:
        # escribir una clave en un fichero. Esto SI se colaba hasta el 21-08.
        comprobar("una clave sin prefijo conocido, asignada en el codigo",
                  escanea(escribir(tmp, "conf2.py",
                                   'ANTHROPIC_API_KEY = "clave-de-otro-proveedor-sin-prefijo"\n')),
                  "la regla es 'ninguna clave se escribe en un fichero', no "
                  "'ninguna clave de estos seis proveedores'", "P0")
        comprobar("una contrasena de base de datos asignada en el codigo",
                  escanea(escribir(tmp, "conf3.py", 'DB_PASSWORD = "Sup3rS3cret0!2026"\n')),
                  severidad="P0")

        # --- Lo que NO debe bloquear --------------------------------------
        # Una barrera que bloquea todo se acaba desactivando, y entonces no
        # bloquea nada. El falso positivo tambien es un fallo.
        print("\nDEBE DEJAR PASAR:")
        comprobar("codigo normal sin nada sensible",
                  not escanea(escribir(tmp, "limpio.py",
                                       "def suma(a, b):\n    return a + b\n")),
                  severidad="P1")
        comprobar("los NIF sinteticos ya declarados en el propio escaner",
                  not escanea(escribir(tmp, "test_algo.py",
                                       "NIF = 'B12345674'\nOTRO = '12345678Z'\n")),
                  severidad="P1")
        comprobar("un fichero de texto en cp1252 con enes y acentos",
                  not escanea(escribir(tmp, "acentos.txt",
                                       "Numero de asientos: cañeria, año, presupuesto\n")),
                  severidad="P1")
        comprobar("un importe de ocho cifras no es un DNI",
                  not escanea(escribir(tmp, "importes.csv",
                                       "total\n12345678.90\n")),
                  severidad="P1")
        # La regla de secretos tiene que dejar en paz a la documentacion y al
        # codigo que hace lo CORRECTO. Si no, alguien desactiva el hook y
        # entonces no protege de nada. Este repo menciona ANTHROPIC_API_KEY en
        # prosa docenas de veces.
        for _txt, _caso in (
                ('clave = os.getenv("ANTHROPIC_API_KEY")\n', "leer la clave del entorno"),
                ('ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]\n', "asignarla desde el entorno"),
                ('API_KEY = "TU_CLAVE_AQUI"\n', "un hueco con instrucciones"),
                ('API_KEY = "<pon-la-aqui>"\n', "un hueco entre angulos"),
                ('token = "${MI_TOKEN}"\n', "una expansion de variable"),
                ('GEMINI_API_KEY = ""\n', "un valor vacio"),
                ('parser.add_argument("--api-key", help="clave de la API")\n', "un argumento de CLI"),
                ('# Se configura ANTHROPIC_API_KEY como variable de entorno\n', "prosa en un comentario")):
            comprobar(f"no bloquea {_caso}",
                      not escanea(escribir(tmp, f"ok_{abs(hash(_caso)) % 10000}.py", _txt)),
                      "un escaner que grita de mas se acaba desactivando", "P1")

        # El control de falsos positivos que de verdad manda: el repositorio
        # entero. Si una regla nueva bloquea la documentacion del propio
        # proyecto, la regla esta mal, por muy bien intencionada que sea.
        _repo = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=AQUI)
        _ficheros = [f for f in _repo.stdout.split() if f]
        _r = subprocess.run([sys.executable, ESCANER] + _ficheros,
                            capture_output=True, text=True, cwd=AQUI)
        comprobar(f"el repositorio entero ({len(_ficheros)} ficheros) sigue limpio",
                  _r.returncode == 0, _r.stdout[-400:], "P0")

        # --- Control negativo de esta misma bateria -----------------------
        # Si con el escaner saboteado la bateria sigue en verde, no prueba nada.
        print("\nCONTROL NEGATIVO (esta bateria, .sabe ponerse roja?):")
        copia = os.path.join(tmp, "escaner_saboteado.py")
        with open(ESCANER, encoding="utf-8") as f:
            fuente = f.read()
        # Un escaner que siempre dice "sin hallazgos": exactamente el fallo real.
        fuente = fuente.replace("def escanear(archivos):",
                                "def escanear(archivos):\n    return []", 1)
        with open(copia, "w", encoding="utf-8") as f:
            f.write(fuente)
        trampa = escribir(tmp, "trampa_control.DAT", zip_bytes(), binario=True)
        r = subprocess.run([sys.executable, copia, trampa],
                           capture_output=True, text=True, cwd=AQUI)
        comprobar("con el escaner saboteado, el ZIP disfrazado SE CUELA",
                  r.returncode == 0,
                  "si esto falla, el sabotaje no funciono y el control no vale",
                  "P0")
        print("           (es lo que pasaba de verdad hasta el 19-08-2026)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    fallos = [r for r in resultados if not r[1]]
    p0 = [r for r in fallos if r[3] == "P0"]
    print()
    print("=" * 72)
    print(f"Pruebas: {len(resultados)}   en verde: {len(resultados)-len(fallos)}   "
          f"FALLAN: {len(fallos)}  (de ellas P0: {len(p0)})")
    if fallos:
        print("\nLA BARRERA DE PRIVACIDAD TIENE HUECOS:")
        for nombre, _, detalle, sev in fallos:
            print(f"  [{sev}] {nombre}")
        return 1
    print("\nLa barrera bloquea lo que debe, deja pasar lo que debe, y esta")
    print("bateria ha demostrado que sabria ponerse roja si dejara de hacerlo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
