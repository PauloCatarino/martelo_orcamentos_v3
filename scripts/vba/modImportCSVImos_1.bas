Attribute VB_Name = "modImportCSVImos_1"
Option Explicit

'====================================================================
'  LANÇA ENCANTO - IMPORTAÇÃO CSV IMOS -> LISTA_ORDENADA 09-01-2026
'--------------------------------------------------------------------
'  Macro principal:
'    Import_CSV_Imos_1
'
'  O que faz:
'   1) Cria (ou recria) um separador com nome = NOME_ENC_IMOS_IX
'      (antes do separador LISTA_ORDENADA)
'   2) Limpa dados antigos (import e LISTA_ORDENADA)
'   3) Importa o CSV do IMOS (delimitado por ; )
'   4) NOVO (Revisão 2026-01-09):
'        - Verifica a coluna "Qt." (quantidade)
'        - Se existirem linhas com Qt.=0 pergunta ao utilizador:
'            "Pretendo importar as linhas com Qt.=0 ?  Sim / Não"
'          (por defeito ativo o botão NÃO)
'            * SIM = mantém/importa linhas com Qt.=0
'            * NÃO = elimina linhas com Qt.=0 no import
'   5) Corrige RP (coluna "RP" no import) -> fica sempre o texto depois do "."
'   6) Verifica/Corrige Notas com "Rasgo ...mm" usando regra:
'         Rasgo = (espessura do FUNDO GAVETA) + 1
'      (procura a espessura em linhas "Gaveteiro Fundo Gaveta" por RP)
'   7) Ordena por sequência da DEFENICOES!A4:A... e copia para LISTA_ORDENADA
'      (valores apenas) e com mapeamento RP -> Artigo
'   8) Converte o "Veio" na LISTA_ORDENADA (coluna H):
'         "1" -> "S" / "0" -> "N"
'      e aplica exceções onde o veio não interessa (força "N")
'====================================================================

'>>> AJUSTA AQUI O CAMINHO DA PASTA DOS CSV
Private Const PASTA_CSV As String = "I:\Cutrite\Work\Cutrite_Import_CSV\"

'--------------------------
' MACRO PRINCIPAL
'--------------------------
Public Sub Import_CSV_Imos_1()

    Dim oldCalc As XlCalculation
    oldCalc = Application.Calculation

    On Error GoTo EH

    Dim numProcesso As String
    numProcesso = GetNomeado_Texto("NOME_ENC_IMOS_IX")
    If Len(Trim$(numProcesso)) = 0 Then
        MsgBox "A variável NOME_ENC_IMOS_IX está vazia (DEFENICOES!E3).", vbCritical
        Exit Sub
    End If

    Application.ScreenUpdating = False
    Application.EnableEvents = False
    Application.Calculation = xlCalculationManual

    Dim wsImport As Worksheet
    Set wsImport = RecriarFolhaImport(numProcesso, "LISTA_ORDENADA")

    ' 1) Limpezas
    LimparFolhaImport wsImport
    LimparListaOrdenada ThisWorkbook.Worksheets("LISTA_ORDENADA")

    ' 2) Encontrar CSV
    Dim caminhoCSV As String
    caminhoCSV = EncontrarCSVPorProcesso(PASTA_CSV, numProcesso)

    If Len(caminhoCSV) = 0 Then
        MsgBox "Não encontrei nenhum CSV na pasta:" & vbCrLf & PASTA_CSV & vbCrLf & _
               "que contenha: " & numProcesso, vbCritical
        GoTo CleanExit
    End If

    ' 3) Importar CSV para wsImport (a partir de A2)
    ImportarCSV_ParaFolha wsImport, caminhoCSV

    ' 4) NOVO: Verificar/Tratar linhas com Qt.=0 (pergunta SIM/NÃO)
    Tratar_Linhas_Qt_Zero wsImport

    ' 5) Corrigir RP (coluna "RP" no import)
    CorrigirColunaRP wsImport

    ' 6) Verificar/Corrigir Notas Rasgo (abre UserForm se houver correções)
    VerificarECorrigir_Rasgo_Em_Notas wsImport

    ' 7) Copiar ordenado para LISTA_ORDENADA
    Criar_Lista_Ordenada wsImport, ThisWorkbook.Worksheets("DEFENICOES"), ThisWorkbook.Worksheets("LISTA_ORDENADA")

    ' 8) Converter Veio (LISTA_ORDENADA col H)
    Converter_Veio_ListaOrdenada ThisWorkbook.Worksheets("LISTA_ORDENADA")
    Application.StatusBar = "Importação concluída com sucesso para: " & numProcesso
    On Error Resume Next
    CreateObject("WScript.Shell").Popup _
        "Importação concluída com sucesso para: " & numProcesso, _
        1, "Microsoft Excel", vbInformation
    On Error GoTo EH
