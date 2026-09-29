Attribute VB_Name = "modulo"
' ============================
' MÓDULO: rotinas utilitárias e actualizações
' ============================

' Função robusta para obter valor de um Name definido (Name Manager)
' Tenta RefersToRange, depois interpreta RefersTo e por fim faz fallback em DEFENICOES.
Function GetDefinedNameValue(ByVal sName As String, Optional ByVal sSheet As String = "DEFENICOES", Optional ByVal sCell As String = "P3") As String
    Dim nm As Name
    Dim rng As Range
    Dim ref As String
    On Error Resume Next
    
    Set nm = ThisWorkbook.Names(sName)
    If Not nm Is Nothing Then
        ' 1) Se o Name aponta para um Range
        On Error Resume Next
        Set rng = Nothing
        Set rng = nm.RefersToRange
        On Error GoTo 0
        If Not rng Is Nothing Then
            GetDefinedNameValue = CStr(rng.Value)
            Exit Function
        End If
        
        ' 2) Se o Name é algo como ="texto" ou uma formula
        ref = nm.RefersTo
        If Len(ref) > 0 Then
            If Left(ref, 1) = "=" Then
                ref = Mid(ref, 2)
                If Left(ref, 1) = """" Then
                    GetDefinedNameValue = Replace(ref, """", "")
                    Exit Function
                End If
                On Error Resume Next
                GetDefinedNameValue = CStr(Application.Evaluate("=" & ref))
                If Err.Number = 0 Then
                    Exit Function
                Else
                    Err.Clear
                End If
                On Error GoTo 0
            End If
        End If
    End If
    
    ' 3) Fallback: ler directamente da folha DEFENICOES na célula indicada
    On Error Resume Next
    GetDefinedNameValue = CStr(ThisWorkbook.Worksheets(sSheet).Range(sCell).Value)
    On Error GoTo 0
End Function

' Atualiza as 3 colunas na Tabela_Cut_Rite (LISTAGEM_CUT_RITE)
Sub Atualizar_Colunas_Cliente_EncPHC_RefCliente()
    Dim ws As Worksheet
    Dim lo As ListObject
    Dim hdrRow As Long, firstDataRow As Long, lastRow As Long
    Dim c As Long, colClienteIdx As Long, colEncIdx As Long, colRefIdx As Long
    Dim clienteVal As String, encVal As String, refVal As String
    Dim tblLeftCol As Long, tblColsCount As Long, hdrCol As Long
    
    On Error GoTo ErrHandler
    Set ws = ThisWorkbook.Worksheets("LISTAGEM_CUT_RITE")
    Set lo = ws.ListObjects("Tabela_Cut_Rite")
    
    hdrRow = lo.HeaderRowRange.Row
    firstDataRow = hdrRow + 1
    
    ' Actualiza referências da tabela depois de eventuais resize
    tblLeftCol = lo.Range.Column
    tblColsCount = lo.Range.Columns.Count
    
    ' Localiza colunas (faz loop pelas colunas reais da tabela)
    colClienteIdx = 0: colEncIdx = 0: colRefIdx = 0
    For c = tblLeftCol To (tblLeftCol + tblColsCount - 1)
        hdrCol = c
        Select Case UCase(Trim(CStr(ws.Cells(hdrRow, hdrCol).Value)))
            Case "CLIENTE"
                colClienteIdx = hdrCol
            Case "ENC_PHC", "ENC PHC"
                colEncIdx = hdrCol
            Case "REF_CLIENTE", "REF CLIENTE"
                colRefIdx = hdrCol
        End Select
    Next c
    
    ' Pega os valores dos Names (com fallback para DEFENICOES)
    clienteVal = GetDefinedNameValue("NOME_CLIENTE_SIMPLEX", "DEFENICOES", "E3")
    encVal = GetDefinedNameValue("PLANO_CORTE", "DEFENICOES", "P3")
    If Len(encVal) >= 13 Then
        encVal = Left(encVal, 13)
    End If
    refVal = GetDefinedNameValue("REF_CLIENTE", "DEFENICOES", "C3")
    
    ' Se não houver dados na tabela, evita erro
    lastRow = lo.Range.Row + lo.Range.Rows.Count - 1
    If lastRow < firstDataRow Then Exit Sub
    
    ' Preenche as colunas (apenas as células do corpo da tabela)
    If colClienteIdx <> 0 Then
        ws.Range(ws.Cells(firstDataRow, colClienteIdx), ws.Cells(lastRow, colClienteIdx)).Value = clienteVal
    End If
    If colEncIdx <> 0 Then
        ws.Range(ws.Cells(firstDataRow, colEncIdx), ws.Cells(lastRow, colEncIdx)).Value = encVal
    End If
    If colRefIdx <> 0 Then
        ws.Range(ws.Cells(firstDataRow, colRefIdx), ws.Cells(lastRow, colRefIdx)).Value = refVal
    End If
    
    Exit Sub
ErrHandler:
    MsgBox "Erro em Atualizar_Colunas_Cliente_EncPHC_RefCliente: " & Err.Description, vbExclamation
End Sub

