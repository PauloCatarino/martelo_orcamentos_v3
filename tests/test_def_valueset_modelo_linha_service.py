"""Tests for the DefValuesetModeloLinha service."""

from __future__ import annotations

from decimal import Decimal

from app.repositories.def_valueset_modelo_linha_repository import DefValuesetModeloLinhaResumo
from app.services import def_valueset_modelo_linha_service as service_module


def _resumo(**kwargs) -> DefValuesetModeloLinhaResumo:
    base = {
        "id": 1,
        "def_valueset_modelo_id": 10,
        "chave": "FERRAGEM_DOBRADICA",
        "codigo_opcao": "FERRAGEM_DOBRADICA",
        "nome_opcao": None,
        "padrao": False,
        "ordem": 1,
        "descricao": None,
        "materia_prima_id": None,
        "ref_materia_prima": None,
        "descricao_materia_prima": None,
        "valor_texto": None,
        "origem": None,
        "ref_le": None,
        "descricao_no_orcamento": None,
        "preco_tabela": None,
        "margem_percentagem": None,
        "desconto_percentagem": None,
        "preco_liquido": None,
        "unidade": None,
        "desperdicio_percentagem": None,
        "tipo_materia_prima": None,
        "familia_materia_prima": None,
        "coresp_orla_0_4": None,
        "coresp_orla_1_0": None,
        "comp_mp": None,
        "larg_mp": None,
        "esp_mp": None,
        "origem_dados": None,
        "editado_localmente": False,
        "ativo": True,
        "observacoes": None,
    }
    base.update(kwargs)
    return DefValuesetModeloLinhaResumo(**base)


class _FakeRepository:
    rows: list[DefValuesetModeloLinhaResumo] = []
    opcao_existing: DefValuesetModeloLinhaResumo | None = None
    default_existing: DefValuesetModeloLinhaResumo | None = None
    by_id: DefValuesetModeloLinhaResumo | None = None
    created_payload: dict | None = None
    updated_payload: dict | None = None
    set_padrao_calls: list = []
    clear_calls: list = []
    deactivate_result = True
    activate_result = True

    def __init__(self, _session: object) -> None:
        pass

    def list_all(self):
        return self.rows

    def list_active(self):
        return self.rows

    def list_by_modelo(self, modelo_id: int):
        return self.rows

    def list_by_modelo_chave(self, modelo_id: int, chave: str):
        return self.rows

    def get_by_id(self, id: int):
        return self.by_id if self.by_id is not None else _resumo(id=id)

    def get_by_modelo_chave(self, modelo_id: int, chave: str):
        return None

    def get_by_modelo_chave_opcao(self, modelo_id: int, chave: str, codigo_opcao: str):
        return self.opcao_existing

    def get_default_by_modelo_chave(self, modelo_id: int, chave: str):
        return self.default_existing

    def create(self, **fields):
        self.__class__.created_payload = fields
        return _resumo(id=1, **fields)

    def update(self, *, id: int, **fields):
        self.__class__.updated_payload = {"id": id, **fields}
        return _resumo(id=id, **fields)

    def deactivate(self, id: int) -> bool:
        return self.deactivate_result

    def activate(self, id: int) -> bool:
        return self.activate_result

    def set_padrao(self, id: int, padrao: bool) -> bool:
        self.__class__.set_padrao_calls.append((id, padrao))
        return True

    def clear_padrao_for_chave(self, modelo_id: int, chave: str, exclude_id=None) -> None:
        self.__class__.clear_calls.append((modelo_id, chave, exclude_id))


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


def _reset() -> None:
    _FakeRepository.rows = []
    _FakeRepository.opcao_existing = None
    _FakeRepository.default_existing = None
    _FakeRepository.by_id = None
    _FakeRepository.created_payload = None
    _FakeRepository.updated_payload = None
    _FakeRepository.set_padrao_calls = []
    _FakeRepository.clear_calls = []
    _FakeRepository.deactivate_result = True
    _FakeRepository.activate_result = True


def _service(monkeypatch):
    _reset()
    monkeypatch.setattr(service_module, "DefValuesetModeloLinhaRepository", _FakeRepository)
    session = _FakeSession()
    return service_module.DefValuesetModeloLinhaService(session=session), session


