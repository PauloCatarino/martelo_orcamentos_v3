"""Cria o modelo de ensaio Lista_Material_IMOS_MARTELO_COLAR.xltm (coluna «Colar» + menu).

Pedido do Paulo (06-11-2026): testar na fábrica uma coluna «Colar» na LISTAGEM_CUT_RITE,
logo a seguir à CNC_2, preenchida por um menu, para as colagens de peças (guia
PROCESSO_ESPECIAL), SEM mexer no modelo de sempre. Este script:

1. copia o modelo de sempre (que fica intacto) para ``..._COLAR.xltm`` na mesma pasta; se
   já houver um COLAR, o anterior fica ao lado com a data e a hora no nome;
2. insere a coluna «Colar» a seguir à CNC_2. O Excel corrige sozinho as fórmulas da folha
   Lacagem (Z passa a AA), a formatação condicional do Material e a área de impressão;
3. junta o ``modColar``, o ``frmColar`` e o duplo clique da folha, e troca o
   ``Copia_List_Soft_Cut_Rite`` pela versão que copia até ao +Larg (``scripts/vba/colar``);
4. põe um botão «Colar» por cima da coluna nova;
5. grava, volta a abrir para confirmar e manda o Excel compilar o projeto VBA (um erro de
   compilação abre uma caixa no Excel escondido e o script fica à espera).

Uso:
    python scripts/criar_modelo_lista_material_colar.py [modelo_de_origem] [modelo_COLAR]

Sem argumentos, usa o modelo do servidor e grava o COLAR ao lado dele. Precisa do Excel e
de "Confiar no acesso ao modelo de objeto do projeto VBA" (como o
``atualizar_macros_modelo_lista_material.py``).
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atualizar_macros_modelo_lista_material import (  # noqa: E402
    MODELO_SERVIDOR,
    _codigo,
    _codigo_do_ficheiro,
    _componente,
    _projeto_vba,
)

PASTA_COLAR = Path(__file__).resolve().parent / "vba" / "colar"
NOME_COLAR = "Lista_Material_IMOS_MARTELO_COLAR.xltm"
FOLHA = "LISTAGEM_CUT_RITE"
TABELA = "Tabela_Cut_Rite"
COLUNA = "Colar"
LARGURA_COLUNA = 24
DICA_COLUNA = (
    "Colagem de peças (ensaio). Duplo clique: menu Colar. "
    "Ex.: 14+14_O4L_CNC = 2 peças ID 14, orlar 4 lados, CNC no fim."
)

# Módulos do modelo COLAR: (ficheiro em scripts/vba/colar, nome no VBA, tipo).
# tipo: 1 = módulo, 3 = formulário, None = já existe no modelo (troca-se o texto).
MODULOS_COLAR = (
    ("modColar.bas", "modColar", 1),
    ("frmColar.vba", "frmColar", 3),
    ("Copia_List_Soft_Cut_Rite.bas", "Copia_List_Soft_Cut_Rite", None),
)
CODIGO_DA_FOLHA = "Folha5_LISTAGEM_CUT_RITE.cls"
MARCADORES = {
    "modColar": "Public Function ColarProblemas",
    "frmColar": "Private Sub btnGravar_Click",
    "Copia_List_Soft_Cut_Rite": "ColunaMaisLarg(lo)",
}

XL_TO_RIGHT = -4161
XL_FORMAT_FROM_LEFT_OR_ABOVE = 0
XL_LEFT = -4131
XL_VALIDATE_INPUT_ONLY = 0


def guardar_anterior(destino: Path) -> Path | None:
    """O COLAR que já lá estava fica ao lado, com a data no nome (nunca se apaga)."""
    if not destino.exists():
        return None
    carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")
    anterior = destino.with_name(f"{destino.stem}_anterior_{carimbo}{destino.suffix}")
    destino.rename(anterior)
    return anterior


def _escrever_codigo(componente, origem: Path) -> None:
    modulo = componente.CodeModule
    if modulo.CountOfLines:
        modulo.DeleteLines(1, modulo.CountOfLines)
    modulo.AddFromString(_codigo_do_ficheiro(origem))


def _nomes_das_colunas(tabela) -> list[str]:
    return [str(tabela.ListColumns(i).Name) for i in range(1, tabela.ListColumns.Count + 1)]


def _inserir_coluna(folha, tabela) -> int:
    """Insere a coluna Colar a seguir à CNC_2; devolve a coluna (na folha) onde ficou."""
    nomes = _nomes_das_colunas(tabela)
    if any(nome.strip().casefold() == COLUNA.casefold() for nome in nomes):
        raise SystemExit("O modelo de origem já tem a coluna Colar: use o modelo de sempre.")
    if "CNC_2" not in nomes:
        raise SystemExit("Não encontrei a coluna CNC_2 na Tabela_Cut_Rite.")
    indice = nomes.index("CNC_2") + 2  # 1-based, a seguir à CNC_2
    coluna = int(tabela.ListColumns(indice - 1).Range.Column) + 1
    folha.Columns(coluna).Insert(Shift=XL_TO_RIGHT, CopyOrigin=XL_FORMAT_FROM_LEFT_OR_ABOVE)
    nova = tabela.ListColumns(indice)
    nova.Name = COLUNA
    nova.Range.ColumnWidth = LARGURA_COLUNA
    corpo = nova.DataBodyRange
    if corpo is not None:
        corpo.NumberFormat = "@"
        corpo.HorizontalAlignment = XL_LEFT
        validacao = corpo.Validation
        validacao.Delete()
        validacao.Add(Type=XL_VALIDATE_INPUT_ONLY)
        validacao.InputTitle = "Colar"
        validacao.InputMessage = DICA_COLUNA
        validacao.ShowInput = True
        validacao.ShowError = False
    return coluna


def _botao(folha, coluna: int) -> None:
    """Um botão «Colar» igual ao «Calculo Orlas», por cima da coluna nova."""
    modelo = None
    for forma in folha.Shapes:
        if str(forma.OnAction).endswith("GERAR_ResumoOrlas"):
            modelo = forma
            break
    if modelo is None:
        raise SystemExit("Não encontrei o botão «Calculo Orlas» para copiar o estilo.")
    botao = modelo.Duplicate()
    botao.Name = "Botao Colar"
    celula = folha.Cells(1, coluna)
    botao.Width = max(110.0, float(celula.Width) - 6)
    botao.Height = 56
    botao.Top = 2
    botao.Left = float(celula.Left) + 3
    botao.TextFrame2.TextRange.Text = "Colar"
    botao.OnAction = "AbrirMenuColar"
    botao.AlternativeText = "Menu Colar: colagens de peças (ensaio)"


def _compilar(livro) -> bool:
    """Manda o Excel compilar o projeto VBA; True quando compilou sem erros."""
    vbe = livro.VBProject.VBE
    botao = vbe.CommandBars.FindControl(Type=1, Id=578)
    if botao is None or not botao.Enabled:
        return True
    botao.Execute()
    return not botao.Enabled


def criar(origem: Path, destino: Path) -> list[str]:
    if not origem.is_file():
        raise SystemExit(f"Modelo de origem não encontrado: {origem}")
    for nome, _, _ in MODULOS_COLAR:
        if not (PASTA_COLAR / nome).is_file():
            raise SystemExit(f"Falta {PASTA_COLAR / nome}")
    relatorio: list[str] = []
    anterior = guardar_anterior(destino)
    if anterior is not None:
        relatorio.append(f"O COLAR anterior ficou em {anterior.name}")
    shutil.copyfile(origem, destino)
    relatorio.append(f"Copiado {origem.name} -> {destino.name}")

    import win32com.client as win32_client

    excel = win32_client.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    try:
        excel.AutomationSecurity = 3  # não correr macros ao abrir
    except Exception:
        pass
    try:  # se a compilação prender o Excel escondido, é este processo que se fecha
        import win32process

        print(f"Excel PID {win32process.GetWindowThreadProcessId(excel.Hwnd)[1]}", flush=True)
    except Exception:
        pass

    def abrir():
        # Editable=True é obrigatório num .xltm (senão abre um livro novo).
        livro = excel.Workbooks.Open(str(destino), UpdateLinks=0, Editable=True, AddToMru=False)
        if livro.ReadOnly:
            raise SystemExit(f"O modelo abriu em só-leitura (alguém o tem aberto?):\n{destino}")
        return livro

    livro = None
    try:
        livro = abrir()
        folha = livro.Worksheets(FOLHA)
        tabela = folha.ListObjects(TABELA)
        coluna = _inserir_coluna(folha, tabela)
        relatorio.append(f"Coluna Colar inserida na coluna {coluna} da {FOLHA}")
        _botao(folha, coluna)
        relatorio.append("Botão «Colar» por cima da coluna")

        projeto = _projeto_vba(livro)
        for ficheiro, nome, tipo in MODULOS_COLAR:
            componente = _componente(projeto, nome)
            if componente is None:
                if tipo is None:
                    raise SystemExit(f"O modelo não tem o módulo {nome}.")
                componente = projeto.VBComponents.Add(tipo)
                componente.Name = nome
            _escrever_codigo(componente, PASTA_COLAR / ficheiro)
            relatorio.append(f"VBA: {nome}")
        codigo_folha = _componente(projeto, str(folha.CodeName))
        _escrever_codigo(codigo_folha, PASTA_COLAR / CODIGO_DA_FOLHA)
        relatorio.append(f"VBA: duplo clique na folha ({folha.CodeName})")
        livro.Save()
        livro.Close(False)
        livro = None

        # Confirmar no ficheiro gravado.
        livro = abrir()
        tabela = livro.Worksheets(FOLHA).ListObjects(TABELA)
        nomes = _nomes_das_colunas(tabela)
        cnc2 = nomes.index("CNC_2")
        if nomes[cnc2 + 1] != COLUNA or nomes[cnc2 + 2].strip() != "+comp":
            raise SystemExit(f"As colunas não ficaram como deviam: {nomes[cnc2:cnc2 + 4]}")
        projeto = _projeto_vba(livro)
        for nome, marcador in MARCADORES.items():
            if marcador not in _codigo(_componente(projeto, nome)):
                raise SystemExit(f"O código de {nome} não ficou gravado no modelo.")
        relatorio.append("Colunas a seguir à CNC_2: " + " | ".join(n.strip() for n in nomes[cnc2:cnc2 + 4]))
        relatorio.append("Projeto VBA compilado sem erros" if _compilar(livro) else
                         "ATENÇÃO: o projeto VBA não compilou")
    finally:
        if livro is not None:
            try:
                livro.Close(False)
            except Exception:
                pass
        try:
            excel.Quit()
        except Exception:
            pass
    return relatorio


def main() -> None:
    origem = Path(sys.argv[1]) if len(sys.argv) > 1 else MODELO_SERVIDOR
    destino = Path(sys.argv[2]) if len(sys.argv) > 2 else origem.with_name(NOME_COLAR)
    if destino.resolve() == origem.resolve():
        raise SystemExit("O modelo COLAR não pode ser o próprio modelo de origem.")
    for linha in criar(origem, destino):
        print(linha)


if __name__ == "__main__":
    main()
