# Fase 3 — Custeio Simplificado

O modo **Simplificado** é definido por item e é independente de **Produção**
(`STD`/`SERIE`). Em Standard, o cálculo existente mantém-se inalterado.

## Regras aplicadas

- O escalão conta a quantidade total das linhas `PECA` ativas do próprio item.
- Escalões: 1–4, 5–14, 15–24 e **>=25**. Logo, exatamente 25 peças recebe o
  escalão mais favorável. Todas as peças contam para o escalão, incluindo as
  de espessura > 19 mm.
- **Espessura <= 19 mm**: corte é tarifa por peça x quantidade da linha;
  PUR/LASER são tarifas de quatro lados: `tarifa / 4 x lados orlados x
  quantidade`. PUR é o valor predefinido; LASER pode ser escolhido por linha
  de peça quando o item está em Simplificado.
- **Espessura > 19 mm** (lida de `esp_real`, que vem do material): tarifa
  própria sem escalões — corte por peça (2,85 € por defeito) e orlagem por
  lado orlado (1,15 € por defeito, código de orlas `2222`=4 lados, `2100`=2,
  `0022`=2, ...). Acima de 19 mm PUR e LASER pagam o mesmo.
- **Urgência**: valor ÚNICO por item, escolhido pelo escalão (2,30 / 1,85 /
  1,70 / 40,00 € por defeito). Nunca multiplica pela quantidade de peças.
- `Sem listagem Excel (+0,10 €/peça)` continua por peça. Ambas as opções são
  do item (botão **Opções Simplificado**, visível só em Simplificado) e
  entram no fim do custo, no bloco Produção.
- As tarifas ficam em **Configurações > Tarifas Custeio Simplificado**: a
  tabela dos escalões (<=19 mm) e a tabela própria de espessura > 19 mm. A
  edição só aceita números (dígitos + um separador decimal, ponto ou vírgula;
  a vírgula é convertida em ponto ao guardar). Guardar novas tarifas não
  reescreve orçamentos automaticamente: atualize o item para lhes aplicar os
  novos valores.
- **Colar do Excel**: na tabela de custeio, com o cursor na coluna Comp (ou
  Larg) e um bloco numérico copiado do Excel, Ctrl+V preenche Comp e Larg das
  linhas PEÇA seguintes (divisões/separadores/compostas são saltados). Texto
  não numérico nunca é aceite; Esp continua a vir do material.
- **Relatórios > Custeio Simplificado**: separador com o resumo por item —
  nº de peças, escalão aplicado, peças <=19 / >19 mm, custos de corte e
  orlagem, urgência e "sem Excel" considerados e o total simplificado (por
  unidade de item).

## Roteiro manual

1. Execute a migração `alembic upgrade head` (inclui `20260726_65`).
2. Em Configurações, abra **Tarifas Custeio Simplificado** e confirme os
   valores iniciais: corte 2,40/1,95/1,55/1,15; PUR 3,60/3,00/2,60/2,40;
   LASER 4,60/4,00/3,60/3,40; urgência 2,30/1,85/1,70/40,00 (€/item);
   espessura > 19 mm: corte 2,85 e orlagem 1,15 €/lado.
3. No orçamento, em **Items**, altere a coluna **Custeio** de um item para
   **Simplificado**. Confirme que a coluna Produção continua a permitir
   STD/SERIE sem ser alterada.
4. Abra o Custeio desse item. Em cada linha `PECA`, escolha PUR ou LASER na
   coluna **Orlagem simp.**. Confirme, por exemplo, que `2000` cobra 1/4 da
   tarifa e `2222` cobra a tarifa completa.
5. Numa peça com material de espessura > 19 mm, confirme corte 2,85 €/peça e
   orlagem 1,15 € x lados orlados, igual em PUR e LASER.
6. Crie/ajuste linhas até perfazer 25 peças ativas e clique **Atualizar**.
   Confirme o corte de 1,15 €/peça e PUR de 2,40 € para quatro lados.
7. Em **Opções Simplificado**, teste Urgente e Sem listagem Excel. Com 25
   peças, confirme 40,00 € de urgência (valor único) e 2,50 € sem Excel no
   custo produzido; com 10 peças, urgência 1,85 € (não multiplica).
8. Copie duas colunas (Comp, Larg) de um Excel, selecione a célula Comp da
   primeira peça e faça Ctrl+V: as medidas descem pelas linhas de peça.
9. Em **Relatórios**, abra o separador **Custeio Simplificado** e confirme o
   resumo do item (escalão, peças >19 mm, urgência, sem Excel, total).
10. Volte a Standard e atualize: os custos passam novamente a seguir as
    máquinas e tarifas STD/SERIE existentes; as opções Simplificado deixam de
    contribuir.
