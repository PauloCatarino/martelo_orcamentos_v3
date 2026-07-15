# Fase 3 — Custeio Simplificado

O modo **Simplificado** é definido por item e é independente de **Produção**
(`STD`/`SERIE`). Em Standard, o cálculo existente mantém-se inalterado.

## Regras aplicadas

- O escalão conta a quantidade total das linhas `PECA` ativas do próprio item.
- Escalões: 1–4, 5–14, 15–24 e **>=25**. Logo, exatamente 25 peças recebe o
  escalão mais favorável.
- Corte é tarifa por peça x quantidade da linha.
- PUR/LASER são tarifas de quatro lados: `tarifa / 4 x lados orlados x quantidade`.
  PUR é o valor predefinido; LASER pode ser escolhido por linha de peça quando o
  item está em Simplificado.
- Urgência e `Sem listagem Excel (+0,10 €/peça)` são opções do item e entram no
  fim do custo, no bloco Produção. Urgência em >=25 é fixa por item (40 €).
- As tarifas ficam em **Configurações > Tarifas Custeio Simplificado**. Guardar
  novas tarifas não reescreve orçamentos automaticamente: atualize o item para
  lhes aplicar os novos valores.

## Roteiro manual

1. Execute a migração `alembic upgrade head` (inclui `20260726_65`).
2. Em Configurações, abra **Tarifas Custeio Simplificado** e confirme os valores
   iniciais: corte 2,40/1,95/1,55/1,15; PUR 3,60/3,00/2,60/2,40; LASER
   4,60/4,00/3,60/3,40.
3. No orçamento, em **Items**, altere a coluna **Custeio** de um item para
   **Simplificado**. Confirme que a coluna Produção continua a permitir
   STD/SERIE sem ser alterada.
4. Abra o Custeio desse item. Em cada linha `PECA`, escolha PUR ou LASER na
   coluna **Orlagem simp.**. Confirme, por exemplo, que `2000` cobra 1/4 da
   tarifa e `2222` cobra a tarifa completa.
5. Crie/ajuste linhas até perfazer 25 peças ativas e clique **Atualizar**.
   Confirme o corte de 1,15 €/peça e PUR de 2,40 € para quatro lados.
6. Em **Opções Simplificado**, teste Urgente e Sem listagem Excel. Com 25
   peças, confirme 40,00 € de urgência e 2,50 € sem Excel no custo produzido.
7. Volte a Standard e atualize: os custos passam novamente a seguir as máquinas
   e tarifas STD/SERIE existentes; as opções Simplificado deixam de contribuir.
