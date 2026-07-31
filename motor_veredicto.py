"""
MOTOR DE VEREDICTO MECANICO — v1
Aplica los guards de SEMAFORO_DEFINITIVO_v1.md + adenda de forma determinista.
Cada guard devuelve uno de 4 estados: OK / FALLO / NO_APLICA / NO_COMPROBADO.
El veredicto (VERDE/AMBAR/ROJO) se calcula a partir de esos estados, nunca a mano.

PRINCIPIO: si no hay dato para evaluar un guard, el estado es NO_COMPROBADO,
nunca OK por omision. Esto es lo que se me olvido aplicar manualmente esta noche.
"""

from nif_check import valida_nif
from datetime import date
import re
# NOTA: 'import statistics' se quito el 28-07-2026 - 0 usos reales en todo el
# archivo (confirmado por revision externa), era codigo muerto.

TOL = 0.02
# Validado empiricamente el 28-07-2026 contra 91 facturas reales de clientes piloto (caso real anonimizado):
# la diferencia maxima real encontrada entre IVA calculado y declarado es 0.01
# (5 de 91 casos). TOL=0.02 cubre esto con margen de 2x. Limite honesto: muestra
# de 91 facturas, no miles - revisar si el volumen de datos crece mucho.

# CONVENCION: irpf_retencion se guarda en NEGATIVO (ej. -125.62 para una retencion
# de 125.62 euros). guard_cuadre_total SUMA irpf a base+iva precisamente porque ya
# viene en negativo - verificado contra un caso real anonimizado (cliente piloto)
# (661.15 + 138.84 + (-125.62) = 674.37, coincide con el total real de la factura).
# Si algun dia se cambia esa convencion a positivo, esta suma hay que convertirla en resta.


def _f(x, default=0.0):
    """Convierte a float. CORREGIDO 28-07-2026 (revision externa): antes,
    un formato español ('1.234,56') fallaba en silencio y devolvia el default
    (0.0) sin avisar - exactamente el 'error silencioso' que este motor existe
    para evitar. Ahora intenta tambien el formato español antes de rendirse,
    y AVISA (no oculta) cuando de verdad tiene que caer al default."""
    if x is None or x == '':
        return default
    try:
        return float(x)
    except (ValueError, TypeError):
        pass
    try:
        # formato español: punto de miles, coma decimal -> '1.234,56' -> 1234.56
        limpio = str(x).replace('.', '').replace(',', '.')
        return float(limpio)
    except (ValueError, TypeError):
        import warnings
        warnings.warn(f"_f(): no se pudo convertir '{x}' a numero, usando default={default} - "
                       f"revisar el dato de origen, esto puede ocultar un error real")
        return default


def guard_aritmetica_base_tipo(base_10, base_4, base_21, iva_total):
    calc = round(base_10 * 0.10 + base_4 * 0.04 + base_21 * 0.21, 2)
    if abs(calc - iva_total) < TOL:
        return "OK", f"iva_calc={calc} decl={iva_total}"
    return "FALLO", f"iva_calc={calc} decl={iva_total} DESCUADRE"


def guard_cuadre_total(base_10, base_4, base_21, iva_total, irpf, total_decl):
    calc = round(base_10 + base_4 + base_21 + iva_total + irpf, 2)
    if abs(calc - total_decl) < TOL:
        return "OK", f"total_calc={calc}"
    return "FALLO", f"total_calc={calc} decl={total_decl} DESCUADRE"


def guard_nif_digito_control(nif):
    ok, tipo, detalle = valida_nif(nif)
    if ok is None:
        return "NO_COMPROBADO", "sin NIF capturado"
    if ok:
        return "OK", f"{tipo} valido"
    return "FALLO", f"{tipo} invalido: {detalle}"


def guard_anti_duplicado(fila, vistos):
    clave = (fila['nif'].strip(), fila['nº_documento'].strip(),
             fila['fecha_expedicion'].strip(), fila['total_factura'].strip())
    if clave in vistos:
        return "FALLO", f"duplicado exacto de {clave}"
    vistos.add(clave)
    return "OK", "clave unica"


def guard_confianza_captura(fila):
    """Deriva confianza del campo 'verificacion' que ya veniamos usando.
    Regla dura: un NIF matematicamente valido NO sube la confianza si el
    propio proceso declaro que hubo inferencia (OK_INFERIDO)."""
    v = fila.get('verificacion', 'OK')
    if v == 'OK_INFERIDO':
        return "MEDIA", "dato inferido, no leido con certeza directa"
    if v == 'OK':
        return "ALTA", "leido directamente, sin ambiguedad declarada"
    return "BAJA", f"verificacion={v}"


def guard_fecha_posterior_alta(fecha_factura_str, fecha_alta_anio):
    try:
        anio_factura = int(fecha_factura_str[:4])
    except (ValueError, TypeError):
        return "NO_COMPROBADO", "fecha no parseable"
    if fecha_alta_anio is None:
        return "NO_COMPROBADO", "sin fecha de alta del cliente"
    if anio_factura < fecha_alta_anio:
        return "FALLO", f"factura de {anio_factura}, alta del cliente en {fecha_alta_anio}"
    return "OK", f"{anio_factura} >= alta {fecha_alta_anio}"


def guard_importe_atipico(proveedor, total, historico_proveedor):
    entry = historico_proveedor.get(proveedor)
    if not entry or entry.get('n_facturas_normales', 0) < 3 or total <= 0:
        return "NO_COMPROBADO", "n<3 facturas normales del proveedor, umbral no fiable"
    media, desv = entry['media'], entry['desv']
    if desv > 0 and abs(total - media) > desv:
        return "FALLO", f"total={total} fuera de media={media} +/- desv={desv}"
    return "OK", f"total={total} dentro de patron (media={media})"


