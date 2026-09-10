#!/usr/bin/env python3
"""ensayo_validar_captura.py — ensayo del contador de FALSOS VERDES.

POR QUE HACE FALTA, Y POR QUE ESTE ANTES QUE NINGUN OTRO
--------------------------------------------------------
`validar_captura_historica.py` produce el unico numero del proyecto con un
umbral duro acordado POR ADELANTADO: `SIGUIENTES_PASOS.md` §4 dice que **un
solo falso verde para la automatizacion**. Es tambien lo unico que puede
hablar de falsos verdes: el retro-semaforo no puede, por construccion (que un
asiento se contabilizara asi demuestra que se hizo asi, no que fuera correcto).

Hasta el 09-09-2026 ese script tenia DOS comprobaciones, dentro de
`ensayo_retro_semaforo.py`: que arranca con un CSV de `;` y cabeceras no
canonicas, y que detecta las columnas solo. Las 12 filas que se le daban eran
**todas VERDE/VERDE**, y no se comprobaba ni un numero de la salida — solo
`returncode == 0` y que aparecieran dos palabras en el texto.

    Traducido: si el script contara MAL los falsos verdes, o se dejara alguno
    sin contar, aquel ensayo seguiria en verde.

Estaba probado que FUNCIONA. No estaba probado que sepa ENCONTRAR lo que
busca, que es lo unico para lo que existe.

QUE PRUEBA ESTE ENSAYO
-----------------------
Seis familias, y ninguna se conforma con "no ha petado":

  A. Cuenta EXACTAMENTE los falsos verdes plantados (3 de 10, no "alguno").
  B. Y no inventa ninguno cuando no hay (si no, A la acertaria un contador
     que siempre devuelve 3).
  C. Distingue un falso verde de un desacuerdo cualquiera: motor ROJO con
     humano VERDE es un fallo, pero NO es un falso verde. Un contador ingenuo
     que sumara todos los desacuerdos pasaria A y B y fallaria aqui.
  D. El denominador son las facturas JUZGADAS, no las filas del fichero.
  E. Regresion de los tres defectos encontrados el 09-09-2026 al escribir
     este ensayo (los tres reproducidos antes de tocar codigo).
  F. Regresion del defecto del 21-08-2026: un fichero que se lee como una
     sola columna no produce ningun numero.

TODO LO DE AQUI ES SINTETICO Y ESTA DECLARADO COMO TAL. Los NIF son inventados
con digito de control matematicamente valido (`.claude/rules/datos.md`); los
nombres son `PROV_SINTETICO_n`. Ninguna cifra sale de una factura real.

Uso:
    python ensayo_validar_captura.py
"""
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AQUI = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(AQUI, "validar_captura_historica.py")
AGREGADO = os.path.join(AQUI, "validacion_captura_agregado.json")
LOCAL = os.path.join(AQUI, "validacion_captura_LOCAL.csv")

FALLOS = []


def comprobar(titulo, condicion, detalle=""):
    if condicion:
        print(f"  OK  {titulo}")
    else:
        print(f"  FALLA  {titulo}   {detalle}")
        FALLOS.append(titulo)


def cif_valido(n):
    """CIF inventado con digito de control correcto (algoritmo oficial).

    Inventado a proposito: hace falta que PASE el guard `nif_digito_control`
    para que la factura pueda llegar a VERDE, y un NIF real no se escribe en
    este repositorio bajo ninguna circunstancia."""
    d = f"{n:07d}"
    pares = sum(int(d[i]) for i in (1, 3, 5))
    impares = 0
    for i in (0, 2, 4, 6):
        x = int(d[i]) * 2
        impares += x // 10 + x % 10
    return f"B{d}{(10 - (pares + impares) % 10) % 10}"


# --- Recetas, verificadas contra evaluar_fila_v4 antes de escribirlas -------
# No se dan por supuestas: cada una se comprueba en la familia 0 de abajo, para
# que si el motor cambia y deja de dar el veredicto que aqui se asume, el
# ensayo lo diga en vez de medir otra cosa creyendo que mide esta.
CABECERA = ("nif;proveedor;nº_documento;fecha_expedicion;base_total;"
            "iva_total;total_factura;verificacion;VEREDICTO_ANTIGUO;CORRECTO")


