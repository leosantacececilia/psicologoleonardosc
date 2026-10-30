from datetime import date
from carteira.motor import Alienacao, Compra
from carteira.apuracao import apurar, detectar_day_trade

REGRAS = {"isencao_20k": {"limite_mensal": 20000.0},
          "aliquotas": {"operacoes_comuns": {"valor": 0.15}, "day_trade": {"valor": 0.20}, "fii": {"valor": 0.20}},
          "darf": {"minimo": 10.0}}


def al(liq, preg, ticker, classe, valor, custo, corretora="NU", tipo="venda"):
    return Alienacao(date.fromisoformat(liq), date.fromisoformat(preg), ticker, classe, 1.0, valor, custo, corretora, tipo)


def test_isencao_acoes_ate_20k_e_tributacao_acima():
    ap = apurar([al("2024-03-05", "2024-03-01", "AAAA3", "acoes", 19000.0, 10000.0)], REGRAS)
    assert ap[0].imposto_mes == 0 and abs(ap[0].acoes_isento_ganho - 9000.0) < 1e-9
    ap = apurar([al("2024-03-05", "2024-03-01", "AAAA3", "acoes", 20000.01, 10000.0)], REGRAS)
    assert abs(ap[0].imposto_mes - round(10000.01 * 0.15, 2)) < 1e-6


def test_limite_usa_mes_do_pregao_e_apuracao_mes_da_liquidacao():
    # duas vendas no pregão de fevereiro somando > 20k, uma liquidada em março
    a1 = al("2024-02-28", "2024-02-26", "AAAA3", "acoes", 15000.0, 10000.0)
    a2 = al("2024-03-01", "2024-02-28", "BBBB3", "acoes", 6000.0, 5000.0)
    ap = apurar([a1, a2], REGRAS)
    assert [m.chave for m in ap] == [(2024, 2), (2024, 3)]
    assert ap[0].imposto_mes == 750.0 and ap[1].imposto_mes == 150.0


def test_prejuizo_em_mes_isento_compensa_ganho_de_bdr():
    ap = apurar([al("2024-01-10", "2024-01-08", "AAAA3", "acoes", 1000.0, 1500.0),      # perda 500 isenta
                 al("2024-02-10", "2024-02-08", "XXXX34", "bdr", 2000.0, 1000.0)], REGRAS)  # ganho 1000
    assert ap[0].prejuizo_acumulado_fim["comuns"] == 500.0
    assert ap[1].prejuizo_usado["comuns"] == 500.0 and ap[1].imposto_mes == 75.0


def test_fii_nao_compensa_com_comuns_e_tem_20pct():
    ap = apurar([al("2024-01-10", "2024-01-08", "FFFF11", "fii", 1000.0, 3000.0),
                 al("2024-02-10", "2024-02-08", "XXXX34", "bdr", 2000.0, 1000.0),
                 al("2024-03-10", "2024-03-08", "GGGG11", "fii", 5000.0, 2000.0)], REGRAS)
    assert ap[1].imposto_mes == 150.0                       # sem usar prejuízo de FII
    assert ap[2].prejuizo_usado["fii"] == 2000.0 and ap[2].imposto_mes == 200.0   # (3000-2000)*20%


def test_minimo_de_10_reais_e_diferido():
    ap = apurar([al("2024-01-10", "2024-01-08", "XXXX34", "bdr", 1030.0, 1000.0),   # imposto 4,50
                 al("2024-03-10", "2024-03-08", "XXXX34", "bdr", 1040.0, 1000.0)], REGRAS)  # imposto 6,00
    assert ap[0].darf_valor == 0.0 and ap[1].darf_valor == 10.5


def test_bdr_e_etf_sem_isencao():
    ap = apurar([al("2024-01-10", "2024-01-08", "XXXX34", "bdr", 500.0, 100.0),
                 al("2024-01-10", "2024-01-08", "IVVB11", "etf", 500.0, 100.0)], REGRAS)
    assert ap[0].imposto_mes == 120.0


def test_day_trade_detectado_e_20pct():
    a = al("2024-01-10", "2024-01-08", "AAAA3", "acoes", 1100.0, 1000.0, corretora="NU")
    c = Compra(date(2024, 1, 10), date(2024, 1, 8), "AAAA3", 1.0, 1000.0, "NU")
    avisos = detectar_day_trade([a], [c])
    assert avisos and a.classe == "day_trade"
    ap = apurar([a], REGRAS)
    assert ap[0].imposto_mes == 20.0
