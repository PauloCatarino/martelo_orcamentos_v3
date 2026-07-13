"""Read-only financial audit of persisted budget costing lines."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.custeio_linha_types import DIVISAO_INDEPENDENTE, OPERACAO_MANUAL, PECA, SEPARADOR
from app.models import Cliente, Orcamento, OrcamentoItem, OrcamentoItemCusteioLinha, OrcamentoVersao, User

CRITICO = "CRÍTICO"
AVISO = "AVISO"


@dataclass(frozen=True)
class LinhaAuditoriaDados:
    linha_id: int
    orcamento_versao_id: int
    orcamento_item_id: int
    codigo_orcamento: str
    cliente: str
    utilizador: str
    item: str
    linha_codigo: str
    tipo_linha: str
    operacoes: str
    observacoes: str
    sem_material: bool
    preco_liquido: Decimal | None
    area_m2: Decimal | None
    tempo_corte: Decimal | None
    tempo_orlagem: Decimal | None
    tempo_cnc: Decimal | None
    tempo_manual: Decimal | None
    custo_corte: Decimal | None
    custo_orlagem: Decimal | None
    custo_cnc: Decimal | None
    custo_montagem_manual: Decimal | None
    custo_producao: Decimal | None
    quantidade: Decimal = Decimal("1")
    qt_mod: Decimal | None = None
    qt_und: Decimal | None = None
    comp_real: Decimal | None = None
    larg_real: Decimal | None = None
    esp_real: Decimal | None = None
    desperdicio_percentagem: Decimal | None = None
    tempo_setup: Decimal | None = None
    custo_mp: Decimal | None = None
    custo_orlas: Decimal | None = None
    custo_ferragem: Decimal | None = None
    custo_acabamento: Decimal | None = None
    custo_total: Decimal | None = None
    excluir_mp: bool = False
    excluir_orla: bool = False
    excluir_ferragem: bool = False
    excluir_producao: bool = False
    excluir_acabamento: bool = False


@dataclass(frozen=True)
class CusteioAuditoriaItem:
    severidade: str
    categoria: str
    codigo_teste: str
    codigo_orcamento: str
    cliente: str
    utilizador: str
    item: str
    linha: str
    problema: str
    impacto_eur: Decimal | None
    impacto_texto: str
    acao: str
    orcamento_versao_id: int
    orcamento_item_id: int
    linha_id: int


@dataclass(frozen=True)
class CusteioAuditoriaResultado:
    itens: tuple[CusteioAuditoriaItem, ...]
    impacto_conhecido: Decimal
    criticos: int
    avisos: int
    resumos: tuple["CusteioSaudeResumo", ...] = ()

    @property
    def total(self) -> int:
        return len(self.itens)


@dataclass(frozen=True)
class CusteioSaudeResumo:
    orcamento_versao_id: int
    orcamento_item_id: int
    codigo_orcamento: str
    cliente: str
    item: str
    saude_pct: int
    criticos: int
    avisos: int
    impacto_conhecido: Decimal


@dataclass(frozen=True)
class CusteioSaudeVersaoResumo:
    saude_pct: int
    criticos: int
    avisos: int
    ocorrencias: int
    impacto_conhecido: Decimal


def resumir_saude_versao(
    resultado: CusteioAuditoriaResultado,
) -> CusteioSaudeVersaoResumo:
    """Use the least healthy item as the version's supervisor health."""
    saude = min(
        (resumo.saude_pct for resumo in resultado.resumos),
        default=100,
    )
    return CusteioSaudeVersaoResumo(
        saude_pct=saude,
        criticos=resultado.criticos,
        avisos=resultado.avisos,
        ocorrencias=resultado.total,
        impacto_conhecido=resultado.impacto_conhecido,
    )


