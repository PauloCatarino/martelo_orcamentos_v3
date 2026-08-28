Attribute VB_Name = "Import_List_Ferr_Etiq_11"
Option Explicit

'==============================================================================
' MÓDULO: Importação IMOS (Ferragens + Etiqueta)  07-01-2026 (revisto)
'------------------------------------------------------------------------------
' OBJETIVO:
'   Importar automaticamente para o ficheiro "Lista_Material*.xlsm" os ficheiros
'   gerados pelo IMOS IX, que estão na mesma pasta do ficheiro atual:
'     - "2_List_Ferragens*.xls*"  (normalmente .xlsx / pode ser .xlsm)
'     - "4_Etiqueta_Palete*.xls*"        (normalmente .xlsx / pode ser .xlsm)
'
' O QUE ESTA MACRO FAZ:
'   1) Desativa temporariamente atualizações do Excel para melhorar desempenho:
'        - ScreenUpdating = False
'        - EnableEvents = False
'        - DisplayAlerts = False
'        - Calculation = Manual
'
'   2) Elimina separadores antigos (se existirem) antes de importar:
'        - 1_FERRAGENS
'        - 2_PURCH
'        - 3_SPP
'        - 5_ETIQUETA_PALETE
'
'   3) Procura na pasta do ficheiro atual os ficheiros mais recentes que
'      correspondem aos padrões:
'        - 2_List_Ferragens*.xls*
'        - 4_Etiqueta_Palete*.xls*
'
'   4) Importa o ficheiro "2_List_Ferragens*.xls*", procurando os separadores
'      PELO NOME (o IMOS IX ja os entrega nomeados):
'        - "1_FERRAGENS" (ou "FERRAGENS")  -> "1_FERRAGENS"
'        - "2_PURCH"     (ou "PURCH")      -> "2_PURCH"
'        - "3_SPP"       (ou "SPP")        -> "3_SPP"
'      NEM SEMPRE existem os tres: importa apenas os que existirem.
'      Se o ficheiro vier sem nenhum destes nomes (ficheiros antigos do IMOS),
'      usa a ordem das folhas como antes (folha 1, 2 e 3).
'
'   5) Aplica ajustes de formatação/impressão nas folhas importadas:
'        - Remove colunas específicas
'        - Remove linhas específicas
'        - Ajusta alturas de linhas
'        - Define margens e escala de impressão
'        - Define repetição de linhas no cabeçalho (PrintTitleRows) em folhas
'          relevantes (ex.: 1_FERRAGENS e 3_SPP)
'
'   6) VALIDAÇÃO DE DADOS ÚTEIS (NOVO - simplificado):
'        - Para 1_FERRAGENS / 2_PURCH / 3_SPP:
'        - Considera "dados úteis" APENAS se existir valor na coluna "Qt."
'          com Qt > 0, a partir da linha 6 (inclusive).
'        - Se NÃO existir Qt > 0, pergunta ao utilizador se pretende:
'            SIM  -> manter o separador
'            NÃO  -> eliminar o separador
'
'   7) Importa o ficheiro "4_Etiqueta_Palete*.xls*" e copia a folha 1:
'        - Renomeada para "5_ETIQUETA_PALETE"
'      - Por defeito NÃO elimina a etiqueta mesmo que H6 esteja vazio
'        (REMOVER_ETIQUETA_SE_H6_VAZIA = False)
'
'   8) No fim, repõe os estados originais do Excel (mesmo em caso de erro).
'
' NOTAS IMPORTANTES:
'   - Todos os procedimentos auxiliares têm prefixo "IMOS_" para evitar conflitos
'     com outras macros no ficheiro/projeto.
'   - A macro insere as folhas importadas a seguir ao separador BASE_SHEET
'     ("LISTA_ORDENADA").
'   - Em caso de erro, mostra a etapa onde falhou e os caminhos completos dos
'     ficheiros que tentou abrir.
'==============================================================================




