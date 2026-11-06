Option Explicit

'====================================================================
'  frmColar - menu para preencher a coluna "Colar"   (ENSAIO 06-11-2026)
'--------------------------------------------------------------------
'  Abre-se com o botão "Colar" da LISTAGEM_CUT_RITE ou com duplo clique numa
'  célula da coluna Colar. O utilizador escolhe as peças a colar (pelo ID),
'  quantas de cada, o que passa na CNC e que orla leva depois da colagem;
'  o menu monta o código e grava-o em todas as peças do conjunto.
'
'  O formulário no modelo está vazio: os controlos criam-se aqui, no
'  UserForm_Initialize, para o menu todo viver em texto no repositório do
'  Martelo (scripts/vba/colar/frmColar.vba). As regras estão no modColar.
'====================================================================

Private WithEvents lstPecas As MSForms.ListBox
Private WithEvents chkSoVermelhas As MSForms.CheckBox
Private WithEvents btnAdicionar As MSForms.CommandButton
Private WithEvents lstConjunto As MSForms.ListBox
Private WithEvents btnTirar As MSForms.CommandButton
Private WithEvents btnMais As MSForms.CommandButton
Private WithEvents btnMenos As MSForms.CommandButton
Private WithEvents chkCncInicio As MSForms.CheckBox
Private WithEvents chkCncFim As MSForms.CheckBox
Private WithEvents cmbComp As MSForms.ComboBox
Private WithEvents cmbLarg As MSForms.ComboBox
Private WithEvents chkRaio As MSForms.CheckBox
Private WithEvents btnGravar As MSForms.CommandButton
Private WithEvents btnLimpar As MSForms.CommandButton
Private WithEvents btnVerificar As MSForms.CommandButton
Private WithEvents btnFechar As MSForms.CommandButton
Private txtQt As MSForms.TextBox
Private lblCodigo As MSForms.Label
Private lblEsp As MSForms.Label
Private lblEstado As MSForms.Label

Private mConj As Object          ' ID (texto) -> quantidade, pela ordem em que entram
Private mCodigoAntigo As String  ' código da linha de onde o menu abriu (para editar)
Private mLo As ListObject
Private cId As Long, cDesc As Long, cMat As Long, cComp As Long, cLarg As Long
Private cQt As Long, cEsp As Long, cEspMat As Long, cEspFinal As Long, cColar As Long
Private mAPreparar As Boolean

'====================================================================
'  ABRIR
'====================================================================
Private Sub UserForm_Initialize()
    mAPreparar = True
    Me.Caption = "Colar - peças a colar (ensaio)"
    Me.Width = 760
    Me.Height = 572
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