CleanExit:
    Application.Calculation = oldCalc
    Application.EnableEvents = True
    Application.ScreenUpdating = True
    Exit Sub

EH:
    MsgBox "Erro em Import_CSV_Imos_1:" & vbCrLf & Err.Number & " - " & Err.Description, vbExclamation
    Resume CleanExit

End Sub

'====================================================================
'  NOVO: TRATAR LINHAS COM Qt.=0 (pergunta SIM/NÃO)
'====================================================================
Private Sub Tratar_Linhas_Qt_Zero(ByVal ws As Worksheet)

    On Error GoTo EH

    Const HEADER_ROW As Long = 2  ' cabeçalhos do import ficam na linha 2
    Dim colQt As Long

    ' Tentativa 1: match flexível (Qt. / Qt / QT)
    colQt = FindColByHeaderFlex(ws, HEADER_ROW, Array("Qt.", "Qt", "QT"))

    ' Se não encontrou, tenta outros nomes típicos (só por segurança)
    If colQt = 0 Then
        colQt = FindColByHeaderFlex(ws, HEADER_ROW, Array("Qtd", "QTD", "Quantidade", "QUANTIDADE"))
    End If

    ' Se mesmo assim não encontrou, não faz nada (não rebenta a macro)
    If colQt = 0 Then Exit Sub

    ' Última linha (usar a coluna 1 "Descricao" para garantir que apanha tudo)
    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    If lastRow < 3 Then Exit Sub

    ' 1) Contar linhas com Qt=0 (ignorar linhas vazias)
    Dim r As Long
    Dim countZero As Long
    Dim desc As String
    Dim qtVal As Double

    countZero = 0

    For r = 3 To lastRow
        desc = Trim$(CStr(ws.Cells(r, 1).Value)) ' coluna Descricao do import (normalmente col 1)
        If Len(desc) > 0 Then
            qtVal = CDbl(Val(ws.Cells(r, colQt).Value))
            If qtVal = 0 Then
                countZero = countZero + 1
            End If
        End If
    Next r

    If countZero = 0 Then Exit Sub

    ' 2) Perguntar ao utilizador (por defeito botão NÃO)
    Dim resp As VbMsgBoxResult
    resp = MsgBox( _
        "Foram encontradas " & countZero & " linha(s) com Qt.=0." & vbCrLf & vbCrLf & _
        "Isto acontece normalmente quando no IMOS IX o campo 'Quantity in BOM' foi colocado a 0." & vbCrLf & vbCrLf & _
        "Pretende importar as linhas com Qt.=0 ?" & vbCrLf & _
        "  SIM  = Importa as linhas com Qt.=0" & vbCrLf & _
        "  NÃO  = Elimina as linhas com Qt.=0", _
        vbYesNo + vbQuestion + vbDefaultButton2, _
        "IMOS -> Importação CSV (Qt.=0)" _
    )

    ' 3) Se NÃO, eliminar linhas (de baixo para cima)
    If resp = vbNo Then
        For r = lastRow To 3 Step -1
            desc = Trim$(CStr(ws.Cells(r, 1).Value))
            If Len(desc) > 0 Then
                qtVal = CDbl(Val(ws.Cells(r, colQt).Value))
                If qtVal = 0 Then
                    ws.Rows(r).Delete
                End If
            End If
        Next r
    End If

    Exit Sub

EH:
    ' Se falhar por qualquer motivo, não bloqueia a importação toda.
End Sub

'====================================================================
'  FUNÇÕES DE SUPORTE - NOMES / FOLHAS / LIMPEZAS
'====================================================================

Private Function GetNomeado_Texto(ByVal nome As String) As String
    ' Lê um Named Range (Gestor de Nomes) de forma segura
    On Error GoTo Falha
    GetNomeado_Texto = CStr(ThisWorkbook.Names(nome).RefersToRange.Value)
    Exit Function