class CusteioAuditoriaService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def executar(self) -> CusteioAuditoriaResultado:
        return self._executar()

    def executar_versao(
        self, orcamento_versao_id: int
    ) -> CusteioAuditoriaResultado:
        """Audit only the requested version for an export/email checkpoint."""
        return self._executar(orcamento_versao_id)

    def _executar(
        self, orcamento_versao_id: int | None = None
    ) -> CusteioAuditoriaResultado:
        stmt = (
            select(OrcamentoItemCusteioLinha, OrcamentoItem, OrcamentoVersao, Orcamento, Cliente, User)
            .join(OrcamentoItem, OrcamentoItem.id == OrcamentoItemCusteioLinha.orcamento_item_id)
            .join(OrcamentoVersao, OrcamentoVersao.id == OrcamentoItem.orcamento_versao_id)
            .join(Orcamento, Orcamento.id == OrcamentoVersao.orcamento_id)
            .join(Cliente, Cliente.id == Orcamento.cliente_id)
            .outerjoin(User, User.id == OrcamentoVersao.created_by_id)
            .where(OrcamentoItemCusteioLinha.ativo.is_(True))
        )
        if orcamento_versao_id is not None:
            stmt = stmt.where(OrcamentoVersao.id == orcamento_versao_id)
        dados = []
        for linha, item, versao, _orcamento, cliente, utilizador in self.session.execute(stmt).all():
            dados.append(LinhaAuditoriaDados(
                linha_id=linha.id, orcamento_versao_id=versao.id,
                orcamento_item_id=item.id, codigo_orcamento=versao.codigo_versao,
                cliente=cliente.nome, utilizador=utilizador.username if utilizador else "",
                item=item.item, linha_codigo=linha.codigo or linha.descricao,
                tipo_linha=linha.tipo_linha, operacoes=linha.operacoes or "",
                observacoes=linha.observacoes or "", sem_material=linha.sem_material,
                preco_liquido=linha.preco_liquido, area_m2=linha.area_m2,
                tempo_corte=linha.tempo_corte, tempo_orlagem=linha.tempo_orlagem,
                tempo_cnc=linha.tempo_cnc, tempo_manual=linha.tempo_manual,
                custo_corte=linha.custo_corte, custo_orlagem=linha.custo_orlagem,
                custo_cnc=linha.custo_cnc,
                custo_montagem_manual=linha.custo_montagem_manual,
                custo_producao=linha.custo_producao,
                quantidade=linha.quantidade, qt_mod=linha.qt_mod, qt_und=linha.qt_und,
                comp_real=linha.comp_real, larg_real=linha.larg_real, esp_real=linha.esp_real,
                desperdicio_percentagem=linha.desperdicio_percentagem,
                tempo_setup=linha.tempo_setup, custo_mp=linha.custo_mp,
                custo_orlas=linha.custo_orlas, custo_ferragem=linha.custo_ferragem,
                custo_acabamento=linha.custo_acabamento, custo_total=linha.custo_total,
                excluir_mp=linha.excluir_mp, excluir_orla=linha.excluir_orla,
                excluir_ferragem=linha.excluir_ferragem,
                excluir_producao=linha.excluir_producao,
                excluir_acabamento=linha.excluir_acabamento,
            ))
        return auditar_linhas(dados)


