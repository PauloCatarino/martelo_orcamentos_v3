-- ===========================================================================
-- Martelo Orcamentos V3 -- contas MySQL por pessoa (BETA)
-- ===========================================================================
--
-- Ate' aqui todos os PCs se ligavam com a mesma conta (martelo_v3) e a password
-- ia dentro do instalador. Quem abrisse o .env ligava-se a` base por fora e
-- fazia o que quisesse -- promover-se a admin, ligar a escrita no iMos, ler as
-- passwords do PHC. Este ficheiro passa a autoridade para o MySQL: cada pessoa
-- tem a sua conta e os seus privilegios.
--
-- COMO CORRER (uma vez, no PC do servidor):
--   mysql -u root -p martelo_v3_beta < deploy\mysql_contas_beta.sql
--
-- PRECISA de MySQL 8.0 ou mais recente (usa ROLES). Confirme antes com:
--   SELECT VERSION();
--
-- Depois deste ficheiro, corra o scripts/gerar_contas_mysql.py para criar as
-- contas das pessoas que ja' existem na tabela `users`.
-- ===========================================================================

-- ###########################################################################
-- A BASE ONDE ISTO VAI SER APLICADO -- confirme antes de executar.
--
-- No Workbench o schema activo e' da LIGACAO, nao do separador: abrir este
-- ficheiro num separador novo herda o que estava escolhido antes, e o script
-- acaba aplicado na base errada sem ninguem dar por isso (ja' aconteceu duas
-- vezes). Por isso o USE esta' aqui dentro, e nao a` mao.
--
-- Trocar a linha se for para outra base.
-- ###########################################################################
USE martelo_v3_beta;

-- Diz alto e bom som onde e' que vai mexer: se esta primeira grelha nao
-- mostrar a base que quer, pare aqui.
SELECT CONCAT('>>> Vai aplicar em: ', DATABASE(), ' <<<') AS confirme_a_base;

-- ---------------------------------------------------------------------------
-- 1. Os dois perfis
-- ---------------------------------------------------------------------------
-- Sao ROLES e nao GRANTs soltos de proposito: quando uma migracao criar uma
-- tabela nova, basta um CALL martelo_aplicar_grants() e TODAS as contas ficam
-- em dia. Sem roles seria preciso repetir os GRANTs pessoa a pessoa.
CREATE ROLE IF NOT EXISTS 'martelo_normal', 'martelo_admin';


-- ---------------------------------------------------------------------------
-- 2. Quem pode o quê
-- ---------------------------------------------------------------------------
-- Tres tabelas mandam em quem e' quem e no que a app faz -- e por isso so' o
-- administrador lhes toca:
--
--   users             -- o `role` daqui decide quem e' admin
--   user_permissions  -- os menus a que cada um chega
--   system_settings   -- caminhos, credenciais das ligacoes externas e o
--                        interruptor `imos_escrita_ativa` (escrita no iMos)
--
-- Toda a gente as LE^ (a app precisa: caminhos das pastas, ligacao ao PHC e ao
-- Streamlit). O que muda e' que so' o admin as ESCREVE.
--
-- As restantes sao o trabalho do dia a dia: orcamentos, producao, catalogos.
-- Quem usa o Martelo escreve nelas — e' para isso que serve.

DROP PROCEDURE IF EXISTS martelo_aplicar_grants;
DELIMITER $$
CREATE PROCEDURE martelo_aplicar_grants()
    SQL SECURITY INVOKER
    COMMENT 'Aplica os privilegios dos dois perfis a todas as tabelas'
