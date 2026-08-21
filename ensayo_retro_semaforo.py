#!/usr/bin/env python3
"""ensayo_retro_semaforo.py — ENSAYO EN SECO del script que da el primer numero.

POR QUE EXISTE
--------------
`retro_semaforo.py` es la pieza que convierte "esperar tres meses de facturas"
en "ejecutar un script". Es, con diferencia, lo que mas puede mover el proyecto.
Y hasta hoy NO SE HABIA EJECUTADO NUNCA, ni una sola vez: no hay corpus con el
que probarlo en este entorno, porque los datos reales no entran aqui jamas.

El riesgo de eso no es teorico. Si manana, en el PC de la asesoria, el script
peta en la linea 300 por un `.DAT` con la cabecera distinta o un campo que no
existe, se pierde la sesion entera — y con ella el primer numero real del
proyecto, que lleva un mes sin llegar.

Este ensayo elimina ese riesgo SIN datos reales:

  1. Fabrica un corpus SINTETICO con la misma forma que ContaPlus: contenedores
     .DAT (que son ZIP), con un Diario.dbf dentro, en dBase III, cp1252, con los
     campos que el script busca (ASIEN, SUBCTA, EURODEBE, EUROHABER, IVA,
     TERNIF, BASEIMPO, RECEQUIV, FECHA, DOCUMENTO).
  2. Ejecuta `retro_semaforo.py` contra el, tal cual, como se ejecutaria alli.
  3. Comprueba que termina, que los numeros salen donde tienen que salir, y que
     el modo --inyectar detecta los errores que mete.

QUE SI PRUEBA Y QUE NO
----------------------
  SI: que el script CORRE de punta a punta, que sabe abrir el contenedor, leer
      la cabecera dBase, reconstruir asientos, llamar al motor y escribir sus
      dos salidas. Es fontaneria, y la fontaneria es justo lo que rompe una
      sesion.
  NO: que las cifras que dara con datos REALES sean buenas. Este corpus esta
      fabricado para ser correcto, asi que un VERDE alto aqui no dice nada del
      mundo. La medicion de verdad solo puede hacerse alli.

REGLA DE DATOS
--------------
Todo lo que genera es INVENTADO. Los NIF llevan digito de control valido
—matematicamente correcto, para no medir falsos rojos que solo existen porque
el dato de prueba estaba mal, error ya cometido y documentado— pero no
corresponden a nadie. El corpus se escribe en un directorio TEMPORAL y se borra
al terminar: ningun .DAT toca este repositorio, ni por accidente.

Uso:  python3 ensayo_retro_semaforo.py
"""
import os
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))

# --- NIF inventados con checksum valido -------------------------------------
LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE"
LETRAS_CIF = "JABCDEFGHI"


def dni_valido(n):
    return f"{n:08d}{LETRAS_DNI[n % 23]}"


def cif_valido(letra, n):
    """CIF inventado con digito de control correcto (algoritmo oficial)."""
    d = f"{n:07d}"
    pares = sum(int(d[i]) for i in (1, 3, 5))
    impares = 0
    for i in (0, 2, 4, 6):
        x = int(d[i]) * 2
        impares += x // 10 + x % 10
    control = (10 - (pares + impares) % 10) % 10
    return f"{letra}{d}{control}" if letra in "ABEH" else f"{letra}{d}{LETRAS_CIF[control]}"


# --- Escritura de un dBase III minimo ---------------------------------------
CAMPOS = [
    ("ASIEN", "N", 6), ("SUBCTA", "C", 12), ("EURODEBE", "N", 14),
    ("EUROHABER", "N", 14), ("IVA", "N", 5), ("TERNIF", "C", 15),
    ("BASEIMPO", "N", 14), ("RECEQUIV", "N", 14), ("FECHA", "C", 8),
    ("DOCUMENTO", "C", 10),
]


