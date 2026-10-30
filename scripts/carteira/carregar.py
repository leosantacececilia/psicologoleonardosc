"""Leitura e normalização do extrato de movimentação da B3 e dos arquivos auxiliares."""
from __future__ import annotations
import csv
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import openpyxl
import yaml

ETFS = {"HASH11", "IVVB11", "AURO11"}
FIIS = {"BPFF11", "HGFF11", "MGFF11", "RBRF11", "RBRX11", "VGHF11", "KNCA11", "PSEC11", "RVBI11", "RVBI15", "BCFF11"}
UNITS_ACOES = {"TAEE11"}
DIREITOS = {"ITSA2", "KNCA12"}
RECIBOS = {"ITSA10"}

RE_TICKER = re.compile(r"^([A-Z0-9]{4}\d{1,2})\s+-\s+(.*)$")


def classificar(ticker: str, produto: str) -> str:
    if not ticker:
        if produto.startswith("Tesouro"):
            return "tesouro"
        if produto.startswith("CDB"):
            return "cdb"
        return "outro"
    if ticker in ETFS:
        return "etf"
    if ticker in FIIS:
        return "fii"
    if ticker in DIREITOS:
        return "direito"
    if ticker in RECIBOS:
        return "recibo"
    if ticker in UNITS_ACOES:
        return "acoes"
    if re.search(r"3[2-9]$", ticker):  # BDRs terminam em 32..39 (34 patrocinados/não patrocinados)
        return "bdr"
    return "acoes"


@dataclass
class Evento:
    data: date
    sentido: str        # Credito / Debito
    mov: str
    produto: str
    ticker: str
    inst: str
    qtd: float | None
    preco: float | None
    valor: float | None
    classe: str = ""
    linha: int = 0


def _num(x):
    return float(x) if isinstance(x, (int, float)) else None


def carregar_extrato(caminho: str | Path) -> list[Evento]:
    wb = openpyxl.load_workbook(str(caminho), data_only=True)
    ws = wb.worksheets[0]
    linhas = list(ws.iter_rows(values_only=True))
    cab = [str(c).strip() for c in linhas[0]]
    esperado = ["Entrada/Saída", "Data", "Movimentação", "Produto", "Instituição", "Quantidade", "Preço unitário", "Valor da Operação"]
    if cab != esperado:
        raise ValueError(f"Cabeçalho inesperado no extrato: {cab}")
    out: list[Evento] = []
    for i, r in enumerate(linhas[1:], start=2):
        if r[1] is None:
            continue
        d = datetime.strptime(str(r[1]), "%d/%m/%Y").date()
        produto = str(r[3]).strip()
        m = RE_TICKER.match(produto)
        ticker = m.group(1) if m else ""
        ev = Evento(d, str(r[0]).strip(), str(r[2]).strip(), produto, ticker, str(r[4]).strip(),
                    _num(r[5]), _num(r[6]), _num(r[7]), classificar(ticker, produto), i)
        out.append(ev)
    # ordem cronológica estável (mantém a ordem do arquivo dentro do mesmo dia, invertida pois o extrato vem do mais novo ao mais antigo)
    out.sort(key=lambda e: (e.data, -e.linha))
    return out


@dataclass
class PosicaoInformada:
    ativo: str
    classe: str
    quantidade: float
    preco_medio: float
    cotacao: float
    proventos_total: float | None


def carregar_posicoes_investidor10(caminho) -> list[PosicaoInformada]:
    out = []
    with open(caminho, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append(PosicaoInformada(r["ativo"], r["classe"], float(r["quantidade"]), float(r["preco_medio"]),
                                        float(r["cotacao_atual"]), float(r["proventos_recebidos_total"]) if r["proventos_recebidos_total"] else None))
    return out


def carregar_proventos_investidor10(caminho) -> list[dict]:
    with open(caminho, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def carregar_selic(caminho) -> dict[tuple[int, int], float]:
    out = {}
    with open(caminho, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            a, m = r["competencia"].split("-")
            out[(int(a), int(m))] = float(r["selic_pct"]) / 100.0
    return out


def carregar_regras(caminho) -> dict:
    with open(caminho, encoding="utf-8") as f:
        return yaml.safe_load(f)


def carregar_precos(caminho) -> dict[str, list[tuple[date, float]]]:
    out: dict[str, list[tuple[date, float]]] = {}
    p = Path(caminho)
    if not p.exists():
        return out
    with open(p, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.setdefault(r["ticker"], []).append((date.fromisoformat(r["data"]), float(r["fechamento_ajustado"])))
    for t in out:
        out[t].sort()
    return out