BEGIN
    DECLARE v_fim INT DEFAULT 0;
    DECLARE v_tabela VARCHAR(64);
    DECLARE v_base VARCHAR(64);

    DECLARE cur CURSOR FOR
        SELECT table_name
          FROM information_schema.tables
         WHERE table_schema = DATABASE()
           AND table_type = 'BASE TABLE'
           AND table_name NOT IN ('users', 'user_permissions', 'system_settings')
           AND table_name <> 'alembic_version';
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_fim = 1;

    SET v_base = DATABASE();

    -- Rede de seguranca: sem base escolhida, os GRANTs iriam parar ao sitio
    -- errado (ou a lado nenhum). Mais vale parar aqui e dizer porque.
    IF v_base IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT =
            'Nenhuma base escolhida. Corra primeiro: USE martelo_v3_beta;';
    END IF;

    -- Segunda rede: so' aplica onde o Martelo vive mesmo. Se a base estiver
    -- vazia ou for outra qualquer, para -- em vez de encher um sitio errado
    -- de privilegios.
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
         WHERE table_schema = v_base AND table_name = 'orcamentos'
    ) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT =
            'Esta base nao parece ser a do Martelo (falta a tabela orcamentos).';
    END IF;

    -- 2a. Tabelas de trabalho: leitura e escrita para os dois perfis.
    OPEN cur;
    percorre: LOOP
        FETCH cur INTO v_tabela;
        IF v_fim = 1 THEN
            LEAVE percorre;
        END IF;

        SET @sql = CONCAT(
            'GRANT SELECT, INSERT, UPDATE, DELETE ON `', v_base, '`.`',
            v_tabela, '` TO ''martelo_normal'', ''martelo_admin'''
        );
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END LOOP;
    CLOSE cur;

    -- 2b. As tres sensiveis: todos leem, so' o admin escreve.
    SET @sql = CONCAT('GRANT SELECT ON `', v_base, '`.`users` TO ''martelo_normal''');
    PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
    SET @sql = CONCAT('GRANT SELECT ON `', v_base, '`.`user_permissions` TO ''martelo_normal''');
    PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
    SET @sql = CONCAT('GRANT SELECT ON `', v_base, '`.`system_settings` TO ''martelo_normal''');
    PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

    SET @sql = CONCAT('GRANT SELECT, INSERT, UPDATE, DELETE ON `', v_base, '`.`users` TO ''martelo_admin''');
    PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
    SET @sql = CONCAT('GRANT SELECT, INSERT, UPDATE, DELETE ON `', v_base, '`.`user_permissions` TO ''martelo_admin''');
    PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
    SET @sql = CONCAT('GRANT SELECT, INSERT, UPDATE, DELETE ON `', v_base, '`.`system_settings` TO ''martelo_admin''');
    PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

    -- 2c. O alembic_version so' interessa a quem faz migracoes (o Paulo, com a
    -- conta de manutencao). Ninguem mais precisa sequer de o ler.
END$$
DELIMITER ;

CALL martelo_aplicar_grants();


-- ---------------------------------------------------------------------------
-- 3. Criar contas a partir da app
-- ---------------------------------------------------------------------------
-- O `CREATE USER` do MySQL e' um privilegio GLOBAL: nao se limita a uma base.
-- Dar-lho a` conta de admin do Martelo seria dar-lhe o servidor inteiro.
--
-- Este procedimento resolve isso: corre com os privilegios de QUEM O CRIOU
-- (SQL SECURITY DEFINER, ou seja o root), e a conta de admin do Martelo so'
-- recebe EXECUTE sobre ele. Resultado: a app cria contas do Martelo -- com o
-- perfil certo e mais nada -- sem poder tocar no resto do servidor.

DROP PROCEDURE IF EXISTS martelo_criar_utilizador;
DELIMITER $$
CREATE PROCEDURE martelo_criar_utilizador(
    IN p_nome     VARCHAR(64),
    IN p_password VARCHAR(255),
    IN p_admin    BOOLEAN
)
    SQL SECURITY DEFINER
    COMMENT 'Cria uma conta do Martelo e da-lhe o perfil normal ou de admin'
BEGIN
    DECLARE v_perfil VARCHAR(32);

    -- O nome entra em SQL dinamico (o CREATE USER nao aceita variaveis), por
    -- isso e' validado a` letra antes de tocar em seja o que for. Sem isto,
    -- um nome com plicas dava para escrever o SQL que se quisesse.
    IF p_nome IS NULL OR p_nome NOT REGEXP '^[A-Za-z0-9_.-]{3,32}$' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Nome de utilizador invalido: use 3 a 32 letras, algarismos, _ . -';
    END IF;

    IF p_password IS NULL OR CHAR_LENGTH(p_password) < 6 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'A palavra-passe tem de ter pelo menos 6 caracteres.';
    END IF;

    IF p_admin THEN
        SET v_perfil = 'martelo_admin';
    ELSE
        SET v_perfil = 'martelo_normal';
    END IF;

    -- QUOTE() escapa o valor; o nome ja' passou pelo REGEXP acima.
    SET @sql = CONCAT('CREATE USER ', QUOTE(p_nome), '@''%'' IDENTIFIED BY ', QUOTE(p_password));
    PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

    SET @sql = CONCAT('GRANT ', v_perfil, ' TO ', QUOTE(p_nome), '@''%''');
    PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

    -- Sem isto a conta liga-se mas sem privilegios nenhuns: o role existe mas
    -- fica por ativar. E' o engano classico dos roles do MySQL.
    SET @sql = CONCAT('SET DEFAULT ROLE ALL TO ', QUOTE(p_nome), '@''%''');
    PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