def escribir_dbf(ruta, filas):
    len_reg = 1 + sum(t for _, _, t in CAMPOS)
    cab = bytearray(32)
    cab[0] = 0x03
    cab[1:4] = bytes((26, 8, 21))           # fecha de creacion, irrelevante
    struct.pack_into("<I", cab, 4, len(filas))
    struct.pack_into("<H", cab, 8, 32 + 32 * len(CAMPOS) + 1)
    struct.pack_into("<H", cab, 10, len_reg)
    with open(ruta, "wb") as f:
        f.write(cab)
        for nombre, tipo, tam in CAMPOS:
            d = bytearray(32)
            d[0:11] = nombre.encode("cp1252").ljust(11, b"\x00")[:11]
            d[11] = ord(tipo)
            d[16] = tam
            d[17] = 2 if tipo == "N" else 0
            f.write(d)
        f.write(b"\x0d")
        for fila in filas:
            f.write(b" ")
            for nombre, tipo, tam in CAMPOS:
                v = fila.get(nombre, "")
                if tipo == "N":
                    s = f"{float(v or 0):.2f}".rjust(tam)[:tam]
                else:
                    s = str(v).ljust(tam)[:tam]
                f.write(s.encode("cp1252", "replace"))
        f.write(b"\x1a")


# --- Corpus sintetico --------------------------------------------------------
def generar_corpus(raiz, n_clientes=3, asientos_por_cliente=40, semilla=21082026):
    rng = random.Random(semilla)
    cuentas_gasto = ["600000", "621000", "623001", "628000", "629000"]
    tipos = [21, 21, 21, 10, 10, 4, 0, 5]
    total_asientos = 0
    # Proveedores COMPARTIDOS entre clientes, cada uno con su cuenta de gasto
    # fija. Sin esto el ensayo no probaria lo unico que el patron de cartera
    # existe para hacer: cruzar clientes. Con NIF distintos en cada carpeta,
    # n_clientes seria 1 en todas partes y la senal fuerte no se ejercitaria
    # jamas — el mismo error de "control que nunca dispara" que caza la FAMILIA G.
    compartidos = [(cif_valido("B", 2000000 + k), cuentas_gasto[k % len(cuentas_gasto)])
                   for k in range(6)]
    for c in range(n_clientes):
        carpeta = os.path.join(raiz, f"CLIENTE_SINTETICO_{c:02d}")
        os.makedirs(carpeta, exist_ok=True)
        filas = []
        asien = 0
        for i in range(asientos_por_cliente):
            asien += 1
            total_asientos += 1
            if i % 2 == 0:                     # mitad de proveedores comunes
                nif, cuenta_gasto = compartidos[i // 2 % len(compartidos)]
            else:
                nif = (cif_valido("B", rng.randrange(10**6, 10**7 - 1)) if i % 3
                       else dni_valido(rng.randrange(10**7, 10**8 - 1)))
                cuenta_gasto = rng.choice(cuentas_gasto)
            tipo = rng.choice(tipos)
            base = round(rng.uniform(20, 3000), 2)
            cuota = round(base * tipo / 100.0, 2)
            total = round(base + cuota, 2)
            fecha = f"20{rng.randrange(16, 25):02d}{rng.randrange(1,13):02d}{rng.randrange(1,29):02d}"
            doc = f"F{rng.randrange(1000, 9999)}"
            comun = {"ASIEN": asien, "TERNIF": nif, "FECHA": fecha, "DOCUMENTO": doc}
            filas.append({**comun, "SUBCTA": cuenta_gasto,
                          "EURODEBE": base, "EUROHABER": 0, "IVA": 0,
                          "BASEIMPO": 0, "RECEQUIV": 0})
            filas.append({**comun, "SUBCTA": "472000", "EURODEBE": cuota,
                          "EUROHABER": 0, "IVA": tipo, "BASEIMPO": base,
                          "RECEQUIV": 0})
            filas.append({**comun, "SUBCTA": "400000", "EURODEBE": 0,
                          "EUROHABER": total, "IVA": 0, "BASEIMPO": 0,
                          "RECEQUIV": 0})
        dbf = os.path.join(carpeta, "Diario.dbf")
        escribir_dbf(dbf, filas)
        # El contenedor: un ZIP con extension .DAT, igual que ContaPlus
        with zipfile.ZipFile(os.path.join(carpeta, f"SP_C_{c:02d}A.DAT"), "w") as z:
            z.write(dbf, "Diario.dbf")
        os.remove(dbf)
    return total_asientos


# --- Comprobaciones ----------------------------------------------------------
fallos = []


def comprobar(nombre, condicion, obtenido=""):
    estado = "OK  " if condicion else "FALLA"
    print(f"  [{estado}] {nombre}" + (f"   -> {obtenido}" if obtenido and not condicion else ""))
    if not condicion:
        fallos.append(nombre)


def main():
    print("=" * 70)
    print("ENSAYO EN SECO DE retro_semaforo.py (corpus sintetico, cero datos reales)")
    print("=" * 70)

    # El NIF inventado tiene que ser valido de verdad, o el ensayo mide su propia
    # chapuza. Se comprueba contra el validador del motor, no contra mi palabra.
    sys.path.insert(0, AQUI)
    from motor_veredicto import valida_nif
    malos = [x for x in [dni_valido(12345678), cif_valido("B", 1234567),
                         cif_valido("A", 9876543), cif_valido("J", 5555555)]
             if not valida_nif(x)[0]]
    comprobar("los NIF inventados pasan el digito de control del propio motor",
              not malos, f"invalidos: {len(malos)}")

    tmp = tempfile.mkdtemp(prefix="ensayo_retro_")
    try:
        n = generar_corpus(tmp)
        dats = [f for _, _, fs in os.walk(tmp) for f in fs if f.endswith(".DAT")]
        comprobar(f"corpus sintetico fabricado ({n} asientos, {len(dats)} contenedores)",
                  len(dats) == 3)

        r = subprocess.run([sys.executable, os.path.join(AQUI, "retro_semaforo.py"), tmp],
                           capture_output=True, text=True, cwd=AQUI)
        salida = r.stdout + r.stderr
        comprobar("retro_semaforo.py termina sin reventar", r.returncode == 0,
                  salida[-500:])
        comprobar("abre los contenedores .DAT (ZIP con Diario.dbf dentro)",
                  "3 contenedores encontrados" in salida, salida[:200])
        comprobar("reconstruye asientos y llama al motor",
                  "VERDE" in salida or "AMBAR" in salida, salida[-400:])
        comprobar("no acumula excepciones del motor",
                  "motor:" not in salida, salida[-400:])

        r2 = subprocess.run([sys.executable, os.path.join(AQUI, "retro_semaforo.py"),
                             tmp, "--inyectar"], capture_output=True, text=True, cwd=AQUI)
        salida2 = r2.stdout + r2.stderr
        comprobar("el modo --inyectar tambien corre entero", r2.returncode == 0,
                  salida2[-500:])
        comprobar("y mide deteccion sobre los errores que mete",
                  "deteccion" in salida2.lower() or "DETECCION" in salida2,
                  salida2[-400:])

        cartera = os.path.join(tmp, "cartera_LOCAL.json")
        # SIN --limite a proposito: la parada temprana corta el recorrido a mitad,
        # asi que el patron saldria de los primeros contenedores y la senal entre
        # clientes no existiria. El script ya lo avisa; aqui se hace bien.
        r3 = subprocess.run([sys.executable, os.path.join(AQUI, "retro_semaforo.py"),
                             tmp, "--emitir-cartera", cartera],
                            capture_output=True, text=True, cwd=AQUI)
        comprobar("--emitir-cartera corre y escribe el fichero",
                  r3.returncode == 0 and os.path.exists(cartera),
                  (r3.stdout + r3.stderr)[-400:])

        r3b = subprocess.run([sys.executable, os.path.join(AQUI, "retro_semaforo.py"),
                              tmp, "--limite", "20", "--emitir-cartera",
                              os.path.join(tmp, "cartera_corta_LOCAL.json")],
                             capture_output=True, text=True, cwd=AQUI)
        comprobar("--limite corre y AVISA de que trunca el patron de cartera",
                  r3b.returncode == 0 and "CORTA tambien el patron" in (r3b.stdout + r3b.stderr),
                  (r3b.stdout + r3b.stderr)[-300:])

        # Que el fichero exista no basta: `{}` tambien existe. Lo que hay que
        # probar es que la senal ENTRE CLIENTES —lo unico que este mapeo aporta
        # sobre el de siempre— llega de verdad al fichero.
        import json as _json
        datos = {}
        if os.path.exists(cartera):
            with open(cartera, encoding="utf-8") as fh:
                datos = _json.load(fh)
        fuertes = [d for d in datos.values()
                   if isinstance(d, dict) and d.get("n_clientes", 0) >= 2]
        comprobar("el fichero trae proveedores, no un {} vacio", len(datos) > 0,
                  f"{len(datos)} entradas")
        comprobar("y la senal fuerte (mismo NIF en 2+ clientes) llega al fichero",
                  len(fuertes) > 0, f"{len(fuertes)} de {len(datos)}")

        # La cadena entera: lo que retro_semaforo emite, .lo lee orquestador?
        # Es el ultimo eslabon de "el criterio sale de los diez anos", y estaba
        # roto hasta hoy sin que nadie lo notara, porque nadie lo habia corrido.
        csv_fact = os.path.join(tmp, "facturas.csv")
        with open(csv_fact, "w", encoding="utf-8", newline="") as fh:
            fh.write("nif,proveedor,nº_documento,fecha_expedicion,base_total,"
                     "base_21,iva_total,total_factura,verificacion\n")
            nif_comun = next(iter(datos), "")
            fh.write(f"{nif_comun},PROV_ENSAYO,F-2026-001,2026-03-15,"
                     f"100.00,100.00,21.00,121.00,OK\n")
        salida_csv = os.path.join(tmp, "veredicto.csv")
        r4 = subprocess.run([sys.executable, os.path.join(AQUI, "orquestador.py"),
                             "--facturas", csv_fact, "--cartera-json", cartera,
                             "--salida", salida_csv, "--config", os.path.join(tmp, "no_existe.json")],
                            capture_output=True, text=True, cwd=AQUI)
        s4 = r4.stdout + r4.stderr
        comprobar("orquestador.py consume el fichero de cartera y termina",
                  r4.returncode == 0 and os.path.exists(salida_csv), s4[-500:])
        comprobar("y declara cuantos proveedores trae ese patron",
                  "Patron de cartera:" in s4, s4[:300])

        # --- El tercer comando de la sesion LOCAL ---------------------------
        # validar_captura_historica.py es el que puede dar el primer numero sobre
        # FALSOS VERDES, que es lo unico que el retro-semaforo NO puede medir.
        # Tampoco se habia ejecutado nunca. Y su gracia es que detecta las
        # columnas solo: justo la clase de cosa que falla en silencio con un
        # fichero que no es el que uno imaginaba.
        csv_hist = os.path.join(tmp, "captura_historica.csv")
        with open(csv_hist, "w", encoding="utf-8", newline="") as fh:
            # Cabeceras a proposito NO canonicas: asi se prueba la deteccion.
            fh.write("NIF;PROVEEDOR;NUM FACTURA;FECHA;BASE;CUOTA IVA;TOTAL;"
                     "VEREDICTO_ANTIGUO;CORRECTO\n")
            for k in range(12):
                base = 100.0 + k
                fh.write(f"{cif_valido('B', 3000000 + k)};PROV_ENSAYO_{k};"
                         f"F-2026-{k:03d};2026-03-15;{base:.2f};"
                         f"{base * 0.21:.2f};{base * 1.21:.2f};VERDE;VERDE\n")
        r5 = subprocess.run([sys.executable, os.path.join(AQUI, "validar_captura_historica.py"),
                             csv_hist, "--columna-humano", "CORRECTO",
                             "--columna-motor", "VEREDICTO_ANTIGUO"],
                            capture_output=True, text=True, cwd=AQUI)
        s5 = r5.stdout + r5.stderr
        comprobar("validar_captura_historica.py corre entero", r5.returncode == 0,
                  s5[-500:])
        comprobar("y detecta solo las columnas de un CSV que no es canonico",
                  "total" in s5.lower() and "nif" in s5.lower(), s5[:400])

        print()
        print("  Nota: que aqui salga mucho VERDE no dice NADA del mundo real. Este")
        print("  corpus esta fabricado para cuadrar. Lo que se prueba es que el")
        print("  script corre de punta a punta, que es lo que rompe una sesion.")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        # Las salidas del script van a su propio directorio, no al temporal.
        for f in ("retro_semaforo_agregado.json", "retro_semaforo_LOCAL.json",
                  "validacion_captura_agregado.json", "validacion_captura_LOCAL.csv"):
            p = os.path.join(AQUI, f)
            if os.path.exists(p):
                os.remove(p)

    print()
    if fallos:
        print(f"FALLAN {len(fallos)}: {fallos}")
        print("Cada uno es una sesion perdida manana si no se arregla hoy.")
        return 1
    print("El ensayo pasa. El script esta listo para correr contra el corpus real.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
