# Fase 6 - Modelo de configuracao de materiais e ferragens por orcamento (ValueSets)

## Objetivo

Este documento descreve como o material ou ferragem concreta deve ser atribuido as pecas no Martelo Orcamentos V3, sem ligar a materia-prima diretamente a definicao da peca.

A ideia central e separar o que a peca e (comportamento tecnico) do material real que ela usa (escolha por orcamento ou item), de forma semelhante aos ValueSets do IMOS.

Esta fase e apenas documentacao tecnica. Nao deve ser criado codigo, models, migrations nem alteracoes de UI neste momento.

## Materias-primas como catalogo real

As materias-primas sao o catalogo real de materiais, ferragens, acessorios, SPP e afins disponiveis no sistema. Este catalogo ja existe no sistema antigo / Excel e contem itens concretos com codigo, descricao, preco e outros dados.

Exemplos de itens concretos:

- `MDF_BRANCO_B3002_19MM`
- `MDF_BRANCO_08MM`
- `BLUM_75B7250`
- `BLUM_TANDEM_500`
- `PUXADOR_X`

Este catalogo representa o que existe e pode ser comprado/usado, nao o que cada peca obrigatoriamente usa.

## A definicao de peca nao aponta para materias-primas concretas

A definicao de peca (`def_pecas`) NAO deve apontar diretamente para uma materia-prima concreta.

Exemplo:

A definicao `PORTA` indica que e uma peca, que pode ter orlas e que pode fazer parte de uma peca composta. Mas a definicao `PORTA` nao deve dizer que usa `MDF_BRANCO_B3002_19MM`.

A definicao da peca guarda apenas comportamento tecnico:

- codigo;
- nome;
- tipo simples ou composta;
- grupo;
- orlas;
- componentes;
- regras futuras;
- operacoes futuras.

Desta forma, a mesma definicao `PORTA` pode ser usada em varios orcamentos com materiais diferentes, sem duplicar a definicao.

## O material concreto vem da configuracao do orcamento ou do item

O material ou ferragem concreta deve vir da configuracao do orcamento ou da configuracao do item, nao da definicao da peca.

Exemplo de configuracao ao nivel do orcamento:

```text
Portas       -> MDF_BRANCO_B3002_19MM
Prateleiras  -> MDF_BRANCO_B3002_19MM
Costas       -> MDF_BRANCO_08MM
Dobradicas   -> BLUM_75B7250
Corredicas   -> BLUM_TANDEM_500
Puxadores    -> PUXADOR_X
```

Quando uma peca composta como `PORTA + DOBRADICA` entra no custeio:

- a `PORTA` usa o material definido para o grupo `PORTAS`;
- a `DOBRADICA` usa a ferragem definida para o grupo `DOBRADICAS`.

A peca diz a que grupo pertence; a configuracao do orcamento ou do item diz qual o material real desse grupo.

## Analogia com ValueSets do IMOS

Esta logica e semelhante aos ValueSets do IMOS:

- o orcamento tem um conjunto de escolhas por defeito (um ValueSet);
- cada item pode herdar essas escolhas do orcamento;
- cada item pode sobrepor algumas escolhas com valores proprios;
- cada linha de custeio pode futuramente permitir override manual/local.

Assim, a maior parte das pecas resolve o seu material automaticamente a partir das escolhas do orcamento, e apenas os casos especiais precisam de ajuste manual.

## Niveis de resolucao do material

Quando o custeio precisa de saber o material de uma peca ou componente, deve resolver por ordem de prioridade:

1. override / manual na linha de custeio, se existir;
2. configuracao especifica do item;
3. configuracao geral do orcamento;
4. valor padrao do sistema, se existir;
5. aviso de material / ferragem nao definido.

O primeiro nivel que tiver valor ganha. Se nenhum nivel definir o material, o sistema deve avisar que o material ou ferragem nao esta definido, em vez de assumir um valor silencioso.

## Override local da linha de custeio

Nem sempre a materia-prima ou ferragem exata existe na tabela geral. Por vezes o utilizador escolhe uma materia-prima parecida e ajusta localmente na linha de custeio, sem ser obrigado a criar uma nova materia-prima global.

Muitas materias-primas podem ser usadas apenas uma vez, para um orcamento especifico. Obrigar a criar um registo global para cada caso encheria o catalogo de itens irrelevantes.

Por isso, a linha de custeio pode partir de uma materia-prima existente, mas permitir ajustes locais que so valem para aquele orcamento.

Exemplos de override local:

- escolher um MDF parecido e alterar a descricao local;
- alterar o preco unitario apenas para aquele orcamento;
- alterar a margem apenas para aquela linha;
- alterar medidas ou consumo especifico;
- escrever uma observacao sobre material especial;
- usar uma referencia temporaria de fornecedor.