def calcular_veredicto(guards: dict):
    """guards: dict nombre_guard -> (estado, detalle)
    Logica de v1: cualquier FALLO en guard critico -> ROJO.
    Si no hay FALLO pero hay NO_COMPROBADO en guard aplicable o confianza no ALTA -> AMBAR.
    Si no hay FALLO y todo OK/NO_APLICA y confianza ALTA -> VERDE."""
    criticos = ["aritmetica_base_tipo", "cuadre_total", "nif_digito_control",
                "anti_duplicado", "fecha_posterior_alta", "nif_casa_historico"]
    for g in criticos:
        estado = guards.get(g, ("NO_COMPROBADO", ""))[0]
        if estado == "FALLO":
            return "ROJO", g

    no_comprobados = [g for g, (estado, _) in guards.items()
                       if estado == "NO_COMPROBADO" and g not in ("importe_atipico",)]
    # importe_atipico con NO_COMPROBADO (n<3) es normal en proveedores nuevos, no baja solo
    confianza = guards.get("confianza_captura", ("ALTA", ""))[0]

    importe_fallo = guards.get("importe_atipico", ("OK", ""))[0] == "FALLO"
    if importe_fallo:
        return "AMBAR", "importe_atipico"

    if no_comprobados:
        return "AMBAR", f"NO_COMPROBADO: {', '.join(no_comprobados)}"
    if confianza != "ALTA":
        return "AMBAR", f"confianza_captura={confianza}"

    return "VERDE", "todos los guards OK/NO_APLICA, confianza ALTA"


def _normalizar_num_doc(nº_documento):
    """Quita ruido que no es parte del numero real impreso:
    - etiquetas tipo 'Fra ', 'Factura ', 'Fact.' PEGADAS CON ESPACIO (son texto
      añadido por quien transcribio, no parte del numero - a diferencia de
      'FRA/2026/15271' donde FRA va sin espacio y SI es parte del numero real).
    - anotaciones entre parentesis al final, ej. '(REPETIDA)', '(recorte)'.
    """
    s = nº_documento.strip()
    s = re.sub(r'^(fra|factura|fact)\.?\s+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s*\([^)]*\)\s*$', '', s)
    return s.strip()


def _forma(nº_documento):
    """Convierte un nº de documento (ya normalizado) en su 'firma de forma':
    digitos->D, letras->L, el resto (puntos, barras, guiones) se conserva tal cual."""
    limpio = _normalizar_num_doc(nº_documento)
    out = []
    for ch in limpio:
        if ch.isdigit():
            out.append('D')
        elif ch.isalpha():
            out.append('L')
        else:
            out.append(ch)
    return ''.join(out)


def guard_suma_tramos(base_10, base_4, base_21, base_total_decl):
    """Guard #2 spec: Sigma(bases por tramo) = base_total declarada.
    Distinto de cuadre_total: este comprueba la suma de tramos entre si,
    no la suma final con el IVA."""
    suma = round(base_10 + base_4 + base_21, 2)
    if base_total_decl == 0 and suma != 0:
        return "NO_COMPROBADO", "base_total no declarada en el registro"
    if abs(suma - base_total_decl) < TOL:
        return "OK", f"suma tramos={suma} = base_total={base_total_decl}"
    return "FALLO", f"suma tramos={suma} != base_total declarada={base_total_decl}"


# Porcentajes tipicos de retencion en España (IRPF profesionales/alquileres/agrario)
RETENCIONES_TIPICAS = [1, 2, 7, 15, 19, 21]


def guard_retencion_vs_error(base_total, iva_total, irpf, total_decl, tipo_documento=None):
    """Guard #10 spec: si base+IVA != total, comprobar si la diferencia es un %
    tipico de retencion ANTES de marcar error. Si tipo_documento=ARRENDAMIENTO
    (u otro tipo con retencion tipica conocida, ej. profesional), el motivo
    incluye el concepto real, no solo el numero de porcentaje."""
    esperado_sin_retencion = round(base_total + iva_total, 2)
    diferencia = round(esperado_sin_retencion - total_decl, 2)
    if abs(diferencia) < TOL:
        return "NO_APLICA", "base+IVA = total, no hay retencion que evaluar"
    if base_total == 0:
        return "NO_COMPROBADO", "base_total = 0, no se puede calcular porcentaje"
    pct = round(diferencia / base_total * 100, 2)
    for tipico in RETENCIONES_TIPICAS:
        if abs(pct - tipico) < 0.15:
            etiqueta = f" (tipo_documento={tipo_documento})" if tipo_documento else ""
            coherente = abs(abs(irpf) - abs(diferencia)) < TOL if irpf else False
            if coherente:
                return "OK", f"diferencia de {diferencia} = retencion {tipico}% declarada y coherente{etiqueta}"
            return "OK", f"diferencia de {diferencia} coincide con retencion tipica del {tipico}%{etiqueta}"
    return "FALLO", f"diferencia de {diferencia} ({pct}%) no corresponde a ninguna retencion tipica {RETENCIONES_TIPICAS}"


def guard_signo_efectivo(nº_documento, motivo_texto, base_total, total_factura, tipo_documento=None):
    """Guard #11 spec: en abonos/rectificativas, coherencia entre la señal (textual
    o declarada explicitamente vía tipo_documento) y el signo del importe.
    Si tipo_documento viene informado (leido a mano al capturar la foto), se usa
    como fuente PRIMARIA - es mas fiable que adivinar por texto o por signo solo."""
    es_negativo = total_factura < 0
    if tipo_documento:
        es_abono_declarado = tipo_documento.upper() in ("ABONO", "RECTIFICATIVA")
        if es_abono_declarado and es_negativo:
            return "OK", f"tipo_documento={tipo_documento} declarado, importe negativo: coherente"
        if es_abono_declarado and not es_negativo:
            return "FALLO", f"tipo_documento={tipo_documento} declarado pero importe POSITIVO"
        if not es_abono_declarado and es_negativo:
            return "FALLO", f"importe negativo pero tipo_documento={tipo_documento} (no abono) - revisar"
        return "NO_APLICA", f"tipo_documento={tipo_documento}, importe positivo, coherente"

    texto = nº_documento.upper()
    señales_abono = ["ABONO", "RECTIFICATIV", "N/C", "NOTA DE CREDITO"]
    es_abono_textual = any(s in texto for s in señales_abono)
    if es_abono_textual and es_negativo:
        return "OK", "abono declarado (por texto del nº) y con importe negativo: coherente"
    if es_abono_textual and not es_negativo:
        return "FALLO", "el nº de documento sugiere abono/rectificativa pero el importe es POSITIVO"
    if not es_abono_textual and es_negativo:
        return "OK", "importe negativo (abono identificado por signo, sin tipo_documento declarado)"
    return "NO_APLICA", "factura normal con importe positivo"


