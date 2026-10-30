"""Gera relatorio.md e carteira.xlsx a partir do resultado de analise.analisar()."""
from __future__ import annotations
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

NOME_CLASSE = {"acoes": "Ações", "bdr": "BDR", "etf": "ETF", "fii": "FII/Fiagro", "day_trade": "Day trade", "direito": "Direito", "recibo": "Recibo"}


def brl(v, casas=2):
    if v is None:
        return "-"
    s = f"{abs(v):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("-" if v < 0 else "") + "R$ " + s


def num(v, casas=2):
    if v is None:
        return "-"
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v, casas=1):
    return "-" if v is None else f"{v * 100:.{casas}f}%".replace(".", ",")


def dt(d):
    return "-" if d is None else d.strftime("%d/%m/%Y")


def comp(c):
    return f"{c[1]:02d}/{c[0]}"


# ---------------------------------------------------------------- xlsx
def _aba(wb, nome, cabecalho, linhas, larguras=None, formatos=None):
    ws = wb.create_sheet(nome)
    ws.append(cabecalho)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F4E78")
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for l in linhas:
        ws.append(l)
    for i, h in enumerate(cabecalho, start=1):
        ws.column_dimensions[get_column_letter(i)].width = (larguras[i - 1] if larguras and i - 1 < len(larguras) else max(12, min(60, len(str(h)) + 2)))
    if formatos:
        for col, f in formatos.items():
            for row in ws.iter_rows(min_row=2, min_col=col, max_col=col):
                for c in row:
                    c.number_format = f
    ws.freeze_panes = "A2"
    return ws


