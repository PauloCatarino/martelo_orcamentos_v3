# Fase 6 - Modelo de pecas, modulos e custeio

## Objetivo

A Fase 6 tem como objetivo documentar o modelo conceptual correto para definicao de pecas, pecas aplicadas ao orcamento, modulos e custeio antes de criar codigo Python, models SQLAlchemy, migrations Alembic ou alteracoes na interface.

O conceito principal desta fase e a `Definicao de Peca`, tambem entendida como biblioteca ou catalogo de pecas. Esta definicao nao pertence a um modulo nem a um orcamento especifico. Ela representa uma peca reutilizavel que pode ser usada em varios contextos.

Esta fase e apenas planeamento tecnico. A implementacao real sera feita numa fase posterior com models, migrations, repositories, services e UI proprios.

## Catalogo de definicao de pecas

O Martelo V3 deve prever um menu ou catalogo de definicao de pecas. Este catalogo representa a biblioteca tecnica reutilizavel, inspirada no conceito vindo do Martelo V2 e dos documentos de planeamento.

Exemplos de definicoes possiveis:

- Lateral;
- Tampo;
- Fundo;
- Costa;
- Porta;
- Peca composta;
- Ferragem associada;
- Operacao associada.

A definicao da peca guarda a identidade tecnica e as regras base da peca. Por exemplo, uma definicao `Lateral` pode futuramente ter regras de medidas, materiais possiveis, operacoes associadas e relacao com ferragens. Essa definicao continua a ser reutilizavel e nao fica presa a um item, modulo ou orcamento concreto.

## Peca aplicada ao orcamento

Quando uma definicao de peca e usada num orcamento, passa a existir como peca aplicada ao orcamento.

A peca aplicada e uma ocorrencia concreta. Ela pode herdar dados da definicao de peca, mas tambem pode guardar valores proprios daquele orcamento, como medidas, quantidade, material, observacoes, custo calculado ou ajustes manuais.

Uma peca aplicada ao orcamento pode estar:

- associada a um modulo;
- associada diretamente ao item como peca solta.

As mesmas definicoes de pecas usadas dentro de modulos tambem podem ser usadas fora dos modulos. Por exemplo, `Lateral`, `Tampo`, `Fundo`, `Costa` ou `Porta` podem aparecer num modulo parametrizado ou serem lancadas diretamente como pecas soltas num item.

## Caminhos possiveis ate ao custo do item

Um item de orcamento pode chegar ao seu custo por diferentes caminhos:

- modulos;
- pecas soltas;
- producao ou mao de obra direta;
- combinacao de modulos, pecas soltas, producao e mao de obra.

Isto significa que o custo de um `OrcamentoItem` nao deve depender obrigatoriamente de uma unica estrutura. Um item pode ser composto por modulos parametrizados, por pecas individuais lancadas diretamente, por tempos de producao sem peca fisica associada, ou por uma combinacao destas opcoes.

## Papel dos modulos

Os modulos devem ser tratados como conjuntos organizados de elementos tecnicos e regras. Um modulo pode agrupar:

- pecas;
- ferragens;
- materiais;
- mao de obra;
- producao;
- regras de medidas e quantidades.

Exemplo: um modulo de roupeiro pode definir laterais, tampo, fundo, costa, prateleiras, portas, ferragens e regras para calcular medidas com base na altura, largura e profundidade do item ou do proprio modulo.

O modulo nao deve ser apenas uma lista fixa de pecas. Deve ser uma estrutura preparada para receber regras, quantidades, formulas e futuras ligacoes ao custeio real.

## Peca dentro de modulo, peca solta e producao direta

Uma peca dentro de um modulo e uma peca aplicada cuja existencia, medidas ou quantidades podem depender das regras do modulo. Nestes casos, o modulo pode controlar dimensoes, formulas, repeticoes, referencias a medidas principais e logica futura de producao.

