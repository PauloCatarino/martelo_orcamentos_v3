"""O comando ``scripts/importar_catalogos.py`` importa-se e sabe do Egger.

Não toca na base nem no Excel do servidor: só garante que o módulo carrega e
que o ``--ver`` mostra a tabela sem escrever nada — que é o modo em que alguém
olha para uma tabela nova antes de a deixar entrar.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from openpyxl import Workbook

_CAMINHO = Path(__file__).resolve().parents[1] / "scripts" / "importar_catalogos.py"


def _carregar():
    spec = importlib.util.spec_from_file_location("importar_catalogos", _CAMINHO)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _xlsx_egger(caminho: Path) -> Path:
    """Um xlsx mínimo com o separador da B&F, para o ``--ver`` ter o que ler."""
    tipo = "Eurodekor Tableros de partículas revestidos E1E05 TSCA P2"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Stock_B&F_Egger"
    worksheet.append(["Tabela de Produtos EGGER Balbino & Faustino - 2026"])
    worksheet.append(["A partir do PDF BF-82 2026/04/20."])
    worksheet.append(
        [
            "id", "Referência", "ST", "Nome Design", "Grupo",
            "Esp 8mm", "Preço Tabela 8mm", "Esp 19mm", "Preço Tabela 19mm",
            "Tipo Produto", "Fornecedor", "Observações",
        ]
    )
    worksheet.append(
        [1, "F037", "ST76", "Travertino Taormina", 8, "SIM", 17.98, "SIM", 21.02,
         tipo, "Balbino & Faustino", None]
    )
    workbook.create_sheet("Stock_WoodSide_Egger")
    workbook.save(caminho)
    return caminho


def test_o_modulo_carrega_e_tem_o_egger() -> None:
    module = _carregar()

    assert "egger" in module.ADAPTADORES
    assert hasattr(module, "main")


def test_um_separador_ilegivel_da_erro_em_vez_de_silencio(tmp_path, capsys) -> None:
    """Só o separador da B&F tem dados; o da WoodSide está vazio de propósito.

    O comando tem de sair com erro e dizer qual foi o separador — nunca
    importar meia tabela e devolver zero.
    """
    module = _carregar()
    caminho = _xlsx_egger(tmp_path / "t.xlsx")

    codigo = module.main(
        ["--fornecedor", "egger", "--ficheiro", str(caminho), "--ver"]
    )
    escrito = capsys.readouterr().out

    assert codigo == 2
    assert "ERRO de formato" in escrito
    assert "Stock_WoodSide_Egger" in escrito


def test_ver_de_um_ficheiro_completo_lista_os_artigos(tmp_path, capsys) -> None:
    module = _carregar()
    caminho = _xlsx_egger(tmp_path / "t.xlsx")

    # Um separador da WoodSide igual ao da B&F, para as duas folhas lerem.
    from openpyxl import load_workbook

    workbook = load_workbook(caminho)
    del workbook["Stock_WoodSide_Egger"]
    origem = workbook["Stock_B&F_Egger"]
    copia = workbook.copy_worksheet(origem)
    copia.title = "Stock_WoodSide_Egger"
    copia["J4"] = "WoodSide"
    workbook.save(caminho)

    codigo = module.main(
        ["--fornecedor", "egger", "--ficheiro", str(caminho), "--ver"]
    )
    escrito = capsys.readouterr().out

    assert codigo == 0
    assert "4 artigos em 2 tabelas" in escrito
    assert "F037|ST76|PB STD|8mm" in escrito
    assert "nada foi escrito" in escrito
