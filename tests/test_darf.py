from datetime import date
from carteira.darf import multa_mora, juros_mora, simular_parcelamento, Darf

SELIC = {(2024, 5): 0.0083, (2024, 6): 0.0079, (2024, 7): 0.0091, (2024, 8): 0.0087}
REGRAS = {"multa_de_mora": {"taxa_dia": 0.0033, "limite": 0.20}}


def test_multa_por_dia_e_teto():
    assert multa_mora(100.0, date(2024, 4, 30), date(2024, 4, 30)) == (0.0, 0.0)
    assert multa_mora(100.0, date(2024, 4, 30), date(2024, 5, 10)) == (0.033, 3.3)     # 10 dias
    pct, v = multa_mora(100.0, date(2024, 4, 30), date(2024, 12, 31))
    assert pct == 0.20 and v == 20.0


def test_juros_selic_mais_um_por_cento():
    assert juros_mora(100.0, date(2024, 4, 30), date(2024, 4, 30), SELIC) == (0.0, 0.0)
    # pago em maio (mês seguinte): só 1%
    assert juros_mora(100.0, date(2024, 4, 30), date(2024, 5, 15), SELIC) == (0.01, 1.0)
    # pago em agosto: selic mai+jun+jul + 1%
    pct, v = juros_mora(1000.0, date(2024, 4, 30), date(2024, 8, 20), SELIC)
    assert abs(pct - (0.0083 + 0.0079 + 0.0091 + 0.01)) < 1e-9 and v == 35.3
    # mês sem selic conhecida usa premissa
    pct, _ = juros_mora(100.0, date(2024, 4, 30), date(2024, 10, 5), SELIC, selic_futura=0.01)
    assert abs(pct - (0.0083 + 0.0079 + 0.0091 + 0.0087 + 0.01 + 0.01)) < 1e-9


def test_parcelamento_paga_do_mais_recente_ao_mais_antigo():
    darfs = [Darf((2024, 3), date(2024, 4, 30), 100.0), Darf((2024, 6), date(2024, 7, 31), 50.0)]
    r = simular_parcelamento(darfs, SELIC, 60.0, date(2024, 8, 30), 0.01, REGRAS)
    cron = r["cronograma"]
    assert cron[0]["competencia"] == (2024, 6)                 # mais recente primeiro
    assert cron[0]["quitado"] and cron[0]["total_pago"] <= 60.0 + 0.01
    assert r["total_pago"] > 150.0                             # custo adicional de multa/juros
    assert cron[-1]["competencia"] == (2024, 3) and cron[-1]["quitado"]
