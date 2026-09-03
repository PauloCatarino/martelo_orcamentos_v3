"""Regras dos componentes de uma matéria-prima composta.

A regra que interessa é uma só, e é a que torna a contagem de uma obra
possível: **uma referência só pode ser PRINCIPAL num conjunto**. Se a mesma
dobradiça de copo fosse principal na ``FER0015`` e na ``FER0016``, ao ler uma
obra ninguém saberia qual dos dois conjuntos contar — e o preço saía a dobrar
ou a menos, sem aviso.

O contrário é permitido de propósito:

- **vários principais no mesmo conjunto** são apelidos (os dois pés AXILO, de
  alturas diferentes, que valem o mesmo Ref LE) e somam-se;
- **um secundário partilhado por muitos conjuntos** é o caso normal (o calço H0
  entra em várias dobradiças).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.session import app_session
from app.domain.materia_prima_types import (
    PAPEIS_COMPONENTE_VALIDOS,
    PAPEL_PRINCIPAL,
)
from app.repositories.def_materia_prima_componente_repository import (
    ComponenteDados,
    ComponenteResumo,
    DefMateriaPrimaComponenteRepository,
)


class ReferenciaJaUsadaError(ValueError):
    """A referência já é principal noutro conjunto — a contagem ficaria ambígua."""


class DefMateriaPrimaComponenteService:
    """Ler e gravar os componentes de uma matéria-prima."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DefMateriaPrimaComponenteRepository(session)

    # ----- leituras -----

    def listar(self, materia_prima_id: int) -> list[ComponenteResumo]:
        return self.repository.listar(materia_prima_id)

    def contar_principais(self, materia_prima_id: int) -> int:
        """Quantos apelidos este conjunto tem."""
        return sum(1 for c in self.listar(materia_prima_id) if c.principal)

    # ----- escritas -----

    def criar(self, materia_prima_id: int, dados: ComponenteDados) -> ComponenteResumo:
        dados = self._normalizar(dados)
        self._validar(materia_prima_id, dados, componente_id=None)
        if dados.ordem <= 0:
            dados = ComponenteDados(
                **{**dados.__dict__, "ordem": self.repository.proxima_ordem(materia_prima_id)}
            )
        return self.repository.criar(
            materia_prima_id, dados, user_id=self._utilizador_atual_id()
        )

    def atualizar(self, componente_id: int, dados: ComponenteDados) -> ComponenteResumo:
        atual = self.repository.obter(componente_id)
        if atual is None:
            raise ValueError("componente não encontrado")
        dados = self._normalizar(dados)
        self._validar(atual.materia_prima_id, dados, componente_id=componente_id)
        return self.repository.atualizar(
            componente_id, dados, user_id=self._utilizador_atual_id()
        )

    def eliminar(self, componente_id: int) -> bool:
        return self.repository.eliminar(componente_id)

    def guardar_lista(
        self, materia_prima_id: int, linhas: list[ComponenteDados]
    ) -> list[ComponenteResumo]:
        """Gravar a lista toda de uma vez, como o ecrã a mostra.

        Valida tudo ANTES de escrever seja o que for: uma ficha com duas linhas
        e a segunda errada não pode ficar meio gravada.
        """
        preparadas = [self._normalizar(linha) for linha in linhas]
        self._validar_entre_si(preparadas)
        for indice, linha in enumerate(preparadas, start=1):
            self._validar(materia_prima_id, linha, componente_id=None, ignorar_conjunto=True)
            preparadas[indice - 1] = ComponenteDados(**{**linha.__dict__, "ordem": indice})

        for antigo in self.repository.listar(materia_prima_id):
            self.repository.eliminar(antigo.id)

        utilizador_id = self._utilizador_atual_id()
        return [
            self.repository.criar(materia_prima_id, linha, user_id=utilizador_id)
            for linha in preparadas
        ]

    # ----- regras -----

    def _normalizar(self, dados: ComponenteDados) -> ComponenteDados:
        papel = (dados.papel or "").strip().upper()
        if papel not in PAPEIS_COMPONENTE_VALIDOS:
            raise ValueError(
                f"Papel do componente desconhecido: «{dados.papel}». "
                f"Só existem {' e '.join(PAPEIS_COMPONENTE_VALIDOS)}."
            )
        return ComponenteDados(**{**dados.__dict__, "papel": papel})

    def _validar(
        self,
        materia_prima_id: int,
        dados: ComponenteDados,
        *,
        componente_id: int | None,
        ignorar_conjunto: bool = False,
    ) -> None:
        if not self._tem_chave(dados):
            raise ValueError(
                "Um componente precisa de pelo menos uma referência — o nome do "
                "artigo no iMos, a Ref PHC ou a referência do fornecedor. Sem "
                "nenhuma delas nunca vai bater certo com a lista de uma obra."
            )
        if dados.quantidade is None or dados.quantidade <= 0:
            raise ValueError(
                "A quantidade por conjunto tem de ser maior do que zero."
            )
        if dados.papel != PAPEL_PRINCIPAL:
            return

        dono = self.repository.procurar_principal(
            nome_imos=dados.nome_imos,
            ref_phc=dados.ref_phc,
            ref_fornecedor=dados.ref_fornecedor,
            excluir_id=componente_id,
        )
        if dono is None:
            return
        if ignorar_conjunto and dono.materia_prima_id == materia_prima_id:
            # Ao gravar a lista toda, as linhas antigas deste mesmo conjunto
            # ainda estão na base — vão ser substituídas já a seguir.
            return
        if dono.materia_prima_id == materia_prima_id:
            return

        onde = self.repository.ref_le_do_conjunto(dono.materia_prima_id) or "outro conjunto"
        raise ReferenciaJaUsadaError(
            f"Esta referência já é o componente principal de «{onde}». "
            "A mesma referência não pode identificar dois conjuntos — ao ler "
            "uma obra não se saberia qual deles contar."
        )

    def _validar_entre_si(self, linhas: list[ComponenteDados]) -> None:
        """Duas linhas da MESMA ficha não podem ser principais com a mesma chave."""
        vistas: dict[tuple[str, str], int] = {}
        for indice, linha in enumerate(linhas, start=1):
            if linha.papel != PAPEL_PRINCIPAL:
                continue
            for campo, valor in self._chaves(linha):
                anterior = vistas.get((campo, valor))
                if anterior is not None:
                    raise ReferenciaJaUsadaError(
                        f"As linhas {anterior} e {indice} são as duas principais "
                        f"com a mesma referência ({valor}). Uma delas tem de ser "
                        "secundária ou levar outra referência."
                    )
                vistas[(campo, valor)] = indice

    @staticmethod
    def _chaves(dados: ComponenteDados):
        from app.domain.materia_prima_types import normalizar_ref_fornecedor

        for campo, valor in (
            ("nome_imos", (dados.nome_imos or "").strip()),
            ("ref_phc", (dados.ref_phc or "").strip()),
            ("ref_fornecedor", normalizar_ref_fornecedor(dados.ref_fornecedor) or ""),
        ):
            if valor:
                yield campo, valor

    def _tem_chave(self, dados: ComponenteDados) -> bool:
        return any(True for _ in self._chaves(dados))

    def _utilizador_atual_id(self) -> int | None:
        """Id de quem está a usar a app, ou None nos scripts."""
        return getattr(app_session.current_user, "id", None)
