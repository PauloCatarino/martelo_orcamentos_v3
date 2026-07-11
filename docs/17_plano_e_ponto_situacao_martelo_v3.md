# Martelo V3 — plano e ponto de situação

Última atualização: 11 de julho de 2026

Este documento é a memória permanente da evolução funcional e técnica do
Martelo V3. Deve ser consultado no início de cada nova fase e atualizado no fim
de cada alteração validada pelo utilizador.

## Regras de trabalho

- Desenvolver por fases pequenas e verificáveis.
- No fim de cada alteração, fornecer instruções de teste local.
- Só considerar uma fase validada depois do retorno do utilizador.
- Executar testes focados e a bateria completa antes do commit.
- Criar um commit por marco funcional coerente.
- Não propagar alterações do catálogo para peças já inseridas no orçamento.
- Uma peça do orçamento fica congelada até atualização explícita através de
  **Atualizar peça da biblioteca**.
- As correções automáticas da auditoria exigem descrição, supervisão e
  confirmação do utilizador.

## Decisões funcionais confirmadas

1. Peças inseridas no orçamento ficam congeladas até atualização explícita.
2. Alterações do catálogo não se propagam automaticamente.
3. Regra inicial de uniões por topo: mínimo 2 e intervalos de 128 mm.
4. Aos 100 mm, o resultado é 2.
5. O custo direto CNC é configurado na operação, com máquina associada.
6. O setup é separado e não é multiplicado pelo número de furos/uniões.
7. ValueSet usa ações explícitas por operação: ADICIONAR ou SUBSTITUIR.
8. Módulos guardam referências e desvios, não filhos derivados.
9. Peças compostas são substituídas na interface pelo conceito único de
   peça/conjunto.
10. Conjuntos virtuais continuam identificados internamente.
11. Regras técnicas, incluindo quantidades por topo, são editáveis nas
    Configurações e usadas como valores predefinidos.

## Fases concluídas e validadas

### Proteção de entradas e fórmulas de custeio

- Validação dos campos de dimensões e fórmulas.
- Suporte controlado das variáveis `H`, `HM`, `P` e `PM` combinadas com números.
- Rejeição de letras, expressões e valores que possam comprometer o cálculo.
- Mensagens de validação apresentadas ao utilizador.

### Peças, associados e regras de quantidade

- Associados ligados à biblioteca de peças.
- Quantidade fixa ou calculada por regra.
- Zona de aplicação, dimensão de referência e número de topos.
- Aplicação **Quantidade por topo**.
- Regra `UNIAO_TOPOS_128`, equivalente a
  `MAX(2, CEIL(MEDIDA_TOPO / 128))`.
- Teste validado: medida do topo 600 mm, 5 uniões por topo e 10 para dois
  topos.

### Operações das peças e ValueSets

- Operações de peças associadas entram no custeio.
- Operações específicas de variantes ValueSet suportam ADICIONAR e SUBSTITUIR.
- A utilidade e os efeitos de ADICIONAR/SUBSTITUIR devem voltar a ser explicados
  numa fase futura com casos práticos completos.
- Botão **Atualizar peça da biblioteca** validado localmente.

### Auditoria do Catálogo

- Auditoria apenas de leitura para peças, associados, operações, máquinas,
  regras, ValueSets e módulos.
- Navegação direta para a configuração que origina a ocorrência.
- Correções supervisionadas apenas quando são seguras e explícitas.
- Estado das ações colocado abaixo dos botões e antes dos totais.
- Deteção, entre outros casos, de operações inativas, operações duplicadas,
  códigos de orla incompatíveis, referências desatualizadas, regras sem uso e
  substituições ValueSet.

### Prioridade ValueSet nos associados

- Cada associado pode escolher a prioridade ValueSet pretendida.
- A resolução é exata para prioridades superiores a 1, sem fallback silencioso.
- Se a prioridade não estiver configurada, `Mat. default` fica vazio e é criada
  uma observação de produção.
- Cenários positivos e negativos validados pelo utilizador.

Commit principal: `9896d60 Resolver associados pela prioridade ValueSet`.

### Piloto de uniões nos topos

Configuração piloto validada na peça `PRATELEIRA FIXA 2000`:

- associado `SISTEMAS_UNIAO`, prioridade 1: cavilha `FER0145`, 8 × 35;
- associado `SISTEMAS_UNIAO`, prioridade 2: parafuso `FER0146`, 3,5 × 50;
- ambos usam `UNIAO_TOPOS_128`, dois topos e quantidade por topo;
- para largura 600 mm, cada ferragem recebe quantidade 10;
- cavilha usa a operação/máquina `CNC_ABD`;
- parafuso usa a operação/máquina `CNC_VERTICAL`;
- tempo variável é multiplicado pelas uniões e o setup é aplicado uma vez.

Foi acrescentado ao Resumo de Consumos o quadro
**Operações efetivas por máquina**, apresentando operação, máquina, quantidade,
setup, tempo CNC, outros tempos e custo de produção. O utilizador confirmou que
o resultado aparece organizado e separado.

A Auditoria passou a detetar:

- prioridades repetidas nos associados;
- prioridades repetidas na chave ValueSet de união;
- prioridade de união inválida;
- união sem CNC ativo;
- CNC de união sem tempo unitário positivo.

O teste negativo com duas prioridades iguais a 1 foi validado: a Auditoria
identificou corretamente a ocorrência. Com a configuração correta não aparecem
ocorrências `UNIAO_*`.

Validação automática deste marco: `1904 passed`.

Commit: `f567817 Auditar e detalhar piloto de unioes`.

## Estado atual

- Branch de desenvolvimento: `codex/pecas-associados`.
- O piloto completo de prateleira fixa, cavilha, parafuso, operações CNC,
  relatórios e auditoria está validado.
- A base funcional está preparada para generalizar as uniões a outras peças.
- Não existem alterações de esquema pendentes nesta fase.

### Generalização controlada — proteção contra CNC duplicado

Implementação concluída e a aguardar validação local do utilizador:

- inventário confirmado das famílias estruturais atuais do catálogo;
- no Martelo, a peça horizontal inferior chama-se `Fundo`; não existe uma
  família autónoma `Base`;
- nomes e aplicações diferentes podem derivar da mesma origem estrutural
  horizontal ou vertical, alterando materiais, orlas, uniões e operações;
- a `DIVISORIA_2000` foi configurada pelo utilizador com cavilha de prioridade 1,
  `UNIAO_TOPOS_128`, dois topos e quantidade por topo, sem parafuso;
- o CNC direto da divisória foi desativado pelo utilizador, ficando a maquinação
  da união na origem associada;
- a Auditoria distingue agora CNC diferentes na peça e no associado, que geram
  aviso para confirmação, da mesma operação CNC repetida nas duas origens, que
  gera o erro `CNC_DUPLICADO_PECA_ASSOCIADO`;
- a proteção não remove operações automaticamente, porque duas maquinações
  distintas podem ser fisicamente necessárias.

Testes automáticos:

- testes focados: `231 passed`;
- bateria completa: `1905 passed`;
- tabela de `UNIAO_TOPOS_128` cobre explicitamente 100, 128, 600 e 601 mm;
- auditoria da base atual: 0 ocorrências `CNC_DUPLICADO_PECA_ASSOCIADO` e 0
  ocorrências `UNIAO_*` na configuração atual da divisória.

Validação local pedida:

1. executar a Auditoria do Catálogo com a divisória corretamente configurada;
2. confirmar que não aparece `CNC_DUPLICADO_PECA_ASSOCIADO`;
3. ativar temporariamente na divisória a mesma CNC usada pela cavilha;
4. confirmar que a Auditoria apresenta o novo erro de duplicação;
5. voltar a desativar a CNC direta e confirmar que o erro desaparece.

Validação do utilizador: concluída. O utilizador confirmou na Auditoria do
Catálogo que `CNC_DUPLICADO_PECA_ASSOCIADO` deixou de aparecer com a origem CNC
corretamente configurada.

Commit: `909bd79 Proteger contra CNC duplicado nas unioes`.

Próximo passo recomendado: rever e normalizar as peças estruturais de
`def_pecas` antes de criar um módulo de teste tipo caixote. Esse módulo deverá
incluir, de forma progressiva, teto, fundo, prateleira fixa, prateleira amovível,
laterais ou divisória, costa e porta, herdando materiais e regras do ValueSet do
item onde for inserido.

### Normalização da origem estrutural das peças

Implementação concluída e a aguardar validação local do utilizador:

- analisada a organização de peças do Martelo V2/iMos fornecida pelo
  utilizador;