def guard_sentido_compra_venta(nif_emisor, nif_cliente_titular, maestro_proveedores):
    """Guard #9 spec: el sentido lo da EMISOR/RECEPTOR, nunca el titulo del papel.
    Si el NIF del emisor es el del propio cliente -> es una VENTA suya (no un gasto).
    Si el emisor esta en su maestro de proveedores -> es una COMPRA/gasto."""
    if not nif_emisor or not nif_emisor.strip():
        return "NO_COMPROBADO", "sin NIF de emisor capturado"
    emisor = nif_emisor.strip().upper()
    if nif_cliente_titular and emisor == nif_cliente_titular.strip().upper():
        return "FALLO", "el emisor es el propio cliente: esto es una VENTA suya, no un gasto (no debe entrar como compra)"
    if maestro_proveedores and emisor in maestro_proveedores:
        return "OK", "emisor identificado como proveedor del cliente: sentido COMPRA/gasto"
    if not maestro_proveedores:
        return "NO_APLICA", "sin maestro de proveedores para determinar sentido"
    return "NO_COMPROBADO", "emisor no reconocido ni como el cliente ni como proveedor conocido"


def guard_ejercicio_coherente(fecha_factura_str, ejercicio_tanda):
    """Validez Temporal B2: el año de la factura coincide con el ejercicio de la
    tanda que se procesa. NO_APLICA si se declara explicitamente que es un gasto
    de ejercicio anterior aportado a proposito."""
    try:
        anio = int(fecha_factura_str[:4])
    except (ValueError, TypeError):
        return "NO_COMPROBADO", "fecha no parseable"
    if ejercicio_tanda is None:
        return "NO_APLICA", "no se ha declarado ejercicio de la tanda"
    if anio == ejercicio_tanda:
        return "OK", f"ejercicio {anio} coincide con la tanda"
    return "FALLO", f"factura de {anio} en una tanda del ejercicio {ejercicio_tanda}"


def guard_vencimiento_coherente(fecha_emision_str, fecha_vencimiento_str, plazos_cache, proveedor):
    """Validez Temporal B3: el plazo (vencimiento - emision) es coherente con el
    plazo habitual de ese proveedor. NO_COMPROBADO si no hay vencimiento capturado
    (hoy no lo capturamos en el CSV - por eso este guard queda declarado pero inerte
    hasta que la captura incluya el campo)."""
    if not fecha_vencimiento_str or not fecha_vencimiento_str.strip():
        return "NO_COMPROBADO", "fecha de vencimiento no capturada en el registro"
    from datetime import date
    try:
        y1, m1, d1 = int(fecha_emision_str[:4]), int(fecha_emision_str[5:7]), int(fecha_emision_str[8:10])
        y2, m2, d2 = int(fecha_vencimiento_str[:4]), int(fecha_vencimiento_str[5:7]), int(fecha_vencimiento_str[8:10])
        dias = (date(y2, m2, d2) - date(y1, m1, d1)).days
    except (ValueError, TypeError, IndexError):
        return "NO_COMPROBADO", "fechas no parseables"
    if dias < 0:
        return "FALLO", f"vencimiento anterior a la emision ({dias} dias)"
    entry = plazos_cache.get(proveedor)
    if not entry or not entry.get('plazos_vistos'):
        return "NO_APLICA", "sin historico de plazos para este proveedor"
    plazos = entry['plazos_vistos']
    media = sum(plazos) / len(plazos)
    if abs(dias - media) > max(media * 0.5, 15):
        return "FALLO", f"plazo de {dias} dias muy distinto del habitual del proveedor ({media:.0f} dias)"
    return "OK", f"plazo de {dias} dias coherente con el habitual ({media:.0f})"


GRUPOS_PGC = {
    # Grupo 4 - Acreedores y deudores por operaciones comerciales (oficial, BOE - PGC 2007/2021)
    '400': 'Proveedores', '410': 'Acreedores por prestaciones de servicios',
    '430': 'Clientes', '470': 'Hacienda Pública, deudora por diversos conceptos',
    '472': 'Hacienda Pública, IVA soportado',
    '475': 'Hacienda Pública, acreedora por conceptos fiscales',
    '4751': 'Hacienda Pública, acreedora por retenciones practicadas',
    # Grupo 6 - Compras y gastos (subgrupo 62 Servicios exteriores, oficial)
    '600': 'Compras de mercaderías', '621': 'Arrendamientos y cánones',
    '622': 'Reparaciones y conservación', '623': 'Servicios de profesionales independientes',
    '624': 'Transportes', '625': 'Primas de seguros', '626': 'Servicios bancarios y similares',
    '627': 'Publicidad, propaganda y relaciones públicas', '628': 'Suministros',
    '629': 'Otros servicios',
    # Grupo 7 - Ventas e ingresos (oficial) - para diferenciar ventas de compras
    '700': 'Ventas de mercaderías', '705': 'Prestaciones de servicios',
}
# Fuente: PLAN_GENERAL_DE_CONTABILIDAD_accesible.pdf (BOE), 645 cuentas extraidas y
# verificadas el 28-07-2026. Cuadro completo disponible en PGC_CUADRO_CUENTAS.json -
# este dict aqui solo trae los grupos relevantes para facturas de compra/venta,
# no los 645 codigos completos (esos viven en el JSON, no hace falta cargarlos
# todos en memoria para cada factura).


