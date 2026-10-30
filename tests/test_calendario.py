from datetime import date
from carteira.calendario import pascoa, eh_dia_util, data_pregao_estimada, vencimento_darf, ultimo_dia_util_do_mes, feriados_nacionais


def test_pascoa_e_feriados_moveis():
    assert pascoa(2024) == date(2024, 3, 31)
    assert pascoa(2026) == date(2026, 4, 5)
    f = feriados_nacionais(2024)
    assert date(2024, 2, 12) in f and date(2024, 2, 13) in f      # carnaval
    assert date(2024, 3, 29) in f                                  # sexta-feira santa
    assert date(2024, 5, 30) in f                                  # Corpus Christi
    assert date(2024, 11, 20) in f and date(2023, 11, 20) not in feriados_nacionais(2023)


def test_data_pregao_d2():
    # quinta 18/06/2026 -> liquidação segunda 22/06/2026 (confirmado pelo data-com do Investidor10)
    assert data_pregao_estimada(date(2026, 6, 22)) == date(2026, 6, 18)
    # liquidação 01/03/2024 (sexta) -> pregão 28/02/2024 (quarta)
    assert data_pregao_estimada(date(2024, 3, 1)) == date(2024, 2, 28)
    # B3 não abre em 24/12 e 31/12
    assert not eh_dia_util(date(2025, 12, 24), b3=True) and eh_dia_util(date(2025, 12, 24), b3=False)


def test_vencimento_darf():
    assert vencimento_darf(2024, 3) == date(2024, 4, 30)
    assert vencimento_darf(2024, 5) == date(2024, 6, 28)     # 30/06/2024 é domingo
    assert vencimento_darf(2026, 1) == date(2026, 2, 27)     # 28/02/2026 é sábado
    assert vencimento_darf(2025, 11) == date(2025, 12, 30)   # 31/12 sem expediente bancário
    assert ultimo_dia_util_do_mes(2026, 10) == date(2026, 10, 30)
