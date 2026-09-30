"""Abrir e gravar a Lista Material por COM sem estragar as fórmulas das macros.

Várias colunas da LISTAGEM_CUT_RITE são funções VBA do próprio livro
(`RefCliente_CutRite`, `EncPHC_CutRite`, `EspMaterialMM`...). Quando o Martelo
abria o livro com as macros desligadas (`AutomationSecurity = 3`) e o gravava,
o Excel recalculava essas colunas sem as funções e guardava `#NAME?`. Foi o que
aconteceu na obra 1610_01_01_JF_VIVA ao importar as ferragens: a cópia de
antes tinha Ref_Cliente 2607010, o ficheiro gravado ficou com `#NAME?`. O envio
para o Cut-Rite lê os valores guardados, e o `#NAME?` ia parar ao plano.

Abrir com as macros ativas mas com os eventos desligados deixa as funções
calcular (valores certos) sem correr `Workbook_Open`, `Worksheet_Change` nem
qualquer outra macro de evento. Antes de gravar recalcula-se tudo.
"""
from __future__ import annotations

import importlib
from pathlib import Path

MACROS_ATIVAS = 1  # msoAutomationSecurityLow


def preparar_excel(excel) -> None:
    """Excel escondido, macros do livro disponíveis e eventos desligados."""
    excel.Visible = False
    excel.DisplayAlerts = False
    try:
        excel.AutomationSecurity = MACROS_ATIVAS
    except Exception:
        pass
    # Tem de ser ANTES de abrir: é o que impede o Workbook_Open de correr.
    excel.EnableEvents = False


def descrever_erro(error: BaseException) -> str:
    """O texto do erro que o Excel deu, sem o tuplo de códigos do COM.

    ``(-2147352567, 'Ocorreu uma exceção.', (0, 'Microsoft Excel', 'Não foi
    possível...', 'xlmain11.chm', 0, -2146827284), None)`` passa a
    «Microsoft Excel: Não foi possível...». Os outros erros ficam como estão.
    """
    args = getattr(error, "args", ())
    detalhe = args[2] if len(args) > 2 else None
    if isinstance(detalhe, tuple) and len(detalhe) > 2 and detalhe[2]:
        origem = str(detalhe[1] or "").strip()
        texto = str(detalhe[2]).strip()
        return f"{origem}: {texto}" if origem else texto
    return str(error)


def recalcular(excel) -> None:
    """Recalcular o livro todo antes de gravar, para a cache ficar certa."""
    try:
        excel.CalculateFull()
    except Exception:
        pass


def reparar_formulas(path: Path) -> None:
    """Abrir, recalcular e gravar: repõe os valores das colunas com macros."""
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"Lista Material não encontrada:\n{path}")
    excel = importlib.import_module("win32com.client").DispatchEx("Excel.Application")
    book = None
    try:
        preparar_excel(excel)
        book = excel.Workbooks.Open(str(path.resolve()), UpdateLinks=0, ReadOnly=False)
        if book.ReadOnly:
            raise ValueError(
                "O Excel está aberto ou bloqueado. Guarde e feche a Lista Material "
                "e tente outra vez."
            )
        recalcular(excel)
        book.Save()
    finally:
        if book is not None:
            book.Close(False)
        excel.Quit()
