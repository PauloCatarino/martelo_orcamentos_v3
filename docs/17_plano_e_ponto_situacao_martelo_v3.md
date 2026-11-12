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

### Fase C — C1 (gravar) e C2 (importar): implementados

Implementação concluída e a aguardar validação local do utilizador:

- ao guardar/substituir um módulo a partir do custeio, o cabeçalho de
  peça/conjunto passa a persistir as suas fórmulas `comp/larg/esp` como texto,
  tal como já acontecia com os filhos (`def_modulo_service`);
- ao importar, um cabeçalho guardado COM fórmulas aplica-as exatamente como
  foram gravadas (retrato fiel: campos vazios ficam vazios), tanto com a
  `def_peca` resolvida como no cabeçalho de recurso quando a peça já não
  existe;
- módulos antigos, gravados com os três campos vazios, mantêm exatamente o
  comportamento anterior (cabeçalho sem dimensões), mesmo que a `def_peca`
  tenha entretanto ganho fórmulas — o mesmo padrão de compatibilidade da
  prioridade ValueSet;
- confirmado que **Biblioteca de Módulos → Ver linhas** e o preview de
  importação já apresentam as colunas Comp/Larg/Esp genericamente, pelo que as
  fórmulas do cabeçalho aparecem sem alterações de interface (C4);
- sem alterações de esquema: as colunas do módulo já eram texto livre.

Testes automáticos:

- gravar preserva as fórmulas do cabeçalho e as transformações `PAI_*` dos
  filhos; importar aplica as fórmulas do cabeçalho (com e sem `def_peca`);
  módulo antigo mantém o cabeçalho sem dimensões; após
  `recalcular_medidas_do_item`, o cabeçalho `H × L/2` resolve 2000 × 500 e o
  filho `PAI_COMP-4 × PAI_LARG-4` resolve 1996 × 496;
- testes focados de módulos: `34 passed`;
- bateria completa: `1934 passed`.

Validação local pedida:

1. reiniciar a aplicação (não é necessária migração);
2. num item de teste com dimensões conhecidas, inserir uma divisão e um
   conjunto dimensionado (por exemplo o piloto de porta com cabeçalho
   `HM`/`LM`) e executar **Atualizar**;
3. selecionar as linhas e **Guardar como Módulo** (ou substituir um módulo de
   teste);
4. abrir **Biblioteca de Módulos → Ver linhas** e confirmar que o cabeçalho
   mostra as fórmulas Comp/Larg/Esp;
5. importar o módulo noutro item com divisão e dimensões diferentes, executar
   **Atualizar** e confirmar que o cabeçalho e os filhos resolvem as dimensões
   reais sem edição manual;
6. importar um módulo ANTIGO (gravado antes desta fase) e confirmar que o
   cabeçalho continua sem dimensões e o resultado não mudou.

Validação do utilizador: concluída (11 de julho de 2026). O utilizador testou
os pontos do guião e confirmou o comportamento correto.

Commit: `Guardar e importar formulas de cabecalho nos modulos`.

### Fase C — C3: proteção HM/LM/PM na importação de módulos

Implementação concluída e a aguardar validação local do utilizador:

- a proteção de divisão independente já existia na inserção de peças da
  biblioteca (fase anterior); a importação de módulos não a tinha;
- `inserir_modulo_no_item` valida agora, ANTES de criar qualquer linha, se o
  módulo precisa do contexto `HM/LM/PM`: a recusa é atómica e nenhuma linha
  parcial é gravada;
- o contexto é aceite quando o ITEM já tem uma divisão independente ativa, ou
  quando o MÓDULO inclui a sua própria divisão acima das linhas que usam
  `HM/LM/PM` (a ordem das linhas do módulo é respeitada);
- a verificação usa as fórmulas EFETIVAS de cada linha: o texto guardado no
  módulo com fallback, campo a campo, para a fórmula da `def_peca` que a
  importação aplicaria;
- num cabeçalho composto sem filhos guardados (módulo antigo que re-expande do
  catálogo), os associados são verificados recursivamente, como na biblioteca;
- a página do custeio passou a mostrar a CAUSA do erro de importação num
  aviso (antes apresentava apenas "Não foi possível importar o módulo").

Testes automáticos:

- recusa atómica sem divisão (zero linhas criadas); permissão com divisão no
  item; permissão com divisão própria do módulo acima das linhas `HM`;
  recusa pela fórmula efetiva da `def_peca` (texto do módulo vazio); recusa
  pelo associado `LM/PM` na re-expansão de módulo antigo e importação normal
  do mesmo módulo depois de existir divisão;
- testes focados de módulos/página: `93 passed`;
- bateria completa: `1939 passed`.

Validação local pedida:

1. num item de teste com o custeio VAZIO, importar um módulo que use
   `HM/LM/PM` e não comece por uma divisão independente;
2. confirmar o aviso com a causa e que nenhuma linha foi criada;
3. inserir uma divisão independente e repetir a importação, confirmando que
   passa;
4. importar um módulo que inclua a sua própria divisão num item vazio e
   confirmar que passa sem aviso;
5. confirmar que módulos só com `H/L/P` continuam a importar sem divisão.

Validação do utilizador: concluída (11 de julho de 2026). O utilizador testou
a fase, incluindo o piloto de porta e o módulo com uniões, e confirmou o
comportamento correto. **FASE C CONCLUÍDA** (C4 verificado sem alterações;
C5 coberto pelos testes e por este registo).

Commit: `Proteger importacao de modulos sem divisao independente`.

### Encaminhar para o ValueSet quando o item ainda não tem dados

Problema detetado pelo utilizador (11 de julho de 2026): num orçamento novo,
ao inserir peças num item cuja tabela ValueSet ainda está vazia, as linhas
ficam sem materiais atribuídos. O fluxo correto é preencher primeiro o
separador ValueSet e só depois inserir peças.

Implementação concluída e a aguardar validação local do utilizador:

- ao abrir o custeio de um item SEM linhas de ValueSet, a página abre
  diretamente no separador **ValueSet**, com a instrução na barra de estado;
- **Adicionar Seleções** (biblioteca de peças) e **Importar Módulo** verificam
  primeiro, na base de dados, se o ValueSet do item tem opções ativas; se
  estiver vazio, mostram um aviso com a explicação, mudam para o separador
  ValueSet e não criam nenhuma linha;
- a verificação é feita à base de dados no momento da ação (não à cache da
  página), para reconhecer um ValueSet acabado de preencher sem recarregar;
- inserções que não precisam de materiais (Divisão independente, separadores,
  operações manuais) não são afetadas.

Testes automáticos:

- teste de página cobre o guarda nas duas ações, a mudança de separador e a
  abertura direta no ValueSet em item vazio;
- testes focados da página: `55 passed`;
- bateria completa: `1940 passed`.

Validação local pedida:

1. criar um orçamento/item NOVO e abrir o custeio: deve abrir já no separador
   ValueSet com a instrução;
2. sem preencher nada, voltar ao Custeio e tentar **Adicionar Seleções** e
   **Importar Módulo**: aviso + regresso ao separador ValueSet, sem linhas
   criadas;
3. preencher o ValueSet (por exemplo **Importar Modelo**) e, sem sair do item,
   inserir peças: deve funcionar e atribuir materiais;
4. confirmar que itens já preenchidos abrem no separador Custeio como antes.

Validação do utilizador: concluída (11 de julho de 2026).

Commit: `Encaminhar para o ValueSet quando o item nao tem dados`.

Próximo passo recomendado: generalização das uniões estruturais (fase
seguinte proposta abaixo). Nesta data o `main` foi atualizado com todo o
trabalho da Fase C.

## Fase em curso

### Generalização das uniões estruturais — passo 1 concluído

O inventário das peças estruturais (leitura só-leitura da base de dados,
61 peças ativas, cruzado com o catálogo V2) está em
`docs/18_inventario_unioes_estruturais.md`: uniões já configuradas
(prateleira fixa, divisória, teto, fundos), tabela de decisão por família
para o utilizador (passo 2), relações topo/lateral, inconsistências
encontradas (placeholder gravado em `funcao`, duas formas de ligar
SISTEMAS_UNIAO, orientação da travessa, gaveta+puxador sem fórmulas `PAI_*`)
e cobertura vs V2. Aguarda as decisões do utilizador família a família.

### Generalização das uniões estruturais — plano original

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
# Alteração CNC — rasgos por comprimento geométrico (2026-07-12)

- Criada tarifa autónoma de rasgo CNC em €/ML STD e SÉRIE, sem reutilizar o €/ML de corte.
- O comprimento faturado é o comprimento geométrico: `n × COMP + n × LARG`; a ida e volta da fresa não duplica os ML.
- O CNC por escalão de área continua válido e pode coexistir com o rasgo na mesma peça.
- A máquina `CNC_ABD` não permite rasgos; as restantes CNC de fresagem iniciam com 0,40 €/ML.
- A definição da peça mostra a construção do rasgo e o simulador permite introduzir COMP, LARG, QT e tarifa.
- Exemplos de teste: `COSTA_INS_0000+RASGO` com `2 × COMP + 2 × LARG`; `LED` com `1 × COMP`.
- Correção posterior: a geometria do rasgo passa também pelos três níveis de operações ValueSet (modelo, orçamento e item) e pelos snapshots congelados das linhas. Snapshots antigos sem os novos campos são hidratados de forma compatível. Os avisos CNC são substituídos em vez de acumulados a cada atualização.

## Próxima fase proposta — Configuração guiada de operações e associados (2026-07-12)

Pedido do utilizador: os diálogos "Editar Operação da Peça", "Editar Associado"
e as operações das variantes ValueSet têm demasiadas opções e não é claro que
campos contam para o custo em cada combinação; pediu ajuda profunda, simulação
do resultado, interatividade e sugestões automáticas por semelhança.

Factos do modelo de cálculo (confirmados no código, base da solução):

- operações de PAINEL (corte/orlagem/CNC de peça com material) custeiam por
  tarifas automáticas: perímetro × €/ML, € por lado orlado (apenas os lados
  com dígito 1/2 no código de orlas) e escalão de área; nestas, a "Regra
  cálculo" é informativa — EXCEÇÃO: `RASGO_CNC`, que ativa o cálculo
  geométrico `n×COMP + n×LARG` × €/ML de rasgo;
- operações POR TEMPO (ferragens, manual/montagem/embalamento) custeiam por
  `(setup + quantidade_calculada × tempo_por_unidade) / 60 × €/h`, e a
  quantidade calculada depende da "Unidade tempo": PECA/UN/FURO/ML →
  quantidade_base × QT; M2 → área × QT; HORA → base em horas; LOTE → base;
- ou seja: por combinação (tipo de operação × regra × unidade) só um
  subconjunto pequeno de campos afeta o custo — os restantes são ruído visual.

Plano proposto (fases pequenas, por ordem de valor):

1. **G1 — Campos dinâmicos + fórmula visível**: nos diálogos de operação,
   mostrar apenas os campos que contam para a combinação escolhida (desativar
   os restantes com explicação) e apresentar SEMPRE a fórmula ativa com um
   mini-exemplo numérico em linguagem simples.
2. **G2 — Simulador completo**: alargar o "Simular cálculo…" para decompor o
   resultado em € com a tarifa REAL da máquina e QT de exemplo, igual à
   tooltip do custeio; disponibilizá-lo também no "Editar Associado".
3. **G3 — Receitas ("Configurar como…")**: pré-definições que preenchem os
   campos certos: ferragem com furação CNC (N furos), cavidade/pocket CNC por
   tempo, união por topos, suporte com regra por medida, operação manual por
   peça, rasgo por comprimento.
4. **G4 — Sugestão por semelhança**: ao criar operação/associado, procurar
   configurações existentes na mesma categoria/chave ValueSet e propor
   "Copiar configuração de X" (determinístico; a camada IA generativa fica
   para a visão futura do assistente).

Validação do utilizador: aprovado começar pelo G1 (12 de julho de 2026).

## G1 implementado — campos dinâmicos + fórmula visível (2026-07-12)

Alterações implementadas:

- Novo módulo puro `app/domain/operacao_guia.py`: dado (tipo de operação ×
  regra × unidade tempo × natureza da peça), devolve o modo de custeio, a
  fórmula ativa em linguagem simples com mini-exemplo numérico e os campos
  que NÃO contam (com o motivo). Reutiliza `classificar_operacao` e os
  helpers reais de custo (`calcular_tempo_operacao`,
  `calcular_custo_por_minutos`, `calcular_comprimento_rasgo_ml`), pelo que o
  guia nunca diverge do motor de custeio. Modos: TARIFA (corte/orlagem/CNC
  em peça de painel), RASGO (CNC_RASGO ou regra Rasgo CNC), TEMPO
  (montagem/manual/embalamento/setup e QUALQUER operação numa ferragem) e
  SEM_CUSTEIO (tipo/código não reconhecido — a operação é ignorada).
- `DefPecaOperacaoDialog` ("Editar Operação da Peça", também usado pelas
  operações de variante ValueSet): painel de fórmula SEMPRE visível por
  baixo do formulário, atualizado ao vivo ao mudar operação, regra, unidade,
  quantidades, tempos ou construção do rasgo; campos que não contam ficam
  desativados com o motivo acrescentado ao tooltip (rasgo → quantidade e
  tempos; unidade M2 → quantidade base; unidade HORA → tempo por unidade);
  tooltips em todos os campos. A ação DESATIVAR das variantes mantém o
  comportamento anterior e mostra a sua própria explicação. O simulador
  "Simular cálculo…" e a construção do rasgo do Codex não foram tocados.
- Contexto painel vs ferragem: a página de detalhe da peça passa a
  `natureza` da def_peça ao diálogo; os três diálogos de linha ValueSet
  (modelo, orçamento e item) derivam o contexto da chave via novo helper
  `natureza_peca_da_chave` (tipo configurado na BD com fallback ao prefixo,
  as mesmas famílias FERRAGEM/SISTEMA_CORRER/ILUMINACAO/ACESSORIO do
  custeio). Sem contexto conhecido, o guia mostra as duas fórmulas
  (tarifa em painel + tempo em ferragem).
- "Editar Associado": tooltips completados em todos os campos de
  configuração (tipo, descrição, quantidade, regra base, zona de aplicação,
  dimensão de referência; os restantes já existiam). O simulador neste
  diálogo fica para o G2.

Decisões tomadas:

- Nas operações por TARIFA, os campos de tempo NÃO são desativados: não
  alteram o custo mas alimentam os tempos de produção informativos — o guia
  e os tooltips explicam isso em vez de bloquear.
- A regra de cálculo continua sempre editável (é informativa, exceto Rasgo
  CNC) com tooltip a explicar.
- Exemplos numéricos usam QT 10, área 0,5 m² e COMP 600/LARG 400 como
  valores de demonstração, calculados pelos próprios helpers do motor.

Correção apanhada em smoke test offscreen: ao trocar da operação
`CNC_RASGO` para outra, a regra ficava presa em "Rasgo CNC" (o diálogo
tinha-a forçado) e os tempos continuavam desativados. O diálogo agora
desfaz apenas a regra que ELE forçou (volta a "Fixa"); uma regra Rasgo CNC
gravada deliberadamente noutra operação não é tocada ao abrir.

Testes automáticos: 1971 a passar (26 novos — `tests/test_operacao_guia.py`
com o comportamento do guia por modo, `tests/
test_def_peca_operacao_dialog_guia.py` com o diálogo real offscreen
(inclui a regressão da regra presa), mais inspeções nos diálogos e no
helper da chave).

Testes locais pedidos ao utilizador:

1. Catálogo Técnico → peça de painel → operações → "Editar Operação da
   Peça": com uma operação de CORTE/ORLAGEM/CNC deve aparecer o painel com a
   fórmula da tarifa e a nota de que os tempos são só informativos;
2. na mesma peça, escolher a operação `CNC_RASGO`: quantidade e tempos ficam
   desativados (motivo no tooltip) e o painel mostra `ML = n×COMP + n×LARG`
   com exemplo em euros quando a máquina tem €/ML de rasgo;
3. operação MANUAL/MONTAGEM com unidade "Por furo": preencher quantidade
   base 5, setup 2 e tempo 0,04 → o exemplo deve dizer "4 min … 3,00 €"
   (com custo/hora 45); mudar a unidade para "Por m2" desativa a quantidade
   base; "Por hora" desativa o tempo por unidade;
4. ValueSets → chave de ferragem (ex.: dobradiça) → operações da linha →
   nova operação CNC: o painel deve indicar custo por TEMPO (contexto
   ferragem), não por escalão de área;
5. variante com ação "Desativar": os campos ficam todos desativados com a
   explicação própria (comportamento anterior mantido).

Validação recebida: 2026-07-12 — o utilizador testou ANTES do merge (a app
corria a pasta principal, então no branch codex/pecas-associados) e por isso
não viu as alterações; aprovou avançar. A pasta principal foi mudada para o
`main` e o G1 foi merged (fast-forward) para o utilizador testar na app.
Pedido novo do utilizador: no fim de cada alteração, entregar um guião de
testes DETALHADO com o caminho exato dos menus (registado na memória do
assistente e aplicado a partir do G2).

Commit: `Guia de configuracao G1 nos dialogos de operacoes` (+ fix
`Repor regra ao sair do rasgo e testar o guia no dialogo real`).

Próximo passo recomendado: G2 — simulador completo com tarifa real da
máquina, também no "Editar Associado".

## G2 implementado — simulador com tarifas reais + Editar Associado (2026-07-12)

Alterações implementadas:

- `DefOperacaoResumo` passa a embutir as tarifas REAIS (STD) da máquina da
  operação: custo/hora (STD e SÉRIE), €/ML de corte, € lado curto/longo +
  limite mm, setup por peça — as mesmas colunas que o custeio usa.
- Simulador por tempo ("Simular cálculo…"): o campo Custo/hora vem agora
  pré-preenchido com o custo/hora real da máquina (antes vinha vazio na
  maioria dos casos, porque só lia o custo/hora da própria operação).
- NOVO simulador de tarifa de painel (`SimuladorTarifaPainelDialog`): para
  operações de CORTE / ORLAGEM / CNC numa peça de painel, o botão
  "Simular cálculo…" abre agora a decomposição em € com a tarifa real:
  corte = perímetro × QT × €/ML + QT × setup; orlagem = lado a lado
  (C1/C2/L1/L2, curto/longo conforme o limite) × QT + setup; CNC = área →
  escalão de área da máquina (lidos da BD) → € por peça × QT. Em ferragens
  continua a abrir o simulador por tempo; no CNC_RASGO o do rasgo.
- NOVO "Simular quantidade…" no "Editar Associado"
  (`SimuladorQuantidadeAssociadoDialog`): com COMP/LARG/ESP/QT de exemplo da
  peça principal, mostra a MEDIDA_TOPO derivada da dimensão de referência,
  o resultado da expressão da regra de quantidade (ou a quantidade fixa),
  a multiplicação por topos no modo "Quantidade por topo" e o qt_und final —
  exatamente a regra do custeio (`avaliar_regra_quantidade` + POR_TOPO).

Decisões tomadas:

- Tarifas do simulador são as STD (o custeio escolhe STD/SÉRIE pelo tipo do
  item; o simulador documenta a base STD — SÉRIE fica para evolução).
- Valores de exemplo pré-preenchidos: peça 600×400 mm (painel), peça
  principal 2000×600×19 mm (associado), QT 1 — todos editáveis em direto.

Testes automáticos: 1981 a passar (10 novos) — testes offscreen dos dois
simuladores (corte 2,70 €, orlagem por lados, CNC por escalão,
regra CEIL(MEDIDA_TOPO/300) × topos, quantidade fixa, erros amigáveis) e
inspeção do read model com as tarifas.

Guião de teste local (caminhos exatos):

1. **Reiniciar a app** (pasta principal, agora no branch `main`).
2. **Simulador de corte com tarifa real** — Catálogo Técnico → separador
   Peças → abrir a peça `COSTA_ONS_0022` → separador Operações → selecionar
   a linha 1 `CORTE_PAINEL` → botão "Editar Operação" → botão
   "Simular cálculo…". DEVE abrir "Simular custo por tarifa da máquina" com
   COMP 600 / LARG 400 / QT 1 e mostrar: perímetro 2 ML e o custo com o €/ML
   real da máquina CORTE (linha cinzenta por baixo da operação mostra as
   tarifas). Mudar COMP para 1000 → o custo recalcula em direto.
3. **Simulador de orlagem** — mesma peça → linha 2 `ORLAGEM_PECA` → Editar
   Operação → Simular cálculo…. Alterar o código de orlas (ex.: `1100`) e
   ver o detalhe lado a lado (C1, C2) e o total; `0000` deve dar 0,00 €.
4. **Simulador CNC por escalão** — mesma peça → linha 3 `CNC_MECANIZACAO` →
   Editar Operação → Simular cálculo…. Com 600×400 deve indicar a área
   0,24 m², o escalão correspondente da máquina CNC_VERTICAL e o preço por
   peça; aumentar COMP/LARG muda de escalão. (Se a máquina não tiver
   escalões ativos, aparece o aviso "escalões de área em falta" — configurar
   em Operações/Máquinas.)
5. **Custo/hora real no simulador por tempo** — mesma peça → linha 4
   `EMBALAMENTO` (ou 5 `OPERACAO_MANUAL`) → Editar Operação → Simular
   cálculo…. O campo "Custo/hora (€/h)" deve vir PRÉ-PREENCHIDO com o
   custo/hora da máquina MANUAL (antes vinha vazio).
6. **Painel-guia G1 (agora visível)** — no mesmo diálogo "Editar Operação da
   Peça" deve aparecer uma CAIXA CINZENTA por baixo do formulário com a
   fórmula ativa; muda em direto ao trocar a Operação / Unidade tempo.
7. **Simular quantidade no Associado** — Catálogo Técnico → Peças → abrir
   uma peça composta com associados (ex.: uma lateral/prateleira com
   cavilhas) → separador Associados → Editar Associado → novo botão
   "Simular quantidade…". Com uma regra de quantidade selecionada deve
   mostrar: MEDIDA_TOPO derivada, resultado da expressão, multiplicação por
   topos (se "Quantidade por topo") e o qt_und final; sem regra mostra a
   quantidade fixa. Mudar LARG de 600 para 900 recalcula em direto.

Validação recebida: 2026-07-12 — o utilizador confirmou melhorias mas
esperava mais: "tenho opções a mais que não dão resultado nenhum" (muitas
regras/unidades selecionáveis sem efeito). Pediu para avançar já para o G3
e avaliar o conjunto no fim.

Commit: `Simuladores com tarifas reais da maquina e quantidade do associado`.

Próximo passo recomendado: G3 — receitas "Configurar como…".

## G3 implementado — receitas "Configurar como…" (2026-07-12)

Resposta direta ao feedback "opções a mais": em vez de escolher entre 11
regras e 9 unidades, o utilizador escolhe UMA receita e os campos certos
ficam preenchidos de uma vez (tudo continua editável e o painel-guia mostra
logo a fórmula resultante).

Alterações implementadas:

- Novo domínio puro `app/domain/operacao_receitas.py` com as receitas dos
  dois diálogos (chave, nome, descrição, valores, campo a rever primeiro).
- "Editar Operação da Peça": novo campo **"Configurar como…"** no topo com
  5 receitas — *Ferragem com furação CNC (por furo)* (unidade FURO, 4 furos,
  0,04 min/furo, setup 0,5), *Cavidade/bolsa (pocket) CNC por tempo* (Fixa,
  base 1, Por peça), *Operação manual/montagem por peça*, *Tempo fixo por
  lote/encomenda* (unidade LOTE, não multiplica pela QT) e *Rasgo CNC por
  comprimento* (esta muda também a Operação para CNC_RASGO e põe
  1 × COMP; avisa se a operação CNC_RASGO não existir). Depois de aplicar,
  o cursor fica no campo que o utilizador deve rever (ex.: n.º de furos).
- Dropdown "Regra cálculo": todas as regras exceto "Rasgo CNC" passam a
  mostrar o sufixo **"(informativa)"** — as opções que não fazem nada agora
  dizem-no explicitamente.
- "Editar Associado": novo campo **"Configurar como…"** com 4 receitas —
  *União nos dois topos* (zona DOIS_TOPOS, por topo × 2, MEDIDA_TOPO),
  *União num topo*, *Suporte/ferragem com regra por medida* (total, COMP,
  foco na escolha da regra) e *Acessório fixo por peça* (quantidade 1, sem
  regra — limpa a regra configurável se estava escolhida).

Testes automáticos: 1991 a passar (10 novos) — receitas bem formadas no
domínio + aplicação real das receitas nos dois diálogos offscreen (furação,
rasgo com/sem CNC_RASGO disponível, marcação "(informativa)", união dois
topos, acessório fixo limpa a regra).

Guião de teste local (caminhos exatos):

1. **Reiniciar a app** (pasta principal, branch `main`).
2. **Receita de furação** — Catálogo Técnico → Peças → abrir uma def_peça
   de ferragem (ex.: a genérica DOBRADICA) → separador Operações → Editar
   Operação (ou Nova Operação com uma operação CNC) → no topo do diálogo,
   campo "Configurar como…" → escolher **"Ferragem com furação CNC (por
   furo)"**. DEVE preencher: Regra "Por furação (informativa)", Quantidade
   base 4 (cursor fica aqui), Tempo setup 0,5, Tempo por unidade 0,04,
   Unidade "Por furo (× QT)"; a caixa-guia mostra logo o tempo/custo de
   exemplo. Ajustar o 4 para o n.º real de furos.
3. **Receita de rasgo** — na peça `COSTA_INS_0000+RASGO` → Operações →
   Editar Operação → "Configurar como…" → **"Rasgo CNC por comprimento"**.
   DEVE mudar a Operação para CNC_RASGO, pôr 1 comprimento × 0 larguras e
   regra "Rasgo CNC"; os campos de tempo ficam desativados (G1).
4. **Regras marcadas** — em qualquer "Editar Operação da Peça", abrir o
   dropdown "Regra cálculo": todas as opções exceto "Rasgo CNC por
   comprimento geométrico" dizem "(informativa)".
5. **Receita união dois topos** — Catálogo Técnico → Peças → peça composta
   → separador Associados → Editar Associado → "Configurar como…" →
   **"União nos dois topos (cavilhas/parafusos)"**. DEVE pôr Zona "Dois
   topos", Aplicação "Quantidade por topo", Número de topos 2, Dimensão
   "Medida do topo", e o cursor fica na "Regra de quantidade (opcional)"
   para escolher a regra (ex.: por medida do topo). Confirmar com o botão
   "Simular quantidade…" (G2) que o qt_und dá o esperado.