def test_criar_linha_normaliza_chave_e_opcao_defaults(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    service.criar_linha(
        service_module.CriarDefValuesetModeloLinhaData(
            def_valueset_modelo_id=10,
            chave=" ferragem_dobradica ",
        )
    )

    payload = _FakeRepository.created_payload
    assert payload is not None
    assert payload["chave"] == "FERRAGEM_DOBRADICA"
    assert payload["codigo_opcao"] == "FERRAGEM_DOBRADICA"
    assert payload["padrao"] is False
    assert payload["ordem"] == 1
    assert session.committed is True


def test_criar_linha_normaliza_codigo_opcao(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.criar_linha(
        service_module.CriarDefValuesetModeloLinhaData(
            def_valueset_modelo_id=10,
            chave="FERRAGEM_DOBRADICA",
            codigo_opcao=" blum_reta ",
            nome_opcao="Blum dobradiça reta",
        )
    )

    assert _FakeRepository.created_payload["codigo_opcao"] == "BLUM_RETA"
    assert _FakeRepository.created_payload["nome_opcao"] == "Blum dobradiça reta"


def test_criar_linha_valida_chave_obrigatoria(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    try:
        service.criar_linha(
            service_module.CriarDefValuesetModeloLinhaData(
                def_valueset_modelo_id=10,
                chave=" ",
            )
        )
    except ValueError as error:
        assert "chave" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_varias_opcoes_mesma_chave_permitidas(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.opcao_existing = None

    service.criar_linha(
        service_module.CriarDefValuesetModeloLinhaData(
            def_valueset_modelo_id=10,
            chave="FERRAGEM_DOBRADICA",
            codigo_opcao="EMUCA_RETA",
        )
    )

    assert _FakeRepository.created_payload["codigo_opcao"] == "EMUCA_RETA"
    assert session.committed is True


def test_duplicar_chave_e_opcao_recusada(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.opcao_existing = _resumo(id=2, codigo_opcao="BLUM_RETA")

    try:
        service.criar_linha(
            service_module.CriarDefValuesetModeloLinhaData(
                def_valueset_modelo_id=10,
                chave="FERRAGEM_DOBRADICA",
                codigo_opcao="BLUM_RETA",
            )
        )
    except ValueError as error:
        assert "opcao" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_criar_linha_com_prioridade(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    service.criar_linha(
        service_module.CriarDefValuesetModeloLinhaData(
            def_valueset_modelo_id=10,
            chave="FERRAGEM_DOBRADICA",
            codigo_opcao="BLUM_RETA",
            prioridade=2,
        )
    )

    assert _FakeRepository.created_payload["prioridade"] == 2
    assert session.committed is True


def test_criar_linha_prioridade_vazia_fica_none(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.criar_linha(
        service_module.CriarDefValuesetModeloLinhaData(
            def_valueset_modelo_id=10,
            chave="FERRAGEM_DOBRADICA",
            codigo_opcao="BLUM_RETA",
        )
    )

    assert _FakeRepository.created_payload["prioridade"] is None


def test_criar_linha_prioridade_invalida_recusada(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    try:
        service.criar_linha(
            service_module.CriarDefValuesetModeloLinhaData(
                def_valueset_modelo_id=10,
                chave="FERRAGEM_DOBRADICA",
                codigo_opcao="BLUM_RETA",
                prioridade=0,
            )
        )
    except ValueError as error:
        assert "prioridade" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_prioridades_repetidas_permitidas(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.default_existing = _resumo(
        id=5, prioridade=1, codigo_opcao="BLUM_RETA"
    )

    service.criar_linha(
        service_module.CriarDefValuesetModeloLinhaData(
            def_valueset_modelo_id=10,
            chave="FERRAGEM_DOBRADICA",
            codigo_opcao="EMUCA_RETA",
            prioridade=1,
        )
    )

    assert _FakeRepository.created_payload["prioridade"] == 1
    assert session.committed is True


def test_obter_padrao_por_chave(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.default_existing = _resumo(id=7, padrao=True, codigo_opcao="BLUM_RETA")

    result = service.obter_padrao_por_chave(10, "ferragem_dobradica")

    assert result is not None
    assert result.id == 7


def test_listar_por_chave(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.rows = [
        _resumo(id=1, codigo_opcao="BLUM_RETA"),
        _resumo(id=2, codigo_opcao="EMUCA_RETA"),
    ]

    result = service.listar_por_chave(10, "FERRAGEM_DOBRADICA")

    assert len(result) == 2


def test_definir_como_padrao(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.by_id = _resumo(
        id=5, def_valueset_modelo_id=10, chave="FERRAGEM_DOBRADICA", codigo_opcao="EMUCA_RETA"
    )

    assert service.definir_como_padrao(5) is True
    assert (10, "FERRAGEM_DOBRADICA", 5) in _FakeRepository.clear_calls
    assert (5, True) in _FakeRepository.set_padrao_calls
    assert session.committed is True


def test_editar_linha_permite_a_propria_opcao(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.by_id = _resumo(id=7, codigo_opcao="BLUM_RETA")
    _FakeRepository.opcao_existing = _resumo(id=7, codigo_opcao="BLUM_RETA")

    service.editar_linha(
        7,
        service_module.EditarDefValuesetModeloLinhaData(
            def_valueset_modelo_id=10,
            chave="FERRAGEM_DOBRADICA",
            codigo_opcao="BLUM_RETA",
            valor_texto="dobradica default",
        ),
    )

    assert _FakeRepository.updated_payload is not None
    assert _FakeRepository.updated_payload["id"] == 7
    assert _FakeRepository.updated_payload["codigo_opcao"] == "BLUM_RETA"
    assert session.committed is True


def test_calcula_preco_liquido(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.criar_linha(
        service_module.CriarDefValuesetModeloLinhaData(
            def_valueset_modelo_id=10,
            chave="MATERIAL_PORTAS",
            codigo_opcao="MDF_19",
            preco_tabela=Decimal("10"),
            margem_percentagem=Decimal("15"),
            desconto_percentagem=Decimal("10"),
        )
    )

    assert _FakeRepository.created_payload["preco_liquido"] == Decimal("10.35")


def test_calcula_preco_liquido_percentagens_humanas(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.criar_linha(
        service_module.CriarDefValuesetModeloLinhaData(
            def_valueset_modelo_id=10,
            chave="MATERIAL_PORTAS",
            codigo_opcao="X",
            preco_tabela=Decimal("10"),
            margem_percentagem=Decimal("10"),
            desconto_percentagem=Decimal("32"),
        )
    )

    assert _FakeRepository.created_payload["preco_liquido"] == Decimal("7.48")


def test_calcula_preco_liquido_8_62(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.criar_linha(
        service_module.CriarDefValuesetModeloLinhaData(
            def_valueset_modelo_id=10,
            chave="MATERIAL_PORTAS",
            codigo_opcao="X",
            preco_tabela=Decimal("8.62"),
            margem_percentagem=Decimal("5"),
            desconto_percentagem=Decimal("36"),
        )
    )

    assert _FakeRepository.created_payload["preco_liquido"] == Decimal("5.79264")


def test_recalcula_ignorando_preco_liquido_fornecido(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.criar_linha(
        service_module.CriarDefValuesetModeloLinhaData(
            def_valueset_modelo_id=10,
            chave="MATERIAL_PORTAS",
            codigo_opcao="X",
            preco_tabela=Decimal("10"),
            margem_percentagem=Decimal("10"),
            desconto_percentagem=Decimal("32"),
            preco_liquido=Decimal("99"),
        )
    )

    assert _FakeRepository.created_payload["preco_liquido"] == Decimal("7.48")


def test_preco_liquido_campos_vazios_usam_zero(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.criar_linha(
        service_module.CriarDefValuesetModeloLinhaData(
            def_valueset_modelo_id=10,
            chave="MATERIAL_PORTAS",
            codigo_opcao="X",
            preco_tabela=Decimal("10"),
        )
    )

    assert _FakeRepository.created_payload["preco_liquido"] == Decimal("10")


def test_preco_tabela_none_mantem_preco_liquido(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.criar_linha(
        service_module.CriarDefValuesetModeloLinhaData(
            def_valueset_modelo_id=10,
            chave="MATERIAL_PORTAS",
            codigo_opcao="MDF_19",
            preco_liquido=Decimal("99"),
        )
    )

    assert _FakeRepository.created_payload["preco_liquido"] == Decimal("99")


def test_atualizar_precos_linhas_so_toca_preco_tabela_e_liquido(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    atualizadas = service.atualizar_precos_linhas(
        [(5, Decimal("12.50"), Decimal("11.25"))]
    )

    assert atualizadas == 1
    assert _FakeRepository.updated_payload == {
        "id": 5,
        "preco_tabela": Decimal("12.50"),
        "preco_liquido": Decimal("11.25"),
    }
    assert "editado_localmente" not in _FakeRepository.updated_payload
    assert session.committed is True


def test_editado_localmente_default_false() -> None:
    data = service_module.CriarDefValuesetModeloLinhaData(
        def_valueset_modelo_id=10, chave="MATERIAL_PORTAS"
    )

    assert data.editado_localmente is False


def test_origem_dados_aceita_texto(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    for origem in ("LIVRE", "MATERIA_PRIMA", "EDITADO_LOCALMENTE"):
        service.criar_linha(
            service_module.CriarDefValuesetModeloLinhaData(
                def_valueset_modelo_id=10,
                chave="MATERIAL_PORTAS",
                codigo_opcao=f"OP_{origem}",
                origem_dados=origem,
            )
        )

        assert _FakeRepository.created_payload["origem_dados"] == origem


def test_criar_opcao_livre_gera_identidade_tecnica_a_partir_do_nome(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.criar_linha(
        service_module.CriarDefValuesetModeloLinhaData(
            def_valueset_modelo_id=10,
            chave="MATERIAL_PORTAS",
            nome_opcao="MDF branco 19mm",
        )
    )

    assert _FakeRepository.created_payload["codigo_opcao"] == "OP_MDF_BRANCO_19MM"
    assert _FakeRepository.created_payload["nome_opcao"] == "MDF branco 19mm"