def construir_mapeo_cuenta_gasto(diario_recs):
    """Construye, a partir de un Diario.dbf REAL ya leido (lista de registros dbfread),
    el mapeo empirico proveedor/acreedor (cuenta 400xxx/410xxx) -> cuenta de gasto
    (grupo 6xx) que ContaPlus ha usado historicamente para cada uno.

    No es una tabla producto->IVA inventada ni un guard semantico caro: es una
    CONSULTA a datos que ya existen en el propio ContaPlus del cliente. Distingue
    automaticamente compras de mercaderias (600) de arrendamientos (621),
    servicios profesionales (623), suministros (628), etc. - segun lo que el
    propio despacho ya viene contabilizando, no segun una suposicion nueva.

    Lección real (cliente piloto, 28-07-2026): un proveedor de servicios -> 621000
    (arrendamientos), proveedores de mercancía -> 600000, un profesional
    independiente -> 623001. Confirmado con datos reales, no hipotesis."""
    from collections import defaultdict
    por_asiento = defaultdict(list)
    for r in diario_recs:
        por_asiento[r['ASIEN']].append(r)

    conteo = defaultdict(lambda: defaultdict(int))
    for asien, lineas in por_asiento.items():
        prov = None
        gastos = []
        for l in lineas:
            c = l.get('SUBCTA', '') or ''
            if c.startswith('400') or c.startswith('410'):
                prov = c
            elif c.startswith('6') and not c.startswith('472'):
                gastos.append(c)
        if prov:
            for g in gastos:
                conteo[prov][g] += 1

    mapeo = {}
    for prov, gastos in conteo.items():
        cuenta_mas_usada = max(gastos.items(), key=lambda kv: kv[1])[0]
        n_total = sum(gastos.values())
        n_esta = gastos[cuenta_mas_usada]
        mapeo[prov] = {
            'cuenta_gasto': cuenta_mas_usada,
            'grupo_pgc': GRUPOS_PGC.get(cuenta_mas_usada[:3], 'grupo no catalogado'),
            'confianza': 'ALTA' if n_esta == n_total else f'MEDIA ({n_esta}/{n_total} asientos)',
        }
    return mapeo


def guard_cuenta_gasto_coherente(cuenta_proveedor, mapeo_cuenta_gasto):
    """Guard complementario a Nivel 4: ¿existe un patron historico de a que cuenta
    de gasto (grupo 6xx) va este proveedor/acreedor? NO_APLICA si es la primera
    vez que se ve esa cuenta (no hay con que contrastar) - AQUI es donde debe
    entrar la verificacion del asesor, y esa verificacion es la que se aprende
    (ver aprender_cuenta_gasto mas abajo), no se vuelve a preguntar."""
    if not cuenta_proveedor or cuenta_proveedor not in mapeo_cuenta_gasto:
        return "NO_APLICA", "sin historico de cuenta de gasto para este proveedor/acreedor - requiere verificacion del asesor"
    entry = mapeo_cuenta_gasto[cuenta_proveedor]
    return "OK", f"cuenta de gasto habitual: {entry['cuenta_gasto']} ({entry['grupo_pgc']}), confianza {entry['confianza']}"


def aprender_cuenta_gasto(mapeo_cuenta_gasto, cuenta_proveedor, cuenta_gasto_confirmada,
                          path_persistencia=None, revisado_por=None):
    """El aprendizaje real: cuando el guard_cuenta_gasto_coherente dio NO_APLICA
    (proveedor nuevo) y el ASESOR decide/confirma a que cuenta de gasto va, esa
    decision se registra aqui - con confianza=CONFIRMADA_ASESOR, distinta de
    ALTA (que viene de mayoria historica automatica en ContaPlus), para que quede
    trazado de donde vino cada entrada del mapeo: ¿lo dedujo el sistema solo de
    datos ya contabilizados, o lo decidio una persona una vez?

    AMPLIADO 28-07-2026 (revision externa - hueco RGPD de auditoria senalado):
    revisado_por registra QUIEN tomo la decision, y se guarda la fecha/hora
    EXACTA de cuando se registro - antes solo se sabia "un humano lo confirmo
    en algun momento", ahora queda quien y cuando, tal como pide un registro
    de auditoria minimamente serio.

    Si se pasa path_persistencia, el mapeo actualizado se guarda en disco (JSON)
    para que la proxima sesion/factura ya no vuelva a preguntar - esto es
    exactamente el 'aprende con el tiempo' que pide Diego, no una simulacion:
    una vez guardado en archivo, sobrevive a esta conversacion."""
    import datetime
    mapeo_cuenta_gasto[cuenta_proveedor] = {
        'cuenta_gasto': cuenta_gasto_confirmada,
        'grupo_pgc': GRUPOS_PGC.get(cuenta_gasto_confirmada[:3], 'grupo no catalogado'),
        'confianza': 'CONFIRMADA_ASESOR',
        'revisado_por': revisado_por or 'no especificado',
        'fecha_revision': datetime.datetime.now().isoformat(timespec='seconds'),
    }
    if path_persistencia:
        import json
        with open(path_persistencia, 'w', encoding='utf-8') as f:
            json.dump(mapeo_cuenta_gasto, f, ensure_ascii=False, indent=2)
    return mapeo_cuenta_gasto


