"""XIRR (TIR com datas), volatilidade e drawdown."""
from __future__ import annotations
from datetime import date
from math import isfinite, log, sqrt


def xnpv(taxa: float, fluxos: list[tuple[date, float]]) -> float:
    d0 = min(d for d, _ in fluxos)
    return sum(v / (1 + taxa) ** ((d - d0).days / 365.0) for d, v in fluxos)


def xirr(fluxos: list[tuple[date, float]], lo: float = -0.9999, hi: float = 10.0, tol: float = 1e-8) -> float | None:
    """Taxa anual que zera o VPL (bisseção). Retorna None se não houver mudança de sinal nos fluxos."""
    fluxos = [(d, v) for d, v in fluxos if abs(v) > 1e-12]
    if not fluxos or not (any(v < 0 for _, v in fluxos) and any(v > 0 for _, v in fluxos)):
        return None
    f_lo, f_hi = xnpv(lo, fluxos), xnpv(hi, fluxos)
    if not (isfinite(f_lo) and isfinite(f_hi)) or f_lo * f_hi > 0:
        # tenta reduzir o intervalo superior
        for h in (5.0, 2.0, 1.0, 0.5):
            f_hi = xnpv(h, fluxos)
            if f_lo * f_hi <= 0:
                hi = h
                break
        else:
            return None
    for _ in range(300):
        mid = (lo + hi) / 2
        f_mid = xnpv(mid, fluxos)
        if abs(f_mid) < tol or (hi - lo) < 1e-10:
            return mid
        if f_lo * f_mid < 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2


def retornos_mensais(serie: list[tuple[date, float]]) -> list[float]:
    return [serie[i][1] / serie[i - 1][1] - 1 for i in range(1, len(serie)) if serie[i - 1][1] > 0]


def volatilidade_anual(retornos: list[float]) -> float | None:
    n = len(retornos)
    if n < 6:
        return None
    mu = sum(retornos) / n
    var = sum((r - mu) ** 2 for r in retornos) / (n - 1)
    return sqrt(var) * sqrt(12)


def max_drawdown(serie: list[tuple[date, float]]) -> tuple[float, date | None, date | None]:
    pico, pico_d, mdd, ini, fim = -1.0, None, 0.0, None, None
    for d, v in serie:
        if v > pico:
            pico, pico_d = v, d
        dd = v / pico - 1 if pico > 0 else 0.0
        if dd < mdd:
            mdd, ini, fim = dd, pico_d, d
    return mdd, ini, fim


def cagr(serie: list[tuple[date, float]]) -> float | None:
    if len(serie) < 2 or serie[0][1] <= 0:
        return None
    anos = (serie[-1][0] - serie[0][0]).days / 365.0
    if anos <= 0:
        return None
    return (serie[-1][1] / serie[0][1]) ** (1 / anos) - 1