Falha:
    GetNomeado_Texto = ""
End Function

Private Function FolhaExiste(ByVal nomeFolha As String) As Boolean
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(nomeFolha)
    FolhaExiste = Not ws Is Nothing
    On Error GoTo 0
End Function

Private Function RecriarFolhaImport(ByVal nomeFolha As String, ByVal folhaReferencia As String) As Worksheet
    ' Apaga a folha se já existir e cria uma nova ANTES da folhaReferencia

    Dim wsRef As Worksheet
    Set wsRef = ThisWorkbook.Worksheets(folhaReferencia)

    Application.DisplayAlerts = False
    If FolhaExiste(nomeFolha) Then
        ThisWorkbook.Worksheets(nomeFolha).Delete
    End If
    Application.DisplayAlerts = True

    Dim wsNovo As Worksheet
    Set wsNovo = ThisWorkbook.Worksheets.Add(Before:=wsRef)
    wsNovo.Name = nomeFolha

    Set RecriarFolhaImport = wsNovo
End Function

Private Sub LimparFolhaImport(ByVal ws As Worksheet)
    ' Limpa dados antigos sem destruir totalmente o separador
    ' (limpa também QueryTables antigas para não acumular)
    On Error Resume Next

    Dim qt As QueryTable
    For Each qt In ws.QueryTables
        qt.Delete
    Next qt

    On Error GoTo 0

    ws.Cells.ClearContents
End Sub

Private Sub LimparListaOrdenada(ByVal wsLO As Worksheet)
    ' Na LISTA_ORDENADA os dados começam em B4 até W...
    wsLO.Range("B4:W25000").ClearContents
End Sub

'====================================================================
'  IMPORTAÇÃO CSV
'====================================================================

Private Function EncontrarCSVPorProcesso(ByVal pasta As String, ByVal numProcesso As String) As String
    ' Procura dentro da pasta um ficheiro *.csv que contenha o numProcesso no nome

    Dim f As String
    f = Dir(pasta & "*.csv")

    Do While Len(f) > 0
        If InStr(1, f, numProcesso, vbTextCompare) > 0 Then
            EncontrarCSVPorProcesso = pasta & f
            Exit Function
        End If
        f = Dir
    Loop

    EncontrarCSVPorProcesso = ""
End Function

Private Sub ImportarCSV_ParaFolha(ByVal ws As Worksheet, ByVal caminhoCSV As String)

    ' Importa CSV para A2 com delimitador ;
    ' O CSV do IMOS normalmente traz cabeçalhos -> ficam na linha 2, dados a partir da linha 3

    ws.Activate
    ws.Range("A2").Select

    Dim qt As QueryTable
    Set qt = ws.QueryTables.Add(Connection:="TEXT;" & caminhoCSV, Destination:=ws.Range("A2"))

    With qt
        .Name = "QT_Import_IMOS"
        .FieldNames = True
        .RowNumbers = False
        .FillAdjacentFormulas = False
        .PreserveFormatting = True
        .RefreshOnFileOpen = False
        .RefreshStyle = xlInsertDeleteCells
        .SaveData = True
        .AdjustColumnWidth = True
        .TextFilePromptOnRefresh = False
        .TextFilePlatform = xlWindows
        .TextFileStartRow = 1
        .TextFileParseType = xlDelimited
        .TextFileTextQualifier = xlTextQualifierDoubleQuote
        .TextFileConsecutiveDelimiter = False

        .TextFileTabDelimiter = False
        .TextFileSemicolonDelimiter = True   ' <<< importante
        .TextFileCommaDelimiter = False
        .TextFileSpaceDelimiter = False
        .TextFileTrailingMinusNumbers = True

        .Refresh BackgroundQuery:=False
    End With

End Sub

'====================================================================
'  1) CORRIGIR RP (coluna "RP")
'====================================================================

Private Sub CorrigirColunaRP(ByVal ws As Worksheet)

    Dim colRP As Long
    colRP = FindColByHeader(ws, 2, "RP")
    If colRP = 0 Then
        MsgBox "Não encontrei a coluna 'RP' na linha 2 do separador " & ws.Name, vbExclamation
        Exit Sub
    End If

    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    If lastRow < 3 Then Exit Sub

    Dim r As Long
    Dim v As String
    Dim p As Long

    For r = 3 To lastRow
        v = CStr(ws.Cells(r, colRP).Value)

        ' Se existir ".", fica com o texto depois do primeiro "."
        p = InStr(1, v, ".", vbTextCompare)
        If p > 0 Then
            ws.Cells(r, colRP).Value = Mid$(v, p + 1)
        End If
    Next r

