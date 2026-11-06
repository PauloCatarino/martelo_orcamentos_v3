Option Explicit

'====================================================================
'  frmColar - menu para preencher a coluna "Colar"   (ENSAIO 06-11-2026)
'--------------------------------------------------------------------
'  Abre-se com o botão "Colar" da LISTAGEM_CUT_RITE ou com duplo clique numa
'  célula da coluna Colar. O utilizador escolhe as peças a colar (pelo ID),
'  quantas de cada, o que passa na CNC e que orla leva depois da colagem
'  (clicando nas arestas do desenho da peça); o menu monta o código e grava-o
'  em todas as peças do conjunto, com a Qt e os excedentes +comp/+Larg.
'
'  O formulário no modelo está vazio: os controlos criam-se aqui, no
'  UserForm_Initialize, para o menu todo viver em texto no repositório do
'  Martelo (scripts/vba/colar/frmColar.vba). As regras estão no modColar.
'
'  2.ª ronda (06-11-2026, pedido do Paulo no teste da obra 1935_01):
'    - Qt das peças = quantas entram no conjunto (5+5 -> Qt 2);
'    - espessuras com tolerância (as colas também contam): o que manda é a Esp do iMos;
'    - +comp / +Larg = 20 por defeito (excedente de corte), editáveis;
'    - pesquisa na lista das peças;
'    - orlas depois da colagem clicando nas arestas do desenho da peça.
'====================================================================

Private Const EXCEDENTE_POR_DEFEITO As String = "20"
Private Const TOLERANCIA_MM As Double = 2

Private WithEvents lstPecas As MSForms.ListBox
Private WithEvents txtPesquisa As MSForms.TextBox
Private WithEvents chkSoVermelhas As MSForms.CheckBox
Private WithEvents btnAdicionar As MSForms.CommandButton
Private WithEvents lstConjunto As MSForms.ListBox
Private WithEvents btnTirar As MSForms.CommandButton
Private WithEvents btnMais As MSForms.CommandButton
Private WithEvents btnMenos As MSForms.CommandButton
Private WithEvents chkCncInicio As MSForms.CheckBox
Private WithEvents chkCncFim As MSForms.CheckBox
Private WithEvents chkRaio As MSForms.CheckBox
Private WithEvents lblArestaC1 As MSForms.Label
Private WithEvents lblArestaC2 As MSForms.Label
Private WithEvents lblArestaL1 As MSForms.Label
Private WithEvents lblArestaL2 As MSForms.Label
Private WithEvents btnQuatroLados As MSForms.CommandButton
Private WithEvents btnSemOrla As MSForms.CommandButton
Private WithEvents btnGravar As MSForms.CommandButton
Private WithEvents btnLimpar As MSForms.CommandButton
Private WithEvents btnVerificar As MSForms.CommandButton
Private WithEvents btnFechar As MSForms.CommandButton
Private txtQt As MSForms.TextBox
Private txtMaisComp As MSForms.TextBox
Private txtMaisLarg As MSForms.TextBox
Private chkMudarQt As MSForms.CheckBox
Private lblPeca As MSForms.Label
Private lblMedidaC As MSForms.Label
Private lblMedidaL As MSForms.Label
Private lblCodigoOrlas As MSForms.Label
Private lblCodigo As MSForms.Label
Private lblEsp As MSForms.Label
Private lblEstado As MSForms.Label

Private mConj As Object          ' ID (texto) -> quantidade, pela ordem em que entram
Private mCodigoAntigo As String  ' código da linha de onde o menu abriu (para editar)
Private mLo As ListObject
Private cId As Long, cDesc As Long, cMat As Long, cComp As Long, cLarg As Long
Private cQt As Long, cEsp As Long, cEspMat As Long, cEspFinal As Long, cColar As Long
Private cMaisComp As Long, cMaisLarg As Long
Private mAPreparar As Boolean
' Arestas com orla depois da colagem: C1 (comprimento de baixo), C2 (de cima),
' L1 (largura da esquerda), L2 (da direita).
Private mC1 As Boolean, mC2 As Boolean, mL1 As Boolean, mL2 As Boolean

' Zona do desenho da peça
Private Const DES_ESQ As Single = 330
Private Const DES_TOPO As Single = 404
Private Const DES_LARG As Single = 230
Private Const DES_ALT As Single = 96
Private Const LARG_ARESTA As Single = 7

