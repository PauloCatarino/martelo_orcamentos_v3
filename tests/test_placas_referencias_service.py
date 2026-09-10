"""O leitor do Excel curado — hoje um caminho alternativo, não o de todos os dias.

Desde a Fase 3 as referências vêm da base (ver ``test_catalogos_consulta``).
Este leitor ficou para comparar as duas origens e para se ter por onde voltar,
e é por isso que continua a ter testes seus.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook

from app.services import placas_referencias_service as service_module


def _criar_excel(caminho: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Egger"
    worksheet.append(["Catalogo curado"])
    worksheet.append(
        [
            "Referencia",
            "ST",
            "Nome Design",
            "Grupo",
            "Tipo Produto",
            "Fornecedor",
            "Preco Tabela 8 mm",
            "PVP 19mm",
        ]
    )
    worksheet.append(["W1000", "ST9", "Branco Premium", "Lisos", "MDF", "Egger", 14.6, 17.72])
    worksheet.append(["", "ST", "linha sem referencia", "Grupo", "MDF", "Egger", 1, 2])

    segundo = workbook.create_sheet("Kronospan")
    segundo.append([])
    segundo.append(["Texto solto"])
    segundo.append(
        [
            "Codigo Referencia",
            "Acabamento",
            "Descricao",
            "Grupo",
            "Familia Produto",
            "Fornecedor",
            "Preco Tabela 16mm",
        ]
    )
    segundo.append(["K101", "SM", "Carvalho Natural", "Madeiras", "Aglomerado", "Krono", 21])

    workbook.save(caminho)


def test_listar_referencias_le_excel_curado(tmp_path, monkeypatch) -> None:
    caminho = tmp_path / service_module.FICHEIRO_REFERENCIAS
    _criar_excel(caminho)

    class _FakeSystemSettingService:
        def __init__(self, session) -> None:
            self.session = session

        def obter_valor(self, chave: str, default: str | None = None) -> str | None:
            assert chave == "pasta_pesquisa_profunda_ia"
            return str(tmp_path)

    monkeypatch.setattr(
        service_module, "SystemSettingService", _FakeSystemSettingService
    )

    referencias = service_module.listar_referencias_do_excel(object())

    assert referencias == [
        service_module.LinhaReferencia(
            folha="Egger",
            referencia="W1000",
            st_acab="ST9",
            nome_design="Branco Premium",
            grupo="Lisos",
            tipo="MDF",
            fornecedor="Egger",
            precos={"8mm": "14,60 \u20ac", "19mm": "17,72 \u20ac"},
        ),
        service_module.LinhaReferencia(
            folha="Kronospan",
            referencia="K101",
            st_acab="SM",
            nome_design="Carvalho Natural",
            grupo="Madeiras",
            tipo="Aglomerado",
            fornecedor="Krono",
            precos={"16mm": "21,00 \u20ac"},
        ),
    ]


def test_listar_referencias_falha_quando_excel_nao_existe(tmp_path, monkeypatch) -> None:
    class _FakeSystemSettingService:
        def __init__(self, session) -> None:
            self.session = session

        def obter_valor(self, chave: str, default: str | None = None) -> str | None:
            assert chave == "pasta_pesquisa_profunda_ia"
            return str(tmp_path)

    monkeypatch.setattr(
        service_module, "SystemSettingService", _FakeSystemSettingService
    )

    with pytest.raises(RuntimeError, match="Excel de referencias nao encontrado"):
        service_module.listar_referencias_do_excel(object())


def test_listar_referencias_recusa_ler_o_excel_as_escondidas(monkeypatch) -> None:
    """Com a base vazia isto falha alto em vez de cair no Excel.

    Uma tabela meia cheia e sem aviso nenhum era pior do que uma que não abre:
    ninguém repararia que faltavam os artigos das tabelas que não foram
    importadas.
    """
    monkeypatch.setattr(service_module, "esta_vazia", lambda _session: True)

    with pytest.raises(RuntimeError, match="importar_catalogos"):
        service_module.listar_referencias(object())


def test_listar_referencias_com_origem_excel_le_o_excel(monkeypatch) -> None:
    chamadas: list[object] = []
    monkeypatch.setattr(
        service_module,
        "listar_referencias_do_excel",
        lambda session: chamadas.append(session) or ["linha"],
    )

    resultado = service_module.listar_referencias(
        object(), origem=service_module.ORIGEM_EXCEL
    )

    assert resultado == ["linha"]
    assert len(chamadas) == 1


def test_listar_referencias_nao_inventa_origens() -> None:
    with pytest.raises(ValueError, match="Origem desconhecida"):
        service_module.listar_referencias(object(), origem="ficheiro")
