"""DARF em atraso: multa de mora (Lei 9.430/96 art. 61 §§1º-2º) e juros Selic (art. 61 §3º)."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta

from .calendario import vencimento_darf, mes_seguinte


def multa_mora(principal: float, vencimento: date, pagamento: date, taxa_dia: float = 0.0033, limite: float = 0.20) -> tuple[float, float]:
    """Retorna (percentual, valor). Contagem: do dia seguinte ao vencimento até o dia do pagamento (dias corridos)."""
    if pagamento <= vencimento:
        return 0.0, 0.0
    dias = (pagamento - vencimento).days
    pct = min(round(taxa_dia * dias, 4), limite)
    return pct, round(principal * pct, 2)


def juros_mora(principal: float, vencimento: date, pagamento: date, selic: dict[tuple[int, int], float],
               selic_futura: float | None = None) -> tuple[float, float]:
    """Selic acumulada do mês seguinte ao vencimento até o mês anterior ao pagamento + 1% no mês do pagamento.
    Sem juros se pago dentro do mês de vencimento. Juros só sobre o principal."""
    if pagamento <= vencimento or (pagamento.year, pagamento.month) == (vencimento.year, vencimento.month):
        return 0.0, 0.0
    am = mes_seguinte(vencimento.year, vencimento.month)
    pct = 0.0
    while am < (pagamento.year, pagamento.month):
        if am in selic:
            pct += selic[am]
        elif selic_futura is not None:
            pct += selic_futura
        else:
            raise KeyError(f"Selic não disponível para {am}")
        am = mes_seguinte(*am)
    pct += 0.01
    pct = round(pct, 6)
    return pct, round(principal * pct, 2)


@dataclass
class Darf:
    competencia: tuple[int, int]
    vencimento: date
    principal: float
    multa_pct: float = 0.0
    multa: float = 0.0
    juros_pct: float = 0.0
    juros: float = 0.0
    data_pagamento: date | None = None

    @property
    def total(self) -> float:
        return round(self.principal + self.multa + self.juros, 2)


def calcular_darfs(apuracao, selic, pagamento: date, regras: dict, selic_futura: float | None = None) -> list[Darf]:
    out = []
    taxa = float(regras["multa_de_mora"]["taxa_dia"])
    lim = float(regras["multa_de_mora"]["limite"])
    for m in apuracao:
        if m.darf_valor <= 0:
            continue
        venc = vencimento_darf(m.ano, m.mes)
        d = Darf((m.ano, m.mes), venc, m.darf_valor, data_pagamento=pagamento)
        d.multa_pct, d.multa = multa_mora(d.principal, venc, pagamento, taxa, lim)
        d.juros_pct, d.juros = juros_mora(d.principal, venc, pagamento, selic, selic_futura)
        out.append(d)
    return out


def simular_parcelamento(darfs: list[Darf], selic, orcamento_mensal: float, inicio: date, selic_futura: float,
                         regras: dict, max_meses: int = 240) -> dict:
    """Paga ~R$ orçamento por mês, do DARF mais recente ao mais antigo, admitindo pagamento parcial do principal
    (o Sicalc permite emitir DARF para parte do principal; multa e juros incidem proporcionalmente).
    Selic futura = premissa constante. Retorna cronograma e custo adicional versus pagar tudo hoje."""
    taxa = float(regras["multa_de_mora"]["taxa_dia"])
    lim = float(regras["multa_de_mora"]["limite"])
    pend = sorted([[d.competencia, d.vencimento, d.principal] for d in darfs], key=lambda x: x[0], reverse=True)
    cron = []
    mes_pag = inicio
    total_pago = 0.0
    n = 0
    while pend and n < max_meses:
        n += 1
        orc = orcamento_mensal
        while pend and orc > 0.005:
            comp, venc, princ = pend[0]
            mp, _ = multa_mora(1.0, venc, mes_pag, taxa, lim)
            jp, _ = juros_mora(1.0, venc, mes_pag, selic, selic_futura)
            fator = 1 + mp + jp
            pagavel = min(princ, orc / fator)
            pago = round(pagavel * fator, 2)
            cron.append({"mes_pagamento": mes_pag, "competencia": comp, "principal_pago": round(pagavel, 2),
                         "multa": round(pagavel * mp, 2), "juros": round(pagavel * jp, 2), "total_pago": pago,
                         "quitado": princ - pagavel < 0.005})
            total_pago += pago
            orc -= pago
            pend[0][2] = princ - pagavel
            if pend[0][2] < 0.005:
                pend.pop(0)
        # próximo mês: último dia útil do mês seguinte (data de pagamento assumida)
        from .calendario import ultimo_dia_util_do_mes
        a, m = mes_seguinte(mes_pag.year, mes_pag.month)
        mes_pag = ultimo_dia_util_do_mes(a, m)
    return {"cronograma": cron, "meses": n, "total_pago": round(total_pago, 2)}