- confirmado que a origem estrutural deve sobreviver a nomes e aplicações
  diferentes: por exemplo, um teto, tampo de acabamento ou tampo de secretária
  podem partir de uma origem horizontal comum e depois divergir em material,
  orlas, uniões e operações;
- o campo técnico existente `funcao` passou a ser apresentado nos formulários
  como **Origem estrutural**, sem alteração de esquema;
- foram criadas opções controladas para teto, fundo, prateleira fixa,
  prateleira amovível, lateral, divisória, costa, portas, gaveta, remate,
  ferragem, acessório e serviço;
- o campo continua editável, permitindo origens novas sem bloquear casos que
  ainda não existam na lista;
- o grupo passou igualmente a apresentar as famílias mais comuns, mantendo a
  possibilidade de texto livre;
- valores antigos ou personalizados continuam preservados ao editar;
- nenhuma das 63 peças atuais foi alterada automaticamente.

Testes automáticos:

- testes focados: `48 passed`;
- bateria completa: `1909 passed`.

Validação local pedida:

1. abrir uma peça existente em modo de edição;
2. confirmar o campo **Origem estrutural** e a lista de famílias;
3. escolher uma origem e confirmar que o grupo continua independente;
4. testar uma origem escrita manualmente e confirmar que é preservada;
5. cancelar sem guardar numa peça produtiva;
6. criar ou usar uma peça de teste, guardar e reabrir para confirmar a origem.

Validação do utilizador: concluída. O utilizador confirmou o novo campo e
preencheu origem estrutural/orientação em várias peças `def_pecas`.

Commit: `12a5e09 Normalizar origem estrutural das pecas`.

Próximo passo recomendado: depois desta validação, preencher
progressivamente origem e orientação nas peças que entrarão no primeiro
módulo caixote, sem fazer uma migração automática do catálogo completo.

### Piloto de módulo paramétrico — caixote simples

Configuração criada na base de testes e a aguardar validação local do
utilizador:

- confirmado como fluxo principal: preparar linhas e fórmulas no custeio,
  selecionar as linhas, usar **Guardar como Módulo** e gerir nome, categoria,
  âmbito e imagem na Biblioteca de Módulos;
- não foi criado um mecanismo alternativo de módulos;
- criado o módulo global `PILOTO_CAIXOTE_SIMPLES`, separado do módulo antigo
  `1_MOD_2_PORTAS`;
- o piloto guarda apenas referências `def_pecas`, fórmulas, quantidades, chaves
  ValueSet e códigos de orla; não guarda materiais, preços nem dimensões reais;
- linhas: divisão paramétrica, duas laterais, teto, fundo, prateleira fixa,
  prateleira amovível, costa e porta;
- fórmulas iniciais: laterais `HM × PM`; horizontais entre laterais
  `LM-38 × PM`; prateleira amovível `LM-40 × PM-20`; costa `HM × LM`;
  porta `HM-4 × LM-4`;
- espessuras piloto: 19 mm nas peças principais e 10 mm na costa;
- as fórmulas são hipóteses iniciais editáveis e precisam de validação
  dimensional/industrial pelo utilizador;
- a imagem fica por associar na Biblioteca de Módulos.

Validação técnica:

- para `H=2000`, `L=600`, `P=500`, as fórmulas resolvem para laterais
  `2000 × 500`, horizontais `562 × 500`, prateleira amovível `560 × 480`,
  costa `2000 × 600` e porta `1996 × 596`;
- Auditoria do Catálogo: nenhuma ocorrência associada ao novo módulo;
- testes focados de módulos/auditoria: `36 passed`;
- bateria completa: `1909 passed`.

Validação local pedida:

1. abrir um item de teste com dimensões conhecidas;
2. importar `PILOTO_CAIXOTE_SIMPLES`;
3. executar **Atualizar** no custeio;
4. confirmar quantidades, dimensões, materiais ValueSet, orlas e associados;
5. confirmar especialmente se teto/fundo/prateleira ficam entre laterais e se
   as folgas de prateleira amovível e porta são adequadas;
6. verificar que cavilhas/CNC não aparecem duplicados;
7. associar uma imagem apenas depois de validar a estrutura.

Validação do utilizador: concluída com correções. O utilizador confirmou que o
piloto inicial não continha as peças compostas/associados pretendidos, recriou
um novo módulo pelo fluxo normal do custeio e validou gravar/importar com os
dados corrigidos.