def auditar_linhas(linhas: list[LinhaAuditoriaDados]) -> CusteioAuditoriaResultado:
    ocorrencias: list[CusteioAuditoriaItem] = []

    def add(linha, categoria, teste, problema, acao, *, impacto=None, severidade=CRITICO):
        impacto_texto = (
            f"{impacto.quantize(Decimal('0.01'))} € de diferença conhecida"
            if impacto is not None
            else "€ por determinar — falta tarifa/preço para estimar"
        )
        ocorrencias.append(CusteioAuditoriaItem(
            severidade=severidade, categoria=categoria, codigo_teste=teste,
            codigo_orcamento=linha.codigo_orcamento, cliente=linha.cliente,
            utilizador=linha.utilizador,
            item=linha.item, linha=linha.linha_codigo, problema=problema,
            impacto_eur=impacto, impacto_texto=impacto_texto, acao=acao,
            orcamento_versao_id=linha.orcamento_versao_id,
            orcamento_item_id=linha.orcamento_item_id, linha_id=linha.linha_id,
        ))

    for linha in linhas:
        ops = linha.operacoes.upper()
        obs = linha.observacoes.casefold()
        if linha.tipo_linha not in {SEPARADOR, DIVISAO_INDEPENDENTE} and (
            linha.quantidade <= 0 or (linha.qt_mod is not None and linha.qt_mod <= 0) or (
            linha.qt_und is not None and linha.qt_und < 0
        )):
            add(
                linha, "Quantidade", "QUANTIDADE_INVALIDA",
                "A quantidade da linha é nula ou inválida para o cálculo.",
                "Corrigir QT módulo/QT unidade e recalcular o item.",
            )

        if linha.tipo_linha == PECA and any(
            valor is None or valor <= 0
            for valor in (linha.comp_real, linha.larg_real, linha.esp_real)
        ):
            add(
                linha, "Dimensões", "DIMENSOES_PECA_EM_FALTA",
                "A peça não tem comprimento, largura e espessura reais válidos.",
                "Corrigir as fórmulas/medidas da peça antes de aceitar o custo.",
            )

        if linha.desperdicio_percentagem is not None and linha.desperdicio_percentagem > 100:
            add(
                linha, "Desperdício", "DESPERDICIO_ELEVADO",
                f"O desperdício configurado é {linha.desperdicio_percentagem}%.",
                "Confirmar se o desperdício acima de 100% é intencional.",
                severidade=AVISO,
            )
        verificacoes = (
            ("CORTE", "Corte", linha.custo_corte, linha.tempo_corte, "CUSTO_CORTE_EM_FALTA"),
            ("ORLAGEM", "Orlagem", linha.custo_orlagem, linha.tempo_orlagem, "CUSTO_ORLAGEM_EM_FALTA"),
            ("CNC", "CNC", linha.custo_cnc, linha.tempo_cnc, "CUSTO_CNC_EM_FALTA"),
        )
        for token, categoria, custo, tempo, teste in verificacoes:
            mencionado = token in ops or token.casefold() in obs
            if mencionado and (custo is None or custo == 0) and (tempo or "não calculado" in obs):
                add(
                    linha, categoria, teste,
                    f"{categoria} está previsto mas não tem custo calculado.",
                    f"Preencher/validar máquina, tarifa e tempo de {categoria.lower()} e recalcular o item.",
                )

        if linha.tipo_linha == OPERACAO_MANUAL and (linha.tempo_manual or Decimal("0")) > 0:
            if linha.custo_montagem_manual is None or linha.custo_montagem_manual == 0:
                add(
                    linha, "Operação manual", "CUSTO_MANUAL_EM_FALTA",
                    "Existe tempo manual preenchido, mas o custo da operação é zero.",
                    "Associar uma máquina/posto com custo horário e recalcular a operação manual.",
                )

        tempos = (linha.tempo_corte, linha.tempo_orlagem, linha.tempo_cnc,
                  linha.tempo_manual, linha.tempo_setup)
        if any(tempo is not None and tempo < 0 for tempo in tempos):
            add(
                linha, "Tempos", "TEMPO_NEGATIVO",
                "Existe um tempo de produção negativo.",
                "Corrigir tempo/setup e recalcular o item.",
            )

        if linha.tipo_linha == PECA and not linha.sem_material and (linha.area_m2 or 0) > 0:
            if linha.preco_liquido is None or linha.preco_liquido == 0:
                add(
                    linha, "Material", "PRECO_MATERIAL_EM_FALTA",
                    "A peça consome material, mas o preço líquido está vazio ou zero.",
                    "Selecionar a matéria-prima correta ou atualizar o preço líquido.",
                )

        parciais = [linha.custo_corte, linha.custo_orlagem, linha.custo_cnc, linha.custo_montagem_manual]
        if linha.custo_producao is not None and any(valor is not None for valor in parciais):
            soma = sum((valor or Decimal("0") for valor in parciais), Decimal("0"))
            diferenca = abs(linha.custo_producao - soma)
            if diferenca > Decimal("0.01"):
                add(
                    linha, "Produção", "TOTAL_PRODUCAO_DIVERGENTE",
                    "O total de produção não coincide com corte + orlagem + CNC + manual.",
                    "Recalcular o item e confirmar exclusões ou fatores manuais.",
                    impacto=diferenca, severidade=AVISO,
                )

        exclusoes = (
            (linha.excluir_mp, linha.custo_mp, "Matéria-prima"),
            (linha.excluir_orla, linha.custo_orlas, "Orlas"),
            (linha.excluir_ferragem, linha.custo_ferragem, "Ferragens"),
            (linha.excluir_producao, linha.custo_producao, "Produção"),
            (linha.excluir_acabamento, linha.custo_acabamento, "Acabamentos"),
        )
        for excluido, custo, nome in exclusoes:
            if excluido and custo is not None and custo > 0:
                add(
                    linha, "Exclusão manual", f"CUSTO_{nome.upper().replace('-', '_')}_EXCLUIDO",
                    f"{nome} tem custo calculado, mas foi excluído manualmente do total.",
                    "Confirmar se a exclusão é intencional antes de enviar o orçamento.",
                    impacto=custo, severidade=AVISO,
                )

        categorias_existentes = {
            item.categoria for item in ocorrencias if item.linha_id == linha.linha_id
        }
        for indice, observacao in enumerate(classificar_observacoes_producao(linha.observacoes), 1):
            categoria, severidade, mensagem = observacao
            # Structured checks have better context and must not be duplicated by
            # the textual observation generated by the same costing pipeline.
            if categoria in categorias_existentes:
                continue
            add(
                linha,
                categoria,
                f"OBS_PRODUCAO_{categoria.upper().replace(' ', '_')}_{indice}",
                f"Observações produção: {mensagem}",
                _acao_observacao(categoria),
                severidade=severidade,
            )
            categorias_existentes.add(categoria)

    impacto = sum((i.impacto_eur or Decimal("0") for i in ocorrencias), Decimal("0"))
    grupos: dict[tuple[int, int], list[CusteioAuditoriaItem]] = {}
    for item in ocorrencias:
        grupos.setdefault((item.orcamento_versao_id, item.orcamento_item_id), []).append(item)
    resumos = []
    for (_versao_id, _item_id), grupo in grupos.items():
        primeiro = grupo[0]
        criticos = sum(i.severidade == CRITICO for i in grupo)
        avisos = sum(i.severidade == AVISO for i in grupo)
        resumos.append(CusteioSaudeResumo(
            orcamento_versao_id=primeiro.orcamento_versao_id,
            orcamento_item_id=primeiro.orcamento_item_id,
            codigo_orcamento=primeiro.codigo_orcamento, cliente=primeiro.cliente,
            item=primeiro.item, saude_pct=max(0, 100 - criticos * 25 - avisos * 10),
            criticos=criticos, avisos=avisos,
            impacto_conhecido=sum((i.impacto_eur or Decimal("0") for i in grupo), Decimal("0")),
        ))
    resumos.sort(key=lambda r: (r.saude_pct, r.codigo_orcamento, r.item))
    return CusteioAuditoriaResultado(
        itens=tuple(ocorrencias), impacto_conhecido=impacto,
        criticos=sum(i.severidade == CRITICO for i in ocorrencias),
        avisos=sum(i.severidade == AVISO for i in ocorrencias),
        resumos=tuple(resumos),
    )


