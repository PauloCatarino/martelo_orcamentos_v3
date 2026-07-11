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

Validação do utilizador: falhou no primeiro teste. O utilizador confirmou que,
apesar de escolher materiais/ferragens diferentes, os módulos eram sempre
gravados e importados com prioridade 1. Foi identificado que o custeio não
guardava a prioridade aplicada e que o snapshot original do associado tinha
precedência sobre a escolha atual em `Mat. default`.

Commit: `Preservar prioridade ValueSet nos modulos`.

Próximo passo recomendado: depois desta validação, modelar fórmulas dimensionais
predefinidas nas `def_pecas` e a herança explícita de dimensões do cabeçalho de
peça/conjunto para os seus filhos.

### Correção da prioridade explícita no custeio

Implementação concluída e a aguardar nova validação local:

- acrescentada `valueset_prioridade` às linhas do custeio;
- criada a coluna visível **Prioridade** junto de Chave ValueSet/Mat. default;
- a lista `Mat. default` mostra também a prioridade de cada opção;
- selecionar uma opção ValueSet grava material e prioridade na mesma operação;
- materiais escolhidos diretamente fora do ValueSet ficam com prioridade vazia;
- ao guardar um módulo, a precedência é agora:
  1. prioridade explícita da linha do custeio;
  2. prioridade correspondente ao `Mat. default` atual;
  3. prioridade histórica do associado, apenas como compatibilidade;
- uma escolha manual de prioridade 2 já não é substituída pelo snapshot de
  prioridade 1 com que o associado foi originalmente criado;
- migração aplicada: `20260718_57`.

Testes automáticos:

- escolha no dropdown grava `valueset_prioridade=2`;
- linha antiga com associado/prioridade 1 e `Mat. default` de prioridade 2
  grava o módulo com prioridade 2;
- testes focados: `298 passed`;
- bateria completa: `1912 passed`.

Validação local pedida:

1. reiniciar a aplicação e confirmar a coluna **Prioridade** no custeio;
2. escolher uma opção de prioridade 2 em `Mat. default`;
3. confirmar que a coluna muda imediatamente para 2 depois da atualização;
4. substituir o módulo a partir dessas linhas;
5. confirmar prioridade 2 em **Biblioteca de Módulos → Ver linhas**;
6. importar noutro item e confirmar prioridade/material 2;
7. testar uma prioridade inexistente e confirmar material vazio mais aviso.

Validação do utilizador: concluída. O utilizador confirmou que a prioridade
passou a ser gravada no custeio, preservada no módulo e aplicada corretamente
na importação.

Commit: `b0d3cbc Corrigir prioridade explicita no custeio`.

### Simplificação visual do material predefinido

Implementação concluída e a aguardar validação local:

- o dropdown `Mat. default` deixou de repetir código interno da opção,
  prioridade e referência LE;
- o texto visível passa a usar apenas `chave · descrição útil · preço líquido`;
- exemplo: `MATERIAL_COSTAS · AGL MLM LINHO CANCUN 12G 10MM · preço líquido
  12,35 €`;
- quando não existe descrição, é usado o código/nome da opção como fallback;
- a coluna **Prioridade** continua existente e persistida, mas passa a estar
  oculta por predefinição para novos estados de visualização;
- **Chave ValueSet**, código e descrição técnica continuam igualmente
  disponíveis no menu de colunas;
- ocultar colunas altera apenas a apresentação, nunca os dados ou a lógica dos
  módulos.

Testes automáticos:

- testes focados de interface/colunas: `64 passed`;
- bateria completa: `1913 passed`.

Validação local pedida:

1. reiniciar a aplicação e abrir o custeio;
2. confirmar o novo texto conciso em `Mat. default`;
3. confirmar a presença do preço líquido;
4. clicar com o botão direito no cabeçalho e usar **Repor padrão** se a coluna
   Prioridade continuar visível devido a uma preferência anteriormente guardada;
