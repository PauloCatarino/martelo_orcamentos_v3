# AGENTS.md — Martelo_Orcamentos_V3

Instruções para agentes de IA (Codex, ChatGPT, Claude) que trabalham neste repositório.

---

## 1. REGRA ABSOLUTA: nunca apagar nada sem o utilizador saber

O Paulo é a única pessoa que decide o que é apagado. Uma eliminação errada pode partir o
software, destruir dados de orçamentos reais, ou afetar outros sistemas da empresa.

**NUNCA fazer, em nenhuma circunstância, sem autorização explícita e no momento:**

| Categoria | Exemplos proibidos |
|---|---|
| Ficheiros e pastas | `rm -rf`, `rm -r`, `Remove-Item -Recurse`, `rmdir /s`, `del /s`, `shutil.rmtree`, `find -delete` |
| Trabalho não commitado | `git clean -f`, `git reset --hard`, `git checkout -- .`, `git restore .` |
| Base de dados | `DROP TABLE`, `DROP DATABASE`, `DROP COLUMN`, `TRUNCATE`, `DELETE FROM` sem `WHERE` |
| Migrações | `alembic downgrade base` |
| PHC | qualquer `INSERT`/`UPDATE`/`DELETE`/`DROP`/`ALTER` — ver secção 3 |

**Pedir sempre confirmação antes de:** apagar um ficheiro individual, `DELETE FROM ... WHERE`,
`UPDATE` sem `WHERE`, `alembic downgrade`, escrever no `.env` ou no `alembic.ini`, e escrever
migrações com `op.drop_table` / `op.drop_column` / `op.drop_constraint`.

**Se precisares mesmo de apagar algo:** explica ao Paulo o que querias apagar e porquê, e
deixa-o fazê-lo. Não procures outro caminho para o mesmo efeito.

> No Claude Code estas regras são impostas por hooks (`.claude/hooks/guard_projeto.py`, mais
> uma camada global fora do repositório) que o harness corre ANTES de cada comando. O Codex
> corre noutro harness e **não** tem essa rede de segurança: aqui a regra depende de ti.

---

## 2. Visão geral do projeto

Software interno de orçamentação e preparação de produção de mobiliário por medida.
Sucessor do Martelo_Orcamentos_V2. Desde 31-08-2026 é o V3 que faz os orçamentos novos
(continua a numeração do V2); o V2 continua a ser consultado pelos colegas — ver secção 3.

- **Stack:** Python 3.12, PySide6 (Qt), SQLAlchemy 2 + Alembic, MySQL (PyMySQL).
- **Arrancar:** `python -m app.main` (a partir da raiz, com o `.venv` ativo).
- **Testes:** `.venv\Scripts\python.exe -m pytest -q` (mais de 5600 testes em outubro de
  2026; devem passar todos). Numa cópia de trabalho (worktree) não há `.venv`: usar o da
  pasta principal, `C:\Users\Utilizador\Documents\Martelo_Orcamentos_V3\.venv\Scripts\python.exe`.

Estrutura: `app/ui` (páginas e diálogos Qt), `app/services` (lógica de negócio),
`app/repositories` (acesso a dados), `app/models` (SQLAlchemy), `app/domain`,
`alembic/versions` (migrações), `tests`.

---

## 3. Fronteiras que não se atravessam

**PHC — SÓ LEITURA.** O acesso ao SQL Server do PHC é exclusivamente `SELECT`. O PHC é o
sistema de gestão da empresa: escrever lá pode corromper dados de outros softwares em uso.

**Martelo V2 — SÓ LEITURA.** O código do V2 (`C:\Users\Utilizador\Documents\Martelo_Orcamentos_V2\`)
serve de referência. Os colegas continuam a consultá-lo e o V3 lê a base dele (histórico
de orçamentos). **Nunca editar.**

**`.env` — nunca commitar.** Contém credenciais da base de dados. O mesmo para
`.claude/settings.local.json`.

**Base real vs base de desenvolvimento.** O `.env` da pasta principal aponta para a
`martelo_v3_dev`. A base real, a que os colegas usam, é a `martelo_v3`. Scripts e consultas
vão à dev sem avisar: antes de tirar conclusões sobre dados reais, confirmar a base com
`SELECT DATABASE()`.

**Migrações que criam tabelas** chamam `martelo_aplicar_grants()`, que precisa de
`GRANT OPTION`: na base real só se aplicam com a conta root, ou seja, pelo Paulo.

**Versões novas** (instaladores para os PCs dos colegas): só a partir do `main` da pasta
principal, subindo o número com `scripts/nova_versao.py`. Passo a passo em
`docs/34_como_fazer_uma_versao_nova.md`.

---

## 4. Convenções

- **Peças horizontais:** a dimensão principal é sempre **comprimento**, nunca "altura".
- **Commits:** usar `git add -A` (depois de rever `git status`), nunca listar pastas à mão —
  senão ficam de fora models e migrações. Mensagens em português.
- **Envio para o GitHub (push):** no fim de cada alteração, **perguntar sempre** ao Paulo se
  quer enviar, e só enviar com o sim dele. O repositório é **público**: antes de enviar,
  procurar passwords e chaves no que vai. Não criar PRs sem ele pedir.
- **Migrações:** cada alteração aos models precisa da migração Alembic correspondente.
- **UI:** todos os menus têm uma linha de estado ("supervisor") por baixo dos botões;
  botões e campos editáveis levam sempre tooltip.

---

## 5. Ao terminar uma alteração

1. Correr os testes e confirmar que passam.
2. Escrever um guião de teste passo-a-passo: caminho exato dos menus, valores a introduzir,
   e resultado esperado. Registar o mesmo guião em
   `docs/17_plano_e_ponto_situacao_martelo_v3.md`.
3. Confirmar que o código está no branch da **pasta principal** — é de lá que a app corre.
4. Perguntar ao Paulo se quer enviar para o GitHub (secção 4).
5. Se algo falhou ou ficou por fazer, dizê-lo claramente. Não apresentar como concluído o
   que não foi verificado.
