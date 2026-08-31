"""Tests for the DefMateriaPrima service."""

from __future__ import annotations

from decimal import Decimal

from app.repositories.def_materia_prima_repository import DefMateriaPrimaResumo
from app.services import def_materia_prima_service as service_module


def _resumo(**kwargs) -> DefMateriaPrimaResumo:
    base = {
        "id": 1,
        "ref_le": None,
        "referencia_fornecedor": None,
        "descricao": "Material",
        "tipo_original_excel": None,
        "familia_original_excel": None,
        "tipo_martelo": None,
        "familia_martelo": None,
        "unidade": None,
        "preco_tabela": None,
        "desconto": None,
        "margem": None,
        "preco_liquido": None,
        "comprimento": None,
        "largura": None,
        "espessura": None,
        "fornecedor": None,
        "origem_dados": "EXCEL",
        "ativo": True,
        "observacoes": None,
    }
    base.update(kwargs)
    return DefMateriaPrimaResumo(**base)


def _campos_do_resumo(kwargs: dict) -> dict:
    """Só os campos que o read model conhece.

    O repositório recebe mais coisas do que o resumo devolve (por exemplo
    ``criado_por_id``), e o duplo de teste tem de deixar essas passar ao lado.
    """
    conhecidos = set(DefMateriaPrimaResumo.__dataclass_fields__)
    return {
        chave: valor for chave, valor in kwargs.items() if chave in conhecidos
    }


class _FakeRepository:
    all_rows: list[DefMateriaPrimaResumo] = []
    active_rows: list[DefMateriaPrimaResumo] = []
    search_rows: list[DefMateriaPrimaResumo] = []
    requested_termo: str | None = None
    requested_limite: int | None = None
    by_ref_le: DefMateriaPrimaResumo | None = None
    by_id: DefMateriaPrimaResumo | None = None
    requested_ref_le: str | None = None
    created_payload: dict | None = None
    updated_payload: dict | None = None
    deactivate_result = True
    deactivated_id: int | None = None
    ativo_definido: bool | None = None
    ultimo_numero: int = 0
    prefixo_pedido: str | None = None
    precos_registados: list = []
    historico_existente: bool = False

    def __init__(self, _session: object) -> None:
        pass

    def list_all(self) -> list[DefMateriaPrimaResumo]:
        return self.all_rows

    def list_active(self) -> list[DefMateriaPrimaResumo]:
        return self.active_rows

    def get_by_id(self, id: int) -> DefMateriaPrimaResumo | None:
        return self.by_id

    def get_by_ref_le(self, ref_le: str) -> DefMateriaPrimaResumo | None:
        self.__class__.requested_ref_le = ref_le
        return self.by_ref_le

    def pesquisar(self, termo=None, limite=200) -> list[DefMateriaPrimaResumo]:
        self.__class__.requested_termo = termo
        self.__class__.requested_limite = limite
        return self.search_rows

    def create_materia_prima(self, **kwargs) -> DefMateriaPrimaResumo:
        self.__class__.created_payload = kwargs
        return _resumo(id=1, **_campos_do_resumo(kwargs))

    def update_materia_prima(self, **kwargs) -> DefMateriaPrimaResumo:
        self.__class__.updated_payload = kwargs
        return _resumo(**_campos_do_resumo(kwargs))

    def deactivate_materia_prima(self, id: int) -> bool:
        self.__class__.deactivated_id = id
        return self.deactivate_result

    def definir_ativo(self, id: int, *, ativo: bool, alterado_por_id=None) -> bool:
        self.__class__.deactivated_id = id
        self.__class__.ativo_definido = ativo
        return self.deactivate_result

    def ultimo_numero_ref_le(self, prefixo: str) -> int:
        self.__class__.prefixo_pedido = prefixo
        return self.ultimo_numero

    def registar_preco(self, **kwargs) -> None:
        self.__class__.precos_registados = [*self.precos_registados, kwargs]

    def tem_historico_precos(self, materia_prima_id: int) -> bool:
        return self.historico_existente

    def historico_precos(self, materia_prima_id: int, limite: int = 50) -> list:
        return []

    def contar_utilizacoes(self, materia_prima_id: int) -> int:
        return 0


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


def _reset() -> None:
    _FakeRepository.search_rows = []
    _FakeRepository.requested_termo = None
    _FakeRepository.requested_limite = None
    _FakeRepository.by_ref_le = None
    _FakeRepository.by_id = None
    _FakeRepository.requested_ref_le = None
    _FakeRepository.created_payload = None
    _FakeRepository.updated_payload = None
    _FakeRepository.deactivate_result = True
    _FakeRepository.deactivated_id = None
    _FakeRepository.ativo_definido = None
    _FakeRepository.ultimo_numero = 0
    _FakeRepository.prefixo_pedido = None
    _FakeRepository.precos_registados = []
    _FakeRepository.historico_existente = False


def _service(monkeypatch):
    _reset()
    monkeypatch.setattr(service_module, "DefMateriaPrimaRepository", _FakeRepository)
    session = _FakeSession()
    return service_module.DefMateriaPrimaService(session=session), session


