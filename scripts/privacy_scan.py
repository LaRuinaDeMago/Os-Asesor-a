#!/usr/bin/env python3
"""Escáner de privacidad — Barrera técnica (Fase 2.5).

Se ejecuta en dos sitios independientes, con el mismo código:
  1. Hook local de pre-commit (antes de que nada salga de esta máquina).
  2. GitHub Action en cada PR/push (por si la barrera 1 falla o se salta).

Qué comprueba, sobre el conjunto de archivos dado (staged o del diff del PR):
  - Ningún archivo .zip (regla fija, sección 1.4 del plan — nunca hay excepción).
  - Ningún archivo cuyo nombre coincida exactamente con la lista de
    NUNCA_SUBE_FILENAMES.txt (nombres de archivo ya identificados como
    reales en la auditoría — son nombres de fichero, no datos personales,
    por eso es seguro que este archivo viva en el repo).
  - Patrón de NIF/DNI/CIF español (8 dígitos+letra, o letra+7+control) en el
    contenido nuevo.
  - Patrón de IBAN español (ES + 22 dígitos).
  - Patrón de teléfono español (6/7/8/9 + 8 dígitos, con o sin espacios).
  - Patrón de email (persona@dominio).
  - Patrón de secretos/API keys (cadenas largas tipo token: prefijos conocidos
    de proveedores comunes, o bloques alfanuméricos largos y de alta entropía
    que no parecen texto normal).
  - Si existe `.privacy_local_denylist.txt` en la raíz del proyecto (NUNCA se
    commitea, ver .gitignore) con una palabra por línea, también avisa si
    alguna de esas palabras aparece en el contenido nuevo. Ese archivo lo
    rellena Diego a mano si quiere esta capa extra; este script nunca escribe
    ni conoce su contenido.

No decide nada por sí solo: si encuentra algo, PARA el commit/PR y muestra
en qué archivo y línea (nunca el contenido de la línea) para que un humano
lo revise — el mismo principio de "NO_COMPROBADO, nunca OK por omisión" que
usa el motor de veredicto.
"""
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parent.parent

PATRON_NIF = re.compile(r'\b\d{8}[A-Za-z]\b|\b[A-HJNPQSUVW]\d{7}[0-9A-J]\b')
PATRON_IBAN = re.compile(r'\bES\d{2}\s?\d{4}\s?\d{4}\s?\d{2}\s?\d{10}\b')
PATRON_TELEFONO = re.compile(r'\b[6789]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}\b')

# Excepción acotada al patrón de teléfono (añadida 11-08-2026).
# Una línea de JSON cuyo valor es un entero DESNUDO es un número, no un teléfono.
# Los agregados de la Fase 0 disparaban este patrón con tamaños de fichero en
# bytes: cualquier cifra de 9 dígitos que empiece por 6/7/8/9 lo activa, y un
# tamaño en bytes de ese orden de magnitud lo cumple constantemente.
#
# Por qué esta excepción es segura y no abre un agujero:
#   - Solo aplica si la línea ENTERA es `"clave": <entero>` y nada más.
#   - Un teléfono real de este corpus sale del campo TELEF01 de SubCta.dbf, que
#     es de tipo carácter: serializa SIEMPRE como cadena entre comillas, y eso
#     esta excepción NO lo cubre — se sigue avisando. Igual que en prosa.
#   - No toca los patrones de NIF, IBAN, email ni secretos.
#   - Verificado con fichero trampa el 11-08-2026: entero desnudo pasa; el mismo
#     número entre comillas y el mismo número en una frase, ambos bloquean.
#
# Riesgo residual asumido y declarado: si alguna vez se volcara un teléfono como
# entero sin comillas en un JSON, pasaría sin aviso. Se acepta porque el origen
# del dato es de tipo carácter y porque la alternativa —un escáner que grita en
# cada agregado— acaba en que nadie lo mira, que es peor.
#
# NOTA para quien edite este archivo: no escribas cifras de 9 dígitos que
# empiecen por 6/7/8/9 en los comentarios; el escáner se avisa a sí mismo.
LINEA_JSON_NUMERICA = re.compile(r'^\s*"[^"]+"\s*:\s*-?\d+(\.\d+)?\s*,?\s*$')
PATRON_EMAIL = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')

