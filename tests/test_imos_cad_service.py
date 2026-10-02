"""Abrir obras no iX CAD pelo mesmo canal do «Abrir iX CAD» do iX Organizer."""

from __future__ import annotations

import ctypes
import re
import sys
import threading
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services import imos_cad_service as svc
from app.services import imos_sql
from app.services.imos_sql import ImosConfig, NoImos

NOME = "1702_01_26_JF_VIVA"
# O comando que abriu a 1702 no iX CAD real a 02-10-2026 (teste com o Paulo).
COMANDO_REAL = r'imosopendwg "I:\Factory\Imorder\1702_01_26_JF_VIVA\1702_01_26_JF_VIVA.dwg"'


def _cfg(**overrides) -> ImosConfig:
    cfg: ImosConfig = {
        "server": r"SERVER_LE\SERVER_LE",
        "database": "imos_le",
        "user": "martelo_readonly",
        "password": "x",
        "trusted": False,
        "trust_server_certificate": True,
    }
    cfg.update(overrides)  # type: ignore[typeddict-item]
    return cfg


def _no(tipo: int = 173, nome: str = NOME, dir_id: int = 7727) -> NoImos:
    return NoImos(dir_id=dir_id, nome=nome, tipo=tipo, parent_id=6626)


# --------------------------------------------------------------------------
# Consulta ao iMos (só leitura)
# --------------------------------------------------------------------------


def _imos_falso(monkeypatch, linhas: list[dict]) -> list[str]:
    queries: list[str] = []

    def _run(_conn: str, query: str) -> list[dict]:
        imos_sql.assert_select_only(query)
        queries.append(query)
        return linhas

    monkeypatch.setattr(imos_sql, "run_select", _run)
    return queries


def test_procura_por_dir_id_ou_nome_numa_so_consulta_de_leitura(monkeypatch) -> None:
    queries = _imos_falso(
        monkeypatch, [{"DIR_ID": 7727, "NAME": NOME, "TYPE": 173, "PARENT_ID": 6626}]
    )

    no = imos_sql.procurar_encomenda_para_abrir(_cfg(), NOME, dir_id=7727)

    assert no == _no()
    assert len(queries) == 1
    assert "TYPE IN (173, 673, 999987)" in queries[0]
    assert f"NAME = N'{NOME}' OR DIR_ID = 7727" in queries[0]


def test_dir_id_gravado_vale_mesmo_com_o_nome_mudado_no_organizer(monkeypatch) -> None:
    _imos_falso(
        monkeypatch,
        [{"DIR_ID": 7727, "NAME": "1702_RENOMEADA", "TYPE": 173, "PARENT_ID": 6626}],
    )

    no = imos_sql.procurar_encomenda_para_abrir(_cfg(), NOME, dir_id=7727)

    assert no is not None and no.nome == "1702_RENOMEADA"


def test_encomenda_feita_a_mao_no_organizer_encontra_se_pelo_nome(monkeypatch) -> None:
    queries = _imos_falso(
        monkeypatch,
        [{"DIR_ID": 9001, "NAME": NOME.lower(), "TYPE": 999987, "PARENT_ID": 6626}],
    )

    no = imos_sql.procurar_encomenda_para_abrir(_cfg(), NOME, dir_id=None)

    assert no is not None and no.dir_id == 9001 and no.tipo == 999987
    assert "DIR_ID =" not in queries[0]


def test_encomenda_inexistente_devolve_none(monkeypatch) -> None:
    _imos_falso(monkeypatch, [])

    assert imos_sql.procurar_encomenda_para_abrir(_cfg(), NOME, dir_id=7727) is None


def test_nome_com_plica_e_recusado_antes_de_chegar_ao_sql(monkeypatch) -> None:
    queries = _imos_falso(monkeypatch, [])

    with pytest.raises(ValueError):
        imos_sql.procurar_encomenda_para_abrir(_cfg(), "X' OR 1=1 --", dir_id=None)
    assert queries == []


# --------------------------------------------------------------------------
# Instalação do iX CAD
# --------------------------------------------------------------------------

