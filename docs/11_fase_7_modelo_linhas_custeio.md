# Fase 7 - Modelo de geracao de linhas de custeio

## Objetivo

Este documento descreve como pecas, pecas compostas, ferragens, orlas, operacoes, maquinas e acabamentos devem gerar linhas de custeio dentro de um item de orcamento.

Serve de base tecnica e funcional antes de criar campos, tabelas, UI ou motor de calculo. Usa como contexto os modelos ja documentados em `docs/02` (pecas e pecas compostas), `docs/03` (orlas), `docs/05` (configuracao de materiais / ValueSets), `docs/09` (operacoes de producao) e `docs/10` (acabamentos).

Esta fase e apenas documentacao. Nao deve ser criado codigo, models, migrations, UI nem calculo neste momento.

## Um item gera varias linhas de custeio

O custeio de um item de orcamento **nao e apenas uma linha com um preco total**. Um item pode gerar varias linhas internas de custeio, cada uma representando uma parcela do custo.

Um item pode conter:

- modulos;
- pecas soltas;
- pecas compostas;
- ferragens soltas;
- acessorios;
- operacoes manuais;
- acabamentos;
- mao de obra;
- producao.

Cada um destes elementos pode dar origem a uma ou mais linhas de custeio.

## Origens de custo de uma peca

Uma unica peca pode gerar custos de varias naturezas:

- material principal / placa;
- area em m2;
- perimetro;
- metros lineares;
- orlas finas;
- orlas grossas;
- ferragens;
- acessorios;
- corte;
- orlagem;
- CNC / mecanizacao;
- furacoes;
- rasgos;
- cortes manuais;
- colagem;
- montagem;
- embalamento;
- acabamento face superior;
- acabamento face inferior;
- setup;
- operacoes manuais.

## O que uma linha de custeio identifica

Cada linha de custeio deve conseguir identificar a sua origem completa:

- orcamento;
- versao;
- item;
- modulo, se existir;
- peca, se existir;
- peca composta, se existir;
- componente, se existir;
- materia-prima, se existir;
- operacao, se existir;
- maquina, se existir;
- origem da linha.

Esta rastreabilidade permite reconstruir como cada custo foi obtido.

## Origem da linha de custeio

Cada linha tem um tipo de origem (`tipo_linha` / origem), de um conjunto controlado:

| Origem | Significado |
| --- | --- |
| `MATERIAL_PECA` | Material principal / placa da peca. |
| `ORLA_PECA` | Orla aplicada a um lado da peca. |
| `FERRAGEM` | Ferragem associada. |
| `ACESSORIO` | Acessorio associado. |
| `OPERACAO` | Operacao de producao. |
| `MAQUINA` | Custo associado a uma maquina. |
| `ACABAMENTO` | Acabamento de superficie de uma face. |
| `MAO_OBRA` | Mao de obra. |
| `SETUP` | Custo de preparacao / setup. |
| `MANUAL` | Linha introduzida manualmente. |
| `OUTRO` | Outra origem nao prevista. |

## Geracao a partir de uma peca simples

Uma peca simples usada no orcamento deve gerar, futuramente:

1. uma linha de material principal;
2. linhas de orlas, se aplicavel;
3. linhas de operacoes associadas a definicao da peca (ver `docs/09` e a ligacao `def_peca_operacoes`);
4. linhas de acabamento, se aplicavel;
5. linhas de ferragens / acessorios, se existirem via peca composta ou insercao manual.

## Pecas compostas: expandir componentes

Uma peca composta deve expandir os seus componentes. Cada componente pode gerar as suas proprias linhas de custeio.

```text
GAVETA
  - LADO_GAVETA
  - TRASEIRA_GAVETA
  - FUNDO_GAVETA
  - FRENTE_GAVETA
  - CORREDICA
  - PUXADOR
```

Cada peca componente (LADO_GAVETA, FRENTE_GAVETA, etc.) segue a logica de peca simples (material, orlas, operacoes, acabamento); cada ferragem (CORREDICA, PUXADOR) segue a logica de ferragem.

## Ferragens e acessorios

As ferragens **nao tem calculo de area, orla ou acabamento**. Normalmente geram custo por unidade, kit, par, conjunto, ml ou outra unidade definida.

A quantidade de uma ferragem ou acessorio pode depender de:

- quantidade fixa;
- quantidade da peca;
- quantidade do modulo;
- altura / comprimento / largura da peca;
- regras dos componentes associados;
- override manual.

## Operacoes manuais ao nivel do item

Operacoes manuais podem ser adicionadas diretamente ao item, **sem peca associada**. Exemplos:

