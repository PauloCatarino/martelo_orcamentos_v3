#!/usr/bin/env python3
"""Guarda especifico do Martelo_Orcamentos_V3.

Corre como hook PreToolUse, ANTES da ferramenta ser executada. Complementa o
guarda global (~/.claude/hooks/guard_destructive.py), que trata do sistema de
ficheiros e do SQL generico. Aqui ficam os riscos proprios deste projeto:

  1. Alembic a apagar tabelas/colunas da BD martelo_orcamentos_v3
  2. Escrita em ficheiros criticos de configuracao (.env, alembic.ini)
  3. Escrita no PHC, que por regra do Paulo e' de SO-LEITURA

Nunca escreve "allow": isso desligaria as permissoes normais.
"""

import json
import re
import sys

DENY = "deny"
ASK = "ask"

# --- Comandos (Bash / PowerShell) ---
CMD_RULES = [
    (r"\balembic\s+downgrade\s+base\b", DENY,
     "alembic downgrade base desfaz TODAS as migracoes e destroi a base de dados."),
    (r"\balembic\s+downgrade\b", ASK,
     "alembic downgrade desfaz migracoes e pode apagar tabelas/colunas com dados."),
    (r"\bmysql\b[^\n]*\bmartelo_orcamentos_v3\b[^\n]*<", ASK,
     "importar um dump por cima da BD do Martelo substitui os dados existentes."),
    # PHC e' so-leitura: qualquer verbo de escrita e' recusado.
    (r"(?:Invoke-Sqlcmd|sqlcmd|SqlClient|SqlConnection)[^\n]*\b(?:INSERT\s+INTO|UPDATE\s+|DELETE\s+FROM|DROP\s+|TRUNCATE|ALTER\s+)",
     DENY, "o acesso ao PHC e' de SO-LEITURA (apenas SELECT). Escrever no PHC pode "
           "corromper dados de outros softwares da empresa."),
]

# --- Ficheiros criticos: escrever por cima e' sempre confirmado ---
FICHEIROS_CRITICOS = [
    (r"(?:^|[/\\])\.env(?:\.|$)", "o .env tem as credenciais da base de dados; "
                                  "escrever por cima parte a ligacao a BD."),
    (r"(?:^|[/\\])alembic\.ini$", "o alembic.ini define a ligacao das migracoes a BD."),
]

# --- Migracoes: operacoes que destroem dados ---
MIGRACAO = re.compile(r"(?:^|[/\\])(?:alembic[/\\]versions|migrations)[/\\]", re.I)
OPS_DESTRUTIVAS = [
    (r"\bop\.drop_table\b", "op.drop_table apaga a tabela e todos os seus dados"),
    (r"\bop\.drop_column\b", "op.drop_column apaga os dados dessa coluna"),
    (r"\bop\.drop_constraint\b", "op.drop_constraint remove uma restricao de integridade"),
    (r"\bop\.execute\b[^\n]*(?:DROP|TRUNCATE|DELETE\s+FROM)", "SQL destrutivo dentro de op.execute"),
]


def _so_git_e_cd(cmd: str) -> bool:
    """True se o comando (ja' sem os textos) for apenas cd/git, nada mais.

    Impede que a excecao sirva de esconderijo: em
    'git commit -m ok; sh <<EOF ... EOF' o heredoc alimenta o sh, nao o git.
    """
    for seg in re.split(r"[;&|\n]+", cmd):
        seg = seg.strip()
        if seg and not re.match(r"^(?:cd|git)\b", seg):
            return False
    return True


def limpar_mensagens_git(cmd: str) -> str:
    """Retira o TEXTO das mensagens de git commit/tag antes da analise.

    Uma mensagem de commit que MENCIONA 'alembic downgrade' esta a descrever,
    nao a executar. Tres travoes, para a excecao nao virar buraco:
      1. so' se aplica a git commit/tag;
      2. o texto so' e' cortado se nao puder executar; um heredoc com
         delimitador entre plicas e' sempre literal por definicao da shell;
      3. o que sobra tem de ser apenas cd/git.
    """
    if not re.search(r"\bgit\s+(?:commit|tag)\b", cmd, re.I):
        return cmd

    def _corta_se_literal(m):
        texto = m.group(0)
        return "" if ("$(" not in texto and "`" not in texto) else texto

    def _corta_sempre(m):
        return ""

    limpo = cmd
    limpo = re.sub(r"<<-?\s*'(\w+)'\n.*?\n\1", _corta_sempre, limpo, flags=re.S)
    limpo = re.sub(r"<<-?\s*(\"?)(\w+)\1\n.*?\n\2", _corta_se_literal, limpo, flags=re.S)
    limpo = re.sub(r"@'\n.*?\n'@", _corta_sempre, limpo, flags=re.S)
    limpo = re.sub(r"@\"\n.*?\n\"@", _corta_se_literal, limpo, flags=re.S)
    limpo = re.sub(r"(?:-m|--message)\s*(['\"])(?:\\.|(?!\1).)*\1", _corta_se_literal, limpo,
                   flags=re.S)

    if not _so_git_e_cd(limpo):
        return cmd
    return limpo


def _decidir(payload):
    """Devolve (decisao, [motivos]) ou (None, [])."""
    ti = payload.get("tool_input") or {}
    hits = []

    cmd = limpar_mensagens_git(ti.get("command") or "")
    if cmd.strip():
        for pattern, decision, reason in CMD_RULES:
            if re.search(pattern, cmd, re.I):
                hits.append((decision, reason))

    caminho = ti.get("file_path") or ti.get("notebook_path") or ""
    if caminho:
        for pattern, reason in FICHEIROS_CRITICOS:
            if re.search(pattern, caminho, re.I):
                hits.append((ASK, reason))

        conteudo = ti.get("content") or ti.get("new_string") or ""
        if conteudo and MIGRACAO.search(caminho):
            for pattern, reason in OPS_DESTRUTIVAS:
                if re.search(pattern, conteudo, re.I):
                    hits.append((ASK, f"esta migracao contem {reason}."))

    if not hits:
        return None, []
    decision = DENY if any(d == DENY for d, _ in hits) else ASK
    motivos = [r for d, r in hits if d == decision]
    return decision, list(dict.fromkeys(motivos))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    decision, motivos = _decidir(payload)
    if not decision:
        return 0

    lista = "\n".join(f"  - {m}" for m in motivos)
    if decision == DENY:
        texto = (
            "BLOQUEADO pela protecao do Martelo V3 (guard_projeto.py).\n"
            f"{lista}\n"
            "Nada foi alterado. Explica ao Paulo o que querias fazer em vez de "
            "tentares outro caminho para o mesmo efeito."
        )
    else:
        texto = (
            "Isto mexe em dados ou configuracao critica do Martelo V3:\n"
            f"{lista}\n"
            "Precisa de confirmacao explicita do Paulo."
        )

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": texto,
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
