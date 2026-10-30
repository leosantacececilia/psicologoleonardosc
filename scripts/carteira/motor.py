"""Motor de posições: custo médio ponderado por ativo, eventos societários e registro de alienações.

Regras de custo: IN RFB 1585/2015, art. 58 (média ponderada; bonificação; desdobramento custo zero;
incorporação/cisão com transferência de custo; restituição de capital reduz custo). Ver regras.yaml.
"""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from .calendario import data_pregao_estimada
from .carregar import Evento

# Eventos de conversão identificados no extrato (ticker antigo -> novo). A quantidade nova é a que
# aparece nas linhas "Atualização"/"Recibo" do ticker novo; o custo total é transferido integralmente.
CONVERSOES: list[tuple[date, tuple[str, ...], str, str]] = [
    (date(2022, 6, 22), ("FBOK34",), "M1TA34", "Troca de ticker FBOK34 -> M1TA34 (Facebook -> Meta)"),
    (date(2024, 2, 1), ("MGFF11",), "VGHF11", "Incorporação do MGFF11 pelo VGHF11 (50 -> 369,66 cotas)"),
    (date(2024, 11, 19), ("TRPL3",), "ISAE3", "Troca de ticker TRPL3 -> ISAE3 (CTEEP -> ISA Energia)"),
    (date(2025, 5, 28), ("ITSA10",), "ITSA4", "Conversão dos recibos de subscrição ITSA10 em ITSA4"),
    (date(2025, 10, 6), ("BPFF11", "HGFF11"), "RVBI15", "Incorporação de BPFF11 e HGFF11 pelo VBI Reits (recibos RVBI15)"),
    (date(2025, 10, 17), ("RVBI15",), "RVBI11", "Conversão dos recibos RVBI15 em cotas RVBI11"),
    (date(2025, 10, 27), ("RVBI11",), "PSEC11", "Troca de ticker RVBI11 -> PSEC11"),
    (date(2025, 11, 26), ("RBRF11",), "RBRX11", "Incorporação do RBRF11 pelo RBRX11 (1.337 -> 1.142,30 cotas)"),
]
# Para fluxo de caixa/XIRR, cada "linha de investimento" é identificada pelo ticker final.
LINHA_XIRR = {"FBOK34": "M1TA34", "TRPL3": "ISAE3", "ITSA2": "ITSA4", "ITSA10": "ITSA4", "MGFF11": "VGHF11",
              "BPFF11": "PSEC11", "HGFF11": "PSEC11", "RVBI15": "PSEC11", "RVBI11": "PSEC11", "RBRF11": "RBRX11",
              "X2ZZ34": "MMMC34", "KNCA12": "KNCA11"}
# Recibos de subscrição: ticker do direito -> ticker do recibo
RECIBO_DE = {"ITSA2": "ITSA10"}

MOV_PROVENTO = {"Dividendo", "Juros Sobre Capital Próprio", "Rendimento", "Juros"}
MOV_IGNORAR = {"Transferência", "Transferencia", "Dividendo - Transferido", "Juros Sobre Capital Próprio - Transferido",
               "Solicitação de Subscrição", "Cessão de Direitos",
               "Direito Sobras de Subscrição", "Direito Sobras de Subscrição - Não Exercido",
               "Compra", "Venda", "COMPRA / VENDA", "VENCIMENTO", "Cobrança de Taxa Semestral"}


@dataclass
class Posicao:
    ticker: str
    classe: str
    qtd: float = 0.0
    custo: float = 0.0
    fracao_qtd: float = 0.0     # fração retirada da custódia aguardando leilão
    fracao_custo: float = 0.0

    @property
    def preco_medio(self) -> float:
        return self.custo / self.qtd if self.qtd > 1e-9 else 0.0


@dataclass
class Alienacao:
    data_liq: date
    data_pregao: date
    ticker: str
    classe: str
    qtd: float
    valor: float
    custo: float
    corretora: str
    tipo: str = "venda"     # venda | leilao_fracao | resgate_cisao | direito_nao_exercido
    obs: str = ""

    @property
    def resultado(self) -> float:
        return self.valor - self.custo


@dataclass
class Fluxo:
    data: date
    ticker: str          # linha de investimento
    classe: str
    tipo: str            # compra | venda | provento | subscricao | fracao | resgate | restituicao
    valor: float         # negativo = saída de caixa do investidor


