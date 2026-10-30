"""Orquestra o cálculo completo e devolve um dicionário com todos os resultados (usado por run.py e relatorio.py)."""
from __future__ import annotations
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from .apuracao import apurar, detectar_day_trade, GRUPO
from .carregar import (carregar_extrato, carregar_posicoes_investidor10, carregar_proventos_investidor10,
                       carregar_selic, carregar_regras, carregar_precos)
from .darf import calcular_darfs, simular_parcelamento
from .motor import Motor, LINHA_XIRR
from .rentabilidade import xirr, volatilidade_anual, max_drawdown, retornos_mensais, cagr
from .simulacao import simular_venda_individual, simular_venda_total

ESCOPO = ("acoes", "bdr", "etf")


def analisar(raiz: str | Path, hoje: date, orcamento_mensal: float = 200.0) -> dict:
    raiz = Path(raiz)
    regras = carregar_regras(raiz / "regras.yaml")
    selic = carregar_selic(raiz / "dados/selic_mensal.csv")
    eventos = carregar_extrato(raiz / "dados/movimentacao-2026-10-30-16-53-43.xlsx")
    inv10 = carregar_posicoes_investidor10(raiz / "dados/posicoes_investidor10_2026-10-30.csv")
    prov10 = carregar_proventos_investidor10(raiz / "dados/proventos_investidor10_pagina1_2026-10-30.csv")
    precos = carregar_precos(raiz / "dados/precos_mensais.csv")

    motor = Motor(ciclo_liquidacao=2)
    res = motor.processar(eventos)
    avisos_dt = detectar_day_trade(res.alienacoes, res.compras)
    ap = apurar(res.alienacoes, regras)
    darfs = calcular_darfs(ap, selic, hoje, regras)
    # Selic futura: último mês completo disponível (premissa para o parcelamento)
    ultimo_mes_completo = (hoje.year, hoje.month - 1) if hoje.month > 1 else (hoje.year - 1, 12)
    selic_futura = selic.get(ultimo_mes_completo, 0.01)
    from .calendario import ultimo_dia_util_do_mes, mes_seguinte
    a, m = mes_seguinte(hoje.year, hoje.month)
    parcel = simular_parcelamento(darfs, selic, orcamento_mensal, ultimo_dia_util_do_mes(a, m), selic_futura, regras)

    cot = {p.ativo: p.cotacao for p in inv10}
    prej = ap[-1].prejuizo_acumulado_fim if ap else {"comuns": 0.0, "fii": 0.0, "day_trade": 0.0}
    sim_ind = simular_venda_individual(res.posicoes, cot, prej, regras)
    sim_tot = simular_venda_total(res.posicoes, cot, prej, regras)

    # ---- reconciliação de posições
    recon = []
    calc = {t: p for t, p in res.posicoes.items() if p.qtd > 1e-9}
    for p in inv10:
        c = calc.get(p.ativo)
        recon.append({"ativo": p.ativo, "classe": p.classe, "qtd_calc": c.qtd if c else 0.0, "qtd_inv10": p.quantidade,
                      "pm_calc": c.preco_medio if c else None, "pm_inv10": p.preco_medio, "cotacao": p.cotacao,
                      "custo_calc": c.custo if c else 0.0, "custo_inv10": p.quantidade * p.preco_medio,
                      "dif_qtd": (c.qtd if c else 0.0) - p.quantidade, "dif_pm": ((c.preco_medio if c else 0.0) - p.preco_medio)})
    for t, c in calc.items():
        if t not in cot:
            recon.append({"ativo": t, "classe": c.classe, "qtd_calc": c.qtd, "qtd_inv10": 0.0, "pm_calc": c.preco_medio, "pm_inv10": None,
                          "cotacao": None, "custo_calc": c.custo, "custo_inv10": 0.0, "dif_qtd": c.qtd, "dif_pm": None})

    # ---- conferência dos proventos do Investidor10 contra o extrato
    from itertools import combinations
    b3_rows = defaultdict(list)            # (ticker, data) -> [valores]
    for e in eventos:
        if e.mov in ("Dividendo", "Juros Sobre Capital Próprio", "Rendimento") and e.ticker:
            b3_rows[(e.ticker, e.data)].append(e.valor or 0.0)

    def _bate(vals, alvo):
        for k in range(1, min(4, len(vals)) + 1):
            for comb in combinations(vals, k):
                if abs(sum(comb) - alvo) < 0.015:
                    return True
        return False

    pagos10 = {(r["ativo"], r["data_com"], r["valor_liquido"]) for r in prov10 if r["status"] == "Pago"}
    conf_prov = []
    for r in prov10:
        t = r["ativo"]; liq = float(r["valor_liquido"]); dp = date.fromisoformat(r["data_pagamento"]); dc = date.fromisoformat(r["data_com"])
        achado = None
        for (tk, d), vals in sorted(b3_rows.items()):
            if tk != t or d < dc:
                continue
            if r["status"] == "Pago" and abs((d - dp).days) > 5:
                continue
            if _bate(vals, liq):
                achado = d
                break
        if r["status"] == "Pago":
            st = "confere com o extrato da B3" if achado else "NÃO encontrado no extrato da B3 (conferir)"
        elif (t, r["data_com"], r["valor_liquido"]) in pagos10:
            st = "DUPLICADO no Investidor10: mesmo provento já aparece como Pago"
        elif achado:
            st = f"já consta como PAGO no extrato da B3 em {achado:%d/%m/%Y} (duplicidade no Investidor10)"
        else:
            st = "a receber (ainda não consta no extrato)"
        conf_prov.append({**r, "status_conferencia": st})

    # ---- rentabilidade por linha de investimento (XIRR) e resumo
    fluxos_linha = defaultdict(list)
    for f in res.fluxos + res.proventos:
        fluxos_linha[f.ticker].append((f.data, f.valor))
    classe_linha = {}
    for t, p in res.posicoes.items():
        classe_linha[LINHA_XIRR.get(t, t)] = p.classe if p.classe not in ("direito", "recibo") else classe_linha.get(LINHA_XIRR.get(t, t), "acoes")
    rent = []
    for linha, fl in sorted(fluxos_linha.items()):
        pos = res.posicoes.get(linha)
        valor_atual = pos.qtd * cot[linha] if pos and pos.qtd > 1e-9 and linha in cot else 0.0
        fl2 = list(fl)
        if valor_atual > 0:
            fl2.append((hoje, valor_atual))
        investido = -sum(v for _, v in fl if v < 0)
        recebido = sum(v for _, v in fl if v > 0)
        prov = sum(f.valor for f in res.proventos if f.ticker == linha)
        taxa = xirr(fl2)
        rent.append({"linha": linha, "classe": classe_linha.get(linha, ""), "investido": investido, "vendas_e_outros": recebido - prov,
                     "proventos": prov, "valor_atual": valor_atual, "resultado_total": recebido + valor_atual - investido,
                     "xirr": taxa, "primeiro_fluxo": min(d for d, _ in fl), "ultimo_fluxo": max(d for d, _ in fl2),
                     "em_carteira": valor_atual > 0})
    def xirr_grupo(classes):
        fl = []
        for linha, lst in fluxos_linha.items():
            if classe_linha.get(linha) in classes:
                fl += lst
                pos = res.posicoes.get(linha)
                if pos and pos.qtd > 1e-9 and linha in cot:
                    fl.append((hoje, pos.qtd * cot[linha]))
        return xirr(fl), fl
    xirr_escopo, fl_escopo = xirr_grupo(ESCOPO)
    xirr_fii, _ = xirr_grupo(("fii",))
    xirr_tudo, _ = xirr_grupo(ESCOPO + ("fii",))
    carteira = {"xirr_escopo": xirr_escopo, "xirr_fii": xirr_fii, "xirr_total": xirr_tudo,
                "investido_escopo": -sum(v for _, v in fl_escopo if v < 0 and _ != hoje),
                "valor_atual": sum(p.qtd * cot[t] for t, p in res.posicoes.items() if p.qtd > 1e-9 and t in cot),
                "proventos_escopo": sum(f.valor for f in res.proventos if classe_linha.get(f.ticker) in ESCOPO),
                "proventos_total": sum(f.valor for f in res.proventos)}

    # ---- risco (série mensal de preços ajustados)
    risco = []
    for t in sorted(cot):
        s = precos.get(t)
        if not s:
            risco.append({"ativo": t, "obs": "sem série de preços"}); continue
        rets = retornos_mensais(s)
        mdd, ini, fim = max_drawdown(s)
        primeira = min((c.data_liq for c in res.compras if c.ticker == t), default=None)
        s_desde = [x for x in s if primeira is None or x[0] >= date(primeira.year, primeira.month, 1)]
        rets_d = retornos_mensais(s_desde)
        mdd_d, ini_d, fim_d = max_drawdown(s_desde) if len(s_desde) > 1 else (None, None, None)
        risco.append({"ativo": t, "inicio_serie": s[0][0], "meses": len(s), "vol_anual": volatilidade_anual(rets), "cagr_serie": cagr(s),
                      "max_drawdown": mdd, "dd_inicio": ini, "dd_fim": fim, "desde_compra": primeira,
                      "vol_anual_desde_compra": volatilidade_anual(rets_d), "max_drawdown_desde_compra": mdd_d, "obs": ""})
    # carteira: pesos atuais, janela comum (últimos 12 meses) e 36 meses sem AURO11
    def risco_carteira(janela_meses: int, excluir=()):
        ativos = [t for t in cot if t in precos and t not in excluir and res.posicoes.get(t) and res.posicoes[t].qtd > 1e-9]
        pesos = {t: res.posicoes[t].qtd * cot[t] for t in ativos}
        tot = sum(pesos.values())
        series = {t: precos[t][-(janela_meses + 1):] for t in ativos}
        n = min(len(s) for s in series.values())
        if n < 7:
            return None
        rets = {t: retornos_mensais(series[t][-n:]) for t in ativos}
        port = [sum(pesos[t] / tot * rets[t][i] for t in ativos) for i in range(n - 1)]
        idx = [(series[ativos[0]][-n:][0][0], 1.0)]
        v = 1.0
        for i, r in enumerate(port):
            v *= 1 + r
            idx.append((series[ativos[0]][-n:][i + 1][0], v))
        mdd, ini, fim = max_drawdown(idx)
        return {"janela_meses": n - 1, "ativos": ativos, "vol_anual": volatilidade_anual(port), "max_drawdown": mdd, "dd_inicio": ini, "dd_fim": fim,
                "retorno_acumulado": v - 1}
    risco_cart = {"12m_todos": risco_carteira(12), "36m_sem_AURO11": risco_carteira(36, excluir=("AURO11",))}

    return {"hoje": hoje, "regras": regras, "selic": selic, "selic_futura": selic_futura, "eventos": eventos, "res": res, "avisos_dt": avisos_dt,
            "apuracao": ap, "darfs": darfs, "parcelamento": parcel, "orcamento_mensal": orcamento_mensal, "cotacoes": cot, "prejuizo_atual": prej,
            "sim_individual": sim_ind, "sim_total": sim_tot, "reconciliacao": recon, "conferencia_proventos": conf_prov, "inv10": inv10,
            "rentabilidade": rent, "carteira": carteira, "risco": risco, "risco_carteira": risco_cart, "precos": precos}