- colagem especial;
- furacao manual;
- rasgo manual;
- montagem especial;
- embalagem especial;
- transporte interno;
- corte manual.

Estas linhas tem origem `OPERACAO` ou `MANUAL` e nao dependem de uma peca.

## Orlas

As orlas dependem de:

- codigo de orlas da peca, por exemplo `[2200]` (ver `docs/03`);
- dimensoes da peca;
- lado da peca: `C1`, `C2`, `L1`, `L2`;
- tipo de orla: sem orla, orla fina, orla grossa;
- materia-prima de orla configurada;
- quantidade de pecas.

Calculo conceptual de orlas:

```text
C1/C2 usam o comprimento da peca
L1/L2 usam a largura da peca

ml_orla = soma dos lados com orla (em metros) * quantidade
```

A orla fina e a orla grossa podem ter precos diferentes, por isso devem ser somadas em parcelas separadas (`ml_orla_fina`, `ml_orla_grossa`). Alem do material de orla, a operacao de **orlagem** tambem pode gerar um custo de producao separado.

## Material principal / placa

O material principal depende de:

- da peca;
- do grupo logico da peca;
- da configuracao do orcamento / item (ver `docs/05`);
- da materia-prima selecionada;
- da area da peca;
- da espessura;
- da quantidade;
- da unidade de compra / calculo.

Calculo conceptual de material de placa:

```text
area_m2 = comp * larg
custo_material = area_m2 * preco_m2 * quantidade
```

Nota: as medidas devem ser normalizadas para metros antes de calcular m2. As medidas seguem a logica de peca horizontal (Comp / Larg / Esp), sem usar a designacao Altura.

## Operacoes de producao

As operacoes dependem de:

- das operacoes associadas a definicao da peca (`def_peca_operacoes`);
- da maquina associada a operacao;
- da regra de calculo;
- da quantidade;
- da area;
- dos metros lineares;
- do setup;
- do tempo base;
- do custo / hora;
- do custo minimo;
- do override manual.

Importante: as operacoes associadas a `def_pecas` **ainda nao calculam automaticamente**. Elas apenas definem que a peca tem necessidade daquela operacao. O calculo real sera feito numa fase posterior.

Regras de calculo possiveis para operacoes (ver dominio `regra_operacao_types`):

- `FIXA`
- `POR_PECA`
- `POR_QUANTIDADE`
- `POR_ML`
- `POR_M2`
- `POR_AREA_FACE`
- `POR_ORLAS`
- `POR_FURACAO`
- `POR_SETUP`
- `MANUAL`

## Acabamentos

Os acabamentos dependem de (ver `docs/10`):

- se a peca permite acabamento;
- acabamento `face_sup`;
- acabamento `face_inf`;
- area da face;
- quantidade;
- preco por m2;
- custo minimo;
- setup;
- mao de obra;
- override manual.

Calculo conceptual de acabamento:

```text
area_face = comp * larg
custo_face_sup = area_face * preco_acabamento_sup
custo_face_inf = area_face * preco_acabamento_inf
custo_total = quantidade * (custo_face_sup + custo_face_inf)
```

Nem todas as pecas tem acabamento. **As ferragens nunca devem ter acabamento.** As pecas compostas podem ter componentes com acabamento diferente.

## Override manual nas linhas

As linhas de custeio devem permitir override manual. O utilizador pode:

- alterar a descricao;
- alterar a materia-prima;
- alterar o preco;
- alterar a quantidade;
- alterar a margem;
- alterar a operacao;
- alterar o tempo;
- alterar observacoes.

Quando existir override manual, deve aparecer um aviso visual claro:

```text
⚠ Editado localmente
```

## Snapshot dos valores usados

Cada linha de custeio deve guardar um snapshot dos valores usados, para preservar o historico:

- descricao da materia-prima;
- referencia;
- preco usado;
- unidade;
- quantidade;
- custo unitario;
- custo total;
- margem;
- preco final;
- origem dos dados.

## Orcamentos historicos nao mudam automaticamente

Os orcamentos historicos **nao devem mudar automaticamente** quando:

- o preco da materia-prima muda;
- a maquina muda o custo / hora;
- uma operacao e desativada;
- a definicao da peca e alterada;
- um modulo de biblioteca e alterado.

Gracas ao snapshot, um orcamento fechado mantem os valores com que foi calculado.

## Rastreabilidade da origem da linha

Uma linha de custeio deve conseguir indicar se veio de:

- configuracao do orcamento;
- configuracao do item;
- modulo;
- peca;
- operacao automatica;
- introducao manual;
- override local.

## Entidades futuras propostas (apenas conceito)

As seguintes entidades sao apenas conceito e nao devem ser criadas nesta fase:

| Entidade conceptual | Funcao prevista |
| --- | --- |
| `orcamento_item_custeio_linhas` | Linhas de custeio detalhadas de um item. |
| `orcamento_item_pecas` | Pecas aplicadas a um item de orcamento. |
| `orcamento_item_peca_componentes` | Componentes das pecas compostas aplicadas. |
| `orcamento_item_operacoes` | Operacoes aplicadas a um item. |
| `orcamento_item_acabamentos` | Acabamentos aplicados a um item. |

## Campos conceptuais de orcamento_item_custeio_linhas

Estrutura conceptual (nao final) de uma linha de custeio:

| Campo | Descricao |
| --- | --- |
| `id` | Identificador da linha. |
| `orcamento_item_id` | Item de orcamento a que a linha pertence. |
| `orcamento_item_modulo_id` | Modulo do item, se existir (nullable). |
| `origem_tipo` | Tipo de origem: `MATERIAL_PECA`, `ORLA_PECA`, `OPERACAO`, etc. |
| `origem_id` | Referencia ao registo de origem (peca, operacao, etc.). |
| `tipo_linha` | Classificacao da linha (material, orla, operacao, acabamento, ...). |
| `codigo` | Codigo tecnico associado. |
| `descricao` | Descricao apresentada. |
| `ref_materia_prima` | Referencia da materia-prima usada (snapshot). |
| `materia_prima_id` | Materia-prima de origem, se existir (nullable). |
| `unidade` | Unidade de calculo / compra. |
| `quantidade` | Quantidade da linha. |
| `comp` | Comprimento (Comp / Larg / Esp). |
| `larg` | Largura. |
| `esp` | Espessura. |
| `area_m2` | Area em metros quadrados. |
| `perimetro_ml` | Perimetro em metros lineares. |
| `ml_orla_fina` | Metros lineares de orla fina. |
| `ml_orla_grossa` | Metros lineares de orla grossa. |
| `custo_unitario` | Custo unitario. |
| `custo_total` | Custo total da linha. |
| `margem_percentagem` | Margem aplicada, em percentagem. |
| `preco_unitario` | Preco unitario final. |
| `preco_total` | Preco total final. |
| `override_manual` | Booleano que indica edicao manual. |
| `observacoes` | Notas livres. |

## Geracao por etapas

A geracao de linhas deve ser feita por etapas:

```text
Etapa 1: gerar material principal da peca
Etapa 2: gerar orlas da peca
Etapa 3: expandir componentes de peca composta
Etapa 4: gerar ferragens / acessorios
Etapa 5: gerar operacoes de producao
Etapa 6: gerar acabamentos
Etapa 7: aplicar overrides locais
Etapa 8: somar totais do item
```

## Testar por fases pequenas

O calculo deve ser construido e testado por fases pequenas, na seguinte ordem:

- primeiro material simples;
- depois orlas;
- depois ferragens;
- depois operacoes;
- depois acabamentos;
- depois pecas compostas;
- depois modulos.

## Exemplos

```text
Exemplo 1 - PRATELEIRA
  - material placa
  - orlas C1/C2
  - operacao corte
  - operacao orlagem

Exemplo 2 - PORTA
  - material placa
  - orlas
  - dobradicas
  - CNC furacao dobradicas
  - acabamento face_sup / face_inf
  - montagem

Exemplo 3 - GAVETA (composta)
  - laterais gaveta
  - frente gaveta
  - fundo gaveta
  - traseira gaveta
  - corredicas
  - puxador
  - montagem
```

## Fora do ambito deste documento

Este documento nao implementa:

- codigo Python;
- models SQLAlchemy;
- migrations Alembic;
- alteracoes de UI;
- tabelas de linhas de custeio;
- motor de calculo;
- geracao automatica de linhas.

## Decisoes pendentes

Antes de implementar a geracao de linhas, devem ficar respondidas as seguintes perguntas:

- como escolher a materia-prima por defeito?
- como aplicar a configuracao do orcamento / item?
- como representar os overrides?
- como tratar o desperdicio?
- como tratar os arredondamentos?
- como tratar o preco minimo?
- como tratar o custo / hora?
- como tratar o setup?
- como recalcular sem perder alteracoes manuais?
- como preservar o historico?
- como mostrar isto ao utilizador sem confusao?

## Proxima fase sugerida

**Fase 7J** - criar o modelo inicial de linhas de custeio do item, ainda sem geracao automatica completa.

Esta fase seguinte deve focar-se em definir a tabela `orcamento_item_custeio_linhas` e os seus campos base, preparando a estrutura para receber linhas geradas e linhas manuais, sem ainda implementar o motor de calculo descrito neste documento.
