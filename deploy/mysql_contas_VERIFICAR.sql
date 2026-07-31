-- ===========================================================================
-- VERIFICAR as contas por utilizador -- corre depois do mysql_contas_beta.sql
-- ===========================================================================
--
-- Comparar listas de GRANTs a olho e' enganador: sao dezenas de linhas quase
-- iguais e o que falta nao salta a` vista. Isto responde por SIM ou NAO.
--
-- COMO CORRER (Workbench, ligado como root):
--   1. Escolher a base (selecione a linha e Ctrl+Enter):
--        USE martelo_v3_dev;    -- se esta a ensaiar
--        USE martelo_v3_beta;   -- a serio
--   2. Executar o resto (o raio) e olhar para a coluna `estado`.
--
-- So' interessa uma coisa: que NAO haja nenhuma linha a dizer PROBLEMA.
-- ===========================================================================

-- ###########################################################################
-- A BASE A VERIFICAR -- troque a linha se for outra.
-- (No Workbench o schema activo e' da ligacao e nao do separador; com o USE
--  aqui dentro nao ha' enganos.)
-- ###########################################################################
USE martelo_v3_beta;

SELECT CONCAT('>>> A verificar: ', DATABASE(), ' <<<') AS base;

-- ---------------------------------------------------------------------------
-- 1. Privilegios tabela a tabela
-- ---------------------------------------------------------------------------
-- Esperado:
--   users / user_permissions / system_settings -> normal le' (1), admin
--     escreve (4). Sao estas tres que impedem alguem de se promover a admin
--     ou de ligar a escrita no iMos.
--   todas as outras -> os dois escrevem (4 e 4). E' o trabalho do dia a dia.
SELECT
    t.table_name AS tabela,
    COALESCE(n.privs, 0) AS normal_tem,
    COALESCE(a.privs, 0) AS admin_tem,
    CASE
        WHEN t.table_name IN ('users', 'user_permissions', 'system_settings')
            THEN IF(COALESCE(n.privs, 0) = 1 AND COALESCE(a.privs, 0) = 4,
                    'OK (so leitura para o normal)', '>>> PROBLEMA <<<')
        ELSE IF(COALESCE(n.privs, 0) = 4 AND COALESCE(a.privs, 0) = 4,
                'OK', '>>> PROBLEMA <<<')
    END AS estado
FROM information_schema.tables t
LEFT JOIN (
    SELECT table_name, COUNT(*) AS privs
      FROM information_schema.table_privileges
     WHERE table_schema = DATABASE() AND grantee = "'martelo_normal'@'%'"
     GROUP BY table_name
) n ON n.table_name = t.table_name
LEFT JOIN (
    SELECT table_name, COUNT(*) AS privs
      FROM information_schema.table_privileges
     WHERE table_schema = DATABASE() AND grantee = "'martelo_admin'@'%'"
     GROUP BY table_name
) a ON a.table_name = t.table_name
WHERE t.table_schema = DATABASE()
  AND t.table_type = 'BASE TABLE'
  -- O alembic_version e' so' de quem faz migracoes; fica de fora de proposito.
  AND t.table_name <> 'alembic_version'
ORDER BY estado DESC, t.table_name;


-- ---------------------------------------------------------------------------
-- 2. Resumo -- a linha que interessa
-- ---------------------------------------------------------------------------
SELECT
    SUM(estado LIKE '%PROBLEMA%') AS tabelas_com_problema,
    COUNT(*) AS tabelas_verificadas,
    IF(SUM(estado LIKE '%PROBLEMA%') = 0,
       'TUDO BEM -- pode seguir para as contas das pessoas.',
       'PARE -- ha tabelas mal configuradas. Volte a correr: CALL martelo_aplicar_grants();'
    ) AS conclusao
FROM (
    SELECT
        CASE
            WHEN t.table_name IN ('users', 'user_permissions', 'system_settings')
                THEN IF(COALESCE(n.privs, 0) = 1 AND COALESCE(a.privs, 0) = 4, 'OK', 'PROBLEMA')
            ELSE IF(COALESCE(n.privs, 0) = 4 AND COALESCE(a.privs, 0) = 4, 'OK', 'PROBLEMA')
        END AS estado
    FROM information_schema.tables t
    LEFT JOIN (
        SELECT table_name, COUNT(*) AS privs
          FROM information_schema.table_privileges
         WHERE table_schema = DATABASE() AND grantee = "'martelo_normal'@'%'"
         GROUP BY table_name
    ) n ON n.table_name = t.table_name
    LEFT JOIN (
        SELECT table_name, COUNT(*) AS privs
          FROM information_schema.table_privileges
         WHERE table_schema = DATABASE() AND grantee = "'martelo_admin'@'%'"
         GROUP BY table_name
    ) a ON a.table_name = t.table_name
    WHERE t.table_schema = DATABASE()
      AND t.table_type = 'BASE TABLE'
      AND t.table_name <> 'alembic_version'
) AS x;


-- ---------------------------------------------------------------------------
-- 3. Os procedimentos
-- ---------------------------------------------------------------------------
SELECT routine_name AS procedimento
  FROM information_schema.routines
 WHERE routine_schema = DATABASE() AND routine_name LIKE 'martelo_%'
 ORDER BY routine_name;
-- Esperado: 5 linhas.


-- ---------------------------------------------------------------------------
-- 4. Quem ja' tem conta do Martelo
-- ---------------------------------------------------------------------------
SELECT to_user AS conta, from_user AS perfil
  FROM mysql.role_edges
 WHERE from_user IN ('martelo_normal', 'martelo_admin')
 ORDER BY from_user, to_user;
-- Antes de criar as contas: 0 linhas. Depois: uma por pessoa.
