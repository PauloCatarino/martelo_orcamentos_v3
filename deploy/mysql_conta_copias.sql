-- ---------------------------------------------------------------------------
-- Conta MySQL para as copias de seguranca do Martelo V3
-- (o nome do ficheiro evita de proposito o sufixo "_backup.sql": essa regra do
--  .gitignore existe para nenhum DUMP da base ir parar ao repositorio publico)
-- ---------------------------------------------------------------------------
--
-- CORRER UMA VEZ, COM A CONTA root, no MySQL Workbench.
--
-- Porque e' que a copia precisa de uma conta so' dela
-- ---------------------------------------------------
-- 1. A conta de manutencao (martelo_v3) tem ALL PRIVILEGES nas bases, mas nao
--    consegue ler o CORPO dos procedimentos: eles foram criados pelo root, e o
--    MySQL 8 exige o privilegio SHOW_ROUTINE para ver procedimentos alheios.
--    Sem isso a copia sai sem o `martelo_aplicar_grants` -- e uma base
--    restaurada sem ele e' uma base onde nenhum colega consegue trabalhar.
--
-- 2. A copia corre sozinha, todas as noites, agendada no Windows. Uma tarefa
--    automatica nao deve ter poder para escrever nada: se um dia correr o
--    comando errado, o pior que pode acontecer e' nao copiar.
--
-- Por isso: le tudo, nao escreve nada.
--
-- DEPOIS DE CORRER ISTO
-- ---------------------
-- Escolha uma password e ponha-a no lugar de COLOQUE_AQUI_UMA_PASSWORD (duas
-- vezes: aqui em baixo e no ficheiro .env de quem corre as copias).
-- Confirme no fim com a seccao 3.
-- ---------------------------------------------------------------------------


-- ---------------------------------------------------------------------------
-- 1. A conta
-- ---------------------------------------------------------------------------
-- Fica limitada a localhost: as copias correm no proprio servidor. Se um dia
-- passarem a correr noutra maquina, troque 'localhost' pelo IP dessa maquina.

CREATE USER IF NOT EXISTS 'martelo_backup'@'localhost'
    IDENTIFIED BY 'admin123';


-- ---------------------------------------------------------------------------
-- 2. Os privilegios -- todos de leitura
-- ---------------------------------------------------------------------------
-- SELECT       ler os dados
-- SHOW VIEW    ler a definicao das vistas
-- TRIGGER      ler os gatilhos
-- EVENT        ler os eventos agendados
-- LOCK TABLES  rede de seguranca, caso um dia se tire o --single-transaction
--
-- Repita o bloco para cada base que queira copiar.

GRANT SELECT, SHOW VIEW, TRIGGER, EVENT, LOCK TABLES
    ON `martelo_v3`.* TO 'martelo_backup'@'localhost';

GRANT SELECT, SHOW VIEW, TRIGGER, EVENT, LOCK TABLES
    ON `martelo_v3_dev`.* TO 'martelo_backup'@'localhost';

-- O SHOW_ROUTINE e' global (nao se pode dar so' a uma base) e e' o que permite
-- ler o corpo dos procedimentos. Sem isto, a copia sai incompleta e o script
-- de backup recusa-se a dar por boa.
GRANT SHOW_ROUTINE ON *.* TO 'martelo_backup'@'localhost';

FLUSH PRIVILEGES;


-- ---------------------------------------------------------------------------
-- 3. Confirmar
-- ---------------------------------------------------------------------------
-- Deve mostrar o SHOW_ROUTINE em *.* e o SELECT... em cada base.

SHOW GRANTS FOR 'martelo_backup'@'localhost';


-- ---------------------------------------------------------------------------
-- 4. Desfazer (se um dia for preciso)
-- ---------------------------------------------------------------------------
-- Apaga SO' a conta das copias. Nao toca em dados nenhuns.
--
--     DROP USER 'martelo_backup'@'localhost';
--
-- ---------------------------------------------------------------------------


-- ---------------------------------------------------------------------------
-- 5. Alternativa rapida (se nao quiser criar conta nova)
-- ---------------------------------------------------------------------------
-- Da' a` conta de manutencao o direito de ler os procedimentos. Resolve o
-- problema da copia, mas continua a ser uma conta com poder de escrita a
-- correr sozinha todas as noites -- por isso a conta propria e' melhor.
--
--     GRANT SHOW_ROUTINE ON *.* TO 'martelo_v3'@'localhost';
--     FLUSH PRIVILEGES;
--
-- ---------------------------------------------------------------------------
