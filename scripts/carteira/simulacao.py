"""Simulação de venda dos ativos atuais na cotação informada (sem recomendação de compra ou venda)."""
from __future__ import annotations
from dataclasses import dataclass, field

from .apuracao import GRUPO


@dataclass
class SimAtivo:
    ticker: str
    classe: str
    qtd: float
    preco_medio: float
    cotacao: float
    valor_venda: float
    custo: float
    resultado: float
    isento_sozinho: bool
    aliquota: float
    imposto_sem_compensacao: float
    prejuizo_compensavel_disponivel: float
    imposto_com_compensacao: float
    liquido_sem_compensacao: float
    liquido_com_compensacao: float
    obs: str = ""


def simular_venda_individual(posicoes, cotacoes: dict[str, float], prejuizo: dict[str, float], regras: dict) -> list[SimAtivo]:
    """Cada ativo vendido isoladamente em um mês sem outras vendas. Para ações, a isenção vale se a venda <= R$ 20 mil."""
    limite = float(regras["isencao_20k"]["limite_mensal"])
    aliq = {"comuns": float(regras["aliquotas"]["operacoes_comuns"]["valor"]),
            "fii": float(regras["aliquotas"]["fii"]["valor"]), "day_trade": float(regras["aliquotas"]["day_trade"]["valor"])}
    out = []
    for t, p in sorted(posicoes.items()):
        if p.qtd < 1e-9 or t not in cotacoes:
            continue
        g = GRUPO.get(p.classe, "comuns")
        venda = p.qtd * cotacoes[t]
        res = venda - p.custo
        isento = p.classe == "acoes" and venda <= limite
        disp = prejuizo.get(g, 0.0)
        if res <= 0:
            imp0 = imp1 = 0.0
            obs = "prejuízo: sem imposto; valor entra no saldo compensável do grupo " + g
            if isento:
                obs += " (mesmo em mês isento, a perda é compensável se declarada)"
        elif isento:
            imp0 = imp1 = 0.0
            obs = f"ganho isento (vendas de ações no mês <= R$ {limite:,.0f}); não consome prejuízo acumulado"
        else:
            imp0 = round(res * aliq[g], 2)
            imp1 = round(max(0.0, res - disp) * aliq[g], 2)
            obs = f"tributável a {aliq[g]*100:.0f}% (sem isenção para {p.classe}); prejuízo acumulado do grupo pode abater"
        out.append(SimAtivo(t, p.classe, p.qtd, p.preco_medio, cotacoes[t], round(venda, 2), round(p.custo, 2), round(res, 2),
                            isento, aliq[g], imp0, disp, imp1, round(venda - imp0, 2), round(venda - imp1, 2), obs))
    return out


def simular_venda_total(posicoes, cotacoes, prejuizo, regras) -> dict:
    """Todos os ativos vendidos no mesmo mês: o total de ações pode ultrapassar R$ 20 mil e perder a isenção."""
    limite = float(regras["isencao_20k"]["limite_mensal"])
    aliq_c = float(regras["aliquotas"]["operacoes_comuns"]["valor"])
    vendas_acoes = sum(p.qtd * cotacoes[t] for t, p in posicoes.items() if p.qtd > 1e-9 and t in cotacoes and p.classe == "acoes")
    res = {"acoes": 0.0, "bdr": 0.0, "etf": 0.0}
    venda_total = 0.0
    for t, p in posicoes.items():
        if p.qtd < 1e-9 or t not in cotacoes or p.classe not in res:
            continue
        v = p.qtd * cotacoes[t]
        venda_total += v
        res[p.classe] += v - p.custo
    isento = vendas_acoes <= limite
    if isento:
        acoes_trib = res["acoes"] if res["acoes"] < 0 else 0.0
        acoes_isento = res["acoes"] if res["acoes"] > 0 else 0.0
    else:
        acoes_trib, acoes_isento = res["acoes"], 0.0
    base = acoes_trib + res["bdr"] + res["etf"]
    usado = min(prejuizo.get("comuns", 0.0), base) if base > 0 else 0.0
    imposto = round(max(0.0, base - usado) * aliq_c, 2)
    return {"vendas_acoes": round(vendas_acoes, 2), "venda_total": round(venda_total, 2), "isento_acoes": isento,
            "resultado": {k: round(v, 2) for k, v in res.items()}, "ganho_acoes_isento": round(acoes_isento, 2),
            "base_comuns": round(base, 2), "prejuizo_usado": round(usado, 2), "imposto": imposto,
            "liquido": round(venda_total - imposto, 2), "prejuizo_restante": round(prejuizo.get("comuns", 0.0) - usado + (-base if base < 0 else 0.0), 2)}
