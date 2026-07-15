# Fase 1 — snapshots locais de orlas em €/m²

## Regra funcional

As referências `coresp_orla_0_4` e `coresp_orla_1_0` continuam a identificar as
orlas fina e grossa. Os novos campos `preco_orla_0_4_m2` e
`preco_orla_1_0_m2` guardam o preço local em euros por metro quadrado (€/m²).

O cálculo de custeio mantém a conversão atual de €/m² para €/ML, usando a
largura de orla determinada pela espessura da peça. O preço local tem
precedência sobre a matéria-prima global.

## Propagação

```text
Modelo ValueSet
  -> ValueSet do orçamento
  -> ValueSet do item
  -> Linha de custeio
```

Ao selecionar uma placa, a aplicação copia a referência de cada orla e tenta
resolver o preço líquido da referência `ORL*` quando a unidade da orla é M2.
Cada nível permite substituir localmente a referência e o preço.

## Compatibilidade

As colunas são nullable para não alterar silenciosamente dados antigos. Se uma
linha antiga ainda não tiver preço snapshot, o custeio usa temporariamente a
referência no catálogo atual e grava uma observação de compatibilidade. A
edição e gravação da linha permite congelar o preço local.

## Migração

A revisão `20260725_64` adiciona as duas colunas de preço às tabelas de linhas
do Modelo ValueSet, ValueSet do orçamento, ValueSet do item e custeio. Não
remove nem reescreve referências existentes.