def classificar_observacoes_producao(texto: str | None) -> list[tuple[str, str, str]]:
    """Return financially relevant production notes; ignore neutral free text."""
    resultado = []
    marcadores_criticos = (
        "não calcul", "nao calcul", "em falta", "sem preço", "sem preco",
        "sem tarifa", "sem material", "não aplic", "nao aplic", "não defin",
        "nao defin", "não configur", "nao configur", "inválid", "invalid",
        "sem chave", "não encontr", "nao encontr", "não permite", "nao permite",
        "incomplet",
    )
    marcadores_aviso = ("confirmar", "manual", "fallback", "rever", "atenção", "atencao")
    for linha in (texto or "").splitlines():
        mensagem = linha.strip()
        normalizada = mensagem.casefold()
        if not mensagem:
            continue
        if any(marcador in normalizada for marcador in marcadores_criticos):
            severidade = CRITICO
        elif any(marcador in normalizada for marcador in marcadores_aviso):
            severidade = AVISO
        else:
            continue
        if "orla" in normalizada:
            categoria = "Orlagem"
        elif "cnc" in normalizada or "rasgo" in normalizada or "fura" in normalizada:
            categoria = "CNC"
        elif "montagem" in normalizada or "manual" in normalizada or "mão de obra" in normalizada:
            categoria = "Operação manual"
        elif "acabamento" in normalizada:
            categoria = "Acabamento"
        elif "ferragem" in normalizada:
            categoria = "Ferragem"
        elif "quantidade" in normalizada or "regra" in normalizada:
            categoria = "Quantidade"
        elif "tempo" in normalizada or "setup" in normalizada:
            categoria = "Tempos"
        elif "material" in normalizada or "custo mp" in normalizada or "valueset" in normalizada:
            categoria = "Material"
        else:
            categoria = "Observações produção"
        resultado.append((categoria, severidade, mensagem))
    return resultado


def _acao_observacao(categoria: str) -> str:
    acoes = {
        "Material": "Completar material, ValueSet e preço líquido; depois recalcular o item.",
        "Orlagem": "Validar orlas, máquina e tarifas de orlagem; depois recalcular.",
        "CNC": "Validar operação, máquina, geometria, tempo e tarifa CNC; depois recalcular.",
        "Operação manual": "Validar tempo e custo horário da operação manual; depois recalcular.",
        "Acabamento": "Completar acabamento, área, preço e desperdício; depois recalcular.",
        "Ferragem": "Completar referência, quantidade e preço da ferragem; depois recalcular.",
        "Quantidade": "Corrigir regra ou quantidade indicada e recalcular o item.",
        "Tempos": "Completar tempos e setup da produção e recalcular o item.",
    }
    return acoes.get(categoria, "Rever a observação de produção e completar os dados antes de aceitar o preço.")
