-- Executar por administrador na base V3 selecionada, após migração 20260908_111.
-- Apenas a nova tabela operacional. Não altera system_settings nem contas.
SET @base_custos = DATABASE();
SET @sql_custos = CONCAT('GRANT SELECT, INSERT, UPDATE ON `', REPLACE(@base_custos,'`','``'), '`.`lista_material_custo_mapeamentos` TO ''martelo_normal'', ''martelo_admin''');
PREPARE stmt_custos FROM @sql_custos;
EXECUTE stmt_custos;
DEALLOCATE PREPARE stmt_custos;
