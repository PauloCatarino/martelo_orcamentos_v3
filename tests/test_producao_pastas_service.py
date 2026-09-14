"""Tests for production folder tree helpers."""

from __future__ import annotations

import pytest

from app.services.producao_service import (
    gerar_nome_enc_imos_ix,
    gerar_nome_plano_cut_rite,
)
from app.services.producao_pastas_service import (
    PRODUCAO_BASE_PATH_DEFAULT,
    _folder_name_matches_prefix,
    _nome_ja_e_do_nivel_seguinte,
    _norm_enc,
    _normalizar_path_windows,
    _num_enc_norm,
    _tipo_dir,
    caminho_versao_de_processo_existente,
    caminho_versao_para_criar,
    encontrar_caminho_versao,
    listar_pastas_enc_arvore,
    segmentos_pasta,
)


def _usar_base(monkeypatch, base) -> None:
    """Faz o servico ler as pastas de teste em vez do servidor real."""
    import app.services.producao_pastas_service as pastas_module

    monkeypatch.setattr(
        pastas_module,
        "_resolve_base_dir",
        lambda _session, _base=None: str(base),
    )


def test_norm_enc_formata_phc_e_cliente_final() -> None:
    assert _norm_enc("475") == "0475"
    assert _norm_enc("_5") == "_005"
    assert _num_enc_norm("1058") == "1058"
    assert _num_enc_norm("_5") == "_005"


def test_tipo_dir_distingue_cliente_final() -> None:
    assert _tipo_dir("Encomenda de Cliente Final") == "Encomenda de Cliente Final"
    assert _tipo_dir("Encomenda de Cliente") == "Encomenda de Cliente"


def test_folder_name_matches_prefix_exige_prefixo_correto() -> None:
    assert _folder_name_matches_prefix("0278_JF_VIVA", "0278") is True
    assert _folder_name_matches_prefix("1058_JF_VIVA", "1058") is True
    assert _folder_name_matches_prefix("1058", "1058") is True
    assert _folder_name_matches_prefix("10589_X", "1058") is False
    assert _folder_name_matches_prefix("0279_X", "0278") is False


def test_default_producao_base_path_usa_host_unc_correto() -> None:
    assert (
        PRODUCAO_BASE_PATH_DEFAULT
        == r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep_Producao"
    )


def test_normalizar_path_windows_colapsa_barras_e_preserva_unc() -> None:
    assert (
        _normalizar_path_windows(
            r"\\\\SERVER_LE\\_Lanca_Encanto\\LancaEncanto\\Dep_Producao"
        )
        == r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep_Producao"
    )
    assert (
        _normalizar_path_windows(
            r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep_Producao"
        )
        == r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep_Producao"
    )
    assert _normalizar_path_windows("C:/a//b") == r"C:\a\b"
    assert _normalizar_path_windows("") == ""


def test_gerar_nomes_externos_de_producao() -> None:
    assert (
        gerar_nome_plano_cut_rite(
            "2026",
            "1058",
            "01",
            "01",
            nome_cliente_simplex="JF VIVA",
        )
        == "1058_01_01_26_JF_VIVA"
    )
    assert (
        gerar_nome_enc_imos_ix(
            "2026",
            "1058",
            "01",
            nome_cliente_simplex="JF VIVA",
        )
        == "1058_01_26_JF_VIVA"
    )


def test_segmentos_pasta_para_nova_versao() -> None:
    assert segmentos_pasta(
        "1058",
        "01",
        "01",
        nome_simplex="JF_VIVA",
    ) == (
        "1058_JF_VIVA",
        "1058_01_JF_VIVA",
        "1058_01_01_JF_VIVA",
    )


def test_listar_pastas_enc_arvore_lista_niveis_do_servidor(tmp_path) -> None:
    root = tmp_path / "2026" / "Encomenda de Cliente"
    pasta_obra = root / "1058_JF_VIVA" / "1058_01_JF_VIVA"
    for plano in ("01", "02", "03"):
        (pasta_obra / f"1058_01_{plano}_JF_VIVA").mkdir(parents=True)
    (root / "10589_X").mkdir()

    root_path, arvore = listar_pastas_enc_arvore(
        object(),
        ano="2026",
        num_enc_phc="1058",
        tipo_pasta="Encomenda de Cliente",
        base_dir=tmp_path,
    )

    assert root_path == str(root)
    assert arvore == {
        "1058_JF_VIVA": {
            "1058_01_JF_VIVA": [
                "1058_01_01_JF_VIVA",
                "1058_01_02_JF_VIVA",
                "1058_01_03_JF_VIVA",
            ]
        }
    }