def fila(k, clase, humano, antiguo=""):
    """Una factura sintetica de la clase pedida.

    clase 'verde' -> base/IVA/total coherentes al 21%, NIF valido, captura OK.
    clase 'rojo'  -> el total no cuadra con base+IVA (descuadre de 9 euros).
    clase 'ambar' -> sin `verificacion`: la confianza de captura queda en duda.
    """
    base = 100.0 + k
    iva = round(base * 0.21, 2)
    total = round(base + iva, 2)
    verificacion = "OK"
    if clase == "rojo":
        total = round(total + 9.0, 2)
    elif clase == "ambar":
        verificacion = ""
    return (f"{cif_valido(3200000 + k)};PROV_SINTETICO_{k};F-{k:04d};"
            f"2026-03-15;{base:.2f};{iva:.2f};{total:.2f};{verificacion};"
            f"{antiguo};{humano}")


def escribir(ruta, filas, cabecera=CABECERA):
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        f.write(cabecera + "\n")
        for l in filas:
            f.write(l + "\n")
    return ruta


def ejecutar(ruta_csv, *extra):
    """Corre el script y devuelve (returncode, salida, agregado_o_None)."""
    if os.path.exists(AGREGADO):
        os.remove(AGREGADO)
    r = subprocess.run([sys.executable, SCRIPT, ruta_csv, *extra],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=AQUI)
    agregado = None
    if os.path.exists(AGREGADO):
        with open(AGREGADO, encoding="utf-8") as f:
            agregado = json.load(f)
    return r.returncode, (r.stdout + r.stderr), agregado


def acierto(agregado):
    return (agregado or {}).get("acierto", {})


