Attribute VB_Name = "modColar"
Option Explicit

'====================================================================
'  LANÇA ENCANTO - COLUNA "Colar" DA LISTAGEM_CUT_RITE   (ENSAIO 06-11-2026)
'--------------------------------------------------------------------
'  Só no modelo Lista_Material_IMOS_MARTELO_COLAR.xltm (o de sempre fica igual).
'  A coluna "Colar" fica logo a seguir à CNC_2 e vai para o Cut-Rite nesse sítio.
'
'  Código (guia PROCESSO_ESPECIAL):  [CNC_]conjunto[_orlas][_CNC]
'    - CNC no início = passa na CNC antes da colagem; CNC no fim = depois.
'    - conjunto = os IDs da coluna ID juntos com "+"; 21x2 = duas peças do ID 21;
'      duas peças do mesmo ID sozinhas escrevem-se 14+14.
'    - orlas depois da colagem = O4L | OC2 | OC1 | OL2 | OL1 | OR, juntas com "+";
'      2 comprimentos + 2 larguras escrevem-se O4L.
'  Exemplos: CNC_20+21x2+22x2_OC2+OL2_CNC   14+14_O4L_CNC   14+16_OC2+OR
'  As peças do mesmo conjunto levam todas o mesmo código.
'
'  As mesmas regras estão no Martelo V3 (app/domain/codigo_colar.py), que confere
'  os códigos antes de enviar para o Cut-Rite. Se mudarem aqui, mudam lá.
'
'  Macros:
'    AbrirMenuColar        - botão "Colar" e duplo clique na coluna Colar
'    VerificarCodigosColar - confere os códigos de toda a listagem
'
'  Cuidado: a coluna ID renumera-se sozinha quando se insere ou apaga uma linha;
'  o código é texto e fica com os IDs antigos. Preencher a Colar no fim e,
'  se mexer nas linhas depois, verificar (o «Copia Listagem» verifica sozinho).
'====================================================================

Public Const COLAR_FOLHA As String = "LISTAGEM_CUT_RITE"
Public Const COLAR_TABELA As String = "Tabela_Cut_Rite"

'====================================================================
'  MACROS DOS BOTÕES
'====================================================================
Public Sub AbrirMenuColar()
    On Error GoTo EH
    If ColarTabela() Is Nothing Then
        MsgBox "Não encontrei a tabela " & COLAR_TABELA & " na folha " & COLAR_FOLHA & ".", _
               vbExclamation, "Colar"
        Exit Sub
    End If
    If ColarIndice("COLAR") = 0 Then
        MsgBox "Esta Lista Material não tem a coluna Colar.", vbExclamation, "Colar"
        Exit Sub
    End If
    frmColar.Show
    Exit Sub
EH:
    MsgBox "Erro ao abrir o menu Colar: " & Err.Number & " - " & Err.Description, _
           vbExclamation, "Colar"
End Sub

Public Sub VerificarCodigosColar()
    Dim problemas As String
    problemas = ColarProblemas(15)
    If Len(problemas) = 0 Then
        MsgBox "Coluna Colar: os códigos estão certos.", vbInformation, "Colar"
    Else
        MsgBox "Coluna Colar - a corrigir:" & vbCrLf & vbCrLf & problemas, vbExclamation, "Colar"
    End If
End Sub

'====================================================================
'  TABELA E COLUNAS (pelo nome, como o resto das macros)
'====================================================================
Public Function ColarTabela() As ListObject
    On Error Resume Next
    Set ColarTabela = ThisWorkbook.Worksheets(COLAR_FOLHA).ListObjects(COLAR_TABELA)
End Function

' Maiúsculas, só letras e algarismos, sem acentos ("Esp.Mat" -> "ESPMAT").
Public Function ColarNormalizar(ByVal s As String) As String
    Dim i As Long, ch As String, saida As String
    s = UCase$(s)
    For i = 1 To Len(s)
        ch = Mid$(s, i, 1)
        Select Case ch
            Case "Á", "À", "Â", "Ã": ch = "A"
            Case "É", "Ê": ch = "E"
            Case "Í": ch = "I"
            Case "Ó", "Ô", "Õ": ch = "O"
            Case "Ú": ch = "U"
            Case "Ç": ch = "C"
        End Select
        If (ch >= "A" And ch <= "Z") Or (ch >= "0" And ch <= "9") Then saida = saida & ch
    Next i
    ColarNormalizar = saida
