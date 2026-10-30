# Apuração de IR em renda variável (pessoa física)

Scripts que leem o extrato de **movimentação** da B3 (Área do Investidor) e os CSVs do Investidor10, calculam
preço médio, apuração mensal (ações, BDR, ETF, FII, day trade), DARFs em atraso (multa e juros), um plano de
pagamento mensal, simulação de venda, XIRR e risco, e geram `relatorio.md` e `carteira.xlsx`.

## Uso

```bash
pip install openpyxl pyyaml pytest
python3 -m pytest -q tests
python3 scripts/run.py --hoje 2026-10-30 --orcamento 200
```

Arquivos esperados em `dados/` (não versionados, por conterem dados pessoais):

- `movimentacao-AAAA-MM-DD-hh-mm-ss.xlsx` — extrato de movimentação da B3 (ajuste o nome em `carteira/analise.py`);
- `posicoes_investidor10_AAAA-MM-DD.csv` e `proventos_investidor10_pagina1_AAAA-MM-DD.csv`;
- `selic_mensal.csv` — série BCB SGS 4390 (competência, selic_pct);
- `precos_mensais.csv` — fechamentos mensais ajustados (opcional; sem ele a aba de risco fica vazia).

## Estrutura

| Arquivo | Função |
|---|---|
| `carteira/calendario.py` | feriados nacionais/B3, D+2, vencimento de DARF (último dia útil do mês seguinte) |
| `carteira/carregar.py` | leitura e normalização dos arquivos; classificação por ticker |
| `carteira/motor.py` | custo médio ponderado e eventos societários (bonificação, desdobro, grupamento, subscrição, incorporação, cisão, frações) |
| `carteira/apuracao.py` | apuração mensal por categoria, isenção de R$ 20 mil, compensação de prejuízos, mínimo de R$ 10 |
| `carteira/darf.py` | multa de mora, juros Selic, plano de pagamento mensal |
| `carteira/simulacao.py` | venda de cada ativo hoje (isolada e conjunta) |
| `carteira/rentabilidade.py` | XIRR, volatilidade, drawdown |
| `carteira/analise.py` | orquestração, reconciliação com o Investidor10, conferência de proventos |
| `carteira/relatorio.py` | geração de `relatorio.md` e `carteira.xlsx` |
| `../regras.yaml` | alíquotas, isenção, compensação, multa, juros, com fonte primária e data de consulta |
| `../fontes/trechos_fontes_primarias.md` | trechos literais das normas consultadas |

Os valores finais de cada DARF devem ser conferidos no Sicalc. Nada aqui é aconselhamento financeiro ou tributário.