Commit de registo: `Registar piloto de modulo caixote simples`.

Próximo passo recomendado: ajustar as fórmulas e as peças do piloto com base
no teste local; depois recriar/substituir o módulo pelo fluxo normal a partir do
custeio, consolidando-o como primeiro módulo produtivo.

### Prioridade ValueSet preservada nos módulos

Implementação concluída e a aguardar validação local do utilizador:

- acrescentada `prioridade_valueset` às linhas guardadas dos módulos;
- ao guardar/substituir um módulo a partir do custeio, a prioridade é obtida da
  opção `Mat. default` selecionada na chave ValueSet do item;
- nos filhos associados é preservado o snapshot
  `associado_valueset_prioridade`;
- o módulo continua sem guardar matéria-prima, referência ou preço concretos;
- ao importar, a prioridade é resolvida exatamente contra o ValueSet do item
  de destino;
- se a prioridade não existir, não existe fallback para outra opção:
  `Mat. default` e material ficam vazios e é criada uma observação/aviso;
- linhas de módulos antigos mantêm prioridade vazia e o comportamento anterior;
  ganham prioridade explícita quando o módulo é substituído a partir de um
  custeio atualizado;
- a Biblioteca de Módulos e o preview de importação mostram a nova coluna
  **Prioridade**;
- migração aplicada: `20260717_56`.

Testes automáticos:

- prioridade 2 é gravada a partir da opção selecionada;
- prioridade 2 é resolvida na importação mesmo existindo prioridade 1;
- prioridade inexistente deixa material vazio e produz aviso, sem fallback;
- testes focados: `44 passed`;
- bateria completa: `1912 passed`.

Validação local pedida:

1. num item de teste, escolher opções com prioridades diferentes para materiais
   e ferragens, por exemplo pés Axilo/prioridade 1 e Boné/prioridade 2;
2. selecionar as linhas e substituir/gravar um módulo;
3. abrir **Biblioteca de Módulos → Ver linhas** e confirmar as prioridades;
4. importar o módulo num item cujo ValueSet contenha essas prioridades;
5. confirmar que `Mat. default` resolve as opções da prioridade guardada;
6. remover temporariamente uma prioridade do ValueSet do item de destino e
   importar novamente;
7. confirmar material vazio e aviso de produção, sem seleção silenciosa de
   outra prioridade.

Validação do utilizador: pendente.

Commit: `Preservar prioridade ValueSet nos modulos`.

Próximo passo recomendado: depois desta validação, modelar fórmulas dimensionais
predefinidas nas `def_pecas` e a herança explícita de dimensões do cabeçalho de
peça/conjunto para os seus filhos.

## Próxima fase proposta

### Generalização das uniões estruturais

Objetivo: aplicar a lógica validada do piloto a laterais, bases, tampos,
divisórias e outras peças horizontais, mantendo uma única lógica de cálculo.

Passos previstos:

1. Inventariar as peças estruturais atuais e identificar relações topo/lateral.
2. Definir quando uma peça recebe cavilha, parafuso ou ambos, evitando assumir
   que todas as peças horizontais usam automaticamente as mesmas ferragens.
3. Reutilizar regras configuráveis por topo e prioridades ValueSet.
4. Garantir que cada união pertence a uma única origem para evitar duplicação
   entre peça principal e associado.
5. Mostrar alertas no custeio quando uma união obrigatória fica sem ferragem,
   prioridade, operação ou máquina.
6. Acrescentar auditorias de duplicação e configuração incompleta específicas
   das novas peças estruturais.
7. Testar primeiro um módulo simples e só depois generalizar ao catálogo.

## Critérios para concluir a próxima fase

- Quantidades corretas por topo para várias dimensões.
- Cavilhas e parafusos resolvidos pelas prioridades corretas.
- Nenhuma duplicação de ferragens ou CNC.
- Setup aplicado uma vez por operação configurada.
- Materiais, operações e máquinas separados no custeio e nos relatórios.
- Alertas claros para configurações incompletas.
- Auditoria sem novas ocorrências estruturais depois da configuração correta.
- Testes automáticos completos e validação local do utilizador.

## Registo obrigatório nas próximas fases

Ao terminar cada fase, atualizar neste ficheiro:

- alterações implementadas;
- decisões tomadas;
- testes automáticos e resultado;
- testes locais pedidos ao utilizador;
- validação recebida;
- commit criado;
- próximo passo recomendado.