def gerar_xlsx(r: dict, caminho: Path):
    wb = Workbook()
    wb.remove(wb.active)
    MOEDA = '#,##0.00;[Red]-#,##0.00'
    PCT = '0.00%'
    res, hoje = r["res"], r["hoje"]

    # Posições
    linhas = []
    for x in r["reconciliacao"]:
        cot = x["cotacao"]
        linhas.append([x["ativo"], x["classe"], x["qtd_calc"], x["qtd_inv10"], x["dif_qtd"], x["pm_calc"], x["pm_inv10"], x["dif_pm"],
                       x["custo_calc"], x["custo_inv10"], cot, (x["qtd_calc"] * cot) if cot else None,
                       (x["qtd_calc"] * cot - x["custo_calc"]) if cot else None])
    _aba(wb, "Posicoes", ["Ativo", "Classe", "Qtd (extrato B3)", "Qtd (Investidor10)", "Dif. qtd", "Preço médio (calculado)", "Preço médio (Investidor10)",
                          "Dif. PM", "Custo total (calculado)", "Custo total (Investidor10)", "Cotação 30/10/2026", "Valor de mercado", "Resultado não realizado"],
         linhas, [10, 10, 14, 14, 10, 16, 16, 10, 16, 16, 14, 16, 18], {3: '0.00', 4: '0.00', 5: '0.00', 6: '0.0000', 7: '0.0000', 8: '0.0000', 9: MOEDA, 10: MOEDA, 11: MOEDA, 12: MOEDA, 13: MOEDA})

    # Apuração mensal
    linhas = []
    for m in r["apuracao"]:
        linhas.append([comp(m.chave), m.vendas.get("acoes", 0.0), m.vendas_acoes_pregao, m.vendas.get("bdr", 0.0), m.vendas.get("etf", 0.0), m.vendas.get("fii", 0.0),
                       m.resultado.get("acoes", 0.0), m.acoes_isento_ganho, m.acoes_resultado_tributavel, m.resultado.get("bdr", 0.0), m.resultado.get("etf", 0.0),
                       m.resultado.get("fii", 0.0), m.resultado.get("day_trade", 0.0),
                       m.base_grupo["comuns"], m.prejuizo_usado["comuns"], m.base_calculo["comuns"], m.imposto_grupo["comuns"],
                       m.base_grupo["fii"], m.prejuizo_usado["fii"], m.base_calculo["fii"], m.imposto_grupo["fii"],
                       m.imposto_grupo["day_trade"], m.imposto_mes, m.imposto_diferido_entrada, m.darf_valor,
                       m.prejuizo_acumulado_fim["comuns"], m.prejuizo_acumulado_fim["fii"], m.prejuizo_acumulado_fim["day_trade"], "; ".join(m.obs)])
    _aba(wb, "Apuracao_Mensal", ["Mês (liquidação)", "Vendas ações", "Vendas ações no mês do pregão (limite 20k)", "Vendas BDR", "Vendas ETF", "Vendas FII",
                                 "Resultado ações", "Ganho ações isento", "Resultado ações levado ao grupo comuns", "Resultado BDR", "Resultado ETF", "Resultado FII", "Resultado day trade",
                                 "Base comuns (ações trib.+BDR+ETF)", "Prejuízo comuns usado", "Base de cálculo comuns", "IR comuns 15%",
                                 "Base FII", "Prejuízo FII usado", "Base de cálculo FII", "IR FII 20%", "IR day trade 20%", "IR do mês", "IR < R$10 diferido (entrada)", "DARF do mês",
                                 "Prejuízo acumulado comuns (fim)", "Prejuízo acumulado FII (fim)", "Prejuízo acumulado day trade (fim)", "Observações"],
         linhas, [12] + [14] * 27 + [80], {i: MOEDA for i in range(2, 29)})

    # DARFs
    linhas = [[comp(d.competencia), "6015", d.vencimento, d.principal, d.multa_pct, d.multa, d.juros_pct, d.juros, d.total, d.data_pagamento] for d in r["darfs"]]
    tot = [sum(d.principal for d in r["darfs"]), sum(d.multa for d in r["darfs"]), sum(d.juros for d in r["darfs"]), sum(d.total for d in r["darfs"])]
    linhas.append(["TOTAL", "", None, tot[0], None, tot[1], None, tot[2], tot[3], None])
    _aba(wb, "DARFs", ["Competência", "Código", "Vencimento", "Principal", "Multa %", "Multa R$", "Juros %", "Juros R$", "Total estimado", "Data de pagamento considerada"],
         linhas, [12, 8, 12, 12, 10, 12, 10, 12, 14, 16], {3: 'dd/mm/yyyy', 4: MOEDA, 5: PCT, 6: MOEDA, 7: PCT, 8: MOEDA, 9: MOEDA, 10: 'dd/mm/yyyy'})

    # Parcelamento
    linhas = [[c["mes_pagamento"], comp(c["competencia"]), c["principal_pago"], c["multa"], c["juros"], c["total_pago"], "sim" if c["quitado"] else "parcial"] for c in r["parcelamento"]["cronograma"]]
    _aba(wb, "Parcelamento_200", ["Data de pagamento", "Competência paga", "Principal pago", "Multa", "Juros", "Total pago", "DARF quitado?"],
         linhas, [16, 14, 14, 12, 12, 14, 14], {1: 'dd/mm/yyyy', 3: MOEDA, 4: MOEDA, 5: MOEDA, 6: MOEDA})

    # Simulação
    linhas = [[s.ticker, NOME_CLASSE.get(s.classe, s.classe), s.qtd, s.preco_medio, s.cotacao, s.valor_venda, s.custo, s.resultado, "sim" if s.isento_sozinho else "não",
               s.imposto_sem_compensacao, s.prejuizo_compensavel_disponivel, s.imposto_com_compensacao, s.liquido_sem_compensacao, s.liquido_com_compensacao, s.obs]
              for s in r["sim_individual"]]
    st = r["sim_total"]
    linhas.append([])
    linhas.append(["TODOS NO MESMO MÊS", "", None, None, None, st["venda_total"], None, sum(st["resultado"].values()), "não" if not st["isento_acoes"] else "sim", None, None, st["imposto"], None, st["liquido"],
                   f"vendas de ações = {num(st['vendas_acoes'])} (> 20 mil => sem isenção); base comuns {num(st['base_comuns'])}; prejuízo restante {num(st['prejuizo_restante'])}"])
    _aba(wb, "Simulacao_Vendas", ["Ativo", "Classe", "Qtd", "Preço médio", "Cotação", "Valor de venda", "Custo", "Resultado", "Isento se vendido sozinho?",
                                  "IR sem compensar prejuízo", "Prejuízo acumulado disponível (grupo)", "IR compensando prejuízo", "Líquido sem compensação", "Líquido com compensação", "Observação"],
         linhas, [20, 10, 8, 12, 10, 14, 14, 12, 12, 14, 16, 14, 16, 16, 90], {3: '0.00', 4: '0.0000', 5: '0.00', 6: MOEDA, 7: MOEDA, 8: MOEDA, 10: MOEDA, 11: MOEDA, 12: MOEDA, 13: MOEDA, 14: MOEDA})

    # Alienações
    linhas = [[a.data_liq, a.data_pregao, a.ticker, NOME_CLASSE.get(a.classe, a.classe), a.tipo, a.qtd, a.valor, a.custo, a.resultado, a.corretora, a.obs] for a in res.alienacoes]
    _aba(wb, "Alienacoes", ["Data liquidação", "Data pregão (est.)", "Ativo", "Classe", "Tipo", "Qtd", "Valor", "Custo (PM)", "Resultado", "Corretora", "Obs"],
         linhas, [14, 14, 10, 10, 16, 10, 12, 12, 12, 30, 40], {1: 'dd/mm/yyyy', 2: 'dd/mm/yyyy', 6: '0.00', 7: MOEDA, 8: MOEDA, 9: MOEDA})

    # Rentabilidade
    linhas = [[x["linha"], NOME_CLASSE.get(x["classe"], x["classe"]), "sim" if x["em_carteira"] else "não", x["primeiro_fluxo"], x["ultimo_fluxo"], x["investido"], x["vendas_e_outros"], x["proventos"],
               x["valor_atual"], x["resultado_total"], x["xirr"]] for x in r["rentabilidade"]]
    c = r["carteira"]
    linhas.append([])
    linhas.append(["CARTEIRA (ações+BDR+ETF)", "", "", None, None, c["investido_escopo"], None, c["proventos_escopo"], c["valor_atual"], None, c["xirr_escopo"]])
    linhas.append(["FII/Fiagro (fora do escopo obrigatório)", "", "", None, None, None, None, c["proventos_total"] - c["proventos_escopo"], 0.0, None, c["xirr_fii"]])
    linhas.append(["TOTAL (incl. FII)", "", "", None, None, None, None, c["proventos_total"], c["valor_atual"], None, c["xirr_total"]])
    _aba(wb, "Rentabilidade", ["Linha de investimento", "Classe", "Em carteira?", "Primeiro fluxo", "Último fluxo", "Total aportado", "Vendas e outros recebimentos", "Proventos líquidos",
                               "Valor atual (30/10/2026)", "Resultado total R$", "XIRR a.a."],
         linhas, [26, 10, 10, 12, 12, 14, 16, 14, 16, 14, 10], {4: 'dd/mm/yyyy', 5: 'dd/mm/yyyy', 6: MOEDA, 7: MOEDA, 8: MOEDA, 9: MOEDA, 10: MOEDA, 11: PCT})

    # Risco
    linhas = [[x["ativo"], x.get("inicio_serie"), x.get("meses"), x.get("vol_anual"), x.get("cagr_serie"), x.get("max_drawdown"), x.get("dd_inicio"), x.get("dd_fim"),
               x.get("desde_compra"), x.get("vol_anual_desde_compra"), x.get("max_drawdown_desde_compra"), x.get("obs", "")] for x in r["risco"]]
    for k, v in r["risco_carteira"].items():
        if v:
            linhas.append([f"CARTEIRA ({k}, pesos atuais)", None, v["janela_meses"], v["vol_anual"], v["retorno_acumulado"], v["max_drawdown"], v["dd_inicio"], v["dd_fim"], None, None, None,
                           "retorno acumulado na janela na coluna CAGR; ativos: " + ", ".join(v["ativos"])])
    _aba(wb, "Risco", ["Ativo", "Início da série", "Meses", "Volatilidade anual (mensal x raiz(12))", "CAGR da série", "Máx. drawdown", "Topo", "Fundo", "1ª compra",
                       "Vol. anual desde a compra", "Máx. drawdown desde a compra", "Obs"],
         linhas, [30, 12, 8, 14, 12, 12, 12, 12, 12, 14, 14, 60], {2: 'dd/mm/yyyy', 4: PCT, 5: PCT, 6: PCT, 7: 'dd/mm/yyyy', 8: 'dd/mm/yyyy', 9: 'dd/mm/yyyy', 10: PCT, 11: PCT})

    # Proventos Investidor10 x B3
    linhas = [[x["ativo"], x["classe"], x["status"], x["tipo"], x["data_com"], x["data_pagamento"], float(x["quantidade"]), float(x["valor_bruto"]), float(x["valor_liquido"]), x["status_conferencia"]]
              for x in r["conferencia_proventos"]]
    _aba(wb, "Proventos_Inv10_x_B3", ["Ativo", "Classe", "Status", "Tipo", "Data com", "Pagamento", "Qtd", "Bruto", "Líquido", "Conferência com o extrato da B3"],
         linhas, [10, 8, 10, 12, 12, 12, 8, 10, 10, 80], {7: '0', 8: MOEDA, 9: MOEDA})

    # Divergências / avisos
    linhas = [["Aviso do processamento", a] for a in res.avisos] + [["Linha repetida no extrato", d] for d in res.duplicatas] + [["Day trade", a] for a in r["avisos_dt"]]
    _aba(wb, "Divergencias_Avisos", ["Tipo", "Descrição"], linhas, [26, 150])

    # Regras resumidas
    rg = r["regras"]
    linhas = [["Alíquota operações comuns", pct(rg["aliquotas"]["operacoes_comuns"]["valor"], 0), rg["aliquotas"]["operacoes_comuns"]["status"], "; ".join(rg["aliquotas"]["operacoes_comuns"]["fonte"])],
              ["Alíquota day trade", pct(rg["aliquotas"]["day_trade"]["valor"], 0), rg["aliquotas"]["day_trade"]["status"], "; ".join(rg["aliquotas"]["day_trade"]["fonte"])],
              ["Alíquota FII", pct(rg["aliquotas"]["fii"]["valor"], 0), rg["aliquotas"]["fii"]["status"], "; ".join(rg["aliquotas"]["fii"]["fonte"])],
              ["Isenção ações", brl(rg["isencao_20k"]["limite_mensal"]), rg["isencao_20k"]["status"], "; ".join(rg["isencao_20k"]["fonte"])],
              ["BDR", rg["bdr"]["regime"], rg["bdr"]["status"], "; ".join(rg["bdr"]["fonte"])],
              ["ETF", rg["etf"]["regime"], rg["etf"]["status"], "; ".join(rg["etf"]["fonte"])],
              ["Compensação", rg["compensacao_prejuizos"]["regra_geral"], rg["compensacao_prejuizos"]["status"], "; ".join(rg["compensacao_prejuizos"]["fonte"])],
              ["Multa de mora", f"{rg['multa_de_mora']['taxa_dia']*100:.2f}% ao dia, limite {pct(rg['multa_de_mora']['limite'],0)}", rg["multa_de_mora"]["status"], "; ".join(rg["multa_de_mora"]["fonte"])],
              ["Juros de mora", rg["juros_de_mora"]["regra"], rg["juros_de_mora"]["status"], "; ".join(rg["juros_de_mora"]["fonte"])],
              ["DARF", f"código {rg['darf']['codigo']}; {rg['darf']['vencimento']}; mínimo {brl(rg['darf']['minimo'])}", rg["darf"]["status"], "; ".join(rg["darf"]["fonte"])],
              ["Datas", rg["datas"]["ciclo_liquidacao"] + " " + rg["datas"]["uso"], rg["datas"]["status"], ""],
              ["Custo de aquisição", rg["custo_de_aquisicao"]["metodo"] + "; bonificação: " + rg["custo_de_aquisicao"]["bonificacao"], rg["custo_de_aquisicao"]["status"], "; ".join(rg["custo_de_aquisicao"]["fonte"])]]
    _aba(wb, "Regras", ["Regra", "Valor / descrição", "Status", "Fonte primária (consultada em 2026-10-30)"], linhas, [24, 80, 14, 120])
    wb.save(caminho)


