from __future__ import annotations

from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20260821_92_grants_lista_material_assistente.py"
)


def test_migracao_atualiza_perfis_mysql_das_tabelas_novas() -> None:
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'down_revision: str | Sequence[str] | None = "20260821_91"' in source
    assert "information_schema.routines" in source
    assert "martelo_aplicar_grants" in source
    assert 'CALL martelo_aplicar_grants()' in source
    assert 'connection.dialect.name != "mysql"' in source
