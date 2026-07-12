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

Estado: G1+G2+G3+G4 completos — fim do plano de configuração guiada.
Próximo: avaliação global do utilizador com dados reais; pendentes antigos
(placeholder "Selecionar origem…", ligação SISTEMAS_UNIAO, caixote de teste
completo) e a visão de IA nos menus.