def test_nome_ja_e_do_nivel_seguinte_separa_versao_de_obra_e_de_plano() -> None:
    assert _nome_ja_e_do_nivel_seguinte("1259_01_01_LINHAS", "1259_01") is True
    assert _nome_ja_e_do_nivel_seguinte("1259_01_LINHAS", "1259_01") is False
    assert _nome_ja_e_do_nivel_seguinte("0621_04_WERNAGEN", "0621_04") is False


def test_encontrar_caminho_versao_usa_o_caminho_calculado_quando_existe(
    tmp_path,
    monkeypatch,
) -> None:
    _usar_base(monkeypatch, tmp_path)
    esperado = (
        tmp_path
        / "2026"
        / "Encomenda de Cliente"
        / "1058_JF_VIVA"
        / "1058_01_JF_VIVA"
        / "1058_01_01_JF_VIVA"
    )
    esperado.mkdir(parents=True)

    encontrado = encontrar_caminho_versao(
        object(),
        ano="2026",
        tipo_pasta="Encomenda de Cliente",
        num_enc_phc="1058",
        versao_obra="01",
        versao_plano="01",
        nome_simplex="JF_VIVA",
    )

    assert encontrado == esperado


def test_encontrar_caminho_versao_aceita_sufixo_no_nome_do_cliente(
    tmp_path,
    monkeypatch,
) -> None:
    """Pastas antigas: seg1 tem sufixo (0621_WERNAGEN__IMOB) e seg2/seg3 nao."""
    _usar_base(monkeypatch, tmp_path)
    root = tmp_path / "2026" / "Encomenda de Cliente"
    real = (
        root
        / "0621_WERNAGEN__IMOB"
        / "0621_04_WERNAGEN"
        / "0621_04_01_WERNAGEN"
    )
    real.mkdir(parents=True)
    # Pasta com o nome exato calculado, mas vazia: nao pode "ganhar".
    (root / "0621_WERNAGEN").mkdir()

    encontrado = encontrar_caminho_versao(
        object(),
        ano="2026",
        tipo_pasta="Encomenda de Cliente",
        num_enc_phc="0621",
        versao_obra="04",
        versao_plano="01",
        nome_simplex="WERNAGEN",
    )

    assert encontrado == real


def test_encontrar_caminho_versao_aceita_nome_de_cliente_truncado(
    tmp_path,
    monkeypatch,
) -> None:
    _usar_base(monkeypatch, tmp_path)
    real = (
        tmp_path
        / "2026"
        / "Encomenda de Cliente"
        / "1259_LINHAS_DIREITA"
        / "1259_01_LINHAS_DIREITA"
        / "1259_01_01_LINHAS_DIREITA"
    )
    real.mkdir(parents=True)

    encontrado = encontrar_caminho_versao(
        object(),
        ano="2026",
        tipo_pasta="Encomenda de Cliente",
        num_enc_phc="1259",
        versao_obra="01",
        versao_plano="01",
        nome_simplex="LINHAS_DIREITAS",
    )

    assert encontrado == real


def test_encontrar_caminho_versao_nao_confunde_versoes_nem_outras_obras(
    tmp_path,
    monkeypatch,
) -> None:
    _usar_base(monkeypatch, tmp_path)
    root = tmp_path / "2026" / "Encomenda de Cliente"
    # Outra versao de obra e outra encomenda parecida.
    (root / "1259_LINHAS" / "1259_02_LINHAS" / "1259_02_01_LINHAS").mkdir(parents=True)
    (root / "12599_OUTRA" / "12599_01_OUTRA" / "12599_01_01_OUTRA").mkdir(parents=True)

    encontrado = encontrar_caminho_versao(
        object(),
        ano="2026",
        tipo_pasta="Encomenda de Cliente",
        num_enc_phc="1259",
        versao_obra="01",
        versao_plano="01",
        nome_simplex="LINHAS",
    )

    assert encontrado is None


