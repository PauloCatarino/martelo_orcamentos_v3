# Fase 8 - Arquitetura do custeio do item

## Objetivo deste documento

Fixar a arquitetura pretendida para o **custeio do item** antes de comecar a
implementar a insercao de pecas e os calculos. Serve de guia para as fases
seguintes (8D em diante).

Esta fase e **apenas documentacao**. Nao altera codigo, models, migrations,
UI nem testes.

Contexto util: `docs/11` (modelo de linhas de custeio), `docs/12` (redesenho do
custeio do item), `docs/13` (ValueSets de orcamento/item), `docs/14` (ligacao
pecas <-> ValueSets) e `docs/15` (arquitetura de definicoes de pecas e chaves).

## Regra de ouro do Martelo V3

```text
Automatico por defeito.
Editavel quando necessario.
Historico preservado sempre.
```

Tudo o que se segue respeita esta regra: o programa resolve sozinho sempre que
pode (material, ferragem, preco, operacao), o utilizador so altera quando
precisa, e o que foi calculado/escolhido fica guardado na linha.

---

## 1. Objetivo do custeio do item

Cada item do orcamento (ex.: `rp_01`, `cozinha_01`) tem a **sua propria tabela
de custeio**: a tabela `orcamento_item_custeio_linhas`.

Essa tabela e uma lista de linhas. Cada linha representa um consumo ou um
trabalho: uma peca de madeira, uma ferragem, uma operacao de producao, um
acabamento, mao de obra, etc.

A regra base e simples:

```text
custo do item = soma do custo de todas as linhas de custeio do item
preco do item = custo interno + margem
```

O custeio do item e o **cerebro do programa**: e onde se ligam definicoes de
pecas, ValueSet do item, materias-primas, ferragens, operacoes, maquinas,
orlas, acabamentos, modulos guardados, quantidades e margens para produzir um
custo interno e um preco final.

Exemplo simples (roupeiro `rp_01`):

| Linha | Tipo | Descricao | QT total | Custo |
| --- | --- | --- | --- | --- |
| 1 | PECA | Lateral (MATERIAL_LATERAIS) | 2 | ... |
| 2 | PECA | Costa (MATERIAL_COSTAS) | 1 | ... |
| 3 | PECA | Porta (MATERIAL_PORTAS) | 2 | ... |
| 4 | FERRAGEM | Dobradica (FERRAGEM_DOBRADICA) | 8 | ... |
| 5 | OPERACAO | Orlagem | ... | ... |

---

## 2. Hierarquia atual

A informacao de material/ferragem/acabamento desce sempre nesta ordem:

```text
Modelo ValueSet (biblioteca reutilizavel)
  -> ValueSet do Orcamento   (def_valueset -> orcamento_valueset_linhas)
  -> ValueSet do Item        (orcamento_item_valueset_linhas)
  -> Linha de Custeio        (orcamento_item_custeio_linhas)
```

- O **Modelo ValueSet** e a biblioteca (ex.: `ROUPEIRO_STANDARD`).
- O **ValueSet do Orcamento** e a configuracao geral do orcamento (pode ser
  criado a partir de um modelo).
- O **ValueSet do Item** e a copia propria do item (criada a partir do
  orcamento ou importada diretamente de um modelo) e ja editavel localmente.
- A **Linha de Custeio** e o consumo concreto.

Principio central:

> A linha de custeio usa **sempre o ValueSet do Item** como origem principal
> para materiais, ferragens e acabamentos.

O orcamento e o modelo so servem para *preencher* o ValueSet do item. Depois de
preenchido, o item e autonomo: editar o item nao altera o orcamento nem o
modelo (ja garantido nas fases 8A, 8A.1, 8A.2 e 8B).

---

## 3. Tipos de linha de custeio

A coluna `tipo_linha` define o que a linha representa:

| Tipo | Funcao |
| --- | --- |
| `MODULO` | Cabecalho/agrupador de um conjunto de linhas vindas de um modulo guardado. |
| `PECA` | Peca simples de madeira (ex.: lateral, costa, prateleira, porta). |
| `PECA_COMPOSTA` | Peca que expande para varias linhas filhas (ex.: PORTA+DOBRADICA). |
| `FERRAGEM` | Ferragem (dobradica, corredica, puxador, suporte, etc.). |
| `OPERACAO` | Trabalho de producao (corte, orlagem, CNC, furacao, montagem...). |
| `ACABAMENTO` | Acabamento aplicado a uma peca (lacar, verniz, etc.). |
| `MAO_OBRA` | Mao de obra direta nao ligada a uma maquina especifica. |
| `MANUAL` | Linha livre introduzida pelo utilizador (sem origem em biblioteca). |
| `SEPARADOR` / `TITULO` | Linha visual de organizacao, sem custo. |

