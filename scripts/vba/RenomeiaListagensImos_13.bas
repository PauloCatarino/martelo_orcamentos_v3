Attribute VB_Name = "RenomeiaListagensImos_13"
Option Explicit

' Fluxo unificado IMOS -> pasta da obra -> separadores Excel.
' Mantem a macro antiga como ponto de entrada por compatibilidade.

Private Const IMOS14_PASTA_ORIGEM As String = "C:\IMOS_Output_Batches\"
Private Const IMOS14_FERRAGENS As String = "2_List_Ferragens"
Private Const IMOS14_RESUMO As String = "3_Resumo_Precos"
Private Const IMOS14_ETIQUETA As String = "4_Etiqueta_Palete"
Private Const IMOS14_INTEGRADOR As String = "5_List_Ferragens_Integrador"
' Onde ficam as listagens substituidas (dentro da pasta da obra). O Martelo
' usa a mesma pasta quando gera as listagens sem o IMOS.
Private Const IMOS14_PASTA_ANTERIORES As String = "Listas_IMOS_anteriores"

Public Function IMOS14_Versao() As String
    IMOS14_Versao = "2026-09-29"
End Function

Public Sub RenomeiaNomesListaImosCopiaParaPstaObra_13()
    ImportarListasFerragensIMOS_14
End Sub

