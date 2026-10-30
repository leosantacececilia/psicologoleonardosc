#!/usr/bin/env python3
"""Gera relatorio.md e carteira.xlsx. Uso: python3 scripts/run.py [--hoje AAAA-MM-DD] [--orcamento 200]"""
import argparse, sys, warnings
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
warnings.filterwarnings("ignore")
from carteira.analise import analisar
from carteira.relatorio import gerar_md, gerar_xlsx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hoje", default="2026-10-30", help="data de referência/pagamento (AAAA-MM-DD)")
    ap.add_argument("--orcamento", type=float, default=200.0, help="valor mensal do plano de pagamento")
    ap.add_argument("--raiz", default=str(Path(__file__).resolve().parents[1]))
    a = ap.parse_args()
    raiz = Path(a.raiz)
    r = analisar(raiz, date.fromisoformat(a.hoje), a.orcamento)
    gerar_xlsx(r, raiz / "carteira.xlsx")
    gerar_md(r, raiz / "relatorio.md")
    darfs = r["darfs"]
    print(f"DARFs: {len(darfs)}  principal R$ {sum(d.principal for d in darfs):,.2f}  total com multa/juros R$ {sum(d.total for d in darfs):,.2f}")
    print(f"Prejuízo compensável: {r['prejuizo_atual']}")
    print("Arquivos gerados: relatorio.md, carteira.xlsx")


if __name__ == "__main__":
    main()