# ---------------------------------------------------------------- markdown
def gerar_md(r: dict, caminho: Path):
    res, hoje, ap, darfs = r["res"], r["hoje"], r["apuracao"], r["darfs"]
    principal = sum(d.principal for d in darfs)
    total = sum(d.total for d in darfs)
    multa = sum(d.multa for d in darfs)
    juros = sum(d.juros for d in darfs)
    prej = r["prejuizo_atual"]
    par = r["parcelamento"]
    c = r["carteira"]
    st = r["sim_total"]
    anos = sorted({m.ano for m in ap})
    L = []
    w = L.append
    w(f"# Apuração de IR em renda variável — pessoa física (posição em {dt(hoje)})\n")
    w(f"**Conclusão:** imposto devido estimado de **{brl(principal)}** (principal) em {len(darfs)} DARFs de {comp(darfs[0].competencia)} a {comp(darfs[-1].competencia)}, todas geradas por BDRs e ETFs; "
      f"com multa e juros até {dt(hoje)} o total sobe para **{brl(total)}** (valor final no Sicalc). "
      f"Vendas de ações ficaram sempre abaixo de R$ 20 mil/mês (ganhos isentos) e os FIIs só geraram prejuízo; "
      f"há {brl(prej['comuns'])} de prejuízo compensável (ações/BDR/ETF) e {brl(prej['fii'])} (só FII) para abater ganhos futuros.\n")
    w("> Este documento traz cálculos e cenários a partir dos seus arquivos; não é aconselhamento financeiro nem tributário. "
      "Regras e fontes estão em `regras.yaml` e `fontes/trechos_fontes_primarias.md`; tudo foi gerado por `scripts/run.py` (testes em `tests/`).\n")

    # 1 dados
    w("## 1. Dados usados e reconciliação\n")
    w(f"- Extrato de **movimentação** da B3 (não é o extrato de negociação): {len(r['eventos'])} linhas, de 14/04/2021 a 29/10/2026, 11 corretoras. "
      "Traz data de **liquidação**, quantidade, preço e valor; não traz corretagem/emolumentos.")
    w(f"- Investidor10: posições ({len(r['inv10'])} ativos, cotação de {dt(hoje)}) e página 1 de proventos ({len(r['conferencia_proventos'])} linhas).")
    w("- Tesouro Direto e CDB foram ignorados (fora do escopo). FIIs/Fiagro estavam no extrato e foram apurados em categoria própria (não estavam no escopo obrigatório, mas afetam a obrigação de declarar e o prejuízo compensável).")
    w("- Posição calculada pelo extrato × Investidor10 (quantidade e preço médio):\n")
    w("| Ativo | Qtd extrato | Qtd Inv10 | PM extrato | PM Inv10 | Situação |")
    w("|---|---:|---:|---:|---:|---|")
    for x in r["reconciliacao"]:
        if x["pm_inv10"] is None:
            sit = "só no extrato"
        elif abs(x["dif_qtd"]) > 1e-6:
            sit = f"**diverge** ({x['dif_qtd']:+.0f} ações)"
        elif abs(x["dif_pm"]) > 0.01:
            sit = f"**PM diverge** ({'+' if x['dif_pm'] > 0 else '-'}{num(abs(x['dif_pm']))})"
        else:
            sit = "confere"
        w(f"| {x['ativo']} | {num(x['qtd_calc'],0)} | {num(x['qtd_inv10'],0) if x['pm_inv10'] is not None else '-'} | {num(x['pm_calc'],4)} | {num(x['pm_inv10'],2) if x['pm_inv10'] is not None else '-'} | {sit} |")
    w("")
    w("- Conferência do seu número de referência: **jan/2026 = base R$ 1.052,03 e IR R$ 157,80** — reproduzido exatamente (venda de 10 RIOT34 em 09/01/2026, custo médio R$ 350,41).")
    w(f"- Os ativos que você citou sem histórico (KLBN4, M1TA34, UPAC34, PFIZ34) **têm histórico completo no extrato** (M1TA34 vem de FBOK34 por troca de ticker em 22/06/2022). Todas as {len(res.compras)} compras e {sum(1 for a in res.alienacoes if a.tipo == 'venda')} vendas (mais {sum(1 for a in res.alienacoes if a.tipo != 'venda')} frações/resgates) fecham sem posição negativa.\n")

    # 2 divergências
    w("## 2. Divergências e dados faltantes\n")
    w("- **ITSA4: 486 ações pelo extrato × 505 no Investidor10** (diferença de 19 = exatamente a última compra, de 19 ações liquidada em 28/10/2026). Hipóteses: compra adicional ainda não liquidada quando o extrato foi gerado, ou dupla contagem no Investidor10. O PM também difere (12,43 × 12,93); com 505 ações a R$ 12,93 o custo seria R$ 489 maior do que o extrato sustenta. Não altera o imposto devido; altera o resultado simulado de ITSA4 (ganho de R$ 24 × prejuízo de R$ 227).")
    w("- **CMIG4: PM 11,20 (extrato) × 11,38 (Investidor10)**. A diferença (R$ 88) equivale a atribuir custo às 17,4 ações da bonificação de 2024 (≈ R$ 5,09/ação, valor que a Cemig declarou e que não consta no extrato). Aqui as bonificações entraram com custo zero (conservador: imposto maior ou igual). Mesmo caso, em menor escala, para ITSA4, KLBN4, GOAU4, UNIP3, SLCE3, TASA3 e BBDC4.")
    dup = [x for x in r["conferencia_proventos"] if "duplic" in x["status_conferencia"].lower()]
    nao = [x for x in r["conferencia_proventos"] if "NÃO encontrado" in x["status_conferencia"]]
    w(f"- **Proventos do Investidor10 (página 1)**: {len(dup)} linhas 'A receber' repetem proventos que o extrato da B3 (ou a própria lista) já mostra como pagos — "
      + "; ".join(f"{x['ativo']} data-com {dt(date.fromisoformat(x['data_com']))} {brl(float(x['valor_liquido']))}" for x in dup)
      + f" (total {brl(sum(float(x['valor_liquido']) for x in dup))}). Inclui o JSCP de CMIG4 de 23/12/2025 que você notou. "
      + (f"{len(nao)} linhas 'Pago' não foram localizadas com valor idêntico no extrato: " + "; ".join(f"{x['ativo']} {brl(float(x['valor_liquido']))} em {dt(date.fromisoformat(x['data_pagamento']))}" for x in nao) + ". " if nao else "")
      + "Detalhe na aba `Proventos_Inv10_x_B3`.")
    w("- **Linhas repetidas no extrato da B3**: JSCP ITSA4 de 01/04/2025 (R$ 2,02, 2×) e dividendo ISAE3 de 29/04/2026 (R$ 17,66, 3×). Podem ser pagamentos distintos de mesmo valor; afetam só proventos/XIRR (≤ R$ 37), não o imposto.")
    w("- **Cessão de direitos KNCA12 (06/2023)**: 5 direitos de subscrição foram cedidos e o valor recebido não consta. Se houve venda em bolsa, há ganho (pequeno) tributável a 20% não apurado aqui.")
    w("- **Cisão 3M → X2ZZ34 (04/2024)**: 0,5 fração resgatada por R$ 156,56 com custo zero (a proporção de custo fixada em assembleia não consta). Se parte do custo de MMMC34 for atribuída, o IR de abr/2024 (R$ 23,48) cai e o de ago/2024 sobe quase na mesma medida.")
    w("- **Incorporações de FIIs** (MGFF11→VGHF11; BPFF11+HGFF11→PSEC11; RBRF11→RBRX11): custo transferido integralmente às cotas novas; o dinheiro recebido nas frações (R$ 139,24) abateu o custo. Tratamento A CONFIRMAR, só afeta o prejuízo de FII (não há imposto).")
    w("- **Restituição de capital VIVT3** de R$ 27,13 recebida em 07/2025, após a venda: tratada como rendimento não tributado (A CONFIRMAR; efeito máximo R$ 4).")
    w("- **Corretagem/emolumentos** não constam: ganhos ficaram ligeiramente maiores do que o real (conservador). **IRRF de 0,005%** ('dedo-duro') não foi deduzido pelo mesmo motivo (máximo ~R$ 2,50 no total).")
    w("- **Páginas 2 e 3 dos proventos do Investidor10** não foram usadas; os proventos vieram integralmente do extrato da B3 (valores líquidos, que batem com o Investidor10 nos ativos atuais com diferença ≤ R$ 0,20).\n")

    # 3 premissas
    w("## 3. Premissas de cálculo\n")
    w("- Custo médio ponderado por ativo, consolidado entre corretoras (IN RFB 1585/2015, art. 58). Desdobro e grupamento mantêm o custo total; bonificação com custo zero; frações vendidas em leilão tratadas como venda.")
    w("- O extrato traz a data de liquidação. A data do pregão foi estimada em D-2 úteis (ciclo D+2 da B3, confirmado por datas-com do Investidor10). Mês de apuração/DARF = mês da liquidação; limite de R$ 20 mil = mês do pregão (P&R IRPF 2026, pergunta 745). Só a venda de HASH11 (pregão 28/02/2024, liquidação 01/03/2024) muda de mês com isso; o imposto é o mesmo, o vencimento muda de 28/03 para 30/04/2024.")
    w("- Categorias: ações (isenção se vendas ≤ R$ 20 mil no mês; perdas de meses isentos são compensáveis quando declaradas), BDR e ETF (15%, sem isenção; HASH11 tratado como ETF), FII/Fiagro (20%, prejuízo só compensa FII), day trade (20%; nenhum detectado). Prejuízos de ações, BDR e ETF formam um único saldo ('operações comuns', IN 1585 art. 64).")
    w("- Imposto mensal abaixo de R$ 10 é somado ao mês seguinte com imposto (Lei 9.430/96, art. 68 §1º): o único caso é jul/2022 (R$ 4,57), pago junto com mar/2024.")
    w("- Multa de mora 0,33%/dia limitada a 20% e juros = Selic acumulada (BCB SGS 4390) do mês seguinte ao vencimento até o mês anterior ao pagamento + 1% no mês do pagamento (Lei 9.430/96, art. 61). Pagamento considerado em " + dt(hoje) + ".")
    w(f"- MP 1.303/2025 (alíquota única de 17,5%) perdeu a validade em 2025 segundo a imprensa; a P&R IRPF 2026 da Receita mantém 15%/20% e a isenção mensal de R$ 20 mil. Marcado como A CONFIRMAR em `regras.yaml`.\n")

    # 4 preço médio
    w("## 4. Preço médio e posição atual (pelo extrato)\n")
    w("| Ativo | Classe | Qtd | PM calculado | Custo total | Cotação | Valor de mercado | Resultado não realizado |")
    w("|---|---|---:|---:|---:|---:|---:|---:|")
    for x in r["reconciliacao"]:
        if x["cotacao"] is None:
            continue
        vm = x["qtd_calc"] * x["cotacao"]
        w(f"| {x['ativo']} | {x['classe']} | {num(x['qtd_calc'],0)} | {num(x['pm_calc'],4)} | {brl(x['custo_calc'])} | {num(x['cotacao'])} | {brl(vm)} | {brl(vm - x['custo_calc'])} |")
    w("")
    # 5 apuração
    w("## 5. Apuração mês a mês (resumo)\n")
    w("Meses com imposto (todos os meses, inclusive isentos e com prejuízo, estão na aba `Apuracao_Mensal`):\n")
    w("| Mês | Operações | Resultado do mês (comuns) | Prejuízo usado | Base | IR 15% | DARF |")
    w("|---|---|---:|---:|---:|---:|---:|")
    por_mes = {}
    for a in res.alienacoes:
        por_mes.setdefault((a.data_liq.year, a.data_liq.month), []).append(a)
    for m in ap:
        if m.darf_valor <= 0 and m.imposto_mes <= 0:
            continue
        ops = ", ".join(sorted({a.ticker for a in por_mes.get(m.chave, []) if a.classe in ("bdr", "etf") or (a.classe == "acoes" and a.resultado < 0)}))
        w(f"| {comp(m.chave)} | {ops} | {brl(m.base_grupo['comuns'])} | {brl(m.prejuizo_usado['comuns'])} | {brl(m.base_calculo['comuns'])} | {brl(m.imposto_mes)} | {brl(m.darf_valor)} |")
    w("")
    w("Por ano (ganhos isentos de ações devem ir em 'Rendimentos isentos' da DIRPF; prejuízos, no demonstrativo de renda variável):\n")
    w("| Ano | Vendas de ações | Ganho isento (ações) | Resultado BDR | Resultado ETF | Resultado FII | IR devido (principal) | Prejuízo comuns (fim do ano) | Prejuízo FII (fim do ano) |")
    w("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for ano in anos:
        ms = [m for m in ap if m.ano == ano]
        w(f"| {ano} | {brl(sum(m.vendas.get('acoes',0) for m in ms))} | {brl(sum(m.acoes_isento_ganho for m in ms))} | {brl(sum(m.resultado.get('bdr',0) for m in ms))} | "
          f"{brl(sum(m.resultado.get('etf',0) for m in ms))} | {brl(sum(m.resultado.get('fii',0) for m in ms))} | {brl(sum(m.darf_valor for m in ms))} | {brl(ms[-1].prejuizo_acumulado_fim['comuns'])} | {brl(ms[-1].prejuizo_acumulado_fim['fii'])} |")
    w("")
    w(f"- Maior mês de vendas de ações: {brl(max(m.vendas_acoes_pregao for m in ap))} (fev/2026), bem abaixo do limite; nenhum ganho de ação foi tributável.")
    w(f"- Os prejuízos de ações em meses isentos (TASA3, CSAN3, SAPR3, ISAE3 em 2026, entre outros) só valem para compensação se forem informados no Demonstrativo de Renda Variável da DIRPF (IN 1585, art. 59 §1º). Se as declarações anteriores não trouxeram essas operações, o uso futuro do saldo de {brl(prej['comuns'])} depende de retificá-las (declaração 2025, 2026 e seguintes).")
    w(f"- Day trade: nenhuma operação de compra e venda no mesmo pregão/corretora foi encontrada.\n")

    # 6 DARFs
    w(f"## 6. DARFs em atraso (código 6015) — estimativa para pagamento em {dt(hoje)}\n")
    w("| Competência | Vencimento | Principal | Multa (20%) | Juros Selic | Total |")
    w("|---|---|---:|---:|---:|---:|")
    for d in darfs:
        w(f"| {comp(d.competencia)} | {dt(d.vencimento)} | {brl(d.principal)} | {brl(d.multa)} | {brl(d.juros)} ({pct(d.juros_pct)}) | {brl(d.total)} |")
    w(f"| **Total** | | **{brl(principal)}** | **{brl(multa)}** | **{brl(juros)}** | **{brl(total)}** |")
    w("")
    w("- Todas as DARFs passaram de 60 dias de atraso, então a multa já está no teto de 20% em todas; só os juros continuam crescendo (≈ Selic mensal, hoje ~1% ao mês sobre o principal de " + brl(principal) + ", isto é, ~R$ 13 por mês de espera).")
    w("- Emita cada DARF no Sicalc (código 6015, período de apuração = mês da competência) para obter o valor exato; os juros usam a Selic oficial da Receita, que pode diferir em centavos da série do BCB.\n")

    # 7 parcelamento
    extra = par["total_pago"] - total
    w(f"## 7. Pagando ~{brl(r['orcamento_mensal'])} por mês, do mais recente ao mais antigo\n")
    w(f"- Prazo: **{par['meses']} meses** (de {dt(par['cronograma'][0]['mes_pagamento'])} a {dt(par['cronograma'][-1]['mes_pagamento'])}), total pago **{brl(par['total_pago'])}**, ou seja, **{brl(extra)} a mais** do que quitar tudo em {dt(hoje)} ({brl(total)}).")
    w(f"- Premissas: pagamento no último dia útil de cada mês; DARF pago parcialmente quando o orçamento não cobre o total (o Sicalc permite emitir DARF por parte do principal); Selic futura constante em {pct(r['selic_futura'],2)} ao mês (último mês fechado). Cronograma completo na aba `Parcelamento_200`.")
    w("- Trade-off: pagar primeiro os mais antigos custaria praticamente o mesmo, porque a multa está no teto em todas e os juros mensais são iguais (Selic) sobre qualquer principal; a ordem só muda qual DARF fica em aberto. O parcelamento oficial da Receita (e-CAC) não foi simulado.\n")

    # 8 simulação
    w(f"## 8. Simulação de venda hoje (cotações de {dt(hoje)})\n")
    w("Cada ativo vendido sozinho, em um mês sem outras vendas:\n")
    w("| Ativo | Classe | Valor de venda | Custo (PM) | Resultado | Tratamento | IR sem compensar | IR compensando prejuízo | Líquido |")
    w("|---|---|---:|---:|---:|---|---:|---:|---:|")
    for s in r["sim_individual"]:
        if s.resultado <= 0:
            trat = "prejuízo (vira saldo compensável)"
        elif s.isento_sozinho:
            trat = "ganho isento (ações ≤ 20 mil)"
        else:
            trat = f"tributável {pct(s.aliquota,0)}"
        w(f"| {s.ticker} | {NOME_CLASSE.get(s.classe, s.classe)} | {brl(s.valor_venda)} | {brl(s.custo)} | {brl(s.resultado)} | {trat} | {brl(s.imposto_sem_compensacao)} | {brl(s.imposto_com_compensacao)} | {brl(s.liquido_com_compensacao)} |")
    w("")
    w(f"- Vendendo **tudo no mesmo mês**: vendas de ações de {brl(st['vendas_acoes'])} (> R$ 20 mil, perde a isenção); resultado ações {brl(st['resultado']['acoes'])}, BDR {brl(st['resultado']['bdr'])}, ETF {brl(st['resultado']['etf'])}; base {brl(st['base_comuns'])} → **IR {brl(st['imposto'])}**, líquido {brl(st['liquido'])}, prejuízo acumulado restante {brl(st['prejuizo_restante'])}.")
    w(f"- Trade-offs visíveis nos números: (a) só BERK34 e IVVB11 têm ganho tributável, e o saldo compensável de {brl(prej['comuns'])} zera esse imposto se as perdas tiverem sido declaradas; (b) BBSE3 tem o maior ganho ({brl(1020.95)}) e fica isento se vendido em mês com vendas de ações ≤ R$ 20 mil, sem consumir o saldo; (c) vender tudo junto faz o ganho de BBSE3 ser absorvido pelas perdas de CMIG4/ISAE4/TAEE3 em vez de ficar isento; (d) pelo PM do Investidor10, ITSA4 teria prejuízo de R$ 227 em vez de ganho de R$ 24.\n")

    # 9 rentabilidade
    w("## 9. Rentabilidade e risco\n")
    w(f"- **Carteira (ações + BDR + ETF), XIRR com proventos: {pct(c['xirr_escopo'])} a.a.** (todos os fluxos de 2021 a 2026, proventos líquidos de {brl(c['proventos_escopo'])}, valor atual {brl(c['valor_atual'])}). Incluindo os FIIs (XIRR {pct(c['xirr_fii'])}): {pct(c['xirr_total'])} a.a.")
    w("- Por ativo em carteira (XIRR a.a. e resultado total incluindo proventos). Atenção: para posições com menos de um ano (AURO11, BERK34, ISAE4, IVVB11) o XIRR anualiza poucos meses e exagera o número; olhe o resultado em R$.\n")
    w("| Ativo | Desde | Aportado | Proventos | Valor atual | Resultado total | XIRR a.a. | Vol. anual (6 anos) | Máx. drawdown (6 anos) | Vol. desde a compra |")
    w("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    risco = {x["ativo"]: x for x in r["risco"]}
    for x in r["rentabilidade"]:
        if not x["em_carteira"]:
            continue
        rk = risco.get(x["linha"], {})
        w(f"| {x['linha']} | {dt(x['primeiro_fluxo'])} | {brl(x['investido'])} | {brl(x['proventos'])} | {brl(x['valor_atual'])} | {brl(x['resultado_total'])} | {pct(x['xirr'])} | {pct(rk.get('vol_anual'))} | {pct(rk.get('max_drawdown'))} | {pct(rk.get('vol_anual_desde_compra'))} |")
    w("")
    rc = r["risco_carteira"]
    if rc.get("12m_todos"):
        v = rc["12m_todos"]
        w(f"- Risco da carteira atual (pesos de hoje, séries mensais ajustadas): últimos 12 meses → volatilidade {pct(v['vol_anual'])} a.a., máximo drawdown {pct(v['max_drawdown'])}, retorno {pct(v['retorno_acumulado'])}.")
    if rc.get("36m_sem_AURO11"):
        v = rc["36m_sem_AURO11"]
        w(f"- Em 36 meses (sem AURO11, que só existe desde out/2025): volatilidade {pct(v['vol_anual'])} a.a., máximo drawdown {pct(v['max_drawdown'])}, retorno acumulado {pct(v['retorno_acumulado'])}. É um proxy com pesos fixos, não a sua trajetória real.")
    w("- Ativos já vendidos: os maiores resultados foram HASH11 (+R$ 1.546), VALE3 (+R$ 1.519), RIOT34 (+R$ 1.454), JPMC34 (+R$ 1.338) e MOOO34 (+R$ 1.313); as maiores perdas, CSAN3 (−R$ 996), C1NS34 (−R$ 882) e TASA3 (−R$ 516). Lista completa na aba `Rentabilidade`.")
    w("- Séries de preços: fechamentos mensais ajustados do Yahoo Finance (6 anos; AURO11 desde out/2025), lidos por ferramenta de leitura de página — servem para ordem de grandeza. Volatilidade = desvio-padrão dos retornos mensais × √12. Para volatilidade diária e drawdown intramensal faltam séries diárias (não disponíveis sem chave de API neste ambiente).\n")

    # 10 confiança
    w("## 10. Nível de confiança\n")
    w("- **Alto** (≥ 95%): imposto principal de BDR/ETF por mês, a isenção das ações, o saldo de prejuízo de FII, preço médio de 9 dos 10 ativos atuais (bate com o Investidor10 ao centavo).")
    w("- **Médio**: multa e juros (dependem da data de pagamento e da Selic oficial; conferir no Sicalc), mês de competência de HASH11 (fev ou mar/2024), tratamento das bonificações (custo zero) e da cisão X2ZZ34, parcelamento (Selic futura).")
    w("- **Baixo**: quantidade/PM de ITSA4 (486 × 505), valor da cessão de direitos KNCA12, duplicidades de proventos (só afetam XIRR), métricas de risco (série mensal relida).\n")
    w("## 11. Como reproduzir\n")
    w("```bash\npython3 -m pytest -q tests\npython3 scripts/run.py --hoje 2026-10-30 --orcamento 200\n```\n")
    caminho.write_text("\n".join(L), encoding="utf-8")