5. confirmar que Prioridade pode voltar a ser mostrada pelo mesmo menu;
6. alterar `Mat. default` e confirmar que prioridade/módulo continuam corretos.

Validação do utilizador: concluída. O utilizador confirmou que a apresentação
ficou mais clara e compacta, mantendo materiais e prioridades corretos.

Commit: `f552730 Simplificar material predefinido no custeio`.

### Abreviatura final do preço no material predefinido

- substituído o texto `preço líquido` por `Pliq` no dropdown `Mat. default`;
- formato final: `chave · descrição útil · Pliq valor`;
- alteração exclusivamente visual, sem impacto nos dados, prioridades ou
  cálculos.

Validação do utilizador: concluída (11 de julho de 2026).

Próximo passo: iniciar numa nova tarefa a fase de fórmulas dimensionais
predefinidas nas `def_pecas` e dimensões no cabeçalho de peça/conjunto, com
regras explícitas para preencher automaticamente os filhos de portas, gavetas
e outros conjuntos.

### Fórmulas dimensionais predefinidas — Fase A: modelo e configuração

Implementação concluída e a aguardar validação local do utilizador:

- acrescentadas às `def_pecas` as fórmulas opcionais `formula_comp`,
  `formula_larg` e `formula_esp`, destinadas às dimensões predefinidas do
  cabeçalho de peça/conjunto;
- acrescentadas às associações `DefPecaComponente` as transformações opcionais
  `formula_comp`, `formula_larg` e `formula_esp` de pai para filho;
- mantidas separadas as variáveis globais `H/L/P`, as variáveis da divisão
  ativa `HM/LM/PM` e as novas variáveis explícitas do pai imediato
  `PAI_COMP/PAI_LARG/PAI_ESP`;
- fórmulas de cabeçalho aceitam apenas `H/L/P` e `HM/LM/PM`; transformações de
  associados aceitam também `PAI_COMP/PAI_LARG/PAI_ESP`;
- validação usa a mesma gramática segura de medidas: números, variáveis
  permitidas, `+`, `-`, `*`, `/` e parênteses, sem `eval`;
- o separador **Regras** da definição de peça deixou de ser um placeholder e
  permite guardar as três fórmulas do cabeçalho, consultar as transformações
  dos associados e abrir a edição do associado por duplo clique;
