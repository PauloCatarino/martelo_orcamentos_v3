-- ===========================================================================
-- DESFAZER as contas por utilizador -- volta tudo ao que era antes
-- ===========================================================================
--
-- Serve para dormir descansado: se alguma coisa correr mal com as contas por
-- pessoa, isto apaga o que o mysql_contas_beta.sql criou e o Martelo volta a
-- trabalhar com a conta partilhada (martelo_v3), como sempre trabalhou.
--
-- NAO APAGA DADOS NENHUNS. Nem orcamentos, nem producao, nem utilizadores da
-- tabela `users`. So' mexe em contas de acesso, roles e procedimentos.
--
-- COMO CORRER (no Workbench, ligado como root):
--   1. Abrir este ficheiro
--   2. Escolher a base:  USE martelo_v3_beta;
--   3. Executar tudo (o raio ⚡)
--
-- DEPOIS de correr isto, para o Martelo voltar a funcionar como antes:
--   - Repor DB_USER=martelo_v3 e DB_PASSWORD=... no .env de cada PC
--   - Voltar a` versao anterior da app (git checkout do commit anterior)
-- ===========================================================================

USE martelo_v3_beta;

-- 1. Os procedimentos
DROP PROCEDURE IF EXISTS martelo_criar_utilizador;
DROP PROCEDURE IF EXISTS martelo_repor_password;
DROP PROCEDURE IF EXISTS martelo_apagar_utilizador;
DROP PROCEDURE IF EXISTS martelo_mudar_a_minha_password;
DROP PROCEDURE IF EXISTS martelo_aplicar_grants;

-- 2. As contas das pessoas
--
-- Descomente e complete com os nomes que criou (os mesmos que estao no
-- contas_martelo.txt). Deixei alguns exemplos:
--
--   DROP USER IF EXISTS 'paulo'@'%';
--   DROP USER IF EXISTS 'admin'@'%';
--   DROP USER IF EXISTS 'ana'@'%';
--
-- Para ver quais existem antes de apagar:
--
--   SELECT to_user AS conta, from_user AS perfil
--     FROM mysql.role_edges
--    WHERE from_user IN ('martelo_normal', 'martelo_admin');

-- 3. Os perfis
--
-- Apagar os roles tira automaticamente os privilegios a quem os tinha.
DROP ROLE IF EXISTS 'martelo_normal';
DROP ROLE IF EXISTS 'martelo_admin';

FLUSH PRIVILEGES;

-- 4. Confirmar que ficou limpo
SELECT 'procedimentos que sobraram' AS o_que, COUNT(*) AS quantos
  FROM information_schema.routines
 WHERE routine_schema = DATABASE() AND routine_name LIKE 'martelo_%'
UNION ALL
SELECT 'perfis que sobraram', COUNT(*)
  FROM mysql.user
 WHERE user IN ('martelo_normal', 'martelo_admin');
-- As duas linhas devem dar 0.