Private Sub CriarControlos()
    Rotulo "lblAjuda", "Escolha as peças que se colam (linhas da LISTAGEM_CUT_RITE, pelo ID), o que passa " & _
        "na CNC e a orla depois da colagem. «Gravar» escreve o código na coluna Colar de todas as peças " & _
        "do conjunto. Preencha a Colar no fim: se inserir ou apagar linhas, os IDs mudam.", 8, 6, 736, 28

    Rotulo "lbl1", "1. Peças da listagem   (ID | Descrição | Material | Comp x Larg | Qt | Esp.Mat | Esp | Colar)", _
        8, 40, 470, 14, True
    Set chkSoVermelhas = Novo("Forms.CheckBox.1", "chkSoVermelhas", 486, 38, 258, 16, _
        "Mostrar só as linhas com o Material a vermelho: a espessura do material é diferente da Esp do iMos.")
    chkSoVermelhas.Caption = "Só as linhas a vermelho (espessura diferente)"

    Set lstPecas = Novo("Forms.ListBox.1", "lstPecas", 8, 56, 736, 146, _
        "Selecione uma ou mais peças (Ctrl/Shift para várias) e carregue em «Juntar ao conjunto», " & _
        "ou faça duplo clique numa peça.")
    lstPecas.ColumnCount = 8
    lstPecas.ColumnWidths = "28;150;206;84;26;42;30;160"
    lstPecas.MultiSelect = fmMultiSelectExtended

    Rotulo "lblQt", "Quantas de cada:", 8, 212, 80, 14
    Set txtQt = Novo("Forms.TextBox.1", "txtQt", 88, 209, 34, 18, _
        "Quantas peças de cada linha escolhida entram no conjunto (ex.: 2 para duas peças iguais).")
    txtQt.Text = "1"
    Set btnAdicionar = Novo("Forms.CommandButton.1", "btnAdicionar", 130, 207, 170, 22, _
        "Juntar as peças selecionadas ao conjunto, com a quantidade ao lado.")
    btnAdicionar.Caption = "Juntar ao conjunto"

    Rotulo "lbl2", "2. Conjunto a colar   (ID | Qt | Descrição | Esp.Mat | Esp)", 8, 238, 460, 14, True
    Set lstConjunto = Novo("Forms.ListBox.1", "lstConjunto", 8, 254, 460, 108, _
        "As peças do conjunto. Selecione uma para lhe mudar a quantidade ou a tirar.")
    lstConjunto.ColumnCount = 5
    lstConjunto.ColumnWidths = "30;28;270;60;40"
    Set btnMais = Novo("Forms.CommandButton.1", "btnMais", 476, 254, 40, 22, _
        "Mais uma peça do ID selecionado no conjunto.")
    btnMais.Caption = "+1"
    Set btnMenos = Novo("Forms.CommandButton.1", "btnMenos", 520, 254, 40, 22, _
        "Menos uma peça do ID selecionado (a 0 sai do conjunto).")
    btnMenos.Caption = "-1"
    Set btnTirar = Novo("Forms.CommandButton.1", "btnTirar", 564, 254, 120, 22, _
        "Tirar do conjunto a peça selecionada.")
    btnTirar.Caption = "Tirar do conjunto"
    Set lblEsp = Rotulo("lblEsp", "", 476, 282, 268, 80)

    Rotulo "lbl3", "3. CNC", 8, 370, 120, 14, True
    Set chkCncInicio = Novo("Forms.CheckBox.1", "chkCncInicio", 8, 386, 260, 16, _
        "As peças passam na CNC ANTES de serem coladas (o código começa por CNC_).")
    chkCncInicio.Caption = "CNC antes da colagem (CNC no início)"
    Set chkCncFim = Novo("Forms.CheckBox.1", "chkCncFim", 8, 404, 260, 16, _
        "O conjunto já colado passa na CNC no FIM (o código acaba em _CNC).")
    chkCncFim.Caption = "CNC depois da colagem (CNC no fim)"

    Rotulo "lbl4", "4. Orlar depois da colagem", 280, 370, 300, 14, True
    Set cmbComp = Novo("Forms.ComboBox.1", "cmbComp", 280, 386, 150, 18, _
        "Orla nos comprimentos do conjunto já colado: OC1 = 1 comprimento, OC2 = 2 comprimentos.")
    cmbComp.Style = fmStyleDropDownList
    cmbComp.AddItem "Sem orla nos comprimentos"
    cmbComp.AddItem "1 comprimento (OC1)"
    cmbComp.AddItem "2 comprimentos (OC2)"
    cmbComp.ListIndex = 0
    Set cmbLarg = Novo("Forms.ComboBox.1", "cmbLarg", 440, 386, 150, 18, _
        "Orla nas larguras do conjunto já colado: OL1 = 1 largura, OL2 = 2 larguras. " & _
        "2 comprimentos + 2 larguras = O4L (4 lados).")
    cmbLarg.Style = fmStyleDropDownList
    cmbLarg.AddItem "Sem orla nas larguras"
    cmbLarg.AddItem "1 largura (OL1)"
    cmbLarg.AddItem "2 larguras (OL2)"
    cmbLarg.ListIndex = 0
    Set chkRaio = Novo("Forms.CheckBox.1", "chkRaio", 600, 387, 144, 16, _
        "Orlar o raio / meia-lua depois da colagem (OR).")
    chkRaio.Caption = "Raio / meia-lua (OR)"
    Rotulo "lblNotaOrla", "A orla que a peça já leva antes de colar continua nas colunas Orla da própria peça.", _
        280, 408, 464, 14

    Set lblCodigo = Rotulo("lblCodigo", "", 8, 430, 736, 24, True)
    lblCodigo.Font.Size = 14

    Set btnGravar = Novo("Forms.CommandButton.1", "btnGravar", 8, 462, 210, 26, _
        "Escrever este código na coluna Colar de todas as peças do conjunto.")
    btnGravar.Caption = "Gravar nas peças do conjunto"
    Set btnLimpar = Novo("Forms.CommandButton.1", "btnLimpar", 226, 462, 200, 26, _
        "Apagar o código da coluna Colar das peças deste conjunto.")
    btnLimpar.Caption = "Tirar o código destas peças"
    Set btnVerificar = Novo("Forms.CommandButton.1", "btnVerificar", 434, 462, 190, 26, _
        "Conferir os códigos de toda a listagem (IDs que não existem, conjuntos desencontrados).")
    btnVerificar.Caption = "Verificar toda a listagem"
    Set btnFechar = Novo("Forms.CommandButton.1", "btnFechar", 644, 462, 100, 26, "Fechar o menu.")
    btnFechar.Caption = "Fechar"

    ' Linha de estado ("supervisor") por baixo dos botões
    Set lblEstado = Rotulo("lblEstado", "", 8, 496, 736, 40)
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

