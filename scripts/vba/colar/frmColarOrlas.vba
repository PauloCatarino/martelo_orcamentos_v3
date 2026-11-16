Option Explicit

'====================================================================
'  frmColarOrlas - orlas ANTES de colar?   (16-11-2026, pedido do Paulo)
'--------------------------------------------------------------------
'  Abre-se no «Gravar» do menu Colar quando o código leva orla depois de colar
'  e as peças do conjunto já têm orla nas colunas Orla ESQ/DIR/CIMA/BAIXO.
'  Escolha: 1 = manter as orlas antes e depois de colar; 2 = orlas só depois de
'  colar (o menu limpa as orlas das peças); 0 = não gravar.
'  Os controlos criam-se no Initialize (o menu vive em texto no repositório:
'  scripts/vba/colar/frmColarOrlas.vba).
'====================================================================

Public Escolha As Long

Private WithEvents btnManter As MSForms.CommandButton
Private WithEvents btnSoDepois As MSForms.CommandButton
Private WithEvents btnCancelar As MSForms.CommandButton
Private lblTexto As MSForms.Label
Private lblEstado As MSForms.Label

Private Sub UserForm_Initialize()
    Me.Caption = "Colar - orlas antes de colar"
    Me.Width = 470
    Me.Height = 300
    Escolha = 0

    Set lblTexto = Me.Controls.Add("Forms.Label.1", "lblTexto", True)
    With lblTexto
        .Left = 10: .Top = 8: .Width = 446: .Height = 160
        .WordWrap = True
        .Font.Size = 9
    End With

    Set btnManter = Me.Controls.Add("Forms.CommandButton.1", "btnManter", True)
    With btnManter
        .Left = 10: .Top = 176: .Width = 446: .Height = 26
        .Caption = "Manter as orlas antes e depois de colar"
        .ControlTipText = "As peças ficam com as orlas das colunas Orla (orladas antes de colar) " & _
                          "e levam também a orla do código depois de colar."
    End With
    Set btnSoDepois = Me.Controls.Add("Forms.CommandButton.1", "btnSoDepois", True)
    With btnSoDepois
        .Left = 10: .Top = 206: .Width = 446: .Height = 26
        .Caption = "Orlas só depois de colar (limpa as orlas das peças)"
        .ControlTipText = "Apaga as orlas das colunas Orla ESQ/DIR/CIMA/BAIXO das peças do conjunto: " & _
                          "só se orla depois de colar. A orla que lá estava fica escrita nas Notas."
    End With
    Set btnCancelar = Me.Controls.Add("Forms.CommandButton.1", "btnCancelar", True)
    With btnCancelar
        .Left = 356: .Top = 236: .Width = 100: .Height = 22
        .Caption = "Cancelar"
        .Cancel = True
        .ControlTipText = "Não grava: volta ao menu Colar."
    End With

    Set lblEstado = Me.Controls.Add("Forms.Label.1", "lblEstado", True)
    With lblEstado
        .Left = 10: .Top = 240: .Width = 340: .Height = 18
        .Font.Size = 8
        .ForeColor = RGB(90, 90, 90)
        .Caption = "Escolha o que fazer às orlas das peças antes de colar."
    End With
End Sub

Public Sub Preparar(ByVal orlasAntes As String)
    lblTexto.Caption = "Foi detetado que as peças contêm orla antes de colar:" & vbCrLf & _
                       orlasAntes & vbCrLf & vbCrLf & _
                       "Pretende manter as orlas nas peças antes de colar e depois de colar?"
End Sub

Private Sub btnManter_Click()
    Escolha = 1
    Me.Hide
End Sub

Private Sub btnSoDepois_Click()
    Escolha = 2
    Me.Hide
End Sub

Private Sub btnCancelar_Click()
    Escolha = 0
    Me.Hide
End Sub

Private Sub UserForm_QueryClose(Cancel As Integer, CloseMode As Integer)
    If CloseMode = 0 Then   ' o X da janela = Cancelar
        Cancel = True
        Escolha = 0
        Me.Hide
    End If
End Sub
