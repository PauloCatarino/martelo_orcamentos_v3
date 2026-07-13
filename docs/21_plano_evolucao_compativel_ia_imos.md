# Evolução compatível, IA assistente e integração iMos

Data da decisão: 13 de julho de 2026.

## Decisões confirmadas

- O Martelo V2 permanece como arquivo histórico apenas de leitura. Nesta fase
  não se importam nem editam os seus orçamentos no V3.
- Um orçamento V3 existente preserva preços, regras, materiais, operações e
  contexto do momento em que foi calculado.
- Uma nova versão/cópia de orçamento é um novo contexto editável e pode aplicar
  preços e regras atuais, sempre através de uma ação explícita do utilizador.
- No custeio, peças, ferragens e associados continuam visíveis. As operações
  existem e são editáveis no detalhe expansível da peça, mas não poluem a lista
  principal com uma linha por operação.
- Alterações estruturais de uma peça utilizada devem poder criar uma nova
  revisão. A revisão anterior fica inativa para novos orçamentos, sem alterar
  os orçamentos em que já foi usada.
- O SQL do iMos é sempre consultado em modo de leitura. O V3 nunca executa
  escrita na base do iMos.
- A IA acompanha o operador como supervisor: analisa, sugere, explica e alerta;
  não cria silenciosamente um orçamento final.
- Na primeira fase visual, a IA analisa PDF/imagem, reconhece padrões e sugere
  módulos compatíveis. As medidas são confirmadas pelo utilizador.

## Ordem de implementação

1. Estabilizar e validar a versão candidata UX-8.
2. Introduzir revisões explícitas no catálogo técnico.
3. Normalizar operações efetivas como detalhe expansível e snapshot versionado.
4. Unificar os editores de peça, associado, ValueSet e operação por contexto.
5. Criar relatórios industriais por peça, operação, máquina, tempo e custo.
6. Criar adaptador iMos isolado, auditável e exclusivamente de leitura.
7. Criar o assistente IA por etapas: documento → itens → ValueSets → módulos →
   auditoria do custeio.

## Primeira fundação técnica

Cada `def_peca` passa a ter uma série estável de revisão, um número sequencial
e uma ligação à revisão anterior. Criar uma revisão gera uma nova linha de
catálogo, copia operações e associados e desativa a anterior. Não atualiza
nenhuma linha de custeio já existente.

Esta infraestrutura é inicialmente de domínio/base de dados. O comando visual
"Criar nova revisão" será acrescentado depois da validação desta fundação.

## Estado da fase R1

- Migração `20260722_61` aplicada à base V3 local.
- As 65 peças existentes foram preservadas e iniciaram 65 séries independentes
  na revisão 1.
- Nenhuma peça, operação, associado ou orçamento foi recriado ou recalculado.
- Serviço de domínio criado para copiar uma peça completa, desativar a revisão
  anterior e impedir a criação de ramificações a partir de revisões antigas.
- Próximo passo: apresentar a revisão no catálogo e acrescentar o comando
  supervisionado "Criar nova revisão".

## Estado da fase R2 — interface de revisões

- A lista do Catálogo Técnico apresenta a coluna `Revisão`.
- O detalhe da peça mostra a revisão no cabeçalho e nos Dados Gerais.
- O separador `Revisões` mostra a cadeia, código, nome, estado e data.
- O comando `Criar nova revisão` apresenta previamente o código sugerido e as
  quantidades de operações e associados que serão copiadas.
- Depois da confirmação, a nova revisão abre automaticamente e a anterior fica
  visível apenas quando se ativa `Mostrar inativas`.
- Uma revisão histórica não pode ser reativada quando já existe uma revisão
  posterior.

Regra de trabalho reafirmada pelo utilizador: no final de cada modificação deve
ser entregue um guião de validação local com caminhos de menus, passos e
resultados esperados.

Validação local R2 recebida em 13 de julho de 2026: coluna de revisão, detalhe
R1, separador de histórico e diálogo de criação confirmados pelo utilizador com
capturas da aplicação real.

## Estado da fase O1 — operações dentro da peça no custeio

- A grelha principal continua a mostrar apenas peças, ferragens e associados.
- Uma linha de peça/ferragem selecionada disponibiliza `Operações da peça…`.
- O detalhe recompõe o snapshot congelado da peça com as ações do ValueSet do
  item e mostra operação, máquina, origem, ação, regra, quantidades, rasgos e
  tempos configurados.
- O topo do detalhe apresenta os custos consolidados de corte, orlagem, CNC,
  montagem/manual e produção já guardados na linha.
- A consulta inicial era exclusivamente de leitura: abrir o detalhe não
  atualizava catálogo, snapshot, preços, tempos ou custos.

Validação local O1 recebida em 13 de julho de 2026:

- Operações congeladas da peça, substituição por ValueSet do item e linha sem
  operações foram confirmadas pelo utilizador com capturas da aplicação real.
- A predominância de origem `Peça congelada` (aproximadamente 95% das linhas
  observadas) é coerente com o catálogo atual; `ValueSet do item` só aparece
  quando o ValueSet acrescenta, substitui ou desativa operações.
