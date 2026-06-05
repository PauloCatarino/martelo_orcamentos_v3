# Fase 6 - Modelo de orlas nas definicoes de pecas

## Objetivo

Este documento define o modelo tecnico previsto para configurar orlas nas definicoes de pecas do Martelo Orcamentos V3, antes de alterar models, migrations, interface ou logica de custeio.

A configuracao de orlas sera usada futuramente para:

- calcular metros lineares de orla;
- calcular custo de orla;
- identificar visualmente a configuracao tecnica da peca;
- apoiar listagens de custeio e leitura rapida de pecas.

Esta fase e apenas documentacao tecnica. Nao devem ser criados campos, migrations, UI ou calculos neste momento.

## Regras das orlas

Cada lado da peca pode ter um de tres valores:

| Valor | Significado | Referencia funcional |
| --- | --- | --- |
| `0` | Sem orla | Nao aplica fita de orla. |
| `1` | Orla fina | ORL 0.4. |
| `2` | Orla grossa | ORL 1.0. |

Estes valores devem ser tratados como codigos tecnicos. A descricao amigavel deve ser apresentada pela UI quando necessario.

## Lados da peca

A configuracao de orlas tem quatro posicoes:

- `C1`: comprimento lado 1;
- `C2`: comprimento lado 2;
- `L1`: largura lado 1;
- `L2`: largura lado 2.

A representacao visual segue a ordem:

```text
[C1 C2 L1 L2]
```

Exemplos:

| Codigo visual | Interpretacao |
| --- | --- |
| `[0000]` | Sem orla em todos os lados. |
| `[2000]` | Orla grossa apenas em C1. |
| `[2200]` | Orla grossa em C1 e C2. |
| `[2222]` | Orla grossa em todos os lados. |
| `[2101]` | Orla grossa em C1, orla fina em C2, sem orla em L1, orla fina em L2. |

## Decisao tecnica proposta

A configuracao deve ser guardada em `def_pecas` com quatro campos separados:

- `orla_c1`;
- `orla_c2`;
- `orla_l1`;
- `orla_l2`.

Cada campo deve guardar um inteiro:

- `0`;
- `1`;
- `2`.

A string visual, como `[2200]`, nao deve ser guardada como campo principal. Deve ser uma representacao calculada a partir dos quatro campos.

Esta separacao torna o modelo mais simples para:

- validar cada lado individualmente;
- calcular metros lineares por lado;
- permitir filtros e regras futuras;
- evitar inconsistencias entre campos individuais e string visual.

## Representacao visual calculada

A UI e as listagens podem apresentar um codigo de orlas calculado:

```text
[orla_c1 orla_c2 orla_l1 orla_l2]
```

Exemplo:

```text
orla_c1 = 2
orla_c2 = 2
orla_l1 = 0
orla_l2 = 0

Codigo visual = [2200]
```

Esta representacao deve ser apenas derivada. Se no futuro for criado um helper, ele deve receber os quatro valores e devolver a string no formato `[0000]`.

## Interface futura

Na interface de definicao de peca, a configuracao de orlas deve ser feita com quatro combo boxes:

- Comprimento C1;
- Comprimento C2;
- Largura L1;
- Largura L2.

Cada combo deve ter as opcoes:

- Sem orla;
- Orla fina;
- Orla grossa.

A interface deve mostrar um preview calculado:

```text
Codigo de orlas: [2200]
```

O preview deve atualizar quando o utilizador alterar qualquer lado.

## Impacto no custeio futuro

No custeio, a lista de pecas deve mostrar o nome da peca acompanhado do codigo de orlas.

Exemplos:

```text
LATERAL [2000]
TAMPO [2200]
PORTA [2222]
```

Isto permite identificar rapidamente a configuracao de cada peca sem abrir detalhe tecnico.

No futuro, o calculo de metros lineares de orla deve usar:

- comprimento da peca;
- largura da peca;
- valor configurado em cada lado;
- tipo de orla fina ou grossa;
- custo unitario da orla;
- regras de arredondamento, desperdicio ou producao, se existirem.

## Pecas compostas e leitura visual

As pecas compostas devem continuar a ser facilmente identificadas nas listagens e no custeio.

Uma peca composta pode apresentar a peca principal com o seu codigo de orlas e os componentes associados.

Exemplos futuros:

```text
FUNDO [2000] + PES
PORTA [2222] + DOBRADICA + PUXADOR
PRATELEIRA [2200] + SUPORTES PRATELEIRA
```

Esta representacao ajuda a distinguir:

- a peca principal;
- a configuracao de orlas da peca principal;
- os componentes associados;
- ferragens, acessorios, SPP, operacoes ou mao de obra ligados a peca composta.

## Fora do ambito deste documento

Este documento nao implementa:

- alteracoes em `def_pecas`;
- models SQLAlchemy;
- migrations Alembic;
- UI de edicao de orlas;
- helper de formatacao;
- calculo de metros lineares;
- custo de orla;
- regras de producao;
- seeds com orlas.

## Decisoes pendentes antes do codigo

Antes de implementar orlas, devem ficar respondidas as seguintes perguntas:

- os campos `orla_c1`, `orla_c2`, `orla_l1`, `orla_l2` devem ter default `0`?
- deve existir constraint para limitar os valores a `0`, `1` e `2`?
- a validacao principal deve ficar no model, service, helper ou UI?
- como calcular metros lineares quando a peca nao tiver medidas definidas?
- orla fina e grossa devem apontar para materiais/custos configuraveis?
- como tratar pecas compostas quando componentes tambem tiverem orlas?
- deve existir override local das orlas quando uma definicao de peca e aplicada ao orcamento?