Public Sub ImportarListasFerragensIMOS_14()
    Dim fso As Object
    Dim pastaDestino As String
    Dim prefixoObra As String
    Dim movidos As String
    Dim substituidos As String
    Dim existentes As String
    Dim erros As String
    Dim emFalta As String
    Dim ficheiroFerragens As String
    Dim ficheiroResumo As String
    Dim ficheiroEtiqueta As String
    Dim ficheiroIntegrador As String
    Dim separadoresExistentes As String
    Dim aImportar As String
    Dim avisoFalta As String
    Dim resposta As VbMsgBoxResult
    Dim estadoAnterior As Variant
    Dim alertasAnteriores As Boolean

    On Error GoTo TrataErro

    estadoAnterior = Application.StatusBar
    alertasAnteriores = Application.DisplayAlerts
    Set fso = CreateObject("Scripting.FileSystemObject")

    Application.StatusBar = "[1/6] A validar a obra e as pastas..."
    DoEvents

    If Len(ThisWorkbook.Path) = 0 Then
        MsgBox "O ficheiro Excel ainda nao foi guardado. Guarda-o primeiro na pasta da obra.", _
               vbExclamation, "Importar listas IMOS"
        GoTo Saida
    End If

    pastaDestino = ThisWorkbook.Path & "\"
    If Not fso.FolderExists(IMOS14_PASTA_ORIGEM) Then
        MsgBox "A pasta de origem do IMOS nao existe:" & vbCrLf & _
               IMOS14_PASTA_ORIGEM, vbExclamation, "Importar listas IMOS"
        GoTo Saida
    End If

    prefixoObra = Trim$(IMOS14_LerPrefixoProcesso())
    If Len(prefixoObra) = 0 Then
        MsgBox "Nao consegui obter o Nome Enc IMOS IX (NOME_ENC_IMOS_IX)." & vbCrLf & _
               "Confirma o valor em DEFENICOES!E3.", vbExclamation, "Importar listas IMOS"
        GoTo Saida
    End If
    If Right$(prefixoObra, 1) <> "_" Then prefixoObra = prefixoObra & "_"

    Application.StatusBar = "[2/6] A trazer do IMOS as listagens mais recentes..."
    DoEvents

    IMOS14_MoverTipo prefixoObra, IMOS14_FERRAGENS, pastaDestino, movidos, substituidos, existentes, erros
    IMOS14_MoverTipo prefixoObra, IMOS14_RESUMO, pastaDestino, movidos, substituidos, existentes, erros
    IMOS14_MoverTipo prefixoObra, IMOS14_ETIQUETA, pastaDestino, movidos, substituidos, existentes, erros
    IMOS14_MoverTipo prefixoObra, IMOS14_INTEGRADOR, pastaDestino, movidos, substituidos, existentes, erros

    Application.StatusBar = "[3/6] A confirmar os ficheiros na pasta da obra..."
    DoEvents

    ficheiroFerragens = IMOS14_FicheiroMaisRecente(pastaDestino, IMOS14_FERRAGENS & "*.xls*")
    ficheiroResumo = IMOS14_FicheiroMaisRecente(pastaDestino, IMOS14_RESUMO & "*.xls*")
    ficheiroEtiqueta = IMOS14_FicheiroMaisRecente(pastaDestino, IMOS14_ETIQUETA & "*.xls*")
    ficheiroIntegrador = IMOS14_FicheiroMaisRecente(pastaDestino, IMOS14_INTEGRADOR & "*.xls*")

    If Len(ficheiroFerragens) = 0 Then emFalta = emFalta & vbCrLf & "- " & IMOS14_FERRAGENS & "*.xlsx"
    If Len(ficheiroResumo) = 0 Then emFalta = emFalta & vbCrLf & "- " & IMOS14_RESUMO & "*.xlsx"
    If Len(ficheiroEtiqueta) = 0 Then emFalta = emFalta & vbCrLf & "- " & IMOS14_ETIQUETA & "*.xlsx"
    If Len(ficheiroIntegrador) = 0 Then emFalta = emFalta & vbCrLf & "- " & IMOS14_INTEGRADOR & "*.xlsx"

    If Len(ficheiroFerragens) = 0 And Len(ficheiroResumo) = 0 And _
       Len(ficheiroEtiqueta) = 0 And Len(ficheiroIntegrador) = 0 Then
        MsgBox "Nao foram encontrados ficheiros desta obra, nem na pasta IMOS nem na pasta da obra." & _
               vbCrLf & vbCrLf & "Prefixo procurado: " & prefixoObra & vbCrLf & _
               "Origem: " & IMOS14_PASTA_ORIGEM & vbCrLf & _
               "Destino: " & pastaDestino & IMOS14_TextoMovimento(movidos, substituidos, existentes, erros), _
               vbExclamation, "Importar listas IMOS"
        GoTo Saida
    End If

    ' Antes exigiam-se os quatro ficheiros e a importacao parava a' primeira
    ' falta. Nem todas as obras geram os quatro no IMOS (ha' obras sem
    ' ferragens, sem etiqueta ou sem integrador), e por causa disso ficava tudo
    ' por importar. Agora importa-se o que existe e diz-se o que faltou.
    aImportar = ""
    If Len(ficheiroFerragens) > 0 Then
        aImportar = aImportar & vbCrLf & "- 2_List_Ferragens -> 1_FERRAGENS / 2_PURCH / 3_SPP" & _
                    IMOS14_DataFicheiro(ficheiroFerragens)
    End If
    If Len(ficheiroResumo) > 0 Then
        aImportar = aImportar & vbCrLf & "- 3_Resumo_Precos -> 4_Resumo_Global_Precos" & _
                    IMOS14_DataFicheiro(ficheiroResumo)
    End If
    If Len(ficheiroEtiqueta) > 0 Then
        aImportar = aImportar & vbCrLf & "- 4_Etiqueta_Palete -> 5_ETIQUETA_PALETE" & _
                    IMOS14_DataFicheiro(ficheiroEtiqueta)
    End If
    If Len(ficheiroIntegrador) > 0 Then
        aImportar = aImportar & vbCrLf & "- 5_List_Ferragens_Integrador -> 5_List_Ferragens_Integrador" & _
                    IMOS14_DataFicheiro(ficheiroIntegrador)
    End If

    avisoFalta = ""
    If Len(emFalta) > 0 Then
        avisoFalta = vbCrLf & vbCrLf & _
                     "Nao existem (nem do IMOS nem do Martelo), nao ha' nada a importar deles:" & emFalta
    End If

    resposta = MsgBox( _
        "Listagens prontas na pasta da obra (geradas no IMOS ou no Martelo)." & vbCrLf & vbCrLf & _
        "Vai importar:" & aImportar & _
        avisoFalta & vbCrLf & _
        IMOS14_TextoMovimento(movidos, substituidos, existentes, erros) & vbCrLf & _
        "Pretende importar agora para os separadores do Excel?", _
        vbQuestion + vbYesNo + vbDefaultButton2, "Importar listas IMOS")

    If resposta <> vbYes Then GoTo Saida

    If Not IMOS14_FolhaExiste(ThisWorkbook, "LISTA_ORDENADA") Then
        MsgBox "Falta o separador 'LISTA_ORDENADA' no ficheiro atual." & vbCrLf & _
               "Crie novamente a Lista de Material a partir do modelo atualizado.", _
               vbExclamation, "Importar listas IMOS"
        GoTo Saida
    End If

    separadoresExistentes = IMOS14_SeparadoresQueExistem(ThisWorkbook)
    If Len(separadoresExistentes) > 0 Then
        resposta = MsgBox( _
            "Ja existem separadores importados:" & vbCrLf & separadoresExistentes & vbCrLf & vbCrLf & _
            "Se continuar, estes separadores serao substituidos pelos ficheiros atuais." & vbCrLf & _
            "Pretende substituir?", _
            vbExclamation + vbYesNo + vbDefaultButton2, "Substituir separadores existentes")
        If resposta <> vbYes Then GoTo Saida
    End If

    If Len(ficheiroFerragens) > 0 Or Len(ficheiroEtiqueta) > 0 Then
        Application.StatusBar = "[4/6] A importar Ferragens, PURCH, SPP e Etiqueta..."
        DoEvents
        ImportarFicheiros_1_Ferragens_5_Etiqueta_Palete_11

        ' So se pode exigir a etiqueta quando o IMOS a gerou.
        If Len(ficheiroEtiqueta) > 0 Then
            If Not IMOS14_FolhaExiste(ThisWorkbook, "5_ETIQUETA_PALETE") Then
                MsgBox "A importacao de Ferragens/Etiqueta nao ficou concluida." & vbCrLf & _
                       "Os ficheiros permanecem na pasta da obra para nova tentativa.", _
                       vbCritical, "Importar listas IMOS"
                GoTo Saida
            End If
        End If
    End If

    Application.DisplayAlerts = False
    If Len(ficheiroResumo) > 0 Then
        Application.StatusBar = "[5/6] A importar Resumo de Precos..."
        DoEvents
        IMOS14_ImportarPrimeiraFolha ficheiroResumo, "4_Resumo_Global_Precos", "RELATORIO"
    End If

    If Len(ficheiroIntegrador) > 0 Then
        Application.StatusBar = "[6/6] A importar Lista de Ferragens do Integrador..."
        DoEvents
        ' O integrador entrava a seguir ao Resumo; sem Resumo, entra a seguir
        ' a' LISTA_ORDENADA, que existe sempre.
        If IMOS14_FolhaExiste(ThisWorkbook, "4_Resumo_Global_Precos") Then
            IMOS14_ImportarPrimeiraFolha ficheiroIntegrador, "5_List_Ferragens_Integrador", "4_Resumo_Global_Precos"
        Else
            IMOS14_ImportarPrimeiraFolha ficheiroIntegrador, "5_List_Ferragens_Integrador", "LISTA_ORDENADA"
        End If
    End If
    Application.DisplayAlerts = alertasAnteriores

    ThisWorkbook.Worksheets("LISTA_ORDENADA").Activate
    MsgBox "Importacao concluida." & vbCrLf & vbCrLf & _
           "Ficheiros relacionados com os respetivos separadores:" & aImportar & _
           avisoFalta & vbCrLf & vbCrLf & _
           "Confirme os dados e guarde o Excel.", vbInformation, "Importar listas IMOS"