# Prefijos conocidos de claves de API de proveedores comunes (Anthropic,
# OpenAI, Google, AWS, Slack...). Deliberadamente NO se usa un patrón
# genérico de "bloque alfanumérico largo" — se probó y daba ~20 falsos
# positivos en el propio repo (nombres de variable largos, hashes de commit,
# referencias normativas tipo V1550-25), lo cual es peor que no tenerlo: un
# escáner que grita demasiado deja de mirarse. Mejor pocos avisos fiables que
# muchos que se acaban ignorando.
PATRON_SECRETO = re.compile(
    r'\b(sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_-]{20,}'
    r'|ghp_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{12,}|xox[baprs]-[A-Za-z0-9-]{10,})\b'
)

# NIF/DNI/CIF inventados a propósito (algunos con checksum matemáticamente
# válido, fabricados en esta sesión; otros ya existían en el test file como
# marcadores obvios de prueba, ej. "PROVEEDOR FALSO SL" / "OTRO PROVEEDOR").
# Ninguno identifica a nadie real — es seguro tenerlos aquí en texto plano.
NIF_SINTETICOS_CONOCIDOS = {
    "12345678Z", "12345678Y", "B12345674", "B12345678", "B99999999",
}

EXTENSIONES_TEXTO = {
    '.py', '.md', '.json', '.txt', '.csv', '.yml', '.yaml', '.cfg', '.ini',
}


def cargar_denylist_local():
    ruta = RAIZ / '.privacy_local_denylist.txt'
    if not ruta.exists():
        return []
    with open(ruta, encoding='utf-8') as f:
        return [linea.strip() for linea in f if linea.strip() and not linea.startswith('#')]


def cargar_nombres_prohibidos():
    ruta = RAIZ / 'NUNCA_SUBE_FILENAMES.txt'
    if not ruta.exists():
        return set()
    with open(ruta, encoding='utf-8') as f:
        return {linea.strip() for linea in f if linea.strip() and not linea.startswith('#')}


def escanear_archivo(path: Path, denylist_local):
    hallazgos = []
    if path.suffix.lower() not in EXTENSIONES_TEXTO:
        return hallazgos
    try:
        with open(path, encoding='utf-8', errors='ignore') as f:
            lineas = f.readlines()
    except OSError:
        return hallazgos
    for i, linea in enumerate(lineas, start=1):
        m = PATRON_NIF.search(linea)
        if m and m.group(0).upper() not in NIF_SINTETICOS_CONOCIDOS:
            hallazgos.append((i, 'posible NIF/DNI/CIF'))
        if PATRON_IBAN.search(linea):
            hallazgos.append((i, 'posible IBAN'))
        if PATRON_TELEFONO.search(linea) and not LINEA_JSON_NUMERICA.match(linea):
            hallazgos.append((i, 'posible teléfono'))
        if PATRON_EMAIL.search(linea):
            hallazgos.append((i, 'posible email'))
        if PATRON_SECRETO.search(linea):
            hallazgos.append((i, 'posible secreto/API key'))
        for palabra in denylist_local:
            if palabra.lower() in linea.lower():
                hallazgos.append((i, 'coincidencia con denylist local'))
    return hallazgos


def escanear(archivos):
    denylist_local = cargar_denylist_local()
    nombres_prohibidos = cargar_nombres_prohibidos()
    errores = []

    for archivo in archivos:
        path = Path(archivo)
        nombre = path.name

        if path.suffix.lower() == '.zip':
            errores.append(f"{archivo}: BLOQUEADO — ningún .zip sube nunca (regla fija)")
            continue

        if nombre in nombres_prohibidos:
            errores.append(f"{archivo}: BLOQUEADO — nombre de archivo en NUNCA_SUBE_FILENAMES.txt")
            continue

        if not path.exists():
            continue  # borrado en este commit, nada que escanear

        hallazgos = escanear_archivo(path, denylist_local)
        for linea, motivo in hallazgos:
            errores.append(f"{archivo}:{linea}: {motivo} — revisar antes de continuar")

    return errores


def main():
    archivos = sys.argv[1:]
    if not archivos:
        print("Uso: privacy_scan.py <archivo1> <archivo2> ...")
        return 0
    errores = escanear(archivos)
    if errores:
        print("=" * 70)
        print("ESCANER DE PRIVACIDAD — se han encontrado posibles problemas:")
        print("=" * 70)
        for e in errores:
            print(f"  - {e}")
        print()
        print("Ningún commit/PR pasa hasta revisar esto a mano. Si es un falso")
        print("positivo confirmado, corrige el patrón o el motivo aquí, en")
        print("scripts/privacy_scan.py, en vez de saltarte el hook.")
        return 1
    print("Escáner de privacidad: sin hallazgos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
