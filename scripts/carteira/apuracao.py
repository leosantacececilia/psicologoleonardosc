"""Apuração mensal de ganhos líquidos por categoria, isenção de R$ 20 mil e compensação de prejuízos.

Fontes: Lei 11.033/2004 arts. 2º e 3º; IN RFB 1585/2015 arts. 37, 56, 58, 59, 64 e 65; P&R IRPF 2026 (ver regras.yaml).
"""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from .motor import Alienacao, Compra

CATEGORIAS = ("acoes", "bdr", "etf", "fii", "day_trade")
GRUPO = {"acoes": "comuns", "bdr": "comuns", "etf": "comuns", "fii": "fii", "day_trade": "day_trade"}


@dataclass
class ApuracaoMes:
    ano: int
    mes: int
    vendas: dict[str, float] = field(default_factory=lambda: defaultdict(float))        # valor alienado por categoria (mês de liquidação)
    vendas_acoes_pregao: float = 0.0                                                    # vendas de ações por mês de PREGÃO (p/ limite)
    resultado: dict[str, float] = field(default_factory=lambda: defaultdict(float))     # resultado bruto por categoria
    acoes_isento_ganho: float = 0.0        # ganho de ações isento no mês
    acoes_resultado_tributavel: float = 0.0  # resultado de ações que entra no grupo "comuns" (perdas isentas e meses > 20k)
    base_grupo: dict[str, float] = field(default_factory=dict)        # resultado líquido do mês por grupo (antes da compensação)
    prejuizo_usado: dict[str, float] = field(default_factory=dict)
    base_calculo: dict[str, float] = field(default_factory=dict)
    imposto_grupo: dict[str, float] = field(default_factory=dict)
    imposto_mes: float = 0.0
    imposto_diferido_entrada: float = 0.0   # acumulado < R$10 vindo de meses anteriores
    darf_valor: float = 0.0                 # valor a recolher neste mês (0 se diferido)
    prejuizo_acumulado_fim: dict[str, float] = field(default_factory=dict)
    obs: list[str] = field(default_factory=list)

    @property
    def chave(self):
        return (self.ano, self.mes)


def detectar_day_trade(alienacoes: list[Alienacao], compras: list[Compra]) -> list[str]:
    """Day trade = compra e venda do mesmo ativo, no mesmo pregão, na mesma corretora (IN 1585 art. 65 §1º).
    Retorna avisos; neste extrato não se espera nenhum. A classificação em 'day_trade' é feita marcando a alienação."""
    avisos = []
    compras_idx = defaultdict(float)
    for c in compras:
        compras_idx[(c.data_pregao, c.ticker, c.corretora)] += c.qtd
    for a in alienacoes:
        k = (a.data_pregao, a.ticker, a.corretora)
        if a.tipo == "venda" and compras_idx.get(k, 0) > 0:
            a.classe = "day_trade"
            avisos.append(f"{a.data_pregao} {a.ticker}: compra e venda no mesmo pregão/corretora -> tratado como day trade (20%)")
    return avisos


def apurar(alienacoes: list[Alienacao], regras: dict, ate: date | None = None) -> list[ApuracaoMes]:
    limite = float(regras["isencao_20k"]["limite_mensal"])
    aliq = {"comuns": float(regras["aliquotas"]["operacoes_comuns"]["valor"]),
            "day_trade": float(regras["aliquotas"]["day_trade"]["valor"]),
            "fii": float(regras["aliquotas"]["fii"]["valor"])}
    minimo = float(regras["darf"]["minimo"])

    als = [a for a in alienacoes if a.classe in CATEGORIAS and (ate is None or a.data_liq <= ate)]
    # 1) total de vendas de ações por mês de pregão (limite de isenção usa a data do fato gerador - P&R 745)
    vendas_pregao = defaultdict(float)
    for a in als:
        if a.classe == "acoes":
            vendas_pregao[(a.data_pregao.year, a.data_pregao.month)] += a.valor
    # 2) agrupa por mês de liquidação (apuração/DARF - P&R 745)
    meses: dict[tuple[int, int], ApuracaoMes] = {}
    for a in als:
        k = (a.data_liq.year, a.data_liq.month)
        m = meses.setdefault(k, ApuracaoMes(*k))
        m.vendas[a.classe] += a.valor
        m.resultado[a.classe] += a.resultado
        if a.classe == "acoes":
            isento = vendas_pregao[(a.data_pregao.year, a.data_pregao.month)] <= limite
            if isento:
                m.acoes_isento_ganho += a.resultado   # líquido do mês; sinal tratado abaixo
            else:
                m.acoes_resultado_tributavel += a.resultado
                m.obs.append(f"{a.ticker}: vendas de ações no pregão de {a.data_pregao:%m/%Y} superaram R$ {limite:,.0f}; ganho tributável")
    for k, m in meses.items():
        m.vendas_acoes_pregao = vendas_pregao.get(k, 0.0)
        # ganho líquido de ações em meses isentos: positivo => isento; negativo => prejuízo compensável (IN 1585 art. 59 §1º)
        if m.acoes_isento_ganho < 0:
            m.acoes_resultado_tributavel += m.acoes_isento_ganho
            m.obs.append(f"prejuízo de R$ {-m.acoes_isento_ganho:,.2f} em ações (mês isento) levado à compensação")
            m.acoes_isento_ganho = 0.0
    # 3) compensação por grupo e imposto
    prej = {"comuns": 0.0, "fii": 0.0, "day_trade": 0.0}
    diferido = 0.0
    saida = []
    for k in sorted(meses):
        m = meses[k]
        base_grupo = {"comuns": m.acoes_resultado_tributavel + m.resultado["bdr"] + m.resultado["etf"],
                      "fii": m.resultado["fii"], "day_trade": m.resultado["day_trade"]}
        m.base_grupo = base_grupo
        imposto = 0.0
        for g, res in base_grupo.items():
            usado = 0.0
            if res > 0:
                usado = min(prej[g], res)
                prej[g] -= usado
                base = res - usado
            else:
                prej[g] += -res
                base = 0.0
            m.prejuizo_usado[g] = usado
            m.base_calculo[g] = base
            m.imposto_grupo[g] = round(base * aliq[g], 2)
            imposto += m.imposto_grupo[g]
        m.imposto_mes = round(imposto, 2)
        m.imposto_diferido_entrada = diferido
        total = round(diferido + m.imposto_mes, 2)
        if total >= minimo:
            m.darf_valor = total
            diferido = 0.0
            if m.imposto_diferido_entrada > 0:
                m.obs.append(f"inclui R$ {m.imposto_diferido_entrada:,.2f} de imposto < R$ 10 diferido de meses anteriores (Lei 9.430 art. 68 §1º)")
        else:
            m.darf_valor = 0.0
            diferido = total
            if total > 0:
                m.obs.append(f"imposto de R$ {total:,.2f} abaixo do mínimo de R$ 10; adiado para o mês seguinte com imposto")
        m.prejuizo_acumulado_fim = dict(prej)
        saida.append(m)
    if diferido > 0 and saida:
        saida[-1].obs.append(f"saldo de R$ {diferido:,.2f} de imposto abaixo de R$ 10 ainda não exigível")
    return saida
