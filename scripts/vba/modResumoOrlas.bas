Attribute VB_Name = "modResumoOrlas"
Option Explicit

'===========================
' modResumoOrlas
' RESUMO ORLAS (REFINADO + AVISOS)
' Editado 23-03-2026
' Editado 07-10-2026: REF_CLIENTE em F1/F2; colunas "stock/enc", "Larg X Esp"
'   e "Obs." (antes "enc", "LARG X ESP" e "Entrada Orlas"). As obras antigas
'   continuam a ser lidas pelos nomes antigos.
' Fonte versionada: scripts/vba/modResumoOrlas.bas (repositório Martelo V3).
'===========================
' Objetivo do módulo:
'   Este módulo lê a tabela Tabela_Cut_Rite da folha LISTAGEM_CUT_RITE,
'   analisa as orlas atribuídas a cada peça e gera automaticamente um
'   resumo final de consumo de orlas na folha ResumoOrlas.
'
' O que o módulo faz:
'   - Lê Material, Comp, Larg, Qt, Esp/ESPFINAL e as colunas de orlas
'     (ORLA_ESQ, ORLA_DIR, ORLA_CIMA, ORLA_BAIXO).
'   - Soma os metros lineares das orlas de todas as peças:
'       * ORLA_ESQ e ORLA_DIR usam a medida COMP
'       * ORLA_CIMA e ORLA_BAIXO usam a medida LARG
'   - Multiplica os metros lineares pela quantidade da peça.
'   - Aplica desperdício de 8%.
'   - Arredonda sempre o resultado final para cima a metro inteiro.
'
' Resultado gerado:
'   A folha ResumoOrlas fica com uma tabela resumida por:
'       Material | Nome_Orlas | ML_QT | stock/enc | Marca / Ref. | Larg X Esp | ML | Obs.
'
' Regras principais:
'   - O resumo é agrupado por combinação de Material + Orla.
'   - Se a espessura final da peça for diferente da espessura base do material,
'     o nome do material no resumo é ajustado para refletir a espessura final.
'   - A largura da fita é calculada automaticamente em função da espessura da peça.
'   - O campo LARG X ESP é montado automaticamente no formato:
'       largura_fita x espessura_orla
'     Exemplo:
'       25 x 1.0
'
' Preservação de dados manuais:
'   Se a folha ResumoOrlas já existir, o módulo tenta preservar os campos
'   preenchidos manualmente pelo utilizador, como:
'       stock/enc | Marca / Ref. | Larg X Esp | ML | Obs.
'
' Validação de orlas:
'   O módulo reconhece atualmente famílias de orlas válidas, como por exemplo:
'       PVC_...
'       FOL_...
'       ABS_...
'       ABS:...
'       ORLA_LASER_...
'
'   A validação foi centralizada para facilitar futuras alterações.
'   Se no futuro surgirem novas famílias de orlas, basta adaptar a lógica
'   numa única zona do módulo.
'
' Extração da espessura da orla:
'   O módulo tenta extrair automaticamente a espessura da orla a partir do nome.
'   Exemplos:
'       PVC_0.4_LINHO         -> 0.4
'       FOL_1.0_CARVALHO      -> 1.0
'       ABS_0.4_H1334/ST9     -> 0.4
'       ABS:0.8_PRETO         -> 0.8
'       ORLA_LASER_1.2        -> 1.2
'
' Avisos ao utilizador:
'   O módulo gera avisos quando encontra situações que podem afetar o cálculo:
'   - texto de orla inválido
'   - espessura da peça em falta
'   - orla sem espessura identificável no nome
'
'   Os avisos podem ser:
'   - mostrados em MsgBox
'   - gravados na folha Avisos_Orlas
'
' Validação com a folha MP:
'   Depois de gerar o resumo, o módulo pode comparar as orlas encontradas
'   com as orlas permitidas na folha MP, assinalando visualmente eventuais
'   orlas sem correspondência.
'
' Vantagem desta versão:
'   Esta versão foi preparada para ser mais flexível e mais fácil de manter.
'   A lógica das famílias de orla ficou centralizada, permitindo adaptar
'   rapidamente o módulo quando surgirem novos tipos de orlas no futuro.
'===========================

Private Const SH_CUTRITE As String = "LISTAGEM_CUT_RITE"
Private Const TBL_CUTRITE As String = "Tabela_Cut_Rite"

Private Const SH_RESUMO As String = "ResumoOrlas"
Private Const START_CELL As String = "B3"
Private Const TBL_RESUMO As String = "Tabela_ResumoOrlas"

Private Const SH_MP As String = "MP"
Private Const DESPERDICIO As Double = 0.08

' --- AVISOS AO UTILIZADOR
Private Const MOSTRAR_AVISOS As Boolean = True
Private Const CRIAR_FOLHA_AVISOS As Boolean = True
Private Const SH_AVISOS As String = "Avisos_Orlas"
Private Const MAX_AVISOS_MSG As Long = 20

' --- valor por omissão da coluna "stock/enc" (antes era "enc")
Private Const VALOR_STOCK_ENC As String = "stock/enc"

