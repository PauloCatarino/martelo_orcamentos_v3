# Fase 6 - Modelo futuro de ferragens, acessorios, SPP, operacoes e mao de obra

## Objetivo

Este documento descreve o modelo tecnico previsto para os componentes de pecas compostas que ainda nao tem catalogo proprio: ferragens, acessorios, SPP, operacoes e mao de obra.

O objetivo e registar decisoes e direcao tecnica antes de criar novas tabelas, models, migrations ou interface. Esta fase e apenas documentacao. Nao deve ser criado codigo, models, migrations nem alteracoes de UI neste momento.

## Estado atual dos componentes

Os componentes de uma peca composta (`def_peca_componentes`) podem ter um dos seguintes tipos:

- `PECA`
- `FERRAGEM`
- `ACESSORIO`
- `SPP`
- `OPERACAO`
- `MAO_OBRA`

Hoje existem dois comportamentos distintos:

| Tipo de componente | Origem atual | Como e guardado |
| --- | --- | --- |
| `PECA` | Catalogo `def_pecas` | `def_peca_componente_id` aponta para a definicao de peca existente. |
| `FERRAGEM` | Referencia textual | `referencia_componente` guarda texto livre; `def_peca_componente_id` fica vazio. |
| `ACESSORIO` | Referencia textual | `referencia_componente` guarda texto livre; `def_peca_componente_id` fica vazio. |
| `SPP` | Referencia textual | `referencia_componente` guarda texto livre; `def_peca_componente_id` fica vazio. |
| `OPERACAO` | Referencia textual | `referencia_componente` guarda texto livre; `def_peca_componente_id` fica vazio. |
| `MAO_OBRA` | Referencia textual | `referencia_componente` guarda texto livre; `def_peca_componente_id` fica vazio. |

Apenas o tipo `PECA` esta ligado a uma tabela real (`def_pecas`). Todos os outros tipos usam, por agora, uma referencia textual livre.

## Natureza temporaria da solucao atual

A referencia textual e aceitavel apenas como solucao temporaria. Ela permite que uma peca composta como `GAVETA` ou `PORTA` ja registe os seus componentes (por exemplo `DOBRADICA` ou `CORREDICA`) antes de existirem catalogos proprios.

No entanto, esta abordagem tem limitacoes:

- nao garante codigos consistentes;
- permite erros de escrita e nomes duplicados;
- nao guarda preco, fornecedor, unidade ou regras de cada item;
- nao permite reutilizar o mesmo item entre varias pecas com dados centralizados;
- dificulta o custeio real futuro.

Por isso, a referencia textual deve ser substituida no futuro por catalogos proprios.

## Catalogos proprios previstos no futuro

No futuro, cada area deve ter o seu catalogo (biblioteca/tabela) ou uma estrutura comum bem pensada de recursos. As areas previstas sao:

- ferragens;
- acessorios;
- SPP / barras / ml;
- operacoes / maquinas;
- mao de obra.

Cada catalogo deve permitir registar itens reutilizaveis, com codigo, dados tecnicos, preco e estado ativo/inativo, de forma a poderem ser referenciados pelos componentes das pecas compostas.

## Exemplos de ferragens

Exemplos de ferragens que um catalogo de ferragens deve conseguir representar:

- `DOBRADICA`
- `CORREDICA`
- `PUXADOR`
- `SUPORTE_PRATELEIRA`
- `SUPORTE_VARAO`
- `VARAO_ROUPEIRO`
- `PES_1`

Estes codigos sao exemplos tecnicos. O catalogo deve guardar codigo, nome amigavel e restantes atributos, sem depender de texto livre digitado em cada peca.

## Relacao com o Excel de materias-primas

O Excel antigo de materias-primas ja contem tipos que podem ajudar a desenhar os catalogos. Exemplos de tipos encontrados:

- `ACESSORIOS`
- `CORREDICAS`
- `DOBRADICAS`
- `FERRAGENS`
- `PUXADOR`
- `SUPORTE PRATELEIRA`
- `SUPORTE VARAO`
- `SPP`

Estes tipos servem como referencia, mas nao devem ser importados automaticamente para o Martelo V3 sem limpeza previa.

Nem todos os tipos do Excel devem virar categorias finais do Martelo V3. Antes de qualquer importacao deve existir revisao e limpeza, porque:

- alguns tipos podem ser redundantes (por exemplo `FERRAGENS` generico versus `DOBRADICAS` e `CORREDICAS` especificos);
- alguns nomes podem estar inconsistentes ou desatualizados;
- alguns tipos podem ser apenas agrupamentos comerciais e nao categorias tecnicas reais;
- a granularidade do Excel pode nao corresponder a granularidade desejada no V3.

A decisao sobre quais tipos se tornam categorias finais deve ser feita manualmente, com criterio tecnico, e nao por importacao direta.

## Campos previstos para ferragens e acessorios

Um catalogo de ferragens ou acessorios deve prever campos como:

- codigo;
- nome;
- descricao;
- familia / tipo;
- unidade;
- preco unitario;
- fornecedor;
- ativo;
- regras de quantidade;
- observacoes.

As regras de quantidade podem reutilizar o dominio ja existente `regra_quantidade_types` (por exemplo `FIXA`, `POR_COMPRIMENTO`, `POR_LARGURA`, `POR_COMPRIMENTO_LARGURA`, `POR_QUANTIDADE_PECA`, `POR_QUANTIDADE_MODULO`), mantendo a logica de peca horizontal (Comp / Larg / Esp) e sem usar a designacao Altura.

## Campos previstos para operacoes e maquinas

Um catalogo de operacoes ou maquinas deve prever campos como:

- codigo;
- nome;
- tipo de operacao;
- maquina;
- unidade de calculo;
- tempo base;
- custo / hora;
- ativo;
- regras futuras.

Estes campos preparam o futuro custeio de producao, permitindo associar tempos e custos a tipos de operacao e a maquinas concretas.

## Mao de obra

A mao de obra pode ser tratada de duas formas, e a decisao ainda esta pendente:

- como um tipo de operacao dentro do catalogo de operacoes;
- como uma categoria propria, com tabela dedicada de mao de obra.

Ambas as abordagens sao possiveis. A escolha depende de quanto a mao de obra partilha estrutura com as operacoes (tempo, custo/hora) ou se justifica regras e atributos proprios.

## Ligacao futura com def_peca_componentes

A direcao prevista e que cada tipo de componente passe a apontar para um catalogo proprio, mantendo `def_peca_componentes` como tabela de ligacao.

| Tipo de componente | Ligacao atual | Ligacao futura prevista |
| --- | --- | --- |
| `PECA` | `def_pecas` | `def_pecas` |
| `FERRAGEM` | `referencia_componente` (texto) | futura tabela `def_ferragens` |
| `ACESSORIO` | `referencia_componente` (texto) | futura tabela `def_acessorios` ou `def_ferragens` |
| `SPP` | `referencia_componente` (texto) | futura tabela `def_materiais` ou `def_spp` |
| `OPERACAO` | `referencia_componente` (texto) | futura tabela `def_operacoes` |
| `MAO_OBRA` | `referencia_componente` (texto) | futura tabela `def_mao_obra` ou `def_operacoes` |

Quando estes catalogos existirem, o componente deve passar a guardar uma referencia ao registo do catalogo, em vez de texto livre. A referencia textual pode manter-se apenas como fallback ou para migracao de dados antigos.

## Fora do ambito deste documento

Este documento nao implementa:

- codigo Python;
- models SQLAlchemy;
- migrations Alembic;
- alteracoes de UI;
- tabelas de ferragens, acessorios, SPP, operacoes ou mao de obra;
- importacao de dados do Excel;
- motor de custeio.

## Decisoes pendentes antes do codigo

Antes de criar catalogos, models e migrations para estas areas, devem ficar respondidas as seguintes perguntas:

- devem ser criadas tabelas separadas por area ou uma tabela comum de recursos?
- ferragens e acessorios ficam na mesma tabela ou em tabelas distintas?
- SPP pertence a materiais ou a acessorios?
- mao de obra fica dentro de operacoes ou em catalogo proprio?
- como importar dados do Excel antigo de materias-primas?
- como evitar tipos duplicados ou nomes antigos inconsistentes?
- como garantir codigos estaveis e unicos por catalogo?
- como migrar componentes que hoje usam `referencia_componente` textual para os novos catalogos?
