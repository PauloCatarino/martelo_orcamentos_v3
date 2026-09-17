-- ===========================================================================
-- Martelo V3 -- dar à conta de administrador o direito de criar utilizadores
-- ===========================================================================
--
-- SINTOMA (17-09-2026, ao criar o utilizador "Ruben Pereira"):
--
--   Nao foi possivel criar a conta na base de dados: execute command denied
--   to user 'admin'@'%' for routine 'martelo_v3.martelo_criar_utilizador'
--
-- O QUE ISTO QUER DIZER: quem cria contas no Martelo não mexe no servidor
-- diretamente -- chama procedimentos que o root deixou preparados
-- (`mysql_contas_beta.sql`). Só o perfil `martelo_admin` os pode chamar. A
-- conta `admin` está a ligar-se sem esse direito: ou ficou com o perfil
-- `martelo_normal`, ou os EXECUTE foram dados noutra base (a beta, que já foi
-- eliminada) e nunca nesta.
--
-- ESTE FICHEIRO repõe as duas coisas e pode correr-se as vezes que forem
-- precisas (não estraga nada se já estiver bem). NÃO toca em dados nem cria
-- contas novas.
--
-- COMO CORRER (precisa do root -- é de propósito, é esse o objetivo destes
-- procedimentos):
--
--   mysql -h 127.0.0.1 -u root -p martelo_v3 < deploy\mysql_corrigir_admin_contas.sql
--
-- ou no MySQL Workbench, na ligação que entra como root.
-- ===========================================================================

-- A base onde os procedimentos vivem. Trocar aqui se for noutra.
USE martelo_v3;
SELECT CONCAT('>>> Vai aplicar em: ', DATABASE(), ' <<<') AS confirme_a_base;

-- A conta do Martelo que administra os utilizadores.
SET @conta = 'admin';


-- 1. Quem pode chamar os procedimentos -----------------------------------
-- (repete o fim do mysql_contas_beta.sql; um DROP/CREATE do procedimento leva
--  os GRANT atrás, por isso vale a pena poder repor sem correr o ficheiro todo)
GRANT EXECUTE ON PROCEDURE martelo_criar_utilizador  TO 'martelo_admin';
GRANT EXECUTE ON PROCEDURE martelo_repor_password    TO 'martelo_admin';
GRANT EXECUTE ON PROCEDURE martelo_apagar_utilizador TO 'martelo_admin';
GRANT EXECUTE ON PROCEDURE martelo_aplicar_grants    TO 'martelo_admin';
GRANT EXECUTE ON PROCEDURE martelo_mudar_a_minha_password
    TO 'martelo_normal', 'martelo_admin';


-- 2. A conta de administração leva o perfil de admin ----------------------
SET @sql = CONCAT('GRANT ''martelo_admin'' TO ', QUOTE(@conta), '@''%''');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Sem o DEFAULT ROLE a conta liga-se com o perfil por ativar -- é o engano
-- clássico dos roles do MySQL, e o erro seria exatamente o mesmo.
SET @sql = CONCAT('SET DEFAULT ROLE ALL TO ', QUOTE(@conta), '@''%''');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

FLUSH PRIVILEGES;


-- 3. Conferir -------------------------------------------------------------
SELECT to_user AS conta, from_user AS perfil
  FROM mysql.role_edges
 WHERE to_user = @conta;

SELECT user AS conta, default_role_user AS perfil_ativo_ao_entrar
  FROM mysql.default_roles
 WHERE user = @conta;

-- Deve aparecer o perfil `martelo_admin` nas duas grelhas. Depois disto,
-- FECHAR e voltar a abrir o Martelo com a conta admin (o perfil é escolhido
-- quando a ligação nasce) e criar o utilizador outra vez.
