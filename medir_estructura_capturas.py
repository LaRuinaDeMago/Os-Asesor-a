#!/usr/bin/env python3
"""medir_estructura_capturas.py — mide como SON tus fotos reales, sin ver
ninguna. Diseño de tres roles: este script lo he escrito yo sin ver un solo
dato; lo ejecutas tu, en tu maquina, sobre tus fotos reales; a mi solo me
llegan los agregados que imprime, nunca una fila por fichero.

PARA QUE SIRVE
---------------
crear_muestras_sinteticas.py fabrica una foto de movil "mala" a ojo
(rotacion, desenfoque y luz fijados por mi criterio, no medidos). Este
script cierra ese hueco: mide como son tus fotos DE VERDAD (nitidez,
resolucion, orientacion, si llevan metadatos de ubicacion) para que la
proxima version de las sinteticas se pueda calibrar contra un numero real
en vez de una suposicion — la misma disciplina que ya siguio
`retro_semaforo.py` con los umbrales de `importe_atipico`.

QUE MIDE, Y QUE NO
-------------------
Solo propiedades ESTRUCTURALES de la imagen — nunca su contenido:
  · dimensiones (ancho x alto) y relacion de aspecto
  · una puntuacion de nitidez (varianza tras un filtro de bordes: cuanto
    mas alta, mas nitida; un valor bajo es sospechoso de desenfoque)
  · si el fichero lleva EXIF, y dentro de el, si lleva GPS — nunca las
    coordenadas, solo si el campo EXISTE
  · si lleva la etiqueta de orientacion (indica si la camara rotó la foto)
  · tamaño de fichero y formato

NO abre el contenido de la factura, no hace OCR, no llama a ninguna IA.

LO QUE SALE POR CONSOLA: SOLO AGREGADOS DE TODA LA CARPETA
--------------------------------------------------------------
Ni una linea por fichero, ni un nombre, ni una ruta. Solo minimo/mediana/
maximo de cada metrica sobre el conjunto entero, y recuentos. Es la misma
regla que ya siguen `consolidar_identidad.py` y `diag_carpetas_multiempresa.py`
("sin imprimir un solo nombre por consola") aplicada a imagenes en vez de a
razones sociales.

Un fichero que no se puede leer se cuenta por el TIPO de excepcion, nunca
por su mensaje (`.claude/rules/datos.md`, tabla de riesgos: "un script peta
e imprime una fila en el mensaje de error").

USO
----
    python medir_estructura_capturas.py "RUTA_A_TU_CARPETA_DE_FOTOS"

Diego: esto lo ejecutas TU, en tu terminal — no se lo pidas a Claude que lo
corra por ti aunque el script solo imprima agregados (regla ya fijada:
comandos sobre ficheros reales, siempre en tu maquina). Lo que imprime al
final SI es seguro de pegar en el chat, letra por letra.
"""
import argparse
import os
import statistics
import sys

from PIL import Image, ImageFilter, ImageStat

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EXTENSIONES = (".jpg", ".jpeg", ".png", ".heic", ".webp")

# Tag EXIF de GPSInfo (IFD), constante de la propia especificacion Exif —
# no es un numero elegido a dedo. Ver PIL.ExifTags.Base.GPSInfo.
TAG_GPS_INFO = 0x8825
TAG_ORIENTATION = 0x0112


def nitidez(img_gris):
    """Varianza tras un filtro de bordes: proxy de nitidez sin depender de
    numpy/opencv. Mas alto = mas nitida. No es una metrica calibrada contra
    nada externo — solo sirve para COMPARAR fotos entre si, no como umbral
    absoluto de "esto es demasiado borroso"."""
    bordes = img_gris.filter(ImageFilter.FIND_EDGES)
    return ImageStat.Stat(bordes).var[0]