'------------------------------------------------------------
' MACRO PRINCIPAL
'------------------------------------------------------------
Public Sub GERAR_ResumoOrlas()

    Dim wsSrc As Worksheet, wsDst As Worksheet
    Dim lo As ListObject
    Dim data As Variant
    Dim nRows As Long
    Dim r As Long

    ' índices de colunas na Tabela_Cut_Rite
    Dim idxMat As Long, idxComp As Long, idxLarg As Long, idxQt As Long
    Dim idxEspFinal As Long, idxEsp As Long, idxEspMat As Long
    Dim idxOrlaEsq As Long, idxOrlaDir As Long, idxOrlaCima As Long, idxOrlaBaixo As Long
    Dim idxCliente As Long, idxEncPhc As Long, idxRefCliente As Long
    Dim idxID As Long   ' opcional

    Dim dict As Object
    Dim dictManual As Object
    Dim dictAllowed As Object
    Dim avisos As Collection

    Dim outArr As Variant
    Dim k As Variant, parts As Variant
    Dim i As Long, outCount As Long

    On Error GoTo EH

    Application.ScreenUpdating = False
    Application.EnableEvents = False
    Application.Calculation = xlCalculationManual

    ' origem
    Set wsSrc = ThisWorkbook.Worksheets(SH_CUTRITE)
    Set lo = wsSrc.ListObjects(TBL_CUTRITE)

    If lo Is Nothing Then
        MsgBox "Não encontrei a tabela '" & TBL_CUTRITE & "' na folha '" & SH_CUTRITE & "'.", vbExclamation
        GoTo CleanExit
    End If

    If lo.DataBodyRange Is Nothing Then GoTo CleanExit

    ' índices robustos
    idxMat = GetColIndexByNorm(lo, "MATERIAL")
    idxComp = GetColIndexByNorm(lo, "COMP")
    idxLarg = GetColIndexByNorm(lo, "LARG")
    idxQt = GetColIndexByNorm(lo, "QT")

    idxOrlaEsq = GetColIndexByNorm(lo, "ORLAESQ")
    idxOrlaDir = GetColIndexByNorm(lo, "ORLADIR")
    idxOrlaCima = GetColIndexByNorm(lo, "ORLACIMA")
    idxOrlaBaixo = GetColIndexByNorm(lo, "ORLABAIXO")

    idxEspFinal = GetColIndexByNorm(lo, "ESPFINAL")
    idxEsp = GetColIndexByNorm(lo, "ESP")
    idxEspMat = GetColIndexByNorm(lo, "ESPMAT")

    idxCliente = GetColIndexByNorm(lo, "CLIENTE")
    idxEncPhc = GetColIndexByNorm(lo, "ENCPHC")
    idxRefCliente = GetColIndexByNorm(lo, "REFCLIENTE")

    idxID = GetColIndexByNorm(lo, "ID")

    If idxMat = 0 Or idxComp = 0 Or idxLarg = 0 Or idxQt = 0 Then
        MsgBox "Não encontrei colunas essenciais (Material/Comp/Larg/Qt) na Tabela_Cut_Rite.", vbExclamation
        GoTo CleanExit
    End If

    If idxOrlaEsq = 0 Or idxOrlaDir = 0 Or idxOrlaCima = 0 Or idxOrlaBaixo = 0 Then
        MsgBox "Não encontrei colunas de Orlas (ESQ/DIR/CIMA/BAIXO) na Tabela_Cut_Rite.", vbExclamation
        GoTo CleanExit
    End If

    ' ler tabela para array
    data = lo.DataBodyRange.Value
    nRows = UBound(data, 1)

    Set dict = CreateObject("Scripting.Dictionary")
    Set avisos = New Collection

    ' varrer linhas
    For r = 1 To nRows

        Dim material As String, materialResumo As String
        Dim compMM As Double, largMM As Double, qt As Double
        Dim espPeca As Double, espMat As Double

        material = CleanText(Nz(data(r, idxMat), ""))
        If Len(material) = 0 Then GoTo NextRow

        compMM = Fix(ToDouble(Nz(data(r, idxComp), 0)))
        largMM = Fix(ToDouble(Nz(data(r, idxLarg), 0)))
        qt = ToDouble(Nz(data(r, idxQt), 0))
        If qt <= 0 Then GoTo NextRow

        ' espessura final da peça
        espPeca = 0
        If idxEspFinal > 0 Then
            espPeca = ToDouble(Nz(data(r, idxEspFinal), 0))
        ElseIf idxEsp > 0 Then
            espPeca = ToDouble(Nz(data(r, idxEsp), 0))
        End If

        ' espessura base do material
        espMat = 0
        If idxEspMat > 0 Then espMat = ToDouble(Nz(data(r, idxEspMat), 0))

        materialResumo = BuildResumoMaterial(material, espPeca, espMat)

        ' orlas
        Dim oEsq As Variant, oDir As Variant, oCima As Variant, oBaixo As Variant
        oEsq = Nz(data(r, idxOrlaEsq), "")
        oDir = Nz(data(r, idxOrlaDir), "")
        oCima = Nz(data(r, idxOrlaCima), "")
        oBaixo = Nz(data(r, idxOrlaBaixo), "")

        ' ID
        Dim idVal As String
        If idxID > 0 Then
            idVal = CStr(Nz(data(r, idxID), ""))
        Else
            idVal = ""
        End If

        ' avisos de texto inválido
        CheckOrlaTexto avisos, r, idVal, materialResumo, espPeca, "ORLA_ESQ", oEsq
        CheckOrlaTexto avisos, r, idVal, materialResumo, espPeca, "ORLA_DIR", oDir
        CheckOrlaTexto avisos, r, idVal, materialResumo, espPeca, "ORLA_CIMA", oCima
        CheckOrlaTexto avisos, r, idVal, materialResumo, espPeca, "ORLA_BAIXO", oBaixo

        ' aviso: existe orla válida, mas espessura da peça está vazia/0
        Dim temOrlaValida As Boolean
        temOrlaValida = IsOrlaValidaParaCalculo(oEsq) Or _
                        IsOrlaValidaParaCalculo(oDir) Or _
                        IsOrlaValidaParaCalculo(oCima) Or _
                        IsOrlaValidaParaCalculo(oBaixo)

        If temOrlaValida And espPeca <= 0 Then
            AddAviso avisos, "ESPESSURA_EM_FALTA", r, idVal, materialResumo, espPeca, "", "", _
                     "Existe orla válida nesta linha, mas a espessura (ESP/ESPFINAL) está vazia/0. O cálculo da largura da fita pode ficar incorreto."
        End If

        ' acumular ML
        AccOrla dict, materialResumo, oEsq, compMM, qt, espPeca
        AccOrla dict, materialResumo, oDir, compMM, qt, espPeca
        AccOrla dict, materialResumo, oCima, largMM, qt, espPeca
        AccOrla dict, materialResumo, oBaixo, largMM, qt, espPeca

