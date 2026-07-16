"""Testes do guarda anti-eliminacao do projeto (.claude/hooks/guard_projeto.py).

O guarda corre como hook PreToolUse e impede que a IA apague dados ou mexa em
configuracao critica sem o utilizador saber. Estes testes garantem que:
  - o que e' destrutivo continua a ser apanhado;
  - o que e' legitimo (SELECT, upgrade, pytest) nao e' bloqueado;
  - mencionar uma operacao perigosa numa mensagem de commit nao a bloqueia,
    mas tambem nao serve de esconderijo para a executar.
"""

import importlib.util
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
GUARDA = RAIZ / ".claude" / "hooks" / "guard_projeto.py"


def _carregar():
    spec = importlib.util.spec_from_file_location("guard_projeto", GUARDA)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


guard = _carregar()


def _decidir(tool_input):
    decisao, _motivos = guard._decidir({"tool_input": tool_input})
    return decisao


def test_guarda_existe():
    assert GUARDA.is_file(), "o hook guard_projeto.py tem de acompanhar o repositorio"


@pytest.mark.parametrize(
    "comando",
    [
        "alembic downgrade base",
        'git commit -m "ok" && alembic downgrade base',
        'git commit -m "$(alembic downgrade base)"',  # substituicao executa mesmo
        'Invoke-Sqlcmd -Query "DELETE FROM dbo.CL"',  # PHC e' so-leitura
        'sqlcmd -Q "UPDATE dbo.CL SET nome=1"',
    ],
)
def test_comandos_catastroficos_sao_bloqueados(comando):
    assert _decidir({"command": comando}) == "deny"


# A excecao das mensagens de commit (ver limpar_mensagens_git) nao pode servir
# de esconderijo. Aqui o heredoc alimenta o sh, nao o git: o commit e' disfarce.
@pytest.mark.parametrize(
    "comando",
    [
        'git commit -m "ok"; sh <<\'EOF\'\nalembic downgrade base\nEOF',
        'git commit -m "ok" | sh <<\'EOF\'\nalembic downgrade base\nEOF',
        "git commit -F - <<EOF\n$(alembic downgrade base)\nEOF",  # heredoc sem plicas expande
    ],
)
def test_excecao_da_mensagem_nao_e_esconderijo(comando):
    assert _decidir({"command": comando}) == "deny"


@pytest.mark.parametrize(
    "comando",
    [
        "alembic downgrade -1",
        "alembic downgrade abc123",
    ],
)
def test_comandos_destrutivos_pedem_confirmacao(comando):
    assert _decidir({"command": comando}) == "ask"


@pytest.mark.parametrize(
    "comando",
    [
        "alembic upgrade head",
        'Invoke-Sqlcmd -Query "SELECT * FROM dbo.CL"',  # PHC a ler: permitido
        "python -m pytest -q",
        "git add -A",
        'git commit -m "ajusta margens"',
        # mencionar a operacao perigosa a descreve-la, nao a executa
        'git commit -m "protege contra alembic downgrade base e escrita no PHC"',
    ],
)
def test_comandos_legitimos_passam(comando):
    assert _decidir({"command": comando}) is None


@pytest.mark.parametrize(
    "caminho, conteudo",
    [
        ("alembic/versions/abc_x.py", "def downgrade():\n    op.drop_table('orcamentos')"),
        ("alembic/versions/abc_x.py", "op.drop_column('orcamentos', 'total')"),
        ("migrations/v2_to_v3/z.py", "op.execute('TRUNCATE TABLE clientes')"),
        (".env", "DB_USER=martelo_v3"),
        ("alembic.ini", "[alembic]"),
    ],
)
def test_ficheiros_e_migracoes_de_risco_pedem_confirmacao(caminho, conteudo):
    assert _decidir({"file_path": str(RAIZ / caminho), "content": conteudo}) == "ask"


@pytest.mark.parametrize(
    "caminho, conteudo",
    [
        ("alembic/versions/abc_x.py", "op.create_table('novo')"),
        ("alembic/versions/abc_x.py", "op.add_column('orcamentos', sa.Column('x'))"),
        ("app/services/orcamento_service.py", "def calcular_total():\n    return 0"),
    ],
)
def test_alteracoes_seguras_passam(caminho, conteudo):
    assert _decidir({"file_path": str(RAIZ / caminho), "content": conteudo}) is None