def analizar_una(ruta):
    """Devuelve un dict de metricas de UNA imagen, o lanza si no se puede
    leer. Nunca toca el nombre de fichero para nada mas que abrirlo."""
    with Image.open(ruta) as img:
        ancho, alto = img.size
        formato = img.format
        gris = img.convert("L")
        n = nitidez(gris)

        exif = {}
        try:
            exif = img.getexif() or {}
        except Exception:
            exif = {}
        tiene_gps = TAG_GPS_INFO in exif
        tiene_orientacion = TAG_ORIENTATION in exif

    tam_bytes = os.path.getsize(ruta)
    return {
        "ancho": ancho, "alto": alto, "formato": formato,
        "nitidez": n, "tiene_gps": tiene_gps,
        "tiene_orientacion": tiene_orientacion, "tam_bytes": tam_bytes,
    }


def resumen(valores):
    if not valores:
        return "sin datos"
    return (f"min {min(valores):.1f} · mediana {statistics.median(valores):.1f} "
            f"· max {max(valores):.1f}")


def main():
    parser = argparse.ArgumentParser(
        description="Mide propiedades estructurales de una carpeta de fotos "
                    "reales, sin ver su contenido. Ejecutar en LOCAL.")
    parser.add_argument("carpeta", help="Carpeta con las fotos reales a medir")
    args = parser.parse_args()

    if not os.path.isdir(args.carpeta):
        print(f"ERROR: '{args.carpeta}' no es una carpeta.")
        return 1

    archivos = sorted(f for f in os.listdir(args.carpeta)
                       if f.lower().endswith(EXTENSIONES))
    print(f"Encontrados {len(archivos)} ficheros de imagen en la carpeta.")
    if not archivos:
        return 0

    anchos, altos, nitideces, tamanos = [], [], [], []
    con_gps = con_orientacion = 0
    formatos = {}
    errores = {}

    for nombre in archivos:
        ruta = os.path.join(args.carpeta, nombre)
        try:
            m = analizar_una(ruta)
        except Exception as e:
            # Solo el TIPO, nunca el mensaje ni el nombre del fichero.
            tipo = type(e).__name__
            errores[tipo] = errores.get(tipo, 0) + 1
            continue
        anchos.append(m["ancho"])
        altos.append(m["alto"])
        nitideces.append(m["nitidez"])
        tamanos.append(m["tam_bytes"] / 1024)  # KB
        formatos[m["formato"]] = formatos.get(m["formato"], 0) + 1
        if m["tiene_gps"]:
            con_gps += 1
        if m["tiene_orientacion"]:
            con_orientacion += 1

    n = len(anchos)
    print("=" * 70)
    print(f"AGREGADO SOBRE {n} IMAGENES LEIDAS CORRECTAMENTE "
          f"(de {len(archivos)} encontradas)")
    print("=" * 70)
    if errores:
        print(f"No se pudieron leer {sum(errores.values())}, por tipo: {errores}")
    if n == 0:
        print("Ninguna imagen se pudo leer — nada mas que agregar.")
        return 0

    print(f"Formato: { {k: v for k, v in formatos.items()} }")
    print(f"Ancho (px):    {resumen(anchos)}")
    print(f"Alto (px):     {resumen(altos)}")
    print(f"Tamaño (KB):   {resumen(tamanos)}")
    print(f"Nitidez (proxy, mas alto = mas nitida): {resumen(nitideces)}")
    print(f"Con etiqueta de orientacion EXIF: {con_orientacion}/{n} "
          f"({100 * con_orientacion / n:.0f}%)")
    print(f"Con datos de UBICACION (GPS) en el EXIF: {con_gps}/{n} "
          f"({100 * con_gps / n:.0f}%)")
    if con_gps:
        print()
        print("⚠️  AVISO — no es ruido: si alguna de estas fotos ha salido")
        print("   alguna vez de tu movil/PC (WhatsApp, email, subida a algun")
        print("   sitio), pudo llevarse consigo la ubicacion GPS del negocio")
        print("   del cliente sin que nadie lo pidiera ni lo supiera. Merece")
        print("   revisarse aparte de este banco de pruebas.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
