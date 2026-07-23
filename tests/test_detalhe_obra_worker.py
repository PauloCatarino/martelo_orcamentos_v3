"""Tests for the background worker that reads the file server."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

import app.ui.helpers.detalhe_obra_worker as worker_mod
from app.ui.helpers.detalhe_obra_worker import (
    DetalheObraResolvido,
    DetalheObraWorker,
)
from app.models.producao import Producao


@pytest.fixture(scope="module", autouse=True)
def _app():
    yield QApplication.instance() or QApplication([])


@pytest.fixture()
def obra(session):
    processo = Producao(
        codigo_processo="26.1134_01_01_JF_VIVA",
        ano="2026",
        num_enc_phc="1134",
        versao_obra="01",
        versao_plano="01",
        estado="Desenho",
        nome_cliente="MÓVEIS J.F. VIVA",
        nome_cliente_simplex="JF_VIVA",
        num_orcamento="260618",
        versao_orc="01",
    )
    session.add(processo)
    session.commit()
    return processo


@pytest.fixture()
def worker_com_sessao(monkeypatch, session):
    """Point the worker at the test session instead of the real database."""

    class SessaoFalsa:
        def __enter__(self):
            return session

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(worker_mod, "SessionLocal", lambda: SessaoFalsa())
    return DetalheObraWorker()


def _resolver(worker) -> DetalheObraResolvido:
    resultados = []
    worker.resolvido.connect(resultados.append)
    worker.resolver(1, 1)
    return resultados[-1]


def test_resolve_pastas_e_imagem(monkeypatch, worker_com_sessao, obra, tmp_path):
    imagem = tmp_path / "obra.png"
    QImage(4, 4, QImage.Format.Format_RGB32).save(str(imagem))
    pasta_obra = tmp_path / "obra"
    pasta_obra.mkdir()
    pasta_orc = tmp_path / "orcamento"
    pasta_orc.mkdir()

    monkeypatch.setattr(
        worker_mod, "caminho_versao_de_processo", lambda _s, _p: pasta_obra
    )
    monkeypatch.setattr(
        worker_mod, "resolver_pasta_orcamento", lambda _s, **_k: pasta_orc
    )
    monkeypatch.setattr(
        worker_mod, "resolver_imagem_imos", lambda _s, **_k: imagem
    )

    resultado = _resolver(worker_com_sessao)

    assert resultado.processo_id == 1
    assert resultado.pasta_obra == str(pasta_obra)
    assert resultado.pasta_orcamento == str(pasta_orc)
    assert resultado.imagem_path == str(imagem)
    assert resultado.tem_imagem is True
    assert resultado.erros == []


def test_sem_imagem_e_sem_pasta_devolve_aviso(monkeypatch, worker_com_sessao, obra):
    monkeypatch.setattr(
        worker_mod, "caminho_versao_de_processo", lambda _s, _p: Path("Z:/nao/existe")
    )
    monkeypatch.setattr(worker_mod, "resolver_pasta_orcamento", lambda _s, **_k: None)
    monkeypatch.setattr(worker_mod, "resolver_imagem_imos", lambda _s, **_k: None)

    resultado = _resolver(worker_com_sessao)

    assert resultado.tem_imagem is False
    assert resultado.imagem_aviso == "Sem imagem IMOS (sem pasta da obra)"
    assert resultado.pasta_orcamento == ""


def test_imagem_apontada_mas_inexistente(monkeypatch, worker_com_sessao, obra, tmp_path):
    monkeypatch.setattr(
        worker_mod, "caminho_versao_de_processo", lambda _s, _p: tmp_path
    )
    monkeypatch.setattr(worker_mod, "resolver_pasta_orcamento", lambda _s, **_k: None)
    monkeypatch.setattr(
        worker_mod, "resolver_imagem_imos", lambda _s, **_k: tmp_path / "nao_ha.png"
    )

    resultado = _resolver(worker_com_sessao)

    assert resultado.tem_imagem is False
    assert resultado.imagem_aviso == "Imagem não encontrada"


def test_erro_no_servidor_nao_rebenta_e_e_reportado(
    monkeypatch, worker_com_sessao, obra
):
    def explode(*_args, **_kwargs):
        raise OSError("servidor inacessível")

    monkeypatch.setattr(worker_mod, "caminho_versao_de_processo", explode)
    monkeypatch.setattr(worker_mod, "resolver_pasta_orcamento", lambda _s, **_k: None)
    monkeypatch.setattr(worker_mod, "resolver_imagem_imos", explode)

    resultado = _resolver(worker_com_sessao)

    assert any("servidor inacessível" in erro for erro in resultado.erros)
    assert resultado.tem_imagem is False


def test_obra_inexistente(monkeypatch, worker_com_sessao):
    resultados = []
    worker_com_sessao.resolvido.connect(resultados.append)

    worker_com_sessao.resolver(1, 999)

    assert resultados[-1].imagem_aviso == "Obra já não existe."