'====================================================================
'  ABRIR
'====================================================================
Private Sub UserForm_Initialize()
    mAPreparar = True
    Me.Caption = "Colar - peças a colar (ensaio)"
    Me.Width = 760
    Me.Height = 662
    Set mConj = CreateObject("Scripting.Dictionary")
    Set mLo = ColarTabela()
    cId = ColarIndice("ID")
    cDesc = ColarIndice("DESCRICAO")
    cMat = ColarIndice("MATERIAL")
    cComp = ColarIndice("COMP")
    cLarg = ColarIndice("LARG")
    cQt = ColarIndice("QT")
    cEsp = ColarIndice("ESP")
    cEspMat = ColarIndice("ESPMAT")
    cEspFinal = ColarIndice("ESPFINAL")
    cColar = ColarIndice("COLAR")
    cMaisComp = ColarIndiceMais("COMP")
    cMaisLarg = ColarIndiceMais("LARG")

    CriarControlos
    chkSoVermelhas.Value = (ContarVermelhas() > 0)
    PreencherPecas
    PrepararPelaCelulaAtiva
    mAPreparar = False
    Atualizar
End Sub

Private Function Novo(ByVal tipo As String, ByVal nome As String, ByVal esquerda As Single, _
                      ByVal topo As Single, ByVal largura As Single, ByVal altura As Single, _
                      Optional ByVal dica As String = "") As Object
    Dim c As Object
    Set c = Me.Controls.Add(tipo, nome, True)
    c.Left = esquerda
    c.Top = topo
    c.Width = largura
    c.Height = altura
    If Len(dica) > 0 Then c.ControlTipText = dica
    Set Novo = c
End Function

Private Function Rotulo(ByVal nome As String, ByVal texto As String, ByVal esquerda As Single, _
                        ByVal topo As Single, ByVal largura As Single, ByVal altura As Single, _
                        Optional ByVal negrito As Boolean = False) As MSForms.Label
    Dim l As MSForms.Label
    Set l = Novo("Forms.Label.1", nome, esquerda, topo, largura, altura)
    l.Caption = texto
    l.WordWrap = True
    l.Font.Bold = negrito
    Set Rotulo = l
End Function

Private Function Aresta(ByVal nome As String, ByVal dica As String) As MSForms.Label
    Dim l As MSForms.Label
    Set l = Novo("Forms.Label.1", nome, DES_ESQ, DES_TOPO, LARG_ARESTA, LARG_ARESTA, dica)
    l.Caption = ""
    l.BackStyle = fmBackStyleOpaque
    l.MousePointer = fmMousePointerUpArrow
    Set Aresta = l
End Function

