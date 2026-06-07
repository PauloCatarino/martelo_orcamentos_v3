# Fase 7 - Arquitetura de definicoes de pecas, chaves ValueSet, opcoes e modulos guardados

## Objetivo

Este documento esclarece como `Codigo`, `Nome`, `Grupo`, `Tipo de peca`, `Chave ValueSet`, opcoes de ValueSet, modulos guardados e linhas de custeio se relacionam.

Serve para fixar a arquitetura antes de evoluir o custeio e os ValueSets. Usa como contexto `docs/02` (pecas), `docs/05` (ValueSets), `docs/11` (linhas de custeio), `docs/12` (redesenho do custeio), `docs/13` (modelo de ValueSets) e `docs/14` (ligacao pecas <-> ValueSets).

Esta fase e apenas documentacao. Nao deve ser criado codigo, models, migrations nem alteracoes de UI neste momento.

## Regra de ouro do Martelo V3

```text
Automatico por defeito.
Editavel quando necessario.
Historico preservado sempre.
```

Tudo o que se segue deve respeitar esta regra: o programa resolve sozinho sempre que pode, o utilizador altera quando precisa, e o que foi calculado fica guardado.

## Martelo V3 deve ser amigo do utilizador

O objetivo e que o programa seja pratico:

- o programa deve preencher automaticamente sempre que possivel;
- o utilizador deve apenas supervisionar, corrigir ou personalizar;
- quanto menos preenchimento manual repetitivo, melhor.

O custeio nao deve obrigar a escolher material, ferragem, preco e operacao linha a linha. Esses dados devem vir de bibliotecas, regras e ValueSets.

## Campos da definicao de peca

| Campo | Funcao |
| --- | --- |
| `Codigo` | Identificador tecnico unico da definicao (ex.: `COSTA`). |
| `Nome` | Nome amigavel apresentado ao utilizador. |
| `Grupo` | Organizacao visual / pesquisa / biblioteca (ex.: `COSTAS`). |
| `Tipo de peca` | Simples, composta, etc. |
| `Chave ValueSet` | Categoria usada para resolver material/ferragem/acabamento por defeito. |

## O Codigo nao e a referencia da materia-prima

O `Codigo` identifica a **definicao tecnica**, nao o artigo comprado.

Exemplo: `CORREDICA` e uma definicao tecnica. A **referencia concreta** da materia-prima (marca, modelo, preco) vem do ValueSet ou da tabela de materias-primas, e nao do codigo da peca.

## O que uma definicao de peca pode representar

Uma definicao de peca e generica e pode representar:

- peca de madeira;
- peca composta;
- ferragem generica;
- ferragem especifica;
- acessorio;
- iluminacao;
- sistema de correr;
- operacao;
- componente tecnico.

## Quatro conceitos distintos

E importante nao confundir quatro coisas diferentes:

| Conceito | O que e |
| --- | --- |
| Definicao tecnica da peca/componente | Regras, comportamento, furacao, montagem, medidas. |
| Materia-prima / artigo comprado | Artigo real com referencia, fornecedor e preco. |
| Opcao de ValueSet | Escolha por defeito (material/ferragem/acabamento) para uma chave. |
| Linha de custeio | Instancia local no item, com snapshot dos valores usados. |

## Exemplos de definicoes de peca

| Codigo | Grupo | Chave ValueSet |
| --- | --- | --- |
| `COSTA` | `COSTAS` | `MATERIAL_COSTAS` |
| `LATERAL` | `LATERAIS` | `MATERIAL_LATERAIS` |
| `TAMPO` | `TAMPOS` | `MATERIAL_TAMPOS` |
| `PORTA` | `PORTAS` | `MATERIAL_PORTAS` |
| `CORREDICA` | `CORREDICAS` | `FERRAGEM_CORREDICA` |
| `CORREDICA_EMUCA_VERTEX` | `CORREDICAS` | `FERRAGEM_CORREDICA` |

Note-se que `CORREDICA` e `CORREDICA_EMUCA_VERTEX` partilham a mesma chave `FERRAGEM_CORREDICA`: sao definicoes diferentes apenas se houver diferenca tecnica relevante.

## Regra de decisao: nova def_peca ou nova opcao de ValueSet?

```text
Se muda apenas artigo / preco / fornecedor  -> opcao do ValueSet.
Se muda comportamento tecnico / regra / furacao / montagem -> definicao de peca/componente.
```

Daqui resulta que:

- podem existir varias linhas de dobradicas, corredicas e puxadores **na biblioteca de pecas** quando houver diferencas tecnicas relevantes;
- podem existir varias opcoes de dobradicas, corredicas e puxadores **dentro do ValueSet** quando forem apenas alternativas de material/ferragem/preco.

## Varias opcoes por chave

Exemplos de varias opcoes para a mesma chave (ver `docs/14` e o modelo da Fase 7P.1):

```text
FERRAGEM_CORREDICA:
  CORREDICA_1 = Blum Tandem extracao total   (padrao)
  CORREDICA_2 = Emuca lateral metalica        (alternativa)
  CORREDICA_3 = Emuca Vertex H140             (alternativa)
  CORREDICA_4 = Silver extracao total         (alternativa)

FERRAGEM_DOBRADICA:
  DOBRADICA_1 = Blum reta                      (padrao)
  DOBRADICA_2 = Emuca reta                     (alternativa)
  DOBRADICA_3 = Salice Lapis                   (alternativa)

FERRAGEM_PUXADOR:
  PUXADOR_1 = Puxador aplicar                  (padrao)
  PUXADOR_2 = Puxador Wave                      (alternativa)
  PUXADOR_3 = Tic Tac                           (alternativa)
```

Cada chave do ValueSet pode ter:

- varias opcoes;
- uma opcao padrao;
- opcoes alternativas;
- ligacao a materia-prima;
- ordem;
- estado ativo/inativo.

## Hierarquia: orcamento -> item -> linha de custeio

```text
Orcamento  ->  Item  ->  Linha de custeio
```

- O **ValueSet do orcamento** define as opcoes globais.
- O **ValueSet do item** herda do orcamento e pode alterar opcoes.
- A **linha de custeio** herda do item e pode ser editada localmente.

## Fluxo ao inserir uma peca simples

```text
a) utilizador seleciona peca na biblioteca
b) programa le a chave ValueSet da definicao da peca
c) procura a opcao padrao no ValueSet do ITEM
d) se nao existir, procura no ValueSet do ORCAMENTO
e) aplica materia-prima / ferragem / acabamento
f) guarda snapshot na linha de custeio
g) permite alteracao local
```

Exemplo:

```text
Peca COSTA
  chave = MATERIAL_COSTAS

ValueSet do item
  MATERIAL_COSTAS padrao = AGL MLC CANCUN 12MM

Linha de custeio
  Def_Peca           = COSTA
  Material           = AGL MLC CANCUN 12MM
  Origem             = ValueSet do item
  Editado localmente = Nao
```

## Ferragens diferentes por item (roupeiro vs cozinha)

O mesmo orcamento pode ter um item `Roupeiro` e um item `Cozinha`, cada um com ferragens diferentes, usando a **mesma** definicao `DOBRADICA`/`CORREDICA` mas opcoes diferentes no ValueSet do item:

```text
Item Roupeiro
  FERRAGEM_DOBRADICA padrao = Blum reta
  FERRAGEM_CORREDICA padrao = Blum Tandem

Item Cozinha
  FERRAGEM_DOBRADICA padrao = Emuca reta
  FERRAGEM_CORREDICA padrao = Emuca Vertex
```

So se deve criar chaves especificas (`FERRAGEM_DOBRADICA_ROUPEIRO`, `FERRAGEM_DOBRADICA_COZINHA`) quando a chave generica `FERRAGEM_DOBRADICA` **nao for suficiente**. Por norma, basta a chave generica com opcoes diferentes por item.

## Modulos guardados

Um modulo guardado e um conjunto reutilizavel de pecas/ferragens/operacoes (ver `docs/12`). Pode ter **predefinicoes proprias** de materiais/ferragens/acabamentos/sistemas.

```text
Modulo de roupeiro guardado
  usa CORREDICA_1 por defeito
  usa DOBRADICA_1 por defeito
  usa MATERIAL_LATERAIS definido para roupeiro
  usa SISTEMA_CORRER_RODIZIO_SUP se aplicavel

Modulo de cozinha guardado
  usa CORREDICA_2 por defeito
  usa DOBRADICA_2 por defeito
  usa MATERIAL_FRENTES especifico
  usa ACABAMENTO_FACE_SUP / ACABAMENTO_FACE_INF especifico se aplicavel
```

## Importar um modulo: estrategias de resolucao

Ao importar um modulo guardado para o custeio do item, os materiais/ferragens podem ser resolvidos por:

- **Estrategia A** - usar sempre o ValueSet do item;
- **Estrategia B** - usar as predefinicoes do modulo guardado quando existirem;
- **Estrategia C** - usar as predefinicoes do modulo, mas permitir adaptar ao ValueSet do item.

**Estrategia inicial recomendada:** para manter simples, o modulo importado deve usar o **ValueSet do item** por defeito. Mais tarde pode existir uma opcao avancada no momento da importacao:

```text
[ ] Usar predefinicoes do modulo guardado
[ ] Adaptar ao ValueSet do item
```

Regras importantes:

- um modulo guardado **nunca** deve alterar o ValueSet do orcamento nem o do item; ao importar, cria uma **instancia local** no item;
- **modulo de biblioteca** e **modulo inserido no item** sao coisas diferentes: o de biblioteca e modelo; o inserido no item e copia local editavel.

## As linhas geradas por modulo sao editaveis

As linhas geradas por um modulo importado devem poder ser alteradas:

- trocar corredica;
- trocar dobradica;
- trocar material;
- trocar acabamento;
- selecionar materia-prima diretamente;
- editar localmente descricao / preco / medidas / desperdicio (com aviso `⚠ Editado localmente`).

## O que a linha de custeio preserva

Para preservar o historico, a linha de custeio deve guardar:

- chave ValueSet original;
- opcao ValueSet usada;
- materia-prima usada;
- origem (ver abaixo);
- snapshot de preco / unidade / descricao.

Valores de origem:

- `VALUESET_ITEM`
- `VALUESET_ORCAMENTO`
- `MODULO_GUARDADO`
- `MATERIA_PRIMA_MANUAL`
- `EDITADO_LOCALMENTE`

## Acabamentos

- a peca pode permitir ou nao acabamento;
- a face superior e a face inferior podem ter chaves diferentes;
- a linha de custeio deve permitir: sem acabamento; so face superior; so face inferior; ambas as faces; faces com acabamentos diferentes.

## Orlas

- a definicao da peca indica os lados com orla (ver `docs/03`);
- o material selecionado pode indicar a orla fina/grossa associada;
- o ValueSet pode definir o fallback de orla fina/grossa;
- a linha de custeio gera os metros lineares de orla;
- a operacao de orlagem e calculada separadamente.

## Chaves ValueSet configuraveis (futura def_valueset_chaves)

As chaves ValueSet **nao devem ficar apenas fixas no codigo**. Deve existir uma futura tabela `def_valueset_chaves`:

| Campo | Descricao |
| --- | --- |
| `id` | Identificador. |
| `codigo` | Codigo tecnico da chave (ex.: `FERRAGEM_CORREDICA`). |
| `nome` | Nome amigavel. |
| `descricao` | Descricao. |
| `tipo` | Material, ferragem, acabamento, sistema, etc. |
| `grupo` | Agrupamento logico. |
| `sistema` | Sistema associado, quando aplicavel. |
| `ativo` | Estado ativo/inativo. |
| `ordem` | Ordenacao. |

As chaves base podem ser criadas por seed, mas o **admin pode adicionar novas** sem mexer no codigo.

## Impacto no UI futuro

- **Configuracoes > Chaves ValueSet** para gerir as chaves;
- as **Definicoes de Pecas** passam a usar um combo vindo dessas chaves;
- o ValueSet do orcamento/item usa essas chaves;
- a linha de custeio mostra a chave, a opcao padrao e a materia-prima aplicada;
- os modulos guardados podem ter predefinicoes proprias.

## Decisoes pendentes

- quando criar uma nova `def_peca` vs uma nova opcao de ValueSet;
- como apresentar as alternativas na linha de custeio;
- como tratar materia-prima inexistente;
- como tratar o historico;
- como copiar o ValueSet do orcamento para o item;
- como os modulos guardados resolvem os defaults;
- se o modulo guardado pode forcar uma opcao especifica;
- se o utilizador escolhe no momento da importacao (usar defaults do modulo ou adaptar ao item);
- como bloquear ou avisar se a chave usada for desativada.

## Fora do ambito deste documento

Este documento nao implementa codigo, models, migrations, UI, motor de resolucao nem geracao automatica de linhas. Serve apenas para fixar a arquitetura.

## Proxima fase sugerida

**Fase 7R** - criar o modelo configuravel de chaves ValueSet (`def_valueset_chaves`), com seed das chaves base, preparando a gestao pelo admin descrita neste documento.
