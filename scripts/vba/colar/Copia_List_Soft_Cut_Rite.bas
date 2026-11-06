Attribute VB_Name = "Copia_List_Soft_Cut_Rite"

       
        
        
Option Explicit

'=====================================================================
' LANÇA ENCANTO - Copiar Listagem de Peças para o programa CUT-RITE
'
' Função:
'   - Copia o conteúdo da tabela "Tabela_Cut_Rite" (folha LISTAGEM_CUT_RITE)
'     para a memória (equivalente a CTRL + C) para depois colar no CUT-RITE
'     com CTRL + V.
'
' Regras desta macro:
'   1) A tabela deve estar SEM filtros (remove automaticamente).
'   2) Copia sempre TODAS as linhas da tabela (não apenas as visíveis).
'   3) Antes de copiar, garante que a coluna N ("Grafico Orlas") contém
'      "111:111:000:000" em todas as linhas de dados.
'   4) Copia de A3 até à coluna +Larg (última que o Cut-Rite lê): W no modelo
'      de sempre, X no modelo de ensaio COLAR (coluna Colar a seguir à CNC_2).
'   5) Antes de copiar, confere os códigos da coluna Colar (modColar).
'
' Revisões:
'   - 2026-01-09: (Paulo / ChatGPT) Refatoração completa:
'       * removido Select/Selection desnecessário
'       * remoção automática de filtros antes de copiar
'       * cálculo da última linha com base no nº de linhas da tabela
'       * validação e preenchimento da coluna N (Grafico Orlas)
'       * tratamento de erros e restauro de settings
'   - 2026-11-06: (Martelo V3, ensaio COLAR) copia até ao +Larg, que no modelo
'       COLAR passa para a X; confere a coluna Colar antes de copiar.
'=====================================================================
Public Sub Copia_Listagem_Software_Cut_Rite()

    '--- Constantes principais (mantém fácil mudar se precisares)
    Const SH As String = "LISTAGEM_CUT_RITE"
    Const TBL As String = "Tabela_Cut_Rite"
    Const GRAFICO_ORLAS As String = "111:111:000:000"

    '--- Objetos
    Dim ws As Worksheet
    Dim lo As ListObject

    '--- Variáveis de apoio
    Dim lastRow As Long
    Dim rngCopy As Range
    Dim rngOrlas As Range
    Dim c As Range

    '--- Guardar estado do Excel (boa prática)
    Dim su As Boolean, ev As Boolean

    On Error GoTo EH

    '=========================================================
    ' 0) Guardar estado e otimizar performance
    '=========================================================
    su = Application.ScreenUpdating
    ev = Application.EnableEvents

    Application.ScreenUpdating = False
    Application.EnableEvents = False

    '=========================================================
    ' 1) Referências à folha e à tabela
    '=========================================================
    Set ws = ThisWorkbook.Worksheets(SH)
    Set lo = ws.ListObjects(TBL)

    '=========================================================
    ' 2) Validar: existe corpo de dados?
    '=========================================================
    If lo.DataBodyRange Is Nothing Then
        MsgBox "A tabela não tem dados para copiar.", vbExclamation, "CUT-RITE"
        GoTo CleanExit
    End If

    '=========================================================
    ' 3) Garantir SEM FILTROS (para copiar todas as linhas)
    '=========================================================
    On Error Resume Next
    If lo.ShowAutoFilter Then
        If lo.AutoFilter.FilterMode Then
            lo.AutoFilter.ShowAllData
        End If
    End If
    On Error GoTo EH

    '=========================================================
    ' 4) Calcular última linha real da tabela
    '    A tabela começa na linha 3 (primeira linha de dados)
    '    lastRow = 3 + nº linhas da tabela - 1
    '=========================================================
    lastRow = 3 + lo.ListRows.Count - 1

    '=========================================================
    ' 5) Garantir coluna N (Grafico Orlas) correta em todas as linhas
    '    Coluna N = 14
    '=========================================================
    Set rngOrlas = ws.Range("N3:N" & lastRow)

    For Each c In rngOrlas.Cells
        ' Se estiver vazio ou diferente, aplica o valor correto
        If CStr(c.Value) <> GRAFICO_ORLAS Then
            c.Value = GRAFICO_ORLAS
        End If
    Next c

    '=========================================================
    ' 6) Copiar de A3 até à coluna +Larg (W no modelo de sempre, X no COLAR),
    '    depois de conferir os códigos da coluna Colar
    '=========================================================
    Dim colFim As Long, problemas As String
    colFim = ColunaMaisLarg(lo)
    If colFim = 0 Then colFim = 23   ' W, como antes
    problemas = ColarProblemas(10)
    If Len(problemas) > 0 Then
        Application.ScreenUpdating = True
        If MsgBox("Coluna Colar - há códigos a corrigir:" & vbCrLf & vbCrLf & problemas & vbCrLf & _
                  "Copiar a listagem mesmo assim?", _
                  vbYesNo + vbExclamation + vbDefaultButton2, "CUT-RITE") <> vbYes Then
            GoTo CleanExit
        End If
    End If
    Set rngCopy = ws.Range(ws.Cells(3, 1), ws.Cells(lastRow, colFim))

    rngCopy.Copy   ' fica na memória (clipboard), pronto para CTRL+V no CutRite

    ' Opcional: posicionar cursor no início da zona copiada
    ws.Range("A3").Select

    MsgBox "Listagem copiada para a memória!" & vbCrLf & _
           "Agora abre o CutRite e faz CTRL + V.", _
           vbInformation, "CUT-RITE"

CleanExit:
    '=========================================================
    ' 7) Restaurar estado do Excel
    '=========================================================
    Application.EnableEvents = ev
    Application.ScreenUpdating = su
    Exit Sub

EH:
    MsgBox "Erro ao copiar listagem: " & Err.Number & vbCrLf & Err.Description, _
           vbCritical, "CUT-RITE"

    Resume CleanExit

End Sub

' Coluna (na folha) do "+Larg": a última que vai para o Cut-Rite; 0 = não há.
Private Function ColunaMaisLarg(ByVal lo As ListObject) As Long
    Dim i As Long, nome As String
    For i = 1 To lo.ListColumns.Count
        nome = Trim$(Replace(Replace(CStr(lo.ListColumns(i).Name), vbLf, ""), vbCr, ""))
        If LCase$(nome) = "+larg" Then
            ColunaMaisLarg = lo.ListColumns(i).Range.Column
            Exit Function
        End If
    Next i
End Function