def main():
    print("=" * 68)
    print("ENSAYO: el contador de FALSOS VERDES")
    print("(todo sintetico — NIF inventados con checksum valido)")
    print("=" * 68)

    # Se guarda a un lado cualquier medicion real que hubiera en la carpeta.
    # En el PC de la asesoria estos dos ficheros pueden ser el resultado de
    # haber pasado las 91 facturas: un ensayo no puede destruirlo por correr.
    respaldo = {}
    for f in (AGREGADO, LOCAL):
        if os.path.exists(f):
            respaldo[f] = f + ".respaldo_ensayo"
            shutil.copy2(f, respaldo[f])

    tmp = tempfile.mkdtemp(prefix="ensayo_valcap_")
    try:
        # === FAMILIA 0 — las recetas son lo que este ensayo cree que son ====
        # Si esto falla, TODO lo de abajo mide otra cosa. Va primero a
        # proposito: es el suelo sobre el que se apoya el resto.
        print("\n=== FAMILIA 0 — las facturas sinteticas dan el veredicto que se asume ===")
        r0 = escribir(os.path.join(tmp, "recetas.csv"),
                      [fila(0, "verde", ""), fila(1, "rojo", ""), fila(2, "ambar", "")])
        _, _, ag0 = ejecutar(r0)
        v0 = (ag0 or {}).get("veredictos_hoy", {})
        comprobar("la receta 'verde' da VERDE, la 'roja' ROJO y la 'ambar' AMBAR",
                  v0 == {"VERDE": 1, "ROJO": 1, "AMBAR": 1},
                  f"veredictos_hoy={v0}")
        comprobar("y no falta ningun campo critico (si no, no se mediria el motor)",
                  ag0 and ag0.get("campos_criticos_ausentes") == []
                  and ag0.get("medicion_valida") is True,
                  f"criticos={(ag0 or {}).get('campos_criticos_ausentes')} "
                  f"valida={(ag0 or {}).get('medicion_valida')}")

        # === FAMILIA A — cuenta EXACTAMENTE los que hay =====================
        print("\n=== FAMILIA A — cuenta exactamente los falsos verdes plantados ===")
        # 10 facturas: 3 falsos verdes (motor VERDE, humano dice que estaba
        # MAL), 5 verdes correctas, 2 rojas correctas. Aciertos = 7 de 10.
        filas_a = ([fila(k, "verde", "MAL") for k in range(3)] +
                   [fila(10 + k, "verde", "VERDE") for k in range(5)] +
                   [fila(20 + k, "rojo", "ROJO") for k in range(2)])
        ruta_a = escribir(os.path.join(tmp, "a.csv"), filas_a)
        _, s_a, ag_a = ejecutar(ruta_a, "--columna-humano", "CORRECTO")
        ac_a = acierto(ag_a)
        comprobar("las 10 se juzgan (ninguna se cae por el camino)",
                  ac_a.get("juzgadas") == 10, f"juzgadas={ac_a.get('juzgadas')}")
        comprobar("cuenta 3 falsos verdes, ni 2 ni 4",
                  ac_a.get("falsos_verdes") == 3,
                  f"falsos_verdes={ac_a.get('falsos_verdes')}")
        comprobar("y el porcentaje es 30.0%, calculado a mano sobre 10",
                  ac_a.get("pct_falsos_verdes") == 30.0,
                  f"pct={ac_a.get('pct_falsos_verdes')}")
        comprobar("la tasa de acierto es 70.0% (7 de 10)",
                  ac_a.get("pct_acierto_hoy") == 70.0,
                  f"pct_acierto={ac_a.get('pct_acierto_hoy')}")
        comprobar("y el numero tambien sale por pantalla, no solo al fichero",
                  "FALSOS VERDES" in s_a and "3" in s_a, s_a[-300:])
        comprobar("la matriz coloca los 3 en la celda VERDE(motor) x ROJO(humano)",
                  ac_a.get("matriz", {}).get("VERDE", {}).get("ROJO") == 3,
                  f"matriz={ac_a.get('matriz')}")

        # === FAMILIA B — y no inventa los que no hay ========================
        # Sin esto, la familia A la aprobaria un contador que devolviera
        # siempre 3. Las dos direcciones o ninguna.
        print("\n=== FAMILIA B — no inventa falsos verdes donde no los hay ===")
        filas_b = [fila(30 + k, "verde", "VERDE") for k in range(8)]
        ruta_b = escribir(os.path.join(tmp, "b.csv"), filas_b)
        _, _, ag_b = ejecutar(ruta_b, "--columna-humano", "CORRECTO")
        ac_b = acierto(ag_b)
        comprobar("8 facturas correctas -> 0 falsos verdes",
                  ac_b.get("falsos_verdes") == 0,
                  f"falsos_verdes={ac_b.get('falsos_verdes')}")
        comprobar("y la tasa de acierto es 100.0%",
                  ac_b.get("pct_acierto_hoy") == 100.0,
                  f"pct_acierto={ac_b.get('pct_acierto_hoy')}")
        comprobar("con estado OK: aqui SI se ha medido, y se publica",
                  ac_b.get("estado") == "OK", f"estado={ac_b.get('estado')}")

        # === FAMILIA C — un desacuerdo NO es un falso verde =================
        # Esta es la que separa un contador de falsos verdes de un contador de
        # desacuerdos. Un falso verde es el motor diciendo VERDE sobre algo
        # que estaba mal: es el error que NO se ve y por eso decide el
        # proyecto. Lo contrario —el motor siendo mas estricto que el humano—
        # es ruido: molesta, no engana.
        print("\n=== FAMILIA C — motor ROJO + humano VERDE es un fallo, NO un falso verde ===")
        filas_c = ([fila(40 + k, "rojo", "VERDE") for k in range(4)] +
                   [fila(50 + k, "verde", "VERDE") for k in range(6)])
        ruta_c = escribir(os.path.join(tmp, "c.csv"), filas_c)
        _, _, ag_c = ejecutar(ruta_c, "--columna-humano", "CORRECTO")
        ac_c = acierto(ag_c)
        comprobar("los 4 desacuerdos cuentan como fallo: acierto 60.0%",
                  ac_c.get("pct_acierto_hoy") == 60.0,
                  f"pct_acierto={ac_c.get('pct_acierto_hoy')}")
        comprobar("pero NINGUNO cuenta como falso verde",
                  ac_c.get("falsos_verdes") == 0,
                  f"falsos_verdes={ac_c.get('falsos_verdes')}")
        comprobar("y van a la celda ROJO(motor) x VERDE(humano), no a la de VERDE",
                  ac_c.get("matriz", {}).get("ROJO", {}).get("VERDE") == 4
                  and "VERDE" not in ac_c.get("matriz", {}).get("ROJO", {}).get("x", {}),
                  f"matriz={ac_c.get('matriz')}")

        # === FAMILIA D — el denominador son las juzgadas ====================
        print("\n=== FAMILIA D — el denominador son las juzgadas, no las filas ===")
        # 10 filas, solo 4 con veredicto humano: 1 falso verde de 4 = 25%.
        # Si el denominador fuera 10 saldria 10%, que es la clase de error que
        # convierte "hay que parar" en "es residual".
        filas_d = ([fila(60, "verde", "MAL")] +
                   [fila(61 + k, "verde", "VERDE") for k in range(3)] +
                   [fila(70 + k, "verde", "") for k in range(6)])
        ruta_d = escribir(os.path.join(tmp, "d.csv"), filas_d)
        _, _, ag_d = ejecutar(ruta_d, "--columna-humano", "CORRECTO")
        ac_d = acierto(ag_d)
        comprobar("10 filas leidas, 4 juzgadas",
                  ag_d.get("filas") == 10 and ac_d.get("juzgadas") == 4,
                  f"filas={ag_d.get('filas')} juzgadas={ac_d.get('juzgadas')}")
        comprobar("1 falso verde sobre 4 juzgadas = 25.0%, no 10.0%",
                  ac_d.get("pct_falsos_verdes") == 25.0,
                  f"pct={ac_d.get('pct_falsos_verdes')}")
        comprobar("las 6 en blanco NO cuentan como descartadas (nadie las juzgo)",
                  ac_d.get("descartadas_por_no_reconocidas") == 0,
                  f"descartadas={ac_d.get('descartadas_por_no_reconocidas')}")

        # === FAMILIA E — regresion de los tres defectos del 09-09-2026 ======
        print("\n=== FAMILIA E — regresion: no publica lo que no ha medido (09-09-2026) ===")

        # E1 — columna humana presente pero sin un solo valor reconocible.
        # Antes: el JSON escribia "falsos_verdes": 0 mientras la pantalla decia
        # "CERO no es el resultado: es la ausencia de resultado".
        filas_e1 = [fila(80 + k, "verde", "") for k in range(5)]
        ruta_e1 = escribir(os.path.join(tmp, "e1.csv"), filas_e1)
        _, s_e1, ag_e1 = ejecutar(ruta_e1, "--columna-humano", "CORRECTO")
        ac_e1 = acierto(ag_e1)
        comprobar("sin ningun veredicto humano -> estado NO_COMPROBADO",
                  ac_e1.get("estado") == "NO_COMPROBADO", f"estado={ac_e1.get('estado')}")
        comprobar("y el agregado NO trae ninguna cifra de falsos verdes",
                  "falsos_verdes" not in ac_e1 and "pct_acierto_hoy" not in ac_e1,
                  f"acierto={ac_e1}")
        comprobar("la pantalla dice que cero no es el resultado",
                  "ausencia de resultado" in s_e1, s_e1[-300:])

        # E2 — hay veredicto humano de verdad, pero faltan campos criticos.
        # Antes: la pantalla decia "LA TASA NO SE PUBLICA... publicarlo seria
        # peor que no tenerlo" y el fichero la publicaba igual.
        ruta_e2 = escribir(os.path.join(tmp, "e2.csv"),
                           [f"PROV_SINTETICO_{k};{100.0+k:.2f};{(100.0+k)*0.21:.2f};VERDE"
                            for k in range(6)],
                           cabecera="proveedor;base_total;iva_total;CORRECTO")
        _, s_e2, ag_e2 = ejecutar(ruta_e2, "--columna-humano", "CORRECTO")
        ac_e2 = acierto(ag_e2)
        comprobar("con criticos ausentes -> estado NO_COMPROBADO, y dice cuales",
                  ac_e2.get("estado") == "NO_COMPROBADO"
                  and ac_e2.get("campos_criticos_ausentes"),
                  f"acierto={ac_e2}")
        comprobar("el agregado NO publica la tasa que la pantalla se niega a dar",
                  "pct_acierto_hoy" not in ac_e2 and "falsos_verdes" not in ac_e2,
                  f"acierto={ac_e2}")
        comprobar("y `medicion_valida` marca en falso TODAS las cifras del fichero",
                  ag_e2.get("medicion_valida") is False,
                  f"medicion_valida={ag_e2.get('medicion_valida')}")

        # E3 — una fila con veredicto humano ESCRITO pero no interpretable no
        # puede caerse en silencio: con ella se caen los falsos verdes que
        # llevara dentro.
        filas_e3 = ([fila(90 + k, "verde", "MAL") for k in range(5)] +
                    [fila(95 + k, "verde", "NO VALIDA") for k in range(5)])
        ruta_e3 = escribir(os.path.join(tmp, "e3.csv"), filas_e3)
        _, s_e3, ag_e3 = ejecutar(ruta_e3, "--columna-humano", "CORRECTO")
        ac_e3 = acierto(ag_e3)
        comprobar("las 5 filas con un veredicto humano ilegible se declaran",
                  ac_e3.get("descartadas_por_no_reconocidas") == 5,
                  f"descartadas={ac_e3.get('descartadas_por_no_reconocidas')}")
        comprobar("y la pantalla avisa de que no estan en el denominador",
                  "DESCARTADAS" in s_e3, s_e3[:900])
        comprobar("las 5 que si se entienden se cuentan como falsos verdes",
                  ac_e3.get("falsos_verdes") == 5 and ac_e3.get("juzgadas") == 5,
                  f"falsos={ac_e3.get('falsos_verdes')} juzgadas={ac_e3.get('juzgadas')}")

        # === FAMILIA F — regresion del separador (21-08-2026) ===============
        print("\n=== FAMILIA F — regresion: un fichero ilegible no da ningun numero (21-08) ===")
        ruta_f = os.path.join(tmp, "f.csv")
        with open(ruta_f, "w", encoding="utf-8", newline="") as f:
            f.write("todo_junto_en_una_sola_columna\n")
            for k in range(4):
                f.write(f"valor_{k}\n")
        rc_f, s_f, ag_f = ejecutar(ruta_f, "--columna-humano", "CORRECTO")
        comprobar("se planta con codigo 2 en vez de seguir",
                  rc_f == 2, f"returncode={rc_f}")
        comprobar("y no escribe NINGUN agregado (ni con ceros)",
                  ag_f is None, f"agregado={ag_f}")
        comprobar("lo dice con todas las letras",
                  "UNA sola columna" in s_f, s_f[:400])

        # === FAMILIA G — el veredicto humano se entiende escrito como se escribe
        print("\n=== FAMILIA G — sinonimos del veredicto humano ===")
        # Si un sinonimo dejara de reconocerse, sus filas se caerian del
        # denominador — y con ellas sus falsos verdes. Se prueba el camino que
        # importa: motor VERDE + humano diciendo que NO, escrito de seis formas.
        sinonimos = ["MAL", "ROJO", "INCORRECTO", "NO", "ERROR", "rojo"]
        filas_g = [fila(110 + k, "verde", s) for k, s in enumerate(sinonimos)]
        ruta_g = escribir(os.path.join(tmp, "g.csv"), filas_g)
        _, _, ag_g = ejecutar(ruta_g, "--columna-humano", "CORRECTO")
        ac_g = acierto(ag_g)
        comprobar(f"las {len(sinonimos)} formas de decir 'estaba mal' cuentan como falso verde",
                  ac_g.get("falsos_verdes") == len(sinonimos),
                  f"falsos_verdes={ac_g.get('falsos_verdes')} de {len(sinonimos)}")
        comprobar("y ninguna se descarta por no entenderse",
                  ac_g.get("descartadas_por_no_reconocidas") == 0,
                  f"descartadas={ac_g.get('descartadas_por_no_reconocidas')}")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        # Se borran las salidas que ha dejado este ensayo y se devuelve a su
        # sitio la medicion real que hubiera antes, si la habia.
        for f in (AGREGADO, LOCAL):
            if os.path.exists(f):
                os.remove(f)
        for original, copia in respaldo.items():
            shutil.move(copia, original)

    print()
    print("=" * 68)
    if FALLOS:
        print(f"FALLAN {len(FALLOS)} comprobaciones:")
        for f in FALLOS:
            print(f"  - {f}")
        print("\nCada una es un falso verde que podria pasar sin contarse el dia")
        print("que se midan las 91 facturas de verdad.")
        return 1
    print("El ensayo pasa. El contador de falsos verdes cuenta los que hay,")
    print("no inventa los que no hay, y no publica lo que no ha medido.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
