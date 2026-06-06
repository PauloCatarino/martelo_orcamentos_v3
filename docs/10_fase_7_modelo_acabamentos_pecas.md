# Fase 7 - Modelo de acabamentos das pecas

## Objetivo

Este documento descreve como o Martelo Orcamentos V3 deve tratar os acabamentos de superficie das pecas, como lacagem, pintura, verniz e outros tratamentos. Serve de base tecnica e funcional antes de criar campos, tabelas, UI ou calculo.

Usa como contexto os modelos ja documentados em `docs/05_fase_6_modelo_valuesets_materiais.md` (configuracao de materiais por orcamento), `docs/06`/`docs/07` (materias-primas) e `docs/09_fase_6_modelo_operacoes_producao.md` (operacoes).

Esta fase e apenas documentacao. Nao deve ser criado codigo, models, migrations, UI nem calculo neste momento.

## Acabamentos no custeio de pecas

Os acabamentos fazem parte do custeio das pecas. O custo de uma peca pintada, lacada ou envernizada nao depende apenas do material base e das operacoes mecanicas; o tratamento de superficie acrescenta custo de material de acabamento e, frequentemente, mao de obra e operacoes de producao.

Por isso, o modelo de custeio deve prever o acabamento como uma componente propria do custo da peca.

## Acabamentos aplicam-se a pecas, nao a ferragens

Os acabamentos aplicam-se a **pecas**, nao a ferragens, acessorios ou SPP. Uma dobradica ou uma corredica nao levam lacagem; uma porta ou um tampo, sim.

Pecas que tipicamente recebem acabamento:

- portas;
- frentes;
- paineis;
- tampos;
- laterais visiveis;
- pecas especiais.

Nem todas as pecas levam acabamento (por exemplo, costas interiores ou fundos podem nao levar). O modelo deve permitir peca com e sem acabamento.

## Tipos de acabamento

Um acabamento pode ser, entre outros:

- lacagem;
- pintura;
- envernizamento;
- primario;
- velatura;
- acabamento manual;
- outros tratamentos de superficie.

A lista final deve ser confirmada e pode crescer com o tempo.

## Onde o acabamento se aplica: faces

O acabamento aplica-se por face. Uma peca pode ter:

- acabamento nas duas faces;
- acabamento apenas na face superior;
- acabamento apenas na face inferior;
- acabamento diferente em cada face;
- sem acabamento.

A nomenclatura conceptual proposta para as faces e:

- `face_sup` (face superior);
- `face_inf` (face inferior).

Cada face pode ter o seu proprio acabamento (ou nenhum), de forma independente.

## Exemplos

```text
Exemplo 1 - PORTA
  face_sup = Lacado branco mate
  face_inf = Lacado branco mate

Exemplo 2 - PAINEL DECORATIVO
  face_sup = Verniz natural
  face_inf = Sem acabamento

Exemplo 3 - TAMPO ESPECIAL
  face_sup = Lacado cor cliente
  face_inf = Primario
```

## Origem do preco e dos dados de acabamento

Os precos dos acabamentos podem vir da tabela de materias-primas / importacao do Excel. Na tabela de materias-primas ja existem precos para varios tipos de pintura e acabamento (ver `docs/06` e `docs/07`).

Isto significa que o acabamento concreto deve poder apontar para um registo de `def_materias_primas` (categoria de acabamento), reutilizando preco, unidade e fornecedor, em vez de duplicar esses dados.

## O acabamento nao fica preso a definicao da peca

O acabamento concreto **nao deve ficar preso a definicao fixa da peca**, tal como o material base tambem nao fica (ver `docs/05`).

A definicao da peca pode, no maximo, indicar comportamento:

- a peca "permite acabamento";
- a peca "normalmente leva acabamento".

Mas o acabamento concreto (qual cor, qual tipo) deve poder vir de:

- configuracao do orcamento;
- configuracao do item;
- modulo;
- peca individual;
- override manual na linha de custeio.

Assim, a mesma definicao `PORTA` pode ser lacada de branco num orcamento e de outra cor noutro, sem duplicar a definicao.

## Relacao com ValueSets / configuracoes

A logica segue os ValueSets ja descritos em `docs/05`:

- o orcamento pode definir um acabamento padrao para portas;
- o item pode alterar o acabamento padrao herdado do orcamento;
- uma peca especifica pode ter um acabamento local diferente;
- uma linha de custeio pode ter override manual.

A resolucao do acabamento segue a mesma ordem de prioridade dos materiais: override manual da linha, depois peca, depois modulo, depois item, depois orcamento, e por fim um eventual padrao do sistema.

## Campos conceptuais futuros na peca

Apenas em conceito, uma peca aplicada ao orcamento podera vir a ter campos como:

| Campo | Descricao |
| --- | --- |
| `acabamento_face_sup_id` | Acabamento da face superior (referencia a materia-prima de acabamento). |
| `acabamento_face_inf_id` | Acabamento da face inferior. |
| `acabamento_face_sup_origem` | Origem do acabamento da face superior: `ORCAMENTO`, `ITEM`, `MODULO`, `PECA` ou `MANUAL`. |
| `acabamento_face_inf_origem` | Origem do acabamento da face inferior. |
| `acabamento_override_manual` | Booleano que indica que o acabamento foi editado manualmente. |

