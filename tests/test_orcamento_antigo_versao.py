"""Orçamento antigo (do V2) que entra no V3 com a versão seguinte (19-10-2026).

Caso real: o 260186 (INNERE) já tem as versões 01 a 05 no servidor, feitas no
Martelo V2. Registado no V3 como antigo, tem de entrar como 06 e gravar os
ficheiros em ``260186_INNERE/06`` — nunca por cima das pastas do V2.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import Cliente, Orcamento, OrcamentoVersao, SystemSetting
from app.repositories.orcamento_repository import OrcamentoRepository
from app.services.orcamento_delete_service import eliminar_versao_completo
from app.services.orcamento_export_service import OrcamentoExportService


def _pasta_do_v2(base: Path) -> Path:
    """``base/2026/260186_INNERE`` com as versões 01 a 05 do V2, com ficheiros."""
    mae = base / "2026" / "260186_INNERE"
    for versao in ("01", "02", "03", "04", "05"):
        (mae / versao).mkdir(parents=True)
        (mae / versao / f"260186_{versao}.pdf").write_text("v2", encoding="utf-8")
    return mae


def _registar_antigo(session: Session, mae: Path, *, numero_versao: int = 6):
    cliente = Cliente(nome="INNERE RUI VIEGAS", nome_simplex="INNERE", is_temporary=True)
    session.add(cliente)
    session.flush()
    return OrcamentoRepository(session).create_orcamento_com_versao_01(
        ano=2026,
        num_orcamento="260186",
        cliente_id=cliente.id,
        obra="",
        descricao=None,
        localizacao=None,
        ref_cliente=None,
        created_by_id=None,
        pasta_manual=mae.as_posix(),
        pasta_manual_por_versao=True,
        numero_versao=numero_versao,
    )


def _definir_pasta_base(session: Session, base: Path) -> None:
    session.add(SystemSetting(chave="pasta_base_orcamentos", valor=str(base)))
    session.flush()


def test_antigo_entra_com_a_versao_escolhida(session, tmp_path) -> None:
    mae = _pasta_do_v2(tmp_path)

    criado = _registar_antigo(session, mae)

    assert criado.numero_versao == 6
    assert criado.codigo_versao == "260186_06"
    resumo = OrcamentoRepository(session).get_orcamento_by_versao_id(
        criado.orcamento_versao_id
    )
    assert resumo.numero_versao == 6
    assert resumo.pasta_manual_por_versao is True


def test_antigo_grava_na_subpasta_da_versao(session, tmp_path) -> None:
    mae = _pasta_do_v2(tmp_path)
    criado = _registar_antigo(session, mae)

    pasta = OrcamentoExportService(session).resolver_pasta_versao(
        criado.orcamento_versao_id, criar=True
    )

    assert pasta == mae / "06"
    assert pasta.is_dir()
    # As versões do V2 ficam como estavam.
    assert (mae / "05" / "260186_05.pdf").exists()


def test_duplicar_versao_do_antigo_da_a_07_na_sua_pasta(session, tmp_path) -> None:
    mae = _pasta_do_v2(tmp_path)
    criado = _registar_antigo(session, mae)

    nova = OrcamentoRepository(session).criar_nova_versao(criado.orcamento_versao_id)

    assert nova.numero_versao == 7
    assert nova.codigo_versao == "260186_07"
    assert OrcamentoExportService(session).resolver_pasta_versao(
        nova.orcamento_versao_id, criar=False
    ) == mae / "07"


def test_pasta_do_orcamento_continua_a_ser_a_mae(session, tmp_path) -> None:
    mae = _pasta_do_v2(tmp_path)
    criado = _registar_antigo(session, mae)

    assert (
        OrcamentoExportService(session).pasta_orcamento_atual(
            criado.orcamento_versao_id
        )
        == Path(mae.as_posix())
    )


def test_eliminar_ultima_versao_do_antigo_so_apaga_a_subpasta(
    session, tmp_path
) -> None:
    base = tmp_path / "orcamentos"
    mae = _pasta_do_v2(base)
    _definir_pasta_base(session, base)
    criado = _registar_antigo(session, mae)
    (mae / "06").mkdir()
    (mae / "06" / "260186_06.pdf").write_text("v3", encoding="utf-8")

    servico = OrcamentoExportService(session)
    assert servico.pasta_a_eliminar(
        criado.orcamento_versao_id, remove_orcamento=True
    ) == mae / "06"

    eliminar_versao_completo(
        session,
        orcamento_versao_id=criado.orcamento_versao_id,
        apagar_registo=True,
        apagar_pasta=True,
    )

    assert not (mae / "06").exists()
    # A pasta-mãe e as versões do V2 nunca se apagam com o V3.
    for versao in ("01", "02", "03", "04", "05"):
        assert (mae / versao / f"260186_{versao}.pdf").exists()
    assert session.get(Orcamento, criado.orcamento_id) is None


def test_antigos_ja_registados_continuam_na_pasta_escolhida(
    session, tmp_path
) -> None:
    """Os 6 registados antes de 19-10-2026 ficam como estão (decisão do Paulo)."""
    pasta = tmp_path / "2026" / "260770_PACE"
    pasta.mkdir(parents=True)
    cliente = Cliente(nome="PACE", nome_simplex="PACE", is_temporary=True)
    session.add(cliente)
    session.flush()
    orcamento = Orcamento(
        ano=2026,
        num_orcamento="260770",
        cliente_id=cliente.id,
        pasta_manual=str(pasta),
    )
    session.add(orcamento)
    session.flush()
    versao = OrcamentoVersao(
        orcamento_id=orcamento.id,
        numero_versao=2,
        codigo_versao="260770_02",
        estado="Enviado",
    )
    session.add(versao)
    session.flush()

    servico = OrcamentoExportService(session)

    assert orcamento.pasta_manual_por_versao is False
    assert servico.resolver_pasta_versao(versao.id, criar=False) == pasta
    assert servico.pasta_a_eliminar(versao.id, remove_orcamento=True) == pasta
