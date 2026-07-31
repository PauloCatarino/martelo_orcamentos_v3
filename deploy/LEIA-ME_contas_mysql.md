# Contas por utilizador — guião passo a passo

Este é o guião para dar a cada pessoa a sua conta na base de dados do Martelo.
Faz-se **uma vez**, na beta.

## Antes de começar: o que este trabalho pode e não pode estragar

**Não toca em dados.** Nenhum orçamento, nenhuma obra, nenhuma peça, nenhum
utilizador da tabela `users`. O que se cria são *contas de acesso*, *perfis de
privilégios* e *procedimentos* — coisas que hoje não existem.

**A conta antiga continua a funcionar.** O `martelo_v3` fica intacto durante
todo o processo. Só se apaga no fim, quando estiver tudo a andar — e essa linha
está comentada de propósito no fim do `mysql_contas_beta.sql`.

**Há um botão de recuo.** O `mysql_contas_DESFAZER.sql` apaga tudo o que se
criou aqui e deixa o servidor como estava.

Ou seja: o pior que acontece se algo correr mal é ficarem umas contas criadas
que não funcionam. Nada se perde.

---

## Passo 0 — Uma cópia de segurança (5 minutos, e dorme melhor)

Não é preciso para este trabalho, mas é bom hábito antes de mexer no servidor.
No **PowerShell** do VS Code:

```powershell
mysqldump -h 192.168.5.201 -u root -p --routines --events martelo_v3_beta > backup_beta_antes_contas.sql
```

Pede a password do root. Fica um ficheiro na pasta do projeto.

---

## Passo 1 — Criar os perfis e os procedimentos

**Onde:** MySQL Workbench (é mais visual do que a linha de comandos, e vê-se o
que acontece).

1. Abrir o **MySQL Workbench**
2. Clicar na ligação **`Servidor 192.168.5.201 (admin)`** — é a que entra como
   `root` no servidor onde vive a beta
3. Menu **File → Open SQL Script…** e escolher
   `deploy\mysql_contas_beta.sql`
4. **IMPORTANTE:** antes de executar, escrever no topo do separador e correr só
   esta linha (selecionar a linha e `Ctrl+Enter`):

   ```sql
   USE martelo_v3_beta;
   ```

   Se falhar este passo o script pára sozinho e diz-lhe porquê — mas é melhor
   não chegar lá.
5. Executar tudo: o botão do **raio ⚡** (ou `Ctrl+Shift+Enter`)

**O que deve ver:** várias linhas verdes no painel de baixo, sem vermelhos.

**Como confirmar que correu bem** — cole isto e execute:

```sql
SELECT routine_name FROM information_schema.routines
 WHERE routine_schema = 'martelo_v3_beta' AND routine_name LIKE 'martelo_%';
```

Devem aparecer **5 linhas** (`martelo_aplicar_grants`, `martelo_apagar_utilizador`,
`martelo_criar_utilizador`, `martelo_mudar_a_minha_password`,
`martelo_repor_password`).

---

## Passo 2 — Gerar as contas das pessoas

**Onde:** terminal **PowerShell** do VS Code, na pasta do projeto.

```powershell
.venv\Scripts\python.exe scripts\gerar_contas_mysql.py
```

Isto **só lê** a base. Escreve dois ficheiros na pasta do projeto:

- `contas_martelo.sql` — o que vai correr a seguir
- `contas_martelo.txt` — as passwords de cada pessoa

Abra o `contas_martelo.sql` no VS Code e veja se os nomes fazem sentido antes de
avançar.

---

## Passo 3 — Criar as contas

De volta ao **Workbench**, na mesma ligação e com a mesma base escolhida:

1. **File → Open SQL Script…** → `contas_martelo.sql`
2. Executar tudo (⚡)

**Confirmar:**

```sql
SELECT to_user AS conta, from_user AS perfil
  FROM mysql.role_edges
 WHERE from_user IN ('martelo_normal', 'martelo_admin')
 ORDER BY to_user;
```

Deve ver uma linha por pessoa, com o perfil ao lado.

---

## Passo 4 — O teste que interessa

Este é o teste que prova que o buraco ficou tapado.

1. No Workbench, criar uma ligação nova (o **+** ao lado de *MySQL Connections*):
   - Connection Name: `Teste conta colega`
   - Hostname: `192.168.5.201`, Port: `3306`
   - Username: o de um colega (ex.: `ana`)
   - Password: a que está no `contas_martelo.txt`
2. Entrar nessa ligação e correr:

```sql
USE martelo_v3_beta;

-- Isto TEM de funcionar (trabalho normal):
SELECT COUNT(*) FROM orcamentos;

-- Isto TEM de dar erro de permissão:
UPDATE users SET role = 'admin' WHERE username = 'ana';

-- Isto também TEM de dar erro de permissão:
UPDATE system_settings SET valor = 'ON' WHERE chave = 'imos_escrita_ativa';
```

Se o primeiro devolve um número e os outros dois dão
`Error Code: 1142 ... command denied`, **está feito**. É exatamente isto que
antes qualquer pessoa conseguia fazer com o `.env`.

---

## Passo 5 — Testar o Martelo

Ainda **sem** distribuir nada aos colegas:

1. Tirar `DB_USER` e `DB_PASSWORD` do `.env` da pasta principal (guarde-os num
   bloco de notas — os scripts de seed ainda precisam deles)
2. Abrir o Martelo e entrar com a sua conta e a password do `contas_martelo.txt`
3. Confirmar o trabalho normal: abrir um orçamento, o Ponto Situação, uma obra
4. Ir a **Configurações → Utilizadores** e usar **"Mudar a minha palavra-passe"**
5. Sair e voltar a entrar com a password nova

---

## Passo 6 — Distribuir

1. Entregar a cada pessoa **só a linha dela** do `contas_martelo.txt`
2. **Apagar o `contas_martelo.txt`**
3. Reconstruir o instalador: `.venv\Scripts\python.exe build_beta.py --installer`
   (o `.env` novo já não leva credenciais; o build recusa-se a empacotar um que
   as tenha)

---

## Se alguma coisa correr mal

Abrir `deploy\mysql_contas_DESFAZER.sql` no Workbench e executar. Depois repor
`DB_USER`/`DB_PASSWORD` no `.env` e voltar à versão anterior da app. Fica tudo
como estava.

---

## Notas para o futuro

**Tabelas novas.** Quando uma migração criar uma tabela nova, as contas não lhe
têm acesso até correr, uma vez, no Workbench:

```sql
USE martelo_v3_beta;
CALL martelo_aplicar_grants();
```

**Pessoas novas.** Cria-se pela app (Configurações → Utilizadores → Novo
utilizador) — ela trata da conta na base de dados sozinha.

**Passar isto para a base principal.** O mesmo guião, trocando
`martelo_v3_beta` pelo nome da base principal em todos os sítios. Só depois de a
beta estar rodada.
