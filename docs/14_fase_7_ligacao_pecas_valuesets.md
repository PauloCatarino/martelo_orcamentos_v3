# Fase 7 - Ligacao entre definicoes de pecas e chaves dos ValueSets

## Objetivo

Este documento descreve como as definicoes de pecas, componentes, ferragens e linhas de custeio devem resolver **automaticamente** o material, a ferragem, o acabamento e a orla atraves dos ValueSets.

A ideia central: a definicao da peca indica uma **chave** (por exemplo `MATERIAL_COSTAS`); o custeio resolve essa chave contra o ValueSet do item e, em fallback, do orcamento, aplicando a materia-prima/ferragem encontrada e guardando snapshot.

Usa como contexto `docs/05` (conceito de ValueSets), `docs/13` (modelo inicial de ValueSets do orcamento/item), `docs/11` (linhas de custeio), `docs/03` (orlas) e `docs/10` (acabamentos).

Esta fase e apenas documentacao. Nao deve ser criado codigo, models, migrations nem alteracoes de UI neste momento.

## ValueSets guardam valores por defeito

Os ValueSets guardam, por chave, os valores por defeito de:

- materiais (placas);
- ferragens e acessorios;
- orlas;
- acabamentos.

Na Fase 7O foram criadas as estruturas base: modelos de biblioteca (`def_valueset_modelos`, `def_valueset_modelo_linhas`) e linhas aplicadas (`orcamento_valueset_linhas`, `orcamento_item_valueset_linhas`). Cada linha de ValueSet associa uma **chave** a uma materia-prima/ferragem concreta.

## As definicoes de pecas indicam a chave do ValueSet

Cada definicao de peca precisa de indicar **qual chave do ValueSet** deve usar para resolver o seu material. Assim, a peca nao guarda a materia-prima concreta (ver `docs/05`); guarda apenas a chave logica.

Exemplos de pecas e respetivas chaves de material:

| Peca | Chave ValueSet (material) |
| --- | --- |
| `COSTA` | `MATERIAL_COSTAS` |
| `LATERAL` | `MATERIAL_CAIXOTE` |
| `TAMPO` | `MATERIAL_CAIXOTE` |
| `FUNDO` | `MATERIAL_FUNDOS` |
| `PORTA` | `MATERIAL_PORTAS` |
| `FRENTE_GAVETA` | `MATERIAL_FRENTES` |
| `PRATELEIRA` | `MATERIAL_PRATELEIRAS` |
| `LADO_GAVETA` | `MATERIAL_GAVETAS` ou `MATERIAL_CAIXOTE` |

## Componentes e ferragens tambem precisam de chave

Os componentes e ferragens tambem precisam de uma chave que os ligue ao ValueSet correspondente:

| Componente / ferragem | Chave ValueSet (ferragem) |
| --- | --- |
| `DOBRADICA` | `FERRAGEM_DOBRADICA` |
| `CORREDICA` | `FERRAGEM_CORREDICA` |
| `PUXADOR` | `FERRAGEM_PUXADOR` |
| `VARAO` | `FERRAGEM_VARAO` |
| `SUPORTE_VARAO` | `FERRAGEM_SUPORTE_VARAO` |
| `PE_NIVELADOR` | `FERRAGEM_PE_NIVELADOR` |
| `SISTEMA_CORRER` | `SISTEMA_CORRER` |

## Fluxo ao inserir uma peca no custeio

Ao inserir uma peca no custeio do item, o fluxo previsto e:

```text
a) utilizador seleciona peca na biblioteca
b) programa le a chave ValueSet da definicao da peca
c) programa procura essa chave primeiro no ValueSet do ITEM
d) se nao existir, procura no ValueSet do ORCAMENTO
e) aplica a materia-prima / ferragem encontrada
f) guarda snapshot na linha de custeio
g) permite edicao local
```

A ordem de resolucao (item antes do orcamento) garante que o item pode sobrepor o material por defeito do orcamento.

## Exemplo de resolucao

```text
Peca COSTA
  chave_valueset = MATERIAL_COSTAS

ValueSet do item
  MATERIAL_COSTAS = AGL MLC CANCUN 12MM

Linha de custeio gerada
  Def_Peca  = COSTA
  Material  = AGL MLC CANCUN 12MM
  Origem    = ValueSet do item
```

## O utilizador pode alterar a linha

Depois de gerada automaticamente, a linha de custeio deve permanecer flexivel. O utilizador pode:

- escolher outro material da mesma chave do ValueSet;
- escolher um material de outra chave do ValueSet;
- escolher uma materia-prima diretamente da tabela geral;
- editar localmente descricao, preco, desperdicio, medidas e observacoes.

Quando a linha for editada localmente, deve mostrar o aviso visual:

```text
⚠ Editado localmente
```

## O que a linha de custeio guarda

Para preservar rastreabilidade e historico (ver `docs/11`), a linha de custeio deve guardar:

