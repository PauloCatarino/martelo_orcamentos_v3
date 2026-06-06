# Fase 6 - Modelo de operacoes, producao e regras de custeio

## Objetivo

Este documento define a filosofia tecnica e funcional prevista para operacoes de producao, maquinas, mao de obra e regras de custeio associadas a pecas, modulos e items no Martelo Orcamentos V3.

Esta fase e apenas documentacao. Nao cria codigo Python, models SQLAlchemy, migrations Alembic, interface, calculos automaticos ou ligacoes reais ao custeio.

O objetivo e preparar uma estrutura onde o custo final de um item possa resultar de:

- materiais;
- ferragens;
- acessorios;
- SPP;
- operacoes de maquina;
- mao de obra;
- setup;
- acabamento;
- ajustes manuais;
- margem;
- preco final.

## Definicoes de pecas e regras tecnicas

As definicoes de pecas nao servem apenas para identificar pecas como `PORTA`, `LATERAL`, `PRATELEIRA` ou `COSTA`.

No futuro, elas tambem devem guardar regras tecnicas para producao e custeio. Uma definicao de peca pode indicar que operacoes sao normalmente necessarias, como devem ser calculadas e em que condicoes devem ser aplicadas.

Uma peca pode ter regras ou necessidades de:

- corte;
- orlagem;
- CNC / mecanizacoes;
- furacao;
- rasgos;
- colagem;
- montagem;
- embalamento;
- mao de obra;
- tempos de setup;
- circulacao entre maquinas;
- operacoes manuais.

Estas regras nao devem ficar presas ao item do orcamento. Devem nascer da biblioteca tecnica sempre que possivel, mas devem poder ser copiadas, recalculadas e editadas localmente quando a peca entra num orcamento.

## Condicoes que influenciam operacoes

As regras de producao podem depender de varios fatores:

- tipo da peca;
- grupo da peca;
- dimensoes `Comp`, `Larg` e `Esp`;
- quantidade;
- orlas;
- material usado;
- acabamento;
- se a peca pertence a modulo;
- se a peca e solta;
- se a peca e componente de peca composta.

Exemplo: uma `PORTA` pode precisar de corte, orlagem e furacao para dobradicas. Uma `COSTA` pode precisar de corte mas nao de orla. Uma `PRATELEIRA` pode precisar de orlagem apenas em `C1` e `C2`, dependendo da configuracao da peca.

## Pecas simples e pecas compostas

Pecas simples e compostas podem trazer regras proprias.

Exemplos:

| Definicao | Regras possiveis |
| --- | --- |
| `PORTA` | Corte, orlagem, CNC/furacao de dobradicas, montagem de dobradicas. |
| `PRATELEIRA` | Corte, orlagem em certos lados, furacao de suportes se aplicavel. |
| `COSTA` | Corte, normalmente sem orla. |
| `GAVETA` composta | Expande varias pecas, ferragens e operacoes associadas. |

Uma peca composta nao e uma operacao em si. Ela expande componentes que podem ser:

- pecas;
- ferragens;
- acessorios;
- SPP;
- operacoes;
- mao de obra.

Cada componente pode gerar custos diferentes. A peca composta serve para organizar a estrutura tecnica, nao para substituir o calculo detalhado de cada componente.

## Origens possiveis das operacoes

As operacoes podem surgir de varias origens:

- regras da definicao da peca;
- regras dos componentes da peca composta;
- regras do modulo de biblioteca;
- alteracoes do modulo inserido no item;
- pecas soltas inseridas no item;
- operacoes soltas adicionadas manualmente ao item.

Esta origem deve ser preservada sempre que possivel. No futuro, uma linha de custeio deve conseguir explicar se nasceu de uma peca, modulo, ferragem, operacao manual ou regra automatica.

## Operacoes soltas

Operacoes soltas sao necessarias porque nem tudo estara previsto nos modulos ou nas definicoes de pecas.

Exemplos:

- colagem de pecas;
- moldagem de pecas;
- rasgos manuais;
- furacoes manuais;
- adaptacao especial;
- montagem especial;
- embalagem especial;
- transporte interno;
- acabamento manual.

Uma operacao solta pode ser adicionada diretamente ao item do orcamento, mesmo que nao exista peca fisica associada. Isto permite representar trabalho real que tem custo, mas que nao deve obrigatoriamente gerar uma peca.

## Combinacao de origens no custo do item

Um item do orcamento pode chegar ao custo por combinacao de:

- modulos pre-feitos;
- pecas soltas;
- pecas compostas;
- ferragens ou acessorios;
- materias-primas;
- operacoes automaticas;
- operacoes manuais adicionadas pelo utilizador.

Esta combinacao e importante porque a realidade de producao nem sempre segue uma estrutura unica. O Martelo V3 deve permitir custear items simples e items complexos sem obrigar todos a passarem pelo mesmo caminho tecnico.

## Tipos de operacao no ciclo de vida

O modelo deve distinguir:

| Tipo | Descricao |
| --- | --- |
| Operacao definida na biblioteca | Operacao reutilizavel, como corte, orlagem, CNC, montagem ou embalagem. |
| Operacao herdada por uma peca | Operacao associada a uma definicao de peca. |
| Operacao gerada automaticamente no custeio | Linha calculada a partir de regras, medidas, quantidades ou materiais. |
| Operacao adicionada manualmente ao item | Operacao solta inserida pelo utilizador. |
| Operacao editada localmente | Operacao gerada ou herdada, mas ajustada no orcamento. |

Operacoes geradas automaticamente devem poder ser revistas e ajustadas localmente. Se o utilizador alterar tempo, preco, descricao ou observacao, a linha deve ficar marcada como editada localmente.

Aviso visual futuro proposto:

```text
[!] Editado localmente
```

A interface pode futuramente substituir `[!]` por um icone visual de aviso, mantendo o texto `Editado localmente`.

## Unidades de calculo

Operacoes podem ter unidades diferentes:

- tempo por peca;
- tempo por lote;
- tempo por metro linear;
- tempo por metro quadrado;
- tempo fixo;
- custo fixo;
- custo por quantidade;
- custo por setup.

A unidade de calculo deve ser parte da definicao da operacao ou da regra associada. Isto evita tratar todas as operacoes como tempo por peca quando, por exemplo, a orlagem pode depender de metros lineares e o setup pode ser fixo por lote.

## Exemplos

### Exemplo 1 - Peca PORTA

Peca: `PORTA`

| Operacao | Regra possivel |
| --- | --- |
| Corte | Por peca. |
| Orlagem | Por lados com orla. |
| CNC | Furacao de dobradicas. |
| Montagem | Colocar dobradicas. |

Neste caso, as ferragens associadas podem influenciar as operacoes. Se a porta tiver dobradicas, pode gerar furacao de dobradicas e eventual montagem.

### Exemplo 2 - Peca PRATELEIRA

Peca: `PRATELEIRA`

| Operacao | Regra possivel |
| --- | --- |
| Corte | Por peca. |
| Orlagem | C1/C2, se aplicavel. |
| Furacao | Suportes de prateleira, se aplicavel. |

A orlagem depende dos lados configurados na definicao da peca ou no override local da peca aplicada ao orcamento.

### Exemplo 3 - Operacao solta no item

Operacao solta:

- colagem especial;
- tempo manual 30 minutos;
- custo manual definido localmente.

Esta operacao pode nao ter origem numa peca ou modulo. Mesmo assim, deve entrar no custo do item e ficar auditavel.

## Relacao com maquinas

Uma operacao pode estar ligada a uma maquina.

Uma maquina pode ter:

- custo/hora;
- tempo de setup;
- tempo de execucao;
- tempo minimo;
- custo minimo;
- disponibilidade futura;
- observacoes tecnicas.

Exemplo: uma operacao de CNC pode apontar para uma maquina CNC especifica, com custo/hora proprio e tempo minimo de execucao. Uma operacao de corte pode apontar para uma serra ou centro de corte. Uma operacao manual pode nao ter maquina, mas pode ter custo/hora de mao de obra.

## Fluxo de producao

O fluxo de producao pode incluir:

- corte;
- orlagem;
- CNC;
- lixagem/acabamento;
- montagem;
- embalagem;
- expedicao.

Nem todos os items passam por todas as fases. Um item com apenas ferragem solta pode nao passar por corte. Uma peca sem orla nao deve gerar operacao de orlagem. Um item especial pode ter montagem ou acabamento manual adicional.

## Custos futuros a calcular

O Martelo V3 deve permitir futuramente calcular:

- custo de materiais;
- custo de ferragens;
- custo de acessorios;
- custo de SPP;
- custo de operacoes/maquinas;
- custo de mao de obra;
- custo de setup;
- custo de acabamento;
- margem;
- preco final.

O calculo deve ser auditavel. O utilizador deve conseguir perceber de onde veio cada custo e se foi calculado automaticamente ou editado localmente.

## Entidades futuras propostas

As entidades abaixo sao apenas conceptuais nesta fase.