Private Sub CriarControlos()
    Dim l As MSForms.Label

    Rotulo "lblAjuda", "Escolha as peças que se colam (linhas da LISTAGEM_CUT_RITE, pelo ID), o que passa " & _
        "na CNC e a orla depois da colagem. «Gravar» escreve o código na coluna Colar de todas as peças " & _
        "do conjunto (e a Qt e o +comp/+Larg). Preencha a Colar no fim: se inserir ou apagar linhas, os IDs mudam.", _
        8, 6, 736, 28

    ' 1. Peças da listagem
    Rotulo "lbl1", "1. Peças da listagem   (ID | Descrição | Material | Comp x Larg | Qt | Esp.Mat | Esp | Colar)", _
        8, 40, 470, 14, True
    Set chkSoVermelhas = Novo("Forms.CheckBox.1", "chkSoVermelhas", 486, 38, 258, 16, _
        "Mostrar só as linhas com o Material a vermelho: a espessura do material é diferente da Esp do iMos.")
    chkSoVermelhas.Caption = "Só as linhas a vermelho (espessura diferente)"
    Rotulo "lblPesquisa", "Pesquisar:", 8, 60, 52, 14
    Set txtPesquisa = Novo("Forms.TextBox.1", "txtPesquisa", 62, 57, 682, 18, _
        "Filtrar a lista: escreva parte do ID, da descrição, do material, das medidas ou do código " & _
        "(várias palavras = todas têm de aparecer).")

    Set lstPecas = Novo("Forms.ListBox.1", "lstPecas", 8, 80, 736, 132, _
        "Selecione uma ou mais peças (Ctrl/Shift para várias) e carregue em «Juntar ao conjunto», " & _
        "ou faça duplo clique numa peça.")
    lstPecas.ColumnCount = 8
    lstPecas.ColumnWidths = "28;150;206;84;26;42;30;160"
    lstPecas.MultiSelect = fmMultiSelectExtended

    Rotulo "lblQt", "Quantas de cada:", 8, 222, 80, 14
    Set txtQt = Novo("Forms.TextBox.1", "txtQt", 88, 219, 34, 18, _
        "Quantas peças de cada linha escolhida entram no conjunto (ex.: 2 para duas peças iguais).")
    txtQt.Text = "1"
    Set btnAdicionar = Novo("Forms.CommandButton.1", "btnAdicionar", 130, 217, 170, 22, _
        "Juntar as peças selecionadas ao conjunto, com a quantidade ao lado.")
    btnAdicionar.Caption = "Juntar ao conjunto"

    ' 2. Conjunto
    Rotulo "lbl2", "2. Conjunto a colar   (ID | Qt | Descrição | Esp.Mat | Esp)", 8, 248, 460, 14, True
    Set lstConjunto = Novo("Forms.ListBox.1", "lstConjunto", 8, 264, 460, 96, _
        "As peças do conjunto. Selecione uma para lhe mudar a quantidade ou a tirar.")
    lstConjunto.ColumnCount = 5
    lstConjunto.ColumnWidths = "30;28;270;60;40"
    Set btnMais = Novo("Forms.CommandButton.1", "btnMais", 476, 264, 40, 22, _
        "Mais uma peça do ID selecionado no conjunto.")
    btnMais.Caption = "+1"
    Set btnMenos = Novo("Forms.CommandButton.1", "btnMenos", 520, 264, 40, 22, _
        "Menos uma peça do ID selecionado (a 0 sai do conjunto).")
    btnMenos.Caption = "-1"
    Set btnTirar = Novo("Forms.CommandButton.1", "btnTirar", 564, 264, 120, 22, _
        "Tirar do conjunto a peça selecionada.")
    btnTirar.Caption = "Tirar do conjunto"
    Set lblEsp = Rotulo("lblEsp", "", 476, 290, 268, 70)

    ' 3. CNC, Qt e excedentes
    Rotulo "lbl3", "3. CNC, quantidade e excedentes de corte", 8, 370, 300, 14, True
    Set chkCncInicio = Novo("Forms.CheckBox.1", "chkCncInicio", 8, 386, 290, 16, _
        "As peças passam na CNC ANTES de serem coladas (o código começa por CNC_).")
    chkCncInicio.Caption = "CNC antes da colagem (CNC no início)"
    Set chkCncFim = Novo("Forms.CheckBox.1", "chkCncFim", 8, 404, 290, 16, _
        "O conjunto já colado passa na CNC no FIM (o código acaba em _CNC).")
    chkCncFim.Caption = "CNC depois da colagem (CNC no fim)"
    Set chkMudarQt = Novo("Forms.CheckBox.1", "chkMudarQt", 8, 428, 300, 16, _
        "A Qt de cada peça passa a ser quantas entram no conjunto (5+5 -> Qt 2): é o que o Cut-Rite corta.")
    chkMudarQt.Caption = "Qt da peça = quantas entram no conjunto"
    chkMudarQt.Value = True
    Rotulo "lblMais", "Excedente de corte:   +comp", 8, 454, 124, 14
    Set txtMaisComp = Novo("Forms.TextBox.1", "txtMaisComp", 134, 451, 36, 18, _
        "Milímetros a mais no comprimento, para acertar depois de colar (coluna +comp). Vazio = não mexe.")
    txtMaisComp.Text = EXCEDENTE_POR_DEFEITO
    Rotulo "lblMaisL", "+Larg", 178, 454, 30, 14
    Set txtMaisLarg = Novo("Forms.TextBox.1", "txtMaisLarg", 210, 451, 36, 18, _
        "Milímetros a mais na largura, para acertar depois de colar (coluna +Larg). Vazio = não mexe.")
    txtMaisLarg.Text = EXCEDENTE_POR_DEFEITO
    Rotulo "lblMaisNota", "(a etiqueta do Cut-Rite mostra a medida da peça e a de corte)", 8, 474, 300, 24

    ' 4. Orlas: desenho da peça com as arestas a clicar
    Rotulo "lbl4", "4. Orlar depois da colagem - clique nas arestas da peça", 320, 370, 424, 14, True
    Set lblPeca = Rotulo("lblPeca", "", DES_ESQ, DES_TOPO, DES_LARG, DES_ALT)
    lblPeca.BackStyle = fmBackStyleOpaque
    lblPeca.BackColor = RGB(240, 236, 228)
    lblPeca.TextAlign = fmTextAlignCenter
    lblPeca.Font.Size = 8
    Set lblArestaC1 = Aresta("lblArestaC1", "C1 - comprimento: clique para pôr ou tirar a orla.")
    Set lblArestaC2 = Aresta("lblArestaC2", "C2 - comprimento: clique para pôr ou tirar a orla.")
    Set lblArestaL1 = Aresta("lblArestaL1", "L1 - largura: clique para pôr ou tirar a orla.")
    Set lblArestaL2 = Aresta("lblArestaL2", "L2 - largura: clique para pôr ou tirar a orla.")
    Set lblMedidaC = Rotulo("lblMedidaC", "", DES_ESQ, DES_TOPO + DES_ALT + 4, DES_LARG, 14)
    lblMedidaC.TextAlign = fmTextAlignCenter
    Set lblMedidaL = Rotulo("lblMedidaL", "", DES_ESQ + DES_LARG + 4, DES_TOPO + DES_ALT / 2 - 7, 60, 14)
    Set btnQuatroLados = Novo("Forms.CommandButton.1", "btnQuatroLados", 630, 404, 114, 22, _
        "Orla nas 4 arestas (O4L).")
    btnQuatroLados.Caption = "4 lados (O4L)"
    Set btnSemOrla = Novo("Forms.CommandButton.1", "btnSemOrla", 630, 430, 114, 22, _
        "Tirar a orla de todas as arestas.")
    btnSemOrla.Caption = "Sem orla"
    Set chkRaio = Novo("Forms.CheckBox.1", "chkRaio", 630, 458, 114, 16, _
        "Orlar o raio / meia-lua depois da colagem (OR).")
    chkRaio.Caption = "Raio / meia-lua (OR)"
    Set lblCodigoOrlas = Rotulo("lblCodigoOrlas", "", 630, 480, 114, 28, True)
    Rotulo "lblNotaOrla", "A orla que a peça já leva antes de colar continua nas colunas Orla da própria peça.", _
        320, 518, 424, 14

    Set lblCodigo = Rotulo("lblCodigo", "", 8, 536, 736, 24, True)
    lblCodigo.Font.Size = 14

    Set btnGravar = Novo("Forms.CommandButton.1", "btnGravar", 8, 566, 210, 26, _
        "Escrever este código na coluna Colar de todas as peças do conjunto (e a Qt e o +comp/+Larg).")
    btnGravar.Caption = "Gravar nas peças do conjunto"
    Set btnLimpar = Novo("Forms.CommandButton.1", "btnLimpar", 226, 566, 200, 26, _
        "Apagar o código da coluna Colar das peças deste conjunto (a Qt e o +comp/+Larg ficam como estão).")
    btnLimpar.Caption = "Tirar o código destas peças"
    Set btnVerificar = Novo("Forms.CommandButton.1", "btnVerificar", 434, 566, 190, 26, _
        "Conferir os códigos de toda a listagem (IDs que não existem, conjuntos desencontrados).")
    btnVerificar.Caption = "Verificar toda a listagem"
    Set btnFechar = Novo("Forms.CommandButton.1", "btnFechar", 644, 566, 100, 26, "Fechar o menu.")
    btnFechar.Caption = "Fechar"

    ' Linha de estado ("supervisor") por baixo dos botões
    Set lblEstado = Rotulo("lblEstado", "", 8, 600, 736, 34)
    lblEstado.ForeColor = RGB(90, 90, 90)
