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
import ast
import json
import os
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

# Sin esto, una consola de Windows en cp1252 revienta al imprimir el detalle
# capturado de un hijo que a su vez avisa con ⚠️ (retro_semaforo.py --limite,
# los avisos de privacidad). Mismo patron que scripts/privacy_scan.py.
# hasattr() porque sys.stdout no siempre es un TextIOWrapper real (ver
# test_motor_veredicto.py: StringIO no tiene .reconfigure()).
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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
    # +1 SOBRE el terminador (25-08-2026): los ficheros REALES de ContaPlus
    # llevan un byte de relleno extra ahi que la version anterior de este
    # generador no reproducia. Por eso el ensayo dio verde durante dias
    # mientras retro_semaforo.py tenia un bug que desplazaba 32 bytes CADA
    # registro leido contra el corpus real (ver el comentario de
    # retro_semaforo.parse_cabecera). Sin este byte aqui, el ensayo vuelve a
    # quedar ciego si alguien reintroduce esa clase de fallo.
    struct.pack_into("<H", cab, 8, 32 + 32 * len(CAMPOS) + 1 + 1)
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
        f.write(b"\x00")   # el byte de relleno real que ContaPlus si lleva
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
            # BASEIMPO se deja a 0 A PROPOSITO, no relleno con `base`.
            # CORREGIDO 27-08-2026: hasta hoy este generador rellenaba
            # BASEIMPO con el valor real, y por eso el ensayo daba VERDE sin
            # haber probado NADA de la derivacion de base -- exactamente lo
            # que reconstruir_303.py necesitaba y no tenia. Medido con
            # diag_baseimpo.py el 26-08-2026 sobre el corpus real: BASEIMPO
            # es un CERO LITERAL en el 99,4% de los apuntes de IVA (44.243 de
            # 44.522). Rellenarlo aqui con el valor correcto era fabricar un
            # ensayo mas facil que la realidad, y por eso no cazo el bug.
            filas.append({**comun, "SUBCTA": "472000", "EURODEBE": cuota,
                          "EUROHABER": 0, "IVA": tipo, "BASEIMPO": 0,
                          "RECEQUIV": 0})
            filas.append({**comun, "SUBCTA": "400000", "EURODEBE": 0,
                          "EUROHABER": total, "IVA": 0, "BASEIMPO": 0,
                          "RECEQUIV": 0})
            # Una VENTA cada cuatro asientos. Hace falta para que el corpus
            # ejercite tambien el IVA repercutido (477): sin ventas,
            # reconstruir_303.py solo veria la mitad del modelo y el ensayo
            # daria verde sin haber probado ese lado.
            if i % 4 == 0:
                asien += 1
                total_asientos += 1
                comun_v = {"ASIEN": asien, "TERNIF": nif, "FECHA": fecha,
                           "DOCUMENTO": "V" + doc[1:]}
                base_v = round(base * 1.4, 2)
                cuota_v = round(base_v * 21 / 100.0, 2)
                filas.append({**comun_v, "SUBCTA": "430000",
                              "EURODEBE": round(base_v + cuota_v, 2), "EUROHABER": 0,
                              "IVA": 0, "BASEIMPO": 0, "RECEQUIV": 0})
                filas.append({**comun_v, "SUBCTA": "700000", "EURODEBE": 0,
                              "EUROHABER": base_v, "IVA": 0, "BASEIMPO": 0,
                              "RECEQUIV": 0})
                # BASEIMPO a 0 tambien en el lado de ventas, mismo motivo.
                filas.append({**comun_v, "SUBCTA": "477021", "EURODEBE": 0,
                              "EUROHABER": cuota_v, "IVA": 21, "BASEIMPO": 0,
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

    # ANADIDO 28-08-2026 (regresion de bug real, medido contra el corpus real:
    # 198 de 606 "proveedores" con tasa de FALLO >=70% en cuenta_gasto_coherente,
    # resulto ser el mismo puñado de codigos de GRUPO (400/410) repetido en
    # cada cliente, no proveedores reales). reconstruir_compra() usaba l[0]
    # (subcuenta truncada a 3 digitos, solo sirve para CLASIFICAR el tipo de
    # linea) como cuenta_proveedor -- asi que dos proveedores DISTINTOS bajo
    # el mismo grupo de acreedor (410) se veian como UNA sola entidad para
    # guard_cuenta_gasto_coherente. Prueba directa de reconstruir_compra(),
    # sin pasar por DBF/ZIP: mas simple y prueba exactamente la funcion que
    # tenia el bug.
    from retro_semaforo import reconstruir_compra

    def _linea(subcta_trunc, debe, haber, iva, nif, base, subcta_completa):
        return (subcta_trunc, debe, haber, iva, nif, base, "20260115", "F1", 0,
                b"", subcta_completa)

    lineas_prov_a = [
        _linea("600", 82.64, 0, 0, "", 82.64, "60000000"),
        _linea("472", 17.35, 0, 21, "", 0, "47200000"),
        _linea("410", 0, 99.99, 0, dni_valido(11111111), 0, "41000023"),
    ]
    lineas_prov_b = [
        _linea("621", 41.32, 0, 0, "", 41.32, "62100000"),
        _linea("472", 8.68, 0, 21, "", 0, "47200000"),
        _linea("410", 0, 50.00, 0, dni_valido(22222222), 0, "41000099"),
    ]
    fila_a = reconstruir_compra(lineas_prov_a)
    fila_b = reconstruir_compra(lineas_prov_b)
    comprobar("dos proveedores DISTINTOS bajo el mismo grupo de acreedor (410) "
              "reciben cuenta_proveedor DISTINTA",
              isinstance(fila_a, dict) and isinstance(fila_b, dict)
              and fila_a.get("cuenta_proveedor") != fila_b.get("cuenta_proveedor"),
              f"a={fila_a and fila_a.get('cuenta_proveedor')!r} "
              f"b={fila_b and fila_b.get('cuenta_proveedor')!r}")
    comprobar("cuenta_proveedor es la subcuenta COMPLETA, no el grupo truncado a 3",
              isinstance(fila_a, dict) and fila_a.get("cuenta_proveedor") == "41000023"
              and isinstance(fila_b, dict) and fila_b.get("cuenta_proveedor") == "41000099",
              f"a={fila_a and fila_a.get('cuenta_proveedor')!r} "
              f"b={fila_b and fila_b.get('cuenta_proveedor')!r}")
    comprobar("cuenta_debe SIGUE siendo el grupo (3 digitos): el guard ya trunca "
              "el gasto el mismo al comparar, pasarlo completo no aporta nada",
              isinstance(fila_a, dict) and fila_a.get("cuenta_debe") == "600"
              and isinstance(fila_b, dict) and fila_b.get("cuenta_debe") == "621",
              f"a={fila_a and fila_a.get('cuenta_debe')!r} "
              f"b={fila_b and fila_b.get('cuenta_debe')!r}")

    tmp = tempfile.mkdtemp(prefix="ensayo_retro_")
    try:
        n = generar_corpus(tmp)
        dats = [f for _, _, fs in os.walk(tmp) for f in fs if f.endswith(".DAT")]
        comprobar(f"corpus sintetico fabricado ({n} asientos, {len(dats)} contenedores)",
                  len(dats) == 3)

        r = subprocess.run([sys.executable, os.path.join(AQUI, "retro_semaforo.py"), tmp],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", cwd=AQUI)
        salida = r.stdout + r.stderr
        comprobar("retro_semaforo.py termina sin reventar", r.returncode == 0,
                  salida[-500:])
        comprobar("abre los contenedores .DAT (ZIP con Diario.dbf dentro)",
                  "3 contenedores encontrados" in salida, salida[:200])
        comprobar("reconstruye asientos y llama al motor",
                  "VERDE" in salida or "AMBAR" in salida, salida[-400:])
        # Sin esto, el numero de manana engana: en el retro, la MITAD de los
        # AMBAR no habla de la factura, sino del instrumento (el diario no trae
        # el NIF del titular, y el maestro se acumula sobre la marcha). Un 51%
        # de AMBAR que en realidad es un 4% se lee como "el motor molesta".
        comprobar("separa el AMBAR del instrumento del AMBAR de la factura",
                  "del INSTRUMENTO" in salida and "de la FACTURA" in salida,
                  salida[-600:])
        comprobar("no acumula excepciones del motor",
                  "motor:" not in salida, salida[-400:])

        r2 = subprocess.run([sys.executable, os.path.join(AQUI, "retro_semaforo.py"),
                             tmp, "--inyectar"], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", cwd=AQUI)
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
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", cwd=AQUI)
        comprobar("--emitir-cartera corre y escribe el fichero",
                  r3.returncode == 0 and os.path.exists(cartera),
                  (r3.stdout + r3.stderr)[-400:])

        r3b = subprocess.run([sys.executable, os.path.join(AQUI, "retro_semaforo.py"),
                              tmp, "--limite", "20", "--emitir-cartera",
                              os.path.join(tmp, "cartera_corta_LOCAL.json")],
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace", cwd=AQUI)
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
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", cwd=AQUI)
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
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", cwd=AQUI)
        s5 = r5.stdout + r5.stderr
        comprobar("validar_captura_historica.py corre entero", r5.returncode == 0,
                  s5[-500:])
        comprobar("y detecta solo las columnas de un CSV que no es canonico",
                  "total" in s5.lower() and "nif" in s5.lower(), s5[:400])

        # --- El comando completo: CSV -> veredicto -> xDiario ---------------
        # ensayo_xdiario.py prueba escribir_xdiario() directamente. Lo que NO
        # estaba probado es el camino real: el orquestador resolviendo las
        # cuentas contra el maestro y llamando despues a la exportacion. Es la
        # unica forma de saber si --xdiario funciona tal y como se teclea.
        maestro_json = os.path.join(tmp, "maestro.json")
        nif_prov = cif_valido("B", 4100001)
        with open(maestro_json, "w", encoding="utf-8") as fh:
            json.dump({nif_prov: {"titulo": "PROVEEDOR ENSAYO", "cuenta": "400001"}}, fh)
        csv_x = os.path.join(tmp, "facturas_x.csv")
        with open(csv_x, "w", encoding="utf-8", newline="") as fh:
            fh.write("nif,proveedor,nº_documento,fecha_expedicion,base_total,"
                     "base_21,iva_total,total_factura,verificacion,cuenta_debe\n")
            fh.write(f"{nif_prov},PROVEEDOR ENSAYO,FX-001,2026-03-15,"
                     f"100.00,100.00,21.00,121.00,OK,600000\n")
        xdiario = os.path.join(tmp, "xDiario.txt")
        # Con configuracion: sin 'alta_cliente_anio' TODAS las facturas salen
        # AMBAR y no se exporta nada. Es correcto y el orquestador ahora lo
        # avisa, pero para probar la exportacion hace falta la config puesta.
        cfg = os.path.join(tmp, "config_ensayo.json")
        with open(cfg, "w", encoding="utf-8") as fh:
            json.dump({"alta_cliente_anio": 2015, "ejercicio_tanda": 2026}, fh)
        r8 = subprocess.run([sys.executable, os.path.join(AQUI, "orquestador.py"),
                             "--facturas", csv_x, "--maestro-json", maestro_json,
                             "--salida", os.path.join(tmp, "ver_x.csv"),
                             "--xdiario", xdiario, "--config", cfg],
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", cwd=AQUI)
        s8 = r8.stdout + r8.stderr
        comprobar("orquestador --xdiario corre entero", r8.returncode == 0, s8[-500:])
        comprobar("y escribe el fichero que ContaPlus importa",
                  os.path.exists(xdiario) and os.path.getsize(xdiario) > 0,
                  f"existe={os.path.exists(xdiario)}")
        if os.path.exists(xdiario) and os.path.getsize(xdiario) > 0:
            from layout_diario_contaplus import ANCHO_LINEA, leer_ascii_completo
            regs_x = leer_ascii_completo(xdiario)
            debe = round(sum(r.get('EURODEBE') or 0 for r in regs_x), 2)
            haber = round(sum(r.get('EUROHABER') or 0 for r in regs_x), 2)
            comprobar("el asiento que sale del orquestador CUADRA",
                      abs(debe - haber) < 0.01, f"debe={debe} haber={haber}")
            comprobar("la cuenta de proveedor sale del maestro, no inventada",
                      any(r['SUBCTA'].strip() == '400001' for r in regs_x),
                      [r['SUBCTA'].strip() for r in regs_x])

        # Y sin configuracion: TODAS AMBAR, nada exportable, y el orquestador lo
        # DICE. El comportamiento es correcto; lo que faltaba era decirlo.
        r8b = subprocess.run([sys.executable, os.path.join(AQUI, "orquestador.py"),
                              "--facturas", csv_x, "--maestro-json", maestro_json,
                              "--salida", os.path.join(tmp, "ver_x2.csv"),
                              "--config", os.path.join(tmp, "no_existe.json")],
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace", cwd=AQUI)
        comprobar("sin alta_cliente_anio, AVISA de que todo saldra AMBAR",
                  "alta_cliente_anio" in (r8b.stdout + r8b.stderr),
                  (r8b.stdout + r8b.stderr)[:300])

        # --- La cola de revision -------------------------------------------
        # Convierte el veredicto.csv del orquestador en un plan de trabajo
        # agrupado por CAUSA. Cierra el circuito de la clasificacion de AMBAR,
        # que el motor producia desde el 20-08 y no leia nadie.
        csv_ver = os.path.join(tmp, "veredicto_cola.csv")
        with open(csv_ver, "w", encoding="utf-8", newline="") as fh:
            fh.write("nif,proveedor,total_factura,VEREDICTO,MOTIVO\n")
            # Tres causas distintas y una repetida muchas veces: lo que se quiere
            # ver es que la repetida sale la PRIMERA, porque arreglarla una vez
            # quita mas facturas de la cola que arreglar la grave que sale una.
            for _ in range(7):
                fh.write('X,P,121.00,AMBAR,"[FALTA DATO] aritmetica_base_tipo: falta el desglose"\n')
            fh.write('X,P,121.00,AMBAR,"[CRITERIO] nif_casa_historico: proveedor NUEVO"\n')
            fh.write('X,P,121.00,AMBAR,"[CRITERIO] tipo_operacion_especial: inmovilizado"\n')
            fh.write('X,P,121.00,ROJO,"nif_digito_control: CIF invalido | y 1 mas: cuadre_total: DESCUADRE"\n')
            fh.write('X,P,121.00,VERDE,"coherencia formal verificada"\n')
        det = os.path.join(tmp, "cola_LOCAL.csv")
        r7 = subprocess.run([sys.executable, os.path.join(AQUI, "cola_revision.py"),
                             csv_ver, "--detalle", det],
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", cwd=AQUI)
        s7 = r7.stdout + r7.stderr
        comprobar("cola_revision.py corre entero", r7.returncode == 0, s7[-400:])
        comprobar("separa los tres montones de trabajo",
                  "CORREGIR" in s7 and "BUSCAR o VERIFICAR" in s7 and "DECIDIR" in s7,
                  s7[:400])
        comprobar("traduce la causa a lo que hay que HACER, no al nombre del guard",
                  "Conseguir el DESGLOSE" in s7, s7[:400])
        # Los tres montones van en orden fijo (son tres trabajos distintos), asi
        # que la pregunta practica —.por cual empiezo?— la contesta la cabecera
        # "EMPIEZA POR AQUI", que mira las tres a la vez.
        _cab = s7.split("EMPIEZA POR AQUI")[1][:400] if "EMPIEZA POR AQUI" in s7 else ""
        comprobar("dice por que accion empezar: la que mas facturas desbloquea",
                  "7 facturas" in _cab and "DESGLOSE" in _cab,
                  (_cab.strip()[:120] or "no hay cabecera")
                  + "   (esperado: la causa que sale 7 veces)")
        comprobar("y avisa de que esas 7 son UNA tarea, no siete",
                  "es UNA" in _cab, _cab[:120])
        comprobar("un ROJO con dos causas cuenta las DOS",
                  "nif_digito_control" in s7 and "cuadre_total" in s7, s7[:600])
        comprobar("escribe el detalle _LOCAL", os.path.exists(det))
        if os.path.exists(det):
            import json as _j2
            with open(os.path.join(AQUI, "cola_revision_agregado.json"), encoding="utf-8") as fh:
                _ag = _j2.load(fh)
            _texto = _j2.dumps(_ag)
            comprobar("el agregado NO lleva motivos (los motivos llevan importes)",
                      "DESCUADRE" not in _texto and "121" not in _texto,
                      _texto[:200] + "   (esperado: solo recuentos y guards)")

        # --- El cuadre contra la unica verdad externa ---------------------
        # reconstruir_303.py agrega bases y cuotas de IVA por trimestre, que es
        # el contenido de las casillas que Diego puede comparar con el 303 ya
        # presentado. Tampoco se habia ejecutado nunca.
        detalle = os.path.join(tmp, "303_LOCAL.json")
        r6 = subprocess.run([sys.executable, os.path.join(AQUI, "reconstruir_303.py"),
                             tmp, "--detalle", detalle],
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", cwd=AQUI)
        s6 = r6.stdout + r6.stderr
        comprobar("reconstruir_303.py corre entero", r6.returncode == 0, s6[-500:])
        comprobar("agrega los DOS lados: IVA soportado (472) y repercutido (477)",
                  "deducible 21%" in s6 and "devengado 21%" in s6, s6[:600])
        comprobar("escribe el detalle por trimestre", os.path.exists(detalle),
                  detalle)
        if os.path.exists(detalle):
            import json as _j
            with open(detalle, encoding="utf-8") as fh:
                d303 = _j.load(fh)
            trimestres = [t for c in d303.values() for t in c]
            comprobar("hay trimestres reconstruidos, no un {} vacio",
                      len(trimestres) > 0, f"{len(trimestres)} trimestres")
            # La comprobacion que de verdad importa: que las cuotas agregadas
            # cuadren con las bases al tipo declarado. Si no cuadran aqui, con un
            # corpus fabricado para cuadrar, no cuadraran nunca con uno real.
            descuadres = []
            for cli, tris in d303.items():
                for tri, lados in tris.items():
                    for lado, celdas in lados.items():
                        for tipo, v in celdas.items():
                            if not tipo.isdigit():
                                continue
                            esperada = round(v["base"] * int(tipo) / 100.0, 2)
                            if abs(esperada - v["cuota"]) > 0.05:
                                descuadres.append((tri, lado, tipo, v["cuota"], esperada))
            comprobar("cada celda cuadra: base x tipo = cuota agregada",
                      not descuadres, f"{len(descuadres)} celdas descuadran: {descuadres[:3]}")

        print()
        print("  Nota: que aqui salga mucho VERDE no dice NADA del mundo real. Este")
        print("  corpus esta fabricado para cuadrar. Lo que se prueba es que el")
        print("  script corre de punta a punta, que es lo que rompe una sesion.")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        # Las salidas del script van a su propio directorio, no al temporal.
        for f in ("retro_semaforo_agregado.json", "retro_semaforo_LOCAL.json",
                  "validacion_captura_agregado.json", "validacion_captura_LOCAL.csv",
                  "reconstruccion_303_agregado.json", "cola_revision_agregado.json"):
            p = os.path.join(AQUI, f)
            if os.path.exists(p):
                os.remove(p)

    # --- El ALCANCE de las caches: por cliente, igual que produccion --------
    # ANADIDO 27-08-2026, y corrige un error introducido ese mismo dia: las
    # tres caches de historial se inicializaban FUERA del bucle de
    # contenedores, asi que acumulaban mezclando todos los clientes del
    # corpus. Produccion no hace eso: orquestador.py construye el historico
    # con las facturas de UNA tanda (un cliente). Un instrumento que no se
    # comporta como el sistema que mide da un numero que no describe nada.
    #
    # Se comprueba sobre el AST y no ejecutando: el reseteo ocurre dentro de
    # main(), y lo que hay que garantizar es estructural — que NINGUNA cache
    # de historial se quede fuera del bloque de cambio de cliente. Es facil
    # añadir una quinta y olvidarla, y el sintoma seria un numero
    # silenciosamente equivocado, no un error.
    print("\n--- Alcance de las caches de historial (por cliente, no global) ---")
    CACHES = ("historico_acumulado", "formato_acumulado", "secuencia_acumulada",
              "mapeo_cuenta_gasto_cliente")
    fuente = open(os.path.join(AQUI, "retro_semaforo.py"), encoding="utf-8").read()
    arbol = ast.parse(fuente)
    reseteadas = set()
    for nodo in ast.walk(arbol):
        # El bloque `if carpeta_ruta != cliente_actual:` es el cambio de cliente
        if not (isinstance(nodo, ast.If) and isinstance(nodo.test, ast.Compare)
                and isinstance(nodo.test.left, ast.Name)
                and nodo.test.left.id == "carpeta_ruta"):
            continue
        for asig in ast.walk(nodo):
            if isinstance(asig, ast.Assign) and isinstance(asig.value, ast.Dict) \
                    and not asig.value.keys:
                for t in asig.targets:
                    if isinstance(t, ast.Name):
                        reseteadas.add(t.id)
    for cache in CACHES:
        comprobar(f"'{cache}' se resetea al cambiar de cliente",
                  cache in reseteadas,
                  "si no, acumula mezclando clientes y la medicion deja de "
                  "describir lo que hara produccion")

    # --- Paridad de llamada: medicion vs produccion -------------------------
    # ANADIDO 27-08-2026. La medicion existe para predecir que hara el motor en
    # produccion, asi que TODA diferencia entre como le llama retro_semaforo.py
    # y como le llama orquestador.py cambia lo que significa el numero. Se
    # exige que cada diferencia este DECLARADA con su motivo.
    #
    # HONESTIDAD SOBRE EL ALCANCE, para que nadie confie de mas en esto: esta
    # comprobacion NO habria cazado el error de las caches de arriba. Alli los
    # parametros SI se pasaban —con el alcance equivocado—, y el alcance no se
    # ve en el punto de llamada. De eso se ocupa la comprobacion anterior. Lo
    # que esta si caza, y no cubre nada mas hoy: un parametro que produccion
    # pasa y la medicion omite, y una CONSTANTE fija donde produccion usa un
    # dato real.
    print("\n--- Paridad de llamada al motor: medicion vs produccion ---")

    #: Diferencias aceptadas, con su motivo. No es "esto da igual": es POR QUE
    #: la medicion tiene que apartarse de produccion en este punto concreto.
    DIVERGENCIAS_DECLARADAS = {}
    DIVERGENCIAS_DECLARADAS["retro_semaforo.py"] = {
        "alta_cliente_anio": (
            "Fijado a 1990 a proposito. Produccion lo lee del config de CADA "
            "cliente; el corpus historico mezcla ~24 clientes cuyo año de alta "
            "no se conoce, y no hay de donde sacarlo. Con 1990, ninguna factura "
            "del corpus (2011-2026) es anterior al alta, asi que "
            "guard_fecha_posterior_alta no dispara nunca y no contamina la "
            "medicion con un ROJO que solo dice 'no se el año de alta'. "
            "Consecuencia declarada: esta medicion NO dice nada sobre ese guard."
        ),
        "nif_cliente_titular": (
            "None a proposito: el diario no trae el NIF del titular. Ya estaba "
            "declarado en AMBAR_DEL_INSTRUMENTO de retro_semaforo.py, que "
            "cuenta como 'ambar del instrumento' —no de la factura— el "
            "sentido_compra_venta que esto deja sin comprobar."
        ),
        "mapeo_cartera": (
            "No se pasa. Comprobado empiricamente el 27-08-2026 que NO cambia "
            "el veredicto: guard_patron_cartera nunca devuelve OK (a proposito, "
            "un patron es una hipotesis) y esta en `exentos`, asi que su "
            "NO_APLICA no baja a AMBAR. Solo enriquece el MOTIVO. Ademas, el "
            "patron de cartera de retro_semaforo se construye con el corpus "
            "ENTERO y usarlo durante la evaluacion seria una fuga de datos "
            "(facturas futuras informando decisiones pasadas), el mismo error "
            "que ya se corrigio para el maestro el 21-08."
        ),
        "plazos_cache": (
            "La medicion lo omite y produccion pasa {}. EQUIVALENTE: el motor "
            "hace `plazos_cache = plazos_cache or {}`, asi que omitirlo da el "
            "mismo {} exacto. Se declara igualmente para que la lista sea el "
            "retrato COMPLETO de las diferencias y no haya que volver a "
            "averiguar si esta es inocua."
        ),
        "vistos_duplicado": (
            "Solo en la llamada de --inyectar, que pasa un set() nuevo en vez "
            "del acumulado. Es DELIBERADO y protege la tasa de deteccion, "
            "aunque no estaba escrito en ninguna parte hasta el 27-08-2026:\n"
            "  La clave documental es (nif, nº_documento, fecha, total). El "
            "error inyectado 'tipo_iva_cambiado' altera SOLO el IVA, asi que "
            "los cuatro campos de la clave quedan IDENTICOS a los de la factura "
            "original, que ya esta en el acumulado. Con el set compartido, "
            "anti_duplicado dispararia -> ROJO -> se contaria como DETECTADO, "
            "pero por el motivo equivocado: el motor no habria visto el IVA "
            "mal, habria visto un duplicado que solo existe porque la propia "
            "medicion fabrico la copia.\n"
            "  Con set() nuevo, cada inyeccion se juzga por su propio defecto. "
            "Ninguno de los cinco tipos inyectados es un duplicado, asi que no "
            "se pierde deteccion de nada: solo se evita apuntarse una que no "
            "es. Es la misma disciplina que el resto del proyecto: mas vale no "
            "contar un acierto que contarlo por la razon que no es."
        ),
    }
    # El OTRO script de medicion, el que va a producir el numero de FALSOS
    # VERDES -- la metrica que SIGUIENTES_PASOS.md §4 dice que decide el
    # proyecto, con un umbral de "≥ 1 falso verde -> se para la
    # automatizacion". El 27-08-2026 se le anadieron --nif-titular,
    # --ejercicio y --mapeo-gasto-json, que NO tenia: sin ellos, guards que
    # produccion si corre quedaban en NO_APLICA y la medicion salia mas
    # pesimista que el motor real.
    DIVERGENCIAS_DECLARADAS["validar_captura_historica.py"] = {
        "mapeo_cartera": (
            "Mismo motivo que en retro_semaforo.py: guard_patron_cartera nunca "
            "devuelve OK y esta en `exentos`, asi que no cambia el veredicto. "
            "Comprobado empiricamente el 27-08-2026."
        ),
        "plazos_cache": (
            "Omitido; el motor hace `plazos_cache or {}`, asi que es "
            "EQUIVALENTE al {} que pasa produccion."
        ),
    }

    def _args_de_llamada(fichero):
        """Nombre de parametro -> expresion, para cada llamada a
        evaluar_fila_v4. Normaliza posicionales a su nombre de parametro."""
        POS = ['fila', 'vistos_duplicado', 'historico_proveedor', 'formato_cache',
               'secuencia_cache', 'maestro_proveedores', 'alta_cliente_anio',
               'nif_cliente_titular', 'ejercicio_tanda', 'plazos_cache',
               'mapeo_cuenta_gasto', 'mapeo_cartera']
        llamadas = []
        arbol_f = ast.parse(open(os.path.join(AQUI, fichero), encoding="utf-8").read())
        for n in ast.walk(arbol_f):
            if not isinstance(n, ast.Call):
                continue
            nombre = getattr(n.func, 'attr', None) or getattr(n.func, 'id', None)
            if nombre != 'evaluar_fila_v4':
                continue
            args = {POS[i]: ast.unparse(a) for i, a in enumerate(n.args) if i < len(POS)}
            args.update({k.arg: ast.unparse(k.value) for k in n.keywords if k.arg})
            llamadas.append(args)
        return llamadas

    prod = _args_de_llamada("orquestador.py")
    comprobar("se encuentra la llamada al motor en produccion", len(prod) >= 1,
              f"produccion={len(prod)}")

    for fichero, declaradas in DIVERGENCIAS_DECLARADAS.items():
      medicion = _args_de_llamada(fichero)
      comprobar(f"{fichero}: se encuentra su llamada al motor", len(medicion) >= 1,
                f"medicion={len(medicion)}")
      if prod and medicion:
        params_prod = set(prod[0])
        divergencias = set()
        for llamada in medicion:
            # 1. Parametros que produccion pasa y la medicion omite.
            divergencias |= (params_prod - set(llamada))
            # 2. Constantes fijas donde produccion usa una variable.
            for p, expr in llamada.items():
                if p in params_prod and expr != prod[0].get(p):
                    try:
                        ast.literal_eval(expr)
                        divergencias.add(p)
                    except (ValueError, SyntaxError):
                        pass          # otra variable: no es una constante fija

        sin_declarar = sorted(divergencias - set(declaradas))
        comprobar(f"{fichero}: toda divergencia con produccion esta declarada",
                  not sin_declarar,
                  f"SIN DECLARAR: {sin_declarar} — cada una cambia lo que "
                  f"significa el numero de la medicion")

        caducadas = sorted(set(declaradas) - divergencias)
        comprobar(f"{fichero}: sin divergencias declaradas que ya no existan",
                  not caducadas,
                  f"CADUCADAS: {caducadas} — una lista que conserva entradas "
                  f"muertas acaba tapando una divergencia real")

    print()
    if fallos:
        print(f"FALLAN {len(fallos)}: {fallos}")
        print("Cada uno es una sesion perdida manana si no se arregla hoy.")
        return 1
    print("El ensayo pasa. El script esta listo para correr contra el corpus real.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