Private Sub PreencherPecas()
    Dim r As Long, i As Long
    lstPecas.Clear
    If mLo Is Nothing Then Exit Sub
    If mLo.DataBodyRange Is Nothing Then Exit Sub
    For r = 1 To mLo.ListRows.Count
        If Len(Celula(r, cDesc)) > 0 Or Len(Celula(r, cMat)) > 0 Then
            If (Not chkSoVermelhas.Value) Or EspDiferente(r) Then
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
            cmbComp.ListIndex = nc
            cmbLarg.ListIndex = nl
            chkRaio.Value = ra
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
'  CONJUNTO E CÓDIGO
'====================================================================
Private Function CodigoAtual() As String
    CodigoAtual = ColarMontar(chkCncInicio.Value, mConj, _
        ColarOrlasTexto(cmbComp.ListIndex, cmbLarg.ListIndex, chkRaio.Value), chkCncFim.Value)
End Function

Private Function Numero(ByVal s As String) As Double
    s = Replace(Trim$(s), ",", ".")
    If Len(s) = 0 Then
        Numero = -1
    Else
        Numero = Val(s)
    End If
End Function

Private Sub Atualizar()
    Dim k As Variant, r As Long, i As Long, q As Long
    Dim soma As Double, partes As String, alvos As String, espTxt As String, cod As String
    Dim semEsp As Boolean
    If mAPreparar Then Exit Sub

    lstConjunto.Clear
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
            If Len(Celula(r, cEsp)) > 0 And InStr(" " & alvos & " ", " " & Celula(r, cEsp) & " ") = 0 Then
                alvos = Trim$(alvos & " " & Celula(r, cEsp))
            End If
        Else
            lstConjunto.List(i, 2) = "(este ID não existe na listagem)"
        End If
    Next k

    If mConj.Count = 0 Then
        lblEsp.Caption = ""
    ElseIf semEsp Then
        lblEsp.Caption = "Espessuras do conjunto: " & partes & " (há peças sem Esp.Mat)." & vbLf & _
                         "Esp no iMos: " & alvos
    Else
        lblEsp.Caption = "Espessuras do conjunto, uma em cima da outra: " & partes & " = " & soma & " mm" & vbLf & _
                         "Esp no iMos: " & alvos & " mm" & vbLf & _
                         "(só para conferir: nem todas as colagens são empilhadas)"
    End If

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

'====================================================================
'  EVENTOS
'====================================================================
Private Sub chkSoVermelhas_Click()
    If mAPreparar Then Exit Sub
    PreencherPecas
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

Private Sub cmbComp_Change()
    Atualizar
End Sub

Private Sub cmbLarg_Change()
    Atualizar
End Sub

Private Sub chkRaio_Click()
    Atualizar
End Sub

Private Sub btnGravar_Click()
    Dim cod As String, msg As String
    If ColarTotalPecas(mConj) < 2 Then
        Estado "O conjunto precisa de pelo menos 2 peças."
        Exit Sub
    End If
    cod = CodigoAtual()
    msg = ColarGravar(mConj, cod, mCodigoAntigo, True)
    If Len(msg) = 0 Then
        Estado "Nada foi gravado."
        Exit Sub
    End If
    ' Pronto para o conjunto seguinte.
    Set mConj = CreateObject("Scripting.Dictionary")
    mCodigoAntigo = ""
    chkCncInicio.Value = False
    chkCncFim.Value = False
    cmbComp.ListIndex = 0
    cmbLarg.ListIndex = 0
    chkRaio.Value = False
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
    If MsgBox("Apagar o código da coluna Colar das peças deste conjunto?", _
              vbYesNo + vbQuestion + vbDefaultButton2, "Colar") <> vbYes Then Exit Sub
    n = ColarLimpar(mConj, mCodigoAntigo)
    mCodigoAntigo = ""
    PreencherPecas
    Atualizar
    Estado "Código tirado de " & n & " linha(s)."
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