END$$
DELIMITER ;


-- ---------------------------------------------------------------------------
-- 4. Repor a palavra-passe de alguem (so' o admin)
-- ---------------------------------------------------------------------------
-- Cada pessoa muda a SUA password sozinha, pela app (ALTER USER USER() ...),
-- sem precisar deste procedimento. Este e' para quando alguem se esquece.
DROP PROCEDURE IF EXISTS martelo_repor_password;
DELIMITER $$
CREATE PROCEDURE martelo_repor_password(
    IN p_nome     VARCHAR(64),
    IN p_password VARCHAR(255)
)
    SQL SECURITY DEFINER
    COMMENT 'Repoe a palavra-passe de uma conta do Martelo'
BEGIN
    IF p_nome IS NULL OR p_nome NOT REGEXP '^[A-Za-z0-9_.-]{3,32}$' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Nome de utilizador invalido.';
    END IF;

    IF p_password IS NULL OR CHAR_LENGTH(p_password) < 6 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'A palavra-passe tem de ter pelo menos 6 caracteres.';
    END IF;

    -- So' mexe em contas que ja' tenham perfil do Martelo. Assim este
    -- procedimento nunca serve para mudar a password do root nem de contas de
    -- outros sistemas que vivam no mesmo servidor.
    IF NOT EXISTS (
        SELECT 1
          FROM mysql.role_edges
         WHERE to_user = p_nome
           AND from_user IN ('martelo_normal', 'martelo_admin')
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Essa conta nao e do Martelo.';
    END IF;

    SET @sql = CONCAT('ALTER USER ', QUOTE(p_nome), '@''%'' IDENTIFIED BY ', QUOTE(p_password));
    PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
END$$
DELIMITER ;


-- ---------------------------------------------------------------------------
-- 5. Cada um muda a SUA palavra-passe
-- ---------------------------------------------------------------------------
-- Sem procedimento, a app teria de montar o ``ALTER USER`` em texto com a
-- password la' dentro. Assim a password viaja como parametro e o escape fica
-- do lado do servidor, no QUOTE().
DROP PROCEDURE IF EXISTS martelo_mudar_a_minha_password;
DELIMITER $$
CREATE PROCEDURE martelo_mudar_a_minha_password(IN p_password VARCHAR(255))
    SQL SECURITY DEFINER
    COMMENT 'Muda a palavra-passe de quem esta ligado'
BEGIN
    DECLARE v_nome VARCHAR(64);

    IF p_password IS NULL OR CHAR_LENGTH(p_password) < 6 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'A palavra-passe tem de ter pelo menos 6 caracteres.';
    END IF;

    -- CUIDADO AQUI. "ALTER USER USER()" parece a forma obvia de dizer "muda a
    -- minha", e e' mesmo -- fora de um procedimento. Aqui dentro, com
    -- SQL SECURITY DEFINER, acaba por apanhar o DONO do procedimento (o root)
    -- em vez de quem o chamou: uma pessoa carregava em "mudar a minha
    -- palavra-passe" e mudava a do root, sem erro nenhum e sem dar por isso.
    --
    -- USER() sozinho, esse sim, devolve sempre quem LIGOU ('Pedro@localhost'),
    -- porque a ligacao nao muda por o codigo correr como outro. Tira-se dai' o
    -- nome e nomeia-se a conta a` mao.
    SET v_nome = SUBSTRING_INDEX(USER(), '@', 1);

    -- Rede de seguranca: mesmo que a linha de cima alguma vez devolva algo
    -- inesperado, so' se mexe em contas que tenham perfil do Martelo. O root
    -- nao tem nenhum, por isso nunca mais pode ser o alvo.
    IF NOT EXISTS (
        SELECT 1 FROM mysql.role_edges
         WHERE to_user = v_nome
           AND from_user IN ('martelo_normal', 'martelo_admin')
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'A conta ligada nao e do Martelo: nada foi alterado.';
    END IF;

    SET @sql = CONCAT('ALTER USER ', QUOTE(v_nome), '@''%'' IDENTIFIED BY ', QUOTE(p_password));
    PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
END$$
DELIMITER ;


-- ---------------------------------------------------------------------------
-- 6. Apagar uma conta do Martelo
-- ---------------------------------------------------------------------------
-- Serve sobretudo para desfazer: se a app criar a conta e falhar logo a seguir
-- a gravar o perfil, apaga a conta em vez de deixar lixo no servidor.
DROP PROCEDURE IF EXISTS martelo_apagar_utilizador;
DELIMITER $$
CREATE PROCEDURE martelo_apagar_utilizador(IN p_nome VARCHAR(64))
    SQL SECURITY DEFINER
    COMMENT 'Apaga uma conta do Martelo (e so do Martelo)'
BEGIN
    IF p_nome IS NULL OR p_nome NOT REGEXP '^[A-Za-z0-9_.-]{3,32}$' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Nome de utilizador invalido.';
    END IF;

    -- Mesma salvaguarda do repor_password: so' mexe em contas com perfil do
    -- Martelo, nunca no root nem em contas de outros sistemas.
    IF NOT EXISTS (
        SELECT 1 FROM mysql.role_edges
         WHERE to_user = p_nome
           AND from_user IN ('martelo_normal', 'martelo_admin')
    ) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Essa conta nao e do Martelo.';
    END IF;

    SET @sql = CONCAT('DROP USER ', QUOTE(p_nome), '@''%''');
    PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
END$$
DELIMITER ;


-- ---------------------------------------------------------------------------
-- 7. Quem pode chamar estes procedimentos
-- ---------------------------------------------------------------------------
GRANT EXECUTE ON PROCEDURE martelo_criar_utilizador  TO 'martelo_admin';
GRANT EXECUTE ON PROCEDURE martelo_repor_password    TO 'martelo_admin';
GRANT EXECUTE ON PROCEDURE martelo_apagar_utilizador TO 'martelo_admin';
GRANT EXECUTE ON PROCEDURE martelo_aplicar_grants    TO 'martelo_admin';

-- Este e' para toda a gente: cada um muda a sua.
GRANT EXECUTE ON PROCEDURE martelo_mudar_a_minha_password
    TO 'martelo_normal', 'martelo_admin';

FLUSH PRIVILEGES;


-- ---------------------------------------------------------------------------
-- 8. O arquivo do V2 (orcamentos_v2)
-- ---------------------------------------------------------------------------
-- A consulta ao Arquivo V2 continua a usar uma conta propria (orc_user), cujas
-- credenciais vao no .env de cada PC -- a app precisa delas para ler os
-- orcamentos antigos.
--
-- O problema e' que essa conta tinha ALL PRIVILEGES. A app poe uma guarda
-- read-only do lado do Python, mas quem abrisse o .env ligava-se por fora, sem
-- guarda nenhuma, e podia apagar o arquivo inteiro. Aqui troca-se por SELECT:
-- as credenciais continuam la', mas o pior que se faz com elas e' LER os
-- orcamentos antigos -- que e' o que a app ja' mostra a toda a gente.
--
-- Nao depende da base escolhida (a conta e' global), mas so' faz sentido correr
-- uma vez no servidor.
REVOKE ALL PRIVILEGES ON `orcamentos_v2`.* FROM 'orc_user'@'%';
GRANT SELECT ON `orcamentos_v2`.* TO 'orc_user'@'%';
FLUSH PRIVILEGES;

-- Confirmar (deve passar a mostrar apenas GRANT SELECT):
--   SHOW GRANTS FOR 'orc_user'@'%';


-- ---------------------------------------------------------------------------
-- 9. Depois de tudo testado: apagar a conta partilhada
-- ---------------------------------------------------------------------------
-- NAO corra esta linha ja'. So' quando as contas por pessoa estiverem a
-- funcionar e o instalador novo estiver distribuido -- enquanto houver um PC
-- com o .env antigo, esta conta ainda e' precisa.
--
--   DROP USER 'martelo_v3'@'%';
