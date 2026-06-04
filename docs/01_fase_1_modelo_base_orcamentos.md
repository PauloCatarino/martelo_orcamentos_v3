# Fase 1 - Modelo base de orcamentos

## Objetivo

A Fase 1 tem como objetivo definir e implementar a base estrutural dos orcamentos no Martelo Orcamentos V3. Esta fase concentra-se no modelo de dados inicial, nas entidades principais e na forma como os orcamentos passam a ser organizados por versoes independentes.

Nesta etapa ainda nao sera criado o motor de custeio, nem serao migrados dados do Martelo V2. A area de producao tambem fica reservada para uma fase posterior.

## Principios do modelo

O Martelo Orcamentos V3 separa o conceito de orcamento do conceito de versao.

O `Orcamento` representa o registo principal e estavel do processo comercial. A `OrcamentoVersao` representa uma proposta concreta, com os seus proprios itens, variaveis e estado. Assim, o mesmo orcamento pode ter varias versoes sem que uma alteracao numa versao modifique automaticamente as restantes.

Cada versao e independente. Isto significa que os itens e variaveis pertencem a uma versao especifica e devem ser tratados como um conjunto fechado de dados para essa proposta. Esta separacao permite preservar historico, comparar alternativas e manter versoes antigas sem depender do estado atual de outras versoes.

A numeracao comercial das versoes, como `260001_01`, `260001_02` ou `260001_03`, sera representada por dois campos:

- `num_orcamento`: numero base do orcamento, por exemplo `260001`;
- `numero_versao`: numero sequencial da versao, por exemplo `1`, `2` ou `3`.

A apresentacao formatada, como `260001_01`, pode ser derivada destes dois valores.

## Fora do ambito desta fase

Nesta fase nao serao implementados:

- custeio, calculos industriais ou regras de preco;
- migracao de dados do Martelo V2;
- funcionalidades de producao;
- fluxos completos de aprovacao, emissao ou faturacao;
- importacao automatica de historico.

O foco e criar uma fundacao coerente para suportar estes modulos em fases posteriores.

## Entidades iniciais

### User

Representa um utilizador do sistema. Nesta fase, a entidade serve como base para autoria, rastreabilidade e futura gestao de permissoes.

### Cliente

Representa a entidade comercial para quem um orcamento e criado. Deve guardar os dados essenciais de identificacao e contacto.

### Orcamento

Representa o processo principal de orcamento. Mantem o numero base e a ligacao ao cliente, mas nao contem diretamente os itens da proposta. Os itens pertencem sempre a uma versao.

### OrcamentoVersao

Representa uma versao concreta de um orcamento. Cada versao tem o seu proprio numero sequencial, estado e conjunto independente de itens.

### OrcamentoItem

Representa uma linha ou componente dentro de uma versao de orcamento. Nesta fase, o item deve permitir descrever a estrutura base da proposta sem aplicar ainda logica de custeio.

### OrcamentoItemVariavel

Representa uma variavel associada a um item de uma versao. Sera usada para guardar parametros relevantes do item, mas sem executar ainda calculos de custo nesta fase.

## Campos principais previstos

| Entidade | Campos principais previstos | Observacoes |
| --- | --- | --- |
| `User` | `id`, `nome`, `email`, `ativo`, `created_at`, `updated_at` | Base para autoria e futura gestao de permissoes. |
| `Cliente` | `id`, `nome`, `nif`, `email`, `telefone`, `morada`, `created_at`, `updated_at` | Dados comerciais essenciais do cliente. |
| `Orcamento` | `id`, `num_orcamento`, `cliente_id`, `titulo`, `estado`, `created_by_id`, `created_at`, `updated_at` | Registo principal do processo; nao contem itens diretamente. |
| `OrcamentoVersao` | `id`, `orcamento_id`, `numero_versao`, `estado`, `observacoes`, `created_by_id`, `created_at`, `updated_at` | Cada versao e independente e representa uma proposta concreta. |
| `OrcamentoItem` | `id`, `orcamento_versao_id`, `ordem`, `referencia`, `descricao`, `quantidade`, `unidade`, `created_at`, `updated_at` | Linha base da proposta dentro de uma versao. |
| `OrcamentoItemVariavel` | `id`, `orcamento_item_id`, `nome`, `valor`, `tipo_valor`, `unidade`, `created_at`, `updated_at` | Parametros associados ao item, ainda sem logica de custeio. |

## Resultado esperado da Fase 1

No final da Fase 1, o projeto deve ter o modelo base de orcamentos preparado para suportar criacao de clientes, orcamentos, versoes, itens e variaveis. Esta base deve permitir evoluir para custeio, migracao, producao e interface operacional sem misturar responsabilidades logo na primeira etapa.