## Rastreabilidade do override

O override local deve preservar a rastreabilidade. A linha deve guardar tanto o valor de origem como o valor local, para se perceber o que foi alterado.

A linha deve poder registar:

- materia-prima base selecionada, se existir;
- descricao original;
- descricao local;
- preco original;
- preco local;
- margem original;
- margem local;
- indicacao de que a linha foi alterada manualmente;
- data da alteracao;
- utilizador que alterou, se possivel no futuro.

Isto permite comparar o valor de catalogo com o valor usado e identificar facilmente as linhas ajustadas.

## Exemplo: PORTA + DOBRADICA

Para uma peca composta `PORTA + DOBRADICA`:

- o componente `PORTA` resolve o material no grupo `PORTAS`;
- o componente `DOBRADICA` resolve a ferragem no grupo `DOBRADICAS`;
- se a dobradica exata nao existir na tabela, o utilizador pode usar uma dobradica parecida e ajustar localmente na linha de custeio (descricao, preco, observacao), sem criar uma nova ferragem global.

A peca composta nao decide o material. Apenas indica os tipos e grupos; o material real e resolvido pela configuracao e, quando preciso, ajustado na linha de custeio.

## Componentes compostos guardam apenas o tipo logico

Os componentes de uma peca composta nao guardam a materia-prima final. Guardam apenas o tipo logico do componente:

- `PECA`;
- `FERRAGEM`;
- `ACESSORIO`;
- `SPP`;
- `OPERACAO`;
- `MAO_OBRA`.

O material concreto entra apenas na fase de custeio, atraves da configuracao do orcamento/item e do eventual override local. Assim, a estrutura da peca composta mantem-se reutilizavel e independente dos materiais escolhidos em cada orcamento.

## Relacao com o Excel de materias-primas

A tabela de materias-primas antiga / Excel pode ser usada como origem futura para o catalogo `def_materias_primas`, mas precisa de limpeza e mapeamento antes de ser usada.

Nem todos os tipos do Excel devem virar categorias finais do Martelo V3. Antes de qualquer importacao deve existir revisao, porque:

- alguns tipos sao redundantes ou inconsistentes;
- alguns nomes estao desatualizados;
- a granularidade do Excel pode nao corresponder a granularidade desejada;
- alguns registos podem ser materiais usados uma unica vez, que nao devem poluir o catalogo global.

O mapeamento entre tipos antigos e grupos novos deve ser feito com criterio tecnico, nao por importacao automatica.

## Entidades futuras propostas (apenas conceito)

As seguintes entidades sao apenas conceito e nao devem ser criadas nesta fase:

| Entidade conceptual | Funcao prevista |
| --- | --- |
| `def_materias_primas` | Catalogo real de materiais, ferragens, acessorios e SPP. |
| `def_grupos_material` | Define os grupos de configuracao, como `PORTAS` ou `DOBRADICAS`. |
| `orcamento_material_config` | Escolhas de material por grupo, ao nivel do orcamento (o ValueSet por defeito). |
| `orcamento_item_material_config` | Escolhas de material por grupo, especificas de um item, que sobrepoem o orcamento. |
| `custeio_linha` | Linha concreta de custeio de um item, com material resolvido e medidas. |
| `custeio_linha_material_override` | Ajustes locais de material de uma linha, preservando a origem. |

A estrutura concreta (campos, chaves, relacoes) sera decidida numa fase posterior.

## Grupos de configuracao possiveis

Grupos de configuracao que o modelo deve conseguir suportar:

- `PORTAS`
- `PRATELEIRAS`
- `COSTAS`
- `FUNDOS`
- `TETOS`
- `GAVETAS`
- `DOBRADICAS`
- `CORREDICAS`
- `PUXADORES`
- `ACESSORIOS`
- `ILUMINACAO`
- `LEDS`
- `SPP`

A lista final de grupos deve ser revista antes de implementar. Alguns grupos podem ser fundidos ou divididos conforme a pratica real de orcamentacao.

## Estrutura conceptual de uma linha de custeio com override

Estrutura conceptual (nao final) de uma linha de custeio que suporta override local:

| Campo | Descricao |
| --- | --- |
| `id` | Identificador da linha. |
| `orcamento_item_id` | Item de orcamento a que a linha pertence. |
| `origem_material_id` | Materia-prima base selecionada, se existir (nullable). |
| `origem_material` | Origem do material da linha: `ORCAMENTO`, `ITEM`, `CATALOGO` ou `MANUAL`. |
| `grupo_material` | Grupo de configuracao, por exemplo `PORTAS` ou `DOBRADICAS`. |
| `descricao_original` | Descricao herdada da materia-prima base. |
| `descricao_local` | Descricao ajustada para esta linha. |
| `preco_original` | Preco herdado da materia-prima base. |
| `preco_local` | Preco ajustado para esta linha. |
| `margem_original` | Margem herdada/por defeito. |
| `margem_local` | Margem ajustada para esta linha. |
| `comp` | Comprimento (logica Comp / Larg / Esp). |
| `larg` | Largura. |
| `esp` | Espessura. |
| `quantidade` | Quantidade usada na linha. |
| `unidade` | Unidade de medida/calculo. |
| `override_manual` | Booleano que indica que a linha foi alterada manualmente. |
| `observacoes` | Notas livres sobre a linha. |

As medidas seguem a logica de peca horizontal (Comp / Larg / Esp), sem usar a designacao Altura.

## Origem da materia-prima na linha de custeio

Uma linha de custeio pode usar uma materia-prima ou ferragem vinda de varias origens:

- configuracao do orcamento;
- configuracao do item;
- materia-prima selecionada diretamente do catalogo;
- edicao manual / local.

Para tornar esta origem explicita, propoe-se o campo conceptual `origem_material`, com os valores possiveis:

| Valor | Significado |
| --- | --- |
| `ORCAMENTO` | O material veio da configuracao geral do orcamento. |
| `ITEM` | O material veio da configuracao especifica do item. |
| `CATALOGO` | O material foi selecionado diretamente do catalogo de materias-primas. |
| `MANUAL` | O material foi editado manualmente na linha de custeio. |

Em complemento, propoe-se o campo conceptual `override_manual` (booleano), que indica se a linha foi alterada manualmente, mesmo que tenha partido de uma das outras origens.

## Marcacao de linhas editadas manualmente

Se o utilizador editar localmente qualquer um dos seguintes valores de uma linha:

- descricao;
- preco;
- margem;
- medidas;
- fornecedor;
- referencia;
- observacoes;

entao a linha deve ficar marcada como editada manualmente (`override_manual = true` e `origem_material = MANUAL`).

Esta marcacao e importante porque a linha ja nao corresponde exatamente:

- a materia-prima original do catalogo;
- a configuracao do orcamento;
- a configuracao do item.

Sem esta marcacao, seria facil confundir uma linha ajustada manualmente com uma linha resolvida automaticamente, e perder a nocao do que foi alterado.

## Identificacao visual no custeio

Na interface de custeio deve existir uma indicacao visual clara da origem e do estado de cada linha. Pode ser, por exemplo:

- uma coluna "Origem";
- ou uma coluna "Estado";
- ou um icone / aviso "Editado manualmente".

Exemplo de apresentacao:

```text
PORTA      -> MDF Branco 19mm          -> Config. orcamento
DOBRADICA  -> BLUM 75B7250             -> Config. orcamento
PUXADOR    -> Puxador especial cliente -> Manual
```

A linha do `PUXADOR` mostra claramente que foi ajustada manualmente, enquanto as restantes foram resolvidas pela configuracao do orcamento.

## Protecao de linhas manuais

Linhas marcadas como `MANUAL` nao devem ser sobrescritas automaticamente quando a configuracao do orcamento ou do item for alterada.

Se uma alteracao de configuracao afetar uma linha manual, o sistema deve pedir confirmacao ao utilizador antes de substituir os valores locais, em vez de apagar silenciosamente o ajuste manual. Isto protege o trabalho do utilizador e evita perder ajustes especificos de um orcamento.

## Fora do ambito deste documento

Este documento nao implementa:

- codigo Python;
- models SQLAlchemy;
- migrations Alembic;
- alteracoes de UI;
- tabelas de materias-primas, grupos, configuracoes ou custeio;
- importacao de dados do Excel;
- motor de custeio.

## Decisoes pendentes antes do codigo

Antes de criar tabelas, models e migrations para esta logica, devem ficar respondidas as seguintes perguntas:

- que grupos finais de configuracao devem existir?
- ferragens e acessorios ficam na mesma tabela ou separadas?
- como importar materias-primas do Excel antigo?
- como mapear tipos antigos para grupos novos?
- como lidar com materiais por defeito por cliente, obra, orcamento ou item?
- como permitir override manual sem perder rastreabilidade?
- quando uma materia-prima usada localmente deve passar a materia-prima global?
- como proteger orcamentos antigos contra alteracoes futuras da tabela global?
- como representar visualmente o estado manual de uma linha?
- alteracoes manuais devem pedir confirmacao antes de sobrepor a configuracao?
- linhas manuais devem poder voltar a herdar a configuracao do orcamento/item?
- como tratar atualizacoes de preco em materias-primas ja usadas em orcamentos antigos?
