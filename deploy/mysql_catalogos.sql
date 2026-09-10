-- ===========================================================================
-- Martelo Orcamentos V3 -- base dos catalogos de fornecedores
-- ===========================================================================
--
-- As tabelas de precos que os fornecedores enviam vao viver numa base propria,
-- no mesmo servidor MySQL dos orcamentos. Servem para CONSULTAR: a Pesquisa IA
-- responde ao utilizador em vez de ele andar por sites, telefonemas e emails.
--
-- Ficam separadas de `martelo_*` (orcamentos) de proposito. Os catalogos
-- reimportam-se dos ficheiros de origem sempre que for preciso; os orcamentos
-- nao. Separadas, esta base pode ser reconstruida do zero sem por um orcamento
-- em risco, e faz-se-lhe backup noutro ritmo.
--
-- COMO CORRER (uma vez, no PC do servidor):
--   mysql -u root -p < deploy\mysql_catalogos.sql
--
-- Porque e' que isto nao esta' na migracao alembic: `CREATE DATABASE` e' um
-- privilegio GLOBAL. Da-lo a` conta de manutencao do Martelo seria dar-lhe o
-- servidor inteiro -- a mesma razao por que o `martelo_criar_utilizador` existe
-- no `mysql_contas_beta.sql` em vez de um GRANT solto.
--
-- Depois deste ficheiro:
--   .venv\Scripts\python.exe -m alembic upgrade head
-- que cria as quatro tabelas.
-- ===========================================================================

CREATE DATABASE IF NOT EXISTS `martelo_catalogos`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

SELECT CONCAT('>>> Base pronta: ', SCHEMA_NAME, ' <<<') AS confirme
  FROM information_schema.schemata
 WHERE schema_name = 'martelo_catalogos';


-- ---------------------------------------------------------------------------
-- Privilegios
-- ---------------------------------------------------------------------------
-- Ao nivel da BASE e nao tabela a tabela, ao contrario do que o
-- `martelo_aplicar_grants` faz do lado dos orcamentos. Duas razoes:
--
--   1. aquele procedimento percorre as tabelas de DATABASE() e por isso nunca
--      chegaria aqui;
--   2. aqui nao ha' nada de sensivel. As tres tabelas que mandam em quem e'
--      quem -- `users`, `user_permissions`, `system_settings` -- ficam todas
--      do lado dos orcamentos.
--
-- Dar a` base inteira significa tambem que as tabelas criadas pelas proximas
-- migracoes ja' nascem acessiveis, sem ninguem se lembrar de nada.
--
-- Os perfis sao os mesmos do `mysql_contas_beta.sql`. Se ainda nao existirem,
-- correr esse ficheiro primeiro.
CREATE ROLE IF NOT EXISTS 'martelo_normal', 'martelo_admin';

GRANT SELECT, INSERT, UPDATE, DELETE ON `martelo_catalogos`.*
    TO 'martelo_normal', 'martelo_admin';

-- A conta de manutencao precisa de criar e alterar tabelas: e' ela que corre o
-- alembic. Trocar o nome se a conta de manutencao for outra.
GRANT ALL PRIVILEGES ON `martelo_catalogos`.* TO 'martelo_v3'@'localhost';

FLUSH PRIVILEGES;

SELECT '>>> Agora correr: .venv\\Scripts\\python.exe -m alembic upgrade head <<<' AS a_seguir;