End Function

' Índice (1..n) da 1.ª coluna da tabela com este nome normalizado; 0 = não há.
' "COMP" e "LARG" dão a Comp e a Larg (o +comp e o +Larg vêm depois).
Public Function ColarIndice(ByVal nomeNormalizado As String) As Long
    Dim lo As ListObject, i As Long
    Set lo = ColarTabela()
    If lo Is Nothing Then Exit Function
    For i = 1 To lo.ListColumns.Count
        If ColarNormalizar(CStr(lo.ListColumns(i).Name)) = nomeNormalizado Then
            ColarIndice = i
            Exit Function
        End If
    Next i
End Function

' O ID de uma linha da tabela, como texto ("14"); vazio se não for um número.
Public Function ColarIdDaLinha(ByVal lo As ListObject, ByVal linha As Long, ByVal colId As Long) As String
    Dim v As Variant
    On Error GoTo Fim
    v = lo.DataBodyRange.Cells(linha, colId).Value
    If IsEmpty(v) Or IsError(v) Then Exit Function
    If Not IsNumeric(v) Then Exit Function
    ColarIdDaLinha = CStr(CLng(v))
Fim:
End Function

' Índice da coluna "+comp" ou "+Larg" (nomeNormalizado = "COMP" ou "LARG"): a que
' começa por "+", para não a confundir com a Comp e a Larg da peça.
Public Function ColarIndiceMais(ByVal nomeNormalizado As String) As Long
    Dim lo As ListObject, i As Long, nome As String
    Set lo = ColarTabela()
    If lo Is Nothing Then Exit Function
    For i = 1 To lo.ListColumns.Count
        nome = Trim$(Replace(Replace(CStr(lo.ListColumns(i).Name), vbLf, ""), vbCr, ""))
        If Left$(nome, 1) = "+" And ColarNormalizar(nome) = nomeNormalizado Then
            ColarIndiceMais = i
            Exit Function
        End If
    Next i
End Function

' Linha da tabela (1..n) com este ID; 0 = não existe.
Public Function ColarLinhaDoId(ByVal ident As String) As Long
    Dim lo As ListObject, colId As Long, r As Long
    Set lo = ColarTabela()
    If lo Is Nothing Then Exit Function
    If lo.DataBodyRange Is Nothing Then Exit Function
    colId = ColarIndice("ID")
    If colId = 0 Then Exit Function
    For r = 1 To lo.ListRows.Count
        If ColarIdDaLinha(lo, r, colId) = ident Then
            ColarLinhaDoId = r
            Exit Function
        End If
    Next r
End Function

' A célula é da coluna Colar (para o duplo clique da folha).
Public Function ColarCelulaDaColuna(ByVal Target As Range) As Boolean
    Dim lo As ListObject, c As Long
    On Error GoTo Fim
    If Target.Cells.Count <> 1 Then Exit Function
    Set lo = ColarTabela()
    If lo Is Nothing Then Exit Function
    If lo.DataBodyRange Is Nothing Then Exit Function
    c = ColarIndice("COLAR")
    If c = 0 Then Exit Function
    ColarCelulaDaColuna = Not (Intersect(Target, lo.ListColumns(c).DataBodyRange) Is Nothing)
Fim:
End Function

'====================================================================
'  ESCREVER O CÓDIGO
'====================================================================
' conj = Scripting.Dictionary  ID (texto) -> quantidade, pela ordem em que entraram.
Public Function ColarConjuntoTexto(ByVal conj As Object) As String
    Dim k As Variant, partes As String, q As Long
    If conj Is Nothing Then Exit Function
    If conj.Count = 1 Then
        k = conj.Keys()(0)
        If CLng(conj(k)) = 2 Then
            ColarConjuntoTexto = k & "+" & k
            Exit Function
        End If
    End If
    For Each k In conj.Keys
        q = CLng(conj(k))
        If q > 0 Then
            If Len(partes) > 0 Then partes = partes & "+"
            If q = 1 Then
                partes = partes & k
            Else
                partes = partes & k & "x" & q
            End If
        End If
    Next k
    ColarConjuntoTexto = partes