End Sub

'====================================================================
'  2) VERIFICAR / CORRIGIR NOTAS "RASGO ...mm"
'     Regra: Rasgo = Espessura(Fundo Gaveta) + 1
'
'  NOTA:
'   - Se houver itens a corrigir, chama o UserForm:
'       MostrarCorrigirRasgoUserForm ws, colNotas, itens
'====================================================================

Private Sub VerificarECorrigir_Rasgo_Em_Notas(ByVal ws As Worksheet)

    Dim colDesc As Long, colMat As Long, colRP As Long, colNotas As Long
    colDesc = FindColByHeader(ws, 2, "Descricao")
    colMat = FindColByHeader(ws, 2, "Material")
    colRP = FindColByHeader(ws, 2, "RP")
    colNotas = FindColByHeader(ws, 2, "Notas")

    If colDesc * colMat * colRP * colNotas = 0 Then
        MsgBox "Faltam colunas essenciais (Descricao/Material/RP/Notas) na folha " & ws.Name, vbExclamation
        Exit Sub
    End If

    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, colDesc).End(xlUp).Row
    If lastRow < 3 Then Exit Sub

    '------------------------------------------------------------
    ' 1) Dicionário: RP -> Array(espessura, material, linhaFundo)
    '------------------------------------------------------------
    Dim dictFundoInfo As Object
    Set dictFundoInfo = CreateObject("Scripting.Dictionary")

    Dim r As Long
    Dim desc As String, rp As String, mat As String
    Dim esp As Long

    For r = 3 To lastRow

        desc = CStr(ws.Cells(r, colDesc).Value)
        rp = CStr(ws.Cells(r, colRP).Value)
        mat = CStr(ws.Cells(r, colMat).Value)

        If Len(rp) > 0 Then
            If IsDescricaoFundoGaveta(desc) Then

                esp = ExtrairEspessuraMM(mat)
                If esp > 0 Then

                    If Not dictFundoInfo.Exists(rp) Then
                        dictFundoInfo.Add rp, Array(esp, mat, r)
                    Else
                        ' Prioridade para "Gaveteiro Fundo Gaveta"
                        If IsGaveteiroFundoGaveta(desc) Then
                            dictFundoInfo(rp) = Array(esp, mat, r)
                        End If
                    End If

                End If
            End If
        End If

    Next r

    '------------------------------------------------------------
    ' 2) Construir lista de correções (itens)
    '------------------------------------------------------------
    Dim itens As Collection
    Set itens = New Collection

    Dim notas As String, notasNova As String
    Dim rasgoEsperado As Long
    Dim fundoEsp As Long, fundoMat As String, fundoLinha As Long
    Dim origemCalculo As String

    For r = 3 To lastRow

        desc = CStr(ws.Cells(r, colDesc).Value)
        rp = CStr(ws.Cells(r, colRP).Value)
        mat = CStr(ws.Cells(r, colMat).Value)
        notas = CStr(ws.Cells(r, colNotas).Value)

        If Len(notas) = 0 Then GoTo ProximaLinha
        If InStr(1, notas, "Rasgo", vbTextCompare) = 0 Then GoTo ProximaLinha
        If Not IsLinhaRelacionadoComGaveta(desc) Then GoTo ProximaLinha

        fundoEsp = 0: fundoMat = "": fundoLinha = 0
        origemCalculo = ""

        If dictFundoInfo.Exists(rp) Then
            fundoEsp = CLng(dictFundoInfo(rp)(0))
            fundoMat = CStr(dictFundoInfo(rp)(1))
            fundoLinha = CLng(dictFundoInfo(rp)(2))
            rasgoEsperado = fundoEsp + 1
            origemCalculo = "FUNDO GAVETA (por RP)"
        Else
            esp = ExtrairEspessuraMM(mat)
            If esp <= 0 Then GoTo ProximaLinha
            rasgoEsperado = esp + 1
            origemCalculo = "MATERIAL DA PRÓPRIA LINHA (fallback)"
        End If

        notasNova = SubstituirRasgoPorValor(notas, rasgoEsperado)
        If notasNova = notas Then GoTo ProximaLinha

        itens.Add Array(r, rp, desc, notas, notasNova, fundoLinha, fundoMat, fundoEsp, rasgoEsperado, origemCalculo)

