-- ============================================================================
-- Criar a base de dados PARTILHADA do beta do Martelo V3
--
-- Servidor : 192.168.5.201 (o mesmo onde vive a base do V2)
-- Base     : martelo_v3_beta
-- Objetivo : varios utilizadores, cada um com o V3 instalado no seu PC, a
--            trabalhar sobre esta mesma base -- tal como ja' acontece no V2.
--
-- COMO CORRER (precisa de credenciais de ADMINISTRACAO do MySQL, ex.: root):
--   No MySQL Workbench / HeidiSQL / phpMyAdmin, ligado a 192.168.5.201,
--   abrir este ficheiro e executar.
--
--   Ou por linha de comandos:
--     mysql -h 192.168.5.201 -u root -p < scripts/criar_base_beta.sql
--
-- ANTES DE CORRER: substituir POR_DEFINIR pela password escolhida (linha 38).
-- Esta password vai ficar no .env de cada utilizador, por isso NAO deve ser
-- igual a nenhuma password de administracao.
--
-- NAO apaga nem altera nada do que ja' existe no servidor. Nao toca na base
-- do V2 (orcamentos_v2). Se martelo_v3_beta ja' existir, nao faz nada.
-- ============================================================================

-- 1. A base de dados -----------------------------------------------------
-- utf8mb4 para suportar acentos e simbolos sem perda.
CREATE DATABASE IF NOT EXISTS martelo_v3_beta
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;


-- 2. O utilizador da aplicacao -------------------------------------------
-- Limitado a rede local (192.168.5.%): impede ligacoes de fora da empresa.
-- Se os postos estiverem noutra gama de IPs, ajustar aqui.
CREATE USER IF NOT EXISTS 'martelo_v3'@'192.168.5.%'
    IDENTIFIED BY 'POR_DEFINIR';


-- 3. Permissoes -----------------------------------------------------------
-- So' nesta base. O utilizador martelo_v3 nao consegue tocar em
-- orcamentos_v2 nem em mais nada do servidor.
-- Inclui DDL (CREATE/ALTER/DROP de tabelas) porque o Alembic precisa dele
-- para aplicar as migracoes.
GRANT ALL PRIVILEGES ON martelo_v3_beta.* TO 'martelo_v3'@'192.168.5.%';

FLUSH PRIVILEGES;


-- 4. Confirmar ------------------------------------------------------------
SELECT
    SCHEMA_NAME    AS base_criada,
    DEFAULT_CHARACTER_SET_NAME AS charset,
    DEFAULT_COLLATION_NAME     AS collation
FROM information_schema.SCHEMATA
WHERE SCHEMA_NAME = 'martelo_v3_beta';

SHOW GRANTS FOR 'martelo_v3'@'192.168.5.%';
