"""Renomear uma chave ValueSet levando atrás quem a usa.

O código de uma chave é **texto solto em sete tabelas, sem chave estrangeira
nenhuma**. Mudar o código em ``def_valueset_chaves`` não avisava nada nem
ninguém: quem ficava com o nome antigo não dava erro, calava-se. No custeio, a
lista de materiais dessa chave vinha vazia e o dropdown "Mat. default" ficava em
branco, sem mensagem e sem registo. Foi assim que o ``FERRAGEM_SUPORTE_VARAO``
sobreviveu meses.

Este serviço faz duas coisas que não existiam:

1. **Contar antes** — dizer, tabela a tabela, quem vai ser afetado, para a
   decisão ser tomada com os números à frente e não às cegas.
2. **Propagar** — mudar o código em todos os sítios escolhidos, de uma vez só.

O alcance é uma escolha explícita, e são dois mundos diferentes:

- **Catálogos** (modelos ValueSet, peças, módulos): é a configuração viva, e
  aqui renomear é o que se quer — é isto que faz o custeio voltar a resolver.
- **Orçamentos já feitos**: são o registo do que foi vendido, com preços e
  descrições congelados. Mexer neles reescreve história. Por isso ficam **de
  fora por omissão**, e quem os quiser incluir tem de o dizer.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import (
    DefModuloLinha,
    DefPeca,
    DefValuesetModeloLinha,
    OrcamentoItemCusteioLinha,
    OrcamentoItemValuesetLinha,
    OrcamentoValuesetLinha,
)
from app.repositories.def_valueset_chave_repository import (
    DefValuesetChaveRepository,
)

#: Onde vive o código de uma chave: (etiqueta, coluna, é de orçamento?).
#: A ordem é a que aparece ao utilizador.
_CAMPOS = (
    ("Linhas de modelos ValueSet", DefValuesetModeloLinha.chave, False),
    ("Peças — material", DefPeca.chave_valueset_material, False),
    ("Peças — acabamento superior", DefPeca.chave_valueset_acabamento_sup, False),
    ("Peças — acabamento inferior", DefPeca.chave_valueset_acabamento_inf, False),
    ("Linhas de módulos guardados", DefModuloLinha.chave_valueset, False),
    ("Orçamentos — ValueSet do orçamento", OrcamentoValuesetLinha.chave, True),
    ("Orçamentos — ValueSet do item", OrcamentoItemValuesetLinha.chave, True),
    ("Orçamentos — linhas de custeio", OrcamentoItemCusteioLinha.chave_valueset, True),
)


@dataclass(frozen=True)
class OcorrenciaChave:
    """Quantas vezes o código aparece numa das tabelas."""

    etiqueta: str
    total: int
    orcamento: bool


@dataclass(frozen=True)
class OcorrenciasChave:
    """O retrato completo de quem usa um código de chave."""

    codigo: str
    ocorrencias: tuple[OcorrenciaChave, ...]

    @property
    def catalogos(self) -> tuple[OcorrenciaChave, ...]:
        """Só as configurações — modelos, peças e módulos."""
        return tuple(o for o in self.ocorrencias if not o.orcamento)

    @property
    def orcamentos(self) -> tuple[OcorrenciaChave, ...]:
        """Só os orçamentos já feitos."""
        return tuple(o for o in self.ocorrencias if o.orcamento)

    @property
    def total_catalogos(self) -> int:
        return sum(o.total for o in self.catalogos)

    @property
    def total_orcamentos(self) -> int:
        return sum(o.total for o in self.orcamentos)

    @property
    def total(self) -> int:
        return self.total_catalogos + self.total_orcamentos


@dataclass(frozen=True)
class ResultadoRenomeacao:
    """O que foi mesmo alterado, para se poder dizer ao utilizador."""

    codigo_antigo: str
    codigo_novo: str
    catalogos_atualizados: int
    orcamentos_atualizados: int
    incluiu_orcamentos: bool

    @property
    def total(self) -> int:
        return self.catalogos_atualizados + self.orcamentos_atualizados


class DefValuesetChaveRenomeacaoService:
    """Contar e propagar a mudança de código de uma chave ValueSet."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DefValuesetChaveRepository(session)

    def contar_utilizacoes(self, codigo: str | None) -> OcorrenciasChave:
        """Onde é que este código aparece, tabela a tabela.

        Serve para mostrar os números ANTES de alterar seja o que for.
        """
        normalizado = self._normalizar(codigo)
        if not normalizado:
            return OcorrenciasChave(codigo="", ocorrencias=tuple())

        ocorrencias = []
        for etiqueta, coluna, eh_orcamento in _CAMPOS:
            total = self.session.execute(
                select(func.count()).select_from(coluna.parent).where(
                    coluna == normalizado
                )
            ).scalar_one()
            ocorrencias.append(
                OcorrenciaChave(
                    etiqueta=etiqueta, total=int(total or 0), orcamento=eh_orcamento
                )
            )

        return OcorrenciasChave(codigo=normalizado, ocorrencias=tuple(ocorrencias))

    def renomear(
        self,
        chave_id: int,
        codigo_novo: str,
        *,
        incluir_orcamentos: bool = False,
    ) -> ResultadoRenomeacao:
        """Muda o código da chave e de quem a usa, no alcance escolhido.

        Tudo numa transação: ou muda o vocabulário e os utilizadores todos, ou
        não muda nada. Ficar a meio era pior do que não ter começado — seria
        exatamente a situação que isto veio resolver.
        """
        chave = self.repository.get_by_id(chave_id)
        if chave is None:
            raise ValueError("chave nao encontrada")

        antigo = self._normalizar(chave.codigo)
        novo = self._normalizar(codigo_novo)
        if not novo:
            raise ValueError("codigo is required")
        if novo == antigo:
            raise ValueError("o codigo novo e igual ao atual")

        existente = self.repository.get_by_codigo(novo)
        if existente is not None and existente.id != chave_id:
            raise ValueError("codigo ja existe")

        catalogos = 0
        orcamentos = 0
        try:
            for _etiqueta, coluna, eh_orcamento in _CAMPOS:
                if eh_orcamento and not incluir_orcamentos:
                    continue
                resultado = self.session.execute(
                    update(coluna.parent.class_)
                    .where(coluna == antigo)
                    .values({coluna.key: novo})
                )
                alteradas = int(resultado.rowcount or 0)
                if eh_orcamento:
                    orcamentos += alteradas
                else:
                    catalogos += alteradas

            self.repository.update_chave(
                id=chave_id,
                codigo=novo,
                nome=chave.nome,
                descricao=chave.descricao,
                tipo=chave.tipo,
                grupo=chave.grupo,
                sistema=chave.sistema,
                ativo=chave.ativo,
                ordem=chave.ordem,
                observacoes=chave.observacoes,
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        return ResultadoRenomeacao(
            codigo_antigo=antigo,
            codigo_novo=novo,
            catalogos_atualizados=catalogos,
            orcamentos_atualizados=orcamentos,
            incluiu_orcamentos=incluir_orcamentos,
        )

    @staticmethod
    def _normalizar(codigo: str | None) -> str:
        """O mesmo tratamento que o serviço das chaves dá ao código."""
        normalizado = (codigo or "").strip().upper()
        if not normalizado:
            return ""
        return "_".join(normalizado.split())
