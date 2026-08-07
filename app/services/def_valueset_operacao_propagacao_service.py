"""Controlled propagation of operations between reusable ValueSet model lines."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.domain.valueset_types import normalize_valueset_key
from app.models import User
from app.repositories.def_valueset_modelo_linha_operacao_repository import (
    DefValuesetModeloLinhaOperacaoResumo,
)
from app.repositories.def_valueset_modelo_linha_repository import (
    DefValuesetModeloLinhaRepository,
    DefValuesetModeloLinhaResumo,
)
from app.repositories.def_valueset_modelo_repository import (
    DefValuesetModeloRepository,
    DefValuesetModeloResumo,
)
from app.services.def_operacao_service import DefOperacaoService
from app.services.def_valueset_modelo_linha_operacao_service import (
    DefValuesetModeloLinhaOperacaoService,
)
from app.services.permission_service import (
    PERMISSAO_PROPAGAR_OPERACOES_VALUESET_OUTROS,
    permissions_for_user,
    pode,
)


@dataclass(frozen=True)
class AlteracaoOperacaoPropagacao:
    """One user-facing operation change in a destination preview."""

    tipo: str
    descricao: str


@dataclass(frozen=True)
class DestinoOperacoesValueset:
    """One matching model line and its exact propagation preview."""

    linha_id: int
    modelo_id: int
    modelo_codigo: str
    modelo_nome: str
    ambito: str
    proprietario: str
    modelo_ativo: bool
    linha_ativa: bool
    chave: str
    codigo_opcao: str | None
    nome_opcao: str | None
    ref_le: str
    permitido: bool
    motivo_bloqueio: str | None
    substituidas: int
    adicionadas: int
    desativadas: int
    inalteradas: int
    alteracoes: tuple[AlteracaoOperacaoPropagacao, ...]
    assinatura_atual: tuple


@dataclass(frozen=True)
class ContextoPropagacaoOperacoesValueset:
    """Read-only source and destination preview shown before confirmation."""

    origem_linha_id: int
    origem_chave: str
    origem_ref_le: str
    origem_modelo: str
    origem_opcao: str
    origem_operacoes: int
    assinatura_origem: tuple
    destinos: tuple[DestinoOperacoesValueset, ...]


@dataclass(frozen=True)
class ResultadoPropagacaoOperacoesValueset:
    """Totals committed by one atomic propagation."""

    destinos_atualizados: int
    substituidas: int
    adicionadas: int
    desativadas: int


class DefValuesetOperacaoPropagacaoService:
    """Find, preview, authorize and atomically update selected destinations."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.linha_repository = DefValuesetModeloLinhaRepository(session)
        self.modelo_repository = DefValuesetModeloRepository(session)
        self.operacao_service = DefValuesetModeloLinhaOperacaoService(session)

    def preparar_contexto(
        self, origem_linha_id: int, utilizador: User | None
    ) -> ContextoPropagacaoOperacoesValueset:
        """Return every same-key/same-Ref-LE candidate with an exact preview."""
        origem = self.linha_repository.get_by_id(origem_linha_id)
        if origem is None:
            raise ValueError("linha origem nao encontrada")

        chave = normalize_valueset_key(origem.chave)
        ref_normalizada = self._normalizar_ref_le(origem.ref_le)
        if not ref_normalizada:
            raise ValueError("A linha origem não tem Ref LE.")

        modelos = {modelo.id: modelo for modelo in self.modelo_repository.list_all()}
        modelo_origem = modelos.get(origem.def_valueset_modelo_id)
        if modelo_origem is None:
            raise ValueError("modelo da linha origem nao encontrado")

        operacoes_origem = self.operacao_service.listar_operacoes_da_linha(origem.id)
        codigos = {
            operacao.id: operacao.codigo
            for operacao in DefOperacaoService(self.session).listar_operacoes()
        }
        permissoes = permissions_for_user(self.session, utilizador)
        utilizador_id = getattr(utilizador, "id", None)

        destinos: list[DestinoOperacoesValueset] = []
        for linha in self.linha_repository.list_all():
            if linha.id == origem.id:
                continue
            if normalize_valueset_key(linha.chave) != chave:
                continue
            if self._normalizar_ref_le(linha.ref_le) != ref_normalizada:
                continue

            modelo = modelos.get(linha.def_valueset_modelo_id)
            if modelo is None:
                continue
            destinos.append(
                self._construir_destino(
                    linha,
                    modelo,
                    operacoes_origem,
                    codigos,
                    utilizador_id,
                    permissoes,
                )
            )

        destinos.sort(
            key=lambda destino: (
                self._ordem_ambito(destino.ambito),
                destino.proprietario.casefold(),
                destino.modelo_codigo.casefold(),
                (destino.nome_opcao or destino.codigo_opcao or "").casefold(),
                destino.linha_id,
            )
        )
        return ContextoPropagacaoOperacoesValueset(
            origem_linha_id=origem.id,
            origem_chave=chave,
            origem_ref_le=(origem.ref_le or "").strip(),
            origem_modelo=modelo_origem.codigo,
            origem_opcao=origem.nome_opcao or origem.codigo_opcao or f"#{origem.id}",
            origem_operacoes=len(operacoes_origem),
            assinatura_origem=self._assinatura_operacoes(operacoes_origem),
            destinos=tuple(destinos),
        )

    def executar(
        self,
        contexto_confirmado: ContextoPropagacaoOperacoesValueset,
        destino_ids: list[int],
        utilizador: User | None,
    ) -> ResultadoPropagacaoOperacoesValueset:
        """Revalidate the preview and update exactly the selected lines once."""
        ids = list(dict.fromkeys(int(destino_id) for destino_id in destino_ids))
        if not ids:
            raise ValueError("Selecione pelo menos um destino.")

        confirmados = {destino.linha_id: destino for destino in contexto_confirmado.destinos}
        if any(destino_id not in confirmados for destino_id in ids):
            raise ValueError("Foi selecionado um destino fora da pré-visualização.")

        contexto_atual = self.preparar_contexto(
            contexto_confirmado.origem_linha_id, utilizador
        )
        atuais = {destino.linha_id: destino for destino in contexto_atual.destinos}
        if contexto_atual.assinatura_origem != contexto_confirmado.assinatura_origem:
            raise ValueError(
                "As operações da origem mudaram. Atualize a pré-visualização antes de confirmar."
            )

        selecionados: list[DestinoOperacoesValueset] = []
        for destino_id in ids:
            confirmado = confirmados[destino_id]
            atual = atuais.get(destino_id)
            if atual is None:
                raise ValueError(
                    "Um destino deixou de ter a mesma chave e Ref LE. Atualize a pré-visualização."
                )
            if not atual.permitido:
                raise PermissionError(atual.motivo_bloqueio or "Sem permissão para o destino.")
            if atual.assinatura_atual != confirmado.assinatura_atual:
                raise ValueError(
                    "As operações de um destino mudaram. Atualize a pré-visualização antes de confirmar."
                )
            selecionados.append(atual)

        operacoes_origem = self.operacao_service.listar_operacoes_da_linha(
            contexto_atual.origem_linha_id
        )
        try:
            for destino in selecionados:
                self.operacao_service.substituir_operacoes_de(
                    operacoes_origem, destino.linha_id, commit=False
                )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        return ResultadoPropagacaoOperacoesValueset(
            destinos_atualizados=len(selecionados),
            substituidas=sum(destino.substituidas for destino in selecionados),
            adicionadas=sum(destino.adicionadas for destino in selecionados),
            desativadas=sum(destino.desativadas for destino in selecionados),
        )

    def _construir_destino(
        self,
        linha: DefValuesetModeloLinhaResumo,
        modelo: DefValuesetModeloResumo,
        origem: list[DefValuesetModeloLinhaOperacaoResumo],
        codigos: dict[int, str],
        utilizador_id: int | None,
        permissoes: dict[str, bool],
    ) -> DestinoOperacoesValueset:
        atuais = self.operacao_service.listar_operacoes_da_linha(linha.id)
        alteracoes: list[AlteracaoOperacaoPropagacao] = []
        substituidas = adicionadas = desativadas = inalteradas = 0

        for indice, operacao_origem in enumerate(origem):
            codigo_novo = codigos.get(
                operacao_origem.def_operacao_id,
                f"Operação #{operacao_origem.def_operacao_id}",
            )
            if indice >= len(atuais):
                adicionadas += 1
                alteracoes.append(
                    AlteracaoOperacaoPropagacao("ADICIONAR", f"Adicionar {codigo_novo}")
                )
                continue

            operacao_atual = atuais[indice]
            if self._assinatura_operacao(operacao_atual) == self._assinatura_operacao(
                operacao_origem
            ):
                inalteradas += 1
                continue

            substituidas += 1
            codigo_atual = codigos.get(
                operacao_atual.def_operacao_id,
                f"Operação #{operacao_atual.def_operacao_id}",
            )
            descricao = (
                f"Substituir {codigo_atual} por {codigo_novo}"
                if codigo_atual != codigo_novo
                else f"Substituir parâmetros de {codigo_novo}"
            )
            alteracoes.append(AlteracaoOperacaoPropagacao("SUBSTITUIR", descricao))

        for excedente in atuais[len(origem) :]:
            if not excedente.ativo:
                inalteradas += 1
                continue
            desativadas += 1
            codigo = codigos.get(
                excedente.def_operacao_id,
                f"Operação #{excedente.def_operacao_id}",
            )
            alteracoes.append(
                AlteracaoOperacaoPropagacao("DESATIVAR", f"Desativar {codigo}")
            )

        global_ = self._modelo_global(modelo)
        proprio = not global_ and utilizador_id is not None and modelo.user_id == utilizador_id
        permitido = proprio or pode(
            permissoes, PERMISSAO_PROPAGAR_OPERACOES_VALUESET_OUTROS
        )
        if global_:
            ambito = "Global"
        elif proprio:
            ambito = "Meu utilizador"
        else:
            ambito = "Outro utilizador"

        proprietario = modelo.owner_username or (
            "Global" if modelo.user_id is None else f"Utilizador #{modelo.user_id}"
        )
        motivo = None
        if not permitido:
            motivo = (
                "Sem a permissão administrativa para alterar modelos globais "
                "ou de outros utilizadores."
            )

        return DestinoOperacoesValueset(
            linha_id=linha.id,
            modelo_id=modelo.id,
            modelo_codigo=modelo.codigo,
            modelo_nome=modelo.nome,
            ambito=ambito,
            proprietario=proprietario,
            modelo_ativo=modelo.ativo,
            linha_ativa=linha.ativo,
            chave=linha.chave,
            codigo_opcao=linha.codigo_opcao,
            nome_opcao=linha.nome_opcao,
            ref_le=(linha.ref_le or "").strip(),
            permitido=permitido,
            motivo_bloqueio=motivo,
            substituidas=substituidas,
            adicionadas=adicionadas,
            desativadas=desativadas,
            inalteradas=inalteradas,
            alteracoes=tuple(alteracoes),
            assinatura_atual=self._assinatura_operacoes(atuais),
        )

    @staticmethod
    def _assinatura_operacao(operacao: DefValuesetModeloLinhaOperacaoResumo) -> tuple:
        return (
            operacao.def_operacao_id,
            operacao.ordem,
            operacao.acao,
            operacao.metodo_calculo,
            operacao.regra_calculo,
            operacao.quantidade_base,
            operacao.rasgo_qt_comp,
            operacao.rasgo_qt_larg,
            operacao.tempo_setup_minutos,
            operacao.tempo_por_unidade_minutos,
            operacao.unidade_tempo,
            operacao.obrigatorio,
            operacao.ativo,
            operacao.observacoes,
        )

    def _assinatura_operacoes(
        self, operacoes: list[DefValuesetModeloLinhaOperacaoResumo]
    ) -> tuple:
        return tuple(self._assinatura_operacao(operacao) for operacao in operacoes)

    @staticmethod
    def _normalizar_ref_le(ref_le: str | None) -> str:
        return (ref_le or "").strip().casefold()

    @staticmethod
    def _modelo_global(modelo: DefValuesetModeloResumo) -> bool:
        return (modelo.ambito or "").strip().upper() == "GLOBAL" or bool(
            modelo.visivel_para_todos
        )

    @staticmethod
    def _ordem_ambito(ambito: str) -> int:
        return {"Meu utilizador": 0, "Outro utilizador": 1, "Global": 2}.get(
            ambito, 3
        )