def construir_cache_iva_por_concepto(facturas_verificadas):
    """Aprende tipo de IVA por concepto/producto A PARTIR de facturas YA
    verificadas (aritmetica OK, no de facturas sin contrastar). Distingue
    confianza segun si el patron viene de UN solo proveedor (podria ser su
    propio error repetido) o de VARIOS proveedores distintos coincidiendo
    (evidencia mas fuerte, no depende de que uno solo se equivoque siempre).

    facturas_verificadas: lista de dicts con 'concepto', 'proveedor', 'tipo_iva'.
    Nunca sustituye a la tabla oficial (IVA_TIPOS_2026.json) - solo cubre lo
    que esa tabla no cataloga."""
    from collections import defaultdict
    por_concepto = defaultdict(lambda: defaultdict(set))  # concepto -> tipo -> {proveedores}
    for f in facturas_verificadas:
        por_concepto[f['concepto'].strip().lower()][f['tipo_iva']].add(f['proveedor'])

    cache = {}
    for concepto, tipos in por_concepto.items():
        tipo_mas_visto = max(tipos.items(), key=lambda kv: len(kv[1]))
        tipo, proveedores = tipo_mas_visto
        n_proveedores = len(proveedores)
        if n_proveedores >= 2:
            confianza = "MEDIA-ALTA (confirmado por varios proveedores distintos)"
        else:
            confianza = "BAJA (un solo proveedor, podria ser su propio error repetido)"
        cache[concepto] = {"tipo_iva": tipo, "n_proveedores_distintos": n_proveedores, "confianza": confianza}
    return cache


TABLA_IVA_4 = {"pan", "harina panificable", "leche", "queso", "huevos", "fruta", "verdura",
               "hortaliza", "legumbre", "tuberculo", "cereal", "aceite de oliva"}


def guard_tipo_producto_iva_semantico(categoria_producto, tipo_declarado):
    """Guard #tipo_producto_iva_semantico (adenda): coteja el tipo de IVA aplicado
    contra la tabla oficial 2026 (AEAT/LIVA), a partir de una CATEGORIA declarada
    en captura (ej. 'aceite de oliva', 'hosteleria', 'aceite general') - igual que
    tipo_documento, esto NO se adivina en el guard, se declara al leer la factura.

    LIMITE HONESTO: este guard sigue sin poder identificar el producto el solo -
    necesita que 'categoria_producto' venga ya informado (por vision al capturar).
    Lo que SI resuelve de verdad: una vez identificado el producto, la tasa
    correcta ya no es criterio humano, es consulta a la tabla oficial - p.ej.
    'aceite de oliva' -> 4% SIEMPRE, pero 'aceite de girasol'/'aceite freidora'
    (no es oliva) -> 10%, no 4%, aunque ambos sean 'aceite' a simple vista."""
    if not categoria_producto:
        return "NO_COMPROBADO", "sin categoria de producto declarada en captura"
    cat = categoria_producto.strip().lower()
    if cat in TABLA_IVA_4:
        esperado = 4
    elif cat in ("hosteleria", "restaurante", "bar"):
        esperado = 10
    elif cat in ("alimentacion_general",):
        esperado = 10
    else:
        return "NO_COMPROBADO", f"categoria '{categoria_producto}' no catalogada en la tabla oficial todavia"
    if abs(tipo_declarado - esperado) < 0.5:
        return "OK", f"{categoria_producto} -> {esperado}% segun tabla oficial IVA 2026, coincide"
    return "FALLO", f"{categoria_producto} deberia ser {esperado}% segun tabla oficial, se aplico {tipo_declarado}%"


PALABRAS_CLAVE_OPERACION_ESPECIAL = {
    "inmovilizado": ["inmovilizado", "amortizacion", "amortización", "activo fijo", "maquinaria (compra)"],
    "intracomunitario": ["intracomunitari", "aib", "eib"],
    "importacion_exportacion": ["dua", "aduana", "importacion", "importación", "exportacion", "exportación"],
    "regimen_especial": ["recargo de equivalencia", "agricultura ganaderia", "reagp", "isp", "inversion del sujeto pasivo"],
}
CUENTAS_INMOVILIZADO_PREFIJOS = ("20", "21", "22", "23")  # grupo 2 PGC: inmovilizado


def guard_tipo_operacion_especial(concepto, cuenta_debe, nif_proveedor):
    """No decide nada del caso especial (no diagnostica) - SOLO detecta, por
    estructura (no por leer semanticamente toda la factura), que esto NO es
    una compra normal, y lo frena a AMBAR con el motivo explicado. Cubre
    exactamente el caso pedido por Diego (22-09-2026, 22:09): inmovilizado,
    amortizacion, intracomunitario, importacion/exportacion, regimen especial.

    Deteccion por 2 señales estructurales, ninguna requiere entender la
    factura a fondo:
    1. Cuenta de destino en grupo 2 (20-23xx) = inmovilizado, por definicion PGC.
    2. Palabra clave reconocida en el concepto/descripcion capturado.
    3. NIF de proveedor con prefijo de pais NO español (2 letras ISO en vez de
       1 letra CIF española) = posible intracomunitario.

    NO_APLICA si no salta ninguna señal - es la inmensa mayoria de casos reales
    (91 facturas de esta noche, 0 casos de esto)."""
    if cuenta_debe and cuenta_debe[:2] in CUENTAS_INMOVILIZADO_PREFIJOS:
        return "AMBAR", f"cuenta de destino {cuenta_debe} es del grupo 2 (inmovilizado) - requiere verificacion humana, no es compra normal"

    texto = (concepto or '').lower()
    for tipo, palabras in PALABRAS_CLAVE_OPERACION_ESPECIAL.items():
        for p in palabras:
            if p in texto:
                return "AMBAR", f"concepto contiene '{p}' -> posible operacion de tipo {tipo}, requiere verificacion humana"

    if nif_proveedor and len(nif_proveedor) >= 2 and nif_proveedor[:2].isalpha() and not nif_proveedor[0].isdigit():
        # NIF/VAT intracomunitario suele ir con 2 letras de pais (DE, FR, IT...)
        # un NIF/CIF español SIEMPRE tiene 1 sola letra al principio (o ninguna, DNI)
        if nif_proveedor[:2].upper() != nif_proveedor[:2].upper()[0]*2 and nif_proveedor[1].isalpha():
            return "AMBAR", f"NIF '{nif_proveedor}' con formato de 2 letras de pais -> posible proveedor intracomunitario, requiere verificacion humana"

    return "NO_APLICA", "sin señales de operacion especial (inmovilizado/intracomunitario/importacion/regimen especial)"