_REGISTO = [
    (
        16,
        {
            "IMOS": r"C:\Program Files\imos AG\iX CAD 2023",
            "ACADPATH": r"C:\Program Files\imos AG\iX CAD 2023\CAD-Kernel\imos.exe",
            "IMORDERPATH": r"I:\Factory\Imorder",
        },
    ),
    (
        17,
        {
            "IMOS": r"C:\Program Files\imos AG\iX CAD 2025",
            "ACADPATH": r"C:\Program Files\imos AG\iX CAD 2025\CAD-Kernel\imos.exe",
            "IMORDERPATH": r"I:\Factory\Imorder",
        },
    ),
]


def test_usa_a_versao_mais_recente_instalada() -> None:
    inst = svc.localizar_instalacao(ler=lambda: _REGISTO, existe=lambda _p: True)

    assert inst is not None
    assert inst.versao == 17
    assert inst.executavel == Path(r"C:\Program Files\imos AG\iX CAD 2025\CAD-Kernel\imos.exe")
    # ACADWORKDIR do Organizer: a pasta BIN da instalação.
    assert inst.pasta_trabalho == Path(r"C:\Program Files\imos AG\iX CAD 2025\BIN")
    assert inst.pasta_imorder == r"I:\Factory\Imorder"


def test_salta_versao_registada_cujo_programa_ja_nao_existe() -> None:
    inst = svc.localizar_instalacao(ler=lambda: _REGISTO, existe=lambda p: "2023" in p)

    assert inst is not None and inst.versao == 16


def test_sem_ix_cad_instalado() -> None:
    assert svc.localizar_instalacao(ler=lambda: [], existe=lambda _p: True) is None


def test_pasta_dos_desenhos_vem_primeiro_do_ix_cad_deste_pc() -> None:
    inst = svc.localizar_instalacao(ler=lambda: _REGISTO, existe=lambda _p: True)
    sem_pasta = svc.InstalacaoIxCad(17, Path("x.exe"), Path("BIN"), "")

    assert svc.pasta_imorder_a_usar(inst, r"Z:\Outra") == r"I:\Factory\Imorder"
    assert svc.pasta_imorder_a_usar(sem_pasta, r"Z:\Outra") == r"Z:\Outra"
    assert svc.pasta_imorder_a_usar(None, "") == svc.DEFAULT_PASTA_IMORDER


# --------------------------------------------------------------------------
# O pedido
# --------------------------------------------------------------------------


def test_comando_e_o_mesmo_do_organizer() -> None:
    desenho = svc.caminho_desenho(r"I:\Factory\Imorder", NOME)

    assert svc.comando_abrir(desenho) == COMANDO_REAL


def test_mensagem_do_canal_em_utf16_com_o_formato_do_organizer() -> None:
    dados = svc.mensagem_canal(COMANDO_REAL)

    assert dados.endswith(b"\0\0")
    assert dados[:-2].decode("utf-16-le") == "<IMOS_COMMAND>" + COMANDO_REAL


def test_mensagem_maior_que_o_canal_e_recusada() -> None:
    with pytest.raises(svc.ErroIxCad):
        svc.mensagem_canal("x" * svc.TAMANHO_CANAL)


def test_le_quem_tem_a_obra_aberta_no_dwl(tmp_path) -> None:
    desenho = tmp_path / f"{NOME}.DWG"
    desenho.with_suffix(".dwl").write_bytes(
        b"Paulo Catarino\r\nPAULOCATARINO \r\n2 de outubro de 2026  09:15:49\r\n"
        b"\\\\SERVER_LE\\Homag_iX\r\n"
    )

    tranca = svc.ler_tranca(desenho)

    assert tranca == svc.TrancaDesenho(
        "Paulo Catarino", "PAULOCATARINO", "2 de outubro de 2026  09:15:49"
    )


def test_sem_dwl_nao_ha_tranca(tmp_path) -> None:
    assert svc.ler_tranca(tmp_path / f"{NOME}.dwg") is None


# --------------------------------------------------------------------------
# preparar_abertura
# --------------------------------------------------------------------------


def _imorder(tmp_path: Path, *, com_desenho: bool = True, dwl: bytes | None = None) -> Path:
    pasta = tmp_path / NOME
    pasta.mkdir()
    if com_desenho:
        (pasta / f"{NOME}.DWG").write_bytes(b"AC1032")
    if dwl is not None:
        (pasta / f"{NOME}.dwl").write_bytes(dwl)
    return tmp_path


