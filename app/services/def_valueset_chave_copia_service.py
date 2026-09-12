"""Copiar chaves inteiras de um modelo ValueSet para outros modelos.

Quando nasce uma chave nova no vocabulário, ou quando um modelo ficou para trás,
pô-la nos outros modelos era opção a opção, à mão. Num modelo de 100 linhas isso
é meio dia de trabalho — e basta esquecer um para o custeio desse modelo ficar
sem material nessa chave, em silêncio (ver ``valueset_compat``).

**Isto só acrescenta e atualiza. Nunca apaga nem desativa nada no destino.**
Uma opção que exista no destino e não na origem fica onde está: pode ter sido
posta de propósito por quem é dono do modelo, e não cabe a uma cópia em massa
decidir que ela sobra.

A identidade de uma linha é ``(modelo, chave, código da opção)``, e é por ela
que se decide o que é criar e o que é atualizar.

As operações viajam com a linha. Sem elas, a opção copiada custeava diferente da
original sem ninguém dar por isso — é a mesma razão por que o "Gravar como…" as
leva atrás.

As permissões seguem a mesma regra da propagação de operações: o modelo próprio
é sempre seu; um modelo global ou de outra pessoa precisa da permissão
``acao.propagar_operacoes_valueset_outros``.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.domain.valueset_types import normalize_valueset_key
from app.models import User
from app.repositories.def_valueset_modelo_linha_repository import (
    DefValuesetModeloLinhaRepository,
    DefValuesetModeloLinhaResumo,
)
from app.repositories.def_valueset_modelo_repository import (
    DefValuesetModeloRepository,
)
from app.services.def_valueset_modelo_linha_operacao_service import (
    DefValuesetModeloLinhaOperacaoService,
)
from app.services.def_valueset_modelo_linha_service import (
    CriarDefValuesetModeloLinhaData,
    DefValuesetModeloLinhaService,
)
from app.services.permission_service import (
    PERMISSAO_PROPAGAR_OPERACOES_VALUESET_OUTROS,
    permissions_for_user,
    pode,
)

#: Só cria o que falta; o que já lá está fica exatamente como está.
SO_ACRESCENTAR = "SO_ACRESCENTAR"
#: Cria o que falta e põe as opções comuns iguais às da origem.
ACRESCENTAR_E_ATUALIZAR = "ACRESCENTAR_E_ATUALIZAR"

MODOS = (SO_ACRESCENTAR, ACRESCENTAR_E_ATUALIZAR)


@dataclass(frozen=True)
class ChaveDisponivel:
    """Uma chave que o modelo de origem tem, e quantas opções lá estão."""

    chave: str
    nome: str
    grupo: str
    opcoes: int


@dataclass(frozen=True)
class PrevisaoChaveDestino:
    """O que aconteceria a uma chave, num modelo de destino."""

    chave: str
    a_criar: int
    a_atualizar: int
    iguais: int
    so_no_destino: int


@dataclass(frozen=True)
class DestinoCopiaChaves:
    """Um modelo candidato, com a conta exata do que ia mudar."""

    modelo_id: int
    modelo_codigo: str
    modelo_nome: str
    tipo: str
    ambito: str
    proprietario: str
    modelo_ativo: bool
    permitido: bool
    motivo_bloqueio: str | None
    previsoes: tuple[PrevisaoChaveDestino, ...]

    @property
    def total_a_criar(self) -> int:
        return sum(p.a_criar for p in self.previsoes)

    @property
    def total_a_atualizar(self) -> int:
        return sum(p.a_atualizar for p in self.previsoes)

    @property
    def sem_efeito(self) -> bool:
        """Nada mudaria neste destino com o modo escolhido."""
        return self.total_a_criar == 0 and self.total_a_atualizar == 0


@dataclass(frozen=True)
class ContextoCopiaChaves:
    """A pré-visualização inteira, para se decidir com os números à frente."""

    modelo_origem_id: int
    modelo_origem_codigo: str
    chaves: tuple[str, ...]
    modo: str
    destinos: tuple[DestinoCopiaChaves, ...]


@dataclass(frozen=True)
class ResultadoCopiaChaves:
    """O que foi mesmo escrito."""

    modelos_afetados: int
    linhas_criadas: int
    linhas_atualizadas: int
    operacoes_copiadas: int


class DefValuesetChaveCopiaService:
    """Pré-visualizar e copiar chaves entre modelos ValueSet."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.modelo_repository = DefValuesetModeloRepository(session)
        self.linha_repository = DefValuesetModeloLinhaRepository(session)
        self.linha_service = DefValuesetModeloLinhaService(session)
        self.operacao_service = DefValuesetModeloLinhaOperacaoService(session)

    def listar_chaves_do_modelo(self, modelo_id: int) -> tuple[ChaveDisponivel, ...]:
        """As chaves que este modelo tem, para se escolher o que copiar."""
        from app.domain.valueset_navegador_chaves import (
            agrupar_linhas,
            metas_por_codigo,
            rotulo_grupo,
        )
        from app.repositories.def_valueset_chave_repository import (
            DefValuesetChaveRepository,
        )

        metas = metas_por_codigo(DefValuesetChaveRepository(self.session).list_all())
        linhas = [
            linha
            for linha in self.linha_repository.list_by_modelo(modelo_id)
            if linha.ativo
        ]
        disponiveis: list[ChaveDisponivel] = []
        for grupo in agrupar_linhas(linhas, metas):
            for chave in grupo.chaves:
                disponiveis.append(
                    ChaveDisponivel(
                        chave=chave.codigo,
                        nome=chave.nome,
                        grupo=rotulo_grupo(grupo.codigo),
                        opcoes=chave.total,
                    )
                )
        return tuple(disponiveis)

    def preparar_contexto(
        self,
        modelo_origem_id: int,
        chaves: list[str],
        utilizador: User | None,
        *,
        modo: str = SO_ACRESCENTAR,
    ) -> ContextoCopiaChaves:
        """Para cada modelo candidato, quantas linhas se criavam e atualizavam."""
        modo = self._validar_modo(modo)
        chaves_normalizadas = self._normalizar_chaves(chaves)
        if not chaves_normalizadas:
            raise ValueError("Escolha pelo menos uma chave para copiar.")

        modelos = {modelo.id: modelo for modelo in self.modelo_repository.list_all()}
        origem = modelos.get(modelo_origem_id)
        if origem is None:
            raise ValueError("modelo de origem nao encontrado")

        linhas_origem = self._linhas_por_chave(modelo_origem_id, chaves_normalizadas)
        em_falta = [c for c in chaves_normalizadas if not linhas_origem.get(c)]
        if em_falta:
            raise ValueError(
                "O modelo de origem não tem opções ativas nestas chaves: "
                + ", ".join(em_falta)
            )

        permissoes = permissions_for_user(self.session, utilizador)
        utilizador_id = getattr(utilizador, "id", None)

        destinos: list[DestinoCopiaChaves] = []
        for modelo in modelos.values():
            if modelo.id == modelo_origem_id or not modelo.ativo:
                continue
            linhas_destino = self._linhas_por_chave(modelo.id, chaves_normalizadas)
            previsoes = tuple(
                self._prever(
                    chave,
                    linhas_origem.get(chave, []),
                    linhas_destino.get(chave, []),
                    modo,
                )
                for chave in chaves_normalizadas
            )
            permitido, motivo, ambito = self._autorizacao(
                modelo, utilizador_id, permissoes
            )
            destinos.append(
                DestinoCopiaChaves(
                    modelo_id=modelo.id,
                    modelo_codigo=modelo.codigo,
                    modelo_nome=modelo.nome,
                    tipo=modelo.tipo or "",
                    ambito=ambito,
                    proprietario=self._proprietario(modelo),
                    modelo_ativo=modelo.ativo,
                    permitido=permitido,
                    motivo_bloqueio=motivo,
                    previsoes=previsoes,
                )
            )

        destinos.sort(
            key=lambda d: (
                # Os do mesmo tipo da origem primeiro: são os prováveis.
                0 if self._mesmo_tipo(d.tipo, origem.tipo) else 1,
                d.sem_efeito,
                d.modelo_codigo.casefold(),
            )
        )
        return ContextoCopiaChaves(
            modelo_origem_id=modelo_origem_id,
            modelo_origem_codigo=origem.codigo,
            chaves=chaves_normalizadas,
            modo=modo,
            destinos=tuple(destinos),
        )

    def executar(
        self,
        contexto: ContextoCopiaChaves,
        destino_ids: list[int],
        utilizador: User | None,
    ) -> ResultadoCopiaChaves:
        """Copiar para os destinos escolhidos, tudo de uma vez.

        A pré-visualização é refeita antes de escrever: entre o "ver" e o
        "confirmar" outra pessoa pode ter mexido, e o que se aplica tem de ser o
        que está agora — nunca o retrato antigo.
        """
        ids = list(dict.fromkeys(int(i) for i in destino_ids))
        if not ids:
            raise ValueError("Selecione pelo menos um modelo de destino.")

        prometidos = {d.modelo_id for d in contexto.destinos}
        fora = [i for i in ids if i not in prometidos]
        if fora:
            raise ValueError("Foi selecionado um destino fora da pré-visualização.")

        atual = self.preparar_contexto(
            contexto.modelo_origem_id,
            list(contexto.chaves),
            utilizador,
            modo=contexto.modo,
        )
        destinos_atuais = {d.modelo_id: d for d in atual.destinos}

        criadas = 0
        atualizadas = 0
        operacoes = 0
        modelos_afetados = 0
        try:
            for modelo_id in ids:
                destino = destinos_atuais.get(modelo_id)
                if destino is None:
                    raise ValueError(
                        "Um modelo de destino deixou de estar disponível. "
                        "Atualize a pré-visualização."
                    )
                if not destino.permitido:
                    raise PermissionError(
                        destino.motivo_bloqueio or "Sem permissão para este modelo."
                    )
                if destino.sem_efeito:
                    continue

                resultado = self._copiar_para(
                    contexto.modelo_origem_id,
                    modelo_id,
                    contexto.chaves,
                    contexto.modo,
                )
                criadas += resultado[0]
                atualizadas += resultado[1]
                operacoes += resultado[2]
                modelos_afetados += 1

            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        return ResultadoCopiaChaves(
            modelos_afetados=modelos_afetados,
            linhas_criadas=criadas,
            linhas_atualizadas=atualizadas,
            operacoes_copiadas=operacoes,
        )

    # ----- interior -----

    def _copiar_para(
        self,
        modelo_origem_id: int,
        modelo_id: int,
        chaves: tuple[str, ...],
        modo: str,
    ) -> tuple[int, int, int]:
        """Escreve uma chave de cada vez. Devolve (criadas, atualizadas, operações)."""
        criadas = 0
        atualizadas = 0
        operacoes = 0

        linhas_origem = self._linhas_por_chave(modelo_origem_id, chaves)
        linhas_destino = self._linhas_por_chave(modelo_id, chaves)

        for chave in chaves:
            existentes = {
                self._codigo(linha): linha for linha in linhas_destino.get(chave, [])
            }
            for linha in linhas_origem.get(chave, []):
                codigo = self._codigo(linha)
                destino = existentes.get(codigo)
                if destino is None:
                    nova = self.linha_service.criar_linha(
                        self._dados_da_copia(linha, modelo_id),
                        commit=False,
                    )
                    operacoes += self.operacao_service.copiar_operacoes_entre_linhas(
                        linha.id, nova.id, commit=False
                    )
                    criadas += 1
                elif modo == ACRESCENTAR_E_ATUALIZAR and not self._iguais(
                    linha, destino
                ):
                    snapshot = self.linha_service.copiar_snapshot_linha(linha.id)
                    # A proveniência viaja com o conteúdo, e a marca ✎ não se
                    # põe: ela é para assinalar o que o utilizador mexeu à mão.
                    snapshot["origem_dados"] = linha.origem_dados
                    self.linha_service.aplicar_snapshot_linha(
                        destino.id,
                        snapshot,
                        commit=False,
                        marcar_editado=False,
                    )
                    operacoes += self.operacao_service.substituir_operacoes_de(
                        self.operacao_service.listar_operacoes_da_linha(linha.id),
                        destino.id,
                        commit=False,
                    )
                    atualizadas += 1

        return criadas, atualizadas, operacoes

    def _prever(
        self,
        chave: str,
        origem: list[DefValuesetModeloLinhaResumo],
        destino: list[DefValuesetModeloLinhaResumo],
        modo: str,
    ) -> PrevisaoChaveDestino:
        """A conta, sem escrever nada."""
        existentes = {self._codigo(linha): linha for linha in destino}
        a_criar = 0
        a_atualizar = 0
        iguais = 0
        for linha in origem:
            atual = existentes.get(self._codigo(linha))
            if atual is None:
                a_criar += 1
            elif self._iguais(linha, atual):
                iguais += 1
            elif modo == ACRESCENTAR_E_ATUALIZAR:
                a_atualizar += 1
            else:
                iguais += 1  # existe e fica como está

        codigos_origem = {self._codigo(linha) for linha in origem}
        so_no_destino = sum(
            1 for linha in destino if self._codigo(linha) not in codigos_origem
        )
        return PrevisaoChaveDestino(
            chave=chave,
            a_criar=a_criar,
            a_atualizar=a_atualizar,
            iguais=iguais,
            so_no_destino=so_no_destino,
        )

    def _linhas_por_chave(
        self, modelo_id: int, chaves: tuple[str, ...]
    ) -> dict[str, list[DefValuesetModeloLinhaResumo]]:
        alvo = set(chaves)
        por_chave: dict[str, list[DefValuesetModeloLinhaResumo]] = {}
        for linha in self.linha_repository.list_by_modelo(modelo_id):
            if not linha.ativo:
                continue
            chave = normalize_valueset_key(linha.chave)
            if chave in alvo:
                por_chave.setdefault(chave, []).append(linha)
        return por_chave

    def _dados_da_copia(
        self, linha: DefValuesetModeloLinhaResumo, modelo_id: int
    ) -> CriarDefValuesetModeloLinhaData:
        """A linha nova leva o conteúdo todo — menos a identidade do destino."""
        return CriarDefValuesetModeloLinhaData(
            def_valueset_modelo_id=modelo_id,
            chave=linha.chave,
            codigo_opcao=linha.codigo_opcao,
            nome_opcao=linha.nome_opcao,
            prioridade=linha.prioridade,
            ordem=None,  # vai para o fim; "Agrupar por chave" arruma depois
            descricao=linha.descricao,
            materia_prima_id=linha.materia_prima_id,
            ref_materia_prima=linha.ref_materia_prima,
            descricao_materia_prima=linha.descricao_materia_prima,
            valor_texto=linha.valor_texto,
            observacoes=linha.observacoes,
            ativo=True,
            ref_le=linha.ref_le,
            descricao_no_orcamento=linha.descricao_no_orcamento,
            preco_tabela=linha.preco_tabela,
            margem_percentagem=linha.margem_percentagem,
            desconto_percentagem=linha.desconto_percentagem,
            preco_liquido=linha.preco_liquido,
            unidade=linha.unidade,
            desperdicio_percentagem=linha.desperdicio_percentagem,
            tipo_materia_prima=linha.tipo_materia_prima,
            familia_materia_prima=linha.familia_materia_prima,
            coresp_orla_0_4=linha.coresp_orla_0_4,
            coresp_orla_1_0=linha.coresp_orla_1_0,
            preco_orla_0_4_m2=linha.preco_orla_0_4_m2,
            preco_orla_1_0_m2=linha.preco_orla_1_0_m2,
            comp_mp=linha.comp_mp,
            larg_mp=linha.larg_mp,
            esp_mp=linha.esp_mp,
            origem_dados=linha.origem_dados,
            editado_localmente=False,
        )

    @staticmethod
    def _iguais(
        origem: DefValuesetModeloLinhaResumo, destino: DefValuesetModeloLinhaResumo
    ) -> bool:
        """Mesmo material, mesmo preço, mesma prioridade: não há o que copiar."""
        campos = (
            "ref_le",
            "descricao_no_orcamento",
            "preco_tabela",
            "margem_percentagem",
            "desconto_percentagem",
            "preco_liquido",
            "unidade",
            "desperdicio_percentagem",
            "tipo_materia_prima",
            "familia_materia_prima",
            "prioridade",
        )
        return all(
            getattr(origem, campo, None) == getattr(destino, campo, None)
            for campo in campos
        )

    @staticmethod
    def _codigo(linha: DefValuesetModeloLinhaResumo) -> str:
        """A identidade de uma opção dentro da chave."""
        return (linha.codigo_opcao or "").strip().upper()

    @staticmethod
    def _mesmo_tipo(a: str | None, b: str | None) -> bool:
        return (a or "").strip().upper() == (b or "").strip().upper()

    @staticmethod
    def _modelo_global(modelo) -> bool:
        return (modelo.ambito or "").strip().upper() == "GLOBAL"

    def _autorizacao(
        self, modelo, utilizador_id: int | None, permissoes: dict
    ) -> tuple[bool, str | None, str]:
        """Mesma regra da propagação de operações, para não haver duas."""
        global_ = self._modelo_global(modelo)
        proprio = (
            not global_
            and utilizador_id is not None
            and modelo.user_id == utilizador_id
        )
        permitido = proprio or pode(
            permissoes, PERMISSAO_PROPAGAR_OPERACOES_VALUESET_OUTROS
        )
        if global_:
            ambito = "Global"
        elif proprio:
            ambito = "Meu utilizador"
        else:
            ambito = "Outro utilizador"

        motivo = None
        if not permitido:
            motivo = (
                f"Sem permissão para alterar um modelo {ambito.lower()}. "
                "Peça a permissão 'Propagar operações ValueSet para modelos "
                "globais ou de outros utilizadores'."
            )
        return permitido, motivo, ambito

    @staticmethod
    def _proprietario(modelo) -> str:
        return modelo.owner_username or (
            "Global" if modelo.user_id is None else f"Utilizador #{modelo.user_id}"
        )

    @staticmethod
    def _validar_modo(modo: str | None) -> str:
        normalizado = (modo or "").strip().upper() or SO_ACRESCENTAR
        if normalizado not in MODOS:
            raise ValueError(f"modo invalido: {modo}")
        return normalizado

    @staticmethod
    def _normalizar_chaves(chaves: list[str] | None) -> tuple[str, ...]:
        normalizadas = []
        for chave in chaves or []:
            codigo = normalize_valueset_key(chave)
            if codigo and codigo not in normalizadas:
                normalizadas.append(codigo)
        return tuple(normalizadas)