'=========================================================
' IMPORTAÇÃO IMOS: 1_List_Ferragens (até 3 folhas) + 5_Etiqueta
'=========================================================
Public Sub ImportarFicheiros_1_Ferragens_5_Etiqueta_Palete_11()

    Const BASE_SHEET As String = "LISTA_ORDENADA"
    Const PATTERN_FERRAGENS As String = "2_List_Ferragens*.xls*"
    Const PATTERN_ETIQUETA As String = "4_Etiqueta_Palete*.xls*"

    ' Layout típico IMOS
    Const HEADER_ROW As Long = 5            ' cabeçalho onde está "Qt."
    Const PRIMEIRA_LINHA_DADOS As Long = 6  ' dados começam aqui (inclusive)

    ' Formatação pedida
    Const ALTURA_LINHAS_FERRAGENS As Double = 60#
    Const REMOVER_ETIQUETA_SE_H6_VAZIA As Boolean = False
    Const MOSTRAR_RESUMO_FINAL As Boolean = False

    Dim wbAtual As Workbook
    Dim wbImportar As Workbook
    Dim abriuWB As Boolean

    Dim wsFerr As Worksheet, wsPurch As Worksheet, wsSpp As Worksheet
    Dim shAfter As Worksheet
    Dim wsEtiqueta As Worksheet

    Dim pasta As String, etapa As String
    Dim f1 As String, f2 As String
    Dim full1 As String, full2 As String

    ' Guardar estados do Excel
    Dim prevScreenUpdating As Boolean
    Dim prevEnableEvents As Boolean
    Dim prevDisplayAlerts As Boolean
    Dim prevCalc As XlCalculation

    ' Contagens para validação (Qt > 0)
    Dim srcFerr As Long, srcPurch As Long, srcSpp As Long
    Dim dstFerr As Long, dstPurch As Long, dstSpp As Long

    ' Guardar nomes em String (para não rebentar se a folha for apagada)
    Dim nomeFerr As String, nomePurch As String, nomeSpp As String

    ' Indice, dentro do ficheiro do IMOS, de cada separador (0 = nao existe)
    Dim idxFerr As Long, idxPurch As Long, idxSpp As Long

    On Error GoTo TrataErro

    Set wbAtual = ThisWorkbook
    pasta = wbAtual.Path

    If Len(pasta) = 0 Then
        MsgBox "O ficheiro Lista_Material ainda não foi guardado. Guarda-o primeiro para eu saber a pasta.", vbExclamation
        Exit Sub
    End If

    ' Guardar estados
    prevScreenUpdating = Application.ScreenUpdating
    prevEnableEvents = Application.EnableEvents
    prevDisplayAlerts = Application.DisplayAlerts
    prevCalc = Application.Calculation

    ' Otimização
    Application.ScreenUpdating = False
    Application.EnableEvents = False
    Application.DisplayAlerts = False
    Application.Calculation = xlCalculationManual

    '---------------------------
    ' 1) Limpar separadores antigos
    '---------------------------
    etapa = "Eliminar separadores antigos"
    IMOS_EliminarSeparador wbAtual, "1_FERRAGENS"
    IMOS_EliminarSeparador wbAtual, "2_PURCH"
    IMOS_EliminarSeparador wbAtual, "3_SPP"
    IMOS_EliminarSeparador wbAtual, "5_ETIQUETA_PALETE"

    '---------------------------
    ' 2) Encontrar ficheiros mais recentes
    '---------------------------
    etapa = "Procurar ficheiros na pasta"
    f1 = IMOS_GetNewestMatchingFile(pasta, PATTERN_FERRAGENS)
    f2 = IMOS_GetNewestMatchingFile(pasta, PATTERN_ETIQUETA)

    If f1 = "" Or f2 = "" Then
        Application.DisplayAlerts = True
        MsgBox "Ficheiros não encontrados na pasta:" & vbCrLf & _
               " - " & PATTERN_FERRAGENS & vbCrLf & _
               " - " & PATTERN_ETIQUETA & vbCrLf & vbCrLf & _
               "Pasta: " & pasta, vbExclamation
        GoTo LimparSair
    End If

    full1 = pasta & "\" & f1
    full2 = pasta & "\" & f2

    '---------------------------
    ' 3) Folha base para inserção
    '---------------------------
    etapa = "Definir folha base de inserção"
    If Not IMOS_FolhaExiste(wbAtual, BASE_SHEET) Then
        MsgBox "Não encontrei a folha base '" & BASE_SHEET & "' no ficheiro atual.", vbCritical
        GoTo LimparSair
    End If
    Set shAfter = wbAtual.Sheets(BASE_SHEET)

    '=========================================================
    ' 4) IMPORTAR 1_List_Ferragens (até 3 folhas)
    '=========================================================
    etapa = "Abrir 2_List_Ferragens"
    Set wbImportar = IMOS_AbrirWorkbookSeguro(full1, abriuWB)

    ' --- Que separadores existem mesmo neste ficheiro do IMOS?
    etapa = "Identificar separadores do IMOS"
    idxFerr = IMOS_IndiceFolhaPorNome(wbImportar, "FERRAGENS")
    idxPurch = IMOS_IndiceFolhaPorNome(wbImportar, "PURCH")
    idxSpp = IMOS_IndiceFolhaPorNome(wbImportar, "SPP")

    ' Ficheiros antigos do IMOS vinham sem nomes: ai vale a ordem das folhas.
    If idxFerr = 0 And idxPurch = 0 And idxSpp = 0 Then
        If wbImportar.Worksheets.Count >= 1 Then idxFerr = 1
        If wbImportar.Worksheets.Count >= 2 Then idxPurch = 2
        If wbImportar.Worksheets.Count >= 3 Then idxSpp = 3
    End If

    ' --- Contar Qt no ficheiro origem (para validação)
    If idxFerr > 0 Then srcFerr = IMOS_ContarLinhasQtPositiva(wbImportar.Worksheets(idxFerr), HEADER_ROW, PRIMEIRA_LINHA_DADOS)
    If idxPurch > 0 Then srcPurch = IMOS_ContarLinhasQtPositiva(wbImportar.Worksheets(idxPurch), HEADER_ROW, PRIMEIRA_LINHA_DADOS)
    If idxSpp > 0 Then srcSpp = IMOS_ContarLinhasQtPositiva(wbImportar.Worksheets(idxSpp), HEADER_ROW, PRIMEIRA_LINHA_DADOS)

    etapa = "Copiar folhas (2_List_Ferragens)"

    If idxFerr > 0 Then
        Set wsFerr = IMOS_CopiarFolhaComNome(wbImportar, idxFerr, wbAtual, shAfter, "1_FERRAGENS")
        Set shAfter = wsFerr
        dstFerr = IMOS_ContarLinhasQtPositiva(wsFerr, HEADER_ROW, PRIMEIRA_LINHA_DADOS)
    End If

    If idxPurch > 0 Then
        Set wsPurch = IMOS_CopiarFolhaComNome(wbImportar, idxPurch, wbAtual, shAfter, "2_PURCH")
        Set shAfter = wsPurch
        dstPurch = IMOS_ContarLinhasQtPositiva(wsPurch, HEADER_ROW, PRIMEIRA_LINHA_DADOS)
    End If

    If idxSpp > 0 Then
        Set wsSpp = IMOS_CopiarFolhaComNome(wbImportar, idxSpp, wbAtual, shAfter, "3_SPP")
        Set shAfter = wsSpp
        dstSpp = IMOS_ContarLinhasQtPositiva(wsSpp, HEADER_ROW, PRIMEIRA_LINHA_DADOS)
    End If

    ' --- Validação imediata (origem vs destino)
    etapa = "Validar contagem Qt (origem vs destino)"
    If (srcFerr <> 0 Or dstFerr <> 0) And (srcFerr <> dstFerr) Then
        MsgBox "ATENÇÃO (1_FERRAGENS): contagem de linhas com Qt>0 diferente!" & vbCrLf & _
               "Origem: " & srcFerr & "  |  Importado: " & dstFerr & vbCrLf & vbCrLf & _
               "Isto é grave: pode significar linhas perdidas. Verifica antes de continuar.", vbCritical
    End If
    If (srcPurch <> 0 Or dstPurch <> 0) And (srcPurch <> dstPurch) Then
        MsgBox "ATENÇÃO (2_PURCH): contagem de linhas com Qt>0 diferente!" & vbCrLf & _
               "Origem: " & srcPurch & "  |  Importado: " & dstPurch, vbCritical
    End If
    If (srcSpp <> 0 Or dstSpp <> 0) And (srcSpp <> dstSpp) Then
        MsgBox "ATENÇÃO (3_SPP): contagem de linhas com Qt>0 diferente!" & vbCrLf & _
               "Origem: " & srcSpp & "  |  Importado: " & dstSpp, vbCritical
    End If

    If abriuWB Then wbImportar.Close SaveChanges:=False
    Set wbImportar = Nothing

    '=========================================================
    ' 5) Ajustes pós-importação + limpeza de linhas finais
    '=========================================================
    etapa = "Ajustar folhas e limpar linhas finais"

    '-------------------------
    ' 1_FERRAGENS
    '-------------------------
    If Not wsFerr Is Nothing Then
        nomeFerr = wsFerr.Name ' <-- guarda ANTES de poder eliminar

        ' Ajustar larguras (pedido)
        IMOS_DefinirLargurasFerragens wsFerr

        ' Impressão / Página
        IMOS_AjustarMargens wsFerr
        IMOS_AjustarPrevisualizacaoImpressao wsFerr
        IMOS_ConfigurarPaginaWS wsFerr, 1, 5

        ' Limpar fim por Qt (remove lixo abaixo do último Qt>0)
        IMOS_LimparFimPorQt wsFerr, HEADER_ROW, PRIMEIRA_LINHA_DADOS

        ' Eliminar linha(s) "fantasma" no fim (ocultas / altura ~0, sem C/D/E)
        IMOS_EliminarLinhasFinaisVazias wsFerr, PRIMEIRA_LINHA_DADOS

        ' Altura 60 nas linhas com dados
        IMOS_DefinirAlturaLinhasDadosPorQt wsFerr, HEADER_ROW, PRIMEIRA_LINHA_DADOS, ALTURA_LINHAS_FERRAGENS

        ' Perguntar se quer manter caso não exista Qt>0
        If Not IMOS_PerguntarManterOuEliminarSeSemQt(wbAtual, nomeFerr, HEADER_ROW, PRIMEIRA_LINHA_DADOS) Then
            Set wsFerr = Nothing
        End If
    End If

    '-------------------------
    ' 2_PURCH
    '-------------------------
    If Not wsPurch Is Nothing Then
        nomePurch = wsPurch.Name ' <-- guarda ANTES de poder eliminar

        IMOS_AjustarMargens wsPurch
        IMOS_AjustarPrevisualizacaoImpressao wsPurch

        ' CORRIGIDO: antes estava wsSpp.Name (errado)
        IMOS_ConfigurarPaginaWS wsPurch, 1, 5

        IMOS_LimparFimPorQt wsPurch, HEADER_ROW, PRIMEIRA_LINHA_DADOS
        IMOS_EliminarLinhasFinaisVazias wsPurch, PRIMEIRA_LINHA_DADOS

        If Not IMOS_PerguntarManterOuEliminarSeSemQt(wbAtual, nomePurch, HEADER_ROW, PRIMEIRA_LINHA_DADOS) Then
            Set wsPurch = Nothing
        End If
    End If

    '-------------------------
    ' 3_SPP
    '-------------------------
    If Not wsSpp Is Nothing Then
        nomeSpp = wsSpp.Name ' <-- guarda ANTES de poder eliminar

        IMOS_AjustarMargens wsSpp
        IMOS_AjustarPrevisualizacaoImpressao wsSpp
        IMOS_ConfigurarPaginaWS wsSpp, 1, 5

        IMOS_LimparFimPorQt wsSpp, HEADER_ROW, PRIMEIRA_LINHA_DADOS
        IMOS_EliminarLinhasFinaisVazias wsSpp, PRIMEIRA_LINHA_DADOS

        If Not IMOS_PerguntarManterOuEliminarSeSemQt(wbAtual, nomeSpp, HEADER_ROW, PRIMEIRA_LINHA_DADOS) Then
            Set wsSpp = Nothing
        End If
    End If

    '=========================================================
    ' 6) Recalcular folha After (para inserir a etiqueta a seguir)
    '=========================================================
    etapa = "Recalcular folha After"
    Set shAfter = IMOS_GetUltimaFolhaImportada(wbAtual, BASE_SHEET)

    '=========================================================
    ' 7) IMPORTAR 5_Etiqueta
    '=========================================================
    etapa = "Abrir 4_Etiqueta_Palete"
    Set wbImportar = IMOS_AbrirWorkbookSeguro(full2, abriuWB)

    etapa = "Copiar etiqueta"
    Set wsEtiqueta = IMOS_CopiarFolhaComNome(wbImportar, 1, wbAtual, shAfter, "5_ETIQUETA_PALETE")

    If REMOVER_ETIQUETA_SE_H6_VAZIA Then
        If Len(Trim$(CStr(wsEtiqueta.Range("H6").Value2))) = 0 Then
            IMOS_EliminarSeparador wbAtual, "5_ETIQUETA_PALETE"
            Set wsEtiqueta = Nothing
        End If
    End If

    If Not wsEtiqueta Is Nothing Then
        etapa = "Ajustar impressão etiqueta"
        IMOS_AjustarMargens wsEtiqueta
        IMOS_AjustarPrevisualizacaoImpressao wsEtiqueta
    End If

    If abriuWB Then wbImportar.Close SaveChanges:=False
    Set wbImportar = Nothing

    '=========================================================
    ' 8) Ativar folha final
    '=========================================================
    If IMOS_FolhaExiste(wbAtual, "1_FERRAGENS") Then
        wbAtual.Sheets("1_FERRAGENS").Activate
    Else
        wbAtual.Sheets(BASE_SHEET).Activate
    End If

    If MOSTRAR_RESUMO_FINAL Then
        MsgBox "Importação concluída." & vbCrLf & _
               "Ferragens: " & f1 & vbCrLf & _
               "Etiqueta: " & f2, vbInformation
    End If

