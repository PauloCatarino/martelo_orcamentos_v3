Attribute VB_Name = "RenomeiaListagensImos_13"
Option Explicit

' Fluxo unificado IMOS -> pasta da obra -> separadores Excel.
' Mantem a macro antiga como ponto de entrada por compatibilidade.

Private Const IMOS14_PASTA_ORIGEM As String = "C:\IMOS_Output_Batches\"
Private Const IMOS14_FERRAGENS As String = "2_List_Ferragens"
Private Const IMOS14_RESUMO As String = "3_Resumo_Precos"
Private Const IMOS14_ETIQUETA As String = "4_Etiqueta_Palete"
Private Const IMOS14_INTEGRADOR As String = "5_List_Ferragens_Integrador"

Public Function IMOS14_Versao() As String
    IMOS14_Versao = "2026-08-23"
End Function

Public Sub RenomeiaNomesListaImosCopiaParaPstaObra_13()
    ImportarListasFerragensIMOS_14
End Sub

Public Sub ImportarListasFerragensIMOS_14()
    Dim fso As Object
    Dim pastaDestino As String
    Dim prefixoObra As String
    Dim movidos As String
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

    Application.StatusBar = "[2/6] A mover e validar as quatro listagens do IMOS..."
    DoEvents

    IMOS14_MoverTipo prefixoObra, IMOS14_FERRAGENS, pastaDestino, movidos, existentes, erros
    IMOS14_MoverTipo prefixoObra, IMOS14_RESUMO, pastaDestino, movidos, existentes, erros
    IMOS14_MoverTipo prefixoObra, IMOS14_ETIQUETA, pastaDestino, movidos, existentes, erros
    IMOS14_MoverTipo prefixoObra, IMOS14_INTEGRADOR, pastaDestino, movidos, existentes, erros

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
               "Destino: " & pastaDestino & IMOS14_TextoMovimento(movidos, existentes, erros), _
               vbExclamation, "Importar listas IMOS"
        GoTo Saida
    End If

    ' Antes exigiam-se os quatro ficheiros e a importacao parava a' primeira
    ' falta. Nem todas as obras geram os quatro no IMOS (ha' obras sem
    ' ferragens, sem etiqueta ou sem integrador), e por causa disso ficava tudo
    ' por importar. Agora importa-se o que existe e diz-se o que faltou.
    aImportar = ""
    If Len(ficheiroFerragens) > 0 Then
        aImportar = aImportar & vbCrLf & "- 2_List_Ferragens -> 1_FERRAGENS / 2_PURCH / 3_SPP"
    End If
    If Len(ficheiroResumo) > 0 Then
        aImportar = aImportar & vbCrLf & "- 3_Resumo_Precos -> 4_Resumo_Global_Precos"
    End If
    If Len(ficheiroEtiqueta) > 0 Then
        aImportar = aImportar & vbCrLf & "- 4_Etiqueta_Palete -> 5_ETIQUETA_PALETE"
    End If
    If Len(ficheiroIntegrador) > 0 Then
        aImportar = aImportar & vbCrLf & "- 5_List_Ferragens_Integrador -> 5_List_Ferragens_Integrador"
    End If

    avisoFalta = ""
    If Len(emFalta) > 0 Then
        avisoFalta = vbCrLf & vbCrLf & _
                     "O IMOS nao gerou estes (nao ha' nada a importar deles):" & emFalta
    End If

    resposta = MsgBox( _
        "Ficheiros do IMOS prontos na pasta da obra." & vbCrLf & vbCrLf & _
        "Vai importar:" & aImportar & _
        avisoFalta & vbCrLf & _
        IMOS14_TextoMovimento(movidos, existentes, erros) & vbCrLf & _
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
                             ByRef existentes As String, ByRef erros As String)
    Dim fso As Object
    Dim pasta As Object
    Dim ficheiro As Object
    Dim candidatos As Collection
    Dim caminho As Variant
    Dim nomeOrigem As String
    Dim nomeDestino As String
    Dim resultado As String
    Dim detalhe As String

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

    For Each caminho In candidatos
        nomeOrigem = fso.GetFileName(CStr(caminho))
        nomeDestino = Mid$(nomeOrigem, Len(prefixoObra) + 1)
        resultado = IMOS14_MoverUmFicheiro(CStr(caminho), pastaDestino & nomeDestino, detalhe)

        Select Case resultado
            Case "MOVIDO"
                movidos = movidos & vbCrLf & "- " & nomeDestino
            Case "EXISTE"
                existentes = existentes & vbCrLf & "- " & nomeDestino & _
                            " (nao substituido; a origem foi mantida)"
            Case Else
                erros = erros & vbCrLf & "- " & nomeOrigem & ": " & detalhe
        End Select
    Next caminho
End Sub

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

Private Function IMOS14_TextoMovimento(ByVal movidos As String, ByVal existentes As String, _
                                       ByVal erros As String) As String
    If Len(movidos) > 0 Then
        IMOS14_TextoMovimento = IMOS14_TextoMovimento & vbCrLf & vbCrLf & _
                                "Movidos para a pasta da obra:" & movidos
    End If
    If Len(existentes) > 0 Then
        IMOS14_TextoMovimento = IMOS14_TextoMovimento & vbCrLf & vbCrLf & _
                                "Ja existentes no destino:" & existentes
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



