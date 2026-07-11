"""Tests for importing a saved module into an item costing (phase 8U.2)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.db.base import Base
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import OrcamentoItem, OrcamentoItemValuesetLinha
from app.repositories.def_peca_componente_repository import DefPecaComponenteRepository
from app.repositories.def_peca_repository import DefPecaRepository
from app.repositories.def_regra_quantidade_repository import (
    DefRegraQuantidadeRepository,
)
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaRepository,
)
from app.services.def_modulo_service import (
    CriarDefModuloData,
    CriarDefModuloLinhaData,
    DefModuloService,
)
from app.services.orcamento_item_custeio_linha_service import (
    OrcamentoItemCusteioLinhaService,
)


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_, compiler, **kw):  # noqa: ANN001
    return "INTEGER"


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _criar_item(session, *, altura="2000", largura="1000", profundidade="500") -> int:
    item = OrcamentoItem(
        orcamento_versao_id=1,
        ordem=1,
        tipo_item="OUTRO",
        item="Item de teste",
        quantidade=Decimal("1"),
        altura=Decimal(altura),
        largura=Decimal(largura),
        profundidade=Decimal(profundidade),
    )
    session.add(item)
    session.flush()
    return item.id


def _criar_valueset_laterais(session, item_id: int) -> None:
    """Default M2 material option for the MATERIAL_LATERAIS key on the item."""
    _criar_valueset_chave(session, item_id, "MATERIAL_LATERAIS")


def _criar_valueset_chave(session, item_id: int, chave: str) -> None:
    """Default M2 material option for a given material key on the item."""
    linha = OrcamentoItemValuesetLinha(
        orcamento_item_id=item_id,
        chave=chave,
        codigo_opcao="AGL_19",
        nome_opcao="AGL 19mm",
        padrao=True,
        ordem=1,
        materia_prima_id=5,
        ref_materia_prima="MP01",
        descricao_materia_prima="AGL Linho",
        ref_le="LE01",
        descricao_no_orcamento="AGL Linho Cancun",
        preco_liquido=Decimal("5.79"),
        unidade="m2",
        desperdicio_percentagem=Decimal("5"),
        tipo_materia_prima="PLACA",
        familia_materia_prima="AGLOMERADO",
        comp_mp=Decimal("2750"),
        larg_mp=Decimal("1830"),
        esp_mp=Decimal("19"),
        ativo=True,
    )
    session.add(linha)
    session.flush()


def _criar_pecas(session) -> tuple[int, int]:
    """Create a simple piece (LATERAL) and a composite (GAVETA) with one component."""
    peca_repo = DefPecaRepository(session)
    componente_repo = DefPecaComponenteRepository(session)

    lateral = peca_repo.create_def_peca(
        codigo="LATERAL", nome="Lateral", descricao=None, grupo="LATERAIS",
        tipo_peca="SIMPLES", chave_valueset_material="MATERIAL_LATERAIS",
    )
    corredica = peca_repo.create_def_peca(
        codigo="CORREDICA", nome="Corrediça", descricao=None, grupo="FERRAGENS",
        tipo_peca="SIMPLES", chave_valueset_material=None,
    )
    gaveta = peca_repo.create_def_peca(
        codigo="GAVETA", nome="Gaveta", descricao=None, grupo="GAVETAS",
        tipo_peca="COMPOSTA",
    )
    componente_repo.create_componente(
        def_peca_pai_id=gaveta.id,
        tipo_componente="FERRAGEM",
        def_peca_componente_id=corredica.id,
        referencia_componente="CORREDICA",
        descricao="Corrediça",
        ordem=1,
        quantidade=Decimal("2"),
        regra_quantidade="FIXA",
        obrigatorio=True,
        ativo=True,
        observacoes=None,
    )
    session.flush()
    return lateral.id, gaveta.id


def _criar_modulo_roupeiro(session, lateral_id: int, gaveta_id: int) -> int:
    """Module: division + simple LATERAL + composite GAVETA (structure only)."""
    com_linhas = DefModuloService(session).criar(
        CriarDefModuloData(
            codigo="ROUP_2P", nome="Roupeiro 2 portas", user_id=7,
            categoria="ROUPEIROS",
            linhas=[
                CriarDefModuloLinhaData(
                    ordem=1, tipo_linha="DIVISAO_INDEPENDENTE", qt_mod="1",
                    descricao_livre="Corpo", comp="H", larg="L", esp="P",
                ),
                CriarDefModuloLinhaData(
                    ordem=2, tipo_linha="PECA", def_peca_id=lateral_id,
                    def_peca_codigo="LATERAL", comp="H", larg="P", esp="19",
                    chave_valueset="MATERIAL_LATERAIS", qt_und="2",
                ),
                CriarDefModuloLinhaData(
                    ordem=3, tipo_linha="PECA_COMPOSTA", def_peca_id=gaveta_id,
                    def_peca_codigo="GAVETA", descricao="Gaveta", qt_und="1",
                ),
            ],
        )
    )
    return com_linhas.modulo.id


def test_importar_modulo_cria_linhas_reexpande_composta(session) -> None:
    item_id = _criar_item(session)
    _criar_valueset_laterais(session, item_id)
    lateral_id, gaveta_id = _criar_pecas(session)
    modulo_id = _criar_modulo_roupeiro(session, lateral_id, gaveta_id)
    session.commit()

    service = OrcamentoItemCusteioLinhaService(session)
    resultado = service.inserir_modulo_no_item(item_id, modulo_id)

    assert resultado.modulo_codigo == "ROUP_2P"
    assert resultado.criadas == 3  # division + lateral + composite header
    assert resultado.componentes == 1  # the composite re-expanded its component

    linhas = OrcamentoItemCusteioLinhaRepository(session).list_active_by_orcamento_item(
        item_id
    )
    assert [l.tipo_linha for l in linhas] == [
        "DIVISAO_INDEPENDENTE",
        "PECA",
        "PECA_COMPOSTA",
        "FERRAGEM",
    ]
    # The re-expanded component hangs from the composite header.
    cabecalho = next(l for l in linhas if l.tipo_linha == "PECA_COMPOSTA")
    componente = next(l for l in linhas if l.tipo_linha == "FERRAGEM")
    assert componente.linha_pai_id == cabecalho.id
    assert componente.nivel == 1

    # The simple piece kept the module STRUCTURE (formulas/qt as text) and got
    # its MATERIAL resolved from the item ValueSet (not from the module).
    lateral = next(l for l in linhas if l.tipo_linha == "PECA")
    assert lateral.comp == "H"
    assert lateral.larg == "P"
    assert lateral.esp == "19"
    assert lateral.qt_und == Decimal("2")
    assert lateral.chave_valueset == "MATERIAL_LATERAIS"
    assert lateral.preco_liquido == Decimal("5.79")
    assert lateral.unidade == "m2"


def test_importar_modulo_resolve_material_pela_prioridade_exata(session) -> None:
    item_id = _criar_item(session)
    for prioridade, codigo, ref in (
        (1, "LINHO", "LE01"),
        (2, "BRANCO", "LE02"),
    ):
        session.add(
            OrcamentoItemValuesetLinha(
                orcamento_item_id=item_id,
                chave="MATERIAL_LATERAIS",
                codigo_opcao=codigo,
                nome_opcao=codigo,
                prioridade=prioridade,
                padrao=prioridade == 1,
                ordem=prioridade,
                materia_prima_id=prioridade,
                ref_materia_prima=ref,
                descricao_materia_prima=codigo,
                ref_le=ref,
                descricao_no_orcamento=codigo,
                preco_liquido=Decimal("5"),
                unidade="m2",
                desperdicio_percentagem=Decimal("5"),
                esp_mp=Decimal("19"),
                ativo=True,
            )
        )
    lateral_id, _gaveta_id = _criar_pecas(session)
    modulo = DefModuloService(session).criar(
        CriarDefModuloData(
            codigo="COZINHA_P2",
            nome="Cozinha prioridade 2",
            user_id=7,
            linhas=[
                CriarDefModuloLinhaData(
                    ordem=1,
                    def_peca_id=lateral_id,
                    def_peca_codigo="LATERAL",
                    chave_valueset="MATERIAL_LATERAIS",
                    prioridade_valueset=2,
                )
            ],
        )
    )

    OrcamentoItemCusteioLinhaService(session).inserir_modulo_no_item(
        item_id, modulo.modulo.id
    )
    linha = OrcamentoItemCusteioLinhaRepository(
        session
    ).list_active_by_orcamento_item(item_id)[0]
    assert linha.mat_default == "BRANCO"
    assert linha.ref_le == "LE02"


def test_importar_modulo_prioridade_inexistente_nao_faz_fallback(session) -> None:
    item_id = _criar_item(session)
    _criar_valueset_laterais(session, item_id)
    lateral_id, _gaveta_id = _criar_pecas(session)
    modulo = DefModuloService(session).criar(
        CriarDefModuloData(
            codigo="SEM_P2",
            nome="Sem prioridade 2",
            user_id=7,
            linhas=[
                CriarDefModuloLinhaData(
                    ordem=1,
                    def_peca_id=lateral_id,
                    def_peca_codigo="LATERAL",
                    chave_valueset="MATERIAL_LATERAIS",
                    prioridade_valueset=2,
                )
            ],
        )
    )

    resultado = OrcamentoItemCusteioLinhaService(session).inserir_modulo_no_item(
        item_id, modulo.modulo.id
    )
    linha = OrcamentoItemCusteioLinhaRepository(
        session
    ).list_active_by_orcamento_item(item_id)[0]
    assert linha.mat_default is None
    assert linha.ref_le is None
    assert "Prioridade ValueSet 2 não configurada" in linha.observacoes
    assert any("Prioridade ValueSet 2 não configurada" in aviso for aviso in resultado.avisos)


def test_importar_modulo_grava_imagem_na_primeira_linha(session) -> None:
    item_id = _criar_item(session)
    _criar_valueset_laterais(session, item_id)
    lateral_id, gaveta_id = _criar_pecas(session)
    # Module WITH an image path on its header.
    com_linhas = DefModuloService(session).criar(
        CriarDefModuloData(
            codigo="ROUP_IMG", nome="Roupeiro com imagem", user_id=7,
            categoria="ROUPEIROS", imagem_path="C:/imagens/ROUP_IMG.png",
            linhas=[
                CriarDefModuloLinhaData(
                    ordem=1, tipo_linha="DIVISAO_INDEPENDENTE", qt_mod="1",
                    descricao_livre="Corpo", comp="H", larg="L", esp="P",
                ),
                CriarDefModuloLinhaData(
                    ordem=2, tipo_linha="PECA", def_peca_id=lateral_id,
                    def_peca_codigo="LATERAL", comp="H", larg="P", esp="19",
                    chave_valueset="MATERIAL_LATERAIS", qt_und="2",
                ),
            ],
        )
    )
    session.commit()

    service = OrcamentoItemCusteioLinhaService(session)
    service.inserir_modulo_no_item(item_id, com_linhas.modulo.id)

    linhas = OrcamentoItemCusteioLinhaRepository(session).list_active_by_orcamento_item(
        item_id
    )
    primeira = min(linhas, key=lambda l: l.id)
    # The image lives on the FIRST line of the block (the division); others empty.
    assert primeira.tipo_linha == "DIVISAO_INDEPENDENTE"
    assert primeira.modulo_imagem_path == "C:/imagens/ROUP_IMG.png"
    outras = [l for l in linhas if l.id != primeira.id]
    assert all(l.modulo_imagem_path is None for l in outras)


def test_importar_modulo_pipeline_reavalia_medidas_e_valueset(session) -> None:
    item_id = _criar_item(session, altura="2000", largura="1000", profundidade="500")
    _criar_valueset_laterais(session, item_id)
    lateral_id, gaveta_id = _criar_pecas(session)
    modulo_id = _criar_modulo_roupeiro(session, lateral_id, gaveta_id)
    session.commit()

    service = OrcamentoItemCusteioLinhaService(session)
    service.inserir_modulo_no_item(item_id, modulo_id)

    # Run the measure + raw-material steps of the Atualizar pipeline.
    service.recalcular_medidas_do_item(item_id)
    service.recalcular_custo_materia_prima_do_item(item_id)

    repo = OrcamentoItemCusteioLinhaRepository(session)
    lateral = next(
        l
        for l in repo.list_active_by_orcamento_item(item_id)
        if l.tipo_linha == "PECA"
    )
    # Module formulas re-evaluated against the item variables (H=2000, P=500).
    assert lateral.comp_real == Decimal("2000.000")
    assert lateral.larg_real == Decimal("500.000")
    assert lateral.area_m2 == Decimal("1.0000")  # 2000 x 500 mm -> 1 m2
    # Cost computed from the item ValueSet material (M2 unit -> positive cost).
    assert lateral.custo_mp is not None
    assert lateral.custo_mp > 0


def test_importar_dois_modulos_acrescenta(session) -> None:
    item_id = _criar_item(session)
    _criar_valueset_laterais(session, item_id)
    lateral_id, gaveta_id = _criar_pecas(session)
    modulo_id = _criar_modulo_roupeiro(session, lateral_id, gaveta_id)
    session.commit()

    service = OrcamentoItemCusteioLinhaService(session)
    repo = OrcamentoItemCusteioLinhaRepository(session)

    service.inserir_modulo_no_item(item_id, modulo_id)
    apos_um = len(repo.list_active_by_orcamento_item(item_id))

    service.inserir_modulo_no_item(item_id, modulo_id)
    apos_dois = len(repo.list_active_by_orcamento_item(item_id))

    assert apos_um == 4  # division + lateral + composite header + component
    assert apos_dois == 2 * apos_um  # second import appends, not replaces


def test_importar_modulo_sem_linhas_avisa(session) -> None:
    item_id = _criar_item(session)
    session.commit()
    vazio = DefModuloService(session).criar(
        CriarDefModuloData(codigo="VAZIO", nome="Vazio", user_id=7)
    )

    service = OrcamentoItemCusteioLinhaService(session)
    resultado = service.inserir_modulo_no_item(item_id, vazio.modulo.id)

    assert resultado.criadas == 0
    assert resultado.avisos
    assert "não tem linhas" in resultado.avisos[0]


def test_importar_modulo_def_peca_inativa_avisa_sem_abortar(session) -> None:
    item_id = _criar_item(session)
    session.commit()
    peca_repo = DefPecaRepository(session)
    obsoleta = peca_repo.create_def_peca(
        codigo="OBSOLETA", nome="Obsoleta", descricao=None, grupo=None,
        tipo_peca="SIMPLES", chave_valueset_material="MATERIAL_LATERAIS",
        ativo=False,
    )
    modulo = DefModuloService(session).criar(
        CriarDefModuloData(
            codigo="MOD_OBS", nome="Módulo obsoleto", user_id=7,
            linhas=[
                CriarDefModuloLinhaData(
                    ordem=1, tipo_linha="PECA", def_peca_id=obsoleta.id,
                    def_peca_codigo="OBSOLETA", comp="H", larg="P",
                ),
            ],
        )
    )
    session.commit()

    service = OrcamentoItemCusteioLinhaService(session)
    resultado = service.inserir_modulo_no_item(item_id, modulo.modulo.id)

    # The line is still created (best effort) and a warning is recorded.
    assert resultado.criadas == 1
    assert any("OBSOLETA" in aviso for aviso in resultado.avisos)
    linhas = OrcamentoItemCusteioLinhaRepository(session).list_active_by_orcamento_item(
        item_id
    )
    assert len(linhas) == 1
    assert linhas[0].def_peca_codigo == "OBSOLETA"
    assert linhas[0].materia_prima_id is None  # no material copied/resolved


def test_importar_modulo_inexistente_erro(session) -> None:
    item_id = _criar_item(session)
    session.commit()
    service = OrcamentoItemCusteioLinhaService(session)
    with pytest.raises(ValueError):
        service.inserir_modulo_no_item(item_id, 9999)


# --- Composite with stored children (phase 8U.2 fix) -------------------------


def _criar_composta_com_regra(session) -> tuple[int, int, int, int, int]:
    """GAVETA (composta) with FUNDO (piece) + PES (hardware with a qty rule)."""
    peca_repo = DefPecaRepository(session)
    componente_repo = DefPecaComponenteRepository(session)
    regra_repo = DefRegraQuantidadeRepository(session)

    fundo = peca_repo.create_def_peca(
        codigo="FUNDO", nome="Fundo", descricao=None, grupo="FUNDOS",
        tipo_peca="SIMPLES", chave_valueset_material="MATERIAL_FUNDOS",
    )
    pes = peca_repo.create_def_peca(
        codigo="PES", nome="Pé nivelador", descricao=None, grupo="FERRAGENS",
        tipo_peca="SIMPLES", chave_valueset_material=None,
    )
    gaveta = peca_repo.create_def_peca(
        codigo="GAVETA", nome="Gaveta", descricao=None, grupo="GAVETAS",
        tipo_peca="COMPOSTA",
    )
    regra = regra_repo.create_regra(
        codigo="PES_NIVELADORES", nome="Pés niveladores",
        expressao="CEIL(COMP / 500)",
    )
    comp_fundo = componente_repo.create_componente(
        def_peca_pai_id=gaveta.id, tipo_componente="PECA",
        def_peca_componente_id=fundo.id, referencia_componente="FUNDO",
        descricao="Fundo", ordem=1, quantidade=Decimal("1"),
        regra_quantidade="FIXA", obrigatorio=True, ativo=True, observacoes=None,
    )
    comp_pes = componente_repo.create_componente(
        def_peca_pai_id=gaveta.id, tipo_componente="FERRAGEM",
        def_peca_componente_id=pes.id, referencia_componente="PES",
        descricao="Pé", ordem=2, quantidade=Decimal("1"),
        regra_quantidade="FIXA", obrigatorio=True, ativo=True, observacoes=None,
        def_regra_quantidade_id=regra.id,
    )
    session.flush()
    return gaveta.id, fundo.id, pes.id, comp_fundo.id, comp_pes.id


def _criar_modulo_composta_com_filhos(
    session, gaveta_id: int, fundo_id: int, pes_id: int, regra_id: int
) -> int:
    """Module with a composite header + its stored children (with formulas)."""
    com_linhas = DefModuloService(session).criar(
        CriarDefModuloData(
            codigo="MOD_GAV", nome="Gaveta módulo", user_id=7, categoria="ROUPEIROS",
            linhas=[
                CriarDefModuloLinhaData(
                    ordem=1, tipo_linha="PECA_COMPOSTA", def_peca_id=gaveta_id,
                    def_peca_codigo="GAVETA", descricao="Gaveta", qt_und="1",
                ),
                CriarDefModuloLinhaData(
                    ordem=2, tipo_linha="PECA", def_peca_id=fundo_id,
                    def_peca_codigo="FUNDO", linha_pai_ordem=1, nivel=1,
                    comp="L", larg="P", esp="19",
                    chave_valueset="MATERIAL_FUNDOS", qt_und="1",
                ),
                CriarDefModuloLinhaData(
                    ordem=3, tipo_linha="FERRAGEM", def_peca_id=pes_id,
                    def_peca_codigo="PES", linha_pai_ordem=1, nivel=1, qt_und="1",
                    def_regra_quantidade_id=regra_id,
                ),
            ],
        )
    )
    return com_linhas.modulo.id


def test_importar_composta_recria_filhos_com_formulas(session) -> None:
    item_id = _criar_item(session, altura="2000", largura="1000", profundidade="500")
    _criar_valueset_chave(session, item_id, "MATERIAL_FUNDOS")
    gaveta_id, fundo_id, pes_id, comp_fundo_id, comp_pes_id = _criar_composta_com_regra(
        session
    )
    regra_id = next(
        c.def_regra_quantidade_id
        for c in DefPecaComponenteRepository(session).list_by_peca_pai_id(gaveta_id)
        if c.referencia_componente == "PES"
    )
    modulo_id = _criar_modulo_composta_com_filhos(
        session, gaveta_id, fundo_id, pes_id, regra_id
    )
    session.commit()

    service = OrcamentoItemCusteioLinhaService(session)
    resultado = service.inserir_modulo_no_item(item_id, modulo_id)

    # Header counts as 1 created line; the two stored children are componentes.
    assert resultado.criadas == 1
    assert resultado.componentes == 2

    repo = OrcamentoItemCusteioLinhaRepository(session)
    linhas = repo.list_active_by_orcamento_item(item_id)
    assert [l.tipo_linha for l in linhas] == ["PECA_COMPOSTA", "PECA", "FERRAGEM"]

    cabecalho = next(l for l in linhas if l.tipo_linha == "PECA_COMPOSTA")
    fundo = next(l for l in linhas if l.def_peca_codigo == "FUNDO")
    pes = next(l for l in linhas if l.def_peca_codigo == "PES")

    # The header is an aggregator (no measures); children hang from it.
    assert cabecalho.comp is None and cabecalho.larg is None
    assert fundo.linha_pai_id == cabecalho.id and fundo.nivel == 1
    assert pes.linha_pai_id == cabecalho.id and pes.nivel == 1
    # The child kept its measure formulas from the module (not re-expanded).
    assert fundo.comp == "L"
    assert fundo.larg == "P"
    # origem_id linked to the matching def_peca_componente (for the rule).
    assert fundo.origem_id == comp_fundo_id
    assert pes.origem_id == comp_pes_id

    # Run the relevant pipeline steps: measures, quantity rule, qty, MP cost.
    service.recalcular_medidas_do_item(item_id)
    service.aplicar_regras_quantidade_do_item(item_id)
    service.recalcular_quantidades_do_item(item_id)
    service.recalcular_custo_materia_prima_do_item(item_id)

    linhas = repo.list_active_by_orcamento_item(item_id)
    fundo = next(l for l in linhas if l.def_peca_codigo == "FUNDO")
    pes = next(l for l in linhas if l.def_peca_codigo == "PES")

    # Child PECA: formulas re-evaluated against the item variables (L=1000, P=500).
    assert fundo.comp_real == Decimal("1000.000")
    assert fundo.larg_real == Decimal("500.000")
    assert fundo.area_m2 == Decimal("0.5000")  # 1000 x 500 mm -> 0.5 m2
    assert fundo.custo_mp is not None and fundo.custo_mp > 0
    # Hardware qty came from the rule: CEIL(COMP/500) = CEIL(1000/500) = 2.
    assert pes.qt_und == Decimal("2")


def test_importar_composta_aplica_formulas_do_cabecalho(session) -> None:
    """Phase C: header formulas stored on the module apply on import and the
    children's PAI_* transformations resolve from the header's real size."""
    item_id = _criar_item(session, altura="2000", largura="1000", profundidade="500")
    _criar_valueset_chave(session, item_id, "MATERIAL_FUNDOS")
    gaveta_id, fundo_id, _pes_id, _comp_fundo_id, _comp_pes_id = (
        _criar_composta_com_regra(session)
    )
    modulo = DefModuloService(session).criar(
        CriarDefModuloData(
            codigo="MOD_DIM", nome="Gaveta dimensionada", user_id=7,
            linhas=[
                CriarDefModuloLinhaData(
                    ordem=1, tipo_linha="PECA_COMPOSTA", def_peca_id=gaveta_id,
                    def_peca_codigo="GAVETA", descricao="Gaveta", qt_und="1",
                    comp="H", larg="L/2", esp="19",
                ),
                CriarDefModuloLinhaData(
                    ordem=2, tipo_linha="PECA", def_peca_id=fundo_id,
                    def_peca_codigo="FUNDO", linha_pai_ordem=1, nivel=1,
                    comp="PAI_COMP-4", larg="PAI_LARG-4",
                    chave_valueset="MATERIAL_FUNDOS", qt_und="1",
                ),
            ],
        )
    )
    session.commit()

    service = OrcamentoItemCusteioLinhaService(session)
    service.inserir_modulo_no_item(item_id, modulo.modulo.id)

    repo = OrcamentoItemCusteioLinhaRepository(session)
    linhas = repo.list_active_by_orcamento_item(item_id)
    cabecalho = next(l for l in linhas if l.tipo_linha == "PECA_COMPOSTA")
    fundo = next(l for l in linhas if l.def_peca_codigo == "FUNDO")

    # The module's header formulas were applied (not dropped, not the def_peca's).
    assert cabecalho.comp == "H"
    assert cabecalho.larg == "L/2"
    assert cabecalho.esp == "19"
    assert fundo.comp == "PAI_COMP-4"
    assert fundo.larg == "PAI_LARG-4"

    # Atualizar resolves the header first, then the child's PAI_* from it.
    service.recalcular_medidas_do_item(item_id)
    linhas = repo.list_active_by_orcamento_item(item_id)
    cabecalho = next(l for l in linhas if l.tipo_linha == "PECA_COMPOSTA")
    fundo = next(l for l in linhas if l.def_peca_codigo == "FUNDO")
    assert cabecalho.comp_real == Decimal("2000.000")
    assert cabecalho.larg_real == Decimal("500.000")  # L/2 = 1000/2
    assert fundo.comp_real == Decimal("1996.000")  # PAI_COMP-4
    assert fundo.larg_real == Decimal("496.000")  # PAI_LARG-4


def test_importar_composta_cabecalho_antigo_fica_sem_dimensoes(session) -> None:
    """Phase C compat: an old module (header saved without formulas) keeps the
    dimensionless header even when the def_peca meanwhile gained formulas."""
    item_id = _criar_item(session)
    _criar_valueset_chave(session, item_id, "MATERIAL_FUNDOS")
    peca_repo = DefPecaRepository(session)
    gaveta = peca_repo.create_def_peca(
        codigo="GAVETA_F", nome="Gaveta", descricao=None, grupo="GAVETAS",
        tipo_peca="COMPOSTA", formula_comp="H", formula_larg="L",
    )
    modulo = DefModuloService(session).criar(
        CriarDefModuloData(
            codigo="MOD_ANTIGO_DIM", nome="Gaveta antiga", user_id=7,
            linhas=[
                CriarDefModuloLinhaData(
                    ordem=1, tipo_linha="PECA_COMPOSTA", def_peca_id=gaveta.id,
                    def_peca_codigo="GAVETA_F", descricao="Gaveta", qt_und="1",
                ),
                CriarDefModuloLinhaData(
                    ordem=2, tipo_linha="PECA", def_peca_codigo="FUNDO_F",
                    linha_pai_ordem=1, nivel=1, comp="L", larg="P",
                    chave_valueset="MATERIAL_FUNDOS", qt_und="1",
                ),
            ],
        )
    )
    session.commit()

    OrcamentoItemCusteioLinhaService(session).inserir_modulo_no_item(
        item_id, modulo.modulo.id
    )

    linhas = OrcamentoItemCusteioLinhaRepository(session).list_active_by_orcamento_item(
        item_id
    )
    cabecalho = next(l for l in linhas if l.tipo_linha == "PECA_COMPOSTA")
    assert cabecalho.comp is None
    assert cabecalho.larg is None
    assert cabecalho.esp is None


def test_importar_composta_sem_def_peca_aplica_formulas_do_cabecalho(session) -> None:
    """Phase C: the best-effort header (piece gone) still gets the formulas."""
    item_id = _criar_item(session)
    modulo = DefModuloService(session).criar(
        CriarDefModuloData(
            codigo="MOD_ORFAO_DIM", nome="Conjunto órfão", user_id=7,
            linhas=[
                CriarDefModuloLinhaData(
                    ordem=1, tipo_linha="PECA_COMPOSTA",
                    def_peca_codigo="CONJ_APAGADO", descricao="Conjunto",
                    qt_und="1", comp="H", larg="L",
                ),
                CriarDefModuloLinhaData(
                    ordem=2, tipo_linha="PECA", def_peca_codigo="FILHO_APAGADO",
                    linha_pai_ordem=1, nivel=1, comp="PAI_COMP", larg="PAI_LARG",
                    qt_und="1",
                ),
            ],
        )
    )
    session.commit()

    service = OrcamentoItemCusteioLinhaService(session)
    resultado = service.inserir_modulo_no_item(item_id, modulo.modulo.id)

    assert any("CONJ_APAGADO" in aviso for aviso in resultado.avisos)
    linhas = OrcamentoItemCusteioLinhaRepository(session).list_active_by_orcamento_item(
        item_id
    )
    cabecalho = next(l for l in linhas if l.tipo_linha == "PECA_COMPOSTA")
    assert cabecalho.comp == "H"
    assert cabecalho.larg == "L"
    assert cabecalho.esp is None


def test_importar_composta_sem_filhos_fallback_reexpande(session) -> None:
    """Old modules (no stored children) still re-expand from the def_peca."""
    item_id = _criar_item(session)
    _criar_valueset_chave(session, item_id, "MATERIAL_FUNDOS")
    gaveta_id, fundo_id, pes_id, _comp_fundo_id, _comp_pes_id = (
        _criar_composta_com_regra(session)
    )
    # Module with ONLY the composite header (no children stored).
    modulo = DefModuloService(session).criar(
        CriarDefModuloData(
            codigo="MOD_OLD", nome="Gaveta antiga", user_id=7,
            linhas=[
                CriarDefModuloLinhaData(
                    ordem=1, tipo_linha="PECA_COMPOSTA", def_peca_id=gaveta_id,
                    def_peca_codigo="GAVETA", descricao="Gaveta", qt_und="1",
                ),
            ],
        )
    )
    session.commit()

    service = OrcamentoItemCusteioLinhaService(session)
    resultado = service.inserir_modulo_no_item(item_id, modulo.modulo.id)

    # Fallback re-expands the def_peca: header + its 2 active components.
    assert resultado.criadas == 1
    assert resultado.componentes == 2
    linhas = OrcamentoItemCusteioLinhaRepository(session).list_active_by_orcamento_item(
        item_id
    )
    assert [l.tipo_linha for l in linhas] == ["PECA_COMPOSTA", "PECA", "FERRAGEM"]