def _preparar(tmp_path, *, no=None, abertos=frozenset(), cfg=None, nome=NOME, dir_id=7727, **kw):
    return svc.preparar_abertura(
        cfg or _cfg(),
        nome,
        dir_id=dir_id,
        pasta_imorder=str(tmp_path),
        procurar=lambda _cfg, _nome, dir_id=None: no if no is not None else _no(),
        abertos=lambda: abertos,
        computador="PAULOCATARINO",
        **kw,
    )


def test_plano_normal(tmp_path) -> None:
    plano = _preparar(_imorder(tmp_path))

    assert plano.nome == NOME
    assert plano.desenho_existe
    assert not plano.ja_aberta_neste_pc
    assert plano.tranca_de_outro_posto is None
    assert plano.avisos() == []
    assert plano.comando == svc.comando_abrir(tmp_path / NOME / f"{NOME}.dwg")


def test_encomenda_que_nao_existe_no_imos_nao_chega_ao_ix_cad(tmp_path) -> None:
    with pytest.raises(svc.ErroIxCad, match="não existe no iX Organizer"):
        svc.preparar_abertura(
            _cfg(),
            NOME,
            dir_id=None,
            pasta_imorder=str(_imorder(tmp_path)),
            procurar=lambda *_a, **_k: None,
            abertos=lambda: frozenset(),
        )


def test_obra_sem_nome_enc_imos(tmp_path) -> None:
    with pytest.raises(svc.ErroIxCad, match="Nome Enc IMOS IX"):
        _preparar(tmp_path, nome="", dir_id=None)


def test_sem_ligacao_ao_imos_nao_se_abre_as_cegas(tmp_path) -> None:
    with pytest.raises(svc.ErroIxCad, match="Ligação iMos"):
        _preparar(tmp_path, cfg=_cfg(server=""))


def test_pasta_da_encomenda_em_falta(tmp_path) -> None:
    with pytest.raises(svc.ErroIxCad, match="pasta dela não foi encontrada"):
        _preparar(tmp_path)


def test_obra_ja_aberta_neste_pc(tmp_path) -> None:
    pasta = _imorder(tmp_path, dwl=b"Paulo Catarino\r\nPAULOCATARINO\r\nhoje\r\n")

    plano = _preparar(pasta, abertos=frozenset({f"{NOME}.DWG", "DRAWING1.DWG"}))

    assert plano.ja_aberta_neste_pc
    assert plano.tranca_de_outro_posto is None


def test_aberta_noutro_pc_avisa_quem_a_tem(tmp_path) -> None:
    pasta = _imorder(tmp_path, dwl=b"Andreia\r\nDESKTOP-LH00VUT \r\n2 de outubro de 2026  10:12:01\r\n")

    plano = _preparar(pasta)

    assert plano.tranca_de_outro_posto is not None
    assert any("Andreia no PC DESKTOP-LH00VUT" in aviso for aviso in plano.avisos())


def test_dwl_que_ficou_deste_pc_nao_assusta_ninguem(tmp_path) -> None:
    pasta = _imorder(tmp_path, dwl=b"Paulo Catarino\r\npaulocatarino\r\nontem\r\n")

    assert _preparar(pasta).avisos() == []


def test_avisos_do_organizer_e_obra_sem_desenho(tmp_path) -> None:
    pasta = _imorder(tmp_path, com_desenho=False)

    referencia = _preparar(pasta, no=_no(tipo=673)).avisos()
    em_producao = _preparar(pasta, no=_no(tipo=999987)).avisos()

    assert any("referência" in aviso for aviso in referencia)
    assert any("em produção" in aviso for aviso in em_producao)
    assert any("ainda não tem desenho" in aviso for aviso in referencia)


# --------------------------------------------------------------------------
# O canal, com objetos verdadeiros do Windows mas com outro nome
# --------------------------------------------------------------------------


