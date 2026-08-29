-- ===========================================================================
-- Dar a toda a gente acesso ao ARQUIVO DO MARTELO V2 (base `orcamentos_v2`)
-- ===========================================================================
--
-- CORRER UMA VEZ, no MySQL Workbench, ligado como `root`.
-- Depois disto ninguem tem de correr isto outra vez -- nem quando entrar gente
-- nova, porque os privilegios ficam nos PERFIS (`martelo_normal` e
-- `martelo_admin`) e nao em cada pessoa.
--
--
-- PORQUE E' QUE ISTO EXISTE
-- -------------------------
-- Os orcamentos antigos continuam na base do Martelo V2 (`orcamentos_v2`), no
-- mesmo servidor MySQL onde vive o V3. O menu "Arquivo V2" do V3 vai la' busca-
-- los.
--
-- Ate' agora, para chegar la', ia no `.env` de cada PC uma segunda conta com
-- utilizador e password escritos no ficheiro. E a conta que la' estava era a
-- `orc_user` -- a MESMA com que o Martelo V2 trabalha, com ESCRITA em tudo.
-- Quem abrisse esse ficheiro com o Bloco de Notas ficava com ela e podia
-- alterar os orcamentos antigos por fora dos dois programas.
--
-- Agora o V3 consulta o arquivo com a conta de quem ENTROU na aplicacao. Nao
-- ha' segunda password em ficheiro nenhum, e quem pode ler o arquivo decide-se
-- aqui, uma vez, no servidor.
--
--
-- PORQUE E' QUE NAO E' `GRANT SELECT ON orcamentos_v2.*`
-- ------------------------------------------------------
-- Porque a tabela `users` do V2 guarda as PASSWORDS (coluna `pass_hash`). Dar
-- a base inteira punha essas passwords a` vista de toda a gente. Por isso
-- damos tabela a tabela, e da `users` so' as duas colunas de que o V3 precisa
-- para mostrar quem criou o orcamento.
--
-- A escrita e' so' na tabela `orcamentos`, e mesmo essa o V3 limita a tres
-- campos (Estado, Enc PHC e preco manual). Os precos de custeio ficam
-- protegidos pelo proprio programa.
-- ===========================================================================


-- --- Leitura: o que o menu "Arquivo V2" precisa de ver --------------------
GRANT SELECT ON `orcamentos_v2`.`orcamentos`
    TO 'martelo_normal', 'martelo_admin';

GRANT SELECT ON `orcamentos_v2`.`orcamento_items`
    TO 'martelo_normal', 'martelo_admin';

GRANT SELECT ON `orcamentos_v2`.`clients`
    TO 'martelo_normal', 'martelo_admin';

-- Da `users` SO' o id e o nome. A coluna das passwords fica de fora e continua
-- inacessivel, mesmo para quem tente por SQL.
GRANT SELECT (`id`, `username`) ON `orcamentos_v2`.`users`
    TO 'martelo_normal', 'martelo_admin';

-- A Producao do V3 compara as obras com as do V2 (menu Producao ->
-- "Sincronizar V2"). Sem isto esse botao dá erro de acesso.
GRANT SELECT ON `orcamentos_v2`.`producao`
    TO 'martelo_normal', 'martelo_admin';


-- --- Escrita: so' na tabela dos orcamentos ---------------------------------
-- E' o que faz o "Editar selecionado" do Arquivo V2 gravar o Estado, o Enc PHC
-- e o preco manual na lista que o V2 tambem le^. Tudo o resto continua barrado:
-- nao ha' INSERT, nao ha' DELETE, e nao ha' acesso a mais nenhuma tabela.
GRANT UPDATE ON `orcamentos_v2`.`orcamentos`
    TO 'martelo_normal', 'martelo_admin';


FLUSH PRIVILEGES;


-- ===========================================================================
-- CONFERIR (deve mostrar as linhas de cima, e NENHUMA a dizer `orcamentos_v2`.*)
-- ===========================================================================
SHOW GRANTS FOR 'martelo_normal';
SHOW GRANTS FOR 'martelo_admin';

-- Nota: quem ja' estiver com o Martelo aberto tem de SAIR e ENTRAR outra vez
-- para apanhar os privilegios novos. O MySQL so' os le^ quando a ligacao nasce.


-- ===========================================================================
-- SO' DEPOIS DE ISTO ESTAR TESTADO: tirar a conta partilhada dos .env
-- ===========================================================================
-- Enquanto houver um PC com o `.env` antigo (com V2_DB_USER=orc_user), esse PC
-- continua a usar a conta partilhada -- o programa da' prioridade ao que estiver
-- no ficheiro. Para fechar mesmo a porta, apagar essas duas linhas do `.env` de
-- cada maquina:
--
--   V2_DB_USER=...
--   V2_DB_PASSWORD=...
--
-- O instalador oficial ja' sai sem elas. So' falta a maquina de manutencao.
--
-- NAO tirar privilegios ao `orc_user`: e' a conta com que o Martelo V2
-- TRABALHA. Ja' aconteceu uma vez e parou o V2 em todos os PCs.
