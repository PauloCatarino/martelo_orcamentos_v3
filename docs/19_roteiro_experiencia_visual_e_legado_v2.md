# Roteiro de experiência visual, auditoria e legado V2

Registo criado em 12 de julho de 2026 a partir das decisões do utilizador e
das quatro maquetes visuais fornecidas para o Martelo Orçamentos V3.

## Decisões funcionais

- A desativação continua a ser eliminação lógica na base de dados.
- Registos inativos ficam ocultos por defeito em todas as listas.
- As páginas que permitem reativar dados devem oferecer **Mostrar inativos**.
- Uma linha desativada não deve permanecer visível na lista normal apenas com
  `Ativo = Não`, porque isso se confunde com um registo utilizável.
- A eliminação física só será avaliada no encerramento do desenvolvimento.
- Ações gerais **Duplicar** ou **Gravar como** devem ser removidas quando a
  edição do próprio registo já oferece **Gravar como**.
- As tabelas devem ter colunas redimensionáveis e guardar as larguras por
  utilizador e computador.
- Configurações deve apresentar apenas áreas reais e cada acesso deve ter um
  tooltip completo.

## Fases

### Fase UX-1 — Configurações e Definições de Peças

- Remover os acessos ainda não desenvolvidos **Materiais**, **Ferragens** e
  **Regras de Custeio**.
- Organizar os acessos existentes numa grelha visual e documentá-los por
  tooltip.
- Remover **Duplicar Peça**.
- Substituir a alternância Lista/Árvore por uma única árvore-tabela, agrupada
  por família e com colunas de dados.
- Manter inativas ocultas por defeito e permitir mostrá-las para reativação.

Estado: implementação inicial concluída; aguarda validação visual local.

### Fase UX-2 — Uniformização de tabelas

- Inventariar cada `QTableWidget`, `QTableView` e `QTreeWidget` funcional.
- Aplicar modo `Interactive`, impedir que uma coluna `Stretch` bloqueie as
  restantes e ligar `ligar_persistencia_larguras` com chave estável.
- Confirmar tabelas principais, tabelas dentro de separadores e tabelas criadas
  em diálogos.
- Adicionar testes de importação e uma verificação automatizada de cobertura.

O mecanismo comum já existe e é usado em muitas páginas. Foram identificadas
exceções visíveis como Histórico do Orçamento, Produção e algumas tabelas
auxiliares/detalhe. Devem ser corrigidas em lote separado para reduzir o risco.

Estado em 12 de julho de 2026:

- persistência acrescentada ao Histórico do Orçamento, transformações dos
  associados, seleção de clientes e seleção de matérias-primas;
- Chaves ValueSet, Modelos ValueSet, linhas de modelos, Regras de Quantidade e
  Margens ocultam inativos por defeito e permitem **Mostrar inativos**;
- as tabelas destas configurações passaram para larguras interativas e
  persistentes;
- Produção conserva a sua persistência própria, que também guarda a
  configuração das colunas;
- falta o lote de tabelas auxiliares em diálogos, que deve usar chaves estáveis
  sem alterar tabelas pequenas de cenários nem árvores de navegação.

### Fase UX-3 — Início e dashboard de orçamentos

- Criar o Painel Inicial com indicadores reais: em curso, adjudicados,
  pendentes e alertas com impacto financeiro.
- Mostrar orçamentos recentes, centro de avisos, fluxo sugerido e atalhos.
- Criar um dashboard dedicado de Orçamentos, separado da lista operacional.
- Os cartões devem abrir a lista já filtrada; não podem ser apenas decorativos.
- Acrescentar uma introdução curta ao Martelo V3 no arranque. A animação deve
  durar poucos segundos, poder ser ignorada e não atrasar carregamentos.

Estado em 12 de julho de 2026:

- o ecrã Início passou a apresentar indicadores reais de Orçamentos e
  Produção, orçamentos recentes, avisos explicáveis e atalhos operacionais;
- os orçamentos recentes abrem por duplo clique e as larguras ficam guardadas;
- a indisponibilidade da fonte de Produção não bloqueia o painel;
- foi criado **Orçamentos > Dashboard**, dedicado à componente comercial e sem
  os cartões de Produção;
- falta avaliar visualmente o painel e desenvolver a introdução curta de
  arranque, que deve ser opcional e não bloquear o trabalho.

Evolução UX-3.1 após a primeira validação visual:

- adicionada pesquisa e filtros Estado, Cliente, Utilizador e Período, com
  data/hora visível;
- pesquisa, Cliente e Utilizador afetam também Produção; Estado e Período são
  de Orçamentos, evitando misturar vocabulários de estado diferentes;
- acrescentados Em desenho, Produções finalizadas, Valor em produção e
  Produções sem preço, perfazendo dez indicadores no Início;
- avisos separados em Orçamentos e Produção;
- tabela recente compactada e ampliada com Ref. Cliente, Enc. PHC, Descrição,
  Data e Utilizador.
- a tabela recente e a lista principal de Orçamentos passaram a partilhar o
  mesmo estilo visual: cabeçalho castanho, estados por cor, código e total em
  destaque, seleção suave, linhas sem grelha pesada e preços manuais em ocre.
- introdução visual integrada depois do login: aparece enquanto a janela
  principal é preparada, dura no mínimo cerca de 3 segundos, pode ser ignorada
  e não volta a aparecer depois de logout/login na mesma execução.

### Fase UX-4 — Auditoria orientada a euros

- Expandir a auditoria para corte, orlagem, CNC e operações manuais.
- Validar dimensões, quantidades, material, desperdício, tarifa, setup, tempo,
  máquina, acabamento e regras de quantidade.
