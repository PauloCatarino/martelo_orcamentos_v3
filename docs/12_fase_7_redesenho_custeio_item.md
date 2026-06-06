# Fase 7 - Redesenho do custeio por item

## Objetivo

Este documento redefine a direcao funcional do custeio depois da experiencia da Fase 7L com uma dialog de "Nova Linha Manual".

A conclusao do teste manual foi clara: a criacao manual por formulario grande nao deve ser o caminho principal do custeio. Ela continua a ser util, mas apenas para excecoes.

O custeio principal do Martelo Orcamentos V3 deve ser rapido, pratico e feito dentro de cada item do orcamento, aproximando-se da filosofia do V2/IMOS: escolher elementos de bibliotecas tecnicas, inserir rapidamente no item e deixar que regras, medidas, materiais e configuracoes gerem as linhas de custo sempre que possivel.

Esta fase e apenas documentacao e analise. Nao cria codigo Python, migrations, models, alteracoes de UI ou implementacao de custeio.

## Porque a "Nova Linha Manual" nao e o caminho principal

A abordagem de "Nova Linha Manual" com formulario grande obriga o utilizador a preencher dezenas de campos para cada linha normal de custeio. Isso torna o processo lento e pouco pratico.

O objetivo principal do custeio deve ser rapidez. O utilizador nao deve preencher manualmente todos os detalhes de material, operacao, maquina, ferragem, orla, quantidade e preco para cada linha normal. Esses dados devem vir, sempre que possivel, de:

- biblioteca de pecas;
- pecas compostas;
- modulos guardados;
- configuracoes de materiais;
- ferragens e acessorios;
- regras de operacoes;
- ValueSets do orcamento ou do item.

A criacao manual por formulario grande fica, por isso, descartada temporariamente como abordagem principal.

## Papel da linha manual

A linha manual continua a ser util, mas apenas para excecoes:

- ajuste manual;
- custo especial;
- operacao livre;
- observacao ou correcao pontual;
- custo que ainda nao existe em biblioteca;
- situacao que nao justifica criar uma regra permanente.

Uma linha manual deve ser uma ferramenta de excecao, nao a forma normal de construir o custeio do item.

## Custeio principal por item

O custeio principal deve acontecer dentro de cada item do orcamento.

Um orcamento pode ter varios items e cada item deve ter o seu proprio custeio:

```text
Orcamento 260001_01
  Item 1: custeio proprio
  Item 2: custeio proprio
  Item 3: custeio proprio
```

O separador Custeio global do orcamento pode futuramente mostrar um resumo geral, consolidando custos e precos dos items. No entanto, a edicao principal deve ser feita no item, porque e no item que existem medidas, contexto tecnico, modulos, pecas, ferragens e operacoes concretas.

## Medidas e variaveis do item

Cada item tem medidas principais:

- Comp;
- Larg;
- Prof;
- Esp, quando aplicavel;
- variaveis futuras.

As pecas inseridas no custeio do item devem poder usar estas medidas e variaveis.

Exemplo: num item `Roupeiro`, uma peca `LATERAL` pode usar `Comp` e `Prof`; uma `PORTA` pode usar `Comp` e `Larg`; uma `PRATELEIRA` pode usar `Larg` e `Prof`. As regras futuras devem permitir que a peca use as medidas do item, do modulo ou overrides locais.

## Acoes rapidas de insercao

O utilizador deve inserir linhas atraves de acoes rapidas:

- selecionar peca da biblioteca;
- importar modulo guardado;
- inserir peca composta;
- inserir ferragem ou acessorio;
- inserir operacao manual simples.

Estas acoes devem gerar linhas de custeio com dados herdados ou calculados. O utilizador deve editar apenas o que precisa de alterar.

## Layout conceptual futuro

O layout futuro deve aproximar-se da logica do V2:

- painel esquerdo com biblioteca de pecas, componentes e modulos;
- grelha central com linhas de custeio do item;
- zona superior com contexto do orcamento e do item;
- botoes de acao rapida.

Proposta conceptual:

```text
Custeio do Item: ITEM-TESTE-001 - Roupeiro Teste

Orcamento 260001_01 > Item: ITEM-TESTE-001 > Custeio

Medidas:
Comp: 2400 | Larg: 1800 | Prof: 600

Botoes:
Importar Modulo
Inserir Peca
Inserir Operacao
Atualizar Custeio
Guardar Custeio

Esquerda:
Biblioteca de pecas/componentes/modulos

Centro:
Grelha de custeio do item
```

Numa representacao de interface:

```text
+--------------------------------------------------------------------+
| Orcamento 260001_01 > Item: ITEM-TESTE-001 > Custeio               |
| Comp: 2400 | Larg: 1800 | Prof: 600                                |
+----------------------+---------------------------------------------+
| Biblioteca           | Grelha de custeio do item                   |
|                      |---------------------------------------------|
| Pesquisa...          | Tipo | Codigo | Descricao | Qtd | Custo     |
| > Pecas simples      | ...                                         |
| > Pecas compostas    |                                             |
| > Ferragens          |                                             |
| > Acessorios         |                                             |
| > Operacoes          |                                             |
| > Modulos guardados  |                                             |
+----------------------+---------------------------------------------+
| [Importar Modulo] [Inserir Peca] [Inserir Operacao]                |
| [Atualizar Custeio] [Guardar Custeio]                              |
+--------------------------------------------------------------------+
```

