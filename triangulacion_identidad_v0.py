# TRIANGULACIÓN DE IDENTIDAD v0 — OS Asesoría 2026-07-21
# Verifica la identidad del emisor por 3 fuentes independientes + la BD del cliente.
# Nace del fallo silencioso de un caso real anonimizado (NIF mal leído casó con OTRO proveedor real).
import re, unicodedata, difflib

# ---------- 1. VALIDACIÓN ESTRUCTURAL DEL NIF (dígito de control) ----------
def _limpia(nif): return re.sub(r'[^A-Z0-9]', '', (nif or '').upper())

def valida_nif(nif):
    """Devuelve (valido:bool, tipo:str, motivo:str)."""
    n = _limpia(nif)
    if not n: return False, '', 'vacío'
    # NIF persona física: 8 dígitos + letra
    if re.fullmatch(r'\d{8}[A-Z]', n):
        letras = 'TRWAGMYFPDXBNJZSQVHLCKE'
        return (letras[int(n[:8]) % 23] == n[8]), 'NIF', 'dígito de control'
    # NIE: X/Y/Z + 7 dígitos + letra
    if re.fullmatch(r'[XYZ]\d{7}[A-Z]', n):
        letras = 'TRWAGMYFPDXBNJZSQVHLCKE'
        num = str('XYZ'.index(n[0])) + n[1:8]
        return (letras[int(num) % 23] == n[8]), 'NIE', 'dígito de control'
    # CIF: letra + 7 dígitos + control (dígito o letra)
    if re.fullmatch(r'[ABCDEFGHJKLMNPQRSUVW]\d{7}[0-9A-J]', n):
        digitos = n[1:8]
        pares = sum(int(digitos[i]) for i in (1,3,5))
        impares = 0
        for i in (0,2,4,6):
            d = int(digitos[i]) * 2
            impares += d // 10 + d % 10
        ctrl = (10 - (pares + impares) % 10) % 10
        c = n[8]
        if n[0] in 'PQRSNW':            # control obligatoriamente LETRA
            return ('JABCDEFGHI'[ctrl] == c), 'CIF', 'control letra'
        if n[0] in 'ABEH':              # control obligatoriamente DÍGITO
            return (str(ctrl) == c), 'CIF', 'control dígito'
        return (str(ctrl) == c or 'JABCDEFGHI'[ctrl] == c), 'CIF', 'control mixto'
    # NIF-IVA intracomunitario (otro país)
    if re.fullmatch(r'(DE|FR|IT|PT|NL|BE|PL|IE|AT|SE|DK|FI|EL|CZ|RO|HU|BG|HR|SK|SI|LT|LV|EE|LU|MT|CY)[0-9A-Z]{2,12}', n):
        return True, 'NIF-IVA UE', 'formato válido (verificar en VIES)'
    return False, '?', 'formato no reconocido'

# ---------- 2. NORMALIZACIÓN Y COMPARACIÓN DE NOMBRES ----------
_RUIDO = (' SL',' S L',' SLU',' SA',' SAL',' SAU',' CB',' SCP',' SLL',' SOCIEDAD LIMITADA',
          ' SOCIEDAD ANONIMA',' Y CIA',' E HIJOS',' HERMANOS')
def norm_nombre(s):
    if not s: return ''
    s = unicodedata.normalize('NFKD', s.upper()).encode('ascii','ignore').decode()
    s = re.sub(r'[^A-Z0-9 ]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    for r in _RUIDO:
        if s.endswith(r): s = s[:-len(r)].strip()
    return s

def similitud(a, b):
    """0..1 combinando ratio de secuencia y solape de tokens significativos."""
    A, B = norm_nombre(a), norm_nombre(b)
    if not A or not B: return 0.0
    ratio = difflib.SequenceMatcher(None, A, B).ratio()
    ta = {t for t in A.split() if len(t) > 2}
    tb = {t for t in B.split() if len(t) > 2}
    solape = len(ta & tb) / max(1, min(len(ta), len(tb)))
    return max(ratio, solape)

# ---------- 3. TRIANGULACIÓN ----------
# ARQUITECTURA (corregida 21-07 tras verificación empírica):
#   La cuenta contable NO es atributo del tercero: es atributo de la RELACIÓN (cliente ↔ tercero).
#   Clave obligatoria de la caché: (NIF_titular, NIF_tercero) -> (cuenta, tipo)
#   Dato real: de 340 NIFs compartidos entre clientes de la cartera, 173 (51%) tienen cuenta distinta
#   según el cliente; y algunos cambian de TIPO (proveedor 400 / acreedor 410 / cliente 430).
#   PROHIBIDO reutilizar la cuenta de un cliente en otro. `tabla_cliente` es SIEMPRE la del titular.
UMBRAL_OK, UMBRAL_DUDA = 0.72, 0.45

def triangula(nif_cabecera, nombre_cabecera, nombre_margen, nif_margen, tabla_cliente):
    """
    tabla_cliente: {nif_normalizado: {'cuenta':..., 'titulo':...}}
    Devuelve dict con veredicto: OK | ALERTA | ALTA | RECHAZO y el detalle.
    """
    out = {'nif': _limpia(nif_cabecera), 'fuentes': {}, 'veredicto': None, 'motivos': []}
    # Fuente 1: NIF de cabecera, estructuralmente válido
    ok_nif, tipo, motivo = valida_nif(nif_cabecera)
    out['fuentes']['nif_cabecera'] = {'valor': _limpia(nif_cabecera), 'valido': ok_nif, 'tipo': tipo}
    if not ok_nif:
        out['veredicto'] = 'RECHAZO'
        out['motivos'].append(f'NIF no supera el dígito de control ({motivo}) → captura defectuosa')
        return out
    # Fuente 2: NIF del margen (si se leyó) debe coincidir con el de cabecera
    if nif_margen:
        coincide_margen = _limpia(nif_margen) == _limpia(nif_cabecera)
        out['fuentes']['nif_margen'] = {'valor': _limpia(nif_margen), 'coincide': coincide_margen}
        if not coincide_margen:
            out['veredicto'] = 'ALERTA'
            out['motivos'].append('el NIF del margen NO coincide con el de cabecera')
            return out
    # Fuente 3: contraste con la BD del cliente
    hit = tabla_cliente.get(_limpia(nif_cabecera))
    if not hit:
        out['veredicto'] = 'ALTA'
        out['motivos'].append('NIF válido pero no está en el histórico del cliente → alta nueva a validar')
        return out
    out['cuenta'] = hit['cuenta']; out['titulo_bd'] = hit['titulo']
    # Fuente 4: el NOMBRE leído debe parecerse al título del histórico
    sim = max(similitud(nombre_cabecera, hit['titulo']),
              similitud(nombre_margen or '', hit['titulo']))
    out['fuentes']['nombre'] = {'leido': nombre_cabecera, 'bd': hit['titulo'], 'similitud': round(sim,2)}
    if sim >= UMBRAL_OK:
        out['veredicto'] = 'OK'
    elif sim >= UMBRAL_DUDA:
        out['veredicto'] = 'ALERTA'
        out['motivos'].append(f'nombre leído y título del histórico solo coinciden al {sim:.0%}')
    else:
        out['veredicto'] = 'ALERTA'
        out['motivos'].append(f'★ NIF casa pero el NOMBRE NO ({sim:.0%}): posible NIF mal leído que apunta a OTRO proveedor real')
    return out