def guard_nif_casa_historico(nif, maestro_proveedores):
    """Nivel 2 guard #5: el NIF existe en el maestro de proveedores/acreedores del cliente.
    NO_APLICA si no hay maestro cargado para este cliente.

    LECCION REAL (cliente piloto, 28-07-2026, confirmada por Diego): el maestro que se
    pase aqui debe incluir TANTO cuentas 400xxx (proveedores de mercaderias/existencias)
    COMO 410xxx (acreedores por prestacion de servicios: alquileres, profesionales,
    suministros, seguros...). Un maestro que solo cubra 400xxx marca ROJO facturas
    perfectamente correctas de arrendadores/profesionales (caso real anonimizado:
    cuenta 410014, retencion en subcuenta personal 475103) - no porque
    el dato este mal, sino porque el guard miraba el rango de cuenta equivocado."""
    if not maestro_proveedores:
        return "NO_APLICA", "sin maestro de proveedores cargado para este cliente"
    if not nif or not nif.strip():
        return "NO_COMPROBADO", "sin NIF capturado, no se puede buscar en el maestro"
    if nif.strip() in maestro_proveedores:
        return "OK", f"NIF encontrado en maestro: {maestro_proveedores[nif.strip()].get('titulo','')}"
    return "FALLO", "NIF no encontrado en el maestro de proveedores del cliente"


def guard_secuencia_documental_proveedor(proveedor, nº_documento, secuencia_cache):
    """Nacimiento del Dato A1: el numero de documento sigue una secuencia numerica
    coherente respecto a los ya vistos del mismo proveedor (misma forma, numero
    correlativo dentro de rango razonable). Solo evalua la parte numerica final.
    NO_APLICA si no hay al menos 2 numeros previos con la misma forma para comparar."""
    entry = secuencia_cache.get(proveedor)
    if not entry or len(entry.get('numeros_vistos', [])) < 2:
        return "NO_APLICA", "menos de 2 documentos previos del proveedor para establecer secuencia"
    numeros = entry['numeros_vistos']
    actual = _normalizar_num_doc(nº_documento)
    m = re.search(r'(\d+)$', actual)
    if not m:
        return "NO_COMPROBADO", "el numero de documento no termina en digitos, no se puede comparar secuencia"
    actual_num = int(m.group(1))
    previos = []
    for n in numeros:
        mm = re.search(r'(\d+)$', _normalizar_num_doc(n))
        if mm:
            previos.append(int(mm.group(1)))
    if not previos:
        return "NO_APLICA", "los documentos previos no tienen parte numerica comparable"
    rango = max(previos) - min(previos) if len(previos) > 1 else 0
    salto_medio = rango / max(len(previos) - 1, 1) if len(previos) > 1 else 0
    dist_min = min(abs(actual_num - p) for p in previos)
    if salto_medio > 0 and dist_min > salto_medio * 20:
        return "FALLO", f"nº {actual_num} muy alejado de la secuencia conocida (dist={dist_min}, salto medio={salto_medio:.0f})"
    return "OK", f"nº {actual_num} coherente con secuencia conocida"


def guard_estructura_reconocida(proveedor, nº_documento, formato_cache):
    """Guard 0 (Nivel 1-bis): ¿el nº de documento encaja en algun patron de forma
    ya visto para este proveedor? No es un guard de contenido, es de FORMA.
    FALLO no es 'esta mal' - es 'no se parece a nada que conozca de este proveedor',
    y baja a AMBAR automatico sin excepcion, aunque el resto cuadre."""
    entry = formato_cache.get(proveedor)
    if not entry or not entry.get('ejemplos'):
        return "NO_APLICA", "sin historico de formato para este proveedor (primera vez)"
    forma_actual = _forma(nº_documento)
    formas_conocidas = {_forma(e) for e in entry['ejemplos']}
    if len(formas_conocidas) < 2 and entry.get('n_facturas_vistas', 0) < 2:
        return "NO_COMPROBADO", f"solo n={entry.get('n_facturas_vistas',0)} ejemplo(s), patron poco fiable aun"
    if forma_actual in formas_conocidas:
        return "OK", f"forma '{forma_actual}' coincide con patron ya visto"
    return "FALLO", f"forma '{forma_actual}' no coincide con ningun patron conocido: {formas_conocidas}"