End Sub

'====================================================================
'  LISTAGEM
'====================================================================
Private Function Celula(ByVal linha As Long, ByVal coluna As Long) As String
    Dim v As Variant
    If coluna = 0 Or mLo Is Nothing Then Exit Function
    On Error Resume Next
    v = mLo.DataBodyRange.Cells(linha, coluna).Value
    If IsError(v) Then Exit Function
    Celula = Trim$(CStr(v))
End Function

' Como a formatação condicional do Material: espessura do material diferente da Esp.
Private Function EspDiferente(ByVal linha As Long) As Boolean
    Dim espMat As String, espFinal As String
    If Len(Celula(linha, cMat)) = 0 Then Exit Function
    espMat = Celula(linha, cEspMat)
    If cEspFinal > 0 Then espFinal = Celula(linha, cEspFinal) Else espFinal = Celula(linha, cEsp)
    EspDiferente = (Len(espMat) = 0 Or Len(espFinal) = 0 Or espMat <> espFinal)
End Function

Private Function ContarVermelhas() As Long
    Dim r As Long
    If mLo Is Nothing Then Exit Function
    If mLo.DataBodyRange Is Nothing Then Exit Function
    For r = 1 To mLo.ListRows.Count
        If EspDiferente(r) Then ContarVermelhas = ContarVermelhas + 1
    Next r
