# Fase 7 - Modelo de ValueSets por orcamento e item

## Objetivo

Este documento define o modelo conceptual de ValueSets para o Martelo Orcamentos V3.

Um ValueSet e um conjunto de materiais, ferragens, orlas, sistemas e acabamentos definidos por defeito para um orcamento ou para um item. A ideia e semelhante aos ValueSets do IMOS: o utilizador escolhe um conjunto de referencias principais e o sistema usa essas escolhas para resolver automaticamente materiais e componentes quando pecas, modulos e operacoes entram no custeio.

Na pratica, os ValueSets definem os materiais, ferragens, acabamentos e orlas que o orcamento ou item vai usar. A peca, modulo ou componente pede uma chave logica; o ValueSet devolve a materia-prima, ferragem, acabamento ou referencia aplicavel.

Esta fase e apenas documentacao e analise. Nao cria codigo Python, models SQLAlchemy, migrations Alembic, UI ou regras reais de calculo.

## Porque os ValueSets sao necessarios

O utilizador nao deve escolher materia-prima linha a linha para tudo.

Quando uma peca e inserida no custeio, ela deve conseguir saber que material usar por defeito. Quando uma ferragem associada e gerada, ela deve saber que referencia usar por defeito. Quando uma peca tem orlas, o sistema deve saber qual materia-prima representa a orla fina e a orla grossa. Quando uma linha precisa de acabamento, o sistema deve saber que acabamento aplicar.

ValueSets sao necessarios para:

- evitar trabalho repetitivo;
- acelerar o custeio por item;
- manter consistencia entre linhas do mesmo orcamento;
- permitir alteracoes locais apenas onde forem necessarias;
- aproximar a logica do Martelo V3 da filosofia do IMOS;
- separar a definicao tecnica da peca do material real usado no orcamento.

## Niveis de heranca

Os ValueSets devem suportar varios niveis de heranca:

1. configuracao global ou biblioteca;
2. orcamento;
3. item;
4. modulo inserido;
5. peca ou linha de custeio.

A regra conceptual e: o nivel mais especifico ganha.

Exemplo de prioridade:

```text
Linha de custeio
  > Peca / modulo inserido
    > Item
      > Orcamento
        > Configuracao global
```

Se uma linha foi editada localmente, essa edicao nao deve ser substituida silenciosamente por alteracoes no item ou no orcamento.

## ValueSet geral do orcamento

O orcamento pode ter um ValueSet geral. Este conjunto define os materiais, ferragens e acabamentos usados por defeito nos items desse orcamento.

Exemplos de chaves:

- `material_caixote`;
- `material_portas`;
- `material_frentes_gaveta`;
- `material_costas`;
- `material_fundos`;
- `material_prateleiras`;
- `orla_fina`;
- `orla_grossa`;
- `dobradica`;
- `corredica`;
- `puxador`;
- `varao`;
- `suporte_varao`;
- `pe_nivelador`;
- `acabamento_face_sup`;
- `acabamento_face_inf`.

Estas chaves nao representam obrigatoriamente campos fixos finais. Podem evoluir para uma tabela de linhas de ValueSet, onde cada chave aponta para uma materia-prima, ferragem, acabamento ou valor textual.

Exemplos principais de resolucao:

| Elemento tecnico | Resolve atraves de |
| --- | --- |
| Portas | material definido para portas. |
| Laterais | material definido para caixote. |
| Tetos | material definido para caixote. |
| Fundos | material definido para fundos. |
| Costas | material definido para costas. |
| Prateleiras | material definido para prateleiras. |
| Dobradicas | ferragem definida para dobradicas. |
| Corredicas | ferragem definida para corredicas. |
| Puxadores | ferragem definida para puxadores. |
| Orla fina | orla definida por material/cor/espessura. |
| Orla grossa | orla definida por material/cor/espessura. |
| Acabamento sup/inf | acabamento definido para portas, frentes e paineis. |

## ValueSet do item

O item pode herdar o ValueSet do orcamento.

Tambem pode editar localmente alguns valores sem alterar o orcamento todo.

Exemplo:

- o orcamento define `material_portas = MDF HIDRO 19MM`;
- um item especifico altera `material_portas = MDF LACADO 22MM`;
- as pecas `PORTA` desse item passam a usar o material local do item;
- os restantes items continuam a usar o valor do orcamento.

Esta heranca permite que um orcamento tenha uma configuracao geral, mas suporte excecoes por item.

## ValueSet da linha de custeio

Uma linha de custeio pode herdar do item, mas tambem pode ser editada localmente.

