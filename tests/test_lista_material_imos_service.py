"""Tests for Lista Material IMOS Excel generation service."""

from __future__ import annotations

import base64
import json
import subprocess

import pytest

from app.db.base import Base
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models.producao import Producao
from app.repositories.system_setting_repository import SystemSettingRepository
from app.services.lista_material_imos_service import (
    TEMPLATE_FILENAME,
    ListaMaterialImosContext,
    _lista_material_imos_ps_script,
    execute_lista_material_imos,
    prepare_lista_material_imos,
)


def test_prepare_lista_material_imos_constroi_contexto(session, tmp_path) -> None:
    folder = tmp_path / "processo"
    folder.mkdir()
    base = tmp_path / "base"
    base.mkdir()
    template = base / TEMPLATE_FILENAME
    template.write_text("template", encoding="utf-8")
    session.add(
        Producao(
            id=1,
            codigo_processo="26.1134_01_01_CLIENTE",
            ano="2026",
            num_enc_phc="1134",
            versao_obra="01",
            versao_plano="01",
            pasta_servidor=str(folder),
        )
    )
    SystemSettingRepository(session).upsert_setting(
        chave="pasta_base_dados_orcamento",
        valor=str(base),
        descricao="Pasta Base Dados Orcamento",
        tipo="pasta",
        grupo="Orcamentos",
    )
    session.commit()

    context = prepare_lista_material_imos(
        session,
        processo_id=1,
        nome_enc_imos="1134_01_26_CLIENTE",
        values={"RESPONSAVEL": "Paulo", "QTD": "3"},
    )

    values = json.loads(base64.b64decode(context.values_b64).decode("utf-8"))
    assert context.processo_id == 1
    assert context.folder_path == folder
    assert context.template_path == template
    assert context.output_path == folder / "Lista_Material_1134_01_26_CLIENTE.xlsm"
    assert values == {"RESPONSAVEL": "Paulo", "QTD": "3"}


def test_prepare_lista_material_imos_valida_pasta_e_template(session, tmp_path) -> None:
    session.add(
        Producao(
            id=1,
            codigo_processo="26.1134_01_01_CLIENTE",
            ano="2026",
            num_enc_phc="1134",
            versao_obra="01",
            versao_plano="01",
            pasta_servidor=str(tmp_path / "nao_existe"),
        )
    )
    session.commit()

    with pytest.raises(ValueError, match="Pasta do processo nao encontrada"):
        prepare_lista_material_imos(
            session,
            processo_id=1,
            nome_enc_imos="1134",
            values={},
        )

    folder = tmp_path / "processo"
    folder.mkdir()
    session.get(Producao, 1).pasta_servidor = str(folder)
    SystemSettingRepository(session).upsert_setting(
        chave="pasta_base_dados_orcamento",
        valor=str(tmp_path),
    )
    session.commit()

    with pytest.raises(ValueError, match="Modelo Excel nao encontrado"):
        prepare_lista_material_imos(
            session,
            processo_id=1,
            nome_enc_imos="1134",
            values={},
        )


def test_execute_lista_material_imos_invoca_powershell(monkeypatch, tmp_path) -> None:
    capturado: dict[str, object] = {}

    def _fake_run(cmd, **kwargs):
        capturado["cmd"] = cmd
        capturado["kwargs"] = kwargs
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr("app.services.lista_material_imos_service.subprocess.run", _fake_run)
    context = ListaMaterialImosContext(
        processo_id=1,
        folder_path=tmp_path,
        template_path=tmp_path / TEMPLATE_FILENAME,
        output_path=tmp_path / "Lista_Material_TESTE.xlsm",
        values_b64="e30=",
    )

    output = execute_lista_material_imos(context, timeout_seconds=12)

    cmd = capturado["cmd"]
    assert output == context.output_path
    assert cmd[:6] == [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-STA",
    ]
    assert cmd[-3:] == [str(context.template_path), str(context.output_path), "e30="]
    assert capturado["kwargs"]["timeout"] == 12


def test_lista_material_imos_ps_script_tem_mapeamento_excel() -> None:
    script = _lista_material_imos_ps_script()

    assert "$ws.Range('B3').Value2 = [string]$v.RESPONSAVEL" in script
    assert "$ws.Range('P3').Value2 = [string]$v.ENC_PHC" in script
    assert "$wb.SaveAs($OutputPath, 52)" in script
    assert "$newLo.Name = 'Tabela_Cut_Rite'" in script