- Classificar ocorrências por impacto: custo em falta, custo possivelmente
  subavaliado, custo possivelmente duplicado e dado apenas informativo.
- Sempre que possível, traduzir o problema em euros ou intervalo estimado e
  indicar a origem e a ação de correção.
- As correções continuam supervisionadas e confirmadas pelo utilizador.

Estado em 12 de julho de 2026 — primeira entrega funcional:

- criado `Orçamentos > Auditoria de Custeio`, separado da Auditoria do
  Catálogo porque analisa dados congelados dos orçamentos e não configuração;
- valida material com consumo sem preço, corte, orlagem e CNC previstos sem
  custo, e operações manuais com tempo mas sem custo;
- compara o total de produção com corte + orlagem + CNC + manual;
- diferenças conhecidas são apresentadas em euros; quando falta tarifa/preço,
  mostra **€ por determinar** e o dado necessário para calcular;
- a grelha permite filtrar por severidade/categoria, pesquisar e abrir o
  orçamento afetado;
- a análise é apenas de leitura e não corrige nem recalcula automaticamente.
- por defeito, a Auditoria de Custeio mostra o utilizador autenticado; o filtro
  **Utilizador** permite escolher outro responsável ou **Todos**.

Evolução UX-6:

- saúde percentual agrupada por orçamento/item, penalizada por críticos e
  avisos e acompanhada do impacto conhecido;
- valida quantidade, dimensões reais, desperdício superior a 100%, tempos
  negativos e custos calculados que foram excluídos manualmente;
- exclusões manuais apresentam em euros o custo retirado, para confirmação;
- abrir uma ocorrência navega para o item e seleciona a linha exata do custeio;
- o cartão Alertas de custo do dashboard inclui críticos e impacto conhecido da
  Auditoria de Custeio.
- a coluna **Observações produção** também alimenta a Saúde: mensagens que
  indiquem dados/preços incompletos, custos não calculados, tarifas, materiais,
  operações ou quantidades em falta criam ocorrência e reduzem a pontuação;
  notas neutras são ignoradas e alertas já detetados estruturalmente não são
  duplicados.

### Fase UX-5 — Consulta de orçamentos V2

- Os orçamentos V2 são histórico de consulta e não precisam de ser editáveis.
- Preferência atual: ligação direta, apenas de leitura, à base de dados V2,
  evitando copiar todo o histórico para a V3.
- Criar uma camada de adaptação que devolva um modelo de consulta estável sem
  misturar entidades V2 com os modelos transacionais V3.
- Mapear primeiro cabeçalho, cliente, obra, estado, data, total, versão e linhas
  resumidas; anexos e detalhe técnico ficam para uma segunda passagem.
- A interface deve identificar claramente a origem **Arquivo V2** e impedir
  qualquer escrita na ligação antiga.
- Antes de implementar, documentar esquema, volume, disponibilidade da base V2,
  credenciais de leitura e comportamento quando o servidor estiver offline.

Estado em 12 de julho de 2026 — infraestrutura inicial:

- criado `Orçamentos > Arquivo V2`, com pesquisa, Estado, colunas de consulta e
  identificação explícita da origem V2;
- adaptador separado dos modelos V3, com descoberta de tabela/colunas e limite
  de registos;
- guarda SQL bloqueia qualquer instrução que não seja de leitura;
- a configuração recomenda e exige operacionalmente uma conta MySQL apenas com
  `SELECT`; exemplos foram acrescentados a `.env.example`;
- a página trata configuração em falta, servidor offline e esquema não
  reconhecido sem afetar a aplicação V3;
- as credenciais estavam inicialmente apenas em `.env.example`; foram
  transferidas para o `.env`, que é o ficheiro efetivamente lido pela aplicação.

Validação com a ligação fornecida:

- ligação confirmada e esquema real confrontado com o código V2 local;
- tabela `orcamentos` ligada por `client_id` a `clients` e por `created_by` a
  `users`; 500 registos testados com número, versão, cliente, estado, data e
  utilizador preenchidos;
- a conta fornecida tem privilégios de escrita no servidor e deve futuramente
  ser substituída por uma conta dedicada apenas com `SELECT`;
- como defesa adicional, o adaptador ativa transações MySQL read-only em cada
  sessão e mantém a guarda local que bloqueia comandos de escrita.

### Fase UX-7 — Consolidação visual

- o helper de larguras converte agora todas as colunas ligadas para modo
  interativo, mesmo que a página as tenha criado como Stretch/ResizeToContents;
- persistência acrescentada aos diálogos operacionais de preços ValueSet,
  conversão de orçamento, escalões, importação ValueSet, módulos, propagação,
  referência duplicada, operações ValueSet e sincronização Produção/PHC;
- estilo global moderado para botões, campos, seletores e grupos, mantendo as
  sobreposições específicas das páginas e a identidade castanho/bege.
- **Atualizar peça da biblioteca** passou a aceitar várias linhas selecionadas;
  peças importadas de módulos atualizam Definição de Peça e ValueSet atual do
  item sem apagar estrutura, fórmulas, quantidades ou desvios guardados no
  módulo; o item é recalculado uma única vez no fim do lote.

## Princípios visuais retirados das maquetes

- Navegação lateral simples e consistente.
- Castanho/bege como identidade, com verde, azul, ocre e vermelho apenas para
  estados e alertas.
- Hierarquia clara: título, resumo, ações, filtros, tabela e detalhe contextual.
- Alertas junto do objeto que afetam e com ligação direta para correção.
- Espaçamento generoso, cartões discretos e menos botões sem função.
- Aspeto visual nunca deve inventar dados; todos os indicadores devem vir de
  serviços reais e ter estado vazio/erro bem definido.