Se o utilizador alterar localmente descricao, referencia, preco, unidade, material, acabamento ou observacao, a linha deve indicar:

```text
⚠ Editado localmente
```

Esta marcacao serve para proteger ajustes manuais. Uma linha editada localmente nao deve ser sobrescrita automaticamente quando o ValueSet do orcamento ou do item muda, salvo se o utilizador pedir explicitamente um recalculo ou uma nova aplicacao de ValueSet.

## Preservacao historica e snapshots

Alteracoes no ValueSet do orcamento nao devem alterar linhas antigas ja congeladas ou guardadas, salvo recalculo explicito.

As linhas de custeio devem guardar snapshot dos valores usados no momento em que foram criadas ou calculadas.

Campos de snapshot importantes:

- `ref_materia_prima`;
- `descricao`;
- `preco`;
- `unidade`;
- origem: `orcamento`, `item` ou `manual`.

O snapshot permite perceber que referencia foi usada no custo, mesmo que a materia-prima, preco, fornecedor ou configuracao do orcamento mude depois.

## Categorias logicas

As configuracoes devem usar categorias logicas. Estas categorias ajudam as pecas e componentes a pedir "o material certo" sem conhecer diretamente a materia-prima final.

Categorias previstas:

- `CAIXOTE`;
- `PORTAS`;
- `FRENTES`;
- `COSTAS`;
- `FUNDOS`;
- `PRATELEIRAS`;
- `GAVETAS`;
- `ORLA_FINA`;
- `ORLA_GROSSA`;
- `DOBRADICAS`;
- `CORREDICAS`;
- `PUXADORES`;
- `VAROES`;
- `SISTEMAS_CORRER`;
- `ACABAMENTOS`;
- `OUTROS`.

A lista final deve ser validada com a pratica real do Martelo V2, o Excel de materias-primas e as necessidades do V3.

## Relacao com def_pecas

Deve existir ligacao direta entre a biblioteca de pecas e os ValueSets.

Cada definicao de peca deve poder indicar qual chave ou categoria de ValueSet deve usar. Esta chave nao e a materia-prima final; e apenas a pergunta que a peca faz ao ValueSet quando entra no custeio.

Exemplos:

| Definicao de peca | Chave / categoria de ValueSet |
| --- | --- |
| `COSTA` | `material_costas` |
| `LATERAL` | `material_caixote` |
| `TAMPO` | `material_caixote` |
| `FUNDO` | `material_fundos` |
| `PORTA` | `material_portas` |
| `PRATELEIRA` | `material_prateleiras` |
| `FRENTE_GAVETA` | `material_frentes` |
| `LADO_GAVETA` | `material_gavetas` ou `material_caixote` |

A peca nao deve apontar diretamente para uma materia-prima final. Ela deve indicar a sua chave logica. O ValueSet do orcamento ou do item resolve a materia-prima concreta.

Exemplo com `COSTA`:

1. o utilizador insere uma `COSTA` no custeio;
2. o programa identifica que `COSTA` usa a chave `material_costas`;
3. o programa procura `material_costas` no ValueSet do item;
4. se nao existir no item, procura `material_costas` no ValueSet do orcamento;
5. aplica essa materia-prima na linha de custeio;
6. guarda snapshot da referencia, descricao, unidade e preco.

## Relacao com ferragens

Uma ferragem associada tambem precisa de chave logica.

Exemplos:

| Ferragem logica | Chave no ValueSet |
| --- | --- |
| `DOBRADICA` | `ferragem_dobradica` |
| `CORREDICA` | `ferragem_corredica` |
| `PUXADOR` | `ferragem_puxador` |
| `VARAO` | `ferragem_varao` |
| `SUPORTE_VARAO` | `ferragem_suporte_varao` |

Esta logica evita fixar referencias concretas dentro das pecas compostas ou modulos de biblioteca.

## Relacao com def_materias_primas

O ValueSet deve apontar para `def_materias_primas`, a tabela de materias-primas importadas do Excel.

No entanto, nem todos os materiais ou ferragens estarao sempre na base. Em alguns casos pode ser necessario usar uma referencia temporaria ou ajustar localmente a descricao, preco ou referencia.

Por isso, a linha de custeio deve permitir edicao local de:

- descricao;
- preco;
- referencia;
- unidade;
- observacoes.

Quando isto acontecer, a linha deve ficar marcada como editada localmente.

## Relacao com modulos

Um modulo de biblioteca nao deve ter materia-prima final rigida.

O modulo de biblioteca deve usar categorias logicas ou grupos, como `PORTAS`, `LATERAIS`, `DOBRADICAS`, `CORREDICAS` ou `PUXADORES`.

