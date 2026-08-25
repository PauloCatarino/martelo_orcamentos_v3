"""Fornecedores: servico e dialogo de contactos."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.repositories.def_fornecedor_repository import (
    DefFornecedorRepository,
    DefFornecedorResumo,
)
from app.services.def_fornecedor_service import DefFornecedorService, FornecedorData
from app.ui.dialogs.fornecedores_dialog import FornecedoresDialog

_app = QApplication.instance() or QApplication([])


@pytest.fixture()
def service(session) -> DefFornecedorService:
    return DefFornecedorService(session)


def test_criar_e_listar(service) -> None:
    service.criar_fornecedor(FornecedorData(nome="SONAE", email="c@sonae.pt"))
    service.criar_fornecedor(FornecedorData(nome="EGGER"))

    fornecedores = service.listar_fornecedores()

    assert [f.nome for f in fornecedores] == ["EGGER", "SONAE"]
    assert fornecedores[1].tem_email is True
    assert fornecedores[0].tem_email is False


def test_nome_repetido_e_recusado(service) -> None:
    service.criar_fornecedor(FornecedorData(nome="SONAE"))

    with pytest.raises(ValueError, match="Já existe"):
        service.criar_fornecedor(FornecedorData(nome="  SONAE  "))


def test_nome_vazio_e_recusado(service) -> None:
    with pytest.raises(ValueError, match="obrigatório"):
        service.criar_fornecedor(FornecedorData(nome="   "))


def test_editar_guarda_os_contactos(service) -> None:
    fornecedor = service.criar_fornecedor(FornecedorData(nome="EMUCA"))

    service.editar_fornecedor(
        fornecedor.id,
        FornecedorData(
            nome="EMUCA",
            email="encomendas@emuca.pt",
            email_cc="comercial@emuca.pt",
            pessoa_contacto="Ana",
            telefone="912345678",
        ),
    )

    guardado = service.obter_por_id(fornecedor.id)
    assert guardado.email == "encomendas@emuca.pt"
    assert guardado.email_cc == "comercial@emuca.pt"
    assert guardado.pessoa_contacto == "Ana"


def test_conta_as_materias_primas_ativas(service, session) -> None:
    from app.services.def_materia_prima_service import (
        CriarDefMateriaPrimaData,
        DefMateriaPrimaService,
    )

    fornecedor = service.criar_fornecedor(FornecedorData(nome="SONAE"))
    materias = DefMateriaPrimaService(session)
    for descricao in ("Placa A", "Placa B"):
        materias.criar_materia_prima(
            CriarDefMateriaPrimaData(
                descricao=descricao,
                familia_original_excel="PLACAS",
                fornecedor="SONAE",
                fornecedor_id=fornecedor.id,
            )
        )
    desativada = materias.criar_materia_prima(
        CriarDefMateriaPrimaData(
            descricao="Placa velha",
            familia_original_excel="PLACAS",
            fornecedor_id=fornecedor.id,
        )
    )
    materias.definir_ativo(desativada.id, ativo=False)

    assert service.listar_fornecedores()[0].materias_primas == 2


def test_fornecedores_sem_email_so_conta_quem_fornece_alguma_coisa(service, session) -> None:
    from app.services.def_materia_prima_service import (
        CriarDefMateriaPrimaData,
        DefMateriaPrimaService,
    )

    com_material = service.criar_fornecedor(FornecedorData(nome="SONAE"))
    service.criar_fornecedor(FornecedorData(nome="SEM MATERIAL"))
    DefMateriaPrimaService(session).criar_materia_prima(
        CriarDefMateriaPrimaData(
            descricao="Placa",
            familia_original_excel="PLACAS",
            fornecedor_id=com_material.id,
        )
    )

    em_falta = service.fornecedores_sem_email()

    assert [f.nome for f in em_falta] == ["SONAE"]


def _resumo(**overrides) -> DefFornecedorResumo:
    base = {
        "id": 1,
        "nome": "SONAE",
        "email": None,
        "email_cc": None,
        "pessoa_contacto": None,
        "telefone": None,
        "observacoes": None,
        "ativo": True,
        "materias_primas": 24,
    }
    base.update(overrides)
    return DefFornecedorResumo(**base)


def test_dialogo_assinala_quem_fornece_sem_email() -> None:
    dialogo = FornecedoresDialog([_resumo(), _resumo(id=2, nome="EGGER", email="a@b.pt")])

    assert "1 fornecedores com material mas sem email" in dialogo.status_label.text()
    assert "SONAE" in dialogo.status_label.text()


def test_dialogo_devolve_so_o_que_mudou() -> None:
    dialogo = FornecedoresDialog([_resumo(), _resumo(id=2, nome="EGGER", email="a@b.pt")])

    assert dialogo.alteracoes() == {}

    dialogo.table.item(0, dialogo.COLUNA_EMAIL).setText("comercial@sonae.pt")
    alteracoes = dialogo.alteracoes()

    assert list(alteracoes) == [1]
    assert alteracoes[1].email == "comercial@sonae.pt"
    assert alteracoes[1].nome == "SONAE"


def test_dialogo_nao_deixa_editar_a_contagem_de_materiais() -> None:
    dialogo = FornecedoresDialog([_resumo()])

    item = dialogo.table.item(0, dialogo.COLUNA_MATERIAIS)

    assert item.text() == "24"
    assert not (item.flags() & Qt.ItemFlag.ItemIsEditable)


def test_importar_pelo_nome_nao_perde_a_ligacao_ao_fornecedor(service, session) -> None:
    """Regressão: a importação só traz o nome, e chegou a apagar a ligação.

    Quem edita na app escolhe o fornecedor de uma lista e manda o id; quem
    importa só sabe o nome. Sem tradução do nome para id, cada importação
    deixava o catálogo inteiro sem fornecedor — e o pedido de preços sem saber
    a quem escrever.
    """
    from app.services.def_materia_prima_service import (
        CriarDefMateriaPrimaData,
        DefMateriaPrimaService,
        EditarDefMateriaPrimaData,
    )

    fornecedor = service.criar_fornecedor(FornecedorData(nome="B&F"))
    materias = DefMateriaPrimaService(session)
    materia = materias.criar_materia_prima(
        CriarDefMateriaPrimaData(
            descricao="AGL MLM BRANCO 19MM",
            familia_original_excel="PLACAS",
            fornecedor="B&F",
        )
    )

    # Criar já liga pelo nome.
    assert materia.fornecedor_id == fornecedor.id

    # E uma importação seguinte (só com o nome) mantém a ligação.
    atualizada = materias.editar_materia_prima(
        materia.id,
        EditarDefMateriaPrimaData(
            descricao=materia.descricao,
            ref_le=materia.ref_le,
            familia_original_excel="PLACAS",
            fornecedor="B&F",
            origem_dados="EXCEL",
        ),
    )

    assert atualizada.fornecedor_id == fornecedor.id
    assert service.listar_fornecedores()[0].materias_primas == 1


def test_fornecedor_desconhecido_fica_sem_ligacao(service, session) -> None:
    from app.services.def_materia_prima_service import (
        CriarDefMateriaPrimaData,
        DefMateriaPrimaService,
    )

    materia = DefMateriaPrimaService(session).criar_materia_prima(
        CriarDefMateriaPrimaData(
            descricao="Placa",
            familia_original_excel="PLACAS",
            fornecedor="FORNECEDOR QUE NAO EXISTE",
        )
    )

    assert materia.fornecedor_id is None
    assert materia.fornecedor == "FORNECEDOR QUE NAO EXISTE"


def test_sem_fornecedor_nenhum_mantem_o_que_estava(service, session) -> None:
    from app.services.def_materia_prima_service import (
        CriarDefMateriaPrimaData,
        DefMateriaPrimaService,
        EditarDefMateriaPrimaData,
    )

    fornecedor = service.criar_fornecedor(FornecedorData(nome="SONAE"))
    materias = DefMateriaPrimaService(session)
    materia = materias.criar_materia_prima(
        CriarDefMateriaPrimaData(
            descricao="Placa",
            familia_original_excel="PLACAS",
            fornecedor_id=fornecedor.id,
        )
    )

    atualizada = materias.editar_materia_prima(
        materia.id,
        EditarDefMateriaPrimaData(
            descricao="Placa",
            ref_le=materia.ref_le,
            familia_original_excel="PLACAS",
        ),
    )

    assert atualizada.fornecedor_id == fornecedor.id


def test_script_repara_as_ligacoes_perdidas(service, session) -> None:
    from scripts.reparar_ligacao_fornecedores import reparar
    from app.models import DefMateriaPrima

    service.criar_fornecedor(FornecedorData(nome="B&F"))
    session.add_all(
        [
            # Como ficaram depois da importação: com nome, sem ligação.
            DefMateriaPrima(descricao="Placa 1", fornecedor="B&F"),
            DefMateriaPrima(descricao="Placa 2", fornecedor=" b&f "),
            DefMateriaPrima(descricao="Placa 3", fornecedor="SEM FICHA"),
            DefMateriaPrima(descricao="Placa 4", fornecedor=None),
        ]
    )
    session.commit()

    resumo = reparar(session)

    assert resumo["ligadas"] == 2
    assert resumo["sem_fornecedor"] == {"SEM FICHA": 1}
    assert service.listar_fornecedores()[0].materias_primas == 2

    # Correr outra vez não muda nada.
    assert reparar(session)["ligadas"] == 0


def test_simular_nao_grava(service, session) -> None:
    from scripts.reparar_ligacao_fornecedores import reparar
    from app.models import DefMateriaPrima

    service.criar_fornecedor(FornecedorData(nome="B&F"))
    session.add(DefMateriaPrima(descricao="Placa", fornecedor="B&F"))
    session.commit()

    resumo = reparar(session, simular=True)

    assert resumo["ligadas"] == 1
    assert service.listar_fornecedores()[0].materias_primas == 0


def test_telefone_fica_no_formato_999_999_999(service) -> None:
    from app.domain.contactos import formatar_telefone

    assert formatar_telefone("932523885") == "932 523 885"
    assert formatar_telefone(" 932-523.885 ") == "932 523 885"
    assert formatar_telefone("+351 932 523 885") == "932 523 885"
    assert formatar_telefone("") is None
    # O que não é um número nacional fica como foi escrito.
    assert formatar_telefone("+34 91 123 4567") == "+34 91 123 4567"
    assert formatar_telefone("21 000 (ext. 4)") == "21 000 (ext. 4)"

    fornecedor = service.criar_fornecedor(
        FornecedorData(nome="B&F", telefone="932523885")
    )

    assert fornecedor.telefone == "932 523 885"