End Function

' Todas as palavras da pesquisa aparecem no texto da linha.
Private Function PassaPesquisa(ByVal linha As Long) As Boolean
    Dim palavras() As String, texto As String, i As Long
    If Len(Trim$(txtPesquisa.Text)) = 0 Then
        PassaPesquisa = True
        Exit Function
    End If
    texto = LCase$(Celula(linha, cId) & " " & Celula(linha, cDesc) & " " & Celula(linha, cMat) & " " & _
                   Celula(linha, cComp) & " " & Celula(linha, cLarg) & " " & Celula(linha, cEsp) & " " & _
                   Celula(linha, cColar))
    palavras = Split(LCase$(Trim$(txtPesquisa.Text)), " ")
    For i = LBound(palavras) To UBound(palavras)
        If Len(palavras(i)) > 0 Then
            If InStr(texto, palavras(i)) = 0 Then Exit Function
        End If
    Next i
    PassaPesquisa = True
End Function

Private Sub PreencherPecas()
    Dim r As Long, i As Long
    lstPecas.Clear
    If mLo Is Nothing Then Exit Sub
    If mLo.DataBodyRange Is Nothing Then Exit Sub
    For r = 1 To mLo.ListRows.Count
        If Len(Celula(r, cDesc)) > 0 Or Len(Celula(r, cMat)) > 0 Then
            If ((Not chkSoVermelhas.Value) Or EspDiferente(r)) And PassaPesquisa(r) Then
                lstPecas.AddItem Celula(r, cId)
                i = lstPecas.ListCount - 1
                lstPecas.List(i, 1) = Celula(r, cDesc)
                lstPecas.List(i, 2) = Celula(r, cMat)
                lstPecas.List(i, 3) = Celula(r, cComp) & " x " & Celula(r, cLarg)
                lstPecas.List(i, 4) = Celula(r, cQt)
                lstPecas.List(i, 5) = Celula(r, cEspMat)
                lstPecas.List(i, 6) = Celula(r, cEsp)
                lstPecas.List(i, 7) = Celula(r, cColar)
            End If
        End If
    Next r
End Sub

' Linha da tabela onde está a célula ativa (0 = fora da tabela).
Private Function LinhaDaCelulaAtiva() As Long
    On Error GoTo Fim
    If mLo Is Nothing Then Exit Function
    If mLo.DataBodyRange Is Nothing Then Exit Function
    If ActiveSheet.Name <> mLo.Parent.Name Then Exit Function
    If Intersect(ActiveCell, mLo.DataBodyRange) Is Nothing Then Exit Function
    LinhaDaCelulaAtiva = ActiveCell.Row - mLo.DataBodyRange.Row + 1
Fim:
End Function

' Abrir na linha certa: se ela já tem código, edita esse conjunto; senão, a peça
' entra no conjunto novo.
Private Sub PrepararPelaCelulaAtiva()
    Dim r As Long, cod As String, motivo As String, conj As Object
    Dim ci As Boolean, cf As Boolean, nc As Long, nl As Long, ra As Boolean
    r = LinhaDaCelulaAtiva()
    If r = 0 Then
        Estado "Escolha as peças do conjunto na lista de cima."
        Exit Sub
    End If
    cod = Celula(r, cColar)
    If Len(cod) > 0 Then
        motivo = ColarLer(cod, conj, ci, cf, nc, nl, ra)
        mCodigoAntigo = cod
        If Len(motivo) = 0 Then
            Set mConj = conj
            chkCncInicio.Value = ci
            chkCncFim.Value = cf
            mC1 = (nc >= 1): mC2 = (nc = 2)
            mL1 = (nl >= 1): mL2 = (nl = 2)
            chkRaio.Value = ra
            If Len(Celula(r, cMaisComp)) > 0 Then txtMaisComp.Text = Celula(r, cMaisComp)
            If Len(Celula(r, cMaisLarg)) > 0 Then txtMaisLarg.Text = Celula(r, cMaisLarg)
            Estado "A editar o conjunto «" & cod & "». «Gravar» muda o código em todas as peças dele."
            Exit Sub
        End If
        Estado "O código desta linha («" & cod & "») " & motivo & ". Refaça o conjunto e grave."
    End If
    If Len(Celula(r, cId)) > 0 Then
        If Not mConj.Exists(Celula(r, cId)) Then mConj.Add Celula(r, cId), 1
    End If