End Function

' nComp / nLarg = 0, 1 ou 2 lados com orla depois da colagem.
Public Function ColarOrlasTexto(ByVal nComp As Long, ByVal nLarg As Long, ByVal raio As Boolean) As String
    Dim s As String
    If nComp = 2 And nLarg = 2 Then
        s = "O4L"
    Else
        If nComp = 1 Or nComp = 2 Then s = "OC" & nComp
        If nLarg = 1 Or nLarg = 2 Then
            If Len(s) > 0 Then s = s & "+"
            s = s & "OL" & nLarg
        End If
    End If
    If raio Then
        If Len(s) > 0 Then s = s & "+"
        s = s & "OR"
    End If
    ColarOrlasTexto = s
End Function

Public Function ColarMontar(ByVal cncInicio As Boolean, ByVal conj As Object, _
                            ByVal orlas As String, ByVal cncFim As Boolean) As String
    Dim c As String
    c = ColarConjuntoTexto(conj)
    If Len(c) = 0 Then Exit Function
    If cncInicio Then c = "CNC_" & c
    If Len(orlas) > 0 Then c = c & "_" & orlas
    If cncFim Then c = c & "_CNC"
    ColarMontar = c
End Function

Public Function ColarTotalPecas(ByVal conj As Object) As Long
    Dim k As Variant
    If conj Is Nothing Then Exit Function
    For Each k In conj.Keys
        ColarTotalPecas = ColarTotalPecas + CLng(conj(k))
    Next k
End Function

'====================================================================
'  LER O CÓDIGO
'====================================================================
Private Function SoAlgarismos(ByVal s As String) As Boolean
    Dim i As Long
    If Len(s) = 0 Or Len(s) > 6 Then Exit Function
    For i = 1 To Len(s)
        If Mid$(s, i, 1) < "0" Or Mid$(s, i, 1) > "9" Then Exit Function
    Next i
    SoAlgarismos = True
End Function