Saida:
    Application.DisplayAlerts = alertasAnteriores
    Application.StatusBar = estadoAnterior
    Exit Sub

TrataErro:
    Dim numeroErro As Long
    Dim descricaoErro As String
    numeroErro = Err.Number
    descricaoErro = Err.Description
    On Error Resume Next
    Application.DisplayAlerts = alertasAnteriores
    Application.StatusBar = estadoAnterior
    MsgBox "Erro no fluxo IMOS: " & numeroErro & " - " & descricaoErro & vbCrLf & vbCrLf & _
           "Os ficheiros que ja tenham sido validados permanecem na pasta da obra.", _
           vbCritical, "Importar listas IMOS"
End Sub

Private Sub IMOS14_MoverTipo(ByVal prefixoObra As String, ByVal tipo As String, _
                             ByVal pastaDestino As String, ByRef movidos As String, _
                             ByRef substituidos As String, ByRef existentes As String, _
                             ByRef erros As String)
    Dim fso As Object
    Dim pasta As Object
    Dim ficheiro As Object
    Dim candidatos As Collection
    Dim caminho As Variant
    Dim nomeOrigem As String
    Dim nomeDestino As String
    Dim destino As String
    Dim resultado As String
    Dim detalhe As String
    Dim guardada As String

    Set fso = CreateObject("Scripting.FileSystemObject")
    Set candidatos = New Collection
    Set pasta = fso.GetFolder(IMOS14_PASTA_ORIGEM)

    For Each ficheiro In pasta.Files
        If Left$(ficheiro.Name, 2) <> "~$" Then
            If LCase$(ficheiro.Name) Like LCase$(prefixoObra & tipo & "*.xls*") Then
                candidatos.Add ficheiro.Path
            End If
        End If
    Next ficheiro

    ' A listagem pode vir do IMOS (C:\IMOS_Output_Batches) ou ter sido gerada
    ' pelo Martelo diretamente na pasta da obra. Vale a MAIS RECENTE, que e' a
    ' da ultima gravacao do desenho; a outra passa para Listas_IMOS_anteriores
    ' com a data em que tinha sido gerada. Antes a da obra nunca era
    ' substituida e uma listagem corrigida no IMOS ficava por importar.
    For Each caminho In candidatos
        nomeOrigem = fso.GetFileName(CStr(caminho))
        nomeDestino = Mid$(nomeOrigem, Len(prefixoObra) + 1)
        destino = pastaDestino & nomeDestino
        detalhe = ""

        If Not fso.FileExists(destino) Then
            resultado = IMOS14_MoverUmFicheiro(CStr(caminho), destino, detalhe)
            If resultado = "MOVIDO" Then
                movidos = movidos & vbCrLf & "- " & nomeDestino
            Else
                erros = erros & vbCrLf & "- " & nomeOrigem & ": " & detalhe
            End If

        ElseIf fso.GetFile(CStr(caminho)).DateLastModified > fso.GetFile(destino).DateLastModified Then
            ' A do IMOS e' mais recente: a da obra vai para as anteriores.
            guardada = IMOS14_GuardarAnterior(destino, pastaDestino, detalhe)
            If Len(guardada) = 0 Then
                erros = erros & vbCrLf & "- " & nomeDestino & " (esta' aberta?): " & detalhe
            Else
                resultado = IMOS14_MoverUmFicheiro(CStr(caminho), destino, detalhe)
                If resultado = "MOVIDO" Then
                    substituidos = substituidos & vbCrLf & "- " & nomeDestino & _
                                   " (a anterior ficou em " & IMOS14_PASTA_ANTERIORES & ")"
                Else
                    ' Nunca deixar a obra sem a listagem: a anterior volta.
                    On Error Resume Next
                    If Not fso.FileExists(destino) Then Name guardada As destino
                    On Error GoTo 0
                    erros = erros & vbCrLf & "- " & nomeOrigem & ": " & detalhe
                End If
            End If

        Else
            ' A da obra e' mais recente (por exemplo, gerada no Martelo): a do
            ' IMOS nao e' importada e sai de C:\IMOS_Output_Batches para as
            ' anteriores, para nao voltar a aparecer.
            guardada = IMOS14_GuardarAnterior(CStr(caminho), pastaDestino, detalhe)
            If Len(guardada) > 0 Then
                existentes = existentes & vbCrLf & "- " & nomeDestino & _
                             " (a do IMOS era mais antiga e ficou em " & IMOS14_PASTA_ANTERIORES & ")"
            Else
                erros = erros & vbCrLf & "- " & nomeOrigem & ": " & detalhe
            End If
        End If
    Next caminho
