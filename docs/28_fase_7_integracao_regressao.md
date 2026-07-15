# Fase 7 — Integração e regressão (fecho do ciclo)

Fecho do plano faseado (fases 1–6): verificação assistida dos dados antigos,
testes focados de todas as fases e roteiro manual completo.

## Migração assistida com relatório

Novo comando (na raiz do projeto, com a app fechada):

```powershell
python -m alembic upgrade head
python -m scripts.relatorio_integracao_fases            # só relatório
python -m scripts.relatorio_integracao_fases --corrigir # aplica correções
```

O relatório mostra, por fase:

- **Base** — revisão alembic atual (esperada `20260729_68`);
- **Fase 2** — linhas de custeio com preço de orla local €/m² vs fallback;
- **Fase 3** — items por modalidade (Standard/Simplificado);
- **Fase 4** — versões por perfil de margens + margens UTILIZADOR antigas
  preservadas como histórico;
- **Fase 5** — versões com Nº Enc PHC vs encomendas registadas; deteta
  versões antigas só com `enc_phc` e espelhos divergentes;
- **Fase 6** — categorias de módulos (ativas/total); deteta códigos usados
  por módulos sem registo na tabela.

`--corrigir` aplica apenas correções determinísticas e idempotentes:
materializa encomendas PHC antigas como registo principal e completa a
tabela de categorias. **Nunca recalcula preços, margens ou custeios.**

## Estado da bateria automática

- 2150 testes passam; 1 ignorado.
- 9 falhas antigas conhecidas, anteriores a este ciclo (bcrypt no ambiente
  local e 2 testes do plano de corte) — sem relação com as fases 1–7.
- Testes focados por fase: `test_fase2_opcao_unica.py`,
  `test_materia_prima_snapshot.py` (orlas), `test_custeio_simplificado.py`,
  `test_margens_padrao_*`, `test_encomendas_phc_versao.py`,
  `test_modulo_categorias_geridas.py`, `test_integracao_fases.py`.

## Roteiro manual completo (regressão das fases)

1. **Migração**: `python -m alembic upgrade head` →
   `python -m scripts.relatorio_integracao_fases` → sem linhas [ATENÇÃO]
   (se houver, correr com `--corrigir` e confirmar que desaparecem).
2. **Fase 1 (opção única)**: abrir um modelo de ValueSet e confirmar a coluna
   simplificada "Opção" + código técnico na vista avançada.
3. **Fase 2 (orlas locais)**: num custeio, alterar a referência/preço local da
   orla de uma linha; alterar o preço global da matéria-prima e confirmar que
   a linha guardada NÃO muda.
4. **Fase 3 (Simplificado)**: num item, mudar a modalidade para Simplificado,
   testar quantidades em escalões diferentes (1–4, 5–14, 15–24, 25+) e
   confirmar que outro item do mesmo orçamento continua Standard.
5. **Fase 4 (margens)**: escolher perfil Cliente Final num orçamento, Repor
   Padrão, editar uma margem localmente e confirmar que outro orçamento não é
   afetado.
6. **Fase 5 (encomendas PHC)**: orçamento com 2+ encomendas; principal com
   `(+N)` na lista; converter cada encomenda para o seu processo de produção.
7. **Fase 6 (categorias)**: criar categoria com nome de cliente, gravar módulo
   nela, filtrar/importar, arquivar/reativar, testar permissões com um
   utilizador não-admin e Converter Âmbito nos dois sentidos.
8. **Conversão PHC + cálculo**: converter um orçamento adjudicado e comparar o
   preço total Standard vs Simplificado num item de teste.

Regra de trabalho mantida: cada fase foi entregue com testes automáticos,
guião manual e validação do utilizador antes da seguinte (F1–F4 validadas a
14/07/2026 no Codex; F5 e F6 validadas a 15/07/2026; F7 fecha o ciclo).