' Lê um código. Devolve "" quando está certo; senão, o motivo (em minúsculas,
' para seguir a "o código «...» ").
Public Function ColarLer(ByVal codigo As String, ByRef conj As Object, _
                         ByRef cncInicio As Boolean, ByRef cncFim As Boolean, _
                         ByRef nComp As Long, ByRef nLarg As Long, ByRef raio As Boolean) As String
    Dim blocos() As String, partes() As String
    Dim ini As Long, fim As Long, n As Long, i As Long
    Dim p As String, idTxt As String, qtTxt As String, posX As Long, q As Long, total As Long
    Dim orla As String, vistas As String, tem4L As Boolean, nOC As Long, nOL As Long

    Set conj = CreateObject("Scripting.Dictionary")
    cncInicio = False: cncFim = False: nComp = 0: nLarg = 0: raio = False
    codigo = Trim$(codigo)
    If Len(codigo) = 0 Then
        ColarLer = "está vazio"
        Exit Function
    End If
    If InStr(codigo, " ") > 0 Or InStr(codigo, vbTab) > 0 Or InStr(codigo, vbLf) > 0 Or InStr(codigo, vbCr) > 0 Then
        ColarLer = "tem espaços (o código escreve-se sem espaços)"
        Exit Function
    End If
    blocos = Split(codigo, "_")
    ini = LBound(blocos)
    fim = UBound(blocos)
    For i = ini To fim
        If Len(blocos(i)) = 0 Then
            ColarLer = "tem um bloco vazio (dois «_» seguidos ou «_» na ponta)"
            Exit Function
        End If
    Next i
    If UCase$(blocos(ini)) = "CNC" Then
        cncInicio = True
        ini = ini + 1
    End If
    If ini <= fim Then
        If UCase$(blocos(fim)) = "CNC" Then
            cncFim = True
            fim = fim - 1
        End If
    End If
    n = fim - ini + 1
    If n < 1 Then
        ColarLer = "não tem o conjunto de peças (os IDs)"
        Exit Function
    End If
    If n > 2 Then
        ColarLer = "tem blocos a mais: [CNC_]conjunto[_orlas][_CNC]"
        Exit Function
    End If

    ' Conjunto
    partes = Split(blocos(ini), "+")
    For i = LBound(partes) To UBound(partes)
        p = UCase$(partes(i))
        posX = InStr(p, "X")
        If posX > 0 Then
            idTxt = Left$(p, posX - 1)
            qtTxt = Mid$(p, posX + 1)
        Else
            idTxt = p
            qtTxt = "1"
        End If
        If Not SoAlgarismos(idTxt) Or Not SoAlgarismos(qtTxt) Then
            ColarLer = "tem «" & partes(i) & "», que não é um ID (ex.: 14 ou 21x2)"
            Exit Function
        End If
        q = CLng(qtTxt)
        If q < 1 Then
            ColarLer = "tem «" & partes(i) & "»: a quantidade tem de ser 1 ou mais"
            Exit Function
        End If
        idTxt = CStr(CLng(idTxt))
        If conj.Exists(idTxt) Then
            conj(idTxt) = CLng(conj(idTxt)) + q
        Else
            conj.Add idTxt, q
        End If
        total = total + q
    Next i
    If total < 2 Then
        ColarLer = "tem uma só peça: um conjunto para colar tem de ter pelo menos 2"
        Exit Function
    End If

    ' Orlas depois da colagem
    If n = 2 Then
        partes = Split(blocos(fim), "+")
        For i = LBound(partes) To UBound(partes)
            orla = UCase$(partes(i))
            If InStr("|" & vistas & "|", "|" & orla & "|") > 0 Then
                ColarLer = "tem a orla " & orla & " repetida"
                Exit Function
            End If
            vistas = vistas & "|" & orla
            Select Case orla
                Case "O4L": tem4L = True
                Case "OC2": nComp = 2: nOC = nOC + 1
                Case "OC1": nComp = 1: nOC = nOC + 1
                Case "OL2": nLarg = 2: nOL = nOL + 1
                Case "OL1": nLarg = 1: nOL = nOL + 1
                Case "OR": raio = True
                Case Else
                    ColarLer = "tem «" & partes(i) & "», que não é uma orla (O4L, OC2, OC1, OL2, OL1, OR)"
                    Exit Function
            End Select
        Next i
        If tem4L And (nOC > 0 Or nOL > 0) Then
            ColarLer = "junta O4L com OC/OL: O4L já são os 4 lados"
            Exit Function
        End If
        If nOC > 1 Or nOL > 1 Then
            ColarLer = "tem mais de um OC ou de um OL (só 1 ou 2 comprimentos e 1 ou 2 larguras)"
            Exit Function
        End If
        If tem4L Then
            nComp = 2
            nLarg = 2
        End If
    End If
End Function