NextRow:
    Next r

    ' criar/mover folha destino
    Set wsDst = GetOrCreateSheetAfter(SH_RESUMO, SH_CUTRITE)

    On Error Resume Next
    wsDst.Unprotect
    On Error GoTo 0

    ' carregar manuais existentes
    Set dictManual = LoadManual_ResumoOrlas(wsDst)

    ' cabeçalho
    WriteHeaderResumo wsDst, lo, idxCliente, idxEncPhc, idxRefCliente

    ' construir array de saída
    outCount = dict.Count
    If outCount = 0 Then
        MsgBox "Não encontrei orlas para resumir (tudo vazio/0?).", vbInformation
        GoTo CleanExit
    End If

    ReDim outArr(1 To outCount, 1 To 8)

    i = 0
    For Each k In dict.keys
        i = i + 1
        parts = Split(CStr(k), "|")

        Dim mlBase As Double
        Dim largFita As Long
        Dim mlQt As Long
        Dim espOrla As Double
        Dim largXEspCalc As String

        mlBase = CDbl(dict(k)(0))
        largFita = CLng(dict(k)(1))
        mlQt = CeilInt(mlBase * (1 + DESPERDICIO))

        espOrla = ExtractOrlaEsp(parts(1))
        largXEspCalc = FormatLargXEsp(largFita, espOrla)

        If espOrla <= 0 Then
            AddAviso avisos, "ESP_ORLA_NAO_ENCONTRADA", 0, "", parts(0), 0, "NOME_ORLA", parts(1), _
                     "O nome da orla não tem espessura identificável. Exemplos aceites: PVC_0.4_..., FOL_1.0_..., ABS_0.4_..., ABS:0.8_..., ORLA_LASER_1.2"
        End If

        outArr(i, 1) = parts(0)
        outArr(i, 2) = parts(1)
        outArr(i, 3) = mlQt
        outArr(i, 4) = VALOR_STOCK_ENC
        outArr(i, 5) = vbNullString
        outArr(i, 6) = largXEspCalc
        outArr(i, 7) = vbNullString
        outArr(i, 8) = vbNullString

        If dictManual.Exists(k) Then
            Dim man As Variant
            man = dictManual(k)

            ' "enc" era o valor por omissão antigo: passa a "stock/enc";
            ' o que o utilizador escreveu à mão (ex.: "stock") fica.
            If Len(CStr(man(0))) > 0 And LCase$(Trim$(CStr(man(0)))) <> "enc" Then outArr(i, 4) = man(0)
            If Len(CStr(man(1))) > 0 Then outArr(i, 5) = man(1)
            If Len(CStr(man(2))) > 0 Then outArr(i, 6) = man(2)
            If Len(CStr(man(3))) > 0 Then outArr(i, 7) = man(3)
            If Len(CStr(man(4))) > 0 Then outArr(i, 8) = man(4)
        End If
    Next k

    ' escrever tabela
    WriteResumoOrlas wsDst, outArr

    ' ordenar
    SortResumoOrlas wsDst

    ' validação visual com base na folha MP
    Set dictAllowed = BuildAllowedOrlas_FromMP()
    If Not dictAllowed Is Nothing Then
        Dim msg As String
        msg = PaintInvalidOrlas_Resumo(wsDst, dictAllowed)
        If Len(msg) > 0 Then MsgBox msg, vbExclamation, "Orlas sem correspondência (MP)"
    End If

    ' avisos
    If MOSTRAR_AVISOS Then
        If avisos.Count > 0 Then
            If CRIAR_FOLHA_AVISOS Then WriteAvisosOrlasSheet avisos
            ShowAvisosOrlas avisos
        End If
    End If

CleanExit:
    Application.Calculation = xlCalculationAutomatic
    Application.EnableEvents = True
    Application.ScreenUpdating = True
    Exit Sub

EH:
    MsgBox "Erro GERAR_ResumoOrlas: " & Err.Number & " - " & Err.Description, vbExclamation
    Resume CleanExit
End Sub