End Sub

'====================================================================
'  CONJUNTO, DESENHO E CÓDIGO
'====================================================================
Private Function NComp() As Long
    NComp = IIf(mC1, 1, 0) + IIf(mC2, 1, 0)
End Function

Private Function NLarg() As Long
    NLarg = IIf(mL1, 1, 0) + IIf(mL2, 1, 0)
End Function

Private Function CodigoAtual() As String
    CodigoAtual = ColarMontar(chkCncInicio.Value, mConj, _
        ColarOrlasTexto(NComp(), NLarg(), chkRaio.Value), chkCncFim.Value)
End Function

Private Function Numero(ByVal s As String) As Double
    s = Replace(Trim$(s), ",", ".")
    If Len(s) = 0 Then
        Numero = -1
    Else
        Numero = Val(s)
    End If
End Function

' Desenha a 1.ª peça do conjunto com as proporções Comp x Larg e as arestas.
Private Sub DesenharPeca()
    Dim comp As Double, larg As Double, w As Single, h As Single, x As Single, y As Single
    Dim r As Long, k As Variant, desc As String
    comp = 600: larg = 400
    For Each k In mConj.Keys
        r = ColarLinhaDoId(CStr(k))
        If r > 0 Then
            If Numero(Celula(r, cComp)) > 0 Then comp = Numero(Celula(r, cComp))
            If Numero(Celula(r, cLarg)) > 0 Then larg = Numero(Celula(r, cLarg))
            desc = Celula(r, cDesc)
            Exit For
        End If
    Next k
    ' Comprimento na horizontal; proporção limitada para caber e ser clicável.
    w = DES_LARG
    h = w * larg / comp
    If h > DES_ALT Then
        h = DES_ALT
        w = h * comp / larg
    End If
    If h < 22 Then h = 22
    If w < 40 Then w = 40
    x = DES_ESQ + (DES_LARG - w) / 2
    y = DES_TOPO + (DES_ALT - h) / 2

    lblPeca.Left = x: lblPeca.Top = y: lblPeca.Width = w: lblPeca.Height = h
    lblPeca.Caption = vbLf & desc
    PorAresta lblArestaC2, x, y - LARG_ARESTA, w, LARG_ARESTA, mC2          ' C2 em cima
    PorAresta lblArestaC1, x, y + h, w, LARG_ARESTA, mC1               ' C1 em baixo
    PorAresta lblArestaL1, x - LARG_ARESTA, y, LARG_ARESTA, h, mL1          ' L1 à esquerda
    PorAresta lblArestaL2, x + w, y, LARG_ARESTA, h, mL2               ' L2 à direita
    lblMedidaC.Left = x: lblMedidaC.Width = w: lblMedidaC.Top = y + h + LARG_ARESTA + 2
    lblMedidaC.Caption = "C1  " & comp & " mm  (C2 em cima)"
    lblMedidaL.Left = x + w + LARG_ARESTA + 4: lblMedidaL.Top = y + h / 2 - 7
    lblMedidaL.Caption = "L2  " & larg
    lblCodigoOrlas.Caption = "Orlas: " & IIf(Len(ColarOrlasTexto(NComp(), NLarg(), chkRaio.Value)) = 0, _
        "nenhuma", ColarOrlasTexto(NComp(), NLarg(), chkRaio.Value))
End Sub

Private Sub PorAresta(ByVal l As MSForms.Label, ByVal x As Single, ByVal y As Single, _
                      ByVal w As Single, ByVal h As Single, ByVal comOrla As Boolean)
    l.Left = x: l.Top = y: l.Width = w: l.Height = h
    If comOrla Then
        l.BackColor = RGB(92, 64, 46)        ' orla
    Else
        l.BackColor = RGB(215, 215, 215)     ' sem orla
    End If
End Sub

