# -*- coding: utf-8 -*-
"""GUARD G7 v1.1 — Reconciliación de ledger (2026-07-14)
Compara lotes vivos del motor vs Available de fecha MÁS RECIENTE por moneda.
Tolerancia 1e-3 unidades: caza operaciones omitidas, ignora polvo de redondeo.
v1.0→v1.1: fix de ordenación (transactions viene DESC; seleccionar por max(Date),
nunca por posición). Bug cazado en estreno por protocolo de discrepancia:
Δ=+17.738,33 PUMP == saldo intermedio tras primer fill 11/09 → raíz identificada."""
import csv, glob
def g7_reconciliar(dir_fuentes, lotes_vivos_motor, tol=1e-3):
    ledger, fecha = {}, {}
    for f in glob.glob(dir_fuentes + "/*transactions*.csv"):
        for r in csv.DictReader(open(f, encoding="utf-8-sig")):
            c, d = r["Coin"], r["Date"]
            if c not in fecha or d > fecha[c]:
                fecha[c], ledger[c] = d, float(str(r["Available"]).replace(",",""))
    fallos = []
    for coin in sorted(set(lotes_vivos_motor) | set(ledger)):
        t, l = lotes_vivos_motor.get(coin, 0.0), ledger.get(coin, 0.0)
        if abs(t - l) > tol:
            fallos.append(f"{coin}: motor={t:.8f} vs ledger={l:.8f} (Δ={t-l:+.8f})")
    return (len(fallos) == 0), fallos