'------------------------------------------------------------
' ACUMULADOR
'------------------------------------------------------------
Private Sub AccOrla(ByVal dict As Object, ByVal material As String, ByVal orlaRaw As Variant, _
                    ByVal medidaMM As Double, ByVal qt As Double, ByVal espPeca As Double)

    Dim orla As String
    orla = UCase$(CleanText(orlaRaw))

    If Len(orla) = 0 Then Exit Sub
    If orla = "0" Then Exit Sub
    If orla = "(EM BRANCO)" Or orla = "(BLANK)" Then Exit Sub

    If Not IsOrlaValidaParaCalculo(orla) Then Exit Sub
    If qt <= 0 Then Exit Sub
    If medidaMM <= 0 Then Exit Sub

    Dim key As String
    key = material & "|" & orla

    Dim ml As Double
    ml = (medidaMM / 1000#) * qt

    Dim largFita As Long
    largFita = GetLarguraFita(CeilInt(espPeca))

    If Not dict.Exists(key) Then
        dict.Add key, Array(ml, largFita)
    Else
        Dim arr As Variant
        arr = dict(key)
        arr(0) = CDbl(arr(0)) + ml
        If largFita > CLng(arr(1)) Then arr(1) = largFita
        dict(key) = arr
    End If

End Sub

'------------------------------------------------------------
' CABEÇALHO
'------------------------------------------------------------
Private Sub WriteHeaderResumo(ByVal wsDst As Worksheet, ByVal lo As ListObject, _
                              ByVal idxCliente As Long, ByVal idxEnc As Long, ByVal idxRef As Long)

    Dim cliente As String, enc As String, refCli As String

    cliente = SafeEvalText("NOME_CLIENTE")
    If Len(cliente) = 0 And idxCliente > 0 Then cliente = CleanText(lo.DataBodyRange.Cells(1, idxCliente).Value)

    enc = SafeEvalText("ENC_PHC")
    If Len(enc) = 0 And idxEnc > 0 Then enc = CleanText(lo.DataBodyRange.Cells(1, idxEnc).Value)

    refCli = SafeEvalText("REF_CLIENTE")
    If Len(refCli) = 0 And idxRef > 0 Then refCli = CleanText(lo.DataBodyRange.Cells(1, idxRef).Value)

    ' Obras antigas tinham o REF_CLIENTE em H1/H2: limpa-se para não ficar repetido.
    If UCase$(CleanText(wsDst.Range("H1").Value)) = "REF_CLIENTE" Then
        wsDst.Range("H1:H2").ClearContents
    End If

    wsDst.Range("B1").Value = "Cliente"
    wsDst.Range("E1").Value = "ENC_PHC"
    wsDst.Range("F1").Value = "REF_CLIENTE"

    wsDst.Range("B2").Value = cliente
    wsDst.Range("E2").Value = enc
    wsDst.Range("F2").Value = refCli

    With wsDst.Range("B1:H1")
        .Font.bold = True
    End With
End Sub

'------------------------------------------------------------
' ESCREVER / FORMATAR TABELA
'------------------------------------------------------------
Private Sub WriteResumoOrlas(ByVal ws As Worksheet, ByVal outArr As Variant)

    Dim start As Range
    Set start = ws.Range(START_CELL)

    On Error Resume Next
    ws.ListObjects(TBL_RESUMO).Delete
    On Error GoTo 0

    ws.Range("B3:K10000").Clear

    Dim n As Long
    n = UBound(outArr, 1)

    Dim headers As Variant
    headers = Array( _
        "Material", "Nome_Orlas", "ML_QT", _
        VALOR_STOCK_ENC, "Marca / Ref.", "Larg X Esp", "ML", "Obs." _
    )

    Dim c As Long
    For c = 0 To UBound(headers)
        start.Offset(0, c).Value = headers(c)
    Next c

    start.Offset(1, 0).Resize(n, 8).Value = outArr

    Dim rng As Range
    Set rng = start.Resize(n + 1, 8)

    Dim lo As ListObject
    Set lo = ws.ListObjects.Add(SourceType:=xlSrcRange, Source:=rng, XlListObjectHasHeaders:=xlYes)
    lo.Name = TBL_RESUMO

    lo.TableStyle = "TableStyleMedium15"
    lo.ShowTableStyleRowStripes = True

    ' larguras iguais às do modelo (07-10-2026)
    lo.ListColumns(1).Range.ColumnWidth = 52
    lo.ListColumns(2).Range.ColumnWidth = 18
    lo.ListColumns(3).Range.ColumnWidth = 7
    lo.ListColumns(4).Range.ColumnWidth = 15
    lo.ListColumns(5).Range.ColumnWidth = 30
    lo.ListColumns(6).Range.ColumnWidth = 12
    lo.ListColumns(7).Range.ColumnWidth = 9
    lo.ListColumns(8).Range.ColumnWidth = 24

    lo.ListColumns(3).DataBodyRange.NumberFormat = "0"
    lo.ListColumns(3).DataBodyRange.HorizontalAlignment = xlCenter

    lo.ListColumns(6).DataBodyRange.NumberFormat = "@"
    lo.ListColumns(6).DataBodyRange.HorizontalAlignment = xlCenter

    If Not lo.DataBodyRange Is Nothing Then
        lo.DataBodyRange.RowHeight = 30
        lo.DataBodyRange.VerticalAlignment = xlCenter
        lo.ListColumns(1).DataBodyRange.WrapText = True
    End If

    ApplyPrintSetup ws, lo

End Sub

'------------------------------------------------------------
' IMPRESSÃO
'------------------------------------------------------------
Private Sub ApplyPrintSetup(ByVal ws As Worksheet, ByVal lo As ListObject)

    Dim planoCorte As String
    planoCorte = SafeEvalText("PLANO_CORTE")

    With ws.PageSetup
        .Orientation = xlLandscape
        .PaperSize = xlPaperA4

        .Zoom = False
        .FitToPagesWide = 1
        .FitToPagesTall = 1

        .LeftMargin = Application.InchesToPoints(0.25)
        .RightMargin = Application.InchesToPoints(0.25)
        .TopMargin = Application.InchesToPoints(0.75)
        .BottomMargin = Application.InchesToPoints(0.75)
        .HeaderMargin = Application.InchesToPoints(0.3)
        .FooterMargin = Application.InchesToPoints(0.3)

        Dim lastRow As Long, lastCol As Long
        lastRow = lo.Range.Row + lo.Range.Rows.Count - 1
        lastCol = lo.Range.Column + lo.Range.Columns.Count - 1

        .PrintArea = ws.Range(ws.Cells(1, 2), ws.Cells(lastRow, lastCol)).Address
        .LeftFooter = "Data: " & Format(Date, "dd/mm/yyyy")
        .CenterFooter = planoCorte
        .RightFooter = "Pag. &P de &N"
    End With

End Sub

'------------------------------------------------------------
' ORDENAR
'------------------------------------------------------------
Private Sub SortResumoOrlas(ByVal ws As Worksheet)

    Dim lo As ListObject
    On Error Resume Next
    Set lo = ws.ListObjects(TBL_RESUMO)
    On Error GoTo 0

    If lo Is Nothing Then Exit Sub
    If lo.DataBodyRange Is Nothing Then Exit Sub

    With lo.Sort
        .SortFields.Clear
        .SortFields.Add key:=lo.ListColumns(1).DataBodyRange, SortOn:=xlSortOnValues, Order:=xlAscending, DataOption:=xlSortNormal
        .SortFields.Add key:=lo.ListColumns(2).DataBodyRange, SortOn:=xlSortOnValues, Order:=xlAscending, DataOption:=xlSortNormal
        .Header = xlYes
        .Apply
    End With

End Sub

'------------------------------------------------------------
' CHECK VISUAL + Msg curto - ORLAS INVÁLIDAS (MP)
'------------------------------------------------------------
Private Function PaintInvalidOrlas_Resumo(ByVal ws As Worksheet, ByVal dictAllowed As Object) As String

    Dim lo As ListObject
    On Error Resume Next
    Set lo = ws.ListObjects(TBL_RESUMO)
    On Error GoTo 0
    If lo Is Nothing Then Exit Function
    If lo.DataBodyRange Is Nothing Then Exit Function

    Dim colMat As Long, colOrla As Long
    colMat = GetListColIndexByNorm(lo, "MATERIAL")
    colOrla = GetListColIndexByNorm(lo, "NOMEORLAS")
    If colMat = 0 Or colOrla = 0 Then Exit Function

    Dim r As Long
    Dim invalidCount As Long
    Dim msg As String, limit As Long
    limit = 20

    msg = "Encontradas orlas sem correspondência na folha MP:" & vbCrLf & vbCrLf

    For r = 1 To lo.ListRows.Count

        Dim material As String, orla As String
        material = CleanText(lo.DataBodyRange.Cells(r, colMat).Value)
        orla = CleanText(lo.DataBodyRange.Cells(r, colOrla).Value)

        lo.DataBodyRange.Cells(r, colOrla).Interior.pattern = xlNone

        If Len(material) = 0 Or Len(orla) = 0 Then GoTo NextR

        Dim ok As Boolean
        ok = AllowedOrlaExiste(dictAllowed, material, orla)

        If Not ok Then
            invalidCount = invalidCount + 1
            lo.DataBodyRange.Cells(r, colOrla).Interior.Color = RGB(255, 120, 120)

            If invalidCount <= limit Then
                Dim realRow As Long
                realRow = lo.HeaderRowRange.Row + r
                msg = msg & "Linha " & realRow & " -> " & material & " | " & orla & vbCrLf
            End If
        End If

NextR:
    Next r

    If invalidCount = 0 Then
        PaintInvalidOrlas_Resumo = vbNullString
    Else
        If invalidCount > limit Then
            msg = msg & vbCrLf & "... e mais " & (invalidCount - limit) & " linhas."
        End If
        PaintInvalidOrlas_Resumo = msg
    End If

End Function

'------------------------------------------------------------
' CARREGAR MANUAIS
'------------------------------------------------------------
Private Function LoadManual_ResumoOrlas(ByVal ws As Worksheet) As Object

    Dim dict As Object
    Set dict = CreateObject("Scripting.Dictionary")

    Dim lo As ListObject
    On Error Resume Next
    Set lo = ws.ListObjects(TBL_RESUMO)
    On Error GoTo 0

    If lo Is Nothing Then
        Set LoadManual_ResumoOrlas = dict
        Exit Function
    End If

    If lo.DataBodyRange Is Nothing Then
        Set LoadManual_ResumoOrlas = dict
        Exit Function
    End If

    Dim cMat As Long, cOrla As Long, cEnc As Long, cMarca As Long, cLargXEsp As Long, cML As Long, cEntrada As Long
    cMat = GetListColIndexByNorm(lo, "MATERIAL")
    cOrla = GetListColIndexByNorm(lo, "NOMEORLAS")
    ' nomes novos primeiro; os antigos ("enc", "Entrada Orlas") para obras antigas
    cEnc = GetListColIndexByNorm(lo, "STOCKENC")
    If cEnc = 0 Then cEnc = GetListColIndexByNorm(lo, "ENC")
    cMarca = GetListColIndexByNorm(lo, "MARCAREF")
    cLargXEsp = GetListColIndexByNorm(lo, "LARGXESP")
    cML = GetListColIndexByNorm(lo, "ML")
    cEntrada = GetListColIndexByNorm(lo, "OBS")
    If cEntrada = 0 Then cEntrada = GetListColIndexByNorm(lo, "ENTRADAORLAS")

    If cMat = 0 Or cOrla = 0 Then
        Set LoadManual_ResumoOrlas = dict
        Exit Function
    End If

    Dim r As Long
    For r = 1 To lo.ListRows.Count

        Dim material As String, orla As String, key As String
        material = CleanText(lo.DataBodyRange.Cells(r, cMat).Value)
        orla = CleanText(lo.DataBodyRange.Cells(r, cOrla).Value)
        If Len(material) = 0 Or Len(orla) = 0 Then GoTo NextR

        key = material & "|" & orla

        dict(key) = Array( _
            IIf(cEnc > 0, lo.DataBodyRange.Cells(r, cEnc).Value, vbNullString), _
            IIf(cMarca > 0, lo.DataBodyRange.Cells(r, cMarca).Value, vbNullString), _
            IIf(cLargXEsp > 0, lo.DataBodyRange.Cells(r, cLargXEsp).Value, vbNullString), _
            IIf(cML > 0, lo.DataBodyRange.Cells(r, cML).Value, vbNullString), _
            IIf(cEntrada > 0, lo.DataBodyRange.Cells(r, cEntrada).Value, vbNullString) _
        )

NextR:
    Next r

    Set LoadManual_ResumoOrlas = dict
End Function

'------------------------------------------------------------
' BUILD DICT - ORLAS PERMITIDAS (folha MP)
'------------------------------------------------------------
Private Function BuildAllowedOrlas_FromMP() As Object
    On Error GoTo EH

    Dim ws As Worksheet
    Set ws = ThisWorkbook.Worksheets(SH_MP)

    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, "A").End(xlUp).Row
    If lastRow < 2 Then
        Set BuildAllowedOrlas_FromMP = Nothing
        Exit Function
    End If

    Dim dict As Object
    Set dict = CreateObject("Scripting.Dictionary")

    Dim r As Long
    For r = 2 To lastRow

        Dim mat As String, orlas As String
        mat = CleanText(Nz(ws.Cells(r, 1).Value, ""))
        orlas = CleanText(Nz(ws.Cells(r, 2).Value, ""))

        If Len(mat) > 0 And Len(orlas) > 0 Then
            orlas = Replace(orlas, " ", "")
            AddAllowedOrlasKey dict, mat, orlas
            AddAllowedOrlasKey dict, "#FAM#" & MaterialFamilyKey(mat), orlas
        End If
    Next r

    Set BuildAllowedOrlas_FromMP = dict
    Exit Function