@dataclass
class Compra:
    data_liq: date
    data_pregao: date
    ticker: str
    qtd: float
    valor: float
    corretora: str


@dataclass
class Resultado:
    posicoes: dict[str, Posicao]
    alienacoes: list[Alienacao]
    compras: list[Compra]
    fluxos: list[Fluxo]
    proventos: list[Fluxo]
    avisos: list[str]
    duplicatas: list[str]


class Motor:
    def __init__(self, ciclo_liquidacao: int = 2):
        self.ciclo = ciclo_liquidacao
        self.pos: dict[str, Posicao] = {}
        self.alienacoes: list[Alienacao] = []
        self.compras: list[Compra] = []
        self.fluxos: list[Fluxo] = []
        self.proventos: list[Fluxo] = []
        self.avisos: list[str] = []
        self.duplicatas: list[str] = []
        self._sub_pendente: dict[str, float] = {}
        self._conv_feitas: set[tuple[date, str]] = set()
        self._convertidos: dict[str, str] = {}   # ticker antigo -> novo

    # ---------- utilidades ----------
    def p(self, ev_or_ticker, classe: str = "") -> Posicao:
        if isinstance(ev_or_ticker, Evento):
            t, c = ev_or_ticker.ticker, ev_or_ticker.classe
        else:
            t, c = ev_or_ticker, classe
        if t not in self.pos:
            self.pos[t] = Posicao(t, c)
        return self.pos[t]

    def _linha(self, ticker: str) -> str:
        return LINHA_XIRR.get(ticker, ticker)

    def aviso(self, msg: str):
        self.avisos.append(msg)

    # ---------- processamento ----------
    def processar(self, eventos: list[Evento]) -> Resultado:
        eventos = [e for e in eventos if e.classe not in ("tesouro", "cdb", "outro")]
        self._detectar_duplicatas(eventos)
        # agrupa "Atualização" por (data, ticker)
        atualiz: dict[tuple[date, str], float] = defaultdict(float)
        for e in eventos:
            if e.mov == "Atualização" and e.sentido == "Credito":
                atualiz[(e.data, e.ticker)] += e.qtd or 0.0
        atualiz_vistas: set[tuple[date, str]] = set()
        for e in eventos:
            m = e.mov
            if m in MOV_IGNORAR:
                continue
            if m in MOV_PROVENTO:
                self._provento(e)
            elif m == "Transferência - Liquidação":
                self._liquidacao(e)
            elif m == "Bonificação em Ativos":
                self.p(e).qtd += e.qtd
                self.aviso(f"{e.data} {e.ticker}: bonificação de {e.qtd:g} ações com custo ZERO (valor capitalizado por ação não consta no extrato; A CONFIRMAR)")
            elif m == "Desdobro":
                self.p(e).qtd += e.qtd
            elif m == "Grupamento":
                pos = self.p(e)
                self.aviso(f"{e.data} {e.ticker}: grupamento, posição {pos.qtd:g} -> {e.qtd:g} (custo total mantido)")
                pos.qtd = e.qtd
            elif m == "Fração em Ativos":
                self._fracao_retirada(e)
            elif m == "Leilão de Fração":
                self._leilao_fracao(e)
            elif m == "Atualização":
                chave = (e.data, e.ticker)
                if chave in atualiz_vistas:
                    continue
                atualiz_vistas.add(chave)
                self._atualizacao(e, atualiz[chave])
            elif m == "Cisão":
                self._cisao(e)
            elif m == "Resgate":
                self._resgate(e)
            elif m == "Restituição de Capital":
                self._restituicao(e)
            elif m == "Direito de Subscrição":
                if e.qtd:
                    self.p(e).qtd += e.qtd   # direitos recebidos gratuitamente, custo zero
            elif m == "Direitos de Subscrição - Exercido":
                self._exercicio_subscricao(e)
            elif m == "Direitos de Subscrição - Não Exercido":
                self._direito_nao_exercido(e)
            elif m == "Cessão de Direitos - Solicitada":
                pos = self.p(e)
                q = min(e.qtd or 0.0, pos.qtd)
                custo = pos.preco_medio * q
                pos.qtd -= q
                pos.custo -= custo
                self.aviso(f"{e.data} {e.ticker}: {q:g} direitos de subscrição cedidos; o valor recebido pela cessão NÃO consta no extrato (dado faltante; se houve venda em bolsa, o ganho é tributável)")
            elif m == "Recibo de Subscrição":
                pos = self.p(e)
                pos.qtd += e.qtd
                pos.custo += self._sub_pendente.pop(e.ticker, 0.0)
            else:
                self.aviso(f"{e.data} {e.ticker}: movimentação não tratada: {m} (linha {e.linha})")
        return Resultado(self.pos, self.alienacoes, self.compras, self.fluxos, self.proventos, self.avisos, self.duplicatas)

    def _detectar_duplicatas(self, eventos: list[Evento]):
        vistos: dict[tuple, int] = {}
        for e in eventos:
            k = (e.data, e.sentido, e.mov, e.produto, e.inst, e.qtd, e.preco, e.valor)
            vistos[k] = vistos.get(k, 0) + 1
        for k, n in vistos.items():
            if n > 1:
                self.duplicatas.append(f"{k[0]} {k[2]} {k[3][:30]} {k[4][:12]} qtd={k[5]} valor={k[7]} aparece {n}x")

    def _provento(self, e: Evento):
        if e.valor:
            self.proventos.append(Fluxo(e.data, self._linha(e.ticker), e.classe, "provento", e.valor))

    def _liquidacao(self, e: Evento):
        pos = self.p(e)
        pregao = data_pregao_estimada(e.data, self.ciclo)
        if e.sentido == "Credito":
            pos.qtd += e.qtd
            pos.custo += e.valor
            self.compras.append(Compra(e.data, pregao, e.ticker, e.qtd, e.valor, e.inst))
            self.fluxos.append(Fluxo(e.data, self._linha(e.ticker), e.classe, "compra", -e.valor))
        else:
            if e.qtd > pos.qtd + 1e-9:
                self.aviso(f"{e.data} {e.ticker}: venda de {e.qtd:g} com posição de apenas {pos.qtd:g} (histórico incompleto?)")
            custo = pos.preco_medio * e.qtd
            pos.qtd -= e.qtd
            pos.custo -= custo
            if pos.qtd < 1e-9:
                pos.qtd, pos.custo = 0.0, 0.0
            self.alienacoes.append(Alienacao(e.data, pregao, e.ticker, e.classe, e.qtd, e.valor, custo, e.inst))
            self.fluxos.append(Fluxo(e.data, self._linha(e.ticker), e.classe, "venda", e.valor))

    def _fracao_retirada(self, e: Evento):
        pos = self.p(e)
        custo = pos.preco_medio * e.qtd
        pos.qtd -= e.qtd
        pos.custo -= custo
        pos.fracao_qtd += e.qtd
        pos.fracao_custo += custo

    def _leilao_fracao(self, e: Evento):
        pos = self.p(e)
        if pos.fracao_qtd > 1e-9:
            custo = pos.fracao_custo * min(1.0, e.qtd / pos.fracao_qtd)
            pos.fracao_qtd -= e.qtd
            pos.fracao_custo -= custo
            if pos.fracao_qtd < 1e-9:
                pos.fracao_qtd, pos.fracao_custo = 0.0, 0.0
        else:
            custo = pos.preco_medio * e.qtd
        pregao = data_pregao_estimada(e.data, self.ciclo)
        self.alienacoes.append(Alienacao(e.data, pregao, e.ticker, e.classe, e.qtd, e.valor, custo, e.inst, "leilao_fracao",
                                         "venda de fração em leilão (B3)"))
        self.fluxos.append(Fluxo(e.data, self._linha(e.ticker), e.classe, "fracao", e.valor))

    def _atualizacao(self, e: Evento, qtd_total: float):
        for d, antigos, novo, desc in CONVERSOES:
            if d == e.data and novo == e.ticker:
                if (d, novo) in self._conv_feitas:
                    return
                self._conv_feitas.add((d, novo))
                pos_novo = self.p(e)
                custo = 0.0
                for a in antigos:
                    pa = self.pos.get(a)
                    if pa is None:
                        self.aviso(f"{d}: conversão {a}->{novo} sem posição em {a}")
                        continue
                    custo += pa.custo
                    pa.qtd, pa.custo = 0.0, 0.0
                    self._convertidos[a] = novo
                pos_novo.qtd += qtd_total
                pos_novo.custo += custo
                self.aviso(f"{d}: {desc}: {qtd_total:g} {novo} recebem custo total de R$ {custo:,.2f} dos ativos de origem")
                return
        if e.ticker in self._convertidos:
            return  # reapresentação da posição do ativo de origem no dia da conversão
        pos = self.p(e)
        if abs(qtd_total - pos.qtd) < 1e-6:
            return  # mera reapresentação da posição (troca de CNPJ/nome, etc.)
        self.aviso(f"{e.data} {e.ticker}: 'Atualização' de {qtd_total:g} não bate com posição {pos.qtd:g} e não está mapeada; ignorada (A CONFIRMAR)")

    def _cisao(self, e: Evento):
        pos = self.p(e)
        if abs((e.qtd or 0) - pos.qtd) < 1e-6:
            return  # reapresentação da posição do ativo cindido
        pos.qtd += e.qtd
        self.aviso(f"{e.data} {e.ticker}: {e.qtd:g} recebidas em cisão com custo ZERO (proporção da assembleia não consta; IN 1585 art. 58 §6 - A CONFIRMAR)")

    def _resgate(self, e: Evento):
        pos = self.p(e)
        if pos.qtd > 1e-9 and (e.qtd or 0) > 0 and abs(e.qtd - pos.qtd) < 1e-6:
            # resgate total do ativo (ex.: fração de cisão X2ZZ34 paga em dinheiro) => alienação
            custo = pos.custo
            pos.qtd, pos.custo = 0.0, 0.0
            pregao = data_pregao_estimada(e.data, self.ciclo)
            self.alienacoes.append(Alienacao(e.data, pregao, e.ticker, e.classe, e.qtd, e.valor, custo, e.inst, "resgate_cisao",
                                             "fração de cisão resgatada em dinheiro"))
            self.fluxos.append(Fluxo(e.data, self._linha(e.ticker), e.classe, "resgate", e.valor))
            return
        novo = self._convertidos.get(e.ticker)
        if novo:
            pn = self.p(novo, self.pos[novo].classe)
            pn.custo -= e.valor
            self.fluxos.append(Fluxo(e.data, self._linha(e.ticker), e.classe, "resgate", e.valor))
            self.aviso(f"{e.data} {e.ticker}: resgate em dinheiro de R$ {e.valor:,.2f} na incorporação -> abate o custo de {novo} (A CONFIRMAR: poderia ser tratado como alienação de fração)")
            return
        self.aviso(f"{e.data} {e.ticker}: resgate de R$ {e.valor} não tratado (linha {e.linha})")

    def _restituicao(self, e: Evento):
        pos = self.p(e)
        self.fluxos.append(Fluxo(e.data, self._linha(e.ticker), e.classe, "restituicao", e.valor))
        if pos.qtd > 1e-9:
            pos.custo -= e.valor   # IN 1585 art. 58 §8
        else:
            self.aviso(f"{e.data} {e.ticker}: restituição de capital de R$ {e.valor:,.2f} recebida após a venda total; tratada como rendimento não tributado no cálculo (A CONFIRMAR)")

    def _exercicio_subscricao(self, e: Evento):
        pos = self.p(e)
        custo_direitos = pos.preco_medio * e.qtd
        pos.qtd -= e.qtd
        pos.custo -= custo_direitos
        if pos.qtd < 1e-9:
            pos.qtd, pos.custo = 0.0, 0.0
        recibo = RECIBO_DE.get(e.ticker, e.ticker)
        self._sub_pendente[recibo] = self._sub_pendente.get(recibo, 0.0) + custo_direitos + e.valor
        self.fluxos.append(Fluxo(e.data, self._linha(e.ticker), "acoes", "subscricao", -e.valor))

    def _direito_nao_exercido(self, e: Evento):
        pos = self.p(e)
        if not e.qtd or pos.qtd < 1e-9:
            return
        q = min(e.qtd, pos.qtd)
        custo = pos.preco_medio * q
        pos.qtd -= q
        pos.custo -= custo
        if custo > 1e-9:
            pregao = data_pregao_estimada(e.data, self.ciclo)
            self.alienacoes.append(Alienacao(e.data, pregao, e.ticker, e.classe, q, 0.0, custo, e.inst, "direito_nao_exercido",
                                             "direitos comprados e não exercidos (perda)"))
