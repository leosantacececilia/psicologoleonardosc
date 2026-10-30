from datetime import date
from carteira.rentabilidade import xirr, xnpv, volatilidade_anual, max_drawdown


def test_xirr_simples():
    fl = [(date(2024, 1, 1), -1000.0), (date(2025, 1, 1), 1100.0)]
    r = xirr(fl)
    assert abs(r - (1.1 ** (365 / 366) - 1)) < 1e-6   # convenção 365 dias; 2024 é bissexto
    assert xirr([(date(2024, 1, 1), -1.0)]) is None


def test_xirr_com_proventos():
    fl = [(date(2024, 1, 1), -1000.0), (date(2024, 7, 1), 50.0), (date(2025, 1, 1), 1000.0)]
    r = xirr(fl)
    assert abs(xnpv(r, fl)) < 1e-6 and 0.04 < r < 0.06


def test_vol_e_drawdown():
    serie = [(date(2024, m, 1), v) for m, v in zip(range(1, 13), [100, 110, 99, 120, 90, 95, 100, 130, 125, 140, 120, 150])]
    mdd, ini, fim = max_drawdown(serie)
    assert abs(mdd - (90 / 120 - 1)) < 1e-9 and ini == date(2024, 4, 1) and fim == date(2024, 5, 1)
    assert volatilidade_anual([0.01] * 12) == 0.0