EH:
    Set BuildAllowedOrlas_FromMP = Nothing
End Function

'------------------------------------------------------------
' Junta uma lista de orlas ao dicionário
'------------------------------------------------------------
Private Sub AddAllowedOrlasKey(ByVal dict As Object, ByVal key As String, ByVal orlas As String)

    If Len(key) = 0 Or Len(orlas) = 0 Then Exit Sub

    If Left$(orlas, 1) <> "," Then orlas = "," & orlas
    If Right$(orlas, 1) <> "," Then orlas = orlas & ","

    If Not dict.Exists(key) Then
        dict.Add key, orlas
    Else
        Dim merged As String
        Dim itens As Variant, it As Variant

        merged = CStr(dict(key))
        itens = Split(Mid$(orlas, 2, Len(orlas) - 2), ",")

        For Each it In itens
            If Len(CStr(it)) > 0 Then
                If InStr(1, merged, "," & CStr(it) & ",", vbTextCompare) = 0 Then
                    merged = merged & CStr(it) & ","
                End If
            End If
        Next it

        dict(key) = merged
    End If

End Sub

'------------------------------------------------------------
' Verifica se a orla existe para o material exacto ou família
'------------------------------------------------------------
Private Function AllowedOrlaExiste(ByVal dictAllowed As Object, ByVal material As String, ByVal orla As String) As Boolean

    Dim famKey As String

    If dictAllowed Is Nothing Then Exit Function
    If Len(material) = 0 Or Len(orla) = 0 Then Exit Function

    If dictAllowed.Exists(material) Then
        If InStr(1, dictAllowed(material), "," & orla & ",", vbTextCompare) > 0 Then
            AllowedOrlaExiste = True
            Exit Function
        End If
    End If

    famKey = "#FAM#" & MaterialFamilyKey(material)
    If dictAllowed.Exists(famKey) Then
        If InStr(1, dictAllowed(famKey), "," & orla & ",", vbTextCompare) > 0 Then
            AllowedOrlaExiste = True
        End If
    End If