@pytest.fixture
def canal_falso(monkeypatch):
    """Um «iX CAD» de mentira: o mesmo evento e memória, com um nome só do teste."""
    if sys.platform != "win32":
        pytest.skip("O canal do iX CAD só existe no Windows.")
    from ctypes import wintypes

    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateEventW.restype = wintypes.HANDLE
    k.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
    k.CreateFileMappingW.restype = wintypes.HANDLE
    k.CreateFileMappingW.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPCWSTR,
    ]
    k.MapViewOfFile.restype = ctypes.c_void_p
    k.MapViewOfFile.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_size_t,
    ]
    k.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
    k.WaitForSingleObject.restype = wintypes.DWORD
    k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k.CloseHandle.argtypes = [wintypes.HANDLE]

    nome = f"MARTELO_TESTE_IXCAD_{uuid.uuid4().hex}"
    monkeypatch.setattr(svc, "CANAL", nome)
    monkeypatch.setattr(svc, "EVENTO_CANAL", nome + "_LOCK")
    monkeypatch.setattr(svc, "PAUSA_EVENTO_S", 0.3)
    assert svc.estado_canal() == svc.ESTADO_CANAL_FECHADO

    evento = k.CreateEventW(None, True, False, nome + "_LOCK")
    mapa = k.CreateFileMappingW(wintypes.HANDLE(-1), None, 0x04, 0, svc.TAMANHO_CANAL, nome)
    vista = k.MapViewOfFile(mapa, 0x0002 | 0x0004, 0, 0, svc.TAMANHO_CANAL)
    assert evento and mapa and vista
    try:
        yield SimpleNamespace(k=k, evento=evento, vista=vista)
    finally:
        k.UnmapViewOfFile(vista)
        k.CloseHandle(mapa)
        k.CloseHandle(evento)


def test_canal_fechado_quando_o_ix_cad_nao_esta_aberto(monkeypatch) -> None:
    monkeypatch.setattr(svc, "EVENTO_CANAL", f"MARTELO_TESTE_{uuid.uuid4().hex}_LOCK")

    assert svc.estado_canal() == svc.ESTADO_CANAL_FECHADO


def test_enviar_escreve_o_pedido_e_acorda_o_ix_cad(canal_falso) -> None:
    lido: dict[str, object] = {}

    def _servidor():
        lido["acordou"] = canal_falso.k.WaitForSingleObject(canal_falso.evento, 5000) == 0
        lido["texto"] = ctypes.wstring_at(canal_falso.vista)

    servidor = threading.Thread(target=_servidor)
    servidor.start()
    assert svc.estado_canal() == svc.ESTADO_CANAL_ATIVO

    svc.enviar_comando(COMANDO_REAL)
    servidor.join(5)

    assert lido == {"acordou": True, "texto": "<IMOS_COMMAND>" + COMANDO_REAL}
    # Como o Organizer: o evento fica desligado depois do toque (258 = WAIT_TIMEOUT).
    assert canal_falso.k.WaitForSingleObject(canal_falso.evento, 0) == 258


def test_nao_escreve_por_cima_de_um_pedido_por_ler(canal_falso) -> None:
    anterior = "<IMOS_COMMAND>outro".encode("utf-16-le")
    ctypes.memmove(canal_falso.vista, anterior, len(anterior))

    with pytest.raises(svc.ErroIxCad, match="ainda não leu"):
        svc.enviar_comando(COMANDO_REAL)

    assert ctypes.string_at(canal_falso.vista, len(anterior)) == anterior
    assert canal_falso.k.WaitForSingleObject(canal_falso.evento, 0) == 258


def test_enviar_com_o_ix_cad_fechado_explica(monkeypatch) -> None:
    monkeypatch.setattr(svc, "EVENTO_CANAL", f"MARTELO_TESTE_{uuid.uuid4().hex}_LOCK")

    with pytest.raises(svc.ErroIxCad, match="não está aberto"):
        svc.enviar_comando(COMANDO_REAL)


def test_servico_nao_tem_escrita_na_base_do_imos() -> None:
    """Abrir no iX CAD só lê o iMos: nada de imos_escrita nem SQL de escrita."""
    fonte = Path(svc.__file__).read_text(encoding="utf-8")

    assert "imos_escrita" not in fonte
    assert not re.search(r"\b(INSERT|UPDATE|DELETE)\b", fonte)