| Campo | Descricao |
| --- | --- |
| `chave_valueset_original` | Chave usada para resolver (por exemplo `MATERIAL_COSTAS`). |
| `materia_prima_id` | Materia-prima resolvida, se existir. |
| `ref_materia_prima` | Referencia da materia-prima (snapshot). |
| `descricao_materia_prima` | Descricao da materia-prima (snapshot). |
| `origem_material` | Origem do material da linha (ver valores abaixo). |

Valores de `origem_material`:

- `VALUESET_ITEM` - resolvido pelo ValueSet do item;
- `VALUESET_ORCAMENTO` - resolvido pelo ValueSet do orcamento;
- `MATERIA_PRIMA_MANUAL` - escolhido diretamente da tabela geral;
- `EDITADO_LOCALMENTE` - alterado manualmente na linha.

## ValueSets como biblioteca editavel

Os ValueSets devem permitir **inserir, editar e suprimir** linhas. Suprimir/desativar significa **ocultar do utilizador, nao apagar** da base (coerente com a regra das bibliotecas tecnicas).

Os modelos de ValueSet devem funcionar como biblioteca:

- guardar um conjunto tipico de materiais/ferragens/acabamentos;
- importar para o orcamento;
- importar/copiar para o item;
- ajustar localmente.

Quanto menos o utilizador tiver de preencher manualmente, melhor. O objetivo e que a maior parte das linhas se resolva sozinha e o utilizador so ajuste excecoes.

## Orlas resolvidas pelo material

As orlas podem vir do **proprio material selecionado**, em vez de serem escolhidas a parte:

- a materia-prima de placa pode ter referencias para orla fina 0.4 e orla grossa 1.0;
- essas referencias apontam para artigos de orla na tabela de materias-primas;
- a definicao da peca indica quais lados levam orla;
- o codigo de orlas da peca (por exemplo `[2200]`, ver `docs/03`) define onde ha orla fina/grossa;
- o calculo usa material + codigo de orlas + dimensoes da peca.

Exemplo de orlas:

```text
Material PORTAS
  ref_orla_fina_04   = ORL0002
  ref_orla_grossa_10 = ORL0005

Peca PORTA [2200]
  lados com orla usam as referencias do material
  -> gera metros lineares de orla
  -> gera custo de material de orla
  -> gera operacao de orlagem
```

## Acabamentos

Os acabamentos tambem podem ser definidos no ValueSet (ver `docs/10`):

- `face_sup` e `face_inf` podem ter valores diferentes;
- as pecas podem permitir ou nao acabamento;
- as ferragens **nunca** tem acabamento.

A chave de acabamento da peca resolve-se contra o ValueSet da mesma forma que o material.

## Flexibilidade final

Uma linha pode comecar automatica, mas deve sempre permitir:

- trocar a chave do ValueSet;
- trocar a materia-prima;
- editar localmente;
- preservar o snapshot dos valores usados.

Automatico por defeito, manual quando preciso.

## Alteracoes futuras em def_pecas

Para suportar esta ligacao, a definicao de peca devera vir a ter campos conceptuais:

| Campo conceptual | Funcao |
| --- | --- |
| `chave_valueset_material` | Chave do material por defeito. |
| `chave_valueset_ferragem` | Chave da ferragem por defeito, quando aplicavel. |
| `permite_acabamento` | Indica se a peca aceita acabamento. |
| `chave_valueset_acabamento_sup` | Chave do acabamento da face superior. |
| `chave_valueset_acabamento_inf` | Chave do acabamento da face inferior. |

## Alteracoes futuras em def_peca_componentes

Os componentes deverao vir a ter campos conceptuais:

| Campo conceptual | Funcao |
| --- | --- |
| `chave_valueset_componente` | Chave do ValueSet do componente (material ou ferragem). |
| `origem_material_default` | Origem por defeito do material do componente. |

## Fora do ambito deste documento

Este documento nao implementa:

- codigo Python;
- models SQLAlchemy;
- migrations Alembic;
- alteracoes de UI;
- motor de resolucao de ValueSets;
- geracao automatica de linhas.

## Decisoes pendentes

Antes de implementar a ligacao, devem ficar respondidas as seguintes perguntas:

- quais os nomes finais dos campos de chave?
- a chave fica na peca ou no grupo da peca?
- como tratar pecas sem chave definida?
- como tratar ferragens que ainda nao tem tabela propria?
- como mapear os dados antigos do V2 para as chaves novas?
- como escolher o fallback quando nao existir ValueSet (nem no item nem no orcamento)?
- o utilizador pode trocar a chave diretamente na grelha do custeio?

## Proxima fase sugerida

**Fase 7P** - adicionar a chave ValueSet as definicoes de pecas, ainda sem aplicar no custeio.

Esta fase seguinte deve focar-se em acrescentar os campos de chave a `def_pecas` (model + migration), preparando a ligacao, sem ainda implementar a resolucao automatica no custeio descrita neste documento.