Private Sub Atualizar()
    Dim k As Variant, r As Long, i As Long, q As Long
    Dim soma As Double, partes As String, alvo As Double, espTxt As String, cod As String
    Dim semEsp As Boolean, avaliacao As String
    If mAPreparar Then Exit Sub

    lstConjunto.Clear
    alvo = -1
    For Each k In mConj.Keys
        q = CLng(mConj(k))
        r = ColarLinhaDoId(CStr(k))
        lstConjunto.AddItem CStr(k)
        i = lstConjunto.ListCount - 1
        lstConjunto.List(i, 1) = q
        If r > 0 Then
            lstConjunto.List(i, 2) = Celula(r, cDesc)
            lstConjunto.List(i, 3) = Celula(r, cEspMat)
            lstConjunto.List(i, 4) = Celula(r, cEsp)
            espTxt = Celula(r, cEspMat)
            If Numero(espTxt) < 0 Then
                semEsp = True
            Else
                soma = soma + Numero(espTxt) * q
            End If
            If Len(partes) > 0 Then partes = partes & " + "
            If q = 1 Then partes = partes & espTxt Else partes = partes & espTxt & "x" & q
            If Numero(Celula(r, cEsp)) > alvo Then alvo = Numero(Celula(r, cEsp))
        Else
            lstConjunto.List(i, 2) = "(este ID não existe na listagem)"
        End If
    Next k

    If mConj.Count = 0 Then
        lblEsp.Caption = ""
    ElseIf semEsp Or alvo < 0 Then
        lblEsp.Caption = "Espessuras do conjunto: " & partes & " (há peças sem Esp.Mat ou sem Esp)."
    Else
        If Abs(alvo - soma) <= TOLERANCIA_MM Then
            avaliacao = "perto da Esp do iMos (as colas também contam)"
        Else
            avaliacao = "LONGE da Esp do iMos: confirme o conjunto ou se há material com esta espessura no Woodstore"
        End If
        lblEsp.Caption = "Esp no iMos: " & alvo & " mm  (é a que manda)" & vbLf & _
                         "Materiais: " & partes & " = aprox. " & soma & " mm" & vbLf & avaliacao
    End If

    DesenharPeca

    cod = CodigoAtual()
    If ColarTotalPecas(mConj) < 2 Then
        lblCodigo.Caption = "Código: (o conjunto precisa de pelo menos 2 peças)"
        btnGravar.Enabled = False
    Else
        lblCodigo.Caption = "Código: " & cod
        btnGravar.Enabled = True
    End If
End Sub

Private Sub Estado(ByVal texto As String)
    lblEstado.Caption = texto
End Sub

Private Function QuantidadeEscolhida() As Long
    QuantidadeEscolhida = CLng(Val(txtQt.Text))
    If QuantidadeEscolhida < 1 Then QuantidadeEscolhida = 1
End Function

Private Sub JuntarId(ByVal ident As String, ByVal q As Long)
    If Len(ident) = 0 Then Exit Sub
    If mConj.Exists(ident) Then
        mConj(ident) = CLng(mConj(ident)) + q
    Else
        mConj.Add ident, q
    End If
End Sub

Private Sub Repor()
    Set mConj = CreateObject("Scripting.Dictionary")
    mCodigoAntigo = ""
    chkCncInicio.Value = False
    chkCncFim.Value = False
    mC1 = False: mC2 = False: mL1 = False: mL2 = False
    chkRaio.Value = False
    txtMaisComp.Text = EXCEDENTE_POR_DEFEITO
    txtMaisLarg.Text = EXCEDENTE_POR_DEFEITO
End Sub

'====================================================================
'  EVENTOS
'====================================================================
Private Sub chkSoVermelhas_Click()
    If mAPreparar Then Exit Sub
    PreencherPecas
End Sub

Private Sub txtPesquisa_Change()
    If mAPreparar Then Exit Sub
    PreencherPecas
    Estado lstPecas.ListCount & " peça(s) na lista."
End Sub

Private Sub btnAdicionar_Click()
    Dim i As Long, n As Long, q As Long
    q = QuantidadeEscolhida()
    For i = 0 To lstPecas.ListCount - 1
        If lstPecas.Selected(i) Then
            JuntarId CStr(lstPecas.List(i, 0)), q
            lstPecas.Selected(i) = False
            n = n + 1
        End If
    Next i
    If n = 0 Then
        Estado "Selecione primeiro uma ou mais peças na lista de cima."
    Else
        Estado n & " peça(s) juntas ao conjunto."
    End If
    Atualizar
End Sub

