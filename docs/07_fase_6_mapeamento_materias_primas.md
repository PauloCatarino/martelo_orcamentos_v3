# Fase 6 - Mapeamento do Excel de materias-primas para o Martelo V3

## Objetivo

Este documento descreve como os dados do Excel `TAB_MATERIAS_PRIMAS.xlsm` devem ser interpretados e mapeados, no futuro, para o modelo interno do Martelo V3.

Usa como base a analise estrutural ja feita em `docs/06_fase_6_analise_excel_materias_primas.md` e os modelos conceptuais de `docs/04_fase_6_modelo_ferragens_operacoes.md` e `docs/05_fase_6_modelo_valuesets_materiais.md`.

Esta fase e apenas documentacao. Nao deve ser criado codigo, models, migrations, UI nem importacao real de dados.

## O Excel como fonte externa atual

Por enquanto, o ficheiro `TAB_MATERIAS_PRIMAS.xlsm` e a fonte externa das materias-primas. Contem materiais, ferragens, acessorios, SPP e afins, com codigos, descricoes, precos, unidades, dimensoes e classificacao por `TIPO` e `FAMILIA`.

No futuro, estes dados poderao ser importados e mapeados para uma tabela interna do Martelo V3 (`def_materias_primas`). A importacao deve, no entanto, preservar a possibilidade de atualizacao a partir do Excel, ou seja, deve ser possivel voltar a sincronizar precos e dados sem perder o trabalho ja feito dentro do Martelo V3.

## Naturezas das materias-primas

As materias-primas nao sao todas da mesma natureza. O catalogo agrupa, pelo menos:

- placas / paineis;
- orlas;
- ferragens;
- acessorios;
- SPP / barras / ML;
- iluminacao / LEDs;
- acabamentos;
- sistemas de correr;
- outros.

Cada natureza pode ter regras, unidades e campos relevantes diferentes, mesmo que partilhem a mesma tabela base.

## Tipos e familias do Excel nao sao categorias finais

Os valores das colunas `TIPO` e `FAMILIA` do Excel **nao devem virar categorias finais do Martelo V3 sem revisao**.

Como mostrado em `docs/06`, existem 17 valores de `TIPO` (por exemplo `AGLOMERADO`, `FERRAGENS`, `CORREDICAS`, `ILUMINACAO`, `ROUPEIROS CORRER`, `VERNIZ`, `VIDRO`) e 4 de `FAMILIA` (`FERRAGENS`, `PLACAS`, `ACABAMENTOS`, `ORLA`). Alguns sao redundantes, outros sao comerciais e nao tecnicos, e outros precisam de ser fundidos ou renomeados. A definicao dos grupos finais deve ser feita com criterio tecnico.

## Modelo conceptual futuro: def_materias_primas

Propoe-se, apenas em conceito, uma tabela interna `def_materias_primas` para o catalogo do Martelo V3.

| Campo | Descricao | Origem no Excel |
| --- | --- | --- |
| `id` | Identificador interno do Martelo V3. | (novo) |
| `ref_le` | Referencia LE, usada como chave de correspondencia. | `Ref_LE` |
| `referencia_fornecedor` | Referencia do fornecedor. | `REF_FORNECEDOR` |
| `descricao` | Descricao usada no orcamento. | `DESCRICAO_no_ORCAMENTO` |
| `tipo_original_excel` | Tipo tal como vem do Excel, sem alterar. | `TIPO` |
| `familia_original_excel` | Familia tal como vem do Excel, sem alterar. | `FAMILIA` |
| `tipo_martelo` | Tipo normalizado/revisto para o Martelo V3. | (derivado, revisto) |
| `familia_martelo` | Familia normalizada/revista para o Martelo V3. | (derivado, revisto) |
| `unidade` | Unidade de medida/calculo. | `UND` |
| `preco_tabela` | Preco de tabela. | `PRECO_TABELA` |
| `desconto` | Desconto aplicado. | `DESC2_(-)` |
| `margem` | Margem aplicada. | `MRG_(+)` |
| `preco_liquido` | Preco liquido calculado. | `PLIQ` |
| `comprimento` | Comprimento (logica Comp / Larg / Esp). | `COMP_MP` |
| `largura` | Largura. | `LARG_MP` |
| `espessura` | Espessura. | `ESP_MP` |
| `fornecedor` | Nome do fornecedor. | `NOME_FORNECEDOR` |
| `ativo` | Indica se a materia-prima esta ativa. | (novo) |
| `origem_dados` | Origem do registo: por exemplo `EXCEL` ou `MANUAL`. | (novo) |
| `data_importacao` | Data da ultima importacao/sincronizacao. | (novo) |
| `observacoes` | Notas livres. | `NOTAS_*` |

A estrutura concreta (tipos, chaves, indices, constraints) sera decidida numa fase posterior.

## Tipo/familia original vs tipo/familia Martelo

O modelo separa, de proposito, os campos originais do Excel dos campos do Martelo:

- `tipo_original_excel` e `familia_original_excel` guardam o valor **exatamente como vem do Excel**, sem limpeza. Servem para rastreabilidade e para nao perder a origem.
- `tipo_martelo` e `familia_martelo` guardam a classificacao **ja revista e normalizada** para o Martelo V3 (por exemplo, mapear `CORREDICAS` para o grupo `CORREDICAS`, ou decidir que `ROUPEIROS CORRER` vira `SISTEMAS_CORRER`).

Esta separacao permite reimportar do Excel e continuar a comparar, sem perder os ajustes feitos no Martelo V3.

## ref_le como chave de correspondencia

A coluna `Ref_LE` deve ser tratada como **chave importante de correspondencia** entre o Excel e o Martelo V3.

Usar `ref_le` como chave permite atualizar dados vindos do Excel (precos, descricoes, dimensoes) sem depender apenas da descricao ou do preco, que podem mudar. Quando uma materia-prima do Excel tiver a mesma `ref_le` de um registo ja existente, a atualizacao deve recair sobre esse registo, em vez de criar um duplicado.

Isto exige que `ref_le` seja, idealmente, unica e estavel. Casos de `ref_le` vazia ou duplicada precisam de tratamento especifico (ver decisoes pendentes).

## As materias-primas nao se ligam a def_pecas

Tal como definido em `docs/05`, as materias-primas **nao sao ligadas diretamente a `def_pecas`**. A definicao da peca guarda apenas comportamento tecnico e um grupo logico; o material concreto e resolvido mais tarde.

A cadeia correta e:

```text
def_pecas
  -> grupo logico / comportamento tecnico
configuracao do orcamento / item
  -> escolhe a materia-prima real
linha de custeio
  -> usa materia-prima herdada ou override manual
```

Assim, a mesma `def_peca` (por exemplo `PORTA`) pode usar materiais diferentes em orcamentos diferentes, sem duplicar a definicao.

## O que o Excel alimenta no Martelo V3

O Excel (atraves do futuro catalogo `def_materias_primas`) pode alimentar:

- o catalogo de materias-primas do Martelo V3;
- as escolhas disponiveis nos **Dados Gerais** do orcamento;
- as escolhas disponiveis nos **Dados do Item**;
- a selecao manual/local na **linha de custeio**.

Em todos estes pontos, o utilizador escolhe a partir do catalogo, mas a escolha concreta pertence ao orcamento, ao item ou a linha, nao a definicao da peca.

## Edicao local na linha de custeio

O utilizador pode **editar localmente** uma materia-prima na linha de custeio (descricao, preco, margem, medidas, fornecedor, referencia, observacoes) sem criar uma nova materia-prima global. Muitas materias-primas sao usadas uma unica vez e nao devem poluir o catalogo.

As linhas editadas localmente devem mostrar um aviso visual claro, por exemplo:

```text
⚠ Editado localmente
```

Quando houver atualizacao de precos a partir do Excel, as linhas com override manual **nao devem ser sobrescritas automaticamente sem confirmacao** do utilizador. O sistema deve preservar o ajuste manual e, no maximo, avisar que existe um valor de catalogo diferente.

## Grupos Martelo iniciais

Proposta inicial de grupos do Martelo V3, ainda sujeita a revisao:

- `PLACAS`
- `ORLAS`
- `DOBRADICAS`
- `CORREDICAS`
- `PUXADORES`
- `SUPORTES`
- `VAROES`
- `SPP`
- `LEDS`
- `ILUMINACAO`
- `ACABAMENTOS`
- `SISTEMAS_CORRER`
- `OUTROS`

Estes grupos serao usados futuramente para **filtrar as escolhas** disponiveis nos Dados Gerais do orcamento, nos Dados do Item e no Custeio. Por exemplo, ao configurar o grupo `PORTAS`, o utilizador so vera materias-primas do grupo `PLACAS`; ao configurar dobradicas, so vera o grupo `DOBRADICAS`.

A lista final de grupos deve ser confirmada antes de implementar, podendo alguns ser fundidos (por exemplo `LEDS` e `ILUMINACAO`) ou divididos.

## Decisoes pendentes

Antes de criar a tabela e a importacao, devem ficar respondidas as seguintes perguntas:

- quais tipos/familias finais usar no Martelo V3?
- como limpar tipos antigos vindos do Excel?
- como lidar com `ref_le` duplicada ou vazia?
- como tratar materias-primas sem preco?
- como tratar unidades diferentes: `un`, `m2`, `ml`, `barra`, `kit`?
- como atualizar precos sem alterar orcamentos historicos?
- como criar snapshots de preco nos orcamentos?
- como tratar materias-primas temporarias usadas apenas num orcamento?

## Proxima fase sugerida

**Fase 6T** - criar o modelo/tabela `def_materias_primas`, ainda sem importacao automatica completa.

Esta fase seguinte deve focar-se em:

- definir os campos finais da tabela `def_materias_primas`;
- criar o model SQLAlchemy e a migration correspondente;
- preparar a estrutura para receber dados do Excel mais tarde;
- ainda sem ligar ao custeio nem a configuracao de orcamento.

A importacao real a partir do Excel e a integracao com os Dados Gerais, Dados do Item e Custeio devem ficar para fases posteriores.