| Entidade conceptual | Funcao prevista |
| --- | --- |
| `def_operacoes` | Catalogo de operacoes reutilizaveis. |
| `def_maquinas` | Catalogo de maquinas ou centros de trabalho. |
| `def_peca_operacoes` | Regras de operacoes associadas a definicoes de pecas. |
| `def_modulo_operacoes` | Operacoes associadas a modelos de modulos. |
| `orcamento_item_operacoes` | Operacoes adicionadas ou herdadas dentro de um item do orcamento. |
| `custeio_linhas_operacao` | Linhas finais de custeio de operacoes. |
| `custeio_linhas_producao` | Linhas finais de producao, setup, mao de obra ou processo. |

## Campos conceptuais para def_operacoes

Campos previstos para uma futura entidade `def_operacoes`:

- `codigo`;
- `nome`;
- `descricao`;
- `tipo_operacao`;
- `unidade_calculo`;
- `custo_hora`;
- `tempo_base`;
- `tempo_setup`;
- `custo_minimo`;
- `maquina_id`;
- `ativo`.

Estes campos devem permitir configurar operacoes simples e operacoes ligadas a maquinas.

## Campos conceptuais para operacao no custeio

Campos previstos para uma operacao aplicada ao custeio:

- `origem`;
- `codigo_operacao`;
- `descricao`;
- `tempo_calculado`;
- `tempo_local`;
- `custo_calculado`;
- `custo_local`;
- `override_manual`;
- `observacoes`.

`tempo_calculado` e `custo_calculado` representam o valor vindo das regras. `tempo_local` e `custo_local` representam alteracoes feitas no orcamento. `override_manual` indica que a linha foi editada localmente.

## Orlagem como tratamento especial

A orlagem merece tratamento especial porque depende de:

- orlas definidas na peca;
- dimensoes da peca;
- tipo de orla;
- materia-prima da orla;
- regras de arredondamento;
- possivel desperdicio;
- tempo de maquina ou operacao.

A orlagem pode gerar dois tipos de custo:

- custo de material de orla;
- custo de operacao de orlagem.

Por isso, a configuracao de orlas em `def_pecas` deve futuramente alimentar tanto o calculo de material como o calculo de operacao.

## CNC e mecanizacoes como tratamento especial

CNC e mecanizacoes tambem merecem tratamento especial porque podem depender de:

- tipo de peca;
- ferragens associadas;
- medidas;
- lado da peca;
- regras do modulo;
- overrides locais.

Exemplos:

- dobradicas podem gerar furacoes na porta;
- corredicas podem gerar furacoes laterais;
- puxadores podem gerar furacao de frente;
- rasgos podem depender da largura ou do comprimento da peca;
- uma ferragem especial pode adicionar uma operacao CNC especifica.

As mecanizacoes devem ser suficientemente detalhadas para custeio, mas sem tornar a interface demasiado pesada para o utilizador.

## Preservacao historica e overrides

Operacoes em orcamentos antigos devem ser preservadas. Se uma regra de operacao for alterada na biblioteca, isso nao deve mudar automaticamente orcamentos ja criados.

Regras principais:

- operacoes geradas no orcamento devem guardar dados suficientes para auditoria;
- alteracoes locais devem ficar marcadas;
- recalculos devem ser feitos apenas por acao explicita ou regra clara;
- operacoes manuais devem manter a origem manual;
- operacoes herdadas devem manter referencia a origem, quando possivel.

## Fora do ambito deste documento

Este documento nao implementa:

- codigo Python;
- models SQLAlchemy;
- migrations Alembic;
- interface;
- catalogo real de operacoes;
- catalogo real de maquinas;
- regras reais de corte, orlagem ou CNC;
- motor de custeio;
- ligacao real a items, pecas ou modulos.

## Decisoes pendentes

Antes de criar codigo para operacoes e producao, devem ficar respondidas as seguintes perguntas:

- como definir regras de corte?
- como definir regras de orlagem?
- como definir regras de CNC?
- como associar operacoes a pecas?
- como associar operacoes a modulos?
- como permitir operacoes manuais?
- como calcular setup?
- como calcular movimentacao entre maquinas?
- como preservar operacoes em orcamentos antigos?
- como permitir overrides locais?
- como apresentar tudo de forma simples ao utilizador?
- como distinguir operacao de maquina, mao de obra e custo manual?
- como tratar custo minimo e tempo minimo?

## Proxima fase sugerida

Fase 7A - desenhar modelo inicial de operacoes e maquinas, ainda sem calculo automatico completo.