ProximaLinha:
    Next r

    '------------------------------------------------------------
    ' 3) Abrir UserForm (se houver itens)
    '------------------------------------------------------------
    If itens.Count > 0 Then
        MostrarCorrigirRasgoUserForm ws, colNotas, itens
    End If

End Sub

'====================================================================
'  NOVO: CONVERTER "VEIO" NA LISTA_ORDENADA (COLUNA H)
'   - "1" -> "S"
'   - "0" -> "N"
'   - Exceções (onde veio não interessa): força "N"
'====================================================================
Private Sub Converter_Veio_ListaOrdenada(ByVal wsLO As Worksheet)

    ' LISTA_ORDENADA:
    '   Col B = Descrição
    '   Col C = Material
    '   Col H = Veio  (é aqui que vamos converter)

    Dim lastRow As Long
    lastRow = wsLO.Cells(wsLO.Rows.Count, "C").End(xlUp).Row
    If lastRow < 4 Then Exit Sub

    Dim r As Long
    Dim vVeio As String
    Dim descricao As String
    Dim material As String

    Const MAT_ESPECIAL As String = "AGL_MLM_CARVALHO_SERRADO_M6054/NTL_19MM"

    For r = 4 To lastRow

        descricao = CStr(wsLO.Cells(r, "B").Value) ' descrição
        material = CStr(wsLO.Cells(r, "C").Value)  ' material
        vVeio = Trim$(CStr(wsLO.Cells(r, "H").Value))

        '---------------------------
        ' 1) Normalização base
        '---------------------------
        Select Case UCase$(vVeio)
            Case "1"
                wsLO.Cells(r, "H").Value = "S"
            Case "0", ""
                wsLO.Cells(r, "H").Value = "N"
            Case "S", "N"
                ' já está ok, não mexe
            Case Else
                ' Se vier numérico (1/0) como número:
                If IsNumeric(vVeio) Then
                    If CLng(Val(vVeio)) = 1 Then
                        wsLO.Cells(r, "H").Value = "S"
                    Else
                        wsLO.Cells(r, "H").Value = "N"
                    End If
                Else
                    ' Qualquer outro caso estranho: por segurança põe N
                    wsLO.Cells(r, "H").Value = "N"
                End If
        End Select

        '---------------------------
        ' 2) Exceções: veio não interessa -> força "N"
        '   (usa TextCompare para não depender de maiúsculas/minúsculas)
        '---------------------------
        If InStr(1, descricao, "Traseira", vbTextCompare) > 0 Then
            wsLO.Cells(r, "H").Value = "N"
        ElseIf InStr(1, descricao, "Enchimento", vbTextCompare) > 0 Then
            wsLO.Cells(r, "H").Value = "N"
        ElseIf InStr(1, descricao, "Rodape Interior", vbTextCompare) > 0 Then
            wsLO.Cells(r, "H").Value = "N"
        ElseIf InStr(1, descricao, "Gaveteiro Vista", vbTextCompare) > 0 Then
            ' Só força N para o material especial
            If StrComp(material, MAT_ESPECIAL, vbTextCompare) = 0 Then
                wsLO.Cells(r, "H").Value = "N"
            End If
        ElseIf InStr(1, descricao, "Rodape Frente", vbTextCompare) > 0 Then
            ' Só força N para o material especial
            If StrComp(material, MAT_ESPECIAL, vbTextCompare) = 0 Then
                wsLO.Cells(r, "H").Value = "N"
            End If
        End If

    Next r

End Sub

'====================================================================
'  FUNÇÕES DE APOIO (para manter a Sub principal limpa)
'====================================================================

Private Function IsDescricaoFundoGaveta(ByVal desc As String) As Boolean
    Dim d As String
    d = LCase$(Trim$(desc))
    IsDescricaoFundoGaveta = (d = LCase$("Gaveteiro Fundo Gaveta") Or d = LCase$("Fundo Gaveta"))
End Function

Private Function IsGaveteiroFundoGaveta(ByVal desc As String) As Boolean
    IsGaveteiroFundoGaveta = (LCase$(Trim$(desc)) = LCase$("Gaveteiro Fundo Gaveta"))