def test_listar_materias_primas(monkeypatch) -> None:
    _FakeRepository.all_rows = [_resumo(id=3)]
    service, _ = _service(monkeypatch)

    assert service.listar_materias_primas() == [_resumo(id=3)]


def test_pesquisar_termo_vazio(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.search_rows = [_resumo(id=1)]

    result = service.pesquisar("")

    assert result == [_resumo(id=1)]
    assert _FakeRepository.requested_termo == ""


def test_pesquisar_com_texto(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.search_rows = [_resumo(id=2, descricao="AGL 19MM")]

    result = service.pesquisar("agl")

    assert result == [_resumo(id=2, descricao="AGL 19MM")]
    assert _FakeRepository.requested_termo == "agl"


def test_pesquisar_sem_resultados(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.search_rows = []

    assert service.pesquisar("inexistente") == []


def test_listar_materias_primas_ativas(monkeypatch) -> None:
    _FakeRepository.active_rows = [_resumo(id=4, ativo=True)]
    service, _ = _service(monkeypatch)

    assert service.listar_materias_primas_ativas() == [_resumo(id=4, ativo=True)]


def test_criar_normaliza_descricao_ref_le_e_origem(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    result = service.criar_materia_prima(
        service_module.CriarDefMateriaPrimaData(
            descricao="  AGL 19MM  ",
            ref_le="  PLC0001  ",
            preco_tabela=Decimal("24.87"),
            preco_liquido=None,
        )
    )

    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["descricao"] == "AGL 19MM"
    assert _FakeRepository.created_payload["ref_le"] == "PLC0001"
    # Sem origem indicada, o material nasceu no proprio V3 (o Excel deixou de
    # ser o dono do catalogo e tem de ser dito expressamente).
    assert _FakeRepository.created_payload["origem_dados"] == "V3"
    assert _FakeRepository.created_payload["preco_tabela"] == Decimal("24.87")
    assert _FakeRepository.created_payload["preco_liquido"] is None
    assert result.descricao == "AGL 19MM"
    assert session.committed is True


def test_criar_copia_correspondencias_de_orla(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    result = service.criar_materia_prima(
        service_module.CriarDefMateriaPrimaData(
            descricao="Material frentes",
            ref_le="PLC0033",
            coresp_orla_0_4="ORL0002",
            coresp_orla_1_0="ORL0003",
        )
    )

    assert _FakeRepository.created_payload["coresp_orla_0_4"] == "ORL0002"
    assert _FakeRepository.created_payload["coresp_orla_1_0"] == "ORL0003"
    assert result.coresp_orla_0_4 == "ORL0002"
    assert result.coresp_orla_1_0 == "ORL0003"


def test_criar_copia_desperdicio(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    result = service.criar_materia_prima(
        service_module.CriarDefMateriaPrimaData(
            descricao="Material",
            ref_le="PLC0001",
            desperdicio_percentagem=Decimal("0.15"),
        )
    )

    assert _FakeRepository.created_payload["desperdicio_percentagem"] == Decimal("0.15")
    assert result.desperdicio_percentagem == Decimal("0.15")


def test_criar_descricao_obrigatoria(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    try:
        service.criar_materia_prima(
            service_module.CriarDefMateriaPrimaData(descricao="   ")
        )
    except ValueError as error:
        assert "descricao" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_criar_ref_le_vazia_fica_none(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.criar_materia_prima(
        service_module.CriarDefMateriaPrimaData(descricao="Material", ref_le="   ")
    )

    assert _FakeRepository.created_payload["ref_le"] is None


def test_criar_origem_dados_personalizada(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.criar_materia_prima(
        service_module.CriarDefMateriaPrimaData(descricao="Material", origem_dados=" MANUAL ")
    )

    assert _FakeRepository.created_payload["origem_dados"] == "MANUAL"


def test_criar_ref_le_duplicada(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.by_ref_le = _resumo(id=99, ref_le="PLC0001")

    try:
        service.criar_materia_prima(
            service_module.CriarDefMateriaPrimaData(descricao="Material", ref_le="PLC0001")
        )
    except ValueError as error:
        assert "ref_le" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_editar_permite_mesma_ref_le_do_proprio_registo(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.by_ref_le = _resumo(id=5, ref_le="PLC0001")

    service.editar_materia_prima(
        5,
        service_module.EditarDefMateriaPrimaData(descricao="Material", ref_le="PLC0001"),
    )

    assert _FakeRepository.updated_payload is not None
    assert _FakeRepository.updated_payload["id"] == 5
    assert session.committed is True


def test_editar_atualiza_orlas_e_desperdicio(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.by_ref_le = _resumo(id=5, ref_le="PLC0033")

    result = service.editar_materia_prima(
        5,
        service_module.EditarDefMateriaPrimaData(
            descricao="Material frentes",
            ref_le="PLC0033",
            desperdicio_percentagem=Decimal("0.15"),
            coresp_orla_0_4="ORL0002",
            coresp_orla_1_0="ORL0003",
        ),
    )

    payload = _FakeRepository.updated_payload
    assert payload["desperdicio_percentagem"] == Decimal("0.15")
    assert payload["coresp_orla_0_4"] == "ORL0002"
    assert payload["coresp_orla_1_0"] == "ORL0003"
    assert result.desperdicio_percentagem == Decimal("0.15")
    assert result.coresp_orla_0_4 == "ORL0002"
    assert result.coresp_orla_1_0 == "ORL0003"
    assert session.committed is True


def test_editar_ref_le_de_outro_registo_falha(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.by_ref_le = _resumo(id=5, ref_le="PLC0001")

    try:
        service.editar_materia_prima(
            7,
            service_module.EditarDefMateriaPrimaData(descricao="Material", ref_le="PLC0001"),
        )
    except ValueError as error:
        assert "ref_le" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_obter_por_ref_le_normaliza(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.by_ref_le = _resumo(id=8, ref_le="PLC0001")

    result = service.obter_por_ref_le("  PLC0001  ")

    assert _FakeRepository.requested_ref_le == "PLC0001"
    assert result.id == 8


def test_obter_por_ref_le_vazia_devolve_none(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    assert service.obter_por_ref_le("   ") is None


def test_desativar_existente(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.deactivate_result = True

    assert service.desativar_materia_prima(10) is True
    assert _FakeRepository.deactivated_id == 10
    assert session.committed is True


def test_desativar_inexistente_sem_commit(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.deactivate_result = False

    assert service.desativar_materia_prima(11) is False
    assert _FakeRepository.deactivated_id == 11
    assert session.committed is False


# ----- Histórico: o preço antigo não se pode perder -----
#
# O catálogo entrou quase todo pela importação inicial, fora da aplicação, e
# esses materiais ficaram sem linha nenhuma no histórico. A primeira alteração
# de preço escrevia só a linha NOVA: o preço que lá estava antes desaparecia e
# a coluna "Variação" ficava com um travessão. Foi o que o Paulo apanhou no
# PLC0051 a 31-08-2026.


def test_primeira_alteracao_de_preco_guarda_o_preco_de_partida(monkeypatch) -> None:
    service, _session = _service(monkeypatch)
    _FakeRepository.by_id = _resumo(
        id=5,
        ref_le="PLC0051",
        preco_tabela=Decimal("20.36"),
        margem=Decimal("10"),
        preco_liquido=Decimal("22.40"),
        origem_dados="EXCEL",
    )
    _FakeRepository.historico_existente = False

    service.editar_materia_prima(
        5,
        service_module.EditarDefMateriaPrimaData(
            descricao="Material",
            ref_le="PLC0051",
            preco_tabela=Decimal("21.36"),
            margem=Decimal("10"),
            preco_liquido=Decimal("23.50"),
        ),
    )

    registados = _FakeRepository.precos_registados
    assert len(registados) == 2, "faltou a linha de partida com o preço antigo"

    partida, nova = registados
    assert partida["preco_tabela"] == Decimal("20.36")
    assert partida["preco_liquido"] == Decimal("22.40")
    assert partida["origem"] == "EXCEL"
    assert partida["user_id"] is None  # não foi ninguém pela aplicação
    assert "partida" in (partida["observacoes"] or "").lower()

    assert nova["preco_tabela"] == Decimal("21.36")
    assert nova["preco_liquido"] == Decimal("23.50")


def test_alteracao_seguinte_nao_repete_a_linha_de_partida(monkeypatch) -> None:
    service, _session = _service(monkeypatch)
    _FakeRepository.by_id = _resumo(
        id=5, ref_le="PLC0051", preco_tabela=Decimal("21.36")
    )
    _FakeRepository.historico_existente = True  # já tem passado guardado

    service.editar_materia_prima(
        5,
        service_module.EditarDefMateriaPrimaData(
            descricao="Material", ref_le="PLC0051", preco_tabela=Decimal("22.00")
        ),
    )

    registados = _FakeRepository.precos_registados
    assert len(registados) == 1
    assert registados[0]["preco_tabela"] == Decimal("22.00")


def test_editar_sem_mexer_no_preco_nao_escreve_historico(monkeypatch) -> None:
    service, _session = _service(monkeypatch)
    _FakeRepository.by_id = _resumo(
        id=5, ref_le="PLC0051", preco_tabela=Decimal("21.36")
    )

    service.editar_materia_prima(
        5,
        service_module.EditarDefMateriaPrimaData(
            descricao="Descrição nova", ref_le="PLC0051",
            preco_tabela=Decimal("21.36"),
        ),
    )

    assert _FakeRepository.precos_registados == []


def test_material_sem_preco_nenhum_nao_ganha_linha_de_partida(monkeypatch) -> None:
    service, _session = _service(monkeypatch)
    _FakeRepository.by_id = _resumo(id=5, ref_le="PLC0051")  # tudo a None

    service.editar_materia_prima(
        5,
        service_module.EditarDefMateriaPrimaData(
            descricao="Material", ref_le="PLC0051", preco_tabela=Decimal("9.99")
        ),
    )

    registados = _FakeRepository.precos_registados
    assert len(registados) == 1  # só a linha nova; não havia preço de partida
    assert registados[0]["preco_tabela"] == Decimal("9.99")