- A ferragem `DOBRADICA` revelou zero operações. O detalhe passa a servir também
  como controlo de qualidade: uma ferragem sem CNC/furação ou montagem pode
  indicar custo de produção incompleto.
- Esta deteção é uma futura entrada do supervisor IA: alertar e sugerir, deixando
  sempre a decisão e a confirmação ao utilizador.

## Estado da fase O2 — edição local de operações

- Migração `20260723_62` aplicada. A nova tabela normaliza as operações apenas
  quando uma linha é efetivamente alterada; nasceu vazia e não recalculou
  orçamentos existentes.
- O detalhe permite `Nova operação`, `Editar operação`, `Remover operação` e
  `Repor operações da origem`.
- Abrir o editor e cancelar não materializa nem altera o orçamento.
- Guardar materializa o conjunto efetivo daquela linha, identifica a origem como
  `Edição local`, marca a linha como editada localmente e executa imediatamente o
  recálculo completo do item.
- A janela atualiza custos de corte, orlagem, CNC, montagem/manual e produção
  sem obrigar o utilizador a fechar o custeio.
- A edição local não altera a definição da peça/ferragem no catálogo nem outras
  linhas que usem a mesma definição.
- Remover a última operação conserva um conjunto local vazio, permitindo testar
  conscientemente o custo sem operações. Repor elimina esse conjunto local e
  volta ao snapshot congelado da peça combinado com o ValueSet do item.
- Uma ferragem sem operações apresenta um aviso explícito de possível custo de
  produção incompleto, sem inserir automaticamente uma operação.

Validação local O2 recebida em 13 de julho de 2026:

- `Nova operação`, `Editar operação`, `Remover operação` e `Repor operações da
  origem` foram confirmados pelo utilizador na aplicação real.
- A edição local de CNC da `DOBRADICA` ficou visível com origem `Edição local` e
  custo de produção recalculado, mantendo as restantes linhas independentes.

## Estado da fase O3 — auditoria de operações do item

- O custeio disponibiliza `Auditar operações`, uma análise apenas de leitura de
  todas as peças e ferragens do item.
- Cada linha apresenta estado, tipo, código, número de operações efetivas,
  origens, máquinas, custo de produção e diagnóstico.
- `ATENÇÃO` identifica linhas sem operações; `VERIFICAR` identifica linhas que
  têm operações mas cujo custo de produção está vazio ou zero; `OK` confirma a
  presença de operações e custo.
- As ocorrências aparecem primeiro e podem abrir diretamente o detalhe de
  operações da linha para correção local.
- A auditoria não cria operações, não recalcula custos e não altera o orçamento.
  Este resultado determinístico será uma das entradas do futuro supervisor IA.

Validação local O3 recebida em 13 de julho de 2026:

- A auditoria de operações dentro do item, a navegação direta para a linha e o
  alerta de ferragem sem operações foram confirmados na aplicação real.
- O utilizador confirmou a complementaridade com a `Auditoria de Custeio`
  geral: supervisão imediata no item e segunda análise transversal a todos os
  orçamentos.

## Estado da fase O4 — relatório industrial de operações

- O separador `Relatórios` passa a ter uma área própria `Operações` para toda a
  versão do orçamento.
- Cada operação efetiva é apresentada numa linha com item, peça/ferragem, ordem,
  tipo, máquina, origem, ação, regra, quantidades, setup, tempo e custo atribuído.
- As quantidades, tempos e custos totais incluem a quantidade dos items da
  versão, permitindo leitura industrial e comparação entre centros.
- Quando existem várias operações do mesmo centro na mesma linha, o custo e o
  tempo consolidados são atribuídos apenas à primeira operação desse centro.
  Assim o relatório detalha as operações sem duplicar os totais financeiros.
- Linhas sem operações também aparecem, destacadas, com diagnóstico para
  confirmação do utilizador.
- Operações com origem `Edição local` ficam visualmente assinaladas.

Validação local O4 recebida em 13 de julho de 2026:

- O separador `Operações`, as linhas sem operações destacadas e a coluna
  `Diagnóstico` foram confirmados pelo utilizador na aplicação real.

## Estado da fase O5 — supervisor antes do PDF/email

- Antes de `Exportar PDF` e antes de `Enviar Orçamento por Email`, o supervisor
  executa a auditoria apenas sobre a versão atual.
- A saúde da versão usa como referência o item menos saudável, impedindo que um
  item correto esconda outro item com problemas.
- O diálogo aparece sempre: a 100% confirma a verificação; entre 75% e 99%
  apresenta avisos; abaixo de 75% apresenta alerta crítico.
- São mostradas quantidades de críticos, avisos e ocorrências, juntamente com as
  principais linhas/problemas encontrados.
- A opção predefinida é `Rever orçamento`. O utilizador pode escolher
  `Assumir e continuar`, preservando a autoridade humana sem silenciar a função
  de alerta do supervisor.
- Se a auditoria estiver tecnicamente indisponível, também existe aviso e a
  continuação exige confirmação explícita.