End Function

Private Function IsLinhaRelacionadoComGaveta(ByVal desc As String) As Boolean
    Dim d As String
    d = LCase$(Trim$(desc))

    IsLinhaRelacionadoComGaveta = ( _
        d = LCase$("Gaveteiro Lateral Gaveta") Or _
        d = LCase$("Lateral Gaveta") Or _
        d = LCase$("Gaveteiro Fundo Gaveta") Or _
        d = LCase$("Fundo Gaveta") _
    )
End Function

Private Function ExtrairEspessuraMM(ByVal material As String) As Long
    ' Extrai 2 ou 1 dígitos antes de "MM"
    Dim re As Object, m As Object
    Set re = CreateObject("VBScript.RegExp")

    With re
        .IgnoreCase = True
        .Global = False
        .pattern = "(\d{1,2})\s*MM"
    End With

    If re.Test(material) Then
        Set m = re.Execute(material)(0)
        ExtrairEspessuraMM = CLng(m.SubMatches(0))
    Else
        ExtrairEspessuraMM = 0
    End If
End Function

Private Function SubstituirRasgoPorValor(ByVal texto As String, ByVal novoRasgo As Long) As String
    ' Troca "Rasgo __mm" ou "Rasgo 09mm" ou "Rasgo 9mm" por "Rasgo Xmm"
    Dim re As Object
    Set re = CreateObject("VBScript.RegExp")

    With re
        .IgnoreCase = True
        .Global = False
        .pattern = "Rasgo\s*0*(\d+|__)\s*mm"
    End With

    If re.Test(texto) Then
        SubstituirRasgoPorValor = re.Replace(texto, "Rasgo " & CStr(novoRasgo) & "mm")
    Else
        SubstituirRasgoPorValor = texto
    End If
End Function

'====================================================================
'  3) ORDENAR (DEFENICOES!A4:A...) E COPIAR PARA LISTA_ORDENADA
'====================================================================

Private Sub Criar_Lista_Ordenada(ByVal wsImport As Worksheet, ByVal wsDef As Worksheet, ByVal wsLO As Worksheet)

    Dim lastRowImp As Long
    lastRowImp = wsImport.Cells(wsImport.Rows.Count, 1).End(xlUp).Row
    If lastRowImp < 3 Then Exit Sub

    ' Ler lista de ordem em DEFENICOES (coluna A a partir da linha 4)
    Dim lastRowDef As Long
    lastRowDef = wsDef.Cells(wsDef.Rows.Count, 1).End(xlUp).Row
    If lastRowDef < 4 Then
        MsgBox "A lista de ordem em DEFENICOES (coluna A) está vazia.", vbExclamation
        Exit Sub
    End If

    Dim ordemArr As Variant
    ordemArr = wsDef.Range("A4:A" & lastRowDef).Value

    ' Criar dicionário para saber rapidamente se uma descrição está na lista
    Dim dictOrdem As Object
    Set dictOrdem = CreateObject("Scripting.Dictionary")

    Dim i As Long
    Dim desc As String

    For i = 1 To UBound(ordemArr, 1)
        desc = Trim$(CStr(ordemArr(i, 1)))
        If Len(desc) > 0 Then
            If Not dictOrdem.Exists(desc) Then dictOrdem.Add desc, True
        End If
    Next i

    ' Limpar destino
    wsLO.Range("B4:W25000").ClearContents

    Dim outRow As Long
    outRow = 4

    ' 1) Primeiro: copiar na ordem definida
    For i = 1 To UBound(ordemArr, 1)
        desc = Trim$(CStr(ordemArr(i, 1)))
        If Len(desc) = 0 Then GoTo ProximoDesc

        Dim r As Long
        For r = 3 To lastRowImp
            If CStr(wsImport.Cells(r, 1).Value) = desc Then
                CopiarLinha_Mapeada wsImport, r, wsLO, outRow
                outRow = outRow + 1
            End If
        Next r

ProximoDesc:
    Next i

    ' 2) Depois: copiar tudo o que NÃO está na lista (mantendo ordem original)
    Dim d As String
    For i = 3 To lastRowImp
        d = CStr(wsImport.Cells(i, 1).Value)
        If Not dictOrdem.Exists(d) Then
            CopiarLinha_Mapeada wsImport, i, wsLO, outRow
            outRow = outRow + 1
        End If
    Next i