Nota: a peca composta normalmente aparece como uma linha "mae"
(`PECA_COMPOSTA`) e gera linhas filhas (`PECA`, `FERRAGEM`, `OPERACAO`).

---

## 4. Biblioteca de pecas no custeio

No lado esquerdo do ecra de custeio do item devera existir uma **biblioteca em
arvore**, semelhante ao Martelo V2, alimentada por `def_pecas`.

A arvore agrupa por grupo/tipo/chave. Grupos tipicos:

```text
COSTAS
LATERAIS
TETOS
FUNDOS
PRATELEIRAS
PORTAS
PORTAS CORRER
FERRAGENS
SERVICOS
REMATES / GUARNICOES
...
```

Cada no folha e uma definicao de peca de `def_pecas` (ex.: `COSTA`,
`LATERAL`, `PORTA`, `DOBRADICA`). O utilizador escolhe na arvore e adiciona ao
custeio. O agrupamento usa o campo `Grupo`/`Tipo` da definicao.

A biblioteca deve ser pesquisavel (por codigo, nome, grupo) para o utilizador
encontrar rapidamente o que precisa.

---

## 5. Insercao de pecas simples

Fluxo automatico ao inserir uma peca simples:

1. O utilizador seleciona a peca na biblioteca (ex.: `COSTA`).
2. Adiciona ao custeio (cria uma linha `PECA`).
3. A definicao da peca indica a **chave ValueSet** (ex.: `MATERIAL_COSTAS`).
4. O item procura essa chave no **ValueSet do Item** (a opcao padrao dessa
   chave).
5. Copia para a linha o material resolvido: `ref_le`, descricao, preco tabela,
   margem, desconto, preco liquido, unidade, tipo/familia, orlas e dimensoes da
   materia-prima.
6. Calcula quantidades e custos a partir das medidas do item e da definicao.

Exemplos de ligacao peca -> chave:

```text
COSTA      -> MATERIAL_COSTAS
LATERAL    -> MATERIAL_LATERAIS
PORTA      -> MATERIAL_PORTAS
DOBRADICA  -> FERRAGEM_DOBRADICA
```

Se a chave nao existir no ValueSet do item, a linha fica sem material resolvido
(em branco) e o utilizador pode escolher manualmente (Selecionar Materia-Prima
ja existe na edicao do ValueSet do item, fase 8B).

---

## 6. Pecas compostas

Uma **peca composta** expande para varias linhas. Exemplo: `PORTA+DOBRADICA`.

```text
PORTA+DOBRADICA            (linha mae, PECA_COMPOSTA)
  PORTA                    (filha, PECA, chave MATERIAL_PORTAS)
  DOBRADICA                (filha, FERRAGEM, chave FERRAGEM_DOBRADICA)
```

- A peca principal usa a sua chave (`MATERIAL_PORTAS`).
- A dobradica usa a sua chave (`FERRAGEM_DOBRADICA`).
- As **quantidades das filhas** podem vir de regras da composta (ex.: 1 porta
  -> 2 dobradicas; portas altas -> 3 dobradicas).

A composicao (que filhas, com que regra de quantidade) e definida ao nivel das
definicoes (`def_pecas` / `def_peca_componentes`), nao manualmente linha a
linha.

---

## 7. Modulos guardados

Um **modulo guardado** e um conjunto de linhas de custeio guardadas para
reutilizacao (ex.: "modulo gaveteiro 3 gavetas", "modulo prateleira+suportes").

Podem existir:

- modulos do utilizador (pessoais);
- modulos globais (partilhados).

Ao importar um modulo para o custeio do item:

- cria as linhas do modulo no item (com `tipo_linha = MODULO` na mae e as
  filhas conforme o modulo);
- por defeito **adapta ao ValueSet do item** (o material/ferragem vem do
  ValueSet do item, nao do que estava guardado no modulo);
- recalcula quantidades/medidas com base no item.

Opcao futura (a oferecer ao importar):

```text
[ ] Usar materiais / ferragens guardados no modulo
[x] Adaptar ao ValueSet do item   (por defeito)
```

