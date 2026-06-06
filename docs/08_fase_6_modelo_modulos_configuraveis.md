# Fase 6 - Modelo de modulos configuraveis

## Objetivo

Este documento define a filosofia tecnica e funcional prevista para modulos configuraveis no Martelo Orcamentos V3, antes de criar models, migrations, repositories, services ou interface avancada.

O objetivo e separar claramente:

- modelos reutilizaveis de modulos;
- modulos inseridos em items concretos de orcamento;
- pecas, ferragens, acessorios, operacoes e mao de obra usados no custeio;
- linhas finais de custeio geradas a partir dessas origens.

A filosofia pretendida e semelhante ao funcionamento do IMOS, mas adaptada ao Martelo V3 e ao seu objetivo principal: orcamentar, custear e preservar historico de forma controlada.

## Conceito geral

Um orcamento tem varios items. Cada item pode conter varios modulos, mas tambem pode conter elementos soltos ou custos diretos.

Um `OrcamentoItem` pode ser composto por:

- modulos;
- pecas soltas;
- pecas compostas;
- ferragens soltas;
- acessorios;
- SPP;
- operacoes;
- mao de obra;
- linhas manuais de custeio.

Nem todos os items precisam obrigatoriamente de modulos. Um item simples pode ser custeado apenas por pecas soltas, ferragens, operacoes ou mao de obra. Um item mais complexo pode combinar modulos pre-feitos com ajustes locais e elementos soltos.

## Modulo de biblioteca e modulo inserido no orcamento

O modelo deve distinguir duas realidades diferentes:

| Conceito | Funcao | Persistencia |
| --- | --- | --- |
| Modulo de biblioteca | Modelo reutilizavel, configurado previamente. | Vive numa biblioteca tecnica. |
| Modulo inserido no item | Instancia concreta usada num item de orcamento. | Vive dentro do orcamento e pode ser editada localmente. |

Esta separacao e essencial para preservar historico. Um orcamento antigo nao deve mudar automaticamente porque o modelo da biblioteca foi alterado depois.

## Modulo de biblioteca

Um modulo de biblioteca e um modelo reutilizavel. Pode representar, por exemplo:

- modulo roupeiro 2 portas;
- modulo 3 gavetas;
- modulo canto;
- modulo movel WC;
- modulo cozinha com aventos.

O modulo de biblioteca pode conter:

- pecas simples;
- pecas compostas;
- ferragens;
- acessorios;
- SPP;
- operacoes;
- mao de obra;
- regras de medidas;
- regras de quantidades;
- variaveis logicas.

O modulo de biblioteca nao deve guardar uma materia-prima concreta final. Em vez disso, deve usar grupos logicos e variaveis, por exemplo:

- `PORTAS`;
- `LATERAIS`;
- `COSTAS`;
- `DOBRADICAS`;
- `CORREDICAS`;
- `PUXADORES`;
- `TAMPOS`;
- `FUNDOS`;
- `PRATELEIRAS`.

Estes grupos permitem que a materia-prima final seja escolhida por configuracao do orcamento, do item, do modulo ou da peca, de forma semelhante aos ValueSets do IMOS.

## Modulo inserido no item

Quando um modulo de biblioteca e usado num orcamento, ele deve gerar uma instancia no item do orcamento.

Essa instancia:

- pertence a um `OrcamentoItem` especifico;
- e uma copia controlada do modulo de biblioteca;
- pode ser editada localmente;
- pode ter medidas alteradas;
- pode ter quantidades alteradas;
- pode receber pecas adicionais;
- pode remover pecas herdadas;
- pode receber ou remover ferragens;
- pode ter overrides locais de materiais, ferragens, precos ou regras.

Alterar a instancia de um modulo dentro de um orcamento nao deve alterar automaticamente o modelo original na biblioteca.

Da mesma forma, alterar no futuro o modulo de biblioteca nao deve alterar orcamentos antigos sem uma acao explicita do utilizador.

## Caminhos possiveis de custeio do item

Um item pode ser custeado por:

- modulos pre-feitos;
- pecas soltas;
- pecas compostas;
- ferragens soltas;
- acessorios soltos;
- SPP;
- operacoes;
- mao de obra;
- combinacao de todos estes.