End Sub

Private Function IMOS14_GuardarAnterior(ByVal caminho As String, ByVal pastaObra As String, _
                                        ByRef detalhe As String) As String
    ' Mover (nunca apagar) uma listagem para Listas_IMOS_anteriores, com a data
    ' em que tinha sido gerada no nome. Devolve o caminho novo, ou "" se falhou.
    Dim fso As Object
    Dim pastaAnteriores As String
    Dim base As String
    Dim extensao As String
    Dim destino As String
    Dim repetido As Long

    On Error GoTo TrataErro
    Set fso = CreateObject("Scripting.FileSystemObject")
    pastaAnteriores = pastaObra & IMOS14_PASTA_ANTERIORES & "\"
    If Not fso.FolderExists(pastaAnteriores) Then fso.CreateFolder pastaAnteriores

    base = fso.GetBaseName(caminho) & "_" & _
           Format$(fso.GetFile(caminho).DateLastModified, "yyyymmdd_hhnnss")
    extensao = "." & fso.GetExtensionName(caminho)
    destino = pastaAnteriores & base & extensao
    repetido = 2
    Do While fso.FileExists(destino)
        destino = pastaAnteriores & base & "_" & CStr(repetido) & extensao
        repetido = repetido + 1
    Loop

    If LCase$(Left$(caminho, 2)) = LCase$(Left$(destino, 2)) Then
        Name caminho As destino
    Else
        ' Entre discos (C: -> servidor): copia, confirma e so' depois tira.
        FileCopy caminho, destino
        If FileLen(caminho) <> FileLen(destino) Then
            Err.Raise vbObjectError + 1404, "IMOS14_GuardarAnterior", _
                      "A copia nao ficou com o mesmo tamanho da origem."
        End If
        Kill caminho
    End If
    IMOS14_GuardarAnterior = destino
    Exit Function

