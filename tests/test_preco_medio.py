from datetime import date
from carteira.carregar import Evento
from carteira.motor import Motor


def ev(d, sentido, mov, ticker, qtd, preco=None, valor=None, inst="NU", classe="acoes", linha=1):
    return Evento(date.fromisoformat(d), sentido, mov, f"{ticker} - X", ticker, inst, qtd, preco, valor, classe, linha)


def test_media_ponderada_e_venda_parcial():
    m = Motor()
    r = m.processar([
        ev("2024-01-10", "Credito", "Transferência - Liquidação", "AAAA3", 10, 10.0, 100.0),
        ev("2024-02-10", "Credito", "Transferência - Liquidação", "AAAA3", 10, 20.0, 200.0),
        ev("2024-03-11", "Debito", "Transferência - Liquidação", "AAAA3", 5, 30.0, 150.0),
    ])
    p = r.posicoes["AAAA3"]
    assert abs(p.preco_medio - 15.0) < 1e-9 and abs(p.qtd - 15) < 1e-9 and abs(p.custo - 225.0) < 1e-9
    a = r.alienacoes[0]
    assert abs(a.custo - 75.0) < 1e-9 and abs(a.resultado - 75.0) < 1e-9
    assert a.data_pregao == date(2024, 3, 7)   # liquidação seg 11/03 -> pregão qui 07/03 (D+2 úteis)


def test_desdobro_bonificacao_grupamento_e_fracao():
    m = Motor()
    r = m.processar([
        ev("2024-01-10", "Credito", "Transferência - Liquidação", "BBBB3", 10, 10.0, 100.0),
        ev("2024-02-01", "Credito", "Desdobro", "BBBB3", 10),            # 10 -> 20, custo mantido
        ev("2024-03-01", "Credito", "Bonificação em Ativos", "BBBB3", 2.5),  # custo zero
        ev("2024-03-05", "Debito", "Fração em Ativos", "BBBB3", 0.5),
        ev("2024-03-20", "Credito", "Leilão de Fração", "BBBB3", 0.5, 6.0, 3.0),
        ev("2024-04-01", "Credito", "Grupamento", "BBBB3", 11),          # 22 -> 11
    ])
    p = r.posicoes["BBBB3"]
    # após desdobro: 20 @ 5; bonificação: 22.5 @ 4.444; fração 0.5 sai com custo 2.22
    assert abs(p.qtd - 11) < 1e-9
    assert abs(p.custo - (100.0 - 100.0 / 22.5 * 0.5)) < 1e-6
    leilao = r.alienacoes[0]
    assert leilao.tipo == "leilao_fracao" and abs(leilao.valor - 3.0) < 1e-9 and abs(leilao.custo - 100.0 / 22.5 * 0.5) < 1e-6


def test_subscricao_e_conversao_de_recibo():
    m = Motor()
    r = m.processar([
        ev("2025-02-19", "Credito", "Direito de Subscrição", "ITSA2", 1, classe="direito"),
        ev("2025-03-13", "Credito", "Transferência - Liquidação", "ITSA2", 55, 2.32, 127.6, classe="direito"),
        ev("2025-04-17", "Debito", "Direitos de Subscrição - Exercido", "ITSA2", 56, 6.7, 375.2, classe="direito"),
        ev("2025-04-22", "Credito", "Recibo de Subscrição", "ITSA10", 56, classe="recibo"),
        ev("2025-05-28", "Credito", "Atualização", "ITSA4", 56),
    ])
    p = r.posicoes["ITSA4"]
    assert abs(p.qtd - 56) < 1e-9 and abs(p.custo - 502.8) < 1e-6
    assert r.posicoes["ITSA10"].qtd == 0 and r.posicoes["ITSA2"].qtd == 0


def test_incorporacao_transfere_custo_e_restituicao_reduz_custo():
    m = Motor()
    r = m.processar([
        ev("2023-01-10", "Credito", "Transferência - Liquidação", "MGFF11", 50, 60.0, 3000.0, classe="fii"),
        ev("2024-02-01", "Credito", "Atualização", "VGHF11", 369.66, classe="fii"),
        ev("2024-02-01", "Credito", "Atualização", "MGFF11", 50, classe="fii"),   # reapresentação
        ev("2024-02-07", "Credito", "Resgate", "MGFF11", 50, 4.26, 3.63, classe="fii"),
        ev("2024-03-10", "Credito", "Transferência - Liquidação", "VIVT3", 20, 40.0, 800.0),
        ev("2024-07-10", "Credito", "Restituição de Capital", "VIVT3", 20, 0.908, 18.15),
    ])
    v = r.posicoes["VGHF11"]
    assert abs(v.qtd - 369.66) < 1e-9 and abs(v.custo - (3000.0 - 3.63)) < 1e-6
    assert r.posicoes["MGFF11"].qtd == 0
    assert abs(r.posicoes["VIVT3"].custo - (800.0 - 18.15)) < 1e-6
    assert not any("não bate" in a for a in r.avisos)


def test_venda_sem_posicao_gera_aviso():
    m = Motor()
    r = m.processar([ev("2024-01-10", "Debito", "Transferência - Liquidação", "ZZZZ3", 5, 10.0, 50.0)])
    assert any("histórico incompleto" in a for a in r.avisos)