LimparSair:
    Application.Calculation = prevCalc
    Application.DisplayAlerts = prevDisplayAlerts
    Application.EnableEvents = prevEnableEvents
    Application.ScreenUpdating = prevScreenUpdating
    Exit Sub

TrataErro:
    Dim errNum As Long, errDesc As String
    errNum = Err.Number
    errDesc = Err.Description

    On Error Resume Next
    Application.Calculation = prevCalc
    Application.DisplayAlerts = prevDisplayAlerts
    Application.EnableEvents = prevEnableEvents
    Application.ScreenUpdating = prevScreenUpdating

    MsgBox "Erro na importação (" & etapa & "): " & errNum & " - " & errDesc & vbCrLf & vbCrLf & _
           "Pasta: " & pasta & vbCrLf & _
           "Ferragens: " & full1 & vbCrLf & _
           "Etiqueta: " & full2, vbCritical
End Sub


'=========================================================
' AUXILIARES IMOS_
'=========================================================

Private Function IMOS_AbrirWorkbookSeguro(ByVal fullPath As String, ByRef abriuAgora As Boolean) As Workbook
    Dim wb As Workbook
    abriuAgora = False

    If Len(Dir(fullPath)) = 0 Then
        Err.Raise vbObjectError + 101, "IMOS_AbrirWorkbookSeguro", "Ficheiro não encontrado: " & fullPath
    End If

    For Each wb In Application.Workbooks
        If LCase$(wb.FullName) = LCase$(fullPath) Then
            Set IMOS_AbrirWorkbookSeguro = wb
            Exit Function
        End If
    Next wb

    Set IMOS_AbrirWorkbookSeguro = Workbooks.Open( _
        fileName:=fullPath, _
        UpdateLinks:=0, _
        ReadOnly:=True, _
        IgnoreReadOnlyRecommended:=True, _
        AddToMru:=False, _
        Notify:=False _
    )
    abriuAgora = True