TrataErro:
    detalhe = CStr(Err.Number) & " - " & Err.Description
    IMOS14_GuardarAnterior = ""
End Function

Private Function IMOS14_DataFicheiro(ByVal caminho As String) As String
    ' "  [gerada 29-09-2026 11:08]", para se ver de quando e' cada listagem.
    Dim fso As Object
    On Error GoTo Fim
    If Len(caminho) = 0 Then Exit Function
    Set fso = CreateObject("Scripting.FileSystemObject")
    IMOS14_DataFicheiro = "  [gerada " & _
        Format$(fso.GetFile(caminho).DateLastModified, "dd-mm-yyyy hh:nn") & "]"
Fim:
End Function

Private Function IMOS14_MoverUmFicheiro(ByVal origem As String, ByVal destino As String, _
                                        ByRef detalhe As String) As String
    Dim fso As Object
    Dim temporario As String
    Dim destinoCriado As Boolean

    On Error GoTo TrataErro
    Set fso = CreateObject("Scripting.FileSystemObject")

    If fso.FileExists(destino) Then
        IMOS14_MoverUmFicheiro = "EXISTE"
        Exit Function
    End If

    temporario = destino & ".martelo_tmp_" & Format$(Now, "yyyymmdd_hhnnss") & _
                 "_" & CStr(CLng(Timer * 100))
    FileCopy origem, temporario

    If FileLen(origem) <> FileLen(temporario) Then
        Err.Raise vbObjectError + 1401, "IMOS14_MoverUmFicheiro", _
                  "A copia nao ficou com o mesmo tamanho da origem."
    End If

    Name temporario As destino
    destinoCriado = True
    Kill origem
    IMOS14_MoverUmFicheiro = "MOVIDO"
    Exit Function

TrataErro:
    detalhe = CStr(Err.Number) & " - " & Err.Description
    On Error Resume Next
    If Not destinoCriado Then
        If Len(temporario) > 0 And fso.FileExists(temporario) Then Kill temporario
    ElseIf fso.FileExists(origem) Then
        detalhe = detalhe & " (a copia ficou no destino e a origem foi mantida)"
    End If
    IMOS14_MoverUmFicheiro = "ERRO"
End Function

Private Function IMOS14_FicheiroMaisRecente(ByVal pasta As String, ByVal padrao As String) As String
    Dim fso As Object
    Dim pastaObj As Object
    Dim ficheiro As Object
    Dim dataMaisRecente As Date

    Set fso = CreateObject("Scripting.FileSystemObject")
    If Not fso.FolderExists(pasta) Then Exit Function
    Set pastaObj = fso.GetFolder(pasta)

    For Each ficheiro In pastaObj.Files
        If Left$(ficheiro.Name, 2) <> "~$" Then
            If LCase$(ficheiro.Name) Like LCase$(padrao) Then
                If Len(IMOS14_FicheiroMaisRecente) = 0 Or ficheiro.DateLastModified > dataMaisRecente Then
                    dataMaisRecente = ficheiro.DateLastModified
                    IMOS14_FicheiroMaisRecente = ficheiro.Path
                End If
            End If
        End If
    Next ficheiro
End Function