End Function

'------------------------------------------------------------
' Material a usar no resumo
'------------------------------------------------------------
Private Function BuildResumoMaterial(ByVal material As String, ByVal espPeca As Double, Optional ByVal espMat As Double = 0) As String

    material = CleanText(material)
    If Len(material) = 0 Then Exit Function

    If espPeca <= 0 Then
        BuildResumoMaterial = material
        Exit Function
    End If

    If espMat <= 0 Then espMat = ExtractMaterialEsp(material)

    If espMat > 0 Then
        If Abs(espPeca - espMat) <= 0.05 Then
            BuildResumoMaterial = material
        Else
            BuildResumoMaterial = ReplaceMaterialEsp(material, espPeca)
        End If
    Else
        BuildResumoMaterial = ReplaceMaterialEsp(material, espPeca)
    End If

End Function

'------------------------------------------------------------
' Extrai a espessura final do nome do material
'------------------------------------------------------------
Private Function ExtractMaterialEsp(ByVal material As String) As Double

    Dim re As Object, m As Object

    material = CleanText(material)
    If Len(material) = 0 Then Exit Function

    Set re = CreateObject("VBScript.RegExp")
    With re
        .Global = False
        .IgnoreCase = True
        .pattern = "_(\d+(?:[.,]\d+)?)MM$"
    End With

    If re.Test(material) Then
        Set m = re.Execute(material)(0)
        ExtractMaterialEsp = ToDouble(m.SubMatches(0))
    End If

End Function

'------------------------------------------------------------
' Substitui/força a espessura final no texto do material
'------------------------------------------------------------
Private Function ReplaceMaterialEsp(ByVal material As String, ByVal espNova As Double) As String

    Dim re As Object
    Dim espTxt As String

    material = CleanText(material)
    espTxt = FormatEspMaterial(espNova)

    If Len(material) = 0 Or Len(espTxt) = 0 Then
        ReplaceMaterialEsp = material
        Exit Function
    End If

    Set re = CreateObject("VBScript.RegExp")
    With re
        .Global = False
        .IgnoreCase = True
        .pattern = "_(\d+(?:[.,]\d+)?)MM$"
    End With

    If re.Test(material) Then
        ReplaceMaterialEsp = re.Replace(material, "_" & espTxt & "MM")
    Else
        ReplaceMaterialEsp = material & "_" & espTxt & "MM"
    End If

End Function

'------------------------------------------------------------
' Família do material
'------------------------------------------------------------
Private Function MaterialFamilyKey(ByVal material As String) As String

    Dim re As Object

    material = CleanText(material)
    If Len(material) = 0 Then Exit Function

    Set re = CreateObject("VBScript.RegExp")
    With re
        .Global = False
        .IgnoreCase = True
        .pattern = "_(\d+(?:[.,]\d+)?)MM$"
    End With

    If re.Test(material) Then
        MaterialFamilyKey = re.Replace(material, "")
    Else
        MaterialFamilyKey = material
    End If

End Function

'------------------------------------------------------------
' Formata a espessura para o sufixo do material
'------------------------------------------------------------
Private Function FormatEspMaterial(ByVal esp As Double) As String

    If esp <= 0 Then Exit Function
    FormatEspMaterial = Replace(Format(esp, "0.############"), ",", ".")

End Function

'============================================================
' ======== NOVA ZONA FLEXÍVEL PARA ORLAS ====================
'============================================================

'------------------------------------------------------------
' Devolve a família da orla
'
' Exemplos:
'   PVC_0.4_LINHO       -> PVC
'   FOL_1.0_CARVALHO    -> FOL
'   ABS_0.4_H1334/ST9   -> ABS
'   ABS:0.8_PRETO       -> ABS
'   ORLA_LASER_1.2      -> ORLA_LASER
'
' Se não reconhecer, devolve vazio.
'------------------------------------------------------------
Private Function GetFamiliaOrla(ByVal v As Variant) As String

    Dim s As String
    s = UCase$(CleanText(v))

    If Len(s) = 0 Then Exit Function

    If Left$(s, 11) = "ORLA_LASER_" Then
        GetFamiliaOrla = "ORLA_LASER"
        Exit Function
    End If

    If Left$(s, 4) = "PVC_" Then
        GetFamiliaOrla = "PVC"
        Exit Function
    End If

    If Left$(s, 4) = "FOL_" Then
        GetFamiliaOrla = "FOL"
        Exit Function
    End If

    If Left$(s, 4) = "ABS_" Or Left$(s, 4) = "ABS:" Then
        GetFamiliaOrla = "ABS"
        Exit Function
    End If

End Function

'------------------------------------------------------------
' Diz se a orla é válida para cálculo
'------------------------------------------------------------
Private Function IsOrlaValidaParaCalculo(ByVal v As Variant) As Boolean

    Dim s As String
    s = UCase$(CleanText(v))

    If Len(s) = 0 Then Exit Function
    If s = "0" Then Exit Function
    If s = "(EM BRANCO)" Or s = "(BLANK)" Then Exit Function

    IsOrlaValidaParaCalculo = (Len(GetFamiliaOrla(s)) > 0)