def test_caminho_versao_de_processo_existente_encontra_pasta_com_outro_nome(
    tmp_path,
    monkeypatch,
) -> None:
    from types import SimpleNamespace

    _usar_base(monkeypatch, tmp_path)
    real = (
        tmp_path
        / "2026"
        / "Encomenda de Cliente"
        / "0621_WERNAGEN__IMOB"
        / "0621_04_WERNAGEN"
        / "0621_04_01_WERNAGEN"
    )
    real.mkdir(parents=True)

    processo = SimpleNamespace(
        ano="2026",
        tipo_pasta="Encomenda de Cliente",
        num_enc_phc="0621",
        versao_obra="04",
        versao_plano="01",
        nome_cliente_simplex="WERNAGEN",
        nome_cliente="WERNAGEN - IMOBILIARIA LDA",
        ref_cliente="",
        pasta_servidor=None,
    )

    assert caminho_versao_de_processo_existente(object(), processo) == real


def test_caminho_versao_de_processo_existente_devolve_none_sem_pasta(
    tmp_path,
    monkeypatch,
) -> None:
    from types import SimpleNamespace

    _usar_base(monkeypatch, tmp_path)
    (tmp_path / "2026" / "Encomenda de Cliente").mkdir(parents=True)

    processo = SimpleNamespace(
        ano="2026",
        tipo_pasta="Encomenda de Cliente",
        num_enc_phc="0621",
        versao_obra="09",
        versao_plano="01",
        nome_cliente_simplex="WERNAGEN",
        nome_cliente="WERNAGEN - IMOBILIARIA LDA",
        ref_cliente="",
        pasta_servidor="",
    )

    assert caminho_versao_de_processo_existente(object(), processo) is None


def test_caminho_para_criar_entra_na_arvore_que_ja_existe(
    tmp_path,
    monkeypatch,
) -> None:
    """Nova versão da 0621 vai para dentro de 0621_WERNAGEN__IMOB."""
    _usar_base(monkeypatch, tmp_path)
    root = tmp_path / "2026" / "Encomenda de Cliente"
    (root / "0621_WERNAGEN__IMOB" / "0621_04_WERNAGEN" / "0621_04_01_WERNAGEN").mkdir(
        parents=True
    )

    caminho = caminho_versao_para_criar(
        object(),
        ano="2026",
        tipo_pasta="Encomenda de Cliente",
        num_enc_phc="0621",
        versao_obra="05",
        versao_plano="01",
        nome_simplex="WERNAGEN",
    )

    assert caminho == (
        root / "0621_WERNAGEN__IMOB" / "0621_05_WERNAGEN" / "0621_05_01_WERNAGEN"
    )


def test_caminho_para_criar_reaproveita_a_versao_de_obra_existente(
    tmp_path,
    monkeypatch,
) -> None:
    """Novo plano CUT-RITE fica ao lado dos outros da mesma versão de obra."""
    _usar_base(monkeypatch, tmp_path)
    root = tmp_path / "2026" / "Encomenda de Cliente"
    (root / "1259_LINHAS_DIREITA" / "1259_01_LINHAS_DIREITA" / "1259_01_01_LINHAS_DIREITA").mkdir(
        parents=True
    )

    caminho = caminho_versao_para_criar(
        object(),
        ano="2026",
        tipo_pasta="Encomenda de Cliente",
        num_enc_phc="1259",
        versao_obra="01",
        versao_plano="02",
        nome_simplex="LINHAS_DIREITAS",
    )

    assert caminho == (
        root
        / "1259_LINHAS_DIREITA"
        / "1259_01_LINHAS_DIREITA"
        / "1259_01_02_LINHAS_DIREITAS"
    )


def test_caminho_para_criar_usa_o_nome_calculado_quando_nao_ha_nada(
    tmp_path,
    monkeypatch,
) -> None:
    _usar_base(monkeypatch, tmp_path)
    root = tmp_path / "2026" / "Encomenda de Cliente"
    root.mkdir(parents=True)
    # Outra encomenda parecida não pode servir de casa.
    (root / "12599_OUTRA").mkdir()

    caminho = caminho_versao_para_criar(
        object(),
        ano="2026",
        tipo_pasta="Encomenda de Cliente",
        num_enc_phc="1259",
        versao_obra="01",
        versao_plano="01",
        nome_simplex="LINHAS_DIREITAS",
    )

    assert caminho == (
        root
        / "1259_LINHAS_DIREITAS"
        / "1259_01_LINHAS_DIREITAS"
        / "1259_01_01_LINHAS_DIREITAS"
    )