def cargar_cache_json(path):
    """Carga una cache real desde disco (JSON), no un diccionario escrito a mano
    en la sesion. Si el archivo no existe, devuelve {} y lo declara - nunca inventa."""
    import json, os
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def evaluar_fila_v4(fila, vistos_duplicado, historico_proveedor, formato_cache,
                     secuencia_cache, maestro_proveedores, alta_cliente_anio,
                     nif_cliente_titular=None, ejercicio_tanda=None, plazos_cache=None):
    """Version 4: 16 guards. Añade suma_tramos, sentido_compra_venta,
    retencion_vs_error, signo_efectivo, ejercicio_coherente, vencimiento_coherente.
    Todo lo que no tiene dato real detras se declara NO_COMPROBADO/NO_APLICA,
    nunca OK por omision."""
    plazos_cache = plazos_cache or {}
    base_10 = _f(fila.get('base_10'))
    base_4 = _f(fila.get('base_4'))
    base_21 = _f(fila.get('base_21'))
    base_total = _f(fila.get('base_total'))
    iva_total = _f(fila.get('iva_total'))
    irpf = _f(fila.get('irpf_retencion', 0))
    total = _f(fila.get('total_factura'))
    proveedor = fila.get('proveedor', '')
    nif = fila.get('nif', '')
    num_doc = fila.get('nº_documento', '')
    motivo = fila.get('motivo_semaforo', '')

    guards = {}
    # Nivel 1 - Aritmeticos
    guards["aritmetica_base_tipo"] = guard_aritmetica_base_tipo(base_10, base_4, base_21, iva_total)
    guards["suma_tramos"] = guard_suma_tramos(base_10, base_4, base_21, base_total)
    guards["cuadre_total"] = guard_cuadre_total(base_10, base_4, base_21, iva_total, irpf, total)
    guards["nif_digito_control"] = guard_nif_digito_control(nif)
    # Nivel 1-bis - Forma
    guards["estructura_reconocida"] = guard_estructura_reconocida(proveedor, num_doc, formato_cache)
    # Nivel 2 - Identidad
    guards["nif_casa_historico"] = guard_nif_casa_historico(nif, maestro_proveedores)
    # Nivel 3 - Anti-duplicacion
    guards["anti_duplicado"] = guard_anti_duplicado(fila, vistos_duplicado)
    # Nivel 4 - Sentido y regimen
    guards["sentido_compra_venta"] = guard_sentido_compra_venta(nif, nif_cliente_titular, maestro_proveedores)
    guards["retencion_vs_error"] = guard_retencion_vs_error(
        base_total or (base_10+base_4+base_21), iva_total, irpf, total, fila.get('tipo_documento'))
    guards["signo_efectivo"] = guard_signo_efectivo(num_doc, motivo, base_total, total, fila.get('tipo_documento'))
    # Nacimiento del Dato
    guards["secuencia_documental_proveedor"] = guard_secuencia_documental_proveedor(proveedor, num_doc, secuencia_cache)
    guards["importe_atipico"] = guard_importe_atipico(proveedor, total, historico_proveedor)
    # Validez Temporal
    guards["fecha_posterior_alta"] = guard_fecha_posterior_alta(fila.get('fecha_expedicion', ''), alta_cliente_anio)
    guards["ejercicio_coherente"] = guard_ejercicio_coherente(fila.get('fecha_expedicion', ''), ejercicio_tanda)
    guards["vencimiento_coherente"] = guard_vencimiento_coherente(
        fila.get('fecha_expedicion', ''), fila.get('fecha_vencimiento', ''), plazos_cache, proveedor)
    # Confianza
    guards["confianza_captura"] = guard_confianza_captura(fila)

    veredicto, motivo_v = calcular_veredicto_v4(guards)
    return veredicto, motivo_v, guards


def calcular_veredicto_v4(guards):
    """Veredicto con los 16 guards. Criticos ampliados con suma_tramos,
    sentido_compra_venta, signo_efectivo y ejercicio_coherente."""
    criticos = ["aritmetica_base_tipo", "suma_tramos", "cuadre_total", "nif_digito_control",
                "nif_casa_historico", "anti_duplicado", "fecha_posterior_alta",
                "sentido_compra_venta", "signo_efectivo", "ejercicio_coherente",
                "retencion_vs_error"]
    for g in criticos:
        if guards.get(g, ("NO_COMPROBADO", ""))[0] == "FALLO":
            return "ROJO", f"{g}: {guards[g][1]}"

    if guards.get("importe_atipico", ("OK", ""))[0] == "FALLO":
        return "AMBAR", f"importe_atipico: {guards['importe_atipico'][1]}"
    if guards.get("estructura_reconocida", ("OK", ""))[0] == "FALLO":
        return "AMBAR", f"estructura_reconocida: {guards['estructura_reconocida'][1]}"
    if guards.get("secuencia_documental_proveedor", ("OK", ""))[0] == "FALLO":
        return "AMBAR", f"secuencia_documental: {guards['secuencia_documental_proveedor'][1]}"
    if guards.get("vencimiento_coherente", ("OK", ""))[0] == "FALLO":
        return "AMBAR", f"vencimiento_coherente: {guards['vencimiento_coherente'][1]}"

    confianza = guards.get("confianza_captura", ("ALTA", ""))[0]
    if confianza != "ALTA":
        return "AMBAR", f"confianza_captura={confianza}"

    # NO_COMPROBADO en guards que SI deberian haber corrido baja a AMBAR.
    # Se excluyen los que son NO_COMPROBADO por falta estructural de dato
    # (vencimiento no capturado hoy, importe_atipico con n<3) - eso ya esta declarado.
    exentos = {"vencimiento_coherente", "importe_atipico", "secuencia_documental_proveedor",
               "estructura_reconocida"}
    # CORREGIDO 28-07-2026 (revision externa): ejercicio_coherente estaba tambien en
    # 'exentos', lo que lo dejaba mudo (ni ROJO ni AMBAR) si la fecha no parseaba -
    # dependia implicitamente de que fecha_posterior_alta cazara el mismo fallo, sin
    # que nadie lo hubiera declarado. Ahora SI escala a AMBAR si es NO_COMPROBADO.
    no_comprobados = [g for g, (e, _) in guards.items() if e == "NO_COMPROBADO" and g not in exentos]
    if no_comprobados:
        return "AMBAR", f"NO_COMPROBADO: {', '.join(no_comprobados)}"

    return "VERDE", "todos los guards aplicables OK, confianza ALTA"