End Function

'------------------------------------------------------------
' Extrai a espessura da orla
'
' Regras atuais:
'   PVC_0.4_...         -> 0.4
'   FOL_1.0_...         -> 1.0
'   ABS_0.4_...         -> 0.4
'   ABS:0.8_...         -> 0.8
'   ORLA_LASER_1.2      -> 1.2
'
' Tem fallback para apanhar o primeiro número.
'------------------------------------------------------------
Private Function ExtractOrlaEsp(ByVal s As String) As Double

    s = UCase$(CleanText(s))
    If Len(s) = 0 Then
        ExtractOrlaEsp = 0
        Exit Function
    End If

    Dim familia As String
    familia = GetFamiliaOrla(s)

    Dim re As Object, m As Object
    Set re = CreateObject("VBScript.RegExp")

    Select Case familia

        Case "PVC", "FOL", "ABS"
            With re
                .Global = False
                .IgnoreCase = True
                .pattern = "^(?:PVC|FOL|ABS)[_:](\d+(?:[.,]\d+)?)"
            End With

            If re.Test(s) Then
                Set m = re.Execute(s)(0)
                ExtractOrlaEsp = ToDouble(m.SubMatches(0))
                Exit Function
            End If

        Case "ORLA_LASER"
            With re
                .Global = False
                .IgnoreCase = True
                .pattern = "^ORLA_LASER_(\d+(?:[.,]\d+)?)"
            End With

            If re.Test(s) Then
                Set m = re.Execute(s)(0)
                ExtractOrlaEsp = ToDouble(m.SubMatches(0))
                Exit Function
            End If

    End Select

    ' fallback: primeiro número que aparecer
    With re
        .Global = False
        .IgnoreCase = True
        .pattern = "(\d+(?:[.,]\d+)?)"
    End With

    If re.Test(s) Then
        Set m = re.Execute(s)(0)
        ExtractOrlaEsp = ToDouble(m.SubMatches(0))
    Else
        ExtractOrlaEsp = 0
    End If

End Function

Private Function FormatLargXEsp(ByVal largFita As Long, ByVal espOrla As Double) As String
    If largFita <= 0 Or espOrla <= 0 Then
        FormatLargXEsp = vbNullString
    Else
        FormatLargXEsp = CStr(largFita) & " x " & Replace(Format(espOrla, "0.0"), ",", ".")
    End If
End Function

'------------------------------------------------------------
' ARREDONDAR SEMPRE PARA CIMA A METRO INTEIRO
'------------------------------------------------------------
Private Function CeilInt(ByVal v As Double) As Long
    If v <= 0 Then
        CeilInt = 0
    Else
        CeilInt = CLng(-Int(-(v - 0.0000001)))
    End If
End Function

'------------------------------------------------------------
' Escolhe a largura da fita conforme a espessura do material
'------------------------------------------------------------
Private Function GetLarguraFita(ByVal espPeca As Long) As Long

    If espPeca <= 0 Then
        GetLarguraFita = 0
        Exit Function
    End If

    Select Case espPeca
        Case Is <= 12: GetLarguraFita = 15
        Case Is <= 16: GetLarguraFita = 19
        Case Is <= 19: GetLarguraFita = 22
        Case Is <= 22: GetLarguraFita = 25
        Case Is <= 25: GetLarguraFita = 28
        Case Is <= 30: GetLarguraFita = 33
        Case Is <= 35: GetLarguraFita = 38
        Case Is <= 40: GetLarguraFita = 43
        Case Is <= 45: GetLarguraFita = 48
        Case Is <= 53: GetLarguraFita = 55
        Case Else:     GetLarguraFita = 60
    End Select

End Function

'============================================================
' ======== AVISOS AO UTILIZADOR =============================
'============================================================

'------------------------------------------------------------
' Regista aviso de texto inválido
'------------------------------------------------------------
Private Sub CheckOrlaTexto(ByRef avisos As Collection, ByVal linhaTabela As Long, ByVal idVal As String, _
                           ByVal material As String, ByVal espPeca As Double, _
                           ByVal campo As String, ByVal valor As Variant)

    Dim s As String
    s = UCase$(CleanText(valor))

    If Len(s) = 0 Then Exit Sub
    If s = "0" Then Exit Sub
    If s = "(EM BRANCO)" Or s = "(BLANK)" Then Exit Sub

    If Not IsOrlaValidaParaCalculo(s) Then
        AddAviso avisos, "ORLA_TEXTO_INVALIDO", linhaTabela, idVal, material, espPeca, campo, s, _
                 "Valor de orla ignorado. Famílias aceites atualmente: PVC_, FOL_, ABS_, ABS: e ORLA_LASER_."
    End If
End Sub

'------------------------------------------------------------
' Guarda um aviso
'------------------------------------------------------------
Private Sub AddAviso(ByRef avisos As Collection, ByVal tipo As String, ByVal linhaTabela As Long, _
                     ByVal idVal As String, ByVal material As String, ByVal esp As Double, _
                     ByVal campo As String, ByVal valor As String, ByVal detalhe As String)

    avisos.Add Array(tipo, linhaTabela, idVal, material, esp, campo, valor, detalhe)
End Sub

'------------------------------------------------------------
' Cria/Atualiza a folha de avisos
'------------------------------------------------------------
Private Sub WriteAvisosOrlasSheet(ByVal avisos As Collection)

    Dim wsA As Worksheet
    Set wsA = GetOrCreateSheetAfter(SH_AVISOS, SH_RESUMO)

    On Error Resume Next
    wsA.Unprotect
    On Error GoTo 0

    wsA.Cells.Clear

    wsA.Range("A1").Value = "Tipo"
    wsA.Range("B1").Value = "Linha_Tabela"
    wsA.Range("C1").Value = "ID"
    wsA.Range("D1").Value = "Material"
    wsA.Range("E1").Value = "Esp"
    wsA.Range("F1").Value = "Campo"
    wsA.Range("G1").Value = "Valor"
    wsA.Range("H1").Value = "Detalhe"

    wsA.Range("A1:H1").Font.bold = True

    Dim i As Long, a As Variant
    For i = 1 To avisos.Count
        a = avisos(i)
        wsA.Cells(i + 1, 1).Value = a(0)
        wsA.Cells(i + 1, 2).Value = a(1)
        wsA.Cells(i + 1, 3).Value = a(2)
        wsA.Cells(i + 1, 4).Value = a(3)
        wsA.Cells(i + 1, 5).Value = a(4)
        wsA.Cells(i + 1, 6).Value = a(5)
        wsA.Cells(i + 1, 7).Value = a(6)
        wsA.Cells(i + 1, 8).Value = a(7)
    Next i

    wsA.Columns("A:H").AutoFit