Uma peca solta e uma peca aplicada diretamente ao item de orcamento. As suas medidas e quantidades sao definidas localmente, sem depender de um modulo. Esta opcao e importante para casos especiais, ajustes manuais, pecas avulsas ou componentes que nao justificam a criacao de um modulo.

A producao direta representa custo sem peca fisica obrigatoria. Pode ser usada para mao de obra, operacoes gerais, instalacao, preparacao, acabamento ou outro custo operacional que deva entrar no item, modulo ou orcamento sem gerar uma peca material.

Esta diferenca deve existir no modelo de dados sem duplicar a nocao de peca. A mesma entidade de peca aplicada ao orcamento pode suportar peca de modulo e peca solta atraves de uma associacao opcional ao modulo.

## Modelo conceptual proposto

O modelo conceptual deve considerar a separacao entre definicoes reutilizaveis e aplicacoes concretas no orcamento.

| Entidade conceptual | Funcao | Observacoes |
| --- | --- | --- |
| `def_peca` | Define a peca reutilizavel da biblioteca, como Lateral, Tampo, Fundo, Costa, Porta ou Peca composta. | Nao pertence a modulo nem a orcamento especifico. |
| `def_peca_operacao` | Associa operacoes, maquinas ou tempos padrao a uma definicao de peca. | Pode suportar producao futura por tipo de peca. |
| `def_peca_material_regra` | Define regras de materiais, ferragens ou consumos associados a uma definicao de peca. | Pode incluir regras condicionais ou formulas numa fase posterior. |
| `orcamento_item_peca` | Representa uma peca aplicada a um item de orcamento. | Deve guardar medidas, quantidades e dados usados para custo naquele orcamento. |
| `orcamento_item_modulo` | Representa um modulo associado a um item de orcamento. | Ja existe como base conceptual para organizar pecas, regras e producao. |
| `orcamento_item_peca.orcamento_item_modulo_id` | Associacao opcional da peca aplicada a um modulo. | Quando for `null`, a peca e solta diretamente no item. |

## Regra de associacao das pecas aplicadas

A regra conceptual proposta para futuras pecas usadas no orcamento e:

- `orcamento_item_id` obrigatorio;
- `orcamento_item_modulo_id` opcional.

Se `orcamento_item_modulo_id` existir, a peca pertence a um modulo.

Se `orcamento_item_modulo_id` for `null`, a peca e solta diretamente no item.

Esta regra permite que o separador `Items` suporte simultaneamente pecas manuais e pecas geradas ou organizadas por modulos, mantendo uma origem clara para cada linha tecnica.

## Impacto no custeio futuro

O custeio deve conseguir somar componentes vindos de varias origens:

- pecas associadas a modulos;
- pecas soltas associadas diretamente ao item;
- ferragens e materiais associados a pecas ou modulos;
- producao e mao de obra associadas a item, modulo ou peca;
- producao direta sem peca fisica;
- ajustes manuais de preco ou custo, se forem definidos numa fase posterior.

Nesta fase ainda nao sera implementado o motor de custeio. A documentacao serve apenas para preparar um modelo que nao bloqueie os cenarios reais do Martelo V3.

## Fora do ambito desta fase

Nesta fase nao sera criado:

- codigo Python;
- models SQLAlchemy;
- migrations Alembic;
- alteracoes de UI;
- tabelas de pecas;
- biblioteca real de pecas base;
- ligacoes reais a materiais, ferragens, operacoes, maquinas ou producao;
- motor de custeio.

## Decisoes pendentes antes do codigo

Antes de criar models, migrations e interface para pecas, devem ficar respondidas as seguintes perguntas:

- quais campos minimos de `def_peca`?
- como representar pecas compostas?
- como associar operacoes/maquinas a peca?
- como associar regras de materiais/ferragens a peca?
- como representar formulas de medidas?
- como distinguir valores herdados de modulo e valores editados manualmente?
- como tratar producao sem pecas?