- O alerta disponibiliza `Abrir Operações`, que cancela a exportação e muda
  diretamente para o relatório industrial de operações da versão.
- `Abrir Auditoria do Custeio` cancela a exportação, abre a auditoria geral,
  filtra o orçamento e seleciona a ocorrência prioritária indicada pelo
  supervisor, reduzindo o caminho entre alerta e correção.

Validação local O5 recebida em 13 de julho de 2026:

- O aviso do supervisor antes da exportação foi confirmado na aplicação real.
- Os atalhos `Abrir Operações` e `Abrir Auditoria do Custeio` foram igualmente
  confirmados pelo utilizador.

## Estado da fase I1 — fundação SQL iMos somente de leitura

- `Configurações > Ligação iMos (leitura)` permite guardar servidor, base de
  dados e credenciais sem iniciar importações.
- A ligação usa o fornecedor SQL Server nativo do Windows e declara
  `ApplicationIntent=ReadOnly`.
- Toda a consulta passa pela mesma barreira de um único `SELECT`; comandos de
  escrita, execução e alteração são recusados antes de abrir a ligação.
- `Testar ligação e permissões` consulta a identidade efetiva e informa as
  permissões estruturais e de escrita da conta, sem executar qualquer escrita.
- Uma conta SQL somente de leitura é recomendada, mas não é obrigatória nesta
  fundação. Se a conta tiver escrita (como uma conta administrativa do iMos), o
  V3 apresenta o aviso e mantém a sua própria barreira limitada a `SELECT`.
- Um teste bem-sucedido indica servidor, base, login e número de tabelas
  consultáveis. Nesta fase nenhum dado iMos é importado para o V3.
- Próxima fase prevista: inventário somente de leitura do esquema/tabelas iMos
  para mapear os campos necessários à pesquisa e sugestão de módulos.

Validação local I1 recebida em 13 de julho de 2026:

- Ligação confirmada pelo utilizador a `SERVER_LE\SERVER_LE`, base `imos_le`.
- Foram identificadas 544 tabelas consultáveis, sem importar ou alterar dados.
- A conta atual possui permissões de escrita; o V3 apresentou o aviso esperado
  e manteve ativa a sua barreira própria de consultas `SELECT`.

## Fase I2 planeada — catálogo iMos e listas Excel (adiada)

Esta fase fica deliberadamente preparada no plano, mas não avança enquanto não
forem compreendidos o modelo de dados iMos e o resultado Excel pretendido.

1. Inventariar apenas metadados: esquemas, tabelas, colunas, tipos, chaves e
   relações, sem descarregar em massa os registos.
2. Selecionar com o utilizador algumas tabelas candidatas e consultar pequenas
   amostras controladas para distinguir peças, ferragens, materiais e módulos.
3. Criar um mapa explícito `campo iMos → campo Martelo/Excel`, versionado e
   validado pelo utilizador; nenhum nome de tabela será assumido automaticamente.
4. Definir o ficheiro/modelo Excel, folhas, colunas, filtros e regras de
   atualização para listas de peças e ferragens.
5. Gerar primeiro uma pré-visualização e um Excel de teste. Só depois da
   validação será disponibilizado o preenchimento normal.

Regras permanentes: consultas iMos apenas por `SELECT`, nenhuma escrita no SQL
iMos e nenhuma importação automática para catálogos/orçamentos do V3.

## Próxima fase recomendada — A1, dossier documental assistido

Sem depender ainda de uma chave API, criar a fundação do futuro assistente:

- novo separador `Documentos / Assistente` dentro do orçamento;
- anexar PDF, desenho ou imagem recebida do cliente;
- conservar o original e associá-lo ao orçamento e, opcionalmente, a um item;
- pré-visualizar/abrir o documento e registar estado (`Por analisar`, `Revisto`);
- preparar etapas visíveis `Documento → Itens → ValueSets → Módulos → Auditoria`;
- nesta fase não criar items, não estimar medidas e não alterar o custeio.

Numa fase A2 posterior, já com API configurada, a IA poderá descrever o
documento e sugerir linhas de items. Cada sugestão continuará dependente da
aceitação explícita do utilizador.

## Encerramento deste ciclo — estabilização e testes

Decisão do utilizador em 13 de julho de 2026:

- O presente ciclo de evolução fica concluído após a validação da fase I1.
- As fases A1 (`Documentos / Assistente`) e A2 (análise e sugestões com API)
  ficam guardadas apenas como funcionalidades extra para avaliação futura.
- A1 e A2 não fazem parte, por agora, do núcleo necessário do programa e não
  devem avançar sem uma decisão explícita posterior do utilizador.
- A prioridade passa a ser testar repetidamente o V3 em utilização real,
  identificar erros, esclarecer comportamentos e melhorar os fluxos existentes.
- Este mesmo chat mantém-se como registo de continuidade para as revisões,
  correções e melhoramentos encontrados durante os testes.
- Cada alteração futura deve continuar a terminar com um roteiro de validação
  manual, indicando menus, passos e resultados esperados.