def test_caminho_para_criar_reaproveita_a_propria_pasta_da_versao(
    tmp_path,
    monkeypatch,
) -> None:
    """Se a pasta da versão já lá está com outro nome, não se cria uma gémea."""
    _usar_base(monkeypatch, tmp_path)
    root = tmp_path / "2026" / "Encomenda de Cliente"
    existente = (
        root / "0621_WERNAGEN__IMOB" / "0621_01_WERNAGEN__IMOB" / "0621_01_01_WERNAGEN__IMOB"
    )
    existente.mkdir(parents=True)

    caminho = caminho_versao_para_criar(
        object(),
        ano="2026",
        tipo_pasta="Encomenda de Cliente",
        num_enc_phc="0621",
        versao_obra="01",
        versao_plano="01",
        nome_simplex="WERNAGEN",
    )

    assert caminho == existente


def test_eliminar_pasta_versao_recusa_nome_inesperado_sem_rmtree(
    tmp_path,
    monkeypatch,
) -> None:
    import app.services.producao_pastas_service as pastas_module

    seg3 = "1058_01_01_JF_VIVA"
    pasta = tmp_path / "2026" / "Encomenda de Cliente" / "1058_JF_VIVA" / "1058_01_JF_VIVA" / seg3
    pasta.mkdir(parents=True)
    chamadas = []

    monkeypatch.setattr(pastas_module, "resolver_base_dir", lambda _session: str(tmp_path))
    monkeypatch.setattr(pastas_module.shutil, "rmtree", lambda path: chamadas.append(path))

    with pytest.raises(ValueError, match="Nome da pasta"):
        pastas_module.eliminar_pasta_versao(
            object(),
            pasta,
            nome_esperado="1058_01_02_JF_VIVA",
        )

    assert chamadas == []
    assert pasta.is_dir()


def test_eliminar_pasta_versao_recusa_caminho_fora_da_base_sem_rmtree(
    tmp_path,
    monkeypatch,
) -> None:
    import app.services.producao_pastas_service as pastas_module

    base = tmp_path / "base"
    base.mkdir()
    seg3 = "1058_01_01_JF_VIVA"
    pasta = tmp_path / "fora" / seg3
    pasta.mkdir(parents=True)
    chamadas = []

    monkeypatch.setattr(pastas_module, "resolver_base_dir", lambda _session: str(base))
    monkeypatch.setattr(pastas_module.shutil, "rmtree", lambda path: chamadas.append(path))

    with pytest.raises(ValueError, match="fora da pasta base"):
        pastas_module.eliminar_pasta_versao(
            object(),
            pasta,
            nome_esperado=seg3,
        )

    assert chamadas == []
    assert pasta.is_dir()


def test_eliminar_pasta_versao_apaga_apenas_seg3_dentro_da_base(
    tmp_path,
    monkeypatch,
) -> None:
    import app.services.producao_pastas_service as pastas_module

    base = tmp_path / "base"
    parent = (
        base
        / "2026"
        / "Encomenda de Cliente"
        / "1058_JF_VIVA"
        / "1058_01_JF_VIVA"
    )
    seg3 = "1058_01_01_JF_VIVA"
    pasta = parent / seg3
    outra_versao = parent / "1058_01_02_JF_VIVA"
    pasta.mkdir(parents=True)
    outra_versao.mkdir(parents=True)
    (pasta / "plano.cut").write_text("conteudo", encoding="utf-8")

    monkeypatch.setattr(pastas_module, "resolver_base_dir", lambda _session: str(base))

    pastas_module.eliminar_pasta_versao(
        object(),
        pasta,
        nome_esperado=seg3,
    )

    assert not pasta.exists()
    assert parent.is_dir()
    assert parent.parent.is_dir()
    assert outra_versao.is_dir()