End Sub

'------------------------------------------------------------
' Mostra resumo final ao utilizador
'------------------------------------------------------------
Private Sub ShowAvisosOrlas(ByVal avisos As Collection)

    Dim cntEsp As Long, cntTxt As Long, cntEspOrla As Long
    Dim i As Long, a As Variant

    For i = 1 To avisos.Count
        a = avisos(i)
        Select Case CStr(a(0))
            Case "ESPESSURA_EM_FALTA": cntEsp = cntEsp + 1
            Case "ORLA_TEXTO_INVALIDO": cntTxt = cntTxt + 1
            Case "ESP_ORLA_NAO_ENCONTRADA": cntEspOrla = cntEspOrla + 1
        End Select
    Next i

    Dim detalhes As String
    detalhes = ""

    Dim shown As Long
    shown = 0
    For i = 1 To avisos.Count
        a = avisos(i)
        shown = shown + 1
        If shown > MAX_AVISOS_MSG Then Exit For

        If CLng(a(1)) > 0 Then
            detalhes = detalhes & "- Linha_Tabela=" & a(1) & _
                       IIf(Len(CStr(a(2))) > 0, " | ID=" & a(2), "") & _
                       " | " & a(0) & " | " & a(7) & vbCrLf
        Else
            detalhes = detalhes & "- " & a(0) & " | " & a(6) & " | " & a(7) & vbCrLf
        End If
    Next i

    Dim msg As String
    msg = "Foram encontrados avisos durante o cálculo das orlas:" & vbCrLf & vbCrLf & _
          "- Espessura em falta (ESP/ESPFINAL=0/vazio): " & cntEsp & vbCrLf & _
          "- Texto de orla inválido: " & cntTxt & vbCrLf & _
          "- Orla sem espessura identificável no nome: " & cntEspOrla & vbCrLf & vbCrLf & _
          "Foi criada/atualizada a folha '" & SH_AVISOS & "' com o detalhe." & vbCrLf & vbCrLf & _
          "Primeiros avisos:" & vbCrLf & detalhes

    MsgBox msg, vbExclamation, "Avisos - ResumoOrlas"
End Sub

'============================================================
' ================== HELPERS GERAIS =========================
'============================================================

Private Function GetOrCreateSheetAfter(ByVal shName As String, ByVal afterSheetName As String) As Worksheet
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(shName)
    On Error GoTo 0

    If ws Is Nothing Then
        On Error Resume Next
        Set ws = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(afterSheetName))
        If ws Is Nothing Then
            Err.Clear
            Set ws = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        End If
        On Error GoTo 0
        ws.Name = shName
    Else
        On Error Resume Next
        If ws.Index <> ThisWorkbook.Worksheets(afterSheetName).Index + 1 Then
            ws.Move After:=ThisWorkbook.Worksheets(afterSheetName)
        End If
        On Error GoTo 0
    End If

    Set GetOrCreateSheetAfter = ws
End Function

Private Function GetColIndexByNorm(ByVal lo As ListObject, ByVal normName As String) As Long
    Dim i As Long
    normName = UCase$(normName)

    For i = 1 To lo.ListColumns.Count
        If NormalizeHeader(lo.ListColumns(i).Name) = normName Then
            GetColIndexByNorm = i
            Exit Function
        End If
    Next i
    GetColIndexByNorm = 0
End Function

Private Function GetListColIndexByNorm(ByVal lo As ListObject, ByVal normName As String) As Long
    GetListColIndexByNorm = GetColIndexByNorm(lo, normName)
End Function

Private Function NormalizeHeader(ByVal s As String) As String
    s = CStr(s)
    s = Replace(s, vbCr, "")
    s = Replace(s, vbLf, "")
    s = UCase$(Trim$(s))

    Dim i As Long, ch As String, out As String
    out = ""

    For i = 1 To Len(s)
        ch = Mid$(s, i, 1)
        If (ch >= "A" And ch <= "Z") Or (ch >= "0" And ch <= "9") Then
            out = out & ch
        End If
    Next i

    NormalizeHeader = out
End Function

Private Function CleanText(ByVal v As Variant) As String
    Dim s As String
    s = CStr(Nz(v, ""))

    s = Replace(s, Chr(160), " ")
    s = Trim$(s)

    CleanText = s
End Function

Private Function Nz(ByVal v As Variant, ByVal Fallback As Variant) As Variant
    If IsError(v) Then Nz = Fallback: Exit Function
    If IsEmpty(v) Then Nz = Fallback: Exit Function
    If v = vbNullString Then Nz = Fallback: Exit Function
    Nz = v
End Function

Private Function ToDouble(ByVal v As Variant) As Double
    Dim s As String

    If IsError(v) Or IsEmpty(v) Then
        ToDouble = 0
        Exit Function
    End If

    If IsNumeric(v) Then
        ToDouble = CDbl(v)
        Exit Function
    End If

    s = CStr(v)
    s = Replace(s, Chr(160), "")
    s = Replace(s, " ", "")
    s = Replace(s, ".", ",")

    If IsNumeric(s) Then
        ToDouble = CDbl(s)
    Else
        ToDouble = 0
    End If
End Function

Private Function SafeEvalText(ByVal nameOrFormula As String) As String
    On Error GoTo EH

    Dim v As Variant
    v = Application.Evaluate(nameOrFormula)
    If IsError(v) Then
        SafeEvalText = ""
        Exit Function
    End If

    SafeEvalText = CleanText(v)
    Exit Function

EH:
    SafeEvalText = ""
End Function