Isto segue a regra de ouro: por defeito o programa adapta automaticamente; o
utilizador pode optar por manter o que estava guardado.

---

## 8. Variaveis e medidas

O item tem medidas principais:

- Comp (comprimento)
- Larg (largura)
- Profundidade / Esp / Prof

Nas formulas das pecas podem aparecer nomenclaturas antigas (`H/L/P`,
`H1/L1/P1`, `H2/L2/P2`...), herdadas da logica anterior.

Principio do Martelo V3 (decisao a fixar):

> Internamente, todas as pecas usam **Comp / Larg / Esp**.

A dimensao principal de uma peca horizontal e sempre o **comprimento**, nunca
"altura". Qualquer nomenclatura antiga (`H/L/P`) deve ser convertida para
`Comp/Larg/Esp` na entrada, e o calculo trabalha sempre com `Comp/Larg/Esp`.

Exemplo: uma prateleira de 800 x 300 x 19 -> Comp=800, Larg=300, Esp=19.

---

## 9. Quantidades

A quantidade total de uma linha resulta de duas quantidades:

| Coluna | Significado |
| --- | --- |
| `QT_mod` | Quantidade de modulos iguais (vem do modulo / item). |
| `QT_und` | Quantidade da peca dentro de um modulo. |
| `QT_total` | `QT_mod * QT_und`. |

```text
QT_total = QT_mod * QT_und
```

Exemplo:

```text
Modulo com quantidade 3   (QT_mod = 3)
Peca lateral, 2 por modulo (QT_und = 2)
QT_total = 3 * 2 = 6 laterais
```

Todos os custos por peca sao depois multiplicados por `QT_total`.

---

## 10. Orlas

A definicao de peca tem um **codigo de orlas** que indica que lados levam orla
(ex.: `[2200]`, `[2111]`, `[2000]`...). Cada digito representa um lado e o tipo:

- 0 = sem orla;
- valor para orla fina;
- valor para orla grossa.

A linha de custeio deve calcular, a partir do perimetro e do codigo de orlas:

- ML de orla fina;
- ML de orla grossa;
- custo de orla fina;
- custo de orla grossa.

A **referencia concreta da orla** nao esta na definicao da peca: vem do material
escolhido no ValueSet do item, atraves dos campos:

- `coresp_orla_0_4` (orla fina, 0.4 mm);
- `coresp_orla_1_0` (orla grossa, 1.0 mm).

Ou seja: o codigo de orlas diz *onde e que espessura*; o ValueSet diz *qual a
orla concreta e o seu preco*.

---

## 11. Acabamentos

Os acabamentos aplicam-se **apenas a pecas**, nunca a ferragens.

Combinacoes possiveis:

- face superior;
- face inferior;
- duas faces;
- face superior com acabamento A e inferior com acabamento B.

A definicao da peca indica se permite acabamento e que chaves usar:

- `ACABAMENTO_FACE_SUP`
- `ACABAMENTO_FACE_INF`

O custo de acabamento e tipicamente calculado por **area (m2)**:

```text
area da face = Comp * Larg (em m2)
custo acabamento = area * QT_total * preco_acabamento_m2
```

O acabamento concreto (e o seu preco) e resolvido pelas chaves
`ACABAMENTO_FACE_SUP` / `ACABAMENTO_FACE_INF` no ValueSet do item.

---

## 12. Operacoes e maquinas

As definicoes de pecas podem ter **operacoes** associadas (ver
`def_peca_operacoes` e `def_maquinas_operacoes`):

- corte;
- orlagem;
- CNC;
- furacao;
- rasgo;
- montagem;
- embalamento;
- setup;
- operacao manual.

Cada operacao pode estar ligada a uma **maquina**:

```text
CORTE
ORLAGEM
CNC_VERTICAL
CNC_HORIZONTAL
CNC_ABD
CNC_5_EIXOS_ORLAGEM
MANUAL
MONTAGEM
```

As operacoes geram **custos de producao** (tempo x custo/hora da maquina, mais
setup). Sao linhas do tipo `OPERACAO` no custeio.

---

## 13. Serie / STD

Futuramente o custeio deve distinguir o tipo de producao:

- `STD` (peca a peca / pequena quantidade);
- `SERIE` (producao em serie).

Isto pode afetar tempos, setup, eficiencia, custo/hora e regras de calculo (por
exemplo, o setup diluido por mais pecas em serie).

Nesta fase **apenas documentar**; nao implementar.

---

## 14. Flags de inclusao no preco