- a duplicação/**Gravar como** preserva as fórmulas da peça e as transformações
  dos associados;
- editar os dados gerais de uma peça preserva as fórmulas geridas no separador
  **Regras**;
- migração criada: `20260719_58`;
- nenhum registo do catálogo foi preenchido automaticamente;
- nesta Fase A as fórmulas são apenas configuradas e persistidas: ainda não são
  aplicadas às linhas do custeio, aos módulos ou à atualização da biblioteca.

Testes automáticos:

- testes focados de modelos, repositórios, serviços, validação e interface:
  `90 passed`;
- bateria completa: `1921 passed`.

Validação local pedida:

1. reiniciar a aplicação para aplicar a migração `20260719_58`;
2. abrir uma peça/conjunto de teste e entrar no separador **Regras**;
3. guardar no cabeçalho, por exemplo, Comp `HM`, Larg `LM/2` e Esp vazio;
4. sair e voltar a abrir a definição, confirmando que as fórmulas persistem;
5. no mesmo separador, fazer duplo clique num associado e guardar, por exemplo,
   Comp `PAI_COMP-4`, Larg `PAI_LARG-4` e Esp `19`;
6. confirmar que as transformações aparecem na tabela do separador **Regras**;
7. tentar guardar `PAI_COMP` numa fórmula do cabeçalho e confirmar a rejeição;
8. tentar guardar uma variável desconhecida num associado e confirmar a
   rejeição;
9. editar apenas os **Dados Gerais** da peça e confirmar que as fórmulas não são
   apagadas;
10. confirmar que nenhuma linha de custeio existente ou nova mudou ainda as
    dimensões automaticamente nesta fase.

Validação do utilizador: concluída. No primeiro arranque, `def_pecas` ficou vazio
porque a base ainda estava em `20260718_57`; confirmou-se que reiniciar a
aplicação não executa migrações automaticamente. Depois de aplicar manualmente
`alembic upgrade head`, a base passou para `20260719_58`, as 63 peças voltaram a
ser apresentadas e o utilizador guardou fórmulas dimensionais no piloto de
porta.

Commit: `Configurar formulas dimensionais nas definicoes`.

Próximo passo recomendado: depois da validação local desta configuração,
implementar a Fase B, aplicando as fórmulas aos cabeçalhos e as transformações
`PAI_*` aos filhos no custeio, incluindo conjuntos aninhados e preservação das
edições locais.

### Fórmulas dimensionais predefinidas — Fase B: aplicação no custeio

Implementação concluída e a aguardar validação local do utilizador:

- novas peças simples recebem `formula_comp`, `formula_larg` e `formula_esp` da
  respetiva `DefPeca` como fórmulas editáveis da linha de custeio;
- novos cabeçalhos de peça/conjunto recebem as fórmulas dimensionais
  configuradas na `DefPeca` quando existirem;
- cada filho recebe, com precedência, as fórmulas configuradas na associação
  `DefPecaComponente`, preservando-as como texto editável na linha;
- filhos podem continuar a usar diretamente `H/L/P` ou `HM/LM/PM`, como no
  piloto `PORTA_SIMPLES+DOBRADICA`, onde o filho `PORTA_SIMPLES` foi configurado
  com Comp `HM` e Larg `LM`;
- `PAI_COMP`, `PAI_LARG` e `PAI_ESP` resolvem sempre as dimensões reais do pai
  imediato, permitindo transformações explícitas e conjuntos aninhados;
- o recálculo segue a ordem estrutural, calculando primeiro o pai e depois os
  filhos, sem reutilizar dimensões de um irmão ou de outro conjunto;
- a validação anterior ao custeio passou também a validar cabeçalhos compostos
  dimensionados e fórmulas `PAI_*`;
- se a fórmula de espessura da peça estiver vazia, mantém-se o comportamento
  anterior de obter Esp a partir do material ValueSet; uma fórmula explícita de
  Esp tem precedência;
- as fórmulas ficam congeladas nas linhas criadas: alterações posteriores no
  catálogo não se propagam automaticamente;
- **Atualizar peça da biblioteca** preserva as dimensões/fórmulas editadas da
  raiz e reconstrói os filhos com as transformações atuais do catálogo, mantendo
  a confirmação já existente para perda de edições locais;
- cabeçalhos importados de módulos mantêm nesta fase o comportamento anterior,
  sem dimensões automáticas; a persistência/importação dessas fórmulas fica
  reservada para a Fase C;
- nenhuma peça do catálogo nem linha de orçamento existente foi alterada
  automaticamente.

Testes automáticos:

- testes focados de custeio, interface e medidas: `279 passed`;
- bateria completa: `1925 passed`;
- cenários novos cobrem inserção do piloto com `HM/LM`, cabeçalho
  `HM × LM/2`, transformação `PAI_COMP-4 × PAI_LARG-4`, espessura explícita,
  conjuntos aninhados e reconstrução através de **Atualizar peça da biblioteca**.

Validação local pedida:

1. criar ou abrir um item de teste com uma divisão independente e dimensões
   conhecidas, por exemplo HM `2000` e LM `600`;
2. inserir novamente da biblioteca `PORTA_SIMPLES+DOBRADICA` — não reutilizar
   uma linha inserida antes desta fase;
3. confirmar que o cabeçalho do conjunto aparece e que o filho
   `PORTA_SIMPLES` recebe automaticamente Comp `HM` e Larg `LM`;
4. executar **Atualizar** no custeio e confirmar Comp real `2000` e Larg real
   `600` no filho;
5. confirmar que a dobradiça continua associada e que a sua quantidade/regra
   não foi alterada por esta fase;
6. editar manualmente no filho Comp para `HM-4`, executar **Atualizar** e
   confirmar Comp real `1996`;
7. alterar no catálogo a transformação do filho apenas numa peça de teste para
   `PAI_COMP-4`/`PAI_LARG-4`, inserir um novo conjunto cujo cabeçalho tenha
   dimensões e confirmar a derivação a partir do pai;
8. confirmar que a primeira linha já inserida não muda com a alteração do
   catálogo;
9. usar **Atualizar peça da biblioteca** nessa primeira linha apenas se quiser
   testar a reconstrução explícita dos filhos e confirmar previamente qualquer
   aviso de perda de edições locais;
10. confirmar que módulos existentes continuam a importar como antes.

Validação do utilizador: concluída. O utilizador confirmou que o piloto de
porta aplicou corretamente as fórmulas dimensionais no custeio.

Commit: `Aplicar formulas dimensionais no custeio`.

Próximo passo recomendado: depois da validação local do piloto de porta,
implementar a Fase C para guardar/importar fórmulas de cabeçalhos nos módulos;
só depois generalizar as transformações a gavetas e ao restante catálogo.

### Proteção de peças paramétricas sem divisão independente

Implementação concluída e a aguardar validação local do utilizador:

- identificado o cenário de uma tabela de custeio vazia onde foi inserida uma
  peça previamente configurada com `HM/LM` sem existir uma divisão independente;
- a expressão não tinha contexto local e era corretamente rejeitada, mas o
  tratamento do erro chamava `carregar()` dentro do sinal `cellChanged`;
- a recarga voltava a emitir o mesmo sinal para a expressão inválida, criando
  um ciclo recursivo de `ValueError` que impedia voltar a abrir o item;
- a recuperação de uma edição inválida passa agora a restaurar apenas a linha
  afetada sob a proteção de sinais da tabela, sem executar uma recarga completa
  dentro de `cellChanged`;
- antes de criar qualquer linha, a inserção da biblioteca percorre a peça, os
  seus associados e conjuntos aninhados à procura de `HM`, `LM` ou `PM`;
- se essas variáveis forem usadas e ainda não existir uma divisão independente
  no custeio, toda a inserção é recusada atomicamente e nenhuma linha parcial é
  gravada;
- a interface apresenta o aviso: começar por inserir uma **Divisão
  independente** e adicionar a peça logo abaixo;
- peças que usam apenas dimensões globais `H/L/P` continuam permitidas sem
  divisão independente;
- peças `HM/LM/PM` continuam permitidas quando já existe uma divisão;
- inspeção somente de leitura encontrou uma única ocorrência preexistente:
  item `10`, linha `668`, peça `COSTA_SEM_CNC_0000`, com `HM × LM × 10` antes de
  qualquer divisão;
- essa linha não foi apagada nem alterada automaticamente; deve ser removida
  pelo utilizador depois de reabrir o item, inserindo em seguida primeiro a
  divisão independente e só depois a peça.

Testes automáticos:

- testes focados de serviço e interface: `267 passed`;
- bateria completa: `1930 passed`;
- cenários cobrem bloqueio atómico sem divisão, permissão com divisão,
  permissão de `H/L`, aviso visível e ausência de `carregar()` recursivo no
  tratamento de erro da célula.

Validação local pedida:

1. reiniciar a aplicação e abrir o item afetado;
2. confirmar que o item abre sem ciclo de erros;
3. eliminar a linha `COSTA_SEM_CNC_0000` inválida;
4. com a tabela vazia, tentar inserir novamente a mesma Costa e confirmar que
   aparece o aviso de divisão independente e que nenhuma linha é criada;
5. inserir uma **Divisão independente** e preencher as dimensões necessárias;
6. inserir a Costa logo abaixo e confirmar que `HM/LM` são aceites;
7. executar **Atualizar** e confirmar as dimensões reais;
8. confirmar que uma peça configurada apenas com `H/L` pode ser inserida sem
   divisão independente.

Validação do utilizador: concluída (11 de julho de 2026). O utilizador
confirmou a correção do item afetado e o aviso de divisão independente.

Commit: `Proteger pecas parametricas sem divisao`.

Próximo passo recomendado: validar esta recuperação antes de retomar a Fase C
dos módulos.

## Próxima fase em curso

### Fórmulas dimensionais predefinidas — Fase C: módulos (plano detalhado)

Decisão do utilizador (11 de julho de 2026): a Fase C é a próxima etapa; a
generalização das uniões estruturais fica para depois.

Objetivo: guardar e importar as fórmulas dimensionais dos cabeçalhos de
peça/conjunto nos módulos, para que um módulo importado resolva as dimensões
dos cabeçalhos e as transformações `PAI_*` dos filhos sem intervenção manual.

Estado atual constatado no código:

- ao gravar um módulo, `_linha_modulo_de_custeio` descarta deliberadamente
  `comp/larg/esp` dos cabeçalhos compostos (`def_modulo_service.py`);
- na importação, `_criar_cabecalho_composta_modulo` força `comp/larg/esp` a
  vazio (comentário explícito a adiar para a Fase C);
- os filhos já guardam e reaplicam as fórmulas como texto, incluindo `PAI_*`,
  mas sem dimensões no cabeçalho as `PAI_*` não têm valores para resolver;
- a proteção de peças `HM/LM/PM` sem divisão independente existe apenas em
  `adicionar_pecas_da_biblioteca`, não em `inserir_modulo_no_item`;
- as colunas `comp/larg/esp` de `def_modulo_linhas` já são texto livre, pelo
  que não é necessária nenhuma migração de esquema.

Passos previstos:

1. **C1 — Gravar**: o cabeçalho composto passa a persistir as suas fórmulas
   `comp/larg/esp` (texto editável da linha de custeio) ao guardar/substituir
   um módulo. Divisões e filhos mantêm o comportamento atual.
2. **C2 — Importar**: se a linha de cabeçalho do módulo tiver fórmulas,
   aplicá-las ao cabeçalho criado (com e sem `def_peca` resolvida); módulos
   antigos, com os três campos vazios, mantêm exatamente o comportamento
   anterior (sem dimensões automáticas), o mesmo padrão de compatibilidade
   usado na prioridade ValueSet.
3. **C3 — Recalcular e proteger**: garantir que **Atualizar** resolve primeiro
   o cabeçalho importado e depois as `PAI_*` dos filhos; alargar a proteção de
   divisão independente à importação de módulos, com recusa atómica quando o
   módulo usa `HM/LM/PM` e não inclui nem encontra uma divisão no item.
4. **C4 — Interface**: confirmar que **Biblioteca de Módulos → Ver linhas** e o
   preview de importação apresentam as fórmulas do cabeçalho.
5. **C5 — Testes e registo**: testes focados (gravar preserva fórmulas do
   cabeçalho; importar aplica-as; módulo antigo mantém comportamento; `PAI_*`
   resolve após importação e Atualizar; proteção de divisão na importação),
   bateria completa e atualização deste documento.

Critérios de conclusão:

- um módulo com conjunto dimensionado (por exemplo, cabeçalho `HM × LM/2` e
  filho `PAI_COMP-4 × PAI_LARG-4`) importa e resolve dimensões reais corretas
  só com **Atualizar**;
- módulos gravados antes da Fase C importam sem alteração de resultados;
- nenhuma linha existente de orçamento é alterada automaticamente;
- testes automáticos completos e validação local do utilizador.

## Fase seguinte proposta

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
