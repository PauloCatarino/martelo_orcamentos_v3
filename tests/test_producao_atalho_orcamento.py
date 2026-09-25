"""Atalho da pasta do orçamento na pasta principal da obra (produção)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import app.services.producao_atalho_orcamento_service as svc


def _processo(**campos):
    base = {
        "num_enc_phc": "1597",
        "tipo_pasta": "Encomenda de Cliente",
        "orcamento_id": None,
        "num_orcamento": "260906",
    }
    base.update(campos)
    return SimpleNamespace(**base)


def _arvore(tmp_path: Path) -> tuple[Path, Path]:
    versao = tmp_path / "Dep_Producao/2026/Encomenda de Cliente/1597_CICOMOL/1597_01_CICOMOL/1597_01_01_CICOMOL"
    versao.mkdir(parents=True)
    orcamento = tmp_path / "Dep._Orcamentos/2026/260906_CICOMOL"
    orcamento.mkdir(parents=True)
    return versao, orcamento


def test_so_encomendas_de_cliente_levam_atalho() -> None:
    assert svc.e_encomenda_de_cliente("1597", "Encomenda de Cliente")
    assert not svc.e_encomenda_de_cliente("_111", "Encomenda de Cliente Final")
    assert not svc.e_encomenda_de_cliente("_111")
    assert not svc.e_encomenda_de_cliente("1597", "Encomenda de Cliente Final")
    assert not svc.e_encomenda_de_cliente("")


def test_nome_e_pasta_principal() -> None:
    assert svc.nome_atalho(Path("X/260906_CICOMOL")) == "260906_CICOMOL - Atalho.lnk"
    versao = Path("E/1597_CICOMOL/1597_01_CICOMOL/1597_01_01_CICOMOL")
    assert svc.pasta_principal_da_obra(versao) == Path("E/1597_CICOMOL")


def test_cria_o_atalho_na_pasta_principal_da_obra(tmp_path, monkeypatch) -> None:
    versao, orcamento = _arvore(tmp_path)
    monkeypatch.setattr(svc, "pasta_do_orcamento", lambda _s, _p: orcamento)
    criados: list[tuple[Path, Path]] = []

    def criar(atalho: Path, destino: Path) -> None:
        criados.append((atalho, destino))
        atalho.write_text("lnk")

    atalho = svc.criar_atalho_orcamento(None, _processo(), versao, criar_lnk=criar)

    esperado = tmp_path / "Dep_Producao/2026/Encomenda de Cliente/1597_CICOMOL/260906_CICOMOL - Atalho.lnk"
    assert atalho == esperado
    assert criados == [(esperado, orcamento)]

    # Segunda vez (nova versão da obra): já existe, não se mexe.
    assert svc.criar_atalho_orcamento(None, _processo(), versao, criar_lnk=criar) == esperado
    assert len(criados) == 1


def test_encomenda_final_e_orcamento_desconhecido_nao_criam_nada(tmp_path, monkeypatch) -> None:
    versao, orcamento = _arvore(tmp_path)
    chamadas: list = []
    criar = lambda a, d: chamadas.append(a)  # noqa: E731

    monkeypatch.setattr(svc, "pasta_do_orcamento", lambda _s, _p: orcamento)
    assert svc.criar_atalho_orcamento(
        None, _processo(num_enc_phc="_111", tipo_pasta="Encomenda de Cliente Final"),
        versao, criar_lnk=criar,
    ) is None

    monkeypatch.setattr(svc, "pasta_do_orcamento", lambda _s, _p: None)
    assert svc.criar_atalho_orcamento(None, _processo(), versao, criar_lnk=criar) is None
    assert chamadas == []


def test_um_erro_no_atalho_nunca_rebenta(tmp_path, monkeypatch) -> None:
    versao, orcamento = _arvore(tmp_path)
    monkeypatch.setattr(svc, "pasta_do_orcamento", lambda _s, _p: orcamento)

    def falha(_a, _d):
        raise OSError("sem permissão")

    assert svc.criar_atalho_orcamento(None, _processo(), versao, criar_lnk=falha) is None


def test_pasta_do_orcamento_pelo_numero_quando_nao_ha_ligacao(monkeypatch) -> None:
    pedidos: list[dict] = []

    def resolver(_session, **kw):
        pedidos.append(kw)
        return Path("Orc/2026/260906_CICOMOL")

    monkeypatch.setattr(svc, "resolver_pasta_orcamento", resolver)
    pasta = svc.pasta_do_orcamento(None, _processo())
    assert pasta == Path("Orc/2026/260906_CICOMOL")
    assert pedidos == [{"ano": 2026, "num_orcamento": "260906"}]


def test_nao_duplica_o_atalho_que_outra_ferramenta_ja_criou(tmp_path, monkeypatch) -> None:
    versao, orcamento = _arvore(tmp_path)
    monkeypatch.setattr(svc, "pasta_do_orcamento", lambda _s, _p: orcamento)
    principal = svc.pasta_principal_da_obra(versao)
    # Como na obra 1538: a pasta nasceu noutra ferramenta, com este atalho.
    existente = principal / "ATALHO_260906_CICOMOL.lnk"
    existente.write_text("lnk")
    (principal / "ATALHO_2609061_OUTRA.lnk").write_text("lnk")  # outro nº
    criados: list[Path] = []

    atalho = svc.criar_atalho_orcamento(
        None, _processo(), versao, criar_lnk=lambda a, _d: criados.append(a)
    )

    assert atalho == existente
    assert criados == []


def test_atalho_de_outro_orcamento_nao_conta(tmp_path, monkeypatch) -> None:
    versao, orcamento = _arvore(tmp_path)
    monkeypatch.setattr(svc, "pasta_do_orcamento", lambda _s, _p: orcamento)
    principal = svc.pasta_principal_da_obra(versao)
    (principal / "ATALHO_2609061_OUTRA.lnk").write_text("lnk")
    criados: list[Path] = []

    svc.criar_atalho_orcamento(
        None, _processo(), versao, criar_lnk=lambda a, _d: criados.append(a)
    )

    assert criados == [principal / "260906_CICOMOL - Atalho.lnk"]