## Biblioteca lateral

A biblioteca lateral deve permitir pesquisar e selecionar:

- pecas simples;
- pecas compostas;
- ferragens;
- acessorios;
- operacoes;
- modulos guardados.

As pecas simples vem de `def_pecas`.

As pecas compostas vem de `def_pecas` e expandem componentes definidos em `def_peca_componentes`.

Os modulos guardados devem ser importados como copias locais editaveis dentro do item. Ao importar um modulo, as suas pecas, ferragens, operacoes e regras passam a pertencer ao item do orcamento e podem ser ajustadas localmente.

Alterar o modulo local dentro do orcamento nao deve alterar automaticamente o modelo da biblioteca.

## Remocao local e bibliotecas tecnicas

As linhas locais do custeio podem ser removidas do item. Elas pertencem ao orcamento em edicao e representam uma instancia local.

Existe uma diferenca importante:

| Tipo | Regra |
| --- | --- |
| Bibliotecas tecnicas | Nao eliminar; apenas desativar. |
| Linhas locais de custeio | Podem ser removidas ou desativadas no item. |

Bibliotecas tecnicas incluem `def_pecas`, `def_operacoes`, `def_maquinas`, materias-primas, ferragens, acessorios e modulos guardados. Eliminar registos de biblioteca pode quebrar historico e referencias antigas.

Linhas locais de custeio, por outro lado, pertencem ao item do orcamento e podem ser removidas durante a edicao.

## Materiais e ValueSets

Os materiais e ferragens por defeito devem vir de configuracoes do orcamento ou do item, semelhante aos ValueSets do IMOS.

Exemplo:

- a peca `PORTA` pertence ao grupo logico `PORTAS`;
- o item define que `PORTAS` usam determinada materia-prima;
- ao inserir `PORTA` no custeio, o sistema resolve o material automaticamente;
- se necessario, o utilizador pode alterar localmente a linha.

Isto evita que o utilizador escolha manualmente o material de cada linha normal.

## Edicao local e aviso visual

Cada linha de custeio deve poder ser editada localmente.

Podem ser editados, por exemplo:

- descricao;
- quantidade;
- medidas;
- material;
- ferragem;
- preco;
- tempo;
- margem;
- observacoes.

Quando uma linha for editada localmente, deve mostrar aviso:

```text
⚠ Editado localmente
```

Este aviso ajuda a distinguir linhas herdadas/calculadas de linhas alteradas pelo utilizador.

## Ligacoes da linha de custeio

As linhas do custeio devem conseguir conectar:

- peca;
- material;
- orlas;
- ferragens;
- operacoes;
- maquinas;
- acabamentos;
- mao de obra;
- preco final.

Uma linha de custeio pode nascer de uma peca simples, de uma peca composta, de um modulo importado, de uma ferragem solta, de uma operacao manual ou de uma insercao manual excepcional.

## Relacao com pecas simples, compostas e modulos

Pecas simples vem de `def_pecas`. Ao inserir uma peca simples no custeio do item, o sistema deve criar uma linha local ou conjunto de linhas locais com medidas, material e operacoes derivadas.

Pecas compostas expandem componentes. Inserir uma peca composta como `GAVETA` pode gerar varias pecas, ferragens e operacoes associadas.

Modulos importados devem ser copias locais editaveis. Um modulo de biblioteca serve como modelo, mas o modulo inserido no item deve poder ser adaptado sem alterar a biblioteca.

## Separador Custeio global do orcamento

O separador Custeio global do orcamento pode continuar a existir, mas como resumo:

- total por item;
- total por tipo de custo;
- total de materiais;
- total de ferragens;
- total de operacoes;
- total de mao de obra;
- preco final consolidado.

A edicao detalhada deve acontecer no custeio do item.

## Fora do ambito deste documento

Este documento nao implementa:

- codigo Python;
- models SQLAlchemy;
- migrations Alembic;
- alteracoes de UI;
- recuperacao do stash experimental;
- nova linha manual;
- motor de calculo;
- geracao automatica de linhas.

Serve apenas para fixar a nova direcao do custeio antes de continuar a implementacao.

## Fases seguintes propostas

- Fase 7M: criar Custeio por Item como pagina propria;
- Fase 7N: mostrar biblioteca de pecas no lado esquerdo;
- Fase 7O: inserir peca simples no custeio do item;
- Fase 7P: remover linha do custeio do item;
- Fase 7Q: importar modulo para custeio do item;
- Fase 7R: expandir peca composta;
- Fase 7S: aplicar materiais/valuesets;
- Fase 7T: gerar orlas;
- Fase 7U: gerar operacoes;
- Fase 7V: gerar acabamentos.