6. **Receita acessório fixo** — no mesmo diálogo, escolher **"Acessório
   fixo por peça"**: quantidade volta a 1, regra configurável volta a
   "— sem regra —", zona Geral, modo "Quantidade total".

Validação recebida: 2026-07-12 — "já existe alguma melhoria"; o utilizador
conta aprender com o uso e quer, a prazo, IA dentro dos menus (sugerir
preenchimentos e analisar se o que o operador seleciona faz sentido).
Aprovou avançar para o G4 em nova conversa.

Nota a verificar no G4: no teste do utilizador, a receita de furação foi
aplicada numa operação CNC_VERTICAL com o guia em modo TARIFA ("cnc") — se
foi numa peça de painel, os tempos configurados não contam para o custo
(reforçar o aviso?); se foi numa ferragem, a natureza não chegou ao diálogo
nesse caminho.

Commit: `Receitas Configurar como nos dialogos de operacoes e associados`.

Próximo passo recomendado: G4 — sugestão por semelhança ("Copiar
configuração de X"): ao criar operação/associado, procurar configurações
existentes na mesma categoria/chave e propor copiar (determinístico; a
camada IA generativa fica para a visão futura).

## G4 implementado — sugestão por semelhança "Copiar configuração de…" (2026-07-12)

Alterações implementadas:

- Novo domínio puro `app/domain/configuracao_sugestoes.py`: dado o conjunto
  de configurações EXISTENTES da mesma operação (ou do mesmo componente
  associado), agrupa as configurações idênticas numa só sugestão, ordena por
  n.º de utilizações (desempate: mais recente, depois nome da origem) e
  produz um resumo humano (ex.: "4 furo(s) × 0,04 min, setup 0,5 min" ou
  "regra CAV300, por topo × 2, Medida do topo"). Determinístico, sem IA.
- Novo repositório `app/repositories/configuracao_sugestoes_repository.py`:
  fontes das sugestões de operação = ligações ativas `DefPecaOperacao`
  (com a peça) + operações ativas de linhas de MODELO ValueSet
  (`DefValuesetModeloLinhaOperacao`, com modelo › chave: opção). As
  operações de linhas de orçamento/item são cópias por orçamento e ficaram
  de fora de propósito. Associados = `DefPecaComponente` ativos (com a peça
  pai e o código da regra de quantidade).
- "Editar Operação da Peça": novo campo **"Copiar configuração de…"** por
  baixo do "Configurar como…". Atualiza ao mudar a Operação; sem
  configurações existentes mostra "— sem configurações desta operação para
  copiar —" desativado. Escolher uma sugestão copia regra, quantidade,
  construção do rasgo, tempos e unidade (o painel-guia G1 mostra logo a
  fórmula com os valores copiados). O tooltip de cada sugestão lista TODOS
  os sítios que usam aquela configuração.
- "Editar Associado": novo campo **"Copiar configuração de…"** que sugere
  as configurações do MESMO componente (mesma peça componente, ou mesma
  referência quando é ferragem/acessório) noutras peças pai; copia
  quantidade, regra base, regra de quantidade configurável, zona, dimensão,
  topos, modo e as fórmulas dimensionais do filho.
- Exclusões: a própria peça (detalhe da peça) e a própria linha de modelo
  ValueSet nunca aparecem como origem; nos diálogos de orçamento/item não é
  preciso excluir (as fontes são só de catálogo).
- ⚠️ do arranque (furação configurada em modo TARIFA): o guia G1 passa a
  mostrar um aviso REFORÇADO quando o utilizador preenche tempos numa
  operação de tarifa de painel: "⚠️ ATENÇÃO: os tempos que preencheu NÃO
  entram no custo … configure a operação na peça ou linha ValueSet de
  FERRAGEM." (só aparece com tempos preenchidos).

Testes automáticos: 2008 a passar (17 novos) — domínio das sugestões
(agrupamento/dedup, ordenação, filtros, resumos, associado por peça e por
referência), aviso reforçado do guia, e os dois diálogos offscreen
(preencher ao escolher, combo desativado sem sugestões, linha escondida sem
fontes, troca de operação/peça componente atualiza as sugestões).

Guião de teste local (caminhos exatos):

1. **Reiniciar a app** (pasta principal, branch `main`).
2. **Sugestão numa operação de ferragem** — ValueSets → Modelos → abrir um
   modelo com uma dobradiça JÁ CONFIGURADA (com operação CNC por furo) →
   escolher/criar OUTRA linha de dobradiça na mesma chave → "Operações da
   linha" → Nova Operação → escolher a MESMA operação CNC. DEVE aparecer o
   campo "Copiar configuração de…" com pelo menos uma sugestão do tipo
   "Modelo X › DOBRADICAS: DOBRADICA_Y — 4 furo(s) × 0,04 min, setup 0,5
   min". Escolhê-la preenche regra/quantidade/tempos/unidade de uma vez e a
   caixa-guia mostra o custo de exemplo. Pousar o rato na sugestão mostra
   onde ela é usada.
3. **Sugestão no Catálogo Técnico** — Catálogo Técnico → Peças → abrir uma
   peça → Operações → Nova Operação → escolher uma operação usada noutras
   peças (ex.: EMBALAMENTO): as configurações das outras peças aparecem
   para copiar; a peça atual nunca aparece como origem.
4. **Sem configurações** — escolher uma operação que ainda não está
   configurada em lado nenhum: o campo mostra "— sem configurações desta
   operação para copiar —" e fica desativado (cinzento).
5. **Sugestão num associado** — Catálogo Técnico → Peças → peça composta →
   Associados → Novo Associado → escolher uma peça componente (ex.: a
   cavilha) que já esteja configurada noutras peças: aparece "Copiar
   configuração de… Peça X — regra …, por topo × 2, Medida do topo".
   Escolher copia zona/topos/modo/dimensão/regra/fórmulas. Com tipo
   Ferragem/Acessório, a sugestão segue a REFERÊNCIA escrita.
6. **Aviso reforçado (⚠️ do G1–G3)** — numa peça de PAINEL (ex.:
   `COSTA_ONS_0022`) → Operações → Editar a operação `CNC_MECANIZACAO` →
   preencher "Tempo por unidade" 0,04: a caixa-guia passa a mostrar
   "⚠️ ATENÇÃO: os tempos que preencheu NÃO entram no custo…". Apagar o
   tempo faz o aviso desaparecer.

Commit: `Sugestoes Copiar configuracao de nos dialogos de operacoes e associados`.

Validação recebida: 2026-07-12 — o utilizador testou ("ficou melhor") e
fechou este ciclo. No teste real (operação CNC_VERTICAL numa linha de
dobradiça do modelo Roupeiro standard) o guia mostrou corretamente o modo
por TEMPO com a nota "Peça de FERRAGEM" — o contexto da natureza chega bem
ao diálogo das linhas ValueSet.

Estado: G1+G2+G3+G4 completos — fim do plano de configuração guiada.
Próximo: avaliação global do utilizador com dados reais; pendentes antigos
(placeholder "Selecionar origem…", ligação SISTEMAS_UNIAO, caixote de teste
completo) e a visão de IA nos menus.

> **Falha no registo (anotada a 2026-10-04):** entre 2026-07-12 e 2026-10-04 os
> guiões de teste não foram registados neste ficheiro. O Paulo confirmou que a
> regra se mantém. O que ficou para trás vai ser reposto numa sessão própria; daqui
> para a frente cada alteração regista aqui o seu guião.

## Cópia de segurança: a memória do Claude entra na cópia das 03:00 (2026-10-04)

Pedido do utilizador: a memória do Claude Code sobre este projeto (118 ficheiros
com as regras do Paulo, armadilhas e decisões) só existia neste PC, sem cópia.

- `scripts/backup_martelo.py` ganhou o passo **[5/5] memória do Claude**: comprime
  a pasta da memória para `memoria_claude_AAAA-MM-DD_HHMM.zip`, confere o zip
  (todos os ficheiros lá dentro, nenhum estragado) e põe-no na subpasta
  `Memoria_Claude` da pasta local e da do servidor.
- Rotação igual à da base (14 diárias, 8 semanais, 12 mensais, nunca menos de 3).
  Só mexe nos zips com o nome exato que o script gera — a cópia feita à mão a
  04-10 (`memoria_2026-10-04`) nunca é tocada.
- Se o passo da memória falhar, fica só um AVISO no `backup.log` e no
  `ultima_copia.txt`: **nunca deita abaixo a cópia da base**. Se for a base a
  falhar, a memória guarda-se na mesma.
- `--sem-memoria` desliga o passo; `--memoria <pasta>` escolhe outra pasta.
- **Nunca vai para o GitHub:** o repositório é público e a memória tem nomes de
  contas e a análise de segurança. Antes da primeira cópia foi retirada a única
  password que lá estava escrita.
- A tarefa agendada não precisou de mudar: corre o script da pasta principal.

Testes automáticos: 12 novos em `tests/test_backup_martelo.py` (caminho da
memória a partir da pasta principal e de um worktree, zip completo e conferido,
memória vazia não deixa zip, subpasta nos dois sítios, falhas só como aviso,
rotação e o que ela nunca pode tocar).

Guião de teste local:

1. Amanhã de manhã, no Explorador do Windows, abrir
   `\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\Base_Dados_Orcamento\Backup_Martelo_V3\Memoria_Claude`.
   Deve lá estar `memoria_claude_2026-10-05_0300.zip`, ao lado da pasta
   `memoria_2026-10-04` (a cópia feita à mão).
2. Fazer duplo clique no zip: deve mostrar o `MEMORY.md` e os outros ficheiros `.md`.
3. Na mesma pasta `Backup_Martelo_V3`, a cópia da base de dados dessa noite deve
   estar lá como sempre (`martelo_v3_2026-10-05_0300.sql.gz`).

Validação recebida: — (por testar).

## Ferragens para o iMos: ferramentas STEP → DWG + imagem no repositório (2026-10-04)

Pedido do utilizador: separar a união `NIVELADOR_40086` em nivelador esquerdo e
direito (cada um com o seu código PHC, para o mapeamento do custeio nas listagens),
gerando os DWG e as imagens a partir dos STEP da Emuca; e guardar as ferramentas,
porque vão aparecer outros tipos de ferragens para converter.

Entregue na biblioteca do iMos (fora do repositório):
`EMUCA_4030705_NIVELADOR_LEVEL_UP_DIR` e `EMUCA_4030805_NIVELADOR_LEVEL_UP_ESQ`
(`.DWG` em `I:\Library\ConnDWG`, `.jpg` 256×256 em `I:\Library\Info\BITMAPS`), no
mesmo referencial do `GS_SH_6301_RECHTS/LINKS` que a união usava (as três cavilhas
coincidem), simplificados (cavilhas lisas, excêntricos e lingueta refeitos com
primitivas): 622 kB e 574 kB.

No repositório, `scripts/imos_ferragens/` (README com o passo a passo, o que muda
de ferragem para ferragem e as armadilhas da consola OEM do iX CAD):

- `step_para_dwg.ps1` — STEP → DWG com os sólidos soltos + SAT. Explode os blocos
  por passagens (conta-os antes), porque uma seleção vazia encrava a consola.
- `cortes.ps1` — corta o sólido em fatias e grava DXF R12 (é assim que se "vê" a
  peça sem CAD gráfico); avisa se o kernel falhar algum corte.
- `arestas.ps1`, `instalar_na_biblioteca.ps1` (nunca grava por cima; confere
  formato 2018, 256×256 e o hash).
- Python (`python -m scripts.imos_ferragens.<comando>`): `sat` (medir faces/eixos),
  `arame`, `vistas`, `imagem`, `sobrepor`, `ficha_pdf`.
- `exemplos/nivelador_levelup.ps1` — a montagem do nivelador, como modelo.

Validação feita por mim: a cadeia toda corrida de novo a partir dos STEP numa pasta
vazia dá sólidos com o mesmo volume e a mesma caixa dos que foram entregues
(direito 20 252,8923 mm³, esquerdo 20 415,5485 mm³) e a mesma imagem.

Testes automáticos: 19 novos em `tests/test_imos_ferragens.py` (SAT, leitura dos
cortes R12 com normal invertida, furo dentro de região, regiões sobrepostas,
contorno aberto, corte em falta, render, `.ps1` só ASCII, README completo).

Guião de teste local:

1. No iX Organizer → Element Manager → Uniões → _LANCA_ENCANTO → NIVELADORES →
   NIVELADORES_COZINHAS → NIVELADOR_EMUCA_40308_ESQ: no grupo que tinha o desenho
   `GS_SH_6301_links_D8630021017_L`, pôr o DWG novo do esquerdo, sem mexer nos pontos
   de inserção; "Preview Image" = o `.jpg` com o mesmo nome. Igual para o direito
   (no lugar do `rechts`).
2. Aplicar as uniões num módulo superior: as 3 cavilhas devem entrar nos furos Ø10
   da lateral, gancho em cima e virado para a parede; a imagem aparece na lista de
   ferragens. Confirmar que a barra da lingueta (97,5 mm abaixo da cavilha de cima)
   cai no 4.º furo do `4F_10MM_NIVELADOR_Lateral`.
3. Ferramentas: numa janela do PowerShell na pasta do Martelo, correr
   `.\scripts\imos_ferragens\step_para_dwg.ps1 -Step C:\Users\Utilizador\Downloads\40307.step -Pasta C:\Temp\teste_ferragem`
   — deve acabar em ~15 s a listar 8 `3DSOLID` e 1 `SURFACE`, com o aviso da SURFACE.

Validação recebida: — (por testar). Nota: às 21:04 já havia em `ConnDWG` versões
`_R` / `_L` destes DWG gravadas pelo iX CAD (os entregues ficaram como `.bak`).
A pedido dele, as imagens passaram a `_R` / `_L` como os DWG. O DWG
`EMUCA_4030805_NIVELADOR_LEVEL_UP.DWG`, que era igual byte a byte ao `_L`, foi
**movido** para `C:\Users\Utilizador\Downloads`: o `I:` não tem Reciclagem, por isso
não foi apagado. Os `.bak` já não existiam.

## Drawing Views do iMos: análise e propostas de layouts (2026-10-05)

Pedido do utilizador: explorar as "Drawing views" do iMos (plantas, alçados e cortes
automáticos com cotas). Já tinha tentado e nunca chegou a layouts válidos. É **só
análise**: não se mexeu na configuração do iMos nem na obra de teste, que foi lida
a partir de uma cópia.

Entregue no repositório:

- `docs/37_drawing_views_imos.md` — como funcionam (vistas = blocos `imosSect*` com
  camadas `AutoDims`/`ManualDims`/`Label`, princípios de cotagem/anotação/moldura,
  condições), o que o iX 2025 já faz sozinho (saída "Drawing Views" nos Output batches),
  o inventário da configuração atual, o diagnóstico da `APAGAR_03` (8 pontos) e o
  plano F0–F8.
- `docs/imos_drawing_views/Propostas_Layouts_A3.pdf` — 7 folhas A3:
  - índice;
  - diagnóstico com as vistas reais redesenhadas;
  - propostas de planta, alçado e corte;
  - folha única;
  - variante para o cliente.

  As propostas são **maquetas** desenhadas por cima das vistas reais da `APAGAR_03`.
  A verde, em cada folha, aparece a configuração do iMos que a produz.

Guião (leitura, não há código para testar):

1. Abrir o PDF. A folha 0 deve mostrar a planta, o alçado e o corte da `APAGAR_03`
   tal como o iMos os gerou, com os 8 problemas numerados.
2. Folhas 1 a 3: confirmar se o tipo de cotagem (cadeias, distâncias, etiquetas por
   posição + tabela) é o que a LE quer nos desenhos de obra.
3. Escolher por onde começar. A proposta é o alçado: F1 moldura `LE_A3_Obra`, depois
   F2 condições, F3 `LE_Alcado` e F4 `LE_Alcado_Pos`. Fazer cada passo no Element
   Manager, numa obra de teste **nova**.

Validação recebida (05-10, à tarde): o PDF agradou. As folhas 1 a 4 foram aprovadas, com
estes requisitos:

- tudo em A3 horizontal, sem "Lanca Encanto" nem "LE";
- cores por tipo de móvel;
- nome e medidas enquadrados no alçado;
- folha única com perspetiva, planta, alçado, corte e tabela.

Os nomes `LE_*` do plano passaram a `DV_*` (neutros).

### Volta 1 na base de testes `imos_LE_TESTES` (2026-10-05, tarde)

Autorizado pelo Paulo:

- escrever `DV_*` na `imos_LE_TESTES`;
- controlar o iX CAD;
- gravar na obra de teste ORC_260881_2604023 (ele tem cópia);
- copiar `DV_*` novos para `I:\Library\AttDWG`.

A `imos_LE` não foi tocada (só `SELECT`). Ferramentas novas em `scripts/imos_drawing_views/`
(README com a receita). O detalhe e os resultados estão no doc 37, secção 6b.

- **Na base de testes** (pasta `DV_Desenhos` de cada árvore):
  - 10 condições;
  - cotagem `DV_Planta`, `DV_Alcado` e `DV_Alcado_Frentes`;
  - etiquetas `DV_Alcado_Etiquetas`, `DV_Alcado_Etiquetas_Modulos` e `DV_Planta_Etiquetas`;
  - moldura `DV_A3_Obra`;
  - Output batch `DV_Desenhos_Obra`.
- **Em `I:\Library\AttDWG`:**
  - em uso: `DV_Etq_Modulo(_r)`, `DV_Etq_Nome(_r)` e `DV_Etq_Frente`;
  - sem uso, da 1.ª tentativa: `DV_Artigo_Medidas(_r)` e `DV_Frente_Medidas`. Só se
    apagam se o Paulo quiser.
- **Na obra de teste:** a planta e os 2 alçados foram refeitos com as `DV_*` (Refresh view)
  e gravados.
  - A planta e o alçado do fundo já saem como as folhas 1 e 2: cores por tipo, uma cadeia
    de alturas e as etiquetas certas.
  - Os layouts ainda têm a moldura antiga (STANDARD): falta correr o batch.

Guião de teste (iX CAD **aberto**, base `imos_LE_TESTES`):

1. No iX Organizer, abrir o Element Manager e carregar em "Atualizar" (⟳). Em Outputs →
   Output Batches deve aparecer a pasta `DV_Desenhos` com o `DV_Desenhos_Obra` (Modo
   Encomenda). Uma saída "Drawing Views": Layouts & PDF, planta e alçados com `DV_A3_Obra`
   e "Best scale".
2. Abrir o Order Manager, pesquisar `2604023` e escolher **ORC_260881_2604023**. Em Output
   Batches, marcar só `DV_Desenhos_Obra` e carregar em ✓.
3. Resultado esperado:
   - PDF em `C:\IMOS_Output_Batches\DV_Desenhos`;
   - na obra, layouts A3 novos (planta + 1 por parede) com a moldura neutra, legenda
     preenchida (Cliente JF_VIVA, Obra ORC_260881_2604023, Escala 1:N, Folha) e nenhum
     nome de campo a vermelho;
   - etiquetas dos módulos legíveis (texto de ~2,5 mm a 1:20).
4. No alçado da parede do fundo:
   - por baixo, 920 | 660 a azul e 720 a vermelho (coluna);
   - por cima, 1580 a magenta;
   - à direita, uma só cadeia 880 / 620 / 810 (2310);
   - nas portas, L×A ao centro.

**Por verificar:** o passo 2. No 1.º teste o iX CAD fechou-se durante o batch e não foi gerado
nada. Não houve erro no registo do Windows, por isso falta repetir com o iX CAD aberto.

## Drawing Views: batch dos roupeiros, ronda R1 (2026-10-06)

O objetivo final ficou acordado com o Paulo (doc 37, secção 6c): um Output batch por tipo
de obra, com o `IMOS.dwt` e o layout "1" intocados. A R1 criou na `imos_LE_TESTES`:

- o batch **`DV_Roupeiros`**, com as regras próprias `DV_Roup_*` (por agora cópias das de
  obra);
- a moldura **`DV_A3_Roupeiro`**, com uma legenda de 2 linhas:
  - linha 1: Artigo, Nome enc. iMOS, Enc. PHC, Ref. cliente, Obra, Entrega;
  - linha 2: Desenho, Escala, Folha, Desenhador, Data.

O `DV_Desenhos_Obra` ficou como estava.

Guião de teste (iX CAD **FECHADO**, base `imos_LE_TESTES`):

1. No iX Organizer, abrir o Element Manager e carregar em "Atualizar" (⟳).
   - Em Outputs → Output Batches → pasta `DV_Desenhos` devem aparecer o
     `DV_Desenhos_Obra` e o **`DV_Roupeiros`**.
   - Em Molduras deve aparecer a **`DV_A3_Roupeiro`**.
2. Fechar o iX CAD. A APAGAR_15 fica fechada para este teste.
3. No Order Manager, escolher **APAGAR_15**. Em Output Batches, marcar só **`DV_Roupeiros`**
   e carregar em ✓.
4. Resultado esperado em `C:\IMOS_Output_Batches\APAGAR_15_Submittals.pdf` (a cópia anterior
   é substituída):
   - a planta e a Vista 1 com o mesmo desenho e as mesmas cotas que hoje;
   - a legenda nova, com 2 linhas, sem Descrição e sem Cliente;
   - na linha de cima, **Artigo = RP_A_01**, 1571_01_26_JF_VIVA, 1571, 2604023, APAGAR_15
     e 20/10/2026;
   - na linha de baixo, Planta 1 / Vista 1, 1:16, a folha, Paulo e a data de hoje.
5. **Se o campo Artigo ficar vazio**, a legenda está certa mas as folhas de obra não
   preenchem o `IMOSARTICLEPOSITION`. Nesse caso volta-se ao assunto antes da R2.

**Por testar:** tudo (o batch corre no PC do Paulo).

**Resultado (06-10):** a legenda de 2 linhas está certa, mas o Artigo veio vazio.

## Drawing Views: roupeiros, ronda R2 (2026-10-06)

Na `imos_LE_TESTES` (doc 37, secção 6c):

- legenda v2: Artigo = `IMOSARTICLEPOSITIONHIERARCHY` + uma faixa de teste provisória com
  5 campos candidatos;
- alçado: etiqueta do artigo em baixo, por fora, e cotas a 14 mm;
- portas, alçado: L × A com os campos `IMOSPART*`;
- planta: largura das portas e nome do artigo à frente;
- blocos novos `DV_Lbl_PortaLxA(_r)` e `DV_Lbl_PortaL(_r)` em `I:\Library\AttDWG`.

Guião de teste (base `imos_LE_TESTES`):

1. **Teste das casas decimais.** Com a APAGAR_15 aberta no iX CAD, escrever `LUPREC`
   (Enter), `1` (Enter) e gravar (Ctrl+S). Fechar o iX CAD.
2. Element Manager → ⟳. Depois Order Manager → **APAGAR_15** → Output Batches → só
   **`DV_Roupeiros`** → ✓.
3. Em `C:\IMOS_Output_Batches\APAGAR_15_Submittals.pdf`:
   - **Legenda:** ver se o Artigo mostra RP_A_01, e qual dos 5 campos da faixa "teste:"
     traz alguma coisa (anotar o nome e o valor);
   - **Alçado:** a etiqueta "RP_A_01 / 5000x2500x600" está por baixo do roupeiro, fora do
     desenho, com a cota 5000 mais abaixo; nas portas aparece L × A ao centro, por exemplo
     **350.8x2344.4** (se sair 350.79x2344.40, o `LUPREC` não manda);
   - **Planta:** à frente de cada porta, a largura (350.8), e mais à frente RP_A_01, ao
     meio.
4. Se as etiquetas da planta saírem rodadas ou por cima das linhas, mandar o PDF assim
   mesmo.

**Resultado (06-10):**

- a planta com as larguras das portas ficou bem;
- o Artigo e os 5 campos de teste vieram vazios: não há campo de artigo nas folhas de obra;
- as portas saem com 2 casas (350.79), mesmo com `LUPREC` 1.

## Drawing Views: roupeiros, ronda R3 (2026-10-06)

Feito na `imos_LE_TESTES` (doc 37, R3):

- "Porta"/"Gaveta" por cima das medidas das frentes;
- "5000 X 2500 X 600" na etiqueta do artigo;
- na planta, o artigo com Alt/Cmp/Prof;
- no alçado, a cota das paredes em cima;
- a legenda sem a faixa de teste e sem o Artigo.

Guião de teste (iX CAD fechado):

1. Element Manager → ⟳. Depois Order Manager → **APAGAR_15** → Output Batches → só
   **`DV_Roupeiros`** → ✓.
2. No `C:\IMOS_Output_Batches\APAGAR_15_Submittals.pdf`:
   - **Planta:**
     - à frente de cada porta, "Porta" e por baixo 350.79;
     - mais à frente, ao meio, RP_A_01 a preto e por baixo, a azul, Alt: 2500, Cmp: 5000 e
       Prof: 600;
     - a cota azul continua do lado da parede (não há opção para a pôr à frente);
   - **Alçado:**
     - a cota verde das paredes (5000 e os 50) está **em cima**;
     - por baixo do roupeiro está "RP_A_01" e "5000 X 2500 X 600";
     - nas portas, "Porta" e por baixo "350.79 X 2344.40";
     - nas frentes de gaveta, "Gaveta" + medidas;
   - **Legenda:** só 2 linhas, sem a faixa "teste:" e sem a célula Artigo.

**Resultado (06-10):** a planta ficou boa.

- No L, as medidas das portas misturam-se com o desenho.
- Na planta faltam a etiqueta "Planta 1" e os indicadores das vistas: são anotativos a 1:16
  e as folhas têm `ANNOALLVISIBLE` = 0.

## Drawing Views: roupeiros, ronda R4 (2026-10-06)

Feito (doc 37, R4):

- portas em 3 linhas por cima da porta, por fora;
- moldura com `ANNOALLVISIBLE` = 1;
- batch de comparação `DV_Roupeiros_Zoom`;
- etiqueta simples da vista (para instalar);
- regra de corte lateral `DV_Roup_Corte_Lateral`.

Guião de teste:

1. Element Manager → ⟳.
   - Em Dimensioning → Side-view section dimensioning → `DV_Desenhos` → abrir
     **`DV_Roup_Corte_Lateral`**.
   - Na linha 2 (Horizontal carcass parts) confirmar que "Height dim. – Reference" diz
     **Between parts** e que "Offset of shelf to article" diz **Yes**. Se não, corrigir aí e
     dizer-me o valor certo.
2. Com o iX CAD fechado: Order Manager → APAGAR_15 → só **`DV_Roupeiros`** → ✓.
   - **Planta:** aparecem "Planta 1" e os indicadores "1 Vista 1" / "2 Vista 2".
   - **Alçados:** por cima de cada porta, fora do desenho, "Porta / L 359.83 / A 2481.40",
     sem se sobrepor às vizinhas. As cotas verdes ficam mais acima.
3. Depois, só **`DV_Roupeiros_Zoom`** → ✓. O PDF sai em `C:\IMOS_Output_Batches\Zoom`.
   Comparar com o do passo 2: o desenho deve encher mais a folha. Ver se as cotas e as
   etiquetas continuam todas visíveis.
4. **Corte lateral à mão** (iX CAD aberto, APAGAR_15):
   - 2D Drawing views → Create Section → Section type **Side view**;
   - Dimensioning principle **`DV_Roup_Corte_Lateral`**;
   - cortar a coluna do nicho (a do meio, com gavetas e nicho).
   - Esperado: a cadeia preta da altura total e da profundidade; a magenta com rodapé,
     tampos/fundos e rodateto; a vermelha com os nichos.
5. **Etiqueta simples da vista** (opcional, numa obra nova):
   - guardar os 2 ficheiros atuais de `%APPDATA%\imos AG\iX CAD 2025\config\DrawingFlags`;
   - copiar para lá os de `C:\Pasta_Transferencia_Ourem_Calvaria\DrawingFlags_simples`;
   - numa obra **sem vistas** correr o `DV_Roupeiros`;
   - esperado: só "Vista 1" pequeno, à esquerda do desenho, ao nível do chão.

**Resultado (06-10):**

- as etiquetas e os indicadores das vistas aparecem em todas as folhas;
- o Zoom é o preferido;
- o corte lateral fica como está.

## Drawing Views: roupeiros, ronda R5 (2026-10-06)

Feito (doc 37, R5):

- `DV_Roupeiros` com Zoom extents (e o `DV_Roupeiros_Zoom` retirado);
- os valores que o Paulo afinou passam a ser os do script;
- estilos DV_AZUL/MAGENTA/PRETO/VERDE com o texto centrado, sem fundo e ao lado quando não
  cabe.

Guião de teste:

1. **Estilos na APAGAR_15** (iX CAD aberto, obra aberta):
   - abrir `C:\Pasta_Transferencia_Ourem_Calvaria\Estilos_cota_R5\comandos_estilos_APAGAR_15.txt`
     no Bloco de Notas, Ctrl+A, Ctrl+C;
   - clicar na linha de comandos do iX CAD, colar com Ctrl+V e carregar em Enter se ficar à
     espera;
   - Ctrl+S e fechar o iX CAD;
   - em alternativa, à mão no Dimension Style Manager, nos 4 estilos:
     - **Text:** Vertical Centered, Horizontal Centered, Fill None;
     - **Fit:** "Text" + "Beside the dimension line" e "Suppress arrows" desligado.
2. **Para as obras novas:** guardar o `%APPDATA%\imos AG\iX CAD 2025\config\imosBlocks.dwg`
   atual e copiar por cima o de `Estilos_cota_R5`.
3. Element Manager → ⟳ (o `DV_Roupeiros_Zoom` desaparece). Depois Order Manager →
   APAGAR_15 → só **`DV_Roupeiros`** → ✓.
4. No `C:\IMOS_Output_Batches\APAGAR_15_Submittals.pdf`:
   - o desenho enche a folha, com escalas como 1:19.9;
   - as cotas têm o texto **ao meio da linha**, sem fundo branco;
   - os "50" pequenos ficam **ao lado**, com a linha prolongada, sem linha de chamada;
   - continuam as posições afinadas pelo Paulo (portas por cima, artigo da planta no canto
     da frente).

**Resultado (06-10):** ficou bem. O DV_PRETO só mudou depois de o Paulo o mudar à mão na
obra, e o DV_VERMELHO deve ficar igual aos outros.

## Drawing Views: roupeiros, ronda R6 (2026-10-06)

Feito (doc 37, R6):

- DV_VERMELHO centrado como os outros;
- folha com a perspetiva pelo Document Manager: princípio `DV_Roup_Perspetiva` + moldura
  `DV_A3_Roup_Persp`.

Guião de teste:

1. **Estilos:**
   - na APAGAR_15 aberta, colar na linha de comandos o
     `Pasta_Transferencia\Estilos_cota_R6\comandos_estilos_APAGAR_15.txt` (Ctrl+A/Ctrl+C no
     Bloco de Notas, Ctrl+V na linha de comandos) e Ctrl+S;
   - para as obras novas, copiar o `imosBlocks.dwg` da mesma pasta para o
     `config\imosBlocks.dwg` (por cima do da R5).
2. **Perspetiva à mão** (primeiro teste):
   - Element Manager → ⟳;
   - no iX CAD com a APAGAR_15: DESIGN → separador Output → Document Manager → escolher
     **`DV_Roup_Perspetiva`** → Apply → selecionar tudo (`ALL` + Enter);
   - esperado em `I:\Factory\Imorder\APAGAR_15\DOC\`: `DV_Perspetiva_3D` em PDF e em DWG,
     com o L inteiro em 3D (Realistic), na folha A3 com a legenda de 2 linhas.
3. **Se estiver bem:** Element Manager → Output batches → `DV_Desenhos` → **`DV_Roupeiros`**
   → acrescentar a saída **"Document Manager 2.0"** com o princípio `DV_Roup_Perspetiva`
   → Guardar. Depois disso eu leio o tipo na base e passo-o para o script.

**Resultado (06-10):** a perspetiva saiu (`APAGAR_15\DOC\DV_Perspetiva_3D`), mas o Paulo
vai usar os Document Managers que já tem. O `DV_Roup_Perspetiva` e a moldura
`DV_A3_Roup_Persp` foram retirados da base, e o `.dwt` da pasta TEMP do iX CAD foi apagado,
tudo a pedido dele. Os estilos (passo 1) continuam por testar.

## Drawing Views: textos e cotas à mão, ronda R7 (2026-10-06)

Feito (doc 37, R7):

- estilos de texto anotativos `DV_Texto` (2,5 mm de papel, camada preta) e `DV_Titulo` (5 mm,
  camada azul);
- Model a 1:20;
- cota atual `DV_VERMELHO`;
- comandos para a APAGAR_15 e um `IMOS.dwt` candidato em `Pasta_Transferencia\Estilos_R7`.

Guião de teste (A primeiro; B só se A ficar bem):

**A. Na APAGAR_15**

0. **imosBlocks:** copiar `Pasta_Transferencia\Estilos_cota_R6\imosBlocks.dwg` para
   `%APPDATA%\imos AG\iX CAD 2025\config\` (por cima do de 05-10). O que está em
   `config\DrawingFlags\` não é usado.
1. **Colar os comandos:**
   - na APAGAR_15, no separador **Model**, abrir
     `Pasta_Transferencia\Estilos_R7\comandos_R7_APAGAR_15.txt` no Bloco de Notas;
   - Ctrl+A, Ctrl+C, clicar na linha de comandos, Ctrl+V e Enter.
   - Esperado:
     - nenhum "Unknown command";
     - a última linha diz que o `DV_Texto` é o estilo de texto atual;
     - na barra de baixo, a escala de anotação está em 1:20;
     - a lista de cotas mostra `DV_VERMELHO`.
2. **Texto novo:**
   - camada `DV_Texto`, MTEXT "TESTE TEXTO". Esperado: no Model com ~50 mm de altura, preto
     na folha;
   - camada `DV_Titulo`, estilo `DV_Titulo`, "TESTE TITULO". Esperado: ~100 mm, azul.
3. **Cota à mão** (DIMLINEAR numa porta). Esperado: vermelha, número no meio da linha, sem
   linha de chamada.
4. **Textos que já existem:** selecionar o título `_01_26_JF_VIVA_()` → Propriedades → Estilo
   `DV_Titulo`. Se a "Altura do texto no papel" não ficar 5, escrever 5. Fazer o mesmo à lista
   de materiais com `DV_Texto` e 2,5.
5. **Layouts `1` e `1 (2)`** (ou voltar a correr o teu Document Manager):
   - esperado: o texto com a altura das letras da legenda (2,5 mm), o título com o dobro, e
     as cotas pequenas como as automáticas;
   - imprimir o PDF e ver se se lê bem;
   - no `1 (2)` (escala 1:25,6, fora da lista) podem sair um pouco mais pequenos: dizer-me.
6. Ctrl+S.

**B. Obras novas** (só depois de A):

7. Abrir no iX CAD o `Pasta_Transferencia\Estilos_R7\IMOS.dwt` (Abrir → tipo .dwt). Os 2
   textos aparecem enormes: é de propósito. Fazer o passo 4 nesses 2 textos e Ctrl+S.
8. Fechar o iX CAD. Em `config\`, mudar o nome do `IMOS.dwt` para `IMOS_antes_R7.dwt` e copiar
   para lá o novo.
9. Criar uma obra de teste (APAGAR_16). Esperado:
   - estilo de texto `DV_Texto`, cota `DV_VERMELHO` e escala 1:20 já escolhidos;
   - os 2 textos com tamanho normal no Model e no layout `1`.

**Resultado (06-10):**
- o imosBlocks da R6 está no `config\`;
- o Paulo instalou o IMOS.dwt da R7;
- o `-STYLE` não existe no iX CAD: os estilos de texto só vêm pelo IMOS.dwt;
- pediu que o `IMOS_Text35` (a cota que usa no Model) fique à escala dos DV_* → R8.

## Drawing Views: IMOS_Text35 e IMOS.dwt para o ciclo completo, ronda R8 (2026-10-06)

Feito (doc 37, R8):

- cota `IMOS_Text35` com as medidas e o comportamento dos `DV_*`. Continua vermelha, com setas
  e 1 casa decimal, e é a cota atual;
- os 2 textos do Model do IMOS.dwt com 5 e 2,5 mm de papel;
- ficheiros em `Pasta_Transferencia\Estilos_R8`.

Guião de teste (ciclo completo):

1. Fechar o iX CAD. Em `%APPDATA%\imos AG\iX CAD 2025\config\`, mudar o nome do `IMOS.dwt`
   (o da R7) para `IMOS_R7.dwt` e copiar para lá o `Estilos_R8\IMOS.dwt`.
2. Abrir o iX CAD e criar uma **obra nova**. Esperado no Model:
   - o título azul e a lista de materiais do tamanho de sempre (~100 e ~50 mm);
   - a escala de anotação em 1:20;
   - o estilo de texto `DV_Texto`;
   - a cota `IMOS_Text35`.
3. Desenhar os roupeiros como sempre. Cotar à mão com o `IMOS_Text35` (esperado: vermelha,
   texto ~50 mm no Model, setas, número ao meio, sem linha de chamada). Escrever com MTEXT e
   `DV_Texto` / `DV_Titulo` (camadas `DV_Texto` / `DV_Titulo` para a cor).
4. Correr o batch `DV_Roupeiros`, o teu Document Manager e os layouts `1`. Esperado: em todas
   as folhas e no PDF:
   - texto e cotas à mão com a altura das letras da legenda (~2,5 mm);
   - o título com 5 mm;
   - nada gigante.
5. Dizer o que ficou grande, pequeno ou fora do sítio, com o nome do layout.

**Resultado (06-10):**
- na APAGAR_16 o PDF do batch saiu vazio e a escala da legenda era 1:447154471544715520;
- causa: a etiqueta simples da vista (R4) não tem geometria → R9;
- o Paulo vai passar ele as DV_* para a `imos_LE` pelo Element Manager.

## Drawing Views: PDF vazio corrigido, ronda R9 (2026-10-06)

Feito (doc 37, R9): os blocos simples `imosLabelElevation` e `imosLabelPlanview` levam 2
pontos na camada Defpoints, que não imprime. Assim o iMos volta a pô-los junto à vista e não
em 1E20.

Guião de teste:

1. Fechar o iX CAD. Copiar os 2 DWG de `Pasta_Transferencia\DrawingFlags_simples_v2` para
   `%APPDATA%\imos AG\iX CAD 2025\config\DrawingFlags\` (por cima dos da R4).
2. **APAGAR_16:**
   - abrir;
   - no Bloco de Notas, abrir `1_redefinir_alcado.txt`, Ctrl+A, Ctrl+C;
   - Ctrl+V na linha de comandos e Enter. Quando pedir o ponto de inserção, carregar **Esc**;
   - fazer o mesmo com `2_redefinir_planta.txt`;
   - correr outra vez o batch `DV_Roupeiros`.
3. Esperado:
   - o PDF com a planta e os alçados;
   - na legenda, a escala com 1 casa decimal (ex.: `1:19.6`);
   - o "Planta 1" / "Vista 1" junto ao desenho.
4. (Alternativa ao passo 2) criar uma obra nova, que já apanha os blocos novos.

**Resultado (06-10):** na APAGAR_17 o PDF saiu certo (3 folhas, escala 1:17.6 / 1:14.2 /
1:20.4). O R9 está no GitHub.

## Drawing Views: etiquetas livres das cotas e desenho maior, ronda R10 (2026-10-06)

Feito (doc 37, R10):

- a 1.ª cota do alçado dos roupeiros passa de 9 para 14 mm (aplicado na `imos_LE_TESTES`);
- os pontos invisíveis da etiqueta da vista ficam só à volta do texto (`DrawingFlags_simples_v3`).

Guião de teste:

1. Fechar o iX CAD. Copiar os 2 DWG de `Pasta_Transferencia\DrawingFlags_simples_v3` para
   `config\DrawingFlags\` (por cima dos da v2).
2. Abrir a APAGAR_17:
   - colar `1_redefinir_alcado.txt` na linha de comandos, Enter e **Esc** no ponto;
   - o mesmo com `2_redefinir_planta.txt`;
   - Element Manager → ⟳ (para ler a cota a 14).
3. Correr o batch `DV_Roupeiros` e comparar com o PDF anterior. Esperado:
   - nos alçados, a cota verde de cima fica acima das etiquetas "Porta";
   - o "RP_A_0x / L X A X P" fica entre o desenho e a cota azul, sem lhe tocar;
   - menos espaço vazio à esquerda e em baixo; o desenho um pouco maior;
   - o "Planta 1" / "Vista 1" junto ao desenho.
4. **Se a etiqueta da vista aparecer num sítio estranho:** voltar a copiar os da v2 e dizer-me.
5. Se ficar bem: na `imos_LE`, Element Manager → cotagem do alçado `DV_Roup_Alcado` →
   distância da 1.ª cota = 14. Copiar os DWG da v3 para o `DrawingFlags` dos outros PCs.
6. **Cotas com o texto por cima e linha de chamada** (pedido do Paulo durante a R10):
   - com o iX CAD fechado, em `config\`, mudar o nome do `IMOS.dwt` para `IMOS_1456.dwt` e
     copiar os `Pasta_Transferencia\Estilos_R10\IMOS.dwt` e `imosBlocks.dwg` para lá;
   - numa obra nova, cotar uma porta estreita com o `DV_VERMELHO`. Esperado: o número sai por
     cima, com linha de chamada; o `IMOS_Text35` faz o mesmo;
   - nas obras já abertas (APAGAR_17) os estilos são os da obra: ficam como os deixaste.

**Resultado (06-10, APAGAR_01):** as etiquetas já não tocam nas cotas. Pedidos novos → R11.

## Drawing Views: "Vista 1" abaixo do chão e portas "A / L", ronda R11 (2026-10-06)

Feito (doc 37, R11):

- a etiqueta "Vista 1" / "Vista 2" dos alçados desce para baixo da linha do chão
  (`DrawingFlags_simples_v4`);
- portas e gavetas com "Porta / A / L" (altura em cima): blocos `DV_Lbl_Porta_AL` /
  `DV_Lbl_Gaveta_AL` na biblioteca, aplicado na `imos_LE_TESTES`.

Guião de teste:

1. Fechar o iX CAD. Copiar os 2 DWG de `Pasta_Transferencia\DrawingFlags_simples_v4` para
   `config\DrawingFlags\`.
2. Abrir a APAGAR_01 (já com o 3.º roupeiro de 2798):
   - colar `1_redefinir_alcado.txt` na linha de comandos, Enter e **Esc** no ponto;
   - colar `2_redefinir_planta.txt` da mesma maneira;
   - Element Manager → ⟳.
3. Correr o batch `DV_Roupeiros`. Esperado:
   - nos alçados, o "Vista 1" fica por baixo da linha do chão, sem tocar nas cotas da
     esquerda;
   - as portas mostram "Porta", por baixo "A 2561.40" e por baixo "L 412.33".
4. Se ficar bem, na `imos_LE`:
   - Element Manager → etiquetas `DV_Roup_Alcado_Etiquetas` → bloco das portas
     `DV_Lbl_Porta_AL` e das gavetas `DV_Lbl_Gaveta_AL`;
   - copiar os DWG da v4 para o `DrawingFlags` dos outros PCs.

## Drawing Views: nome do artigo a vermelho, ronda R12 (2026-10-06)

Feito (doc 37, R12):

- na planta, o nome do artigo e o valor do Cmp saem a vermelho;
- no alçado, o nome do artigo sai a vermelho e as medidas a azul;
- a posição do artigo de chão que o Paulo afinou (700 / −300) passou para o script.

Guião de teste:

1. Element Manager → ⟳.
2. Na APAGAR_01, correr o batch `DV_Roupeiros`. Esperado:
   - na planta, "RP_A_01(b)" a vermelho, por baixo "Alt:" azul, "Cmp: 2585" com o número a
     vermelho e "Prof:" azul, no sítio onde o puseste;
   - nos alçados, "RP_A_01(a)" a vermelho e "2435 X 2592 X 600" a azul.
3. Se ficar bem, na `imos_LE`, Element Manager:
   - em `DV_Roup_Planta_Etiquetas`, os blocos `DV_Lbl_Artigo_Planta_NV`;
   - em `DV_Roup_Alcado_Etiquetas`, o bloco `DV_Lbl_Artigo_Azul_NV`.

**Correção (06-10):** o artigo fica TODO a vermelho:
- alçado com o `DV_Lbl_Artigo_Verm`;
- planta com o `DV_Lbl_Artigo_Planta_Verm`;
- os `_NV` saíram.

## Drawing Views: DV_Roupeiros na imos_LE e limpeza da AttDWG (2026-10-06)

Feito (doc 37):

- o batch `DV_Roupeiros` e tudo o que usa foi copiado da `imos_LE_TESTES` para a **`imos_LE`**
  (`publicar_roupeiros.py`), conferido; o `DV_Desenhos_Obra` e as regras dele não foram;
- 28 blocos `DV_*` sem uso saíram de `I:\Library\AttDWG` para
  `Pasta_Transferencia\AttDWG_DV_sem_uso`.

Guião de teste:

1. Element Manager **ligado à `imos_LE`** → ⟳. Em Output Batches → `DV_Desenhos` deve
   aparecer só o `DV_Roupeiros`. As regras `DV_Roup_*`, a moldura `DV_A3_Roupeiro` e as
   condições `DV_*` devem estar nas pastas `DV_Desenhos`.
2. Numa obra (base oficial), correr o batch `DV_Roupeiros`. Esperado: o mesmo PDF que na
   base de testes, com o artigo todo a vermelho na planta e nos alçados.
3. Nos outros PCs que vão usar: copiar para `config\` o `IMOS.dwt` e o `imosBlocks.dwg`
   (`Estilos_R10`), e para `config\DrawingFlags` os DWG de `DrawingFlags_simples_v4`.
4. Se em uns dias nada se queixar da falta de um bloco, apagar a pasta `AttDWG_DV_sem_uso`.

## Lista Material: ResumoOrlas com REF_CLIENTE em F e «stock/enc» (2026-10-07)

O Paulo mudou o separador `ResumoOrlas` do modelo `Lista_Material_IMOS_MARTELO.xltm`. Os
títulos da tabela passaram a ser `stock/enc`, `Larg X Esp` e `Obs.`, e o REF_CLIENTE
passou para F1. A macro que gera o resumo tinha os títulos antigos escritos no código.

Feito:

- a macro `modResumoOrlas` passou a ter fonte no repositório (`scripts/vba/modResumoOrlas.bas`),
  e o `atualizar_macros_modelo_lista_material.py` passou a escrevê-la no modelo;
- REF_CLIENTE em **F1**, valor em **F2**. Numa obra antiga com o REF_CLIENTE em H1/H2,
  o H1/H2 é limpo;
- títulos: `Material | Nome_Orlas | ML_QT | stock/enc | Marca / Ref. | Larg X Esp | ML | Obs.`,
  com as larguras do modelo;
- cada linha com orla leva `stock/enc`. O que foi escrito à mão nessa coluna fica, menos o
  antigo `enc`, que passa a `stock/enc`. As obras antigas continuam a ser lidas pelos
  títulos antigos (`enc`, `Entrada Orlas`);
- a análise de custo do Martelo lê o `Larg X Esp` sem olhar a maiúsculas. Sem isto, as
  orlas das obras novas ficavam sem largura;
- foi escrito no modelo do servidor a 07-10 às 18:04, com cópia
  `Lista_Material_IMOS_MARTELO_backup_20261007_180455.xltm`. Numa cópia, o projeto VBA
  compila sem erros. Numa cópia da 1699, a macro deu as mesmas 6 linhas e os mesmos ML.

Guião de teste:

1. Produção → selecionar uma obra nova → **«Lista Material_IMOS»**, que cria o Excel a partir
   do modelo. Importar o IMOS como de costume, até a `LISTAGEM_CUT_RITE` ter peças com orlas.
2. No Excel, separador **LISTAGEM_CUT_RITE** → botão **«Calculo Orlas»**. Esperado no
   separador **ResumoOrlas**:
   - B1 «Cliente», E1 «ENC_PHC», **F1 «REF_CLIENTE»**; na linha 2 o cliente, a encomenda e
     **o REF_CLIENTE em F2**. H1/H2 vazios;
   - títulos da tabela na linha 3: `Material | Nome_Orlas | ML_QT | stock/enc | Marca / Ref. |
     Larg X Esp | ML | Obs.`;
   - em **todas** as linhas com orlas, a coluna E diz **`stock/enc`**; `Larg X Esp` no formato
     `22 x 1.0`.
3. Na coluna E, trocar uma linha para `stock`, escrever algo em `Obs.` e carregar outra vez
   em «Calculo Orlas». Esperado: o `stock` e a observação continuam lá.
4. Numa obra antiga (Excel criado antes de 07-10), nada muda: a macro está dentro de cada
   Excel e só as obras criadas a partir de agora têm a nova.
5. Gravar o Excel. Produção → a mesma obra → «Lista Material_IMOS» → janela «Análise da Lista
   Material» → separador **«Custo de produção (parcial)»**. Esperado: as orlas do
   ResumoOrlas aparecem com a largura (22, 25…), como antes.

## Enviar CUT-RITE: sem o Excel escondido (2026-10-07)

O envio para o CUT-RITE lê a `LISTAGEM_CUT_RITE` diretamente do ficheiro. Se essa leitura
falhasse, havia um plano B, trazido do V2: abrir o Excel escondido e correr as macros
`GERAR_ResumoOrlas` e `Copia_Listagem_Software_Cut_Rite`. As duas abrem mensagens, e a
segunda abre sempre «Listagem copiada para a memória!». Com o Excel invisível, ninguém
carregava no OK e o envio ficava parado no passo «A preparar a listagem CUT-RITE».

Feito:

- o plano B saiu (`cutrite_service.py`). Se o Martelo não conseguir ler a Lista Material,
  aparece uma janela «Enviar CUT-RITE» com o motivo e a linha de estado diz «Falha ao enviar
  para o CUT-RITE.». O motivo é «Grave e feche o Excel da obra e tente outra vez», com o
  caminho do ficheiro e o detalhe do erro;
- se faltar o separador `LISTAGEM_CUT_RITE`, a mensagem diz isso mesmo;
- o caso normal não muda. A 1715 lê-se bem (32 linhas), mesmo com o Excel aberto.

Guião de teste:

1. Produção → selecionar a obra 1715 → preencher o «Nome Plano CUT-RITE» → botão
   **«CUT-RITE»**. Esperado: igual a antes, o CUT-RITE recebe as peças.
2. Teste do erro (numa cópia, nunca na obra real): copiar uma Lista Material para uma obra
   de teste, abri-la no Bloco de Notas, apagar tudo e gravar. Produção → essa obra → botão
   **«CUT-RITE»**. Esperado: em poucos segundos, a janela «Enviar CUT-RITE» com «Nao
   consegui ler a Lista Material para o CUT-RITE. Grave e feche o Excel da obra…» e o
   caminho do ficheiro. O envio não fica parado e o Excel não aparece nos processos do
   Gestor de Tarefas.

## Produção: campo «Pesquisar» mais certeiro (2026-10-08)

O Paulo achava que a pesquisa da Produção nem sempre devolvia obras ligadas ao que escrevia.
Testado com as 623 obras da base dev, havia três problemas, e nenhum era a «consola» do print:

- **os sinónimos do «meu perfil» estragavam tudo.** Cada palavra de uma linha do perfil valia
  por todas as outras, incluindo «a», «de», «na». A linha «roupeiro; abrir; correr; …;
  cozinha | termos de móvel/artigo que uso na pesquisa» fazia `roupeiro`, `cozinha`, `cama`
  e `mesa` devolverem **as 623 obras**; «a Viva … | MÓVEIS J.F. VIVA» fazia `viva` apanhar
  qualquer obra com a palavra «a» ou de outro cliente «Móveis…» (372 obras);
- **as frases não funcionavam:** `obras da viva com consola` obrigava cada obra a ter «obras»,
  «da» e «com», e dava 0;
- **o pedaço de palavra apanhava o meio das palavras:** `laca` encontrava «contraplacado» e
  «instalacao», `porta` encontrava «transportadora», `aro` encontrava «claro».

A 1418 do print estava certa: «consola» está na **descrição do orçamento** («…1 roupeiro
consola 2 gavetas…»), que a pesquisa lê mas o detalhe da obra não mostra.

Feito (motor partilhado com os Orçamentos e o assistente):

- sinónimos frase a frase: «guarda-fatos» é uma forma com duas palavras, que só conta se a
  obra tiver as duas; «a Viva» é «viva». Linhas com mais de 6 formas são listas de
  vocabulário e já não contam como sinónimos (no perfil dele: a lista de 19 termos de
  móveis, «lacar; verniz; …; velatura» e «Guarnições…»);
- palavras de ligação e pedidos («de», «da», «com», «obras», «quero ver», «mostra»,
  «cliente»…) são ignoradas na pesquisa;
- pedaço de palavra só pelo **início** («roup» → roupeiro, «cancu» → cancun); os números
  continuam a valer pelo meio («877» → 260877);
- letras coladas a números separam-se («4gavetas» → «4 gavetas»);
- o `%` já funcionava e continua: `consola%gavetas` = as duas palavras, em qualquer campo;
- a linha de estado diz **onde** a pesquisa encontrou a obra selecionada: «Pesquisa
  encontrada em: Descrição produção, Notas 1.»;
- **a pesquisa deixou de ler a descrição do orçamento** (decisão do Paulo, 08-10): procura
  só nos dados da produção, os campos que se veem no menu. Com isso a 1418 sai de
  `consola`.

Antes → depois (base dev, 623 obras): `roupeiro` 623 → 294; `cozinha` 623 → 136; `viva`
372 → 132; `laca` 233 → 163; `obras da viva com consola` 0 → 8; `consola` 11 → 10 (a 1418 saiu).

Guião de teste (olhar para a etiqueta: BASE REAL ou dev):

1. Produção → «Limpar filtros» → desligar «As minhas obras» → Pesquisar: `cozinha`.
   Esperado: só obras com «cozinha» num campo; já não aparecem as obras todas (rodapé
   «N de 755» bem abaixo de 755).
2. Pesquisar: `consola`. Esperado: a **1418 já não aparece** (só tinha «consola» na
   descrição do orçamento).
3. Clicar na **0837**. Esperado: na linha de estado, «Pesquisa encontrada em: Descrição
   produção, Notas 1.».
4. Pesquisar: `obras da viva com consola`. Esperado: as obras da J.F. Viva do passo 2
   (antes dava 0).
5. Pesquisar: `consola%gavetas`. Esperado: só obras que têm as duas palavras.
6. Pesquisar: `laca`. Esperado: obras com lacagem/lacado/lacar; nenhuma só por
   «contraplacado».
7. Pesquisar: `viva`. Esperado: obras da J.F. Viva (ou com «viva» escrito); já não
   aparecem obras de outros clientes «Móveis…».
8. Apagar a pesquisa (✕). Esperado: a linha de estado deixa de dizer «Pesquisa encontrada
   em».

## Pesquisa IA copiável, Subsídio de Alimentação e menu IMOS IX (2026-10-10)

Três pedidos do Paulo no mesmo dia (maqueta do IMOS IX aprovada antes de programar).

**1. Pesquisa IA: copiar texto.** Nas tabelas só de leitura não dava para apanhar um
pedaço de texto: a linha inteira ficava selecionada e o Ctrl+C levava só a célula onde se
tinha clicado, sem se ver qual. Agora (ajudante `app/ui/helpers/tabela_copiavel.py`, nas 6
tabelas da Pesquisa IA): seleção célula a célula como no Excel; Ctrl+C copia o que está
selecionado (várias células saem com tabulações, prontas para o Excel); botão direito com
«Copiar», «Copiar a linha inteira» e «Copiar a tabela toda (com títulos)»; e a barra
**«Texto da célula:»** por cima dos separadores mostra o texto completo da célula escolhida,
para selecionar só uma parte (como a barra de fórmulas do Excel). A resposta IA também se
seleciona com Shift+setas.

**2. Registo de Horas: Subsídio de Alimentação.** Regra (respostas dele de 10-10): só nos
dias fora do horário normal — sábado, domingo, feriado e dia de férias trabalhado —,
**1,25 € por hora inteira**, máximo **10 € por dia**; dias úteis não contam, mesmo com horas
extra. Coluna «Subs. Alimentação» no ecrã, no PDF e na janela de envio; linha própria no
resumo e no email do dia 2, à parte do total de horas. Doc 36.

**3. Menu IMOS IX › Traduções do iX.** Substitui o `AtualizaIMOSMsgPTG.exe` (feito para o
iX 2023): lê o Excel `I:\imos_msg.xlsx`, compara com o `imos.msg` do iX deste PC, pede para
fechar o iX CAD e o Organizer, faz **sempre a cópia** do `imos.msg` antes de gravar e mostra
linha a linha o que mudou. Aviso ao entrar no Martelo quando o PC tem traduções por aplicar.
Acesso novo «IMOS IX», que nasce desligado. Doc 38.

Guião de teste (a app corre do `main` da pasta principal; reiniciar o Martelo):

*Pesquisa IA*

1. Orçamentos › Pesquisa IA → Pesquisar: `dobradiça x91` → separador **PHC**.
2. Clicar na célula «DOBRADIÇA 90ºC/ FECHO SUAVE X91». Esperado: a barra «Texto da célula:»
   mostra o texto completo.
3. Na barra, arrastar o rato só sobre `FECHO SUAVE` → Ctrl+C → colar no Bloco de Notas.
   Esperado: `FECHO SUAVE`.
4. Na tabela, clicar em `FF00495` e Ctrl+C → colar. Esperado: só `FF00495`.
5. Arrastar de `FF00495` até ao preço da mesma linha → Ctrl+C → colar no Excel. Esperado:
   cada valor na sua coluna.
6. Botão direito numa linha → «Copiar a tabela toda (com títulos)» → colar no Excel.
   Esperado: títulos na 1.ª linha e todos os artigos por baixo.
7. Na Resposta IA (à direita), selecionar uma frase → Ctrl+C → colar. Esperado: a frase.

*Registo de Horas* (fazer num mês de teste ou apagar os dias depois)

8. Registo de Horas → duplo clique num **sábado** → 4 horas → Guardar. Esperado: coluna
   «Subs. Alimentação» = `5,00 €`.
9. Duplo clique num **domingo** → 9 horas. Esperado: `10,00 €` (máximo do dia).
10. Um dia de **Férias** com 2h30. Esperado: `2,50 €` (só horas inteiras).
11. Um dia útil com 8h–17h + 20h–23h. Esperado: coluna vazia (dias úteis não contam).
12. No «Resumo do mês», a linha a ocre «Subsídio de alimentação» = soma dos dias
    (17,50 € com os passos 8–10).
13. «Folha em PDF». Esperado: coluna «Subs. Alim.» e a linha do subsídio no fim do resumo.
14. «Enviar à contabilidade…» (só ver, Cancelar). Esperado: coluna nova na tabela, linha no
    resumo e «• Subsídio de alimentação: …» no texto do email.

*Menu IMOS IX*

15. Entrar como **admin** → Configurações → Utilizadores e Acessos → coluna **«IMOS IX»** →
    marcar para o `paulo` → Guardar. Sair e entrar como `paulo`.
16. Esperado: na barra da esquerda, **IMOS IX** com o logótipo do iX, entre Produção e
    Registo de Horas.
17. IMOS IX → separador «Traduções do iX». Esperado: «Ficheiro do iX» =
    `C:\Program Files\imos AG\iX CAD 2025\BIN\MSG\imos.msg`, «✓ Encontrado: iX CAD 2025»;
    fichas do iX CAD/Organizer (aberto/fechado, conforme estiverem); «Excel: 19
    traduções»; «19 já certas» — este PC já tem tudo aplicado; linha de estado «Tudo
    certo…».
18. Testar com o ficheiro de teste (cópia de julho, em
    `Documentos\Teste_traducoes_iX\imos.msg`): «Procurar…» → escolher esse ficheiro.
    Esperado: «✓ Escolhido à mão neste PC», **4 por aplicar** em cima da tabela (1220
    Descrição → Materiais Usados, 6128, 10279, 18012) e o botão «Encontrar sozinho».
19. Com o iX CAD aberto → «Aplicar traduções». Esperado: janela «Feche o iX CAD e o iX
    Organizer» com «aberto»; «Continuar» desligado. Fechar os dois programas. Esperado: a
    janela passa sozinha a «fechado» e «Continuar» liga-se → Continuar.
20. Esperado: janela com o progresso: cópia `imos.msg.copia_2026-10-10_…`, as 4 linhas
    «antes → depois», «gravado e confirmado», resumo «4 alterada(s) · 15 já estavam
    certas». «Abrir pasta da cópia» abre a pasta de teste com a cópia.
21. Fechar. Esperado: «0 por aplicar», linha de estado «4 tradução(ões) aplicada(s)…».
    Carregar outra vez em «Aplicar traduções». Esperado: «Nada para aplicar» e nenhuma
    cópia nova.
22. «Repor uma cópia…» → escolher a cópia de hoje → Repor esta cópia → Sim. Esperado:
    volta a «4 por aplicar»; na pasta ficam as duas cópias (nenhuma apagada).
23. «Encontrar sozinho». Esperado: volta ao ficheiro do iX CAD 2025, «19 já certas».
24. Desmarcar «Avisar ao entrar no Martelo…». Esperado: linha de estado «Aviso
    desligado…». Voltar a marcar.

**Testado pelo Paulo a 10-10-2026** (IMOS IX na base real): «ficou muito bom e prático».
Pediu a seguir:

### Larguras das colunas nas Traduções do iX + ícones em todos os menus (2026-10-10)

- **Traduções do iX:** as 4 colunas ajustam-se arrastando a divisão dos títulos e a largura
  fica guardada por utilizador neste PC (o mesmo `ligar_persistencia_larguras` dos outros
  menus, chave `imos_ix_traducoes`). A coluna «Estado» enche o resto da tabela.
- **Barra lateral:** cada menu tem o seu ícone, como o do IMOS IX («fica mais fácil de
  identificar»). 14 ícones novos `app/ui/assets/icons/nav_*.svg`, no estilo dos botões
  (bege e castanho); a Ajuda usa o `ajuda.svg` que já existia; o IMOS IX mantém o logótipo
  do iX. Na linha selecionada o ícone vai sobre um quadradinho bege (os traços castanhos
  desapareciam no castanho da seleção). Lista em `MainWindow._ICONES_NAV`; um teste obriga
  a que todos os menus tenham ícone.

Guião de teste (reiniciar o Martelo):

1. Olhar para a barra da esquerda. Esperado: todos os menus com ícone — casa (Início),
   ponto de interrogação (Ajuda), folha com € (Orçamentos), barras (Dashboard), folha com
   lupa (Auditoria de Custeio), caixa (Arquivo V2), placas empilhadas (Matérias-Primas),
   lupa com estrela (Pesquisa IA), duas pessoas (Clientes), fábrica (Produção), caixa de
   encomenda (Encomendas PHC), barras das fases (Ponto Situação), triângulo de aviso
   (Ocorrências), logótipo do iX (IMOS IX), relógio (Registo de Horas), roda dentada
   (Configurações).
2. Clicar em Registo de Horas. Esperado: na linha selecionada (castanha) o relógio vê-se
   sobre um quadradinho bege.
3. IMOS IX › Traduções do iX: arrastar a divisão entre «Texto que o iX mostra agora» e
   «Texto da empresa (Excel)» para a esquerda. Esperado: a coluna estreita, as outras
   ajustam-se e «Estado» enche o fim.
4. Ir a outro menu, sair do Martelo e voltar a entrar como `paulo` → IMOS IX. Esperado: as
   larguras ficaram como as deixou.
5. Entrar com outra conta no mesmo PC. Esperado: essa conta vê as larguras de origem.

## Orçamentos: descrições pré-definidas no Info 1 e Info 2 (2026-10-11)

O Paulo usa o Info 1 e o Info 2 do orçamento para indicar os materiais («INTERIORES MLM
LINHO CANCUN», «FRENTES MDF BRANCO») e escrevia-os à mão. Esses textos já existem nas
**descrições pré-definidas** que se usam na descrição dos items; pediu para ter o mesmo
menu nos orçamentos.

Feito:

- **Novo Orçamento** e **Editar Orçamento**: botão **«Descrições…»** à direita do Info 1 e do
  Info 2. Abre o mesmo menu dos items (a mesma lista, de cada utilizador) e acrescenta no
  fim do campo as descrições marcadas, **uma por linha e sem o «-»/«*» nem a tabulação**
  que levam na descrição do item. Uma linha que o campo já tenha não se repete. As duas
  janelas ficaram um pouco mais largas (540) para o botão não roubar espaço ao texto.
- **Menu das descrições:** o título diz para onde vai o texto («Descrições pré-definidas →
  Info 1»; nos items «→ Descrição»); linha de estado nova em baixo («Marque…» / «2
  descrições marcadas — «Inserir» acrescenta-as ao campo «Info 1».»); dicas em todos os
  botões; e **adicionar ou editar uma descrição já não tira as marcas** às que estavam
  marcadas (antes, tinha de se marcar tudo outra vez).
- Componente partilhado: `app/ui/widgets/campo_descricoes_predefinidas.py`. Testes em
  `tests/test_descricoes_predefinidas_orcamento.py`.

O texto entra tal como está na lista (não passa a maiúsculas).

Guião de teste (reiniciar o Martelo; nada disto grava sem carregar em Guardar):

1. Orçamentos → **«Novo Orçamento»**. Esperado: ao lado do **Info 1** e do **Info 2** um
   botão «Descrições…»; com o rato por cima aparece a dica «…acrescentar as que marcar ao
   Info 1…».
2. «Descrições…» do **Info 1**. Esperado: janela «Descrições pré-definidas → Info 1» com a
   mesma lista do Novo Item; em baixo, a castanho: «Marque na caixa à esquerda as
   descrições a inserir no campo «Info 1» e carregue em «Inserir».»
3. Marcar «Interiores AGL MLM LINHO CANCUN 10/16/19mm» e «Frentes MDF HIDROFUGO BRANCO
   B3002/MA_19MM». Esperado: linha a verde «2 descrições marcadas — «Inserir» acrescenta-as
   ao campo «Info 1».»
4. «Inserir». Esperado: Info 1 com as duas linhas, sem «-» à frente e sem espaço no início;
   Info 2 continua vazio.
5. «Descrições…» do Info 1 outra vez → marcar «Interiores AGL MLM LINHO CANCUN…» (a mesma)
   e «Puxador Fresado 'J'» → Inserir. Esperado: só entra «Puxador Fresado 'J'» numa linha
   nova; a dos interiores não fica repetida.
6. «Descrições…» do **Info 2** → marcar «Dobradiças Blum» → «Adicionar» → texto `TESTE
   INFO` → OK. Esperado: `- TESTE INFO` aparece na lista e «Dobradiças Blum» **continua
   marcada**; linha de estado «1 descrição marcada…». (Depois pode selecionar `TESTE INFO`
   e «Eliminar», se não a quiser.) «Inserir». Esperado: Info 2 = «Dobradiças Blum».
7. **Cancelar** o Novo Orçamento (para não gastar um número de orçamento).
8. Na lista, selecionar o **261023** (J.F. Viva) → «Editar Orçamento». Esperado: o mesmo
   botão ao lado do Info 1 e do Info 2; o Info 1 tem o texto que já lá estava.
9. «Descrições…» do Info 1 → marcar «Frentes AGL MLM BRANCO B3768/SC 19mm» → Inserir.
   Esperado: a linha entra no fim, por baixo do texto que já existia. Cancelar (ou Guardar,
   se quiser ficar com ela).
10. Abrir um orçamento → separador **Items** → «Novo Item» → «Descrições pré-definidas…».
    Esperado: título «Descrições pré-definidas → Descrição»; ao inserir, a descrição do item
    continua como antes (com a tabulação e o «-» à frente).

## Orçamentos antigos: entrar no V3 com a versão seguinte (2026-10-19)

Caso real: o **260186 (INNERE)** já tem as versões **01 a 05** no servidor, feitas no
Martelo V2. Registado no V3 como «Orçamento antigo», entrava sempre como **01**, e os
ficheiros gravavam soltos na pasta escolhida, ao lado das pastas do V2. Na base real havia
6 antigos registados, cada um à sua maneira: uns com a pasta-mãe, outros com a pasta de uma
versão (`260427_PACE/03`, `260851_BRUNO_OLIVEIRA/02`) para contornar o problema.

Decisões do Paulo (19-10-2026):

- A versão do V2 que já tem ficheiros **não se reaproveita**. Cria-se a versão seguinte e
  copiam-se à mão os ficheiros que interessarem.
- **Os 6 antigos já registados ficam como estão**, incluindo o 260466 ligado à pasta
  `260446_JF_VIVA` (gralha antiga, fica assim).

Feito:

- **Novo Orçamento → «Orçamento antigo»**: linha nova **«Versão»** por baixo da pasta. Ao
  escolher a pasta, o Martelo lê as subpastas `01`…`05` e propõe a seguinte (**06**). Ao lado
  mostra onde vai gravar («grava em 260186_INNERE/06 · no servidor: 01, 02, 03, 04, 05»).
- Quem escolher a pasta **de uma versão** (`…/260186_INNERE/05`) fica com a **pasta-mãe**; o
  Martelo avisa por baixo do caminho.
- O **N.º orçamento** preenche-se sozinho a partir do nome da pasta, se estiver vazio.
- **Guardar** recusa uma versão cuja pasta já existe **com ficheiros** e diz qual é a
  seguinte. Se o número escrito não bater com o da pasta (o caso 260466 / 260446), pergunta
  antes de gravar (por omissão «Não»).
- Depois de guardar pergunta «Criar a pasta do orçamento agora?», como nos orçamentos
  normais. A pasta é a da versão, dentro da pasta-mãe.
- **Ficheiros:** PDF, Excel e relatórios destes registos novos gravam em
  `<pasta-mãe>/<versão>` (`260186_INNERE/06`). «Duplicar para versão 07…» vai para a `/07`.
- **Eliminar:** num antigo com pasta-mãe, «Eliminar Orçamento» com a pasta apaga **só a
  subpasta da versão do V3**, nunca a pasta-mãe com as versões do V2. Antes, nos que
  apontavam para a pasta-mãe, era a pasta-mãe inteira.
- Migração `20261019_119`: coluna `orcamentos.pasta_manual_por_versao` (0 nos registos
  antigos, que continuam a gravar diretamente na pasta escolhida). Testes em
  `tests/test_orcamento_antigo_versao.py`, `tests/test_novo_orcamento_antigo_versao.py`,
  `tests/test_export_paths.py` e `tests/test_orcamento_service.py`.

Guião de teste (reiniciar o Martelo; ver na etiqueta do topo se está na **BASE REAL** ou na
dev):

1. Orçamentos → **«Novo Orçamento»** → «Escolher cliente…» → INNERE RUI VIEGAS → marcar
   **«Orçamento antigo (registo manual)»**. Esperado: aparecem Ano, N.º orçamento, Pasta do
   orçamento e **Versão** («01» e «— escolha primeiro a pasta do orçamento —»).
2. Ano = **2026**, deixar o N.º orçamento **vazio** → «Escolher pasta…» → `Rede › server_le ›
   _Lanca_Encanto › LancaEncanto › Dep._Orcamentos › 2026 › 260186_INNERE` → «Selecionar
   pasta». Esperado: N.º orçamento = **260186**; Versão = **06**; ao lado «grava em
   260186_INNERE/06 · no servidor: 01, 02, 03, 04, 05».
3. Mudar a Versão para **05**. Esperado: texto ao lado a castanho «… — atenção: a pasta 05 já
   existe no servidor». Carregar em **Guardar**. Esperado: não grava; mensagem a vermelho «A
   versão 05 já existe no servidor e tem ficheiros (do Martelo V2). Escolha uma versão nova —
   a seguinte é a 06 — …».
4. «Escolher pasta…» outra vez, entrar em `260186_INNERE` e escolher a pasta **05** →
   «Selecionar pasta». Esperado: o caminho volta a ser o de `260186_INNERE` (sem o «/05») e por
   baixo «(escolheu a versão 05: ficou a pasta-mãe)»; Versão = **06**.
5. Mudar o N.º orçamento para **260187** → Guardar. Esperado: pergunta «O número do orçamento
   é 260187, mas a pasta escolhida é a do 260186 … Gravar assim mesmo?» → **Não**. Voltar a
   pôr **260186**.
6. Versão **06** → **Guardar**. Esperado: pergunta «Orçamento 260186_06 criado. Criar a pasta
   do orçamento agora?» → **Sim** → «Pasta criada: …\260186_INNERE\06». Na lista aparece o
   **260186**, versão **06**.
7. Com o 260186 / 06 selecionado → **«Pasta do Orçamento»**. Esperado: abre
   `260186_INNERE\06` (vazia); as pastas 01 a 05 continuam lá ao lado, intactas.
8. Abrir o orçamento, pôr um item e gerar o PDF do orçamento. Esperado: o PDF fica dentro de
   `260186_INNERE\06`, não solto na `260186_INNERE`.
9. (Opcional) «Editar Orçamento» → o botão diz **«Duplicar para versão 07…»**. Se duplicar,
   a pasta da 07 é `260186_INNERE\07`.
10. (Opcional, para ver que a pasta-mãe está a salvo) Selecionar a versão 07 criada no passo
    9 → «Eliminar Orçamento» → com a pasta. Esperado: a confirmação mostra só
    `…\260186_INNERE\07`; depois de eliminar, `260186_INNERE` e as pastas 01 a 06 continuam
    lá.
11. Um orçamento **normal** (sem «Orçamento antigo») continua igual: sem linha «Versão» e
    entra como 01.

Resultado: **testado pelo Paulo a 19-10** com a Catia, na base real. O 260186_06 ficou
criado e a pasta também.

### Terminal: avisos de tamanho da janela e relógios depois de mudar de utilizador (2026-10-19)

No mesmo teste, o terminal do VS Code mostrou duas coisas:

- **`QWindowsWindow::setGeometry: Unable to set geometry …`** (8 linhas por cada «Novo
  Orçamento»). Não é erro: a janela cresce para mostrar o texto novo (pasta, versão,
  avisos), o Qt pede a altura exata e o Windows, com o ecrã em escala, arredonda-a uns
  pixels para cima. Entrou no filtro do ruído do Qt (`app/config/qt_message_handler.py`),
  ao lado do «Could not parse stylesheet».
- **`ERRO Assistente dos Orçamentos: Could not locate a bind…`**. Era um erro a sério, que
  já vinha de antes. Na «mudança de utilizador» a janela de quem sai fecha-se mas não é
  destruída, e os relógios dela (Assistente dos Orçamentos, avisos do PHC, Registo de Horas,
  traduções do iX, aviso de versão nova) continuavam a dar horas. Sem ninguém entrado davam
  este erro; depois de outra pessoa entrar, corriam com a ligação dela mas com os dados de
  quem saiu (podiam mostrar à Catia o resumo ou as mensagens do Paulo). Agora, ao fechar a
  janela principal, param-se todos os relógios dela (`parar_relogios` em
  `app/ui/main_window.py`). Testes em `tests/test_main_window_parar_relogios.py`.

Guião de teste (reiniciar o Martelo a partir do VS Code, para ver o terminal):

1. Orçamentos → «Novo Orçamento» → marcar «Orçamento antigo» → escolher a pasta de um
   orçamento → Cancelar. Esperado: o terminal **não** mostra linhas
   `QWindowsWindow::setGeometry`.
2. Botão **«Sair»** no canto de cima, à direita (ao lado de «Reportar problema»). Na janela
   de login, esperar **mais de 10 minutos** sem entrar. Esperado: o terminal não mostra `ERRO Assistente dos Orçamentos`.
3. Entrar como **Catia** e trabalhar normalmente mais de 10 minutos. Esperado: não aparece
   nenhuma janela do Assistente nem mensagem de (Não) Adjudicado que seja do Paulo; no
   terminal, nenhum `ERRO`.

## Items do orçamento: setas ↑/↓ para mudar a ordem (2026-10-19)

Pedido do Paulo: no separador **Items** de um orçamento, selecionar um ou mais items e
subi-los ou descê-los na lista. Até aqui ficavam pela ordem em que tinham sido criados.

Feito:

- Duas setas **↑** e **↓** à direita dos botões **STD / SERIE**. Cada clique move os items
  selecionados **uma posição**. Vários selecionados (Ctrl/Shift) andam juntos e mantêm a
  ordem entre eles; quando um bate no princípio ou no fim, os outros continuam até
  encostarem. Depois de mover, os items continuam selecionados, para se poder carregar
  outra vez.
- A ordem nova é a da coluna **Ordem**, do **PDF** e dos **relatórios**. Preços e totais não
  mudam.
- A versão fica numerada **1..N**: os buracos deixados por items removidos (havia 2 versões
  assim na base real) desaparecem ao primeiro movimento.
- As linhas de **suplemento** (placas não stock) são automáticas e ficam sempre no fim; não
  se movem.
- A base tem um índice único (versão, ordem). Trocar o 1 com o 2 diretamente chocava a meio,
  por isso a ordem nova grava-se em dois passos (`OrcamentoItemRepository.reordenar_items`).
  Regra pura em `app/domain/mover_selecao.py`; testes em
  `tests/test_orcamento_items_mover.py`.

Guião de teste (reiniciar o Martelo; se estiver na **BASE REAL**, no fim volte a pôr a ordem
como estava):

1. Orçamentos → selecionar o **261057** → «Abrir Orçamento» → separador **Items**. Esperado:
   à direita de **STD / SERIE**, dois botões **↑** e **↓**; com o rato por cima, «Subir os
   items selecionados uma posição na lista…».
2. Clicar na linha **3 (RP_03)** → **↑**. Esperado: RP_03 passa para a posição 2 (coluna
   Ordem = 2), RP_02 desce para 3, a linha continua selecionada e em baixo aparece «Item
   movido.». A Soma Preço Final continua **2.650,44 €**.
3. **↑** outra vez. Esperado: RP_03 na posição 1. **↑** mais uma vez. Esperado: nada mexe e
   aparece «A seleção já está na primeira posição.».
4. Clicar em RP_03, **Ctrl+clique** em RP_01 (as duas primeiras) → **↓**. Esperado: as duas
   descem juntas e RP_02 fica em 1. Aparece «2 items movidos.».
5. Separador **Relatórios** (ou gerar o PDF do orçamento). Esperado: os items saem pela
   ordem nova.
6. Sem nada selecionado (clicar numa zona vazia da tabela) → **↓**. Esperado: «Selecione os
   items a mover (Ctrl/Shift para escolher vários).».
7. Voltar a pôr RP_01, RP_02, RP_03 pela ordem original com as setas.

## Registo de Horas: Teletrabalho e várias entradas e saídas (2026-10-19)

Pedido do Paulo, com um mockup em HTML e 15 perguntas antes de mexer no código
(respostas e decisões em `docs/36_registo_horas.md`, secção «Teletrabalho e várias
entradas e saídas»).

Feito:

- Tipo de dia novo **Teletrabalho**, a seguir a «Dia útil». Conta **pelo relógio**: dentro
  do horário habitual das Definições (08:00–17:00) são horas normais, antes ou depois é
  extra, e o que faltar para as 8h desconta ao mês. Campo **«Ausência justificada»** (só
  neste tipo) para o tempo fora que não desconta. Extra junto com as dos dias úteis; sem
  subsídio de alimentação.
- **Linhas Entrada/Saída** em todos os tipos menos a Folga: uma por defeito, o botão
  **«+ Acrescentar entrada e saída»** acrescenta outra por baixo (até 6), o **✕** tira-a. O
  «2.º período» do dia útil passou a ser a linha 2. Os botões 17h…22h mudam a saída da
  última linha. As linhas ficam pela ordem do dia; linhas sobrepostas dão erro e não gravam.
- **Almoço automático:** um intervalo entre linhas à hora de almoço desliga «Descontar
  almoço» e a janela diz porquê.
- Fim de semana, feriado e férias: linhas (vazias por defeito), «Descontar almoço»
  desligado, e a caixa **«Só o total de horas»** (os dias antigos abrem assim).
- Folha do mês e janela de envio: coluna «Horário» com todas as linhas; no teletrabalho a
  coluna Extra mostra «+3h · −2h». **PDF:** uma coluna «Horário» em vez das duas
  Entrada/Saída. Resumo do mês: as extra e as faltas do teletrabalho cada uma no seu sítio.
- **Definições:** campo novo «Tipo de dia habitual» (Dia útil / Teletrabalho).
- Base: migração `20261019_120` (3 colunas em `registo_horas_dias`: `periodos`,
  `ausencia_min`, `falta_min`). Campo de hora que pode ficar vazio:
  `app/ui/widgets/campo_hora.py`. Testes em `tests/test_registo_horas_*.py`.
- Atenção: uma versão antiga do Martelo que abra uma folha com um dia de Teletrabalho dá
  erro. Fazer versão nova antes de o Pedro (ou o admin noutro PC) ver esses dias.

Guião de teste (reiniciar o Martelo; VS Code → «Martelo V3 — BASE REAL (martelo_v3)»,
entrar como **paulo** → menu **Registo de Horas**, mês de **outubro de 2026**). Os dias 20
a 24 são de teste: no fim apague-os (passo 13) ou ponha lá as horas verdadeiras.

1. **Duplo clique na terça 20.** Esperado: a janela tem 6 tipos de dia (**Teletrabalho**
   a seguir a «Dia útil»), uma linha **1 · Entrada 08:00 · Saída 17:00**
   com os botões 17h…22h à direita, o botão **«+ Acrescentar entrada e saída»**, e o
   resultado **«8»** / «8h trabalhadas · sem horas extra».
2. Marcar **Teletrabalho**. Esperado: o texto por baixo diz «Dentro do horário
   (08:00–17:00) são horas normais…» e aparece o campo **«Ausência justificada»**.
3. Na linha 1, Saída **10:00**. Carregar em **«+»** e na linha 2 escrever Entrada **13:00**,
   Saída **17:00**. Esperado: **«Descontar almoço» desliga-se sozinho** e aparece «Almoço
   não descontado: o intervalo 10:00 → 13:00 já inclui a pausa.»; resultado **«6 − 2»**, com
   «faltam 2h para as 8h: descontam ao mês» a vermelho.
4. Carregar em **«+»**. Esperado: os botões 17h…22h passam para a linha 3 (só a última linha
   os tem). Na linha 3 escrever Entrada **20:00**, Saída **23:00**. Esperado: **«6 + 3»** / «9h trabalhadas · 3h extra (fora do
   horário) · faltam 2h para as 8h: descontam ao mês».
5. **Ausência justificada 2,0 h**, Observações **«Consulta»**. Esperado: **«8 + 3»** /
   «9h trabalhadas · 2h de ausência justificada · 3h extra (fora do horário)».
6. **Guardar.** Esperado na folha, dia 20: Tipo **Teletrabalho**, Horário **«8h – 10h ·
   13h – 17h · 20h – 23h»**, Horas **8 + 3**, Normais **8**, Extra **+3h**, Observações
   «Teletrabalho – Ausência justificada 2h – Consulta». No resumo, «Dias registados: … ·
   teletrabalho: 1».
7. **Linhas sobrepostas:** duplo clique na **quarta 21** → «+» → linha 2 Entrada **11:00**,
   Saída **18:00**. Esperado: «—» e «As linhas 1 e 2 sobrepõem-se: das 11:00 às 17:00 estaria
   contado duas vezes.»; **Guardar** não grava (mensagem vermelha). Carregar no **✕** da
   linha 2: volta a «8».
8. **Fora de ordem:** ainda no dia 21, linha 1 Entrada **13:00** e Saída **17:00**; «+»;
   linha 2 Entrada **08:00**, Saída **12:00** e carregar em **Tab**. Esperado: as linhas
   trocam de lugar (1 = 08:00–12:00, 2 = 13:00–17:00), o almoço desliga-se sozinho
   (intervalo 12:00 → 13:00) e o resultado é **«8»**. **Fechar** sem guardar.
9. **Sábado 24:** duplo clique. Esperado: tipo **Fim de semana**, uma linha vazia
   «--:-- / --:--», «Descontar almoço» desligado, caixa **«Só o total de horas»** e a
   mensagem «Indique as horas trabalhadas: a entrada e a saída, ou marque «Só o total de
   horas».». Escrever **09:00–13:00**, «+», **14:00–17:00**. Esperado: **«7»** / «7h extra».
   **Guardar.** Na folha: Horário «9h – 13h · 14h – 17h», Subs. Alimentação **8,75 €**.
10. **Dia antigo:** duplo clique no **domingo 4**. Esperado: abre com **«Só o total de
    horas»** marcado, **3,0 h**, e a nota «Este dia foi registado só com o total…»;
    resultado «3». **Fechar.**
11. **Dia com 2.º período:** duplo clique na **segunda 19**. Esperado: duas linhas
    **08:00–17:00** e **17:00–20:00**, «8 + 3». **Fechar.**
12. **Folha em PDF.** Esperado: uma só coluna **«Horário»** (já não há Entrada/Saída duas
    vezes); dia 20 «8H – 10H · 13H – 17H · 20H – 23H», Extra «+3».
13. **Definições…** → campo novo **«Tipo de dia habitual»** → **Teletrabalho** → Guardar →
    duplo clique na **quinta 22** (sem registo). Esperado: abre já em **Teletrabalho**.
    Fechar e voltar a pôr nas Definições o tipo que quer de verdade. Por fim, apagar os dias
    de teste **20** e **24** (abrir o dia → **«Apagar dia»** → Sim) ou pôr lá as horas
    verdadeiras.

## Criar Encomenda IMOS: favoritos do Article Designer (2026-10-19)

Problema apanhado pelo Paulo: nas obras criadas pelo Martelo, no iX CAD › **Article
Designer**, as setas do **«Princípio de construção»** e da **«Informação de produção»**
abriam vazias. Nas obras criadas à mão no iX Organizer vêm logo preenchidas.

Causa (comparação da `1804_01_26_JF_VIVA`, do Martelo, com a `1804_01_26_JF_VIVA_copia`,
feita à mão): ao criar uma obra, o iX Organizer copia a lista global de favoritos
(`dbo.FAVORITES` com `INORDER` vazio, 891 linhas em 47 listas) para a obra nova. O Martelo
não fazia essa cópia. Antes de mexer no código, o Paulo correu o script
`scripts/imos_favoritos/copiar_favoritos_para_obra.sql` sobre a 1804 e as listas passaram a
aparecer.

Feito:

- **Criar Encomenda IMOS** copia a lista global de favoritos para a encomenda, na mesma
  transação que a cria. Só copia as listas que a obra ainda não tenha. Continua a ser só
  INSERT: o Martelo não altera nem apaga nada no iMos.
- O resumo final diz quantos favoritos foram copiados.
- O script SQL fica no repositório e serve para acertar à mão uma obra antiga criada pelo
  Martelo: abre-se no SSMS ligado à `imos_LE`, muda-se `@obra`, corre-se primeiro com
  `@ensaio = 1` e depois com `@ensaio = 0`.
- Código em `app/services/imos_escrita.py` (passo 4 do script PowerShell) e
  `app/ui/dialogs/imos_encomenda_dialog.py`. Testes em `tests/test_imos_escrita.py` e
  `tests/test_imos_encomenda_dialog.py`. Explicação completa no doc 21, fase E1.

Guião de teste (reiniciar o Martelo; usar a próxima obra verdadeira que precise de
encomenda no iMos):

1. **Produção** → selecionar a obra (a coluna **«Enc. iMos»** tem de estar vazia) → botão
   **Funções** → **«Criar Encomenda IMOS…»**. Confirmar o caminho e o nome como sempre.
2. **«Criar no IMOS»** → **Sim**. Esperado: a mensagem «Criado no iMos por …» com a linha
   «• <nome da obra> — DIR_ID …, PROADMIN …» e, por baixo dela, **«891 favoritos do Article
   Designer copiados»**. O número pode ser um pouco diferente: é o tamanho da lista global
   nesse dia.
3. **iX Organizer** → **↻** → abrir a obra no **iX CAD** (ou no Martelo: Funções → «Abrir no
   iX CAD»).
4. **Article Designer** → artigo novo → **Tipo de peça = Topo** → seta do **«Princípio de
   construção»**. Esperado: a lista vem preenchida (TP_I_2020, TP_O_2222, TMP_O_2222, …,
   TP_I_2000_CV_PRF_Ov03_Rf1).
5. **Tipo de peça = Lateral** → mesma seta. Esperado: LT_2020, LT_2202, LT_GAVTRO_2010, …
6. Seta da **«Informação de produção»**. Esperado: RODATETO, REGUA_HORIZONTAL, RODAPE,
   LATERAL, …
7. Se alguma lista vier vazia, dizer o nome da obra ao Claude: ele confirma na base quantas
   linhas a obra tem na `FAVORITES`.

## Guia do menu Produção para os colegas (2026-10-20)

Pedido do Paulo: com vários utilizadores e muitas opções, faltava uma apresentação que
explicasse o menu Produção — criar obras (do orçamento e da encomenda PHC), Novo
Modelo/Versão, encomenda e iX CAD do iMos, listas de ferragens, Lista Material (Excel),
CUT-RITE (enviar e PDF), Preparação, Imprimir, Exportar documentação, notificar o
cliente e Ocorrências. Formato escolhido por ele: **HTML + PDF**, que abre em qualquer PC
sem internet.

Feito (só documentação, o programa não mudou):

- `docs/guias/producao/`: 31 diapositivos com os ecrãs reais do Martelo (obra de exemplo
  26.1058_01_01_JF_VIVA) e marcações numeradas. Resultado num só ficheiro,
  `Guia_Producao_Martelo_V3.html` (modo leitura, modo apresentação, imprimir), e no
  `Guia_Producao_Martelo_V3.pdf`. Como se altera e reconstrói: `LEIA-ME.md` da pasta.
- Os prints, as imagens e os dois ficheiros finais **ficam fora do GitHub** (`.gitignore`
  da pasta): têm dados reais de clientes. O email do cliente aparece desfocado.
- `docs/guias/capturar_janela.py`: captura o Martelo janela a janela, limpo, para os
  guias dos outros menus.
- Prints tirados na base real só a abrir janelas e a cancelar: nada foi criado, enviado
  ou gravado.

Guião de teste (não é preciso reiniciar o Martelo):

1. Explorador de Ficheiros → `C:\Users\Utilizador\Documents\Martelo_Orcamentos_V3\docs\guias\producao`
   → duplo clique em **`Guia_Producao_Martelo_V3.html`**. Esperado: abre no Edge, com a
   barra castanha em cima («Martelo V3 · Guia do menu Produção») e os diapositivos uns por
   baixo dos outros, com os prints visíveis.
2. Carregar em **☰ Índice**. Esperado: lista dos 31 diapositivos; clicar em
   «Lista Material: o Excel em 4 passos» salta para o diapositivo 16.
3. Carregar em **▶ Apresentar**. Esperado: ecrã inteiro, um diapositivo de cada vez.
   **→** avança, **←** recua, **I** abre o índice, **Esc** volta ao modo leitura no mesmo
   diapositivo.
4. No diapositivo 2 (índice) clicar no cartão **«5 CUT-RITE»**. Esperado: salta para o 19.
5. Abrir **`Guia_Producao_Martelo_V3.pdf`**. Esperado: 31 páginas 16:9, uma por diapositivo.
6. Rever os textos: o que estiver mal explicado ou faltar, dizer ao Claude o número do
   diapositivo.

## Lista Material_IMOS: passo 4 (Análise) suprimido por agora (2026-10-20)

Pedido do Paulo: o módulo **Análise da Lista Material** (validar materiais e consultar
custos) ainda não está verdadeiramente concluído e a análise de custos vai ser repensada.
Para os colegas não o usarem a partir do fluxo da Lista Material, o passo 4 fica
suprimido por agora.

Feito:

- O passo 4 **continua a aparecer** (mesmo título, «LISTAGEM_CUT_RITE preenchida — passo 4
  de 4»), mas deixou de perguntar Sim/Não: é só um aviso a dizer que a análise está
  suprimida por agora porque vai ser melhorada. Ao fechar o aviso abre-se o Excel, como
  acontecia quando se respondia «Não».
- A linha de estado depois do passo 3 já não diz «a preparar o Assistente»; diz «falta o
  passo 4».
- Para voltar a ligar o passo 4 basta pôr `PASSO_4_ANALISE_LISTA_MATERIAL_ATIVO = True` em
  `app/ui/pages/producao_page.py`: o código antigo ficou lá, sem mexer.
- **Não mudou:** Funções › «Analisar/Completar Lista Material…» continua a abrir a análise
  a quem tiver o acesso «Análise Lista Material» (Utilizadores e Acessos).
- Testes em `tests/test_producao_page_import.py` (o passo suprimido e, com a constante a
  True, o comportamento antigo).

Guião de teste (reiniciar o Martelo; usar a próxima obra que precise de Lista Material,
com o CSV já exportado do iMos para `I:\Cutrite\Work\Cutrite_Import_CSV`):

1. **Produção** → selecionar a obra → botão **«Lista Material_IMOS»**. Se a lista já
   existir, escolher **«Criar nova»** (a antiga fica na pasta com a data e a hora no nome).
2. **«Lista Material criada — passo 1 de 4»** → **Yes**. Responder às perguntas da macro no
   Excel como sempre.
3. **«CSV IMOS importado — passo 2 de 4»** → **Yes**.
4. **«Listas de ferragens IMOS — passo 3 de 4»** → **Yes** (fechar a janela «Gerar listas
   iMOS» quando quiser) ou **No**. Esperado: a linha de estado por baixo dos botões diz
   «Listas de ferragens processadas; falta o passo 4.» (ou «… ignorada; falta o passo 4.»).
5. Esperado: aparece **«LISTAGEM_CUT_RITE preenchida — passo 4 de 4»** com o ícone de
   informação (i) e **só o botão OK**, com o texto «… O passo 4 — módulo Análise da Lista
   Material (validar materiais e consultar custos) — está suprimido por agora: a análise de
   custos vai ser melhorada antes de voltar a ficar disponível. …».
6. **OK**. Esperado: a janela da Análise da Lista Material **não** abre; abre-se o Excel da
   Lista Material e a linha de estado diz «LISTAGEM_CUT_RITE preenchida; a abrir o Excel
   para continuar o trabalho.»

## Criar Encomenda IMOS: abrir e gravar no iX CAD sem o Organizer (2026-10-22)

Pedido do Paulo: depois de criar a encomenda no Martelo, ainda era preciso ir ao iX
Organizer confirmar e gravar, abrir a obra no iX CAD e voltar a gravá-la como a
encomenda. A ideia é que o Martelo faça esse ciclo todo.

Análise e teste ao vivo antes do código (22-10, obra de teste `1804_02_26_JF_VIVA`): o
Organizer, ao criar uma encomenda, copia o `IMOS.dwt` da pasta config do iX CAD do PC para
`I:\Factory\Imorder\<obra>\<obra>.dwg`. Fazendo o mesmo, abrindo a obra pelo canal do iX
CAD e pedindo o `imosqsave` (a gravação rápida do iMos), a obra abriu e ficou gravada em
poucos segundos, sem janelas, com os mesmos ficheiros e os mesmos dados de uma obra feita
pelo caminho antigo. Detalhe no doc 21, fase E3.

Feito:

- **Criar Encomenda IMOS** tem a opção **«Abrir no iX CAD e gravar»**, marcada quando o
  PC tem o iX CAD (sem ele fica desligada e a dica diz porquê). Com ela marcada, depois de
  criar, o diálogo fecha-se e o Martelo prepara a pasta e o desenho, abre a obra no iX CAD
  e grava-a. Vai dizendo o que faz na linha de estado da Produção.
- Só grava se o separador ativo do iX CAD for mesmo a obra. Se a obra já tiver desenho, não
  se mexe nele: só é aberta.
- Com o iX CAD fechado, pergunta se o deve abrir (como no «Abrir no iX CAD») e grava
  depois de ele arrancar.
- Com a opção desmarcada fica tudo como antes.
- No disco o Martelo só cria (a pasta e o desenho, nunca por cima). Na base do iMos não
  escreve nada de novo: quem grava a obra é o iX CAD.
- Código em `app/services/imos_cad_service.py`, `app/ui/helpers/abrir_ix_cad.py`,
  `app/ui/dialogs/imos_encomenda_dialog.py` e `app/ui/pages/producao_page.py`. Testes em
  `tests/test_imos_cad_service.py`, `tests/test_abrir_ix_cad.py` e
  `tests/test_imos_encomenda_dialog.py`.

Guião de teste (reiniciar o Martelo; usar a próxima obra verdadeira que precise de
encomenda no iMos):

1. Deixar o **iX CAD aberto**, como normalmente. Não é preciso abrir o Organizer.
2. **Produção** → selecionar a obra (a coluna **«Enc. iMos»** tem de estar vazia) → botão
   **Funções** → **«Criar Encomenda IMOS…»**. Esperado: ao lado do botão «Criar no IMOS»
   está a caixa **«Abrir no iX CAD e gravar»** marcada; ao passar o rato, a dica fala do
   IMOS.dwt e de não ser preciso ir ao Organizer.
3. **«Criar no IMOS»** → **Yes**. Esperado: «Criado no iMos por …», com os favoritos
   copiados e, no fim, «A seguir o Martelo abre a obra no iX CAD e grava-a: acompanhe na
   linha de estado da Produção.» → **OK**. O diálogo fecha-se sozinho.
4. Olhar para a linha por baixo dos botões da Produção. Esperado, em poucos segundos:
   «A confirmar a encomenda no iMos…» → «Pedido enviado ao iX CAD…» → «Obra <nome> aberta
   no iX CAD; a seguir é gravada…» → «A gravar a obra <nome> no iX CAD…» → **«Obra <nome>
   aberta e gravada no iX CAD: pode desenhar.»**
5. **iX CAD**. Esperado: separador novo com o nome da obra, **sem asterisco** (está
   gravada), sem a janela «Guardar encomenda» e sem nenhum aviso. Os dados da encomenda
   (Nº Enc PHC, cliente, descrição) aparecem e, no Article Designer, as listas do
   «Princípio de construção» e da «Informação de produção» estão preenchidas.
6. **Explorador** → `I:\Factory\Imorder\<obra>`. Esperado: `<obra>.dwg`, `<obra>.bak`
   (com a data do IMOS.dwt, 06/10/2026), `<obra>.FXF`, `<obra>.PNG` e a pasta `XML`.
7. **Variante com o iX CAD fechado** (noutra obra): no passo 4 aparece «O iX CAD não está
   aberto. Quer que o Martelo o abra agora…?» → **Yes**. Esperado: «A abrir o iX CAD…» e,
   quando ele acaba de arrancar, o resto da sequência do passo 4 até «aberta e gravada».
8. **Variante com a caixa desmarcada**: o diálogo fica aberto depois de criar, a dizer que
   a encomenda já está criada, e o iX CAD não é tocado (como antes).
9. Se a linha de estado parar numa mensagem que manda gravar no iX CAD, gravar lá e dizer
   ao Claude o nome da obra e a mensagem que apareceu.

## Produção ↔ Escritório do Streamlit: Desenho → Aprovisionamento (2026-10-28)

Pedido do Paulo, com o «prompt mestre» do Leitor_PHC3 (Streamlit): quando uma obra passa a
**Produção** no menu Produção e se grava, o Martelo continua a fazer o que fazia (gravar,
supervisor, email ao cliente) e, além disso, avança esse modelo/versão no Escritório do
Streamlit, de `DESENHO` para `APROVISIONAMENTO` — o mesmo passo do botão «Enviar para o
Aprovisionamento» do Streamlit, registado «via MARTELO». No sentido contrário, quando alguém
dá esse passo no Streamlit, o Martelo avisa e propõe pôr a obra em Produção, na mesma caixa
do analisador de estados do PHC.

Fase 0 (só leitura, 28-10): esquema da base do Streamlit confirmado por `SELECT`; a conta do
Martelo no Streamlit (`Lanca_Encanto_ReadOnly`) só lia. Ao fim do dia o lado do Streamlit deu-lhe
`INSERT`+`UPDATE` em `Escritorio_Versoes` e `INSERT` em `Escritorio_Eventos`,
`TemposProducaoHistorico` e `TemposProducaoHistorico_` (confirmado com `fn_my_permissions`).
Decisões: as recomendações da Fase 0, todas aceites.

Feito:

- **Gravar → Produção.** Antes de gravar, o Martelo lê o Streamlit (uma só ida, ~1-2 s) e
  decide pelas regras do próprio Streamlit, pela mesma ordem: assistências (`A###`) e versões
  ≠ 01 não passam; a obra tem de estar no Escritório «com desenho» e com desenhador; quem
  grava tem de ter a permissão `Escritorio_Desenhos` (ou ser administrador) e ser o desenhador
  da obra; tem de haver Caderno de Encargos; se o modelo/versão já saiu do Desenho, diz quando
  e por quem. Os avisos do Streamlit (sem plano de corte, plano não enviado, sem materiais)
  aparecem numa caixa com **«Enviar mesmo assim» / «Só gravar no Martelo»**. Depois de gravar
  no Martelo, escreve no Streamlit numa só transação. **O Streamlit nunca impede nem desfaz o
  Gravar**: se não responder, a obra fica gravada e uma caixa diz como repetir.
- **Material só do cliente** (placas do cliente e orla do cliente ou não indicada): como no
  Streamlit, não passa pelo Aprovisionamento e fica logo libertado para a fábrica
  (`LIBERTAR_AUTO`, `libertada_por = 'sistema'`).
- **O registo** (`Escritorio_Eventos`): `tipo = AVANCAR`, `utilizador` = quem gravou (nome do
  Streamlit), `motivo = «Desenho concluído.»`, `detalhe` com `"via": "MARTELO"`, a versão do
  Martelo, o PC, a pasta da obra e, quando há, `em_nome_de` e os avisos aceites. Mais uma
  linha `escritorio` no Histórico do Tempos de Produção:
  `Desenho → Aprovisionamento · via MARTELO · motivo: Desenho concluído.`
- **Quem é quem.** Os nomes de utilizador não coincidem (Ana → `ana.felix`, paulo →
  `paulo_catarino`). O Martelo liga pelo nome da pessoa (completo, depois o primeiro nome);
  nunca pelo username sozinho, porque o `admin` do Martelo não é o `admin` do Streamlit.
  Correção à mão em `streamlit_mapa_utilizadores` (ex.: `admin=paulo_catarino`).
- **Funções › «Enviar para o Aprovisionamento»**: só o passo do Streamlit, para repetir (o
  Streamlit estava desligado) ou para uma obra que já estava em Produção. Não muda o estado
  no Martelo.
- **Aviso do Escritório (Streamlit → Martelo).** De 5 em 5 minutos o Martelo pergunta ao
  Streamlit se houve algo novo (o `MAX(id)` dos eventos); se houve, procura as **suas** obras
  em Desenho cujo modelo/versão já está no Aprovisionamento ou libertado e mostra a caixa
  «Aviso do Escritório (Streamlit)». As marcadas passam a Produção (e, com a opção do email
  ligada, propõe o email ao cliente como no Gravar); as desmarcadas não voltam a ser
  perguntadas (só se a etapa mudar); «Ver depois» volta no dia seguinte. Nunca faz uma obra
  recuar. É a única exceção à regra «Desenho e Produção são do utilizador»: aqui quem avançou
  foi o próprio desenhador, no Streamlit — o «4 - PRODUÇÃO» do PHC continua ignorado.
- **Interruptor** `streamlit_escrita_ativa` (Configurações › Caminhos do Sistema), **OFF por
  omissão**. Com ele desligado, o Gravar fica exatamente como antes. A conta SQL é a mesma de
  todas as leituras e já pode escrever: é este interruptor que segura a escrita. O aviso do
  Escritório (só leitura) funciona com ele desligado.
- Migração `20261028_121` (só acrescenta as duas definições; não cria tabelas). Aplicada na
  `martelo_v3_dev` e, a 28-10 à noite (com o sim do Paulo), na `martelo_v3`.
- Código: `app/domain/escritorio_streamlit.py` (regras), `app/services/escritorio_streamlit_service.py`
  (leitura), `app/services/escritorio_streamlit_escrita.py` (escrita — SQL fixo, só `INSERT` e
  `UPDATE` com compare-and-set, nunca `DELETE`; tem um modo `ensaio` que corre tudo e desfaz),
  `app/ui/helpers/escritorio_producao.py`, `app/ui/helpers/verificacao_escritorio_streamlit.py`,
  `app/ui/pages/producao_page.py`, `app/ui/dialogs/producao_phc_sync_dialog.py`,
  `app/ui/main_window.py`. Testes em `tests/test_escritorio_streamlit*.py` e
  `tests/test_verificacao_escritorio_streamlit.py`.
- Verificado ao vivo, só a ler: as mensagens saem certas para obras reais (sem CE, de outro
  desenhador, já enviada «em 28/10/2026 14:30 por bruno (via Streamlit)», já libertada); a
  `admin` do Martelo é recusada; as 6 obras da base real em Desenho que o Streamlit já avançou
  aparecem no aviso. **A escrita ainda não foi feita contra o Streamlit real.**
- **Segurança, por resolver:** o `scripts/create_default_system_settings.py` (repositório
  público) tem a password por omissão desta conta, que agora escreve. Rodar a password no SQL
  Server e tirá-la do script.

Primeiro teste do Paulo (28-10, 19h35–20h17, base REAL) — «não aconteceu nada» nos dois
sentidos. Causas, confirmadas pelo diário, pelo Martelo e pelo Streamlit (só leitura):

- **Martelo → Streamlit (obra 26.1831_01_01_JF_VIVA, gravada Desenho → Producao às 20:16):**
  a `martelo_v3` não tinha a definição `streamlit_escrita_ativa` (a migração 121 só estava
  na dev), por isso o Gravar ficou como antes, de propósito. O Streamlit, lido depois, dava
  esta obra como «pronta a seguir», só com o aviso «plano de corte não enviado».
- **Streamlit → Martelo (1866 às 20:14 e 1849 às 20:15, enviadas por `paulo_catarino`):**
  no Martelo as duas já estavam em **Producao** (desde as 15:00 e as 15:57). O aviso só
  propõe obras que no Martelo ainda estão em Desenho: não tinha nada a perguntar. Correto.
- **Ligação ao Streamlit intermitente:** às 19:37 e às 19:56 o aviso falhou com «Este
  anfitrião não é conhecido». O PC do Streamlit mudou outra vez de IP (agora 192.168.5.210) e
  a empresa não tem DNS interno: o nome resolve-se pela rede local e o SqlClient do PowerShell
  às vezes desiste ao fim dos 8 s (reproduzido: falha, e a tentativa seguinte liga).
  **Corrigido:** o Martelo pergunta primeiro o IP ao Windows e liga pelo IP; se o Windows não
  souber, fica o nome, como antes (`servidor_por_ip`). Nas Configurações continua o nome.
- **Mensagem de erro ilegível** («nÆo foi encontrado»): o PowerShell escreve na página de
  código 850 e o Martelo lia na 1252, por isso o erro também não se traduzia para «servidor
  desligado ou fora da rede». **Corrigido** (lê na página OEM).
- **Diário:** depois de uma falha, as seguintes só voltavam ao diário após uma volta com
  novidades; agora também após uma volta «sem novidades».

**Segundo teste (28-10, 21h01, base REAL): OK.** Com o interruptor ligado pelo `admin`, o
Paulo enviou do Martelo a obra **26.1800_01_01_JF_VIVA**. Conferido no Streamlit: evento 144
`AVANCAR` DESENHO → APROVISIONAMENTO por `paulo_catarino`, motivo «Desenho concluído.»,
`detalhe.via = "MARTELO"` (versão 1.0.29, posto); a versão no Aprovisionamento; a linha
`escritorio` no Histórico «Desenho → Aprovisionamento · via MARTELO · motivo: Desenho
concluído.». O aviso no sentido contrário ficou por testar (não havia mais obras em Desenho).

Para o segundo teste: aplicar a migração 121 na `martelo_v3` (passo 2 do guião) e ligar o
interruptor. A 1831 serve para o caso feliz (está em Producao: usar **Funções › «Enviar para
o Aprovisionamento»**). Para o aviso: pôr a 1849 (ou a 1866) em **Desenho** no Martelo,
gravar, **fechar e voltar a abrir o Martelo** e esperar ~1,5 min — a caixa «Aviso do
Escritório (Streamlit)» deve propô-la. (Sem reiniciar, só volta a procurar quando houver um
evento novo no Streamlit.)

Guião de teste (reiniciar o Martelo). **Atenção:** tanto na base de testes como na real, o
Martelo fala com o **Streamlit verdadeiro** — os passos 4 a 6 escrevem lá. Antes, fazer uma
cópia de segurança da base do Streamlit e escolher uma obra de teste.

1. **Interruptor desligado (nada muda).** Produção → uma obra em Desenho → Estado
   **Producao** → **Salvar**. Esperado: tudo como antes (supervisor, email ao cliente) e
   nenhuma caixa do Escritório.
2. **Ligar (como `admin`).** As definições do sistema só se gravam com a conta de
   administrador: o perfil normal (`paulo`) só as lê. **Sair** → entrar como **admin** →
   Configurações → **Caminhos do Sistema** → pesquisar `str` → linha «Streamlit - Enviar para
   o Aprovisionamento ao gravar uma obra em Produção (ON/OFF)» → valor **ON** → **Guardar
   Configurações** → «Configuracoes guardadas com sucesso.» → **Sair** e voltar a entrar como
   **paulo** (o Streamlit não conhece o `admin` do Martelo). Com a conta `paulo`, a página
   mostra «Só leitura…» e o Guardar fica cinzento (desde 28-10; antes dizia só «Nao foi
   possivel guardar» e o valor voltava a OFF).
3. **Recusa, sem escrever nada.** Produção → obra **26.1472_01_01_JF_VIVA** (do Paulo, ainda
   sem Caderno de Encargos no Streamlit) → **Funções** → **«Enviar para o Aprovisionamento»**.
   Esperado: caixa «Escritório (Streamlit)» com «Falta criar o Caderno de Encargos desta
   versão (no Streamlit) antes de a enviar.» Variantes: uma obra com Versão 02 → «Só a versão
   01 de cada modelo segue…»; entrar como **admin** → «Não encontrei «admin» entre os
   utilizadores do Streamlit…».
4. **Caso feliz (escreve no Streamlit).** No Streamlit, criar o Caderno de Encargos da obra
   de teste (ex.: 1472 modelo 01). No Martelo, Produção → essa obra (em Desenho) → Estado
   **Producao** → **Salvar**. Esperado: se faltar plano de corte/materiais, caixa com os
   avisos e os botões «Enviar mesmo assim» / «Só gravar no Martelo» → **Enviar mesmo
   assim**; depois o email ao cliente, como sempre; na linha de estado
   «… Escritório: ✔ Modelo 01 · Versão 01 enviado para o Aprovisionamento.»
5. **Conferir no Streamlit.** Escritório → **Aprovisionamento**: a obra aparece (até ~60 s ou
   «Atualizar»). **Histórico** da obra: «enviada» por `paulo_catarino`, motivo «Desenho
   concluído.» Tempos de Produção → **Histórico**: linha `escritorio` com
   «Desenho → Aprovisionamento · via MARTELO · motivo: Desenho concluído.»
6. **Repetir não duplica.** Funções → «Enviar para o Aprovisionamento» na mesma obra.
   Esperado: «Este modelo/versão já foi enviado em <data> por paulo_catarino (via MARTELO).»
   Para desfazer o ensaio: no Streamlit, Aprovisionamento → **«Devolver ao Desenho»**.
7. **Aviso Streamlit → Martelo.** No Streamlit, Desenhos → enviar para o Aprovisionamento
   outra obra tua que **no Martelo esteja em Desenho** (se já estiver em Producao, não há
   aviso — é o esperado). No Martelo, esperar até 5 minutos (ou reiniciar e esperar ~1,5 min). Esperado: caixa **«Aviso do Escritório (Streamlit)»** com a
   obra, «Desenho → Producao», Fonte «Escritório», «No Aprovisionamento desde <data> (…)» →
   **«Atualizar as marcadas»** → «1 obra(s) passada(s) a Produção no Martelo.» e a lista da
   Produção atualizada.
8. **Desmarcar / Ver depois.** Com duas obras no aviso: desmarcar uma e atualizar a outra →
   a desmarcada não volta a aparecer. Fechar com **«Ver depois»** → volta no dia seguinte.

## Registo de Horas: Teletrabalho só conta as horas fora do ponto (2026-10-28)

Pedido do Paulo: no Teletrabalho as horas das 08h–17h estão no **ponto da empresa**, por isso
o Martelo só deve contar as horas fora desse horário, todas como extra, sem descontar nada
(19h–21h = 2h extra; com a regra de 19-10 dava «0 + 2» e −6h no mês). Antes do código, um
mockup com 7 perguntas (`https://claude.ai/artifact/N3Rfgg521dgXB4jj3cD7qX`); ele aceitou
as 7 recomendações. Decisões em `docs/36_registo_horas.md`, secção «Teletrabalho: só as
horas fora do ponto».

Feito:

- **Regra nova do Teletrabalho:** o horário habitual das Definições fica no ponto e não conta;
  só contam as horas antes ou depois dele, todas extra; nada desconta. A folha mostra
  **«ponto + 2»** (ou só «ponto»). Uma linha que apanhe parte do horário conta só a parte de
  fora. Sem almoço; jantar e acerto ficam.
- **Janela do dia:** um dia novo de Teletrabalho abre com a **linha vazia**; cada linha diz
  «conta 2h», «conta 2h · 9h no ponto» ou «no ponto, não conta»; os botões 17h…22h, com a
  entrada vazia, põem a entrada às 17:00. Saiu a «Ausência justificada» e o «Descontar
  almoço» (só no Teletrabalho). Um dia sem linhas guarda-se («ponto») e o lembrete deixa de o
  pedir.
- **Resumo, PDF e email:** linha nova «Dias em teletrabalho (horário no ponto da empresa)».
- **Dias já gravados com a regra de 19-10:** botão **«Recalcular teletrabalho (N)…»** na página
  (só aparece se houver dias desses em meses ainda não enviados). Mostra o antes e o depois de
  cada dia e só grava com «Sim». Os meses já enviados não mudam. A janela de envio avisa se o
  mês ainda tem dias desses.
- Sem migração (as colunas `ausencia_min`/`falta_min` ficam a 0 nos dias novos). Testes em
  `tests/test_registo_horas_*.py`.

Guião de teste (reiniciar o Martelo; VS Code → «Martelo V3 — BASE REAL (martelo_v3)», entrar
como **paulo** → menu **Registo de Horas**, mês de **outubro de 2026**):

1. **Dias de teletrabalho já gravados.** Se já gravou dias de Teletrabalho em outubro, aparece
   em baixo, ao lado de «Importar da app antiga…», o botão **«Recalcular teletrabalho (N)…»**.
   Carregar. Esperado: uma lista com cada dia, por exemplo «ter 27/10:  0 + 2 (−6h)  →  ponto +
   2 (+2h)», e o total desses dias «passam de … para …». Conferir e carregar em **Sim**.
   Esperado: na folha esses dias passam a «ponto + N», o botão desaparece e a linha de estado
   diz «N dia(s) de Teletrabalho recalculado(s) com a regra nova». (Sem dias desses, o botão
   não aparece: passar ao 2.)
2. **Dia novo.** Duplo clique num dia útil de outubro sem registo (ex.: **sexta 30**) → marcar
   **Teletrabalho**. Esperado: o texto por baixo diz «Dia na empresa com horas extra fora do
   horário. Das 08:00 às 17:00 as horas ficam no ponto da empresa…»; uma linha **vazia**;
   não há «Descontar almoço» nem «Ausência justificada»; resultado **«ponto»** / «sem horas
   extra · o horário fica no ponto da empresa · não desconta nada».
3. Carregar no botão **19h**. Esperado: a linha fica **17:00–19:00**, com «conta 2h» a verde;
   resultado **«ponto + 2»** / «2h extra (fora do horário) · não desconta nada».
4. Mudar a Entrada para **08:00** (08:00–19:00). Esperado: continua **«ponto + 2»**; a linha
   diz «conta 2h · 9h no ponto» e o detalhe «08:00–17:00 fica no ponto da empresa».
5. Mudar para Entrada **19:00**, Saída **21:00** (o exemplo do pedido). Esperado: **«ponto +
   2»**. **Guardar.** Na folha: Horas **ponto + 2**, Normais vazio, Extra **+2h**, Observações
   «Teletrabalho». No resumo: «Descontos» não mexe e o «Total de horas extra» sobe 2h.
6. **Linha dentro do horário:** abrir outra vez o dia 30 → «+» → linha 2 **10:00–12:00**.
   Esperado: a linha 2 diz «no ponto, não conta» (cinzento) e o resultado fica **«ponto + 2»**.
   **Fechar** sem guardar.
7. **Jantar:** dia 30 → linha 1 **19:00–23:00** → marcar **«Descontar jantar»**. Esperado:
   **«ponto + 3»**. **Fechar** sem guardar.
8. **Dia sem horas fora:** duplo clique noutro dia útil por registar → **Teletrabalho** →
   deixar a linha vazia → **Guardar**. Esperado: grava; na folha Horas **«ponto»** e o dia
   deixa de aparecer «por registar».
9. **Folha em PDF.** Esperado: os dias de teletrabalho com Extra «+2»… e, no quadro do fim,
   depois do subsídio, a linha **«Dias em teletrabalho (horário no ponto da empresa)»** com o
   número de dias.
10. **Enviar à contabilidade…** (só ver; **não enviar**). Esperado: no resumo e no texto do
    email aparece «Dias em teletrabalho (horário no ponto da empresa): N». Carregar em
    «Corrigir primeiro».
11. Os dias usados no teste (30 e o do passo 8): apagar («Apagar dia» → Sim) ou pôr lá as horas
    verdadeiras.

## CSV do iMos para a Lista Material: coluna Sub_Artigo (2026-10-29, ENSAIO ronda 1)

Pedido do Paulo: no CSV que o iMos exporta para a Lista Material
(`I:\Cutrite\Work\Cutrite_Import_CSV\<obra>_Lista_Corte.csv`) não sai o nome dos artigos que
estão **dentro** do artigo principal (ex.: o bloco de gavetas `BL_3GVT_RP_01`, Group type =
Artigo, dentro do `RP_A_01_ESQ` na obra de teste `APAGAR_14`). Quer um `.cfg` novo com uma
coluna para esses sub-artigos; as colunas CNC/ABD/BHT podem sair. Não mexe no programa
Martelo: é um `.cfg` do iMos e um verificador. Detalhe em `scripts/imos_cfg/README.md`.

Descoberto:

- O `.cfg` que o iMos usa está **dentro da base** (`BINDATA`), não na pasta `I:\CFG`: tem de
  ser importado no princípio (Element Manager). O princípio de ensaio
  `EXPORT_CSV_CUT_RITE_LE_V1` tinha lá dentro o `Homag_DF_Productionmanager.cfg` — por isso o
  teste dele saiu em XML, em `I:\Cutrite\Work\Cutrite_Import_CSV\Productionmanager\Project.xml`.
- **Defeito que já existe:** o `ACCUMULATE` atual junta peças iguais de sub-artigos de RPs
  diferentes numa só linha, com o RP da primeira (as peças de sub-artigos têm `POSSTR`
  vazio). O total corta-se certo, mas a coluna Artigo fica errada. Visto em 5 obras com o CSV
  posterior à última gravação; ex.: `CRW_2128_2711_01`, «Gaveteiro Lateral Gaveta 451×135»
  são 6 no RP_01 + 6 no RP_02 + 6 no RP_03 e o CSV tem 18 no RP_01.

Feito (ronda 1, ensaio):

- `EXPORT_CSV_CUT_RITE_LE_V2.cfg` (em `I:\CFG` e em `scripts/imos_cfg`): igual ao atual nas
  colunas 1–19; coluna 20 **Sub_Artigo** (`IFEMPTY[POSSTR;ARTNR;TEXT[]]`: nome do artigo mais
  próximo quando a peça está num sub-artigo; vazio no resto); sem CNC/ABD/BHT; `ACCUMULATE`
  com `ARTNR_NR_ID`. Só no ensaio: 4 colunas `DIAG_*` e `SUBDIRNAME=TESTE_SUBARTIGOS`.
  **Erro meu (corrigido na ronda 2):** o ficheiro não foi para a subpasta; saiu na pasta de
  cima com o nome colado (`TESTE_SUBARTIGOSAPAGAR_14_Lista_Corte.csv`), porque o
  `SUBDIRNAME` só funciona se o nome do ficheiro começar por `\`.
- `scripts/imos_cfg/verificar_csv_subartigos.py`: compara o CSV com a base do iMos (só
  SELECT). Com o CSV atual da `APAGAR_14` dá «OK» (110 linhas).

Guião de teste (ronda 1):

1. **Element Manager** → **Processar transferência de dados** → pasta **LANCA_ENCANTO** →
   **EXPORT_CSV_CUT_RITE_LE_V1**. Em «Default Settings», botão **↓ (Importar)** → escolher
   `I:\CFG\EXPORT_CSV_CUT_RITE_LE_V2.cfg` (= `\\SERVER_LE\Homag_iX\CFG`). Esperado: o campo
   **File** passa a `EXPORT_CSV_CUT_RITE_LE_V2.cfg`. Não mexer em «Set as Default»,
   «Configuration of path» (Standard) nem «Output path» (`I:\Cutrite\Work\Cutrite_Import_CSV`).
   **Guardar**. (Nada se perde: o Productionmanager continua no princípio
   `Homag_DF_Productionmanager` e o ficheiro na pasta CFG.)
2. **iX CAD** com a obra **APAGAR_14** aberta → gravar com a caixa **«Lista de peças»**
   marcada → **DESIGN › Output › Processar transferência de dados** → marcar **só**
   `EXPORT_CSV_CUT_RITE_LE_V1` → ✓. Esperado: «Todos os ficheiros foram criados!» e o
   ficheiro novo `I:\Cutrite\Work\Cutrite_Import_CSV\TESTE_SUBARTIGOS\APAGAR_14_Lista_Corte.csv`.
   O `APAGAR_14_Lista_Corte.csv` da pasta de cima **não** muda.
3. Abrir esse CSV no Bloco de Notas. Esperado: o cabeçalho acaba em
   `Cliente_Final;Sub_Artigo;DIAG_ARTNR;DIAG_TOPO;DIAG_POSSTR;DIAG_ARTNR_NR_ID;`; as linhas do
   bloco de gavetas do **RP_A_01_ESQ** (Gaveteiro Tampo/Fundo/Lateral/Vista, Frente de gaveta,
   Gaveteiro Lateral/Traseira/Fundo Gaveta — 21 peças) têm `BL_3GVT_RP_01` na coluna
   Sub_Artigo; todas as outras linhas têm Sub_Artigo vazio.
4. **iX Organizer** → **Order Manager** → selecionar a obra **CRW_2128_2711_01** (obra
   antiga, só se lê) → **Processar transferência de dados** → **só**
   `EXPORT_CSV_CUT_RITE_LE_V1` → ✓. Esperado:
   `...\TESTE_SUBARTIGOS\CRW_2128_2711_01_Lista_Corte.csv`, com o «GAVETEIRO 3GV + 1VISTA» na
   coluna Sub_Artigo e as peças do gaveteiro **separadas por RP** (ex.: «Gaveteiro Lateral
   Gaveta 451×135» com Qt. 6 no RP_01, 6 no RP_02 e 6 no RP_03, e não 18 no RP_01).
5. Avisar o Claude: ele corre `verificar_csv_subartigos.py` nas duas obras, lê as colunas
   `DIAG_*` e prepara a versão final (sem `DIAG_*`, na pasta normal). Só depois se decide
   importar no princípio por defeito `EXPORT_CSV_CUT_RITE_LE` e ajustar o modelo da Lista
   Material (coluna U da `LISTA_ORDENADA` passa de «CNC» a «Sub_Artigo»).

### Ronda 2: colunas finais (2026-10-29)

Resultado da ronda 1 (o Paulo testou a `APAGAR_14`; a `CRW_2128_2711_01` ficou de fora por ser
antiga): `DIAG_ARTNR` sai certo — `BL_3GVT_RP_01` nas 10 linhas (21 peças) do gaveteiro do
`RP_A_01_ESQ`, o nome do RP nas outras — e o verificador dá «OK» (110 linhas, igual ao CSV
antigo, por isso o `ARTNR_NR_ID` no `ACCUMULATE` não estragou a junção). A coluna
`Sub_Artigo` (`IFEMPTY`) falhou: saiu ao contrário. O `TOPARTICLE_NAME[ARTNR_NR_ID]` também
funciona.

Decisões do Paulo: ordem `… Enc.; Cliente; Artigo; SubArtigo; Notas …` — a coluna **RP passa a
chamar-se Artigo** e a **SubArtigo** (= `DIAG_ARTNR`, ou seja `ARTNR`) fica à direita; o
ficheiro volta ao nome normal `<obra>_Lista_Corte.csv`; primeiro afina-se a exportação, depois
o Excel; é ele que importa o `.cfg` no princípio por defeito quando estiver afinado.

Feito: `EXPORT_CSV_CUT_RITE_LE_V2.cfg` final (em `I:\CFG` e no repositório) — colunas 1–15
iguais, 16 Artigo, 17 SubArtigo, 18 Notas, 19 Notas_1, 20 Cliente_Final (as duas últimas têm
dados em obras reais: 15 e 856 linhas em 500 CSV), sem `DIAG_*` nem `SUBDIRNAME`. Nas peças
fora de sub-artigo o SubArtigo repete o nome do artigo (é o que o `ARTNR` dá).

**Falta no Excel — não esquecer** (detalhe em `scripts/imos_cfg/README.md`, «Falta no
Excel»): a macro `Import_CSV_Imos_1` procura o cabeçalho «RP» e copia as colunas **por
posição**; com o CSV novo o SubArtigo cairia em **Notas** e as notas em Notas_1. Por isso o V2
**não vai para o princípio por defeito** antes de a macro passar a copiar por nome e a
`LISTA_ORDENADA` ganhar a coluna SubArtigo à direita de Artigo.

Guião de teste (ronda 2):

1. **Element Manager** → **Processar transferência de dados** → **LANCA_ENCANTO** →
   **EXPORT_CSV_CUT_RITE_LE_V1** → botão **↓ (Importar)** → outra vez
   `I:\CFG\EXPORT_CSV_CUT_RITE_LE_V2.cfg` (o ficheiro mudou; o iMos usa a cópia que tem na
   base, por isso é preciso importar de novo) → **Guardar**.
2. **iX CAD**, obra **APAGAR_14** → gravar com **«Lista de peças»** → **Processar transferência
   de dados** → **só** `EXPORT_CSV_CUT_RITE_LE_V1` → ✓. Se perguntar «Substituir ficheiro
   existente?» → **Sim**. Esperado: `I:\Cutrite\Work\Cutrite_Import_CSV\APAGAR_14_Lista_Corte.csv`
   (o normal, substituído — é obra de teste).
3. Abrir o CSV no Bloco de Notas (não gravar no Excel). Esperado: cabeçalho
   `Descricao;…;Enc.;Cliente;Artigo;SubArtigo;Notas;Notas_1;Cliente_Final;`; 110 linhas;
   `BL_3GVT_RP_01` na coluna SubArtigo das 10 linhas do gaveteiro do RP_A_01_ESQ; nas
   outras, o SubArtigo igual ao Artigo.
4. **Não** usar o V1 em obras reais até o Excel estar adaptado (o CSV tem o mesmo nome e a
   Lista Material importá-lo-ia com as colunas trocadas).
5. Avisar o Claude para conferir com o verificador.

### Ronda 3: SubArtigo vazio quando o nome é igual ao artigo (2026-10-29, ENSAIO)

Resultado da ronda 2: exportação OK (o Paulo confirmou no Excel). Pedido novo: a coluna
Artigo fica como está; a **SubArtigo só mostra o nome quando é diferente do nome do artigo
principal, senão fica vazia**.

Descoberto:

- O `IFEMPTY[x;se_vazio;se_não]` funciona (confirmado no XML do Productionmanager); o que
  falhou na ronda 1 foi o `TEXT[]` vazio. Para «vazio» usa-se o campo `VENEER_ID`, que está
  vazio em todas as peças das obras recentes (139 903).
- A coluna Artigo mostra a **posição**, que em ~9 % dos artigos é um número («1», «001») e não
  o nome (ex.: `1870_01_26_JF_VIVA`, artigo `RP_A_01a` na posição `1`). Por isso o SubArtigo
  compara **nome com nome**: `IFEQUAL[ARTNR;TOPARTICLE_NAME[ARTNR_NR_ID];VENEER_ID;ARTNR]`.
- Com esta regra também aparecem sub-artigos com posição própria e nome diferente («Peça de
  pontos», «Grupo Article Designer», `WC_A_01_MOB1_SUITE_B`); os artigos compostos com o mesmo
  nome (ex. `RP_D_15_RC_FRENTE`) ficam vazios.
- A sintaxe do `IFEQUAL` não está documentada: o ensaio leva 3 colunas `TESTE_*` no fim para a
  confirmar (e uma alternativa, se falhar).

Guião de teste (ronda 3):

1. **Element Manager** → **Processar transferência de dados** → **LANCA_ENCANTO** →
   **EXPORT_CSV_CUT_RITE_LE_V1** → **↓ (Importar)** → `I:\CFG\EXPORT_CSV_CUT_RITE_LE_V2.cfg`
   (mudou outra vez) → **Guardar**.
2. **iX CAD**, obra **APAGAR_14** → gravar com **«Lista de peças»** → **Processar transferência
   de dados** → **só** `EXPORT_CSV_CUT_RITE_LE_V1` → ✓ → «Substituir?» **Sim**. Se der erro,
   copiar a mensagem para o Claude.
3. Esperado em `I:\Cutrite\Work\Cutrite_Import_CSV\APAGAR_14_Lista_Corte.csv`:
   - **SubArtigo** = `BL_3GVT_RP_01` nas 10 linhas do gaveteiro do RP_A_01_ESQ e **vazio** em
     todas as outras;
   - no fim, `TESTE_IFEQUAL_TXT` = `DIFERENTE` no gaveteiro e `IGUAL` no resto;
     `TESTE_IFEMPTY_CAMPO` = `BL_3GVT_RP_01` no gaveteiro e vazio no resto;
     `TESTE_IFEMPTY_TXT` = `VAZIO` no gaveteiro e `CHEIO` no resto.
4. Avisar o Claude: ele confere com o verificador e tira as colunas `TESTE_*` (versão final).

### Ronda 4: versão final da exportação, regra do SubArtigo no Excel (2026-10-29)

Resultado da ronda 3: o SubArtigo continuou com `RP_A_01_*` nas peças fora de sub-artigos.
As 3 colunas de teste mostraram porquê: no iMos, `IFEQUAL` e `IFEMPTY` com um campo simples à
cabeça devolvem **sempre o valor desse campo** (até `IFEMPTY[POSSTR;TEXT[VAZIO];TEXT[CHEIO]]`
deu `RP_A_01_DIR`). Não há forma de fazer o «vazio se igual» no `.cfg`.

Decisão do Paulo: a regra passa para o **Excel** (como outras regras que a macro já faz ao ler
o CSV), e o CSV leva no fim uma coluna técnica **ArtigoNome** (nome do artigo principal,
`TOPARTICLE_NAME[ARTNR_NR_ID]`). O Excel compara o SubArtigo com ela, e não com a coluna
Artigo, porque o Artigo mostra a posição: nas cozinhas é `001`, `002`… (ex. `1431_02_26_CRW`,
posição `001` = `MB_01_GVT_PL`); comparar com o Artigo deixaria o SubArtigo preenchido em
todas as peças dessas obras.

Feito: `EXPORT_CSV_CUT_RITE_LE_V2.cfg` final em `I:\CFG` e no repositório — `… Cliente;
Artigo; SubArtigo; Notas; Notas_1; Cliente_Final; ArtigoNome`, SubArtigo = `ARTNR`, sem
colunas de teste. O verificador aplica a mesma regra que o Excel vai aplicar e dá «OK» com os
dados do ensaio da ronda 1 (que já traziam os dois nomes).

Guião de teste (ronda 4):

1. **Element Manager** → **Processar transferência de dados** → **LANCA_ENCANTO** →
   **EXPORT_CSV_CUT_RITE_LE_V1** → **↓ (Importar)** → `I:\CFG\EXPORT_CSV_CUT_RITE_LE_V2.cfg` →
   **Guardar**.
2. **iX CAD**, obra **APAGAR_14** → gravar com **«Lista de peças»** → **Processar transferência
   de dados** → **só** `EXPORT_CSV_CUT_RITE_LE_V1` → ✓ → «Substituir?» **Sim**.
3. Esperado em `I:\Cutrite\Work\Cutrite_Import_CSV\APAGAR_14_Lista_Corte.csv`: cabeçalho
   `…;Cliente;Artigo;SubArtigo;Notas;Notas_1;Cliente_Final;ArtigoNome;`; 110 linhas; SubArtigo =
   `BL_3GVT_RP_01` no gaveteiro do RP_A_01_ESQ e o nome do RP no resto (o Excel é que o vai
   apagar); ArtigoNome = `RP_A_01_ESQ`, `RP_A_01_DIR`, … em todas as linhas.
4. A seguir: adaptar o Excel da Lista Material (ver `scripts/imos_cfg/README.md`, «Falta no
   Excel»). Só depois o V2 vai para o princípio por defeito (é o Paulo que o importa).

**TESTADO (29-10-2026, 11h44):** o Paulo exportou a `APAGAR_14` com a versão final; o
`verificar_csv_subartigos.py` dá «OK» (110 linhas; colunas `…;Artigo;SubArtigo;Notas;Notas_1;
Cliente_Final;ArtigoNome`; as 21 peças do `BL_3GVT_RP_01` no `RP_A_01_ESQ`). A exportação
está afinada; falta o Excel. Por provar ainda: a correção do `ACCUMULATE` numa obra com o
mesmo sub-artigo em dois RPs.

### Ronda 5: coluna ISPEC, forma da peça (2026-10-29, ENSAIO)

Pedido do Paulo: pôr no CSV o `ISPEC` (0 = retangular de 4 lados, 1 = 4 lados com contorno,
2 = mais de 4 lados, 3 = não é painel), para o Excel avisar nas Notas que a peça tem forma
especial e pode ter CAM. Na `APAGAR_14` ele criou duas peças em L para testar: **PECA_L**
(«Topo», L desenhado com 6 orlas) e **RECORTE_L** («Teto», retangular com o recorte interior
`REC_CNT_L_CIMA_TRAS`).

Descoberto na base: PECA_L tem **ISPEC 2**; RECORTE_L tem **ISPEC 0**, porque o L é um
contorno interior (perfil `PTYPE='I'` na `IDBPRF`) e o contorno exterior continua com 4 lados.
Nas 160 obras recentes há **382 peças (48 obras) assim**, quase todas com recortes de rodapé
(`REC_CNT_L_RODAPE_FRENTE/TRAS`) — o ISPEC sozinho não as apanha. Valores do ISPEC nessas obras:
30 676 × 0, 84 × 1, 348 × 2, 108 × 3 e 30 × 4 (o 4 não está documentado). O `ACCUMULATE` não
junta peças de formas diferentes.

Feito: `.cfg` V2 com a coluna **ISPEC** depois de ArtigoNome e 3 colunas de ensaio
`TESTE_EDGECOUNT`, `TESTE_PRFCNT`, `TESTE_IDBPRF_PRFID` (campos do motor que podem contar ou
dizer os perfis, à procura de um que apanhe o recorte interior). O verificador confere o
ISPEC linha a linha e marca as peças com recorte interior.

Guião de teste (ronda 5):

1. **Element Manager** → **Processar transferência de dados** → **LANCA_ENCANTO** →
   **EXPORT_CSV_CUT_RITE_LE_V1** → **↓ (Importar)** → `I:\CFG\EXPORT_CSV_CUT_RITE_LE_V2.cfg` →
   **Guardar**.
2. **iX CAD**, obra **APAGAR_14** (com a PECA_L e a RECORTE_L) → gravar com **«Lista de
   peças»** → **Processar transferência de dados** → **só** `EXPORT_CSV_CUT_RITE_LE_V1` → ✓ →
   «Substituir?» **Sim**. Se der erro, mandar a mensagem ao Claude.
3. Esperado no `APAGAR_14_Lista_Corte.csv` (abrir no Bloco de Notas): 112 linhas (as 110 + as
   2 peças em L); coluna **ISPEC** = `2` na linha «Topo» (Artigo `PECA_L`) e `0` em todas as
   outras, incluindo «Teto» (Artigo `RECORTE_L`); nas `TESTE_*` não há resultado esperado:
   é o que se quer descobrir.
4. Avisar o Claude: ele confere e decide com o Paulo como apanhar o recorte interior.

**1.ª tentativa (29-10-2026, ~13h): «Erro no ficheiro!APAGAR_14_Lista_Corte.csv».** Não era o
`.cfg`: o CSV estava aberto noutro programa (Windows 0x80070020, «está a ser utilizado por
outro processo»; deixava ler mas não escrever, como o Excel) e o iMos não o conseguia
substituir. O ficheiro ficou como estava às 11h44. Neste PC não havia Excel visível; só um
`EXCEL.EXE -Embedding` invisível, aberto desde 27-10 às 14h29 por outro programa, sem livros.
Antes de exportar outra vez: fechar o que tiver o CSV aberto (Excel, também noutro PC; o painel
de pré-visualização do Explorador com o CSV selecionado). Para ver o CSV, usar o Notepad++.

**2.ª tentativa (29-10-2026, 14h38): caixas «Erro no ficheiro de configuração.
Chave:STRING_MAT / EDGECOUNT (e PRFCNT) / O campo não existe na base de dados!»**, uma atrás da
outra (uma por peça e por campo). Quem as mostrava era o `idbcclg.exe`, o motor da
transferência, que corre à parte do iX CAD e ficou preso. O OK enviado de fora não as
fechava, por isso o Claude terminou o processo, a pedido do Paulo.

O CSV ficou escrito até meio (54 linhas, a última cortada) e as linhas saíram com 23 colunas
em vez de 25, porque os campos que não existem desaparecem da linha. Mesmo assim mostrou o
que interessava:
- **ISPEC certo:** `2` no «Topo» (`PECA_L`) e `0` no «Teto» (`RECORTE_L`) e nas outras peças.
- **Nenhum `TESTE_*` serve:** `EDGECOUNT` e `PRFCNT` não existem, e o `IDBPRF_PRFID` sai vazio.

Os recortes interiores ficam para o plano B (princípio «Views» ou o Martelo ler a `IDBPRF`).

### Ronda 6: `.cfg` V2 final, sem colunas de ensaio (2026-10-29, TESTADO às 15h05)

Feito: `gerar_cfg_v2.py` com `TESTES = []`. O `.cfg` fica com 22 colunas,
`…;Cliente_Final;ArtigoNome;ISPEC;`, e foi copiado para `I:\CFG\EXPORT_CSV_CUT_RITE_LE_V2.cfg`
(igual ao do repositório).

Guião de teste (ronda 6):

1. Se voltar a aparecer uma caixa «IDBCCLG25» que não fecha: **Gestor de Tarefas** →
   **idbcclg** → **Terminar tarefa** (não mexe na obra).
2. **Element Manager** → **Processar transferência de dados** → **LANCA_ENCANTO** →
   **EXPORT_CSV_CUT_RITE_LE_V1** → **↓ (Importar)** → `I:\CFG\EXPORT_CSV_CUT_RITE_LE_V2.cfg` →
   **Guardar**. Sem isto o iMos continua com o `.cfg` do ensaio e as caixas voltam.
3. **iX CAD**, obra **APAGAR_14** → gravar com **«Lista de peças»** → **Processar
   transferência de dados** → **só** `EXPORT_CSV_CUT_RITE_LE_V1` → ✓ → «Substituir?» **Sim**.
   Não deve aparecer nenhuma caixa de erro.
4. Esperado no `APAGAR_14_Lista_Corte.csv` (abrir no Notepad++): 112 linhas de peças, todas
   com 22 colunas, a acabar em `…;ArtigoNome;ISPEC;`; **ISPEC** = `2` no «Topo» (Artigo
   `PECA_L`) e `0` nas outras, incluindo o «Teto» do `RECORTE_L`.
5. Avisar o Claude: ele corre o verificador (`verificar_csv_subartigos.py APAGAR_14`).

**Resultado (29-10-2026, 15h05): OK.** Sem caixas de erro. O CSV tem 112 linhas de peças +
cabeçalho, todas com 22 colunas e fim de linha CRLF. O verificador diz «Artigo, SubArtigo e
quantidades do CSV batem certo com a base» e «ISPEC certo em todas as linhas»: `2` no «Topo»
(`PECA_L`), `0` no «Teto» (`RECORTE_L`, que tem recorte interior e por isso não é apanhado
pelo ISPEC) e `0` nas outras. A exportação V2 está fechada. Falta:
- o Excel (README `scripts/imos_cfg`, «Falta no Excel»), incluindo o texto do aviso do ISPEC;
- o plano B para os recortes interiores;
- provar o `ACCUMULATE` numa obra com o mesmo sub-artigo em dois RPs;
- depois disto, o Paulo passa a V2 para o princípio por defeito.

### Ronda 7: `.cfg` V1 com Posicao, Artigo/SubArtigo e Piso (2026-10-29, ENSAIO)

O Paulo deu nomes novos, no `imos.msg`, aos campos do artigo no iX CAD:
- 10410 «Pos. Number» passa a **Posicao**;
- 6700 «Hierarchy» passa a **Hierarquia de Artigo**;
- 41 «Name of Element Group» passa a **Artigo/SubArtigo**;
- 1219 «Name» passa a **Piso**.

Pediu um `.cfg` com as colunas Posicao, Artigo/SubArtigo e Piso. Esse `.cfg` é o
`EXPORT_CSV_CUT_RITE_LE_V1.cfg`, feito a partir da V2, que fica como cópia de referência.

Descoberto na base:
- O Piso é a coluna `IDBINFO.CPID` do artigo. Na `APAGAR_14` o `RP_04_DIR` tem Posicao
  `Fração_A` e Piso `Piso 1º`; os outros artigos têm `.` (o valor por defeito).
- Num sub-artigo o «Name» é o ID dele (`49187` no `BL_3GVT_RP_01`).
- No `.cfg`, a Posicao e o Artigo/SubArtigo já existiam: são as colunas Artigo e SubArtigo da
  V2, com outro nome.
- Para o Piso usa-se `ART_CPID`. O prefixo `ART_` lê as colunas da `IDBINFO` do artigo da
  peça. Foi lido no motor (`IDBCCLG25.dll`) e a imos não o documenta: é o que este ensaio
  confirma.

Feito: `gerar_cfg_v1_piso.py` gera o `.cfg` com 23 colunas,
`…;Cliente;Posicao;Artigo/SubArtigo;Piso;Notas;Notas_1;Cliente_Final;ArtigoNome;ISPEC;`, e
copiou-se para `I:\CFG\EXPORT_CSV_CUT_RITE_LE_V1.cfg`. O `V1.cfg` antigo (ensaio do cabeçalho
da obra, de 07-10) ficou em `I:\CFG\EXPORT_CSV_CUT_RITE_LE_V1.cfg.copia_2026-10-29_173746`. O
verificador passou a conferir também o Piso.

Guião de teste (ronda 7):

1. Se o `EXPORT_CSV_CUT_RITE_LE_V1.cfg` estiver aberto no Notepad++, ele pergunta se quer
   recarregar: **Sim** (não gravar por cima).
2. **Element Manager** → **Processar transferência de dados** → **LANCA_ENCANTO** →
   **EXPORT_CSV_CUT_RITE_LE_V1** → **↓ (Importar)** → `I:\CFG\EXPORT_CSV_CUT_RITE_LE_V1.cfg` →
   **Guardar**.
3. **iX CAD**, obra **APAGAR_14** (com o `RP_04_DIR`: Posicao `Fração_A`, Piso `Piso 1º`) →
   gravar com **«Lista de peças»** → **Processar transferência de dados** → **só**
   `EXPORT_CSV_CUT_RITE_LE_V1` → ✓ → «Substituir?» **Sim**.
4. Se aparecer «Erro no ficheiro de configuração… ART_CPID… O campo não existe na base de
   dados!»: **Gestor de Tarefas** → **idbcclg** → **Terminar tarefa**, e avisar o Claude. O
   prefixo `ART_` não serve e o Piso tem de vir por outro caminho.
5. Esperado no `APAGAR_14_Lista_Corte.csv` (abrir no Notepad++): 112 linhas de peças, todas
   com 23 colunas.
   - Posicao: `Fração_A` nas linhas do `RP_04_DIR` e o nome nas outras.
   - Artigo/SubArtigo: `RP_04_DIR` (ou `BL_3GVT_RP_01` no gaveteiro do `RP_A_01_ESQ`).
   - Piso: `Piso 1º` nas linhas do `RP_04_DIR`; `.` nas dos outros artigos; `49187` nas do
     gaveteiro (é o «Name» do sub-artigo; o Excel vai corrigir).
6. Avisar o Claude: ele corre o verificador (`verificar_csv_subartigos.py APAGAR_14`).

**Resultado (29-10-2026, 18h26):** não houve caixas de erro e as 112 linhas saíram com 23
colunas. Posicao e Artigo/SubArtigo estão certos: `Apart_B`/`RP_01` (o antigo `RP_A_01_ESQ`,
agora com Piso `R/C`) e `Fração_A`/`RP_04_DIR`. **O Piso saiu vazio em todas as linhas.**

O código do motor explica porquê. O `ART_<campo>` não lê a `IDBINFO`: lê o «Name» do artigo e
procura o `<campo>` no artigo do **catálogo** com esse nome. Como «R/C» e «Piso 1º» não são
artigos do catálogo, vem vazio.

O campo que lê a coluna `CPID` do artigo é o **`CP90NAME`**, que a imos usa nos `.cfg` dela;
o `IDBINFO_CPID` faz o mesmo.

### Ronda 8: Piso com `CP90NAME` (2026-10-29, TESTADO às 19h40)

Feito: `gerar_cfg_v1_piso.py` com o Piso = `CP90NAME`. O resto do `.cfg` V1 fica igual (23
colunas) e foi copiado para `I:\CFG\EXPORT_CSV_CUT_RITE_LE_V1.cfg`.

Guião de teste (ronda 8):

1. **Element Manager** → **Processar transferência de dados** → **LANCA_ENCANTO** →
   **EXPORT_CSV_CUT_RITE_LE_V1** → **↓ (Importar)** → `I:\CFG\EXPORT_CSV_CUT_RITE_LE_V1.cfg` →
   **Guardar**.
2. **iX CAD**, obra **APAGAR_14** → gravar com **«Lista de peças»** → **Processar
   transferência de dados** → **só** `EXPORT_CSV_CUT_RITE_LE_V1` → ✓ → «Substituir?» **Sim**.
   Se o CSV estiver aberto no Excel, fechá-lo antes; se não, dá «Erro no ficheiro!».
3. Esperado no `APAGAR_14_Lista_Corte.csv` (abrir no Notepad++), coluna **Piso**:
   - `R/C` nas linhas do `RP_01` (Posicao `Apart_B`);
   - `49187` nas do gaveteiro `BL_3GVT_RP_01`: é o «Name» do sub-artigo, que o Excel vai
     trocar pelo `R/C` do principal;
   - `Piso 1º` nas do `RP_04_DIR`;
   - `.` nas outras.
4. Avisar o Claude: ele corre o verificador (`verificar_csv_subartigos.py APAGAR_14`).

**Resultado (29-10-2026, 19h40): OK.** O CSV tem 112 linhas de peças (196 peças) + cabeçalho,
todas com 23 colunas e fim de linha CRLF. O verificador confirmou Posicao, Artigo/SubArtigo,
quantidades, ISPEC e Piso em todas as linhas:

| Posicao | Artigo/SubArtigo | Piso | ArtigoNome | Linhas |
|---|---|---|---|---|
| `Apart_B` | `BL_3GVT_RP_01` | `49187` | `RP_01` | 10 |
| `Apart_B` | `RP_01` | `R/C` | `RP_01` | 21 |
| `Fração_A` | `RP_04_DIR` | `Piso 1º` | `RP_04_DIR` | 24 |
| `PECA_L`, `RECORTE_L`, `RP_A_01_DIR`, `RP_A_02_ESQ` | (o mesmo) | `.` | (o mesmo) | 57 |

ISPEC: `2` no «Topo» (PECA_L) e `0` nas outras. A exportação V1 fica fechada. Falta:
- o Excel (README `scripts/imos_cfg`, «Falta no Excel»):
  - procurar as colunas pelo nome (Posicao, Artigo/SubArtigo, Piso);
  - nas linhas de sub-artigos, pôr o Piso do principal (`R/C` em vez de `49187`);
  - `.` → vazio;
  - aviso do ISPEC nas Notas;
- passar o V1 para o princípio por defeito, o que o Paulo faz depois do Excel.

## Lista Material: lista de peças lida da base do iMos, em ENSAIO (2026-10-29)

Pedido do Paulo (29-10-2026, noite): explorar a lista de peças tirada diretamente da base do
iMos, como já se faz nas ferragens, em vez do CSV do `.cfg`. **Em ensaio e em paralelo**: o
caminho normal (CSV do `.cfg` + macro `Import_CSV_Imos_1`) **não muda**. Se ficar complexo,
aborta-se e volta-se ao CSV. Antes de mexer, o Paulo fez uma cópia do modelo:
`Lista_Material_IMOS_MARTELO - Cópia.xltm`.

Porquê: o `.cfg` não dá o Piso do artigo principal às peças dos sub-artigos (o gaveteiro da
APAGAR_14 saía com `49187`, o «Name» do próprio sub-artigo). Além disso, no CSV da 1608_03 o
`.cfg` junta numa linha peças iguais com notas diferentes: a nota «Rasgo 'Tupia' MDF 3MM 1
comp» passa para a peça errada no RP_APT4_14.

O que mudou:
- **Martelo** (`app/services/lista_corte_imos_base_service.py`): lê a obra na base do iMos
  (só SELECT) e escreve um CSV com as mesmas 22 colunas do CSV do `.cfg`, pela mesma ordem.
  No fim leva mais quatro colunas: `Artigo/SubArtigo`, `Piso` (do artigo principal, vazio
  quando é `.`), `ArtigoNome` e `ISPEC`. Compara com o CSV do `.cfg` e escreve um relatório.
- **Martelo, Produção** → **Funções** → **«Lista Material da base iMos (ensaio)…»**. Tudo vai
  para a subpasta `Ensaio_Lista_Base_iMos` da obra: o CSV, o relatório e o Excel
  `Lista_Material_<obra>_BASE.xlsm`. A Lista Material da obra não é tocada, e o Enviar
  CUT-RITE, o Analisar e os PDFs continuam a usar só a dela.
- **Modelo do Excel** (`Lista_Material_IMOS_MARTELO.xltm`, no servidor): ganha a macro
  **`Import_Base_Imos_1`**, que fica no fim do módulo `modImportCSVImos_1` (agora versionado em
  `scripts/vba`). Faz os mesmos passos da `Import_CSV_Imos_1`: Qt.=0, RP, Rasgo, ordem da
  DEFENICOES e Veio. A única diferença é que importa o CSV do Martelo. A `Import_CSV_Imos_1`
  ficou igual, letra a letra.

Confirmado antes de entregar:
- as 22 colunas são iguais às do CSV do `.cfg` em 8 obras (~2100 linhas);
- numa cópia do modelo, a macro compila. A LISTA_ORDENADA feita com a lista da base saiu igual
  à feita com o CSV do `.cfg`:
  - na **0993_04**, linha a linha;
  - na **1849_01**, com as mesmas peças e quantidades (só muda a ordem de linhas com a mesma
    descrição);
  - na **1608_03**, só nas 4 linhas do RP_APT4_14 em que o `.cfg` troca as notas.

Guião de teste:

1. Fechar o Martelo e voltar a abri-lo (para carregar a versão nova).
2. **Produção** → escolher a obra **1608_03_26_HIRONDELLES** (o CSV do iMos foi exportado a
   29-10 às 16h23). Confirmar que o campo **Nome Enc IMOS IX** diz `1608_03_26_HIRONDELLES`.
3. **Funções** → **«Lista Material da base iMos (ensaio)…»**.
4. Esperado na 1.ª caixa:
   - «Lista da base: 480 linhas, 748 peças»;
   - «CSV do iMos: … 499 linhas, 748 peças»;
   - «Resultado: 7 diferença(s)», todas no `RP_APT4_14_P_CORRER` (as notas «Rasgo 'Tupia'»
     e uma no CNC_1).

   Se o desenho tiver sido gravado depois das 16h23, aparece o aviso «o desenho foi gravado
   DEPOIS de o CSV ser exportado».
5. Clicar **Sim**. O Excel abre-se e a macro pergunta pelas linhas com **Qt.=0** (o
   RP_APT7_12 tem quantidade 0 no iMos): responder como na importação normal (**Não**).
6. Na caixa «A LISTA_ORDENADA do Excel de ensaio foi preenchida», clicar **Sim** para o
   AUTOMATION. No fim, o Excel de ensaio abre-se.
7. Esperado:
   - na pasta da obra, uma subpasta **`Ensaio_Lista_Base_iMos`** com 3 ficheiros:
     - `1608_03_26_HIRONDELLES_Lista_Corte_Base.csv`;
     - `1608_03_26_HIRONDELLES_Comparacao_com_CSV_iMos.txt`;
     - `Lista_Material_1608_03_26_HIRONDELLES_BASE.xlsm`;
   - a `Lista_Material_1608_03_26_HIRONDELLES.xlsm` da obra com a data de antes;
   - no Excel de ensaio:
     - o separador `1608_03_26_HIRONDELLES` tem, depois da coluna BHT, as colunas
       `Artigo/SubArtigo`, `Piso`, `ArtigoNome` e `ISPEC`;
     - a LISTA_ORDENADA e a LISTAGEM_CUT_RITE batem com a Lista Material da obra, exceto no
       RP_APT4_14. Lá, a nota «Rasgo 'Tupia' MDF 3MM 1 comp» fica só nas peças que a têm no
       iMos.
8. Repetir com a obra de ensaio do iMos que tem o gaveteiro (**APAGAR_14**), se houver obra no
   Martelo com esse Nome Enc IMOS IX. No separador da importação, as linhas do
   `BL_3GVT_RP_01` devem ter **Piso `R/C`**.

Por fazer, depois do ensaio:
- passar as colunas novas (Artigo/SubArtigo, Piso) para a LISTA_ORDENADA e a
  LISTAGEM_CUT_RITE;
- o aviso do ISPEC nas Notas;
- decidir se o caminho da base substitui o do CSV.

## Cópias de segurança: pasta nova no servidor (2026-11-06)

Pedido do utilizador (04-10): as cópias do Martelo passam a ficar em
`\\SERVER_LE\Backup\Backup_Martelo_V3`, junto dos outros backups da empresa (iMos,
Streamlit, PCs), em vez de `...\Dep._Orcamentos\Base_Dados_Orcamento\Backup_Martelo_V3`.

- O código mudou a 04-10 (`3ce83b3`): o `scripts/backup_martelo.py` usa a pasta nova por
  omissão (`PASTA_SERVIDOR`) e o instalador da tarefa também.
- Faltava a permissão: este PC entra no servidor com a conta `gestao`, que só podia ler a
  pasta nova. O administrador da empresa deu a escrita a 06-11.
- 06-11: as 161 cópias da pasta antiga (base, `Memoria_Claude` e `memoria_2026-10-04`)
  foram copiadas para a pasta nova e conferidas uma a uma (SHA-256). A cópia da antiga app
  das horas (`copia_app_antiga_horarios_2026-10-04.sql`) ficou na subpasta `Registo_Horas`.
- A tarefa «Martelo V3 - copia de seguranca» passou a usar `--copia
  "\\SERVER_LE\Backup\Backup_Martelo_V3"`. A hora e a conta não mudaram. A cópia de
  teste das 13h33 de 06-11 correu bem: base (65 tabelas, 5 procedimentos) e memória do
  Claude chegaram à pasta nova.
- A pasta antiga deixou de receber cópias e o Paulo apagou-a a 06-11.

Guião de teste:

1. Na manhã seguinte, no Explorador do Windows, abrir `\\SERVER_LE\Backup\Backup_Martelo_V3`.
   Deve estar lá a cópia dessa noite, `martelo_v3_<data>_0200.sql.gz` (cerca de 6,5 MB).
2. Abrir a subpasta `Memoria_Claude`: deve estar lá `memoria_claude_<data>_0200.zip`.
3. Abrir a subpasta `Registo_Horas`: deve estar lá
   `copia_app_antiga_horarios_2026-10-04.sql` (38 KB).

Validação recebida: — (por testar).

## Lista Material: coluna «Colar» para as colagens, em ENSAIO (2026-11-06)

Pedido do Paulo: testar na fábrica uma coluna nova, «Colar», na LISTAGEM_CUT_RITE, logo a
seguir à CNC_2. Serve para as peças que se colam para chegar à espessura do iMos: o material
tem uma espessura (Esp.Mat) e o iMos outra (Esp, coluna M), e a linha fica a vermelho. Até
agora escrevia-se nas Notas «colar 19+19 = 38» ou «colar ID 14+14». Passa a haver um código
(guia PROCESSO_ESPECIAL), preenchido por um menu: `[CNC_]conjunto[_orlas][_CNC]`, por
exemplo `CNC_20+21x2+22x2_O4L_CNC` ou `14+14_O4L_CNC`. **O modelo de sempre não muda**: o
ensaio usa uma cópia.

Decisões do Paulo (06-11-2026):
- o Cut-Rite passa a receber **24 colunas**, com a Colar a seguir à CNC_2;
- duas peças do mesmo ID sozinhas escrevem-se `14+14`;
- 2 comprimentos + 2 larguras escrevem-se `O4L`.

O que mudou:
- **Modelo novo no servidor** `Lista_Material_IMOS_MARTELO_COLAR.xltm`, ao lado do de
  sempre. É criado por `scripts/criar_modelo_lista_material_colar.py` a partir do de sempre,
  que fica igual. Tem:
  - a coluna Colar (V) e um botão verde «Colar»;
  - o menu de colagens, que abre com o botão ou com duplo clique numa célula da Colar
    (`frmColar`; regras no `modColar`);
  - a «Copia Listagem CUT_RITE» a copiar até à +Larg (agora a X) e a conferir a Colar antes.

  As macros estão em `scripts/vba/colar`. Ao inserir a coluna, o Excel acertou sozinho as
  fórmulas da Lacagem (Z → AA), o alerta vermelho do Material e a área de impressão.
- **Martelo, Produção → Funções → «Lista Material com coluna Colar (ensaio)…»**: o mesmo que
  o botão «Lista Material_IMOS», mas com o modelo novo. O livro é a Lista Material da obra:
  o Enviar CUT-RITE, o Analisar e os PDFs usam-no.
- **Enviar CUT-RITE**: 23 colunas como sempre; 24 quando o livro tem a Colar logo a seguir
  à CNC_2. Se a Colar estiver noutro sítio, para com uma mensagem. A verificação antes do
  envio avisa dos códigos mal escritos ou desencontrados (regras em
  `app/domain/codigo_colar.py`, iguais às do VBA).
- **Fica igual no modelo de sempre**, porque o Martelo procura estas colunas pela posição
  certa em cada modelo:
  - a ligação da folha Lacagem ao Tipo_Lacagem;
  - o SourceID / Estado_Assistente da Análise, que ia para AA/AB fixas e no modelo Colar
    apagava o Tipo_Lacagem.

Confirmado antes de entregar:
- todos os testes do Martelo passam;
- a regra do código dá o mesmo no VBA e no Python nos 14 casos do guia;
- numa cópia, com a obra 0993_04:
  - o livro criado tem a Colar na V e o SourceID na AB;
  - a AUTOMATION preencheu 336 linhas;
  - o menu gravou e editou conjuntos, e a verificação apanhou um conjunto desencontrado;
  - o Enviar CUT-RITE montou 24 colunas com o código na 22.ª;
- com o modelo de sempre, as colunas e o SourceID (AA) ficam como antes.

**Antes do teste: no Cut-Rite, acrescentar à lista de peças uma coluna de texto logo a seguir
à CNC_2.** Sem ela, uma lista do modelo Colar enviada para o Cut-Rite põe o código no
+comp e o +comp no +Larg.

Guião de teste:

1. Fechar o Martelo e voltar a abri-lo.
2. **Produção** → escolher a obra de teste (com o CSV do iMos já exportado) → **Funções** →
   **«Lista Material com coluna Colar (ensaio)…»**. Se a obra já tem Lista Material, escolher
   «Criar nova (substitui a atual)»: a anterior fica na pasta com a data no nome.
   - Esperado na linha de estado: «Lista Material criada (modelo de ensaio com a coluna
     Colar).»
3. **Passo 1 de 4** → Sim (importar o CSV do iMos). **Passo 2** → Sim (AUTOMATION), como
   sempre.
4. No Excel, separador **LISTAGEM_CUT_RITE**:
   - a coluna **V «Colar»** fica entre a CNC_2 e o +comp;
   - há um botão verde «Colar» por cima dela;
   - ao clicar numa célula da Colar aparece a dica «Duplo clique: menu Colar…».
5. **Duplo clique** na célula Colar de uma peça com o Material a vermelho, por exemplo um
   tampo de 38 mm em material de 19 mm (ID 14). Esperado:
   - abre «Colar - peças a colar (ensaio)», com essa peça no conjunto;
   - a lista de cima mostra só as linhas a vermelho.
6. **Conjunto da mesma peça duas vezes:**
   - no conjunto, selecionar a peça e clicar **+1**: o código fica «14+14»;
   - escolher «2 comprimentos (OC2)» e «2 larguras (OL2)»: fica «14+14_O4L»;
   - marcar «CNC depois da colagem»: fica «14+14_O4L_CNC»;
   - ao lado do conjunto deve aparecer «… 19x2 = 38 mm / Esp no iMos: 38 mm»;
   - clicar **Gravar nas peças do conjunto**. Esperado na linha de estado: «Código
     «14+14_O4L_CNC» gravado em 1 linha(s): ID 14.»
7. **Conjunto de linhas diferentes:**
   - selecionar o ID 20 em cima → **Juntar ao conjunto**;
   - pôr «Quantas de cada» = 2, selecionar o ID 21 → **Juntar**: o código fica «20+21x2»;
   - marcar «CNC antes da colagem» e **Gravar**.
   - Esperado: as linhas ID 20 e ID 21 ficam as duas com «CNC_20+21x2».
8. **Numeração mudada:**
   - inserir uma linha acima da ID 20 (os IDs andam um para a frente);
   - botão «Colar» → **Verificar toda a listagem**.
   - Esperado: aviso de que o código «CNC_20+21x2» não inclui o ID 21 e de que a numeração
     mudou.
   - Desfazer (Ctrl+Z) ou refazer o conjunto.
9. **Copia Listagem CUT_RITE**: com códigos a corrigir, pergunta antes de copiar. A cópia vai
   da A à X (24 colunas).
10. Gravar e fechar o Excel. **CUT-RITE → Enviar CUT-RITE**. Esperado:
    - com códigos desencontrados, aparece a caixa com «COLUNA COLAR — …»;
    - no Cut-Rite, os códigos ficam na coluna nova;
    - o +comp e o +Larg ficam nos sítios de sempre.
11. Numa obra qualquer, o botão **«Lista Material_IMOS»** continua a dar a lista sem a coluna
    Colar.

Por fazer, depois do teste:
- o Streamlit ainda não lê o código;
- se a Colar ficar, passar o modelo Colar a modelo de sempre. As correções às macros comuns
  (`atualizar_macros_modelo_lista_material.py`) só vão para o modelo de sempre; para o Colar,
  volta-se a correr o `criar_modelo_lista_material_colar.py`.

### Coluna «Colar», 2.ª ronda (2026-11-06, depois do 1.º teste na obra 1935_01_01_JF_VIVA)

Pedidos do Paulo, já no menu Colar:
- **Qt:** a Qt de cada peça do conjunto passa a ser quantas entram nele (5+5 → Qt 2), porque o
  Cut-Rite tem de cortar todas. A opção «Qt da peça = quantas entram no conjunto» vem marcada;
  com 1 peça desse ID, a Qt fica como estava.
- **Espessuras:** a soma das espessuras é aproximada, porque as colas também contam. O que
  manda é a Esp do iMos. O menu diz se a soma fica perto (até 2 mm) ou longe; se fica longe,
  sugere ver o conjunto ou se há material com essa espessura no Woodstore.
- **Excedente de corte:** +comp e +Larg a 20 por defeito, editáveis no menu. Ficam nas colunas
  +comp/+Larg das peças do conjunto e vão para o Cut-Rite, onde a etiqueta mostra a medida da
  peça e a de corte. Vazio = não mexe nessas colunas.
- **Pesquisa** por cima da lista das peças, para listas longas (todas as palavras escritas têm
  de aparecer).
- **Orlas depois da colagem num desenho da peça:** um retângulo com as proporções Comp x
  Larg da 1.ª peça do conjunto. Clica-se nas arestas C1/C2 (comprimentos) e L1/L2 (larguras)
  para pôr ou tirar a orla; o código das orlas vai aparecendo (OC2, OL1, O4L…). Há botões
  «4 lados (O4L)» e «Sem orla», e o «Raio / meia-lua (OR)».

«Tirar o código destas peças» não repõe a Qt nem o +comp/+Larg: o menu avisa para os rever.

Confirmado numa cópia (obra 0993_04):
- o projeto VBA compila e o VBA dá o mesmo que o Martelo nos 14 casos;
- o conjunto 3+3 pôs a Qt da peça 3 a 2 e +comp/+Larg a 20 (chegam ao Cut-Rite na 23.ª e
  24.ª colunas);
- a pesquisa «lateral» deixou 86 peças;
- ao abrir numa linha com código, o desenho fica com as arestas desse código.

O desenho não foi visto no ecrã: confirmar no teste que fica legível.

O modelo `Lista_Material_IMOS_MARTELO_COLAR.xltm` do servidor foi refeito. O da 1.ª ronda
ficou ao lado, como `..._COLAR_anterior_20261106_160328.xltm`. **A Lista Material da obra
1935_01 foi feita com o modelo da 1.ª ronda e não tem o menu novo**: para o ver, criar outra
vez a lista com a opção das Funções.

Guião de teste:

1. Produção → obra **26.1935_01_01_JF_VIVA** → Funções → «Lista Material com coluna Colar
   (ensaio)…» → «Criar nova (substitui a atual)». A anterior fica com a data no nome.
2. Passo 1 (CSV) e passo 2 (AUTOMATION) como sempre.
3. LISTAGEM_CUT_RITE → duplo clique na célula Colar do «Lateral» a vermelho (ID 3, 2358 x 75,
   Esp 30,2, material de 19).
4. No campo **Pesquisar**, escrever «lateral». Esperado: a lista fica só com as laterais.
5. No conjunto, selecionar o ID 3 e clicar **+1**. Esperado:
   - o código fica «3+3»;
   - ao lado do conjunto aparece «Esp no iMos: 30,2 mm (é a que manda)», depois «19x2 =
     aprox. 38 mm» e «LONGE da Esp do iMos…».
6. No desenho, clicar nas duas arestas compridas (C1 e C2). Esperado:
   - elas ficam castanhas;
   - «Orlas: OC2»;
   - o código fica «3+3_OC2».
7. Marcar «CNC depois da colagem»: o código fica «3+3_OC2_CNC». Os excedentes ficam a 20 e 20.
8. **Gravar**. Esperado:
   - na linha de estado: «Código «3+3_OC2_CNC» gravado em 1 linha(s): ID 3. Qt: ID 3 = 2.
     +comp 20 / +Larg 20.»;
   - na folha, a linha ID 3 fica com Qt 2, Colar «3+3_OC2_CNC», +comp 20 e +Larg 20.
9. Duplo clique outra vez na mesma célula Colar. Esperado: o menu abre a editar o conjunto,
   com as arestas C1/C2 castanhas e a CNC no fim marcada.
10. «Copia Listagem CUT_RITE» / Enviar CUT-RITE (com a coluna Colar já criada no Cut-Rite).
    Esperado: a etiqueta mostra a medida da peça e a de corte (+20).

### Coluna «Colar», 3.ª ronda: nº de conjuntos (2026-11-12)

Pedidos do Paulo, no menu Colar:
- **Nº de conjuntos (já colados).** Campo novo, a 1 por defeito: é o produto final, já colado.
  A **Qt (coluna E)** de cada peça passa a ser peças dela no conjunto x nº de conjuntos.
  - `47+47` com 8 conjuntos → Qt 16 no ID 47.
  - `47+48` com 6 conjuntos → Qt 6 no ID 47 e Qt 6 no ID 48.

  A opção «Atualizar a Qt (coluna E) para o corte» vem marcada; desmarcada, a Qt não mexe.
  Ao lado do conjunto aparece «Qt a cortar (N conjunto(s)): ID … = …». Ao editar um conjunto
  já gravado, o nº de conjuntos lê-se da Qt (Qt 16 em `47+47` → 8 conjuntos).
- **Desenho da peça:** mostra a linha **selecionada** no quadro 2 (antes era sempre a 1.ª),
  com o ID e a descrição. Sem nada selecionado, mostra a 1.ª.
- **Saiu o campo «Quantas de cada»:** cada peça entra 1 vez; para a mesma peça entrar mais
  vezes usa-se **+1** no quadro 2.
- **Saiu o botão «Tirar o código destas peças».**

Atenção: com a opção marcada, a Qt fica **sempre** peças no conjunto x conjuntos, também
com 1 conjunto. Uma peça com Qt 2 no iMos, numa colagem `47+48`, fica com Qt 1 se o nº de
conjuntos ficar a 1: pôr 2.

Correção ao lado: desde 12-11 o Excel abre os `.xltm` como livro novo mesmo com
`Editable=True`, e o «Gravar» ia parar a Documentos sem mexer no modelo. Os scripts
`criar_modelo_lista_material_colar.py` e `atualizar_macros_modelo_lista_material.py` passam a
gravar com `SaveAs` no próprio modelo.

Confirmado numa cópia (obra 0993_04):
- o projeto VBA compila;
- 7+7 com 8 conjuntos → Qt 16; 8+9 com 6 conjuntos → Qt 6 e 6;
- 1+2 editado para 3 conjuntos → Qt 3 e 3, e ao reabrir o menu o campo mostra 3;
- o desenho passa do ID 1 para o ID 2 ao selecionar a 2.ª linha;
- o Cut-Rite recebe as 24 colunas.

O modelo `Lista_Material_IMOS_MARTELO_COLAR.xltm` do servidor foi refeito; o de 06-11 ficou
ao lado, como `..._COLAR_anterior_20261112_153504.xltm`. As listas feitas antes têm o menu
antigo: criar outra vez a lista para testar.

Guião de teste:

1. Produção → a obra de teste → Funções → «Lista Material com coluna Colar (ensaio)…» →
   «Criar nova (substitui a atual)» → passo 1 (CSV) e passo 2 (AUTOMATION).
2. Duplo clique na Colar de uma peça (ex.: ID 47). No quadro 2, selecionar o 47 e clicar
   **+1**: o código fica «47+47».
3. Em «Nº de conjuntos (já colados)», escrever **8**. Esperado: «Qt a cortar (8
   conjunto(s)): ID 47 = 16».
4. **Gravar**. Esperado: na folha, a Qt do ID 47 fica **16** e a Colar fica «47+47».
5. Novo conjunto: duplo clique na Colar do ID 48. Na lista de cima, selecionar o ID 49 →
   **Juntar ao conjunto**: fica «48+49».
6. Clicar no 48 e depois no 49, no quadro 2. Esperado: o desenho muda para a peça
   selecionada (ID, descrição e medidas).
7. Nº de conjuntos **6** → Gravar. Esperado: Qt **6** no ID 48 e Qt **6** no ID 49.
8. Duplo clique outra vez na Colar do ID 47. Esperado: o menu abre com «47+47» e o nº de
   conjuntos a **8**.
9. Confirmar que já não há o campo «Quantas de cada» nem o botão «Tirar o código destas
   peças».

### Coluna «Colar», 4.ª ronda: aviso O4L, Notas, roda do rato (2026-11-12, obra 1854)

Pedidos do Paulo, no menu Colar:
- **Aviso ao gravar com orla nos 4 lados (O4L) e peças de medidas diferentes.** Se as peças
  do conjunto não têm todas o mesmo Comp x Larg, aparece «Não é possível orlar os 4 lados
  (O4L) com peças de dimensões diferentes», com a lista das medidas.
  - «Sim» grava mesmo assim (o utilizador pode ignorar).
  - «Não» não grava.
- **Lista das peças (quadro 1):** coluna nova **Notas** no fim; a pesquisa também procura
  nas Notas.
- **Quadro 2 (conjunto):** colunas novas **Comp** e **Larg**.
- **Roda do rato** nas duas listas. As listas dos formulários do Excel não andam com a roda;
  um gancho do Windows (só no Excel, enquanto o menu está aberto) faz a lista onde o rato
  passou por último andar 3 linhas por passo. O menu liga-o ao abrir e desliga-o ao fechar.

Armadilha do VBA, já com teste: um `Declare` partido em duas linhas com « _» faz o
`AddFromString` deixar uma linha «()» solta no fim do módulo, e o projeto deixa de
compilar. Os `Declare` ficam numa linha só.

Confirmado numa cópia (obra 0993_04):
- o projeto VBA compila;
- o quadro 1 tem 9 colunas (Notas na última);
- o quadro 2 tem 7 colunas, com o Comp e o Larg da peça;
- o menu abre e fecha com o gancho da roda ligado;
- os conjuntos e a Qt da 3.ª ronda continuam certos.

A roda e o aviso só se veem no ecrã: é no teste.

O modelo Colar do servidor foi refeito; o anterior ficou ao lado, como
`..._COLAR_anterior_20261112_163035.xltm`. Na pasta do modelo há agora 3 COLAR «anterior»:
podem ser apagados quando o ensaio fechar. **A lista da obra 1854 já aberta tem o menu
anterior**: criar outra vez a lista para testar.

Guião de teste (obra 1854):

1. Produção → obra 1854 → Funções → «Lista Material com coluna Colar (ensaio)…» →
   «Criar nova (substitui a atual)» → passo 1 (CSV) e passo 2 (AUTOMATION).
2. Duplo clique numa célula da Colar. Esperado:
   - o quadro 1 tem a coluna Notas no fim;
   - com o rato por cima da lista, a roda faz a lista subir e descer.
3. Juntar ao conjunto duas peças com medidas diferentes (ex.: um Comp diferente). Esperado:
   - o quadro 2 mostra o Comp e o Larg de cada uma;
   - a roda também mexe nesta lista.
4. Clicar em «4 lados (O4L)» → **Gravar**. Esperado: o aviso «Não é possível orlar os 4 lados
   (O4L) com peças de dimensões diferentes», com as medidas das peças.
   - «Não» → nada é gravado.
   - Repetir e responder «Sim» → grava.
5. Com duas peças de medidas iguais e O4L → Gravar. Esperado: grava sem aviso.
6. Fechar o menu e confirmar que a roda do rato continua normal na folha do Excel.

### ResumoOrlas com as colagens (2026-11-12, modelo COLAR)

Pedido do Paulo: o separador **ResumoOrlas** (ml de orla por material e orla, com 8 % de
desperdício) passa a contar as colagens da coluna Colar. **Só no modelo de ensaio COLAR**:
`scripts/vba/colar/modResumoOrlas.bas`, que o `criar_modelo_lista_material_colar.py` mete no
modelo. O modelo de sempre fica igual.

Regras:
- **Linhas sem Colar:** tudo como antes.
- **Linhas com Colar, orlas nas colunas ESQ/DIR/CIMA/BAIXO:** são orlas **antes de colar**. A
  largura da fita vem da **Esp.Mat** (19 → 22 mm) e o resumo usa o nome real do material
  (`..._19MM`).
- **Orlas depois de colar:** vêm do código (O4L, OC2, OC1, OL2, OL1, OR) e contam **uma vez
  por conjunto**:
  - **nº de conjuntos** = Qt do 1.º ID do código ÷ peças desse ID no conjunto. Por exemplo,
    `47+47` com Qt 16 dá 8 conjuntos e `47+48` com Qt 6 e 6 dá 6 conjuntos, contados uma vez
    e não duas;
  - **medidas:** as comuns às peças do conjunto. Só se orla o lado em que batem certo: os
    comprimentos se o Comp é igual em todas, as larguras se a Larg é igual. Se não batem,
    conta a maior e aparece um aviso;
  - **ml** = (nº de comprimentos × Comp + nº de larguras × Larg) ÷ 1000 × nº de conjuntos. O4L
    são 2 + 2, e **OR conta 1 comprimento** (decisão do Paulo);
  - **fita e material:** a largura da fita vem da **Esp.Final** (Esp do iMos), e o material
    aparece com essa espessura (ex.: `..._30MM`), como já era;
  - **orla:** a da própria peça, a 1.ª preenchida nas colunas Orla. Sem nenhuma, aparece um
    aviso e o conjunto não conta.
- **O desperdício de 8 % e o arredondamento para cima ficam iguais.**
- **Avisos novos** (folha Avisos_Orlas e caixa no fim): `COLAR_CODIGO_INVALIDO`,
  `COLAR_ID_EM_FALTA`, `COLAR_QT_NAO_DIVIDE`, `COLAR_LADO_NAO_BATE`, `COLAR_SEM_ORLA`.
- ~~**Correção de passagem:** o `..._30.MM`~~ — **desfeita a 12-11**: o `.MM` é um alerta de
  propósito (material colado), ver a secção seguinte.

**Menu Colar.** O aviso que era só para o O4L passa a ver lado a lado:
- orla nos comprimentos (ou OR) com Comp diferentes → aviso;
- orla nas larguras com Larg diferentes → aviso.

Pode ignorar, como antes. O quadro de informação diz que lados batem certo, ex.: «Comp igual
(2394): pode orlar os comprimentos · Larg diferentes: não orlar as larguras». O código aceita
conjuntos como `3x2+5`: duas peças do ID 3 e uma do ID 5.

Confirmado em cópias das obras 0993_04, 1935_01 e 1854_01. Refiz em Python estas regras e
comparei **todas as linhas** do ResumoOrlas, com o resultado **igual**:
- sem colagens;
- com 3 conjuntos: `X+X_O4L` com 8 conjuntos, `A+B_OC2+OR` com o mesmo Comp e 6 conjuntos,
  e `Cx2+D_OL1` com Larg diferentes e 3 conjuntos (dá o aviso «lado não bate»).

O projeto VBA compila e todos os testes do Martelo passam. O modelo COLAR do servidor foi
refeito; o anterior ficou `..._COLAR_anterior_20261112_181748.xltm`.

Guião de teste (obra 1854):

1. Produção → obra 1854 → Funções → «Lista Material com coluna Colar (ensaio)…» → «Criar nova
   (substitui a atual)» → passo 1 (CSV) e passo 2 (AUTOMATION).
2. **Antes de colar:** botão «Calculo Orlas» → anotar os ml do separador ResumoOrlas.
3. Colar uma peça com orla consigo própria (ex.: ID 9), 2 vezes → «O4L», **8 conjuntos** →
   Gravar. Esperado: Qt do ID 9 = 16.
4. «Calculo Orlas» outra vez. Esperado:
   - as orlas das colunas do ID 9 contam com Qt 16 e fita da Esp.Mat;
   - a mais, na mesma orla, 2 × (Comp + Larg) ÷ 1000 × 8 + 8 %, arredondado para cima. Se a
     Esp do iMos é diferente da do material, isto aparece numa linha à parte, com o material
     na espessura do iMos (ex.: `_38MM`).
5. **Conjunto com Larg diferentes e orla numa largura:**
   - colar ID 11 + ID 12 → «1 largura (OL1)» → Gravar;
   - esperado no menu: o aviso «Não é possível orlar as larguras (Larg diferentes)…». Responder
     «Sim» e gravar;
   - «Calculo Orlas» → esperado o aviso «Colagens (coluna Colar): 1» e, na folha Avisos_Orlas,
     `COLAR_LADO_NAO_BATE`.
6. Conferir que as linhas sem Colar dão os mesmos ml que antes.

### ResumoOrlas: material colado `_38.MM` e linha sem orla; Excel «Livro2» (2026-11-12, obra 1854)

Pedido do Paulo, depois de testar a obra 1854 (ID 45 + ID 45, O4L, sem orla nas colunas):

- **Nome do material colado:** família + **espessura depois de colar** + `.MM`, ex.
  `AGL_MLM_ACACIA_H1277/ST9_38.MM`. A espessura é a **soma das Esp.Mat** das peças do conjunto
  (19 + 19 = 38; `9x2+11` com 19 dá 57). Pode diferir um pouco da Esp do iMos (coluna M): manda
  a soma. A fita é pela mesma espessura. O `.MM` é o **alerta de material colado**, de propósito.
- **O `_30.MM` das linhas sem código volta** (a «correção» da secção anterior foi desfeita): é o
  alerta antigo de material que vai ser colado.
- **Conjunto sem orla nas colunas Orla:** já não desaparece. Aparece a linha do material colado com
  os ml e o **Nome_Orlas vazio**, para o utilizador escrever a orla. Continua o aviso
  `COLAR_SEM_ORLA` (com o texto novo), sem o aviso de espessura da orla.
- **O que o utilizador escreve nessa linha fica:** ao carregar outra vez em «Calculo Orlas», a linha
  sai com a orla que ele escreveu (e o Stock/Enc, Marca, LargXEsp, ML e Obs dele).

Confirmado em cópias das obras 0993_04, 1935_01 e 1854_01. O ensaio em Python compara **todas as
linhas** do ResumoOrlas e o resultado é igual, sem colagens e com 4 conjuntos:
- os 3 conjuntos da secção anterior;
- um conjunto `X+X_O4L` de uma peça sem orla, que dá a linha `..._24.MM` ou `..._20.MM` com o
  Nome_Orlas vazio.

Escrevi `PVC_1.0_TESTE_MAO` nessa linha e gerei outra vez: a orla e a Obs ficaram.

**Excel «Livro2.xlsx — Guardar alterações?» antes do passo 4.**
- **Causa:** o passo 2 (AUTOMATION) corre num Excel visível com os alertas ligados. No fim, o
  Martelo fechava a lista da obra e fazia `Quit`. Se as macros tinham deixado um livro em branco
  aberto («Livro2»), o Excel perguntava se o queria gravar.
- **Correção:** `lista_material_excel_com.fechar_excel` desliga os alertas, fecha **sem gravar**
  os livros que esse Excel (só do Martelo) ainda tem abertos, e sai. A lista da obra já foi gravada
  antes.
- **Onde:** no passo AUTOMATION (`execute_lista_material_workbook_macro`) e na importação das
  ferragens (`import_hardware_cost`).

Testes novos em `tests/test_lista_material_excel_fechar.py`. O modelo COLAR do servidor foi refeito;
o anterior ficou `..._COLAR_anterior_20261112_191137.xltm`.

Guião de teste (obra 1854):

1. Produção → obra 1854 → Funções → «Lista Material com coluna Colar (ensaio)…» → «Criar nova
   (substitui a atual)» → passos 1, 2, 3. Esperado: **não aparece** a caixa «Livro2.xlsx —
   Guardar alterações?». Só abre o Excel da obra.
2. No Excel: colar o ID 45 consigo próprio (2 vezes) → «O4L» → nº de conjuntos à escolha → Gravar.
3. Botão «Calculo Orlas». Esperado:
   - o aviso `COLAR_SEM_ORLA`;
   - no ResumoOrlas, uma linha `AGL_MLM_ACACIA_H1277/ST9_38.MM` (38 = 19 + 19) com os ml e o
     **Nome_Orlas vazio**.
4. Escrever a orla nessa linha (ex.: `PVC_1.0_ACACIA`) e uma Obs → «Calculo Orlas» outra vez.
   Esperado: a linha fica com a orla e a Obs escritas.
5. Um conjunto **com** orla nas colunas (ex.: ID com PVC, `X+X_O4L`). Esperado: a linha
   `..._38.MM | PVC_...` com os ml depois de colar. As orlas das colunas ficam no material de 19.
6. Numa peça sem código com Esp do iMos ≠ Esp.Mat. Esperado: a linha `..._30.MM` como sempre.