Private Sub IMOS14_ImportarPrimeiraFolha(ByVal caminhoFicheiro As String, _
                                         ByVal nomeDestino As String, _
                                         ByVal inserirDepoisDe As String)
    Dim wbOrigem As Workbook
    Dim wsNova As Worksheet

    If Len(caminhoFicheiro) = 0 Then
        Err.Raise vbObjectError + 1402, "IMOS14_ImportarPrimeiraFolha", _
                  "Ficheiro de origem nao indicado para " & nomeDestino
    End If
    If Not IMOS14_FolhaExiste(ThisWorkbook, inserirDepoisDe) Then
        Err.Raise vbObjectError + 1403, "IMOS14_ImportarPrimeiraFolha", _
                  "Separador base nao encontrado: " & inserirDepoisDe
    End If

    IMOS14_EliminarFolhaSeExiste ThisWorkbook, nomeDestino
    Set wbOrigem = Workbooks.Open(fileName:=caminhoFicheiro, UpdateLinks:=0, _
                                  ReadOnly:=True, AddToMru:=False)
    wbOrigem.Worksheets(1).Copy After:=ThisWorkbook.Worksheets(inserirDepoisDe)
    Set wsNova = ThisWorkbook.Worksheets(ThisWorkbook.Worksheets(inserirDepoisDe).Index + 1)
    wsNova.Name = nomeDestino
    wbOrigem.Close SaveChanges:=False

    If nomeDestino = "4_Resumo_Global_Precos" Then
        With wsNova.Columns("I:J")
            .HorizontalAlignment = xlGeneral
            .Orientation = 0
            .AddIndent = False
            .IndentLevel = 0
            .ShrinkToFit = False
            .MergeCells = False
        End With
        wsNova.Columns("G:L").EntireColumn.AutoFit
    End If
End Sub

Private Sub IMOS14_EliminarFolhaSeExiste(ByVal wb As Workbook, ByVal nomeFolha As String)
    If IMOS14_FolhaExiste(wb, nomeFolha) Then wb.Worksheets(nomeFolha).Delete
End Sub

Private Function IMOS14_SeparadoresQueExistem(ByVal wb As Workbook) As String
    Dim nomes As Variant
    Dim nome As Variant

    nomes = Array("1_FERRAGENS", "2_PURCH", "3_SPP", "5_ETIQUETA_PALETE", _
                  "4_Resumo_Global_Precos", "5_List_Ferragens_Integrador")
    For Each nome In nomes
        If IMOS14_FolhaExiste(wb, CStr(nome)) Then
            IMOS14_SeparadoresQueExistem = IMOS14_SeparadoresQueExistem & vbCrLf & "- " & CStr(nome)
        End If
    Next nome
End Function

Private Function IMOS14_FolhaExiste(ByVal wb As Workbook, ByVal nomeFolha As String) As Boolean
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = wb.Worksheets(nomeFolha)
    IMOS14_FolhaExiste = Not ws Is Nothing
    Set ws = Nothing
    On Error GoTo 0
End Function

Private Function IMOS14_TextoMovimento(ByVal movidos As String, ByVal substituidos As String, _
                                       ByVal existentes As String, ByVal erros As String) As String
    If Len(movidos) > 0 Then
        IMOS14_TextoMovimento = IMOS14_TextoMovimento & vbCrLf & vbCrLf & _
                                "Trazidos do IMOS para a pasta da obra:" & movidos
    End If
    If Len(substituidos) > 0 Then
        IMOS14_TextoMovimento = IMOS14_TextoMovimento & vbCrLf & vbCrLf & _
                                "Trazidos do IMOS por serem mais recentes do que os da obra:" & substituidos
    End If
    If Len(existentes) > 0 Then
        IMOS14_TextoMovimento = IMOS14_TextoMovimento & vbCrLf & vbCrLf & _
                                "Ficam os da pasta da obra, por serem mais recentes:" & existentes
    End If
    If Len(erros) > 0 Then
        IMOS14_TextoMovimento = IMOS14_TextoMovimento & vbCrLf & vbCrLf & _
                                "Erros:" & erros
    End If
End Function

Private Function IMOS14_LerPrefixoProcesso() As String
    On Error GoTo Fallback
    IMOS14_LerPrefixoProcesso = Trim$(CStr( _
        ThisWorkbook.Names("NOME_ENC_IMOS_IX").RefersToRange.Value))
    Exit Function

Fallback:
    On Error Resume Next
    IMOS14_LerPrefixoProcesso = Trim$(CStr( _
        ThisWorkbook.Worksheets("DEFENICOES").Range("E3").Value))
    On Error GoTo 0
End Function