'====================================================================
'  GRAVAR / TIRAR NA TABELA
'====================================================================
' Escreve o código em todas as linhas do conjunto e tira-o das linhas que tinham
' o código antigo e já não são do conjunto. Devolve o texto para a linha de estado,
' ou "" quando não gravou (IDs em falta ou o utilizador disse que não).
'   mudarQt  : a Qt de cada peça passa a ser peças dela no conjunto x conjuntos
'              (47+47 e 8 conjuntos -> Qt 16; 47+48 e 6 -> Qt 6 e 6): é o que o
'              Cut-Rite tem de cortar para, depois de colar, haver os conjuntos pedidos.
'   maisComp / maisLarg : excedente de corte para as colunas +comp e +Larg (por
'              defeito 20 no menu); vazio = não mexe nessas colunas.
Public Function ColarGravar(ByVal conj As Object, ByVal codigo As String, _
                            ByVal codigoAntigo As String, _
                            Optional ByVal perguntar As Boolean = True, _
                            Optional ByVal mudarQt As Boolean = False, _
                            Optional ByVal maisComp As String = "", _
                            Optional ByVal maisLarg As String = "", _
                            Optional ByVal conjuntos As Long = 1) As String
    Dim lo As ListObject, colId As Long, colColar As Long, r As Long
    Dim colQt As Long, colMaisComp As Long, colMaisLarg As Long
    Dim idTxt As String, atual As String, k As Variant
    Dim faltam As String, conflitos As String, escritos As String, qts As String
    Dim n As Long, tirados As Long

    Set lo = ColarTabela()
    If lo Is Nothing Then Exit Function
    If lo.DataBodyRange Is Nothing Then Exit Function
    colId = ColarIndice("ID")
    colColar = ColarIndice("COLAR")
    If colId = 0 Or colColar = 0 Then Exit Function
    If Len(codigo) = 0 Then Exit Function
    colQt = ColarIndice("QT")
    colMaisComp = ColarIndiceMais("COMP")
    colMaisLarg = ColarIndiceMais("LARG")

    For Each k In conj.Keys
        If ColarLinhaDoId(CStr(k)) = 0 Then faltam = faltam & " " & k
    Next k
    If Len(faltam) > 0 Then
        MsgBox "Estes IDs não existem na listagem:" & faltam, vbExclamation, "Colar"
        Exit Function
    End If

    For r = 1 To lo.ListRows.Count
        idTxt = ColarIdDaLinha(lo, r, colId)
        If Len(idTxt) > 0 Then
            If conj.Exists(idTxt) Then
                atual = Trim$(CStr(lo.DataBodyRange.Cells(r, colColar).Value))
                If Len(atual) > 0 And atual <> codigo And atual <> codigoAntigo Then
                    conflitos = conflitos & vbCrLf & "   ID " & idTxt & ": " & atual
                End If
            End If
        End If
    Next r
    If Len(conflitos) > 0 And perguntar Then
        If MsgBox("Estas peças já têm outro código na coluna Colar:" & conflitos & vbCrLf & vbCrLf & _
                  "Substituir pelo código novo «" & codigo & "»?" & vbCrLf & _
                  "(o outro conjunto fica com peças a menos: veja a verificação)", _
                  vbYesNo + vbQuestion + vbDefaultButton2, "Colar") <> vbYes Then
            Exit Function
        End If
    End If

    For r = 1 To lo.ListRows.Count
        idTxt = ColarIdDaLinha(lo, r, colId)
        atual = Trim$(CStr(lo.DataBodyRange.Cells(r, colColar).Value))
        If Len(idTxt) > 0 And conj.Exists(idTxt) Then
            With lo.DataBodyRange.Cells(r, colColar)
                .NumberFormat = "@"
                .Value = codigo
            End With
            If mudarQt And colQt > 0 Then
                If conjuntos < 1 Then conjuntos = 1
                lo.DataBodyRange.Cells(r, colQt).Value = CLng(conj(idTxt)) * conjuntos
                qts = qts & IIf(Len(qts) > 0, ", ", "") & "ID " & idTxt & " = " & CLng(conj(idTxt)) * conjuntos
            End If
            If Len(Trim$(maisComp)) > 0 And colMaisComp > 0 Then
                lo.DataBodyRange.Cells(r, colMaisComp).Value = Val(Replace(maisComp, ",", "."))
            End If
            If Len(Trim$(maisLarg)) > 0 And colMaisLarg > 0 Then
                lo.DataBodyRange.Cells(r, colMaisLarg).Value = Val(Replace(maisLarg, ",", "."))
            End If
            n = n + 1
            If Len(escritos) > 0 Then escritos = escritos & ", "
            escritos = escritos & idTxt
        ElseIf Len(codigoAntigo) > 0 And atual = codigoAntigo Then
            lo.DataBodyRange.Cells(r, colColar).ClearContents
            tirados = tirados + 1
        End If
    Next r

    ColarGravar = "Código «" & codigo & "» gravado em " & n & " linha(s): ID " & escritos & "."
    If Len(qts) > 0 Then ColarGravar = ColarGravar & " Qt (" & conjuntos & " conjunto(s)): " & qts & "."
    If Len(Trim$(maisComp)) > 0 Or Len(Trim$(maisLarg)) > 0 Then
        ColarGravar = ColarGravar & " +comp " & maisComp & " / +Larg " & maisLarg & "."
    End If
    If tirados > 0 Then
        ColarGravar = ColarGravar & " Tirado de " & tirados & " linha(s) que já não são do conjunto."
    End If
End Function

