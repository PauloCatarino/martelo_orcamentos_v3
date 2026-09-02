"""A importação IMOS aceita só os ficheiros que o IMOS gerou.

Antes exigiam-se os quatro (2_List_Ferragens, 3_Resumo_Precos, 4_Etiqueta_Palete
e 5_List_Ferragens_Integrador) e parava tudo à primeira falta. Há obras que não
geram os quatro, e por causa disso ficava tudo por importar.

O código corre dentro do modelo Excel, mas a fonte de verdade são os .bas do
repositório: é deles que o `atualizar_macros_modelo_lista_material.py` escreve
no `Lista_Material_IMOS_MARTELO.xltm`.
"""

from __future__ import annotations

from pathlib import Path

VBA = Path(__file__).resolve().parents[1] / "scripts" / "vba"
MODULO_13 = VBA / "RenomeiaListagensImos_13.bas"
MODULO_11 = VBA / "Import_List_Ferr_Etiq_11.bas"


def _codigo(modulo: Path) -> str:
    return modulo.read_text(encoding="cp1252")


# ---- o módulo de entrada (macro 14) ----------------------------------------


def test_o_modulo_de_entrada_esta_versionado() -> None:
    """A app chama esta macro; sem fonte no repo, mexer nela era às cegas."""
    codigo = _codigo(MODULO_13)

    assert "Public Sub ImportarListasFerragensIMOS_14()" in codigo


def test_deixou_de_parar_quando_falta_um_ficheiro() -> None:
    codigo = _codigo(MODULO_13)

    assert "O movimento foi interrompido antes da importacao" not in codigo
    assert "Os quatro ficheiros estao prontos" not in codigo


def test_continua_a_parar_quando_nao_ha_ficheiro_nenhum() -> None:
    """Sem nada para importar não há nada a fazer — isso mantém-se."""
    codigo = _codigo(MODULO_13)

    assert (
        'If Len(ficheiroFerragens) = 0 And Len(ficheiroResumo) = 0 And _' in codigo
    )
    assert "Nao foram encontrados ficheiros desta obra" in codigo


def test_cada_importacao_e_guardada_pelo_seu_ficheiro() -> None:
    codigo = _codigo(MODULO_13)

    # Ferragens/etiqueta: só chama a macro 11 se houver algum dos dois.
    assert (
        'If Len(ficheiroFerragens) > 0 Or Len(ficheiroEtiqueta) > 0 Then' in codigo
    )
    # Resumo e integrador: cada um atrás do seu próprio ficheiro.
    assert "If Len(ficheiroResumo) > 0 Then" in codigo
    assert "If Len(ficheiroIntegrador) > 0 Then" in codigo


def test_a_etiqueta_so_e_exigida_quando_o_imos_a_gerou() -> None:
    """O aviso «não ficou concluída» olhava para uma folha que podia não vir."""
    codigo = _codigo(MODULO_13)
    antes = codigo.index("If Len(ficheiroEtiqueta) > 0 Then")
    depois = codigo.index('IMOS14_FolhaExiste(ThisWorkbook, "5_ETIQUETA_PALETE")')

    assert antes < depois


def test_o_integrador_entra_mesmo_sem_o_resumo() -> None:
    """Entrava a seguir ao Resumo; sem Resumo iria buscar uma folha inexistente."""
    codigo = _codigo(MODULO_13)

    assert (
        'IMOS14_ImportarPrimeiraFolha ficheiroIntegrador, '
        '"5_List_Ferragens_Integrador", "LISTA_ORDENADA"' in codigo
    )


def test_as_mensagens_dizem_o_que_entrou_e_o_que_faltou() -> None:
    codigo = _codigo(MODULO_13)

    assert "Vai importar:" in codigo
    assert "O IMOS nao gerou estes" in codigo
    assert "Ficheiros relacionados com os respetivos separadores:" in codigo


# ---- o módulo das ferragens e da etiqueta (macro 11) -----------------------


def test_so_desiste_quando_faltam_os_dois() -> None:
    codigo = _codigo(MODULO_11)

    assert 'If f1 = "" And f2 = "" Then' in codigo
    assert 'If f1 = "" Or f2 = "" Then' not in codigo


def test_cada_bloco_e_saltado_quando_o_ficheiro_falta() -> None:
    codigo = _codigo(MODULO_11)

    assert 'If f1 = "" Then GoTo SemFerragens' in codigo
    assert "SemFerragens:" in codigo
    assert 'If f2 = "" Then GoTo SemEtiqueta' in codigo
    assert "SemEtiqueta:" in codigo


def test_so_se_apaga_o_separador_que_vai_ser_substituido() -> None:
    """Apagar um separador sem ficheiro para pôr no lugar era perdê-lo."""
    codigo = _codigo(MODULO_11)
    procura = codigo.index("f1 = IMOS_GetNewestMatchingFile")
    apaga_ferragens = codigo.index('IMOS_EliminarSeparador wbAtual, "1_FERRAGENS"')

    # As eliminações passaram para DEPOIS de se saber que ficheiros existem.
    assert procura < apaga_ferragens
    assert 'If f2 <> "" Then IMOS_EliminarSeparador wbAtual, "5_ETIQUETA_PALETE"' in codigo


def test_os_dois_modulos_sao_escritos_no_modelo() -> None:
    """Sem estar na lista, a alteração ficava só no repositório."""
    script = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "atualizar_macros_modelo_lista_material.py"
    ).read_text(encoding="utf-8")

    assert '"Import_List_Ferr_Etiq_11", "RenomeiaListagensImos_13"' in script