Isto permite que o Martelo V3 suporte varios niveis de detalhe. Um roupeiro completo pode usar modulos, enquanto uma prateleira extra pode ser uma peca solta. Uma montagem especial pode ser apenas uma operacao ou mao de obra sem peca fisica associada.

## Relacao com def_pecas

A biblioteca de pecas continua a ser a base tecnica das pecas do sistema.

As pecas simples vem de `def_pecas`.

As pecas compostas vem de:

- `def_pecas`;
- `def_peca_componentes`.

Os modulos usam estas definicoes, mas nao substituem a biblioteca de pecas. Um modulo deve referenciar conceitos tecnicos ja definidos, como `LATERAL`, `PORTA`, `FUNDO`, `GAVETA` ou `PRATELEIRA`, e depois aplicar regras de quantidade, medidas e contexto.

As mesmas pecas podem ser usadas:

- dentro de um modulo;
- diretamente no item como pecas soltas;
- dentro de uma peca composta.

## Relacao com materias-primas

Modulos e pecas nao devem apontar diretamente para uma materia-prima final fixa.

A materia-prima final deve vir de configuracao do orcamento, item, modulo ou peca, de forma semelhante aos ValueSets do IMOS. Isto permite que um mesmo modulo de roupeiro use materiais diferentes consoante o orcamento, cliente, acabamento ou regra comercial.

Exemplo:

- o modulo define uma peca logica `PORTA`;
- a configuracao do item define que `PORTAS` usam uma materia-prima especifica;
- a linha final de custeio resolve essa configuracao para a materia-prima concreta;
- se necessario, a linha pode ter override manual.

Esta abordagem evita duplicar modulos apenas porque o material mudou.

## Analogia com IMOS

No IMOS existem artigos ou modulos guardados em biblioteca. Ao criar uma encomenda, o utilizador insere esses artigos ou modulos e depois aplica configuracoes de materiais, ferragens e variaveis.

Os modulos recebem materiais atraves de ValueSets. As variaveis podem ser alteradas em varios niveis:

- globalmente;
- por encomenda;
- por artigo/item;
- por modulo;
- por peca.

O Martelo V3 deve seguir uma filosofia semelhante, mas adaptada ao custeio. O foco nao e substituir o IMOS, mas permitir que o orcamento tenha uma estrutura tecnica suficiente para calcular custo, preco, quantidades, materiais, ferragens, operacoes e mao de obra.

## Exemplos funcionais

### Exemplo 1 - Roupeiro

Item: Roupeiro

| Origem | Elemento |
| --- | --- |
| Modulo 1 | Modulo 2 portas |
| Modulo 2 | Modulo gavetas |
| Peca solta | Prateleira extra |
| Ferragem solta | Varao roupeiro |
| Operacao | Montagem especial |

Neste exemplo, o item mistura modulos reutilizaveis com ajustes locais. A prateleira extra e uma peca solta porque nao pertence obrigatoriamente ao modulo original. O varao pode entrar como ferragem solta. A montagem especial pode ser uma operacao direta.

### Exemplo 2 - Movel WC

Item: Movel WC

| Origem | Elemento |
| --- | --- |
| Modulo | Modulo base com gaveta |
| Peca composta | Gaveta |
| Ferragens | Corredicas e puxador |
| Operacoes | Corte, orlagem, CNC e montagem |

Neste exemplo, a gaveta pode vir de uma peca composta, gerando componentes associados. As operacoes podem ser calculadas pelas pecas ou adicionadas ao modulo/item conforme as regras futuras.

## Biblioteca, instancia e historico

Os modulos configurados devem ser gravados numa biblioteca de modelos. Quando entram no orcamento, devem gerar uma instancia independente.

Regras principais:

- alteracoes na instancia do orcamento nao alteram automaticamente o modelo de biblioteca;
- alteracoes futuras no modelo de biblioteca nao alteram automaticamente orcamentos antigos;
- atualizacoes de uma instancia a partir da biblioteca devem ser uma acao explicita;
- orcamentos fechados ou historicos devem manter os dados com que foram calculados.

Esta regra e importante para evitar que um preco antigo mude porque uma regra, peca ou ferragem da biblioteca foi ajustada depois.

## Entidades futuras propostas

As entidades abaixo sao apenas conceptuais nesta fase.

