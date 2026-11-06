Attribute VB_Name = "Folha5"
Attribute VB_Base = "0{00020820-0000-0000-C000-000000000046}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = True
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = True
Option Explicit

Private Sub Workbook_Open()
    ' Garante que a validação (Esp.Mat/Esp.Final + CF) funciona "online"
    Application.Calculation = xlCalculationAutomatic
    Application.CalculateFull
End Sub

Private Sub Worksheet_BeforeDoubleClick(ByVal Target As Range, Cancel As Boolean)
    ' ENSAIO 06-11-2026 (modelo COLAR): duplo clique numa célula da coluna Colar
    ' abre o menu de colagens (frmColar, regras no modColar).
    If ColarCelulaDaColuna(Target) Then
        Cancel = True
        AbrirMenuColar
    End If
End Sub