End Sub

Private Sub CopiarLinha_Mapeada(ByVal wsImp As Worksheet, ByVal rowImp As Long, ByVal wsLO As Worksheet, ByVal rowLO As Long)
    ' Copia valores do import para LISTA_ORDENADA respeitando as colunas
    ' LISTA_ORDENADA começa em B (col 2)

    wsLO.Cells(rowLO, "B").Value = wsImp.Cells(rowImp, 1).Value
    wsLO.Cells(rowLO, "C").Value = wsImp.Cells(rowImp, 2).Value
    wsLO.Cells(rowLO, "D").Value = wsImp.Cells(rowImp, 3).Value
    wsLO.Cells(rowLO, "E").Value = wsImp.Cells(rowImp, 4).Value
    wsLO.Cells(rowLO, "F").Value = wsImp.Cells(rowImp, 5).Value
    wsLO.Cells(rowLO, "G").Value = wsImp.Cells(rowImp, 6).Value
    wsLO.Cells(rowLO, "H").Value = wsImp.Cells(rowImp, 7).Value     ' << Veio (aqui ainda vem 0/1; convertemos depois)
    wsLO.Cells(rowLO, "I").Value = wsImp.Cells(rowImp, 8).Value
    wsLO.Cells(rowLO, "J").Value = wsImp.Cells(rowImp, 9).Value
    wsLO.Cells(rowLO, "K").Value = wsImp.Cells(rowImp, 10).Value
    wsLO.Cells(rowLO, "L").Value = wsImp.Cells(rowImp, 11).Value
    wsLO.Cells(rowLO, "M").Value = wsImp.Cells(rowImp, 12).Value
    wsLO.Cells(rowLO, "N").Value = wsImp.Cells(rowImp, 13).Value
    wsLO.Cells(rowLO, "O").Value = wsImp.Cells(rowImp, 14).Value
    wsLO.Cells(rowLO, "P").Value = wsImp.Cells(rowImp, 15).Value

    ' RP -> Artigo
    wsLO.Cells(rowLO, "Q").Value = wsImp.Cells(rowImp, 16).Value

    wsLO.Cells(rowLO, "R").Value = wsImp.Cells(rowImp, 17).Value
    wsLO.Cells(rowLO, "S").Value = wsImp.Cells(rowImp, 18).Value
    wsLO.Cells(rowLO, "T").Value = wsImp.Cells(rowImp, 19).Value
    wsLO.Cells(rowLO, "U").Value = wsImp.Cells(rowImp, 20).Value
    wsLO.Cells(rowLO, "V").Value = wsImp.Cells(rowImp, 21).Value
    wsLO.Cells(rowLO, "W").Value = wsImp.Cells(rowImp, 22).Value

End Sub

Private Function FindColByHeader(ByVal ws As Worksheet, ByVal headerRow As Long, ByVal headerText As String) As Long
    ' Procura um texto de cabeçalho na linha headerRow e devolve o nº da coluna
    Dim lastCol As Long
    lastCol = ws.Cells(headerRow, ws.Columns.Count).End(xlToLeft).Column

    Dim c As Long
    For c = 1 To lastCol
        If CStr(ws.Cells(headerRow, c).Value) = headerText Then
            FindColByHeader = c
            Exit Function
        End If
    Next c

    FindColByHeader = 0
End Function

Private Function FindColByHeaderFlex(ByVal ws As Worksheet, ByVal headerRow As Long, ByVal possiveis As Variant) As Long
    ' Procura cabeçalho aceitando várias opções (ex.: "Qt.", "Qt", "QT")
    Dim lastCol As Long
    lastCol = ws.Cells(headerRow, ws.Columns.Count).End(xlToLeft).Column

    Dim c As Long, i As Long
    Dim h As String, alvo As String

    For c = 1 To lastCol
        h = Trim$(CStr(ws.Cells(headerRow, c).Value))
        For i = LBound(possiveis) To UBound(possiveis)
            alvo = Trim$(CStr(possiveis(i)))
            If StrComp(h, alvo, vbTextCompare) = 0 Then
                FindColByHeaderFlex = c
                Exit Function
            End If
        Next i
    Next c

    FindColByHeaderFlex = 0
End Function
