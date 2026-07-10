"""Read-only technical catalog audit.

The audit never changes catalog records. It turns potentially dangerous or
ambiguous configurations into explicit, reviewable findings.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.operacao_acao_types import SUBSTITUIR, normalize_operacao_acao
from app.domain.peca_natureza_types import CONJUNTO
from app.domain.peca_types import COMPOSTA
from app.models import (
    DefMaquina,
    DefModulo,
    DefModuloLinha,
    DefOperacao,
    DefPeca,
    DefPecaComponente,
    DefPecaOperacao,
    DefRegraQuantidade,
    DefValuesetChave,
    DefValuesetModelo,
    DefValuesetModeloLinha,
    DefValuesetModeloLinhaOperacao,
)

ERRO = "ERRO"
AVISO = "AVISO"
INFORMACAO = "INFORMAÇÃO"


@dataclass(frozen=True)
class CatalogoAuditoriaItem:
    severidade: str
    codigo_teste: str
    area: str
    entidade: str
    entidade_id: int | None
    entidade_codigo: str
    problema: str
    impacto: str
    sugestao: str


@dataclass(frozen=True)
class CatalogoAuditoriaResultado:
    itens: tuple[CatalogoAuditoriaItem, ...]
    erros: int
    avisos: int
    informacoes: int

    @property
    def total(self) -> int:
        return len(self.itens)


@dataclass(frozen=True)
class CatalogoAuditoriaDados:
    pecas: tuple
    componentes: tuple
    ligacoes_operacoes: tuple
    operacoes: tuple
    maquinas: tuple
    regras: tuple
    chaves_valueset: tuple
    modelos_valueset: tuple
    linhas_valueset: tuple
    operacoes_valueset: tuple
    modulos: tuple
    linhas_modulo: tuple


class CatalogoAuditoriaService:
    """Inspect catalog consistency without writes or automatic corrections."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def executar(self) -> CatalogoAuditoriaResultado:
        dados = CatalogoAuditoriaDados(
            pecas=self._listar(DefPeca),
            componentes=self._listar(DefPecaComponente),
            ligacoes_operacoes=self._listar(DefPecaOperacao),
            operacoes=self._listar(DefOperacao),
            maquinas=self._listar(DefMaquina),
            regras=self._listar(DefRegraQuantidade),
            chaves_valueset=self._listar(DefValuesetChave),
            modelos_valueset=self._listar(DefValuesetModelo),
            linhas_valueset=self._listar(DefValuesetModeloLinha),
            operacoes_valueset=self._listar(DefValuesetModeloLinhaOperacao),
            modulos=self._listar(DefModulo),
            linhas_modulo=self._listar(DefModuloLinha),
        )
        return self.auditar_dados(dados)

    def _listar(self, model) -> tuple:
        return tuple(self.session.execute(select(model)).scalars().all())

    @classmethod
    def auditar_dados(
        cls, dados: CatalogoAuditoriaDados
    ) -> CatalogoAuditoriaResultado:
        itens: list[CatalogoAuditoriaItem] = []
        pecas = {p.id: p for p in dados.pecas}
        pecas_codigo = {cls._norm(p.codigo): p for p in dados.pecas}
        operacoes = {o.id: o for o in dados.operacoes}
        maquinas = {m.id: m for m in dados.maquinas}
        regras = {r.id: r for r in dados.regras}
        chaves = {cls._norm(c.codigo): c for c in dados.chaves_valueset}
        modelos = {m.id: m for m in dados.modelos_valueset}
        linhas_vs = {l.id: l for l in dados.linhas_valueset}
        modulos = {m.id: m for m in dados.modulos}

        ligacoes_por_peca: dict[int, list] = {}
        for ligacao in dados.ligacoes_operacoes:
            ligacoes_por_peca.setdefault(ligacao.def_peca_id, []).append(ligacao)

        componentes_por_peca: dict[int, list] = {}
        for componente in dados.componentes:
            componentes_por_peca.setdefault(
                componente.def_peca_pai_id, []
            ).append(componente)

        def add(severidade, teste, area, entidade, obj, codigo, problema, impacto, sugestao):
            itens.append(
                CatalogoAuditoriaItem(
                    severidade=severidade,
                    codigo_teste=teste,
                    area=area,
                    entidade=entidade,
                    entidade_id=getattr(obj, "id", None),
                    entidade_codigo=str(codigo or ""),
                    problema=problema,
                    impacto=impacto,
                    sugestao=sugestao,
                )
            )

        # Pieces: effective operations, naming, edging and material keys.
        for peca in dados.pecas:
            if not getattr(peca, "ativo", True):
                continue
            ligacoes = ligacoes_por_peca.get(peca.id, [])
            ativas = [l for l in ligacoes if getattr(l, "ativo", True)]
            ops_ativas = [
                operacoes[l.def_operacao_id]
                for l in ativas
                if l.def_operacao_id in operacoes
                and getattr(operacoes[l.def_operacao_id], "ativo", True)
            ]
            tem_cnc = any(cls._eh_cnc(op) for op in ops_ativas)
            nome_codigo = cls._norm(f"{peca.codigo} {getattr(peca, 'nome', '')}")
            if "COM_CNC" in nome_codigo and not tem_cnc:
                add(
                    AVISO, "PECA_COM_CNC_SEM_CNC", "Peças", "Peça", peca,
                    peca.codigo, "O nome indica COM_CNC, mas não existe CNC direto ativo.",
                    "O nome pode induzir o utilizador a assumir um custo CNC inexistente.",
                    "Confirmar se o CNC vem de um associado ou associar/renomear a peça.",
                )
            if "SEM_CNC" in nome_codigo and tem_cnc:
                add(
                    ERRO, "PECA_SEM_CNC_COM_CNC", "Peças", "Peça", peca,
                    peca.codigo, "O nome indica SEM_CNC, mas existe CNC direto ativo.",
                    "Pode ser contabilizado CNC numa peça apresentada como sem CNC.",
                    "Remover/desativar o CNC ou corrigir o nome da peça.",
                )

            codigo_orla = f"{peca.orla_c1}{peca.orla_c2}{peca.orla_l1}{peca.orla_l2}"
            tem_orla = any(str(valor) != "0" for valor in codigo_orla)
            tem_orlagem = any(cls._eh_orlagem(op) for op in ops_ativas)
            if tem_orla and not tem_orlagem:
                add(
                    AVISO, "ORLA_SEM_OPERACAO", "Peças", "Peça", peca,
                    peca.codigo, f"Código de orla {codigo_orla} sem operação de orlagem ativa.",
                    "O consumo de orla pode existir sem o respetivo custo de produção.",
                    "Associar uma operação de orlagem ou rever o código de orla.",
                )
            if not tem_orla and tem_orlagem:
                add(
                    AVISO, "OPERACAO_ORLA_SEM_ORLA", "Peças", "Peça", peca,
                    peca.codigo, "Existe operação de orlagem, mas o código de orla é 0000.",
                    "Pode existir tempo/custo de orlagem sem lados configurados.",
                    "Rever os lados de orla ou remover a operação de orlagem.",
                )

            eh_conjunto = (
                getattr(peca, "natureza", None) == CONJUNTO
                or getattr(peca, "tipo_peca", None) == COMPOSTA
            )
            if not getattr(peca, "sem_material", False) and not eh_conjunto:
                chave_codigo = cls._norm(
                    getattr(peca, "chave_valueset_material", None)
                )
                if not chave_codigo:
                    add(
                        ERRO, "PECA_SEM_VALUESET", "Peças", "Peça", peca,
                        peca.codigo, "Peça com material sem chave ValueSet.",
                        "A matéria-prima e o preço podem ficar vazios no custeio.",
                        "Associar uma chave ValueSet ou marcar a peça como sem material.",
                    )
                elif chave_codigo not in chaves:
                    add(
                        ERRO, "VALUESET_INEXISTENTE", "Peças", "Peça", peca,
                        peca.codigo, f"A chave ValueSet {chave_codigo} não existe.",
                        "A peça não consegue resolver a matéria-prima no orçamento.",
                        "Criar/corrigir a chave ValueSet da peça.",
                    )
                elif not getattr(chaves[chave_codigo], "ativo", True):
                    add(
                        ERRO, "VALUESET_INATIVO", "Peças", "Peça", peca,
                        peca.codigo, f"A chave ValueSet {chave_codigo} está inativa.",
                        "Novos orçamentos podem não resolver o material da peça.",
                        "Ativar a chave ou escolher outra chave ativa.",
                    )

            vistos: set[int] = set()
            for ligacao in ativas:
                if ligacao.def_operacao_id in vistos:
                    add(
                        ERRO, "OPERACAO_DUPLICADA", "Operações", "Peça", peca,
                        peca.codigo, "A mesma operação está associada mais de uma vez.",
                        "Tempos e custos podem ser contabilizados em duplicado.",
                        "Manter apenas uma ligação ativa para a operação.",
                    )
                vistos.add(ligacao.def_operacao_id)
                op = operacoes.get(ligacao.def_operacao_id)
                if op is None:
                    add(
                        ERRO, "OPERACAO_INEXISTENTE", "Operações", "Peça", peca,
                        peca.codigo, "Ligação para uma operação inexistente.",
                        "O cálculo ignora ou falha ao resolver a operação.",
                        "Remover a ligação inválida e associar uma operação existente.",
                    )
                elif not getattr(op, "ativo", True):
                    add(
                        ERRO, "OPERACAO_INATIVA_ASSOCIADA", "Operações", "Peça", peca,
                        peca.codigo, f"A operação {op.codigo} está inativa mas a ligação está ativa.",
                        "A operação não entra no snapshot e o custo pode ficar incompleto.",
                        "Ativar a operação ou desativar/remover a ligação na peça.",
                    )

        # Global operation -> machine consistency.
        for op in dados.operacoes:
            if not getattr(op, "ativo", True) or getattr(op, "maquina_id", None) is None:
                continue
            maquina = maquinas.get(op.maquina_id)
            if maquina is None or not getattr(maquina, "ativo", True):
                add(
                    ERRO, "MAQUINA_INATIVA_OPERACAO", "Operações", "Operação", op,
                    op.codigo, "Operação ativa ligada a máquina inexistente ou inativa.",
                    "O tempo pode ser calculado sem tarifa/máquina válida.",
                    "Associar uma máquina ativa ou desativar a operação.",
                )

        # Components, quantity rules and possible CNC double counting.
        usados_regras = {
            c.def_regra_quantidade_id
            for c in dados.componentes
            if getattr(c, "ativo", True) and c.def_regra_quantidade_id is not None
        }
        usados_regras.update(
            l.def_regra_quantidade_id
            for l in dados.linhas_modulo
            if getattr(l, "ativo", True) and l.def_regra_quantidade_id is not None
        )
        graph: dict[int, set[int]] = {}
        for componente in dados.componentes:
            if not getattr(componente, "ativo", True):
                continue
            pai = pecas.get(componente.def_peca_pai_id)
            if pai is not None and not getattr(pai, "ativo", True):
                continue
            filho = cls._resolver_peca_componente(
                componente, pecas, pecas_codigo
            )
            codigo_pai = getattr(pai, "codigo", componente.def_peca_pai_id)
            if filho is None:
                add(
                    ERRO, "ASSOCIADO_SEM_BIBLIOTECA", "Associados", "Associado",
                    componente, codigo_pai,
                    f"Associado {getattr(componente, 'referencia_componente', '') or componente.id} sem ligação real à biblioteca.",
                    "Material, operações e preço do associado podem ficar incompletos.",
                    "Selecionar uma peça existente no campo Peça componente.",
                )
            else:
                graph.setdefault(componente.def_peca_pai_id, set()).add(filho.id)
                if not getattr(filho, "ativo", True):
                    add(
                        ERRO, "ASSOCIADO_INATIVO", "Associados", "Associado",
                        componente, codigo_pai,
                        f"O associado {filho.codigo} está inativo.",
                        "Novas inserções podem gerar uma referência desatualizada.",
                        "Ativar/substituir o associado ou desativar esta ligação.",
                    )

                pai_cnc = cls._peca_tem_cnc(
                    componente.def_peca_pai_id, ligacoes_por_peca, operacoes
                )
                filho_cnc = cls._peca_tem_cnc(
                    filho.id, ligacoes_por_peca, operacoes
                )
                if pai_cnc and filho_cnc:
                    add(
                        AVISO, "CNC_PECA_E_ASSOCIADO", "Custos", "Associado",
                        componente, codigo_pai,
                        f"A peça {codigo_pai} e o associado {filho.codigo} têm CNC ativo.",
                        "O CNC pode ser contabilizado duas vezes sem intenção explícita.",
                        "Confirmar se são operações diferentes; caso contrário manter apenas a origem correta.",
                    )

            regra_id = getattr(componente, "def_regra_quantidade_id", None)
            if regra_id is not None:
                regra = regras.get(regra_id)
                if regra is None or not getattr(regra, "ativo", True):
                    add(
                        ERRO, "REGRA_INATIVA_ASSOCIADA", "Regras", "Associado",
                        componente, codigo_pai,
                        "Associado ligado a regra de quantidade inexistente ou inativa.",
                        "A quantidade pode usar um valor fixo inesperado.",
                        "Selecionar uma regra ativa ou remover a ligação à regra.",
                    )

        for regra in dados.regras:
            if getattr(regra, "ativo", True) and regra.id not in usados_regras:
                add(
                    INFORMACAO, "REGRA_NAO_UTILIZADA", "Regras", "Regra", regra,
                    regra.codigo, "Regra ativa sem utilização em associados ou módulos.",
                    "Não altera custos, mas aumenta a configuração sem efeito.",
                    "Confirmar utilização futura ou desativar a regra.",
                )

        cls._auditar_ciclos(graph, pecas, add)

        # ValueSet actions: make every replacement visible for review.
        for ligacao in dados.operacoes_valueset:
            if not getattr(ligacao, "ativo", True):
                continue
            linha = linhas_vs.get(ligacao.def_valueset_modelo_linha_id)
            modelo = modelos.get(getattr(linha, "def_valueset_modelo_id", None))
            if (
                linha is not None
                and not getattr(linha, "ativo", True)
                or modelo is not None
                and not getattr(modelo, "ativo", True)
            ):
                continue
            op = operacoes.get(ligacao.def_operacao_id)
            if op is None or not getattr(op, "ativo", True):
                add(
                    ERRO, "VALUESET_OPERACAO_INATIVA", "ValueSet", "Linha ValueSet",
                    linha or ligacao, getattr(linha, "codigo_opcao", ligacao.id),
                    "Ação ValueSet ligada a operação inexistente ou inativa.",
                    "A ação não produzirá o resultado esperado no custeio.",
                    "Escolher uma operação ativa ou desativar a ação.",
                )
            if normalize_operacao_acao(getattr(ligacao, "acao", None)) == SUBSTITUIR:
                add(
                    INFORMACAO, "VALUESET_SUBSTITUICAO", "ValueSet", "Linha ValueSet",
                    linha or ligacao,
                    getattr(linha, "codigo_opcao", None) or getattr(modelo, "codigo", ""),
                    f"A variante substitui operações da categoria de {getattr(op, 'codigo', 'operação desconhecida')}.",
                    "Ao aplicar a variante, uma operação base da mesma categoria pode desaparecer.",
                    "Rever no orçamento se SUBSTITUIR é preferível a ADICIONAR.",
                )

        # Saved modules: stale piece ids/codes and inactive references.
        for linha in dados.linhas_modulo:
            if not getattr(linha, "ativo", True):
                continue
            modulo = modulos.get(linha.def_modulo_id)
            if modulo is not None and not getattr(modulo, "ativo", True):
                continue
            codigo_modulo = getattr(modulo, "codigo", linha.def_modulo_id)
            referencia_linha = (
                f"{codigo_modulo} / linha {getattr(linha, 'ordem', linha.id)}"
            )
            peca = pecas.get(getattr(linha, "def_peca_id", None))
            codigo_guardado = cls._norm(getattr(linha, "def_peca_codigo", None))
            if getattr(linha, "def_peca_id", None) is not None and peca is None:
                add(
                    ERRO, "MODULO_PECA_INEXISTENTE", "Módulos", "Linha de módulo",
                    linha, referencia_linha, "Linha ligada a uma peça que já não existe.",
                    "A importação pode criar uma linha incompleta e sem material.",
                    "Substituir a referência da linha ou recriar o módulo.",
                )
            elif peca is not None:
                if not getattr(peca, "ativo", True):
                    add(
                        AVISO, "MODULO_PECA_INATIVA", "Módulos", "Linha de módulo",
                        linha, referencia_linha, f"O módulo referencia a peça inativa {peca.codigo}.",
                        "A importação reutiliza uma definição que deixou de estar disponível.",
                        "Atualizar a referência do módulo para uma peça ativa.",
                    )
                if codigo_guardado and codigo_guardado != cls._norm(peca.codigo):
                    add(
                        AVISO, "MODULO_CODIGO_DESATUALIZADO", "Módulos", "Linha de módulo",
                        linha, referencia_linha,
                        f"Código guardado {codigo_guardado} difere da peça atual {peca.codigo}.",
                        "O módulo contém um snapshot de referência desatualizado.",
                        "Atualizar explicitamente o módulo preservando os desvios.",
                    )
            elif codigo_guardado and codigo_guardado not in pecas_codigo:
                add(
                    AVISO, "MODULO_REFERENCIA_SEM_PECA", "Módulos", "Linha de módulo",
                    linha, referencia_linha,
                    f"A referência {codigo_guardado} não corresponde a uma peça atual.",
                    "A linha será importada sem ligação completa à biblioteca.",
                    "Associar uma peça existente ou remover a linha obsoleta do módulo.",
                )

        ordem = {ERRO: 0, AVISO: 1, INFORMACAO: 2}
        itens.sort(
            key=lambda item: (
                ordem.get(item.severidade, 9),
                item.area,
                item.entidade_codigo,
                item.codigo_teste,
            )
        )
        return CatalogoAuditoriaResultado(
            itens=tuple(itens),
            erros=sum(i.severidade == ERRO for i in itens),
            avisos=sum(i.severidade == AVISO for i in itens),
            informacoes=sum(i.severidade == INFORMACAO for i in itens),
        )

    @staticmethod
    def _norm(value) -> str:
        return str(value or "").strip().upper()

    @classmethod
    def _eh_cnc(cls, operacao) -> bool:
        texto = cls._norm(
            f"{getattr(operacao, 'codigo', '')} {getattr(operacao, 'nome', '')} "
            f"{getattr(operacao, 'tipo_operacao', '')}"
        )
        return "CNC" in texto

    @classmethod
    def _eh_orlagem(cls, operacao) -> bool:
        texto = cls._norm(
            f"{getattr(operacao, 'codigo', '')} {getattr(operacao, 'nome', '')} "
            f"{getattr(operacao, 'tipo_operacao', '')}"
        )
        return "ORLAGEM" in texto or "ORLAR" in texto

    @classmethod
    def _peca_tem_cnc(cls, peca_id, ligacoes_por_peca, operacoes) -> bool:
        return any(
            getattr(ligacao, "ativo", True)
            and ligacao.def_operacao_id in operacoes
            and getattr(operacoes[ligacao.def_operacao_id], "ativo", True)
            and cls._eh_cnc(operacoes[ligacao.def_operacao_id])
            for ligacao in ligacoes_por_peca.get(peca_id, [])
        )

    @classmethod
    def _resolver_peca_componente(cls, componente, pecas, pecas_codigo):
        peca_id = getattr(componente, "def_peca_componente_id", None)
        if peca_id is not None:
            return pecas.get(peca_id)
        return pecas_codigo.get(cls._norm(getattr(componente, "referencia_componente", None)))

    @classmethod
    def _auditar_ciclos(cls, graph, pecas, add) -> None:
        encontrados: set[frozenset[int]] = set()

        def visitar(inicio, atual, caminho):
            for seguinte in graph.get(atual, set()):
                if seguinte == inicio:
                    ciclo = frozenset((*caminho, atual))
                    if ciclo and ciclo not in encontrados:
                        encontrados.add(ciclo)
                elif seguinte not in caminho:
                    visitar(inicio, seguinte, (*caminho, atual))

        for inicio in graph:
            visitar(inicio, inicio, tuple())

        for ciclo in encontrados:
            codigos = sorted(
                getattr(pecas.get(peca_id), "codigo", str(peca_id))
                for peca_id in ciclo
            )
            primeira = pecas.get(next(iter(ciclo)))
            add(
                ERRO, "ASSOCIACAO_CIRCULAR", "Associados", "Peça", primeira,
                " → ".join(codigos),
                f"Associação circular detetada entre: {', '.join(codigos)}.",
                "A expansão recursiva pode repetir peças ou ser interrompida.",
                "Remover uma das ligações para tornar a hierarquia acíclica.",
            )