' Tira o código das linhas do conjunto e das que tinham o código antigo.
Public Function ColarLimpar(ByVal conj As Object, ByVal codigoAntigo As String) As Long
    Dim lo As ListObject, colId As Long, colColar As Long, r As Long
    Dim idTxt As String, atual As String
    Set lo = ColarTabela()
    If lo Is Nothing Then Exit Function
    If lo.DataBodyRange Is Nothing Then Exit Function
    colId = ColarIndice("ID")
    colColar = ColarIndice("COLAR")
    If colId = 0 Or colColar = 0 Then Exit Function
    For r = 1 To lo.ListRows.Count
        idTxt = ColarIdDaLinha(lo, r, colId)
        atual = Trim$(CStr(lo.DataBodyRange.Cells(r, colColar).Value))
        If Len(atual) > 0 Then
            If (Len(idTxt) > 0 And conj.Exists(idTxt)) Or (Len(codigoAntigo) > 0 And atual = codigoAntigo) Then
                lo.DataBodyRange.Cells(r, colColar).ClearContents
                ColarLimpar = ColarLimpar + 1
            End If
        End If
    Next r
End Function

'====================================================================
'  VERIFICAR A LISTAGEM
'====================================================================
Private Sub JuntarProblema(ByVal lista As Collection, ByVal texto As String)
    Dim i As Long
    For i = 1 To lista.Count
        If lista(i) = texto Then Exit Sub
    Next i
    lista.Add texto
End Sub

' Os problemas da coluna Colar, um por linha ("" = tudo certo). Apanha códigos mal
' escritos, IDs que não existem e conjuntos desencontrados (numeração mudada).
Public Function ColarProblemas(Optional ByVal maximo As Long = 15) As String
    Dim lo As ListObject, colId As Long, colColar As Long, r As Long
    Dim porId As Object, lista As Collection
    Dim k As Variant, outro As Variant, cod As String, motivo As String, idTxt As String
    Dim conj As Object, ci As Boolean, cf As Boolean, nc As Long, nl As Long, ra As Boolean
    Dim i As Long, texto As String, doOutro As String

    Set lo = ColarTabela()
    If lo Is Nothing Then Exit Function
    If lo.DataBodyRange Is Nothing Then Exit Function
    colId = ColarIndice("ID")
    colColar = ColarIndice("COLAR")
    If colId = 0 Or colColar = 0 Then Exit Function

    Set porId = CreateObject("Scripting.Dictionary")
    For r = 1 To lo.ListRows.Count
        idTxt = ColarIdDaLinha(lo, r, colId)
        If Len(idTxt) > 0 Then porId(idTxt) = Trim$(CStr(lo.DataBodyRange.Cells(r, colColar).Value))
    Next r

    Set lista = New Collection
    For Each k In porId.Keys
        cod = porId(k)
        If Len(cod) > 0 Then
            motivo = ColarLer(cod, conj, ci, cf, nc, nl, ra)
            If Len(motivo) > 0 Then
                JuntarProblema lista, "ID " & k & ": o código «" & cod & "» " & motivo & "."
            Else
                If Not conj.Exists(CStr(k)) Then
                    JuntarProblema lista, "ID " & k & ": o código «" & cod & "» não inclui o ID " & k & _
                        " (a numeração mudou depois de o código ser escrito?)."
                End If
                For Each outro In conj.Keys
                    If Not porId.Exists(CStr(outro)) Then
                        JuntarProblema lista, "«" & cod & "»: o ID " & outro & " não existe na listagem."
                    ElseIf porId(CStr(outro)) <> cod Then
                        doOutro = porId(CStr(outro))
                        If Len(doOutro) = 0 Then doOutro = "vazio"
                        JuntarProblema lista, "«" & cod & "»: a linha ID " & outro & " tem outro código (" & _
                            doOutro & "); o conjunto leva o mesmo código em todas as peças."
                    End If
                Next outro
            End If
        End If
    Next k

    For i = 1 To lista.Count
        If i > maximo Then
            texto = texto & "... e mais " & (lista.Count - maximo) & "." & vbCrLf
            Exit For
        End If
        texto = texto & "- " & lista(i) & vbCrLf
    Next i
    ColarProblemas = texto
End Function