' Versão melhorada do CopiarParaListaCutRite_5 (após copiar colunas e fazer resize)
Sub CopiarParaListaCutRite_5()
    Dim wsListaOrdenada As Worksheet
    Dim wsListaCutRite As Worksheet
    Dim ultimaLinha As Long
    Dim ultimaColuna As Long
    Dim i As Long, j As Long
    Dim lo As ListObject
    Dim lastRow As Long
    Dim firstDataRow As Long
    Dim totalRows As Long
    Dim totalCols As Long
    Dim hdrRow As Long
    Dim tblLeftCol As Long
    
    ' Definir as worksheets a serem utilizadas
    Set wsListaOrdenada = ThisWorkbook.Sheets("LISTA_ORDENADA")
    Set wsListaCutRite = ThisWorkbook.Sheets("LISTAGEM_CUT_RITE")
    
    ' Encontrar a última linha e a última coluna na worksheet "LISTA_ORDENADA"
    ultimaLinha = wsListaOrdenada.Cells(wsListaOrdenada.Rows.Count, "B").End(xlUp).Row
    ultimaColuna = wsListaOrdenada.Cells(3, wsListaOrdenada.Columns.Count).End(xlToLeft).Column
    
    ' Copiar cada coluna da "LISTA_ORDENADA" para a "LISTAGEM_CUT_RITE"
    For j = 2 To ultimaColuna
        ' Encontrar a coluna correspondente na "LISTAGEM_CUT_RITE"
        For i = 1 To 21
            If wsListaOrdenada.Cells(3, j).Value = wsListaCutRite.Cells(2, i).Value Then
                ' Copiar a coluna correspondente
                wsListaOrdenada.Range(wsListaOrdenada.Cells(4, j), wsListaOrdenada.Cells(ultimaLinha, j)).Copy
                wsListaCutRite.Cells(3, i).PasteSpecial xlPasteValuesAndNumberFormats
                Exit For
            End If
        Next i
    Next j
    
    Set lo = wsListaCutRite.ListObjects("Tabela_Cut_Rite")

    ' A tabela começa no cabeçalho (linha 2). Os dados começam na linha 3.
    firstDataRow = lo.HeaderRowRange.Row + 1

    ' Última linha com dados (assumo que alguma coluna da tabela tem dados)
    lastRow = wsListaCutRite.Cells(wsListaCutRite.Rows.Count, lo.Range.Column).End(xlUp).Row

    ' Se não houver dados, evita erro
    If lastRow < firstDataRow Then
        ' Se não há dados, redimensiona para incluir apenas o cabeçalho
        On Error Resume Next
        lo.Resize lo.Range.Resize(1, lo.Range.Columns.Count)
        On Error GoTo 0
        Exit Sub
    End If

    totalRows = (lastRow - lo.HeaderRowRange.Row) + 1   ' +1 para incluir o cabeçalho
    totalCols = lo.Range.Columns.Count
    tblLeftCol = lo.Range.Column
    
    ' Redimensiona a tabela mantendo o mesmo nº de colunas
    On Error Resume Next
    lo.Resize lo.Range.Resize(totalRows, totalCols)
    On Error GoTo 0

    ' Re-obter o objecto da tabela (para garantir referências actualizadas)
    Set lo = wsListaCutRite.ListObjects("Tabela_Cut_Rite")
    
    ' Aplicar um estilo leve e desactivar stripes do estilo da tabela (para não sobrepor o nosso pincel)
    On Error Resume Next
    lo.TableStyle = "TableStyleLight1"   ' podes trocar por outra se preferires (ver ListTableStyles)
    lo.ShowTableStyleRowStripes = False
    lo.ShowTableStyleColumnStripes = False
    On Error GoTo 0
    
    ' Reaplica o pincel (alternância de linhas)
    Call AplicarPincelFormatacao_CutRite

    ' Atualiza as 3 colunas do cliente / enc_phc / ref
    Call Atualizar_Colunas_Cliente_EncPHC_RefCliente

End Sub

' Reaplica a alternancia de linhas (zebra) na Tabela_Cut_Rite.
' A CopiarParaListaCutRite_5 chamava esta macro, mas ela nao existia no
' modelo e o projeto VBA nao compilava (Depurar > Compilar dava "Sub or
' Function not defined"). Faz o mesmo que o botao AUTOMATION faz hoje
' (ReaplicarVisual_CutRite, no modCutRite_Mapeamento): tira o preenchimento
' fixo das linhas e repoe o estilo da tabela com linhas alternadas.
Private Sub AplicarPincelFormatacao_CutRite()
    Dim lo As ListObject

    On Error Resume Next
    Set lo = ThisWorkbook.Sheets("LISTAGEM_CUT_RITE").ListObjects("Tabela_Cut_Rite")
    If lo Is Nothing Then Exit Sub
    If lo.DataBodyRange Is Nothing Then Exit Sub

    lo.DataBodyRange.Interior.pattern = xlNone
    lo.DataBodyRange.Interior.ColorIndex = xlColorIndexNone
    lo.TableStyle = "TableStyleMedium1"
    lo.ShowTableStyleRowStripes = True
    On Error GoTo 0
End Sub

' Lista estilos de tabela (imprimir no Immediate Window) - útil para escolher nome de estilo correcto
Sub ListTableStyles()
    Dim t As TableStyle
    For Each t In ActiveWorkbook.TableStyles
        Debug.Print t.Name
    Next t
    MsgBox "Lista de TableStyles enviada ao Immediate Window (Ctrl+G)."
End Sub