Private Sub lstPecas_DblClick(ByVal Cancel As MSForms.ReturnBoolean)
    If lstPecas.ListIndex < 0 Then Exit Sub
    JuntarId CStr(lstPecas.List(lstPecas.ListIndex, 0)), QuantidadeEscolhida()
    Estado "ID " & lstPecas.List(lstPecas.ListIndex, 0) & " junto ao conjunto."
    Atualizar
End Sub

Private Function IdDoConjuntoSelecionado() As String
    If lstConjunto.ListIndex < 0 Then
        Estado "Selecione primeiro uma peça do conjunto."
        Exit Function
    End If
    IdDoConjuntoSelecionado = CStr(lstConjunto.List(lstConjunto.ListIndex, 0))
End Function

Private Sub btnMais_Click()
    Dim ident As String
    ident = IdDoConjuntoSelecionado()
    If Len(ident) = 0 Then Exit Sub
    JuntarId ident, 1
    Atualizar
End Sub

Private Sub btnMenos_Click()
    Dim ident As String
    ident = IdDoConjuntoSelecionado()
    If Len(ident) = 0 Then Exit Sub
    If CLng(mConj(ident)) <= 1 Then
        mConj.Remove ident
    Else
        mConj(ident) = CLng(mConj(ident)) - 1
    End If
    Atualizar
End Sub

Private Sub btnTirar_Click()
    Dim ident As String
    ident = IdDoConjuntoSelecionado()
    If Len(ident) = 0 Then Exit Sub
    If mConj.Exists(ident) Then mConj.Remove ident
    Estado "ID " & ident & " tirado do conjunto."
    Atualizar
End Sub

Private Sub chkCncInicio_Click()
    Atualizar
End Sub

Private Sub chkCncFim_Click()
    Atualizar
End Sub

Private Sub chkRaio_Click()
    Atualizar
End Sub

Private Sub lblArestaC1_Click()
    mC1 = Not mC1
    Atualizar
End Sub

Private Sub lblArestaC2_Click()
    mC2 = Not mC2
    Atualizar
End Sub

Private Sub lblArestaL1_Click()
    mL1 = Not mL1
    Atualizar
End Sub

Private Sub lblArestaL2_Click()
    mL2 = Not mL2
    Atualizar
End Sub

Private Sub btnQuatroLados_Click()
    mC1 = True: mC2 = True: mL1 = True: mL2 = True
    Atualizar
End Sub

Private Sub btnSemOrla_Click()
    mC1 = False: mC2 = False: mL1 = False: mL2 = False
    Atualizar
End Sub

Private Sub btnGravar_Click()
    Dim cod As String, msg As String
    If ColarTotalPecas(mConj) < 2 Then
        Estado "O conjunto precisa de pelo menos 2 peças."
        Exit Sub
    End If
    cod = CodigoAtual()
    msg = ColarGravar(mConj, cod, mCodigoAntigo, True, CBool(chkMudarQt.Value), _
                      Trim$(txtMaisComp.Text), Trim$(txtMaisLarg.Text))
    If Len(msg) = 0 Then
        Estado "Nada foi gravado."
        Exit Sub
    End If
    ' Pronto para o conjunto seguinte.
    Repor
    PreencherPecas
    Atualizar
    Estado msg
End Sub

Private Sub btnLimpar_Click()
    Dim n As Long
    If mConj.Count = 0 And Len(mCodigoAntigo) = 0 Then
        Estado "Não há peças no conjunto."
        Exit Sub
    End If
    If MsgBox("Apagar o código da coluna Colar das peças deste conjunto?" & vbCrLf & _
              "(a Qt e o +comp/+Larg ficam como estão)", _
              vbYesNo + vbQuestion + vbDefaultButton2, "Colar") <> vbYes Then Exit Sub
    n = ColarLimpar(mConj, mCodigoAntigo)
    Repor
    PreencherPecas
    Atualizar
    Estado "Código tirado de " & n & " linha(s). Reveja a Qt e o +comp/+Larg dessas peças."
End Sub

Private Sub btnVerificar_Click()
    Dim problemas As String
    problemas = ColarProblemas(15)
    If Len(problemas) = 0 Then
        Estado "Verificação: os códigos da coluna Colar estão certos."
        MsgBox "Coluna Colar: os códigos estão certos.", vbInformation, "Colar"
    Else
        Estado "Verificação: há códigos a corrigir (ver a mensagem)."
        MsgBox "Coluna Colar - a corrigir:" & vbCrLf & vbCrLf & problemas, vbExclamation, "Colar"
    End If
End Sub

Private Sub btnFechar_Click()
    Unload Me
End Sub