End Function

Private Function IMOS_GetNewestMatchingFile(ByVal folderPath As String, ByVal pattern As String) As String
    Dim f As String, bestFile As String
    Dim bestDT As Date

    bestDT = 0
    f = Dir(folderPath & "\" & pattern)

    Do While f <> ""
        If FileDateTime(folderPath & "\" & f) > bestDT Then
            bestDT = FileDateTime(folderPath & "\" & f)
            bestFile = f
        End If
        f = Dir()
    Loop

    IMOS_GetNewestMatchingFile = bestFile
End Function

Private Function IMOS_CopiarFolhaComNome(ByVal wbOrigem As Workbook, ByVal sheetIndex As Long, _
                                        ByVal wbDestino As Workbook, ByVal afterSheet As Worksheet, _
                                        ByVal novoNome As String) As Worksheet
    ' Copia a folha do wbOrigem para o wbDestino e renomeia.
    ' Se já existir uma folha com esse nome, apaga primeiro (para evitar erro de nome duplicado).
    If IMOS_FolhaExiste(wbDestino, novoNome) Then
        IMOS_EliminarSeparador wbDestino, novoNome
    End If

    wbOrigem.Worksheets(sheetIndex).Copy After:=afterSheet
    Set IMOS_CopiarFolhaComNome = wbDestino.ActiveSheet

    ' Renomear (pode falhar se workbook estiver com estrutura protegida)
    IMOS_CopiarFolhaComNome.Name = novoNome
End Function

'---------------------------------------------------------
' Indice da folha do ficheiro do IMOS que corresponde a
' "FERRAGENS", "PURCH" ou "SPP".
' O IMOS IX ja entrega os separadores com nome, mas nem
' sempre existem os tres. Devolve 0 quando nao existe.
'---------------------------------------------------------
Private Function IMOS_IndiceFolhaPorNome(ByVal wb As Workbook, ByVal alvo As String) As Long

    Dim i As Long

    For i = 1 To wb.Worksheets.Count
        If IMOS_NomeBaseFolha(wb.Worksheets(i).Name) = UCase$(Trim$(alvo)) Then
            IMOS_IndiceFolhaPorNome = i
            Exit Function
        End If
    Next i

    IMOS_IndiceFolhaPorNome = 0
End Function


'---------------------------------------------------------
' Nome do separador sem o numero da frente e sem espacos:
'   "1_FERRAGENS" / "1 Ferragens" / "Ferragens " -> "FERRAGENS"
'---------------------------------------------------------
Private Function IMOS_NomeBaseFolha(ByVal nome As String) As String

    Dim s As String

    s = UCase$(Trim$(nome))
    s = Replace(s, " ", "")
    s = Replace(s, "-", "_")

    Do While Len(s) > 0
        If Left$(s, 1) = "_" Or (Left$(s, 1) >= "0" And Left$(s, 1) <= "9") Then
            s = Mid$(s, 2)
        Else
            Exit Do
        End If
    Loop

    IMOS_NomeBaseFolha = s
End Function


Private Function IMOS_FolhaExiste(ByVal wb As Workbook, ByVal sheetName As String) As Boolean
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = wb.Sheets(sheetName)
    On Error GoTo 0
    IMOS_FolhaExiste = Not ws Is Nothing
End Function

Private Sub IMOS_EliminarSeparador(ByVal wb As Workbook, ByVal sheetName As String)
    Dim ws As Worksheet
    Dim prevAlerts As Boolean

    On Error Resume Next
    Set ws = wb.Sheets(sheetName)
    On Error GoTo 0
    If ws Is Nothing Then Exit Sub

    prevAlerts = Application.DisplayAlerts
    Application.DisplayAlerts = False
    ws.Delete
    Application.DisplayAlerts = prevAlerts
End Sub

Private Function IMOS_GetUltimaFolhaImportada(ByVal wb As Workbook, ByVal baseSheetName As String) As Worksheet
    If IMOS_FolhaExiste(wb, "3_SPP") Then
        Set IMOS_GetUltimaFolhaImportada = wb.Sheets("3_SPP")
    ElseIf IMOS_FolhaExiste(wb, "2_PURCH") Then
        Set IMOS_GetUltimaFolhaImportada = wb.Sheets("2_PURCH")
    ElseIf IMOS_FolhaExiste(wb, "1_FERRAGENS") Then
        Set IMOS_GetUltimaFolhaImportada = wb.Sheets("1_FERRAGENS")
    Else
        Set IMOS_GetUltimaFolhaImportada = wb.Sheets(baseSheetName)
    End If
End Function


'-----------------------------
' Formatação específica 1_FERRAGENS
'-----------------------------
Private Sub IMOS_DefinirLargurasFerragens(ByVal ws As Worksheet)
    On Error Resume Next
    ws.Columns("D").ColumnWidth = 12
    ws.Columns("E").ColumnWidth = 25
    ws.Columns("J").ColumnWidth = 20
    On Error GoTo 0
End Sub

Private Sub IMOS_RemoverColunasSeExistirem(ByVal ws As Worksheet, ByVal cols As Variant)
    ' Apagar da direita para a esquerda evita “saltos” de colunas durante o delete.
    Dim i As Long
    On Error Resume Next
    For i = UBound(cols) To LBound(cols) Step -1
        ws.Columns(CStr(cols(i))).Delete
    Next i
    On Error GoTo 0
End Sub

Private Sub IMOS_AjustarMargens(ByVal ws As Worksheet)
    With ws.PageSetup
        .LeftMargin = Application.InchesToPoints(0.25)
        .RightMargin = Application.InchesToPoints(0.25)
        .TopMargin = Application.InchesToPoints(0.35)
        .BottomMargin = Application.InchesToPoints(0.35)
        .HeaderMargin = Application.InchesToPoints(0.12)
        .FooterMargin = Application.InchesToPoints(0.12)
    End With
End Sub

Private Sub IMOS_AjustarPrevisualizacaoImpressao(ByVal ws As Worksheet)
    On Error Resume Next
    Application.PrintCommunication = False
    With ws.PageSetup
        .FitToPagesWide = 1
        .FitToPagesTall = False
    End With
    Application.PrintCommunication = True
    On Error GoTo 0
End Sub

Private Sub IMOS_ConfigurarPaginaWS(ByVal ws As Worksheet, ByVal linhaInicio As Long, ByVal linhaFim As Long)
    ' Versão segura: recebe Worksheet (não procura por nome).
    If ws Is Nothing Then Exit Sub
    With ws.PageSetup
        .PrintTitleRows = ws.Rows(linhaInicio & ":" & linhaFim).Address
        .CenterHeader = ""
        .CenterFooter = ""
    End With
End Sub


'=========================================================
' Funções Qt (dados úteis)
'=========================================================

Private Function IMOS_NormalizarCabecalho(ByVal v As Variant) As String
    Dim s As String
    s = LCase$(Trim$(CStr(v)))
    s = Replace(s, vbCr, " ")
    s = Replace(s, vbLf, " ")
    s = Replace(s, ".", "")
    s = Replace(s, ":", "")
    s = WorksheetFunction.Trim(s)
    IMOS_NormalizarCabecalho = s
End Function

Private Function IMOS_EncontrarColunaQt(ByVal ws As Worksheet, ByVal headerRow As Long) As Long
    Dim lastCell As Range
    Dim lastCol As Long, c As Long
    Dim txt As String

    Set lastCell = ws.Rows(headerRow).Find(What:="*", LookIn:=xlValues, SearchOrder:=xlByColumns, SearchDirection:=xlPrevious)
    If lastCell Is Nothing Then
        IMOS_EncontrarColunaQt = 0
        Exit Function
    End If
    lastCol = lastCell.Column

    For c = 1 To lastCol
        txt = IMOS_NormalizarCabecalho(ws.Cells(headerRow, c).Value2)
        If txt = "qt" Then
            IMOS_EncontrarColunaQt = c
            Exit Function
        End If
    Next c

    IMOS_EncontrarColunaQt = 0
End Function

Private Function IMOS_ContarLinhasQtPositiva(ByVal ws As Worksheet, ByVal headerRow As Long, ByVal primeiraLinhaDados As Long) As Long
    Dim qtCol As Long
    Dim lastRow As Long, r As Long
    Dim v As Variant
    Dim countQt As Long

    qtCol = IMOS_EncontrarColunaQt(ws, headerRow)
    If qtCol = 0 Then
        IMOS_ContarLinhasQtPositiva = 0
        Exit Function
    End If

    lastRow = ws.Cells(ws.Rows.Count, qtCol).End(xlUp).Row
    If lastRow < primeiraLinhaDados Then
        IMOS_ContarLinhasQtPositiva = 0
        Exit Function
    End If

    For r = primeiraLinhaDados To lastRow
        v = ws.Cells(r, qtCol).Value2
        If IsNumeric(v) Then
            If CDbl(v) > 0 Then countQt = countQt + 1
        End If
    Next r

    IMOS_ContarLinhasQtPositiva = countQt
End Function

Private Function IMOS_UltimaLinhaQtPositiva(ByVal ws As Worksheet, ByVal qtCol As Long, ByVal primeiraLinhaDados As Long) As Long
    Dim lastRow As Long, r As Long
    Dim v As Variant

    lastRow = ws.Cells(ws.Rows.Count, qtCol).End(xlUp).Row
    If lastRow < primeiraLinhaDados Then
        IMOS_UltimaLinhaQtPositiva = 0
        Exit Function
    End If

    For r = lastRow To primeiraLinhaDados Step -1
        v = ws.Cells(r, qtCol).Value2
        If IsNumeric(v) Then
            If CDbl(v) > 0 Then
                IMOS_UltimaLinhaQtPositiva = r
                Exit Function
            End If
        End If
    Next r

    IMOS_UltimaLinhaQtPositiva = 0
End Function


'=========================================================
' Limpeza do fim da folha (linhas vazias / coladas / ocultas)
'=========================================================
Private Sub IMOS_LimparFimPorQt(ByVal ws As Worksheet, ByVal headerRow As Long, ByVal primeiraLinhaDados As Long)

    Dim qtCol As Long
    Dim lastDataRow As Long
    Dim lastUsedCell As Range
    Dim lastUsedRow As Long
    Dim startDel As Long

    On Error Resume Next
    ws.Rows.Hidden = False
    ws.Columns.Hidden = False
    ws.Cells.ClearOutline
    On Error GoTo 0

    qtCol = IMOS_EncontrarColunaQt(ws, headerRow)
    If qtCol = 0 Then Exit Sub

    lastDataRow = IMOS_UltimaLinhaQtPositiva(ws, qtCol, primeiraLinhaDados)
    If lastDataRow = 0 Then Exit Sub

    Set lastUsedCell = ws.Cells.Find(What:="*", LookIn:=xlValues, SearchOrder:=xlByRows, SearchDirection:=xlPrevious)
    If lastUsedCell Is Nothing Then Exit Sub

    lastUsedRow = lastUsedCell.Row
    startDel = lastDataRow + 1

    If lastUsedRow < startDel Then Exit Sub

    ' Evitar problemas com merges no fim (linhas coladas)
    On Error Resume Next
    ws.Rows(lastDataRow & ":" & lastUsedRow).UnMerge
    On Error GoTo 0

    On Error Resume Next
    ws.Rows(startDel & ":" & lastUsedRow).Delete
    On Error GoTo 0

End Sub


'=========================================================
' Altura das linhas do 1_FERRAGENS (linha 6 até última Qt>0)
'=========================================================
Private Sub IMOS_DefinirAlturaLinhasDadosPorQt(ByVal ws As Worksheet, _
                                               ByVal headerRow As Long, _
                                               ByVal primeiraLinhaDados As Long, _
                                               ByVal altura As Double)

    Dim qtCol As Long
    Dim lastDataRow As Long

    qtCol = IMOS_EncontrarColunaQt(ws, headerRow)
    If qtCol = 0 Then Exit Sub

    lastDataRow = IMOS_UltimaLinhaQtPositiva(ws, qtCol, primeiraLinhaDados)
    If lastDataRow = 0 Then Exit Sub

    On Error Resume Next
    ws.Rows(primeiraLinhaDados & ":" & lastDataRow).Hidden = False
    ws.Rows(primeiraLinhaDados & ":" & lastDataRow).RowHeight = altura
    On Error GoTo 0

End Sub


'=========================================================
' Perguntar ao utilizador se quer manter/eliminar separador vazio (sem Qt>0)
'  - DEVOLVE:
'      True  -> folha mantida (existe no fim)
'      False -> folha eliminada ou não existe
'=========================================================
Private Function IMOS_PerguntarManterOuEliminarSeSemQt(ByVal wb As Workbook, _
                                                      ByVal sheetName As String, _
                                                      ByVal headerRow As Long, _
                                                      ByVal primeiraLinhaDados As Long) As Boolean

    Dim ws As Worksheet
    Dim qtCount As Long
    Dim resp As VbMsgBoxResult

    ' Se não existir, devolve False
    If Not IMOS_FolhaExiste(wb, sheetName) Then
        IMOS_PerguntarManterOuEliminarSeSemQt = False
        Exit Function
    End If

    Set ws = wb.Sheets(sheetName)

    qtCount = IMOS_ContarLinhasQtPositiva(ws, headerRow, primeiraLinhaDados)

    If qtCount = 0 Then
        resp = MsgBox("Não encontrei dados úteis no separador '" & sheetName & "'." & vbCrLf & _
                      "Critério: Qt. > 0 a partir da linha " & primeiraLinhaDados & "." & vbCrLf & vbCrLf & _
                      "Pretende manter este separador?" & vbCrLf & _
                      "SIM = Manter | NÃO = Eliminar", vbYesNo + vbQuestion)

        If resp = vbNo Then
            IMOS_EliminarSeparador wb, sheetName
            IMOS_PerguntarManterOuEliminarSeSemQt = False
            Exit Function
        End If
    End If

    ' Se chegou aqui, é porque a folha ficou
    IMOS_PerguntarManterOuEliminarSeSemQt = IMOS_FolhaExiste(wb, sheetName)
End Function


'=========================================================
' ELIMINAR LINHAS "FANTASMA" NO FIM DA FOLHA
'---------------------------------------------------------
' PROBLEMA:
'   O IMOS gera muitas vezes, a seguir à última linha de dados,
'   uma linha extra que fica OCULTA ou com altura quase nula
'   (normalmente criada pela imagem/moldura da última linha).
'   Ex.: linha 41 no 1_FERRAGENS, linha 11 no 3_SPP.
'
' REGRA (pedido do utilizador):
'   Se a linha NÃO tiver conteúdo em NENHUMA das colunas
'   C, D ou E  ->  pode ser eliminada.
'
' COMO FUNCIONA:
'   - Percorre de BAIXO para CIMA a partir da última linha usada
'     (considera valores, formatação e imagens).
'   - Elimina cada linha sem conteúdo em C/D/E.
'   - PÁRA na primeira linha que tenha conteúdo em C, D ou E.
'   - Limite de segurança: maxEliminar linhas.
'=========================================================
Private Sub IMOS_EliminarLinhasFinaisVazias(ByVal ws As Worksheet, _
                                            ByVal primeiraLinhaDados As Long, _
                                            Optional ByVal maxEliminar As Long = 30)

    Dim lastRow As Long
    Dim r As Long
    Dim eliminadas As Long

    If ws Is Nothing Then Exit Sub

    ' Nada pode ficar escondido antes de avaliar
    On Error Resume Next
    ws.Rows.Hidden = False
    ws.Cells.ClearOutline
    On Error GoTo 0

    lastRow = IMOS_UltimaLinhaReal(ws)
    If lastRow <= primeiraLinhaDados Then Exit Sub

    For r = lastRow To primeiraLinhaDados Step -1

        If IMOS_LinhaTemConteudo_CDE(ws, r) Then Exit For

        On Error Resume Next
        IMOS_ApagarImagensDaLinha ws, r      ' imagens ancoradas nessa linha
        ws.Rows(r).UnMerge                   ' evita erros com células unidas
        ws.Rows(r).Delete
        On Error GoTo 0

        eliminadas = eliminadas + 1
        If eliminadas >= maxEliminar Then Exit For
    Next r

End Sub


'---------------------------------------------------------
' A linha tem conteúdo em C, D ou E ?
'---------------------------------------------------------
Private Function IMOS_LinhaTemConteudo_CDE(ByVal ws As Worksheet, ByVal r As Long) As Boolean

    Dim c As Long

    For c = 3 To 5                      ' C, D, E
        If Len(Trim$(CStr(ws.Cells(r, c).Value2))) > 0 Then
            IMOS_LinhaTemConteudo_CDE = True
            Exit Function
        End If
    Next c

    IMOS_LinhaTemConteudo_CDE = False
End Function


'---------------------------------------------------------
' Última linha REAL da folha:
'   maior valor entre UsedRange (apanha linhas só com
'   formatação/moldura), Find (valores) e as imagens.
'---------------------------------------------------------
Private Function IMOS_UltimaLinhaReal(ByVal ws As Worksheet) As Long

    Dim lastRow As Long
    Dim c As Range
    Dim shp As Shape
    Dim rShp As Long

    On Error Resume Next

    lastRow = ws.UsedRange.Row + ws.UsedRange.Rows.Count - 1

    Set c = ws.Cells.Find(What:="*", LookIn:=xlFormulas, _
                          SearchOrder:=xlByRows, SearchDirection:=xlPrevious)
    If Not c Is Nothing Then
        If c.Row > lastRow Then lastRow = c.Row
    End If

    For Each shp In ws.Shapes
        rShp = 0
        rShp = shp.BottomRightCell.Row
        If rShp > lastRow Then lastRow = rShp
    Next shp

    On Error GoTo 0

    IMOS_UltimaLinhaReal = lastRow
End Function


'---------------------------------------------------------
' Apaga imagens/formas cuja âncora superior está na linha r
' (evita ficarem "penduradas" depois de eliminar a linha)
'---------------------------------------------------------
Private Sub IMOS_ApagarImagensDaLinha(ByVal ws As Worksheet, ByVal r As Long)

    Dim i As Long
    Dim linhaTopo As Long

    On Error Resume Next
    For i = ws.Shapes.Count To 1 Step -1
        linhaTopo = 0
        linhaTopo = ws.Shapes(i).TopLeftCell.Row
        If linhaTopo = r Then ws.Shapes(i).Delete
    Next i
    On Error GoTo 0

End Sub


'=========================================================
' MACRO MANUAL (opcional)
'---------------------------------------------------------
' Corre a limpeza das linhas finais nos separadores
' 1_FERRAGENS / 2_PURCH / 3_SPP já importados,
' sem ser preciso repetir a importação.
'=========================================================
Public Sub IMOS_LimparLinhasFinais_Ferragens()

    Const PRIMEIRA_LINHA_DADOS As Long = 6

    Dim nomes As Variant
    Dim i As Long
    Dim wb As Workbook
    Dim prevScreen As Boolean

    Set wb = ThisWorkbook
    nomes = Array("1_FERRAGENS", "2_PURCH", "3_SPP")

    prevScreen = Application.ScreenUpdating
    Application.ScreenUpdating = False

    For i = LBound(nomes) To UBound(nomes)
        If IMOS_FolhaExiste(wb, CStr(nomes(i))) Then
            IMOS_EliminarLinhasFinaisVazias wb.Worksheets(CStr(nomes(i))), PRIMEIRA_LINHA_DADOS
        End If
    Next i

    Application.ScreenUpdating = prevScreen

End Sub