| Entidade conceptual | Funcao prevista |
| --- | --- |
| `def_modulos` | Guarda modelos reutilizaveis de modulos. |
| `def_modulo_pecas` | Define pecas que pertencem a um modelo de modulo. |
| `def_modulo_componentes` | Define ferragens, acessorios, SPP, operacoes ou mao de obra associados ao modelo de modulo. |
| `orcamento_item_modulos` | Guarda a instancia do modulo dentro de um item de orcamento. |
| `orcamento_item_modulo_pecas` | Guarda pecas pertencentes a uma instancia de modulo. |
| `orcamento_item_pecas_soltas` | Guarda pecas aplicadas diretamente ao item, sem modulo. |
| `orcamento_item_operacoes` | Guarda operacoes ou mao de obra associadas ao item. |
| `custeio_linhas` | Guarda linhas finais de custeio resolvidas a partir de modulos, pecas, ferragens, operacoes ou insercao manual. |

## Definicao, instancia e linha final de custeio

O modelo deve separar tres niveis:

| Nivel | Descricao | Exemplo |
| --- | --- | --- |
| Definicao/base/modelo | Elemento reutilizavel da biblioteca. | Modulo 2 portas, peca `PORTA`, peca composta `GAVETA`. |
| Instancia no orcamento | Copia usada num item concreto. | Modulo 2 portas inserido no roupeiro 260001_01. |
| Linha final de custeio | Resultado calculado para custo/preco. | Placa, orla, dobradica, corte, montagem ou linha manual. |

A linha final de custeio deve conseguir identificar a sua origem:

- modulo;
- peca solta;
- peca composta;
- ferragem solta;
- operacao;
- manual.

Esta origem e necessaria para auditoria, diagnostico, recalculo e leitura pelo utilizador.

## Overrides locais

O modelo deve permitir overrides locais quando uma instancia de modulo ou uma peca aplicada ao orcamento precise de se afastar da biblioteca.

Exemplos de overrides:

- alterar material das portas;
- trocar ferragem;
- alterar quantidade;
- alterar medida;
- adicionar peca extra;
- remover componente herdado;
- alterar preco manualmente;
- desativar uma regra numa instancia especifica.

Overrides devem ficar registados na instancia do orcamento, nao na definicao de biblioteca.

## Contexto visual e breadcrumbs

No futuro, a interface deve ajudar o utilizador a perceber onde esta dentro da estrutura:

- Orcamento;
- Item;
- Modulo;
- Peca;
- Linha de custeio.

Breadcrumbs e contexto visual sao importantes porque a navegacao pode ter varios niveis. A interface deve deixar claro se o utilizador esta a editar uma definicao de biblioteca ou uma instancia de orcamento.

Exemplos de contexto:

```text
Orcamento 260001_01 > Item: Roupeiro > Modulo: 2 portas
Orcamento 260001_01 > Item: Roupeiro > Modulo: Gavetas > Peca: Frente Gaveta
Orcamento 260001_01 > Item: Roupeiro > Linha de custeio: Dobradica
```

## Fora do ambito deste documento

Este documento nao implementa:

- codigo Python;
- models SQLAlchemy;
- migrations Alembic;
- repositories;
- services;
- interface;
- motor de regras;
- motor de custeio;
- copia real de modulos para items;
- ValueSets reais;
- ligacao real a materias-primas.

## Decisoes pendentes

Antes de criar codigo para modulos configuraveis, devem ficar respondidas as seguintes perguntas:

- como gravar modelos de modulos?
- que campos minimos devem existir em `def_modulos`?
- como representar pecas, ferragens, acessorios, SPP, operacoes e mao de obra dentro de um modelo?
- como copiar modulo de biblioteca para item?
- que dados devem ser congelados na instancia do orcamento?
- como aplicar ValueSets ou configuracao de materiais?
- como recalcular quando medidas mudam?
- como preservar orcamentos historicos?
- como permitir overrides locais?
- como tratar modulos criados apenas para um orcamento especifico?
- como converter um modulo local em modelo de biblioteca?
- como distinguir alteracoes locais de alteracoes herdadas da biblioteca?
- como auditar a origem de cada linha final de custeio?

## Proxima fase sugerida

Fase 7A - desenhar modelo inicial de biblioteca de modulos, ainda sem UI avancada.