Cada linha pode ter flags que controlam o que entra no **preco ao cliente**:

- incluir materia-prima no preco;
- incluir mao de obra no preco;
- incluir orla no preco;
- incluir producao no preco;
- incluir acabamento no preco;
- incluir ferragem no preco.

Motivo pratico: pode haver casos em que **o cliente fornece** o material ou a
ferragem. Nesse caso:

- esse custo **nao entra no preco** ao cliente;
- mas a linha **continua a aparecer nos relatorios** de consumo/producao (porque
  fisicamente a peca/ferragem e usada).

Ou seja, as flags separam "o que custa a nos" de "o que cobramos" de "o que
consumimos".

---

## 15. Custo interno e preco cliente

Cada linha (e o item) deve poder mostrar os custos por bloco:

| Bloco | Conteudo |
| --- | --- |
| Custo material | placas / materia-prima da peca. |
| Custo ferragem | dobradicas, corredicas, puxadores... |
| Custo orla | orla fina + orla grossa. |
| Custo operacoes | corte, orlagem, CNC, montagem... |
| Custo acabamento | lacar/verniz por m2. |
| Custo mao de obra | mao de obra direta. |
| **Custo total interno** | soma dos blocos incluidos. |
| Margem | margem aplicada (por tipo de custo ou global). |
| **Preco final da linha** | custo interno + margem. |

O preco do item e a soma dos precos finais das linhas (respeitando as flags de
inclusao da seccao 14).

---

## 16. Origem e edicao local

Tal como nos ValueSets, cada linha de custeio deve registar a **origem**:

| `origem_dados` | Significado |
| --- | --- |
| `BIBLIOTECA_PECA` | veio de uma peca simples da biblioteca. |
| `PECA_COMPOSTA` | gerada pela expansao de uma peca composta. |
| `MODULO_GUARDADO` | veio de um modulo guardado. |
| `VALUESET_ITEM` | material/ferragem resolvido pelo ValueSet do item. |
| `MATERIA_PRIMA` | material escolhido diretamente da tabela de materias-primas. |
| `MANUAL` | linha livre criada pelo utilizador. |
| `EDITADO_LOCALMENTE` | linha que foi alterada manualmente. |

A linha deve indicar tambem `editado_localmente = True` quando o utilizador
altera qualquer campo relevante (mesma logica ja usada no ValueSet do item na
fase 8B). Assim preserva-se o historico: sabe-se de onde veio e se foi mexida.

---

## 17. Relacao com relatorios

Algumas linhas (ou componentes) podem **nao entrar no preco** mas **devem entrar
nos relatorios internos**. Exemplos de relatorios:

- consumo de placas (m2 por material / referencia);
- consumo de orlas (ML de orla fina e grossa);
- ferragens (lista e quantidades);
- tempos de maquinas (horas por maquina/operacao);
- operacoes;
- acabamentos (m2 por acabamento).

Por isso a separacao da seccao 14 e importante: material fornecido pelo cliente
sai do preco mas continua no relatorio de consumo, para a producao saber o que
precisa.

---

## 18. Proximas fases propostas

```text
8D - criar biblioteca de pecas no custeio do item (arvore a partir de def_pecas)
8E - inserir peca simples no custeio usando o ValueSet do item
8F - expandir pecas compostas no custeio
8G - calcular areas / perimetros / orlas
8H - ligar operacoes / maquinas ao custo da linha
8I - considerar acabamentos
8J - modelo inicial de modulos guardados
```

Cada fase deve continuar a respeitar: automatico por defeito, editavel quando
necessario, historico preservado.

---

## 19. Decisoes pendentes

Pontos ainda a decidir antes/durante a implementacao:

- quais as **colunas definitivas** da tabela de custeio do item;
- como **representar Serie / STD** (campo no item? por linha? por operacao?);
- como **calcular setup** (por operacao, por maquina, diluido em serie?);
- como **tratar material fornecido pelo cliente** (flags por linha + relatorio);
- como **mostrar a arvore** da biblioteca de pecas (agrupamento, pesquisa);
- como **guardar modulos** (estrutura, ambito utilizador/global, versao);
- como **calcular acabamentos complexos** (faces diferentes, parcial);
- como **organizar margens** por tipo de custo (material vs producao vs
  ferragem) ou margem global.

Estas decisoes serao fechadas nas fases 8D em diante, sempre alinhadas com as
decisoes ja tomadas nas fases 7 e 8.
