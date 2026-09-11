import pytest
from sqlalchemy import select

from app.models.producao import Producao
from app.services import producao_service as svc
from app.services import streamlit_sql_service as st


@pytest.fixture
def origem(session, monkeypatch):
    proc = Producao(codigo_processo="26.1551_01_01_ARTIMOL", ano="2026",
                    num_enc_phc="1551", versao_obra="01", versao_plano="01",
                    nome_cliente_simplex="ARTIMOL", tipo_pasta="Encomenda de Cliente",
                    data_inicio="2026-09-10", data_entrega="2026-09-18")
    session.add(proc)
    session.commit()
    monkeypatch.setattr(svc, "listar_pastas_enc_arvore", lambda *a, **k: ("root", {}))
    monkeypatch.setattr(svc, "sugerir_proxima_versao_obra", lambda *a, **k: "02")
    monkeypatch.setattr(svc, "sugerir_proxima_versao_plano", lambda *a, **k: "02")
    return proc


def test_sugestoes_e_revalidacao_sem_pasta(session, monkeypatch, origem):
    keys = {("01", "02"), ("02", "01")}
    monkeypatch.setattr(svc, "query_modelos_versoes", lambda *a, **k: keys.copy())
    preparado = svc.preparar_nova_versao(session, processo_id=origem.id)
    assert preparado["sug_cutrite"] == ("01", "03")
    assert preparado["sug_obra"] == ("03", "01")
    assert preparado["streamlit_keys"] == keys
    # A record created after opening the dialog must still block creation.
    keys.add(("01", "03"))
    monkeypatch.setattr(svc, "criar_pasta_versao", lambda *a: pytest.fail("Não criar pasta"))
    with pytest.raises(ValueError, match="já existe no Streamlit"):
        svc.criar_nova_versao(session, processo_id=origem.id, versao_obra="01", versao_plano="03")
    assert len(session.scalars(select(Producao)).all()) == 1


def test_copia_datas(session, monkeypatch, origem):
    monkeypatch.setattr(svc, "query_modelos_versoes", lambda *a, **k: set())
    novo = svc.criar_nova_versao(session, processo_id=origem.id, versao_obra="02",
                               versao_plano="01", criar_pasta=False)
    assert novo.data_inicio == origem.data_inicio == "2026-09-10"
    assert novo.data_entrega == origem.data_entrega == "2026-09-18"


def test_pasta_criada_entretanto_nao_e_reutilizada(session, monkeypatch, origem, tmp_path):
    monkeypatch.setattr(svc, "query_modelos_versoes", lambda *a, **k: set())
    destino = tmp_path / "1551_02_01_ARTIMOL"
    destino.mkdir()
    monkeypatch.setattr(svc, "caminho_versao_para_criar", lambda *a, **k: destino)
    with pytest.raises(OSError):
        svc.criar_nova_versao(session, processo_id=origem.id, versao_obra="02", versao_plano="01")
    assert len(session.scalars(select(Producao)).all()) == 1


def test_falha_streamlit_nao_cria(session, monkeypatch, origem):
    def falhar(*a, **k):
        raise ValueError("Streamlit indisponível")
    monkeypatch.setattr(svc, "query_modelos_versoes", falhar)
    with pytest.raises(ValueError, match="indisponível"):
        svc.criar_nova_versao(session, processo_id=origem.id, versao_obra="02", versao_plano="01")
    assert len(session.scalars(select(Producao)).all()) == 1


@pytest.mark.parametrize("numero,tabela", [("01551", "dbo.CadernoEncargos"), ("_007", "dbo.CadernoEncargos_")])
def test_query_so_leitura_normaliza(monkeypatch, numero, tabela):
    monkeypatch.setattr(st, "load_streamlit_config", lambda s: {})
    monkeypatch.setattr(st, "build_connection_string", lambda c: "connection")
    queries = []
    def read(conn, query):
        queries.append(query)
        return [{"bd_modelo": "1", "bd_versao": "02"}]
    monkeypatch.setattr(st, "run_select", read)
    assert st.query_modelos_versoes(None, ano="2026", num_enc_phc=numero) == {("01", "02")}
    assert f"FROM {tabela} WHERE" in queries[0]
    assert "NOLOCK" not in queries[0]
    st.assert_select_only(queries[0])


def test_query_falhada_nao_parece_lista_vazia(monkeypatch):
    monkeypatch.setattr(st, "load_streamlit_config", lambda s: {})
    monkeypatch.setattr(st, "build_connection_string", lambda c: "connection")
    def fail(*a):
        raise RuntimeError("detalhe privado da ligação")
    monkeypatch.setattr(st, "run_select", fail)
    with pytest.raises(ValueError, match="criação foi bloqueada") as error:
        st.query_modelos_versoes(None, ano="2026", num_enc_phc="1551")
    assert "privado" not in str(error.value)


def test_aviso_streamlit_no_dialogo():
    from PySide6.QtWidgets import QApplication
    from app.ui.dialogs.nova_versao_processo_dialog import NovaVersaoProcessoDialog
    app = QApplication.instance() or QApplication([])
    dialog = NovaVersaoProcessoDialog(
        versao_obra_sug_cutrite="01", versao_plano_sug_cutrite="03",
        versao_obra_sug_obra="03", versao_plano_sug_obra="01",
        existing_keys={("01", "02")}, streamlit_keys={("01", "02")})
    dialog._apply("01", "02")
    assert "Streamlit" in dialog.warning_label.text()
    assert not dialog.ok_button.isEnabled()
    dialog._apply("01", "03")
    assert dialog.ok_button.isEnabled()
    dialog.close()