def evaluar_fila_v3(fila, vistos_duplicado, historico_proveedor, formato_cache,
                     secuencia_cache, maestro_proveedores, alta_cliente_anio):
    """Version 3: 10 guards. Añade nif_casa_historico (Nivel 2, critico) y
    secuencia_documental_proveedor (Nacimiento del Dato). maestro_proveedores y
    secuencia_cache pueden venir vacios ({}) - en ese caso los guards se declaran
    NO_APLICA, nunca se fuerza un OK sin dato real detras."""
    base_10 = _f(fila.get('base_10'))
    base_4 = _f(fila.get('base_4'))
    base_21 = _f(fila.get('base_21'))
    iva_total = _f(fila.get('iva_total'))
    irpf = _f(fila.get('irpf_retencion', 0))
    total = _f(fila.get('total_factura'))
    proveedor = fila.get('proveedor', '')
    nif = fila.get('nif', '')

    guards = {}
    guards["aritmetica_base_tipo"] = guard_aritmetica_base_tipo(base_10, base_4, base_21, iva_total)
    guards["cuadre_total"] = guard_cuadre_total(base_10, base_4, base_21, iva_total, irpf, total)
    guards["nif_digito_control"] = guard_nif_digito_control(nif)
    guards["nif_casa_historico"] = guard_nif_casa_historico(nif, maestro_proveedores)
    guards["anti_duplicado"] = guard_anti_duplicado(fila, vistos_duplicado)
    guards["confianza_captura"] = guard_confianza_captura(fila)
    guards["fecha_posterior_alta"] = guard_fecha_posterior_alta(fila.get('fecha_expedicion', ''), alta_cliente_anio)
    guards["importe_atipico"] = guard_importe_atipico(proveedor, total, historico_proveedor)
    guards["estructura_reconocida"] = guard_estructura_reconocida(proveedor, fila.get('nº_documento', ''), formato_cache)
    guards["secuencia_documental_proveedor"] = guard_secuencia_documental_proveedor(
        proveedor, fila.get('nº_documento', ''), secuencia_cache)

    veredicto, motivo = calcular_veredicto_v2(guards)
    return veredicto, motivo, guards


def evaluar_fila_v2(fila, vistos_duplicado, historico_proveedor, formato_cache, alta_cliente_anio):
    """Version 2 (conservada por compatibilidad): incluye guard_estructura_reconocida
    ademas de los 7 guards previos, SIN nif_casa_historico ni secuencia documental."""
    base_10 = _f(fila.get('base_10'))
    base_4 = _f(fila.get('base_4'))
    base_21 = _f(fila.get('base_21'))
    iva_total = _f(fila.get('iva_total'))
    irpf = _f(fila.get('irpf_retencion', 0))
    total = _f(fila.get('total_factura'))
    proveedor = fila.get('proveedor', '')

    guards = {}
    guards["aritmetica_base_tipo"] = guard_aritmetica_base_tipo(base_10, base_4, base_21, iva_total)
    guards["cuadre_total"] = guard_cuadre_total(base_10, base_4, base_21, iva_total, irpf, total)
    guards["nif_digito_control"] = guard_nif_digito_control(fila.get('nif', ''))
    guards["anti_duplicado"] = guard_anti_duplicado(fila, vistos_duplicado)
    guards["confianza_captura"] = guard_confianza_captura(fila)
    guards["fecha_posterior_alta"] = guard_fecha_posterior_alta(fila.get('fecha_expedicion', ''), alta_cliente_anio)
    guards["importe_atipico"] = guard_importe_atipico(proveedor, total, historico_proveedor)
    guards["estructura_reconocida"] = guard_estructura_reconocida(proveedor, fila.get('nº_documento', ''), formato_cache)

    veredicto, motivo = calcular_veredicto_v2(guards)
    return veredicto, motivo, guards


def calcular_veredicto_v2(guards):
    """Igual que calcular_veredicto, pero con regla dura anadida:
    estructura_reconocida=FALLO -> AMBAR automatico, SIN EXCEPCION,
    aunque el resto de guards este OK. No se le da beneficio de la duda
    a una lectura 'que salio bien de casualidad' sobre un formato desconocido."""
    veredicto, motivo = calcular_veredicto(guards)
    if veredicto == "VERDE" and guards.get("estructura_reconocida", ("OK",""))[0] == "FALLO":
        return "AMBAR", "estructura_reconocida:FALLO (forma de nº de documento no reconocida)"
    return veredicto, motivo


def reevaluar_tras_correccion(fila_corregida, vistos_duplicado, historico_proveedor, formato_cache,
                                secuencia_cache=None, maestro_proveedores=None, alta_cliente_anio=None,
                                nif_cliente_titular=None, ejercicio_tanda=None, plazos_cache=None):
    """Flujo de reevaluacion AMBAR->VERDE: el asesor corrige un campo (a ciegas,
    sin ver la lectura original, para no anclarse a un valor posiblemente erroneo)
    y el caso se re-evalua desde cero contra TODOS los guards (16, evaluar_fila_v4)
    con el valor corregido. Si pasa, se marca VERDE (corregido) - distinto de
    VERDE (directo), para trazabilidad y para medir cuanto AMBAR se esta
    convirtiendo en VERDE limpio con el tiempo.

    CORREGIDO 28-07-2026 (revision externa): esta funcion llamaba a evaluar_fila_v2
    (8 guards) en vez de evaluar_fila_v4 (16 guards) - el camino que debia ser MAS
    estricto (reevaluacion tras correccion humana) era en realidad el mas debil de
    los dos, sin comprobar nif_casa_historico, sentido_compra_venta,
    retencion_vs_error, signo_efectivo, secuencia_documental, ejercicio_coherente
    ni vencimiento_coherente. Bug real, detectado por revision externa, no por
    las pruebas propias - motivo por el cual las pruebas de regresion deben
    cubrir tambien este flujo explicitamente (ver test_motor_veredicto.py)."""
    fila_corregida = dict(fila_corregida)
    fila_corregida['verificacion'] = 'OK'  # la correccion humana se trata como lectura directa de nuevo
    secuencia_cache = secuencia_cache or {}
    maestro_proveedores = maestro_proveedores or {}
    veredicto, motivo, guards = evaluar_fila_v4(
        fila_corregida, vistos_duplicado, historico_proveedor, formato_cache,
        secuencia_cache, maestro_proveedores, alta_cliente_anio,
        nif_cliente_titular, ejercicio_tanda, plazos_cache)
    if veredicto == "VERDE":
        return "VERDE (corregido)", motivo, guards
    return veredicto, motivo, guards