A estrutura concreta sera decidida numa fase posterior.

## Calculo conceptual do acabamento

O calculo do acabamento pode depender de:

- area da face superior;
- area da face inferior;
- quantidade de pecas;
- preco por m2;
- custo minimo;
- setup;
- mao de obra;
- tipo de acabamento;
- numero de demaos / fases, se aplicavel.

Calculo conceptual base (por area):

```text
area_face = comp * larg
custo_face_sup = area_face * preco_acabamento_face_sup
custo_face_inf = area_face * preco_acabamento_face_inf
custo_total = quantidade * (custo_face_sup + custo_face_inf)
```

As medidas seguem a logica de peca horizontal (Comp / Larg / Esp), sem usar a designacao Altura.

Alguns acabamentos podem nao ser apenas por area. Um acabamento pode ter:

- custo por m2;
- custo fixo;
- custo minimo;
- custo por peca;
- custo de setup;
- custo de mao de obra.

O modelo de calculo deve permitir combinar estas parcelas conforme o tipo de acabamento.

## Acabamentos geram operacoes de producao

Alem do material de acabamento, um acabamento pode gerar operacoes de producao, por exemplo:

- preparacao;
- lixagem;
- aplicacao de primario;
- pintura / lacagem;
- secagem;
- polimento;
- embalagem especial.

Futuramente, um acabamento aplicado a uma peca pode gerar varias linhas no custeio:

- uma linha de material / acabamento;
- uma linha de operacao / mao de obra;
- uma linha de setup.

Estas operacoes ligam-se ao catalogo de operacoes ja documentado em `docs/09`.

## Identificacao visual no UI futuro

Na interface futura, o utilizador deve perceber facilmente:

- se a peca tem acabamento;
- qual o acabamento na face superior;
- qual o acabamento na face inferior;
- se o acabamento foi herdado do orcamento / item;
- ou se foi editado manualmente.

Para acabamento editado localmente, deve existir um aviso visual claro, por exemplo:

```text
⚠ Acabamento editado localmente
```

## Historico e snapshots de preco

Os acabamentos devem preservar historico:

- se o preco do acabamento mudar na tabela de materias-primas, os orcamentos antigos **nao devem ser alterados automaticamente**;
- as linhas ja calculadas devem guardar um snapshot do preco usado.

Isto garante que um orcamento aprovado mantem os valores com que foi fechado, mesmo que a tabela global mude depois.

## Relacao com materias-primas

Os acabamentos relacionam-se com o catalogo de materias-primas:

- os acabamentos podem ser uma categoria / grupo dentro de `def_materias_primas`;
- podem ser filtrados por tipo / familia Martelo, por exemplo `ACABAMENTOS`;
- nem todas as materias-primas sao acabamentos;
- so acabamentos ativos devem aparecer nas escolhas novas.

Assim, a selecao de acabamento reaproveita o catalogo e a logica de importacao do Excel ja documentados, sem criar uma tabela separada so para acabamentos (decisao a confirmar).

## Relacao com pecas compostas

Numa peca composta, o acabamento deve aplicar-se a peca componente correta, e nao obrigatoriamente a peca composta como um todo.

Exemplo: uma `GAVETA` pode ter a frente com acabamento (lacado) e as laterais sem acabamento. O acabamento da frente nao deve ser aplicado as laterais.

Isto significa que o acabamento e resolvido ao nivel de cada peca componente, respeitando a estrutura da peca composta descrita em `docs/02`.

## Relacao com modulos

Em relacao aos modulos:

- um modulo pode herdar o acabamento do item / orcamento;
- pecas dentro do modulo podem ter acabamento diferente;
- alteracoes ao modulo inserido num orcamento nao devem alterar a biblioteca de modulos.

Ou seja, o acabamento aplicado a um modulo concreto de um orcamento e uma ocorrencia local, que nao deve modificar a definicao reutilizavel do modulo (ver `docs/08`).

## Fora do ambito deste documento

Este documento nao implementa:

- codigo Python;
- models SQLAlchemy;
- migrations Alembic;
- alteracoes de UI;
- tabelas ou campos de acabamento;
- importacao de acabamentos do Excel;
- motor de calculo de acabamentos.

## Decisoes pendentes

Antes de implementar acabamentos, devem ficar respondidas as seguintes perguntas:

- como identificar acabamentos no Excel de materias-primas?
- usar `tipo_martelo = ACABAMENTO` ou `familia_martelo = ACABAMENTOS`?
- a selecao do acabamento sera feita nos Dados Gerais do orcamento, no item, no modulo ou na peca?
- como calcular o custo minimo?
- como tratar o setup?
- como criar os snapshots de preco?
- como apresentar `face_sup` / `face_inf` de forma simples para o utilizador?
- como tratar pecas sem acabamento?
- como tratar acabamento diferente por face?

## Proxima fase sugerida

**Fase 7F** - ligar operacoes as definicoes de pecas, considerando que as pecas tambem poderao ter acabamentos no futuro.

Esta fase seguinte deve permitir associar operacoes de producao as definicoes de pecas, deixando o modelo preparado para que, mais tarde, os acabamentos tambem possam gerar operacoes e materiais de forma coerente com o que este documento descreve.