Quando o modulo e inserido num item, passa a ser uma instancia local. Essa instancia deve receber os materiais do ValueSet do item ou, se o item nao tiver override, do ValueSet do orcamento.

O utilizador pode alterar localmente dentro do modulo inserido. Essas alteracoes devem afetar apenas aquele item/orcamento, nao o modulo de biblioteca.

## Relacao com pecas compostas

Uma peca composta expande componentes. Cada componente deve resolver material ou ferragem pelo ValueSet.

Exemplo:

```text
GAVETA:
  LADO_GAVETA    -> material gavetas/caixote
  TRASEIRA_GAVETA -> material gavetas/caixote
  FUNDO_GAVETA   -> material fundos
  FRENTE_GAVETA  -> material frentes
  CORREDICA      -> corredica do ValueSet
  PUXADOR        -> puxador do ValueSet
```

Isto permite que a peca composta `GAVETA` seja reutilizavel em varios orcamentos, sem fixar materiais ou ferragens concretas na sua definicao.

## Relacao com acabamentos

O acabamento pode ser definido por orcamento ou por item.

Pode existir acabamento diferente para:

- `face_sup`;
- `face_inf`.

O acabamento tambem deve poder ser editado localmente por peca ou linha de custeio.

Exemplo:

- o orcamento define `acabamento_face_sup = Lacado branco`;
- o item herda esse acabamento;
- uma peca especifica pode alterar localmente para outro acabamento, se necessario.

## Relacao com orlas

A peca define os lados que levam orla, por exemplo `[2200]`.

As orlas nao sao sempre preenchidas de forma linear no ValueSet. Em muitos casos, ao escolher um material de placa, essa materia-prima pode ja ter colunas com referencias de orla fina 0.4 e orla grossa 1.0.

Essas referencias apontam para artigos de orla existentes na lista de materias-primas. Assim, o ValueSet pode escolher o material principal, e o material principal pode indicar quais artigos de orla devem ser usados.

O ValueSet pode definir diretamente ou indiretamente qual materia-prima usar para:

- `orla_fina`;
- `orla_grossa`.

O calculo futuro deve:

- ler as orlas da peca;
- calcular ML de orla fina e grossa;
- resolver a materia-prima da orla pelo ValueSet;
- aplicar preco do ValueSet ou da materia-prima resolvida;
- gerar custo de material de orla e, quando aplicavel, custo de operacao de orlagem.

Exemplo:

```text
Material selecionado para portas:
  MDF Branco 19mm
  ref_orla_fina_04 = ORL0002
  ref_orla_grossa_10 = ORL0005

Peca PORTA com orlas [2200]:
  C1 e C2 usam orla grossa ou fina conforme codigo;
  programa procura a referencia de orla no material;
  programa gera custo de orla por ML.
```

Quando a peca tiver codigo de orlas `[2200]`, o programa deve calcular os metros lineares e escolher orla fina/grossa com base na referencia associada ao material.

Se o material nao tiver referencia de orla configurada, o sistema deve usar uma regra de fallback ainda a definir: avisar, pedir escolha manual, usar orla geral do ValueSet ou bloquear calculo ate o utilizador configurar.

## Linhas e modelos de ValueSet

A tabela de ValueSets deve permitir:

- inserir novas linhas;
- editar linhas;
- suprimir ou desativar linhas para nao aparecerem ao utilizador;
- nao eliminar fisicamente linhas que ja foram usadas em orcamentos.

Tambem deve existir biblioteca ou modelos de ValueSets.

Objetivos da biblioteca de ValueSets:

- poupar tempo ao utilizador;
- guardar conjuntos tipicos de materiais, ferragens e acabamentos;
- permitir importar um modelo de ValueSet para um novo orcamento ou item;
- reduzir preenchimento manual repetitivo.

Exemplos de modelos de ValueSet:

- Roupeiro branco standard;
- Roupeiro melamina Cancun;
- Cozinha lacada branca;
- Movel WC hidrofugo;
- Obra especial cliente X.

Fluxo esperado:

1. o utilizador cria um orcamento;
2. importa um ValueSet guardado;
3. ajusta apenas o que for diferente;
4. copia ValueSet do orcamento para o item quando necessario;
5. edita localmente o ValueSet do item.

Quanto menos o utilizador tiver de preencher manualmente, melhor.

## UI futura

No UI futuro deve existir:

- ValueSet do Orcamento;
- ValueSet do Item;
- botao para copiar ou herdar do orcamento;
- indicacao visual de campos herdados;
- indicacao visual de campos localmente editados.

Exemplos de estados visuais:

| Estado | Significado |
| --- | --- |
| Herdado do orcamento | O item usa o valor definido no orcamento. |
| Editado no item | O item tem override local. |
| Editado na linha | A linha de custeio ja nao segue totalmente o ValueSet. |

O UI deve deixar claro se o utilizador esta a alterar uma configuracao geral do orcamento, uma configuracao local do item ou uma linha individual.

## Exemplo pratico

ValueSet do Orcamento:

```text
material_caixote = AGL MLC CANCUN 19MM
material_portas = MDF HIDRO 19MM
orla_fina = ORL 0.4 Cancun
orla_grossa = ORL 1.0 Cancun
dobradica = BLUM reta
puxador = Puxador Tic Tac
acabamento_face_sup = Lacado branco
acabamento_face_inf = Lacado branco
```

Item Roupeiro:

```text
herda tudo do orcamento
mas altera material_portas para MDF lacado 22MM
```

Linha `PORTA`:

```text
usa material_portas do item
usa orlas do item
usa dobradicas do item
guarda snapshot no custeio
```

Neste exemplo, alterar `material_portas` no item afeta as portas desse item. Os outros items continuam a herdar `material_portas` do orcamento.

## Entidades futuras propostas

As entidades abaixo sao apenas conceptuais nesta fase:

- `biblioteca_valuesets`;
- `biblioteca_valueset_linhas`;
- `orcamento_valuesets`;
- `orcamento_item_valuesets`;
- `valueset_campos`;
- `valueset_linhas`;
- `tipos_valueset`.

## Campos conceptuais

Campos conceptuais previstos:

- `id`;
- `orcamento_versao_id`;
- `orcamento_item_id` nullable;
- `chave`;
- `descricao`;
- `materia_prima_id`;
- `ref_materia_prima`;
- `valor_texto`;
- `origem`;
- `editado_localmente`;
- `ativo`.

`orcamento_item_id` nullable permite que a mesma estrutura suporte ValueSet do orcamento e ValueSet de item, se for escolhida uma tabela unica.

## Regras de origem

A origem de um valor deve ficar explicita.

Exemplos:

| Origem | Significado |
| --- | --- |
| `GLOBAL` | Valor veio da configuracao global ou biblioteca. |
| `ORCAMENTO` | Valor definido no ValueSet do orcamento. |
| `ITEM` | Valor definido no ValueSet do item. |
| `MODULO` | Valor editado no modulo inserido. |
| `LINHA` | Valor editado diretamente na linha de custeio. |
| `MANUAL` | Valor escrito manualmente sem referencia principal. |

Esta origem ajuda a preservar auditoria e historico.

## Recalculo e protecao de linhas

Se o ValueSet do orcamento ou do item mudar, o sistema deve ser cuidadoso ao recalcular.

Regras conceptuais:

- linhas congeladas ou guardadas nao mudam automaticamente;
- linhas editadas localmente nao devem ser sobrescritas sem confirmacao;
- recalculo deve ser acao explicita;
- o sistema deve informar que linhas serao afetadas;
- snapshots anteriores devem permitir auditar o que mudou.

## Fora do ambito deste documento

Este documento nao implementa:

- codigo Python;
- models SQLAlchemy;
- migrations Alembic;
- UI;
- aplicacao real de ValueSets no calculo;
- importacao ou mapeamento automatico de materias-primas;
- recalculo de linhas existentes.

## Decisoes pendentes

Antes de criar codigo para ValueSets, devem ficar respondidas as seguintes perguntas:

- usar tabela unica para orcamento e item ou tabelas separadas?
- como mapear tipo/familia Excel para categorias Martelo?
- confirmar nomes reais das colunas de orlas no Excel de materias-primas;
- mapear colunas de orlas do Excel para `def_materias_primas`;
- como definir valores default?
- como editar rapidamente no UI?
- como recalcular linhas existentes?
- como preservar historico?
- como lidar com materia-prima inexistente?
- como tratar varios fornecedores/precos?
- a orla do ValueSet pode ser manualmente substituida?
- cada material pode ter orla fina/grossa propria?
- qual fallback usar se o material nao tiver referencia de orla configurada?
- que categorias logicas finais devem existir?
- como distinguir override do item e override da linha?
- quando uma linha deve ficar congelada?

## Proxima fase sugerida

Fase 7O - criar modelo inicial de ValueSet do orcamento e item, ainda sem aplicar no calculo.

Essa fase deve considerar:

- ValueSet de orcamento;
- ValueSet de item;
- biblioteca/modelo de ValueSet;
- chave logica de material, ferragem, acabamento e orla;
- ligacao futura as definicoes de pecas.