def test_eliminar_pasta_versao_remove_pais_vazios_dentro_da_base(
    tmp_path,
    monkeypatch,
) -> None:
    import app.services.producao_pastas_service as pastas_module

    base = tmp_path / "base"
    seg1 = base / "2026" / "Encomenda de Cliente" / "1055_RIOCRIATIVO"
    seg2 = seg1 / "1055_02_RIOCRIATIVO"
    seg3 = seg2 / "1055_02_01_RIOCRIATIVO"
    seg3.mkdir(parents=True)
    (seg3 / "plano.cut").write_text("conteudo", encoding="utf-8")

    monkeypatch.setattr(pastas_module, "resolver_base_dir", lambda _session: str(base))

    pastas_module.eliminar_pasta_versao(
        object(),
        seg3,
        nome_esperado=seg3.name,
    )

    assert not seg3.exists()
    assert not seg2.exists()
    assert not seg1.exists()
    assert (base / "2026" / "Encomenda de Cliente").is_dir()


# ---- erros do servidor explicados em portugues ------------------------------
def _erro_windows(winerror: int, texto: str = "erro") -> OSError:
    exc = OSError(22, texto, None, winerror)
    if getattr(exc, "winerror", None) != winerror:  # fora do Windows
        exc.winerror = winerror
    return exc


def test_erro_1385_explica_a_conta_e_manda_abrir_pelo_atalho(monkeypatch) -> None:
    from app.services.producao_pastas_service import explicar_erro_pasta_servidor

    monkeypatch.setenv("USERNAME", "ADMIN_Bruno")
    texto = explicar_erro_pasta_servidor(
        _erro_windows(1385, "Falha de início de sessão"), r"\SERVER_LE\x\0977_02_01"
    )

    assert "1385" in texto
    assert "ADMIN_Bruno" in texto
    assert "atalho normal" in texto
    assert r"\SERVER_LE\x\0977_02_01" in texto
    assert "WinError" not in texto


def test_erro_sem_permissao_e_erro_desconhecido(monkeypatch) -> None:
    from app.services.producao_pastas_service import explicar_erro_pasta_servidor

    monkeypatch.setenv("USERNAME", "Bruno")
    sem_permissao = explicar_erro_pasta_servidor(PermissionError(13, "Acesso negado"), "P")
    assert "não tem permissão" in sem_permissao and "Bruno" in sem_permissao

    desconhecido = explicar_erro_pasta_servidor(_erro_windows(999, "coisa rara"), "P")
    assert "coisa rara" in desconhecido


def test_criar_pasta_versao_devolve_a_mensagem_explicada(monkeypatch, tmp_path) -> None:
    from pathlib import Path

    from app.services.producao_pastas_service import criar_pasta_versao

    def _recusa(self, *a, **kw):
        raise _erro_windows(1385)

    monkeypatch.setattr(Path, "mkdir", _recusa)
    with pytest.raises(OSError, match="atalho normal"):
        criar_pasta_versao(tmp_path / "0977_02_01", exist_ok=False)


def test_verificar_acesso_pastas_ok_mesmo_sem_pasta_do_ano(monkeypatch, tmp_path) -> None:
    from app.services.producao_pastas_service import verificar_acesso_pastas_servidor

    _usar_base(monkeypatch, tmp_path)
    assert verificar_acesso_pastas_servidor(None, ano="2026", tipo_pasta=None) is None

    (tmp_path / "2026" / "Encomenda de Cliente").mkdir(parents=True)
    assert verificar_acesso_pastas_servidor(None, ano="2026", tipo_pasta=None) is None


def test_verificar_acesso_pastas_sem_base_diz_que_nao_encontra(monkeypatch, tmp_path) -> None:
    from app.services.producao_pastas_service import verificar_acesso_pastas_servidor

    _usar_base(monkeypatch, tmp_path / "nao_existe")
    aviso = verificar_acesso_pastas_servidor(None, ano="2026", tipo_pasta=None)
    assert aviso and "Não foi possível encontrar" in aviso


def test_verificar_acesso_pastas_conta_recusada(monkeypatch, tmp_path) -> None:
    import app.services.producao_pastas_service as pastas_module

    _usar_base(monkeypatch, tmp_path)

    def _recusa(_caminho):
        raise _erro_windows(1385)

    monkeypatch.setattr(pastas_module.os, "scandir", _recusa)
    aviso = pastas_module.verificar_acesso_pastas_servidor(None, ano="2026", tipo_pasta=None)
    assert aviso and "1385" in aviso and "ler as pastas de produção" in aviso
