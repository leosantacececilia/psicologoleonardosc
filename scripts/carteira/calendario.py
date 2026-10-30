"""Calendário de dias úteis (feriados nacionais e da B3) e prazos de DARF."""
from __future__ import annotations
from datetime import date, timedelta
from functools import lru_cache


def pascoa(ano: int) -> date:
    """Domingo de Páscoa (algoritmo de Meeus/Jones/Butcher, calendário gregoriano)."""
    a = ano % 19
    b, c = divmod(ano, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(ano, mes, dia)


@lru_cache(maxsize=None)
def feriados_nacionais(ano: int) -> frozenset[date]:
    p = pascoa(ano)
    fixos = [(1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15), (12, 25)]
    fs = {date(ano, m, d) for m, d in fixos}
    if ano >= 2024:  # Lei 14.759/2023 - Dia Nacional de Zumbi e da Consciência Negra
        fs.add(date(ano, 11, 20))
    fs |= {p - timedelta(days=48), p - timedelta(days=47),  # carnaval (seg/ter)
           p - timedelta(days=2),                           # sexta-feira santa
           p + timedelta(days=60)}                          # Corpus Christi
    return frozenset(fs)


@lru_cache(maxsize=None)
def feriados_b3(ano: int) -> frozenset[date]:
    """Dias sem pregão na B3: feriados nacionais + 24/12 e 31/12."""
    return frozenset(feriados_nacionais(ano) | {date(ano, 12, 24), date(ano, 12, 31)})


def eh_dia_util(d: date, b3: bool = False) -> bool:
    if d.weekday() >= 5:
        return False
    fer = feriados_b3(d.year) if b3 else feriados_nacionais(d.year)
    return d not in fer


def somar_dias_uteis(d: date, n: int, b3: bool = False) -> date:
    """Soma n dias úteis (n pode ser negativo)."""
    passo = 1 if n >= 0 else -1
    restante = abs(n)
    while restante > 0:
        d = d + timedelta(days=passo)
        if eh_dia_util(d, b3=b3):
            restante -= 1
    return d


def data_pregao_estimada(data_liquidacao: date, ciclo: int = 2) -> date:
    """Data do pregão estimada a partir da data de liquidação (ciclo D+n da B3)."""
    return somar_dias_uteis(data_liquidacao, -ciclo, b3=True)


def ultimo_dia_util_do_mes(ano: int, mes: int) -> date:
    """Último dia útil bancário do mês. 31/12 não tem expediente bancário."""
    if mes == 12:
        d = date(ano, 12, 31)
    else:
        d = date(ano, mes + 1, 1) - timedelta(days=1)
    while (not eh_dia_util(d)) or (d.month == 12 and d.day == 31):
        d -= timedelta(days=1)
    return d


def vencimento_darf(ano: int, mes: int) -> date:
    """Vencimento do DARF 6015: último dia útil do mês seguinte ao da apuração (IN 1585 art. 56 §5)."""
    ano2, mes2 = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
    return ultimo_dia_util_do_mes(ano2, mes2)


def mes_seguinte(ano: int, mes: int) -> tuple[int, int]:
    return (ano + 1, 1) if mes == 12 else (ano, mes + 1)
