# Teste da Análise da Lista Material — obra 0722

## Preparação

Código na pasta principal do projeto, branch `main`. Reiniciar o Martelo V3
para carregar o novo módulo. Aplicar a migração **20260908_111** na base usada
pela aplicação. Em instalações com contas MySQL por utilizador, o administrador
deve executar `deploy/mysql_custo_mapeamentos.sql` nessa mesma base: concede
leitura, inserção e atualização apenas da nova tabela de mapeamentos aos perfis
existentes. `system_settings` continua protegida. As associações antigas são
lidas e preservadas; as novas ficam na tabela operacional partilhada.

1. Com um administrador, abrir **Configurações técnicas > Utilizadores e Acessos**.
2. Selecionar o utilizador de teste e atribuir:
   - **Análise da Lista Material — aceder ao módulo**;
   - **Análise da Lista Material — consultar e guardar custos**;
   - **Análise da Lista Material — aplicar correções**.
3. Abrir **Produção**, pesquisar a encomenda PHC **0722** e selecionar a versão
   de obra **01**, plano **01**. Confirmar:
   - Nome Enc IMOS IX: `0722_01_26_JF_VIVA`;
   - Nome Plano CUT-RITE: `0722_01_01_26_JF_VIVA`;
   - pasta de trabalho termina em `0722_01_01_JF_VIVA`, sem `ORIGINAL`.

Os ficheiros dentro de `ORIGINAL` permanecem exclusivamente de consulta.
Os testes automáticos com Excel foram realizados numa cópia local separada.

## Importação e revisão de materiais

1. Clicar **Lista Material_IMOS** e seguir as fases de importação CSV,
   AUTOMATION e listas de ferragens.
2. Na fase 3, além das listas existentes, o V3 procura
   `0722_01_26_JF_VIVA_5_Custo_Obra_Ferragens*.xlsx` em
   `C:\IMOS_Output_Batches`. Se existir uma única fonte, importa o separador e
   transfere o ficheiro para **5_Custo_Obra_Ferragens.xlsx** na obra. A fonte só
   é removida após verificar que o conteúdo está integralmente no destino.
   Numa repetição pode usar o ficheiro já arquivado na obra. Não altera o modelo `.xltm`.
3. Na fase 4, abrir a análise. Também está disponível em
   **Produção > Funções > Analisar/Completar Lista Material…**.
4. No separador **Materiais Woodstore**, confirmar uma linha por código do
   Excel, com número de peças e linhas afetadas.
5. Um código criado deve aparecer como **Código igual — validado**, com a
   coluna **Materialcode encontrado** a mostrar o código exato junto ao do
   Excel. A coluna **Esp. nominal** ignora as décimas de tolerância: 19,2,
   19,4 e 18,9 correspondem à espessura nominal 19. O stock não condiciona.
6. Para testar uma gralha, na Lista Material de trabalho guardar temporariamente
   `AGL_MLM_BRANCO_B3768/SC_12M` numa linha com `Esp.Mat = 12`. Fechar o Excel
   e clicar **Reanalisar ficheiros**. A referência de 12 mm deve ser proposta
   se constar no catálogo; alternativas de 19 mm não devem ser sugeridas.
7. Nenhuma proposta vem selecionada. Escolher a referência correta e clicar
   **Aplicar materiais selecionados**. Só a coluna Material é corrigida nas
   linhas com o código selecionado. Confirmar o registo em **LOG_MATERIAIS_V3**.
8. Confirmar a cópia anterior em **Analise_Lista_Material\Copias**. As correções
   não criam equivalências globais nem alteram Woodstore/Cut-Rite.
9. Se o Excel mudar entre análise e aplicação, a aplicação deve pedir nova
   análise, sem aplicar decisões a dados antigos.
10. Um material desconhecido ou uma falha de ligação não deve impedir
    **CUT-RITE > Enviar CUT-RITE**. Esse percurso não chama a análise.

Para placas, a comparação usa a espessura nominal **Esp.Mat**. A coluna
**Esp** da 0722 contém valores como 19,2 e 19,4, que não representam a
espessura nominal do código. A decoração e o acabamento são mostrados nas
alternativas; diferenças exigem escolha humana.

## Custos e preços guardados

1. Abrir **Custo de produção (parcial)**.
2. Se o novo ficheiro não foi importado na fase 3, usar **Importar custo de
   ferragens…**. O botão dá prioridade ao separador existente na Lista Material;
   nesse caso apenas reanalisa o Excel. Se faltar, procura primeiro
   **5_Custo_Obra_Ferragens.xlsx** (ou o nome completo desta versão) na pasta
   da obra e depois na pasta IMOS. Uma única fonte é importada diretamente;
   se houver várias, pede seleção. Sem fontes encontradas, a seleção abre
   na pasta da obra e o filtro permite também o nome curto. Uma segunda
   importação não duplica nem substitui o separador existente.
3. Confirmar os consumos do plano 0722, reconciliados com as páginas 1–2 do PDF:

| Material | m² de placas usadas |
|---|---:|
| AGL_MLM_BRANCO_B3768/SC_12MM | 12,34 |
| AGL_MLM_BRANCO_B3768/SC_19MM | 41,27 |
| AGL_MLM_LINHO_CANCUN_10MM | 57,78 |
| AGL_MLM_LINHO_CANCUN_16MM | 4,78 |
| AGL_MLM_LINHO_CANCUN_19MM | 145,92 |
| MDF_MR_MLM_BRANCO_B3002/MA_19MM | 75,72 |
| MDF_MR_MLM_BRANCO_B3822/MA_10MM | 2,77 |
| MDF_MR_MLM_BRANCO_B3822/MA_30MM | 1,73 |
| **Total** | **342,30** |

4. Verificar as orlas vindas de **ResumoOrlas**, sem nova percentagem de
   desperdício. Exemplo independente: 100 ml, largura 22 mm e preço 10 €/m²
   resultam em **22 €**. Preço de 0,20 €/ml resulta em **20 €**.
5. No novo ficheiro de referência existem 35 linhas de ferragens, 6 de SPP e
   3 de objetos comprados. O objeto sem nome IMOS também deve aparecer,
   identificado pela descrição. As cavilhas marcadas `fora` são incluídas.
6. O preço vem exclusivamente de **preco_liquido** do V3. Uma referência PHC
   ou nome IMOS com correspondência única permite associar automaticamente.
   Correspondências ambíguas permanecem por associar. Os preços IMOS não são usados.
7. Selecionar uma linha pendente e usar **Associar matéria-prima V3…**, ou
   clicar diretamente na célula **Referência V3 — descrição**. A janela abre
   pré-filtrada por Placas, Orlas ou Ferragens. Pesquisar palavras da descrição,
   Ref_LE, referência PHC, nome IMOS ou fornecedor. O filtro pode mudar para Todas.
   A seleção não é automática. Confirmar com **Associar e memorizar no V3**.
   A coluna passa a mostrar **Ref_LE — Descrição**. Conversões desconhecidas
   ficam pendentes; preço ausente não é convertido em zero.
8. A correspondência de custo é guardada no V3 e reutilizada em outras obras,
   distinguindo espessuras de placas, larguras/orlas e jogos de uniões.
   Não é uma correção global de nomes Woodstore. Numa obra nova recolhe o
   preço líquido atual; os preços já guardados numa obra antiga mantêm-se.
   Associações feitas antes desta atualização só ficam globais ao serem
   novamente confirmadas na janela de associação.
9. Para EGGER, um código/decoração e acabamento presentes no catálogo de
   referências permite encontrar o grupo. Só associa automaticamente quando
   existe uma única matéria-prima V3 compatível com grupo, tipo e espessura.
   O preço continua a vir do V3. Ambiguidades podem ser resolvidas na pesquisa,
   que destaca os grupos compatíveis.
10. As colunas **Comp, Larg e Esp** mostram as dimensões IMOS de SPP/comprados,
    incluindo intervalos como `511-2438`. Os jogos de uniões e nomes individuais
    são conservados. Ligações a matérias-primas de componentes e preços
    individuais de componentes podem ser usados; o preço total de um conjunto
    não é repetido automaticamente em cada componente.
11. Clicar **Guardar análise de custos**. Fechar e reabrir: mantêm-se o preço
   e a data usados. **Atualizar preços do V3** é uma ação explícita e exige
   guardar uma nova análise para conservar os novos preços. O histórico não é apagado.
12. As análises ficam em **Analise_Lista_Material**, junto da Lista Material,
   com fontes, hashes, linhas, preços, utilizador e pendências. Os preços das
   matérias-primas não são alterados por esta operação.
13. Usar **Inserir relatório no Excel** para acrescentar um separador de custos
    com resumo por Placas, Orlas, Ferragens, SPP e Comprados, detalhe e fórmulas.
    Corte, Orlagem, CNC, Montagem e Embalamento ficam identificados como pendentes.
    Cada relatório é novo; preserva os anteriores e guarda uma cópia do Excel antes da alteração.
14. Modificar/reotimizar um plano deve atualizar as quantidades na reanálise,
    mantendo os preços guardados. Não se soma duas vezes o mesmo nome de plano.

### Orlas quando o resumo ainda não foi gerado

No ficheiro de trabalho da 0722, `ResumoOrlas` estava vazio. Quando isso acontece,
o módulo calcula as orlas a partir das peças: comprimento para ESQ/DIR, largura
para CIMA/BAIXO, dimensões inteiras em mm, 8% uma única vez e arredondamento por
excesso em ml, seguindo `modResumoOrlas` do modelo. A largura é escolhida pelo
escalão da espessura final. Operações como `CNC_FRESAR` não são orlas.

A equivalência foi verificada nas 14 linhas do resumo de `ORIGINAL`: os metros
coincidem. Se o resumo já estiver preenchido, usam-se os seus valores, sem
acrescentar desperdício. O filtro de categoria **Orlas** permite vê-las isoladamente.

## Versões e permissões

1. Na 0418 versão 01, os planos `0418_01_01`, `0418_01_02` e `0418_01_03`
   pertencem ao mesmo custo. `0418_02_01` fica exclusivamente na versão 02.
2. Se um plano só tiver ficheiros de entrada e não tiver `.ptn`, aparece como
   consumo por apurar. Não é assumido como zero nem se inventa o consumo.
3. Com um utilizador que tenha apenas acesso ao módulo, a área de custos não
   aparece e o botão de aplicação fica desativado. Sem acesso ao módulo, a
   função informa que o administrador precisa de o atribuir.

## Limites desta primeira versão de teste

- Horas reais disponíveis no separador **Tempos por setor**, por consulta explícita.
  As tarifas usam `custo_hora` STD da máquina V3, com associação manual quando
  o nome/código não coincide exatamente. Não são usadas tarifas de série automaticamente.
- Um setor a 0% não é classificado como falha. O custo permanece parcial até
  serem confirmadas as horas e tarifas dos setores aplicáveis à obra.
- A leitura PTN está validada para `V12.00.5.1 / 2.15`. Outros layouts geram
  uma pendência explícita, sem cálculos presumidos.
- A consulta Woodstore em rede não pôde ser validada nesta sessão. Confirmar
  a ligação e o campo `Materialcode` dentro do V3 autenticado.
- As otimizações antigas por peça permanecem no código, mas já não são
  executadas pela fase 4. A nova fase centra-se em materiais e custos.

## Tempos reais Streamlit — oito setores

### Apresentação e preferências pessoais

1. Abrir a análise: a janela deve ocupar quase todo o ecrã e permitir maximizar.
2. Em **Tempos por setor**, arrastar a divisória entre as duas tabelas para dar
   mais espaço aos lançamentos e planos de corte. Ajustar também as larguras.
3. Fechar e reabrir com o mesmo utilizador: as larguras e a divisão devem manter-se.
   Outro utilizador tem a sua própria disposição, guardada em `user_prefs`.
4. Horas, desvios, quantidades, dimensões e preços mostram duas casas decimais.
   O relatório Excel novo usa o mesmo formato, mantendo os valores completos
   nos cálculos: 133 minutos × 90 €/h resulta em 199,50 €, mesmo mostrando 2,22 h.
5. Em **Produção**, marcar **👤 As minhas obras** deve selecionar o responsável
   do utilizador atual; desmarcar volta a Todos. Selecionar outro responsável
   desmarca o atalho. O filtro antigo de atrasadas deixa de ser aplicado,
   incluindo nas vistas antigas; os outros critérios da vista mantêm-se.

### Regressão da associação Linho 10 mm

Depois da atualização da base e das permissões, entrar com o mesmo utilizador
que recebia o erro. Abrir **Produção > 0722 > Funções > Analisar/Completar Lista
Material… > Custo de produção (parcial)**. Na linha
`AGL_MLM_LINHO_CANCUN_10MM`, clicar **Referência V3 — descrição**, selecionar a
matéria-prima correta e confirmar **Associar e memorizar no V3**. Deve apresentar
a referência/descrição e o custo, sem erro de `system_settings`. Guardar a
análise e reabrir para confirmar a persistência. Esta correção exige a atualização
da base; apenas reiniciar o executável não cria a nova tabela.

1. Reiniciar o Martelo. Abrir **Produção > obra > Funções >
   Analisar/Completar Lista Material… > Tempos por setor**.
2. Clicar **Consultar / atualizar tempos Streamlit**. A ligação configurada
   no V3 executa apenas SELECT, sem escrever no Streamlit/PHC.
3. Para `0722_01_26_JF_VIVA`, confirmar ano 2026, encomenda 0722, modelo 01.
   O modelo Streamlit corresponde à versão Martelo. Somam-se todas as versões
   Streamlit deste modelo; o modelo 02 fica separado.
4. Confirmar oito linhas: Stock, Preparação, Corte, Orlagem, CNC, Montagem,
   Embalagem e Expedição. Ver horas registadas, estimadas, desvio e estado.
   O quadro inferior identifica cada lançamento por data, pessoa/login,
   máquina, chave e plano. Registos com zero minutos não acrescentam horas.
5. Referência consultada em 08/09/2026: 0418 modelo 01 tem versões 01/02/03,
   33 lançamentos, preparação 0,0333 h, corte 10,9167 h, orlagem 6,55 h e
   CNC 5,4167 h. A 0722 modelo 01 tem estimativas mas nenhum lançamento real.
   Os valores podem aumentar com novos lançamentos.
6. Estado `N` significa não aplicável. Na montagem também se consulta
   `bd_existe_montagem`. Zero horas ou zero percentagem não prova ausência
   de trabalho; os casos sem informação suficiente ficam por confirmar.
   Minutos inválidos nunca são convertidos silenciosamente em zero.
7. Em **Custo de produção (parcial)**, filtrar **Produção**. Clicar na coluna
   **Referência V3 — descrição** de uma linha e escolher a máquina/centro de
   trabalho. Exemplo de teste: 1,5 h × 40 €/h = 60 €. Tarifa ausente fica pendente.
8. **Guardar análise de custos**, fechar e reabrir: tempos, data da consulta
   e tarifas mantêm-se. **Atualizar preços do V3** atualiza também as tarifas;
   consultar tempos novamente mantém as tarifas já associadas às mesmas linhas.
9. **Inserir relatório no Excel** deve incluir a categoria Produção no total,
   resumo dos oito setores e detalhe dos lançamentos abaixo das linhas de custo.
   Usar a Lista Material de trabalho, nunca a pasta `ORIGINAL`.
10. Uma falha de consulta deve dizer que não foi possível consultar. Se existir
    uma consulta guardada, mantém a respetiva data e identifica a falha recente.

O total continua parcial: horas lançadas por pessoas não equivalem necessariamente
ao tempo de ocupação da máquina. O módulo não inventa tempos para os completar.

## F0 (21-09-2026) — Excel sem #NAME?, verificação antes do Cut-Rite, Woodstore real

Obra de teste: **26.1610_01_01_JF_VIVA** (Nº Enc PHC 1610, Nome Plano CUT-RITE
`1610_01_01_26_JF_VIVA`). O Excel desta obra ficou com `#NAME?` em Ref_Cliente e
Processo quando o Martelo importou as ferragens com as macros desligadas.

1. **Produção** → Pesquisar `1610` → selecionar a linha `26.1610_01_01_JF_VIVA`
   → botão **CUT-RITE** → **Enviar CUT-RITE**.
2. Antes de abrir o Cut-Rite aparece **«Enviar CUT-RITE — verificação»** com:
   - `Tampo PostForming_30mm — 1 peça(s) em 1 linha(s) (Tampo)` em
     «MATERIAL QUE NÃO EXISTE NO WOODSTORE»;
   - `Ref_Cliente: #NAME? em 223 linha(s)` e `Processo: #NAME? em 223 linha(s)`.
3. Carregar em **Reparar e enviar** (com o Excel da obra FECHADO). O Martelo
   recalcula e grava a lista; volta a mostrar o aviso só com o Tampo PostForming.
   Carregar em **Enviar assim** para seguir, ou **Cancelar** para parar.
4. Abrir o Excel da obra → folha LISTAGEM_CUT_RITE: colunas Ref_Cliente = `2607010`
   e Processo = `1610_01_01_26` (já não `#NAME?`).
5. Numa obra com todos os materiais no Woodstore e sem erros, o envio segue
   direto e a linha de estado diz «Verificação feita: todos os materiais existem
   no Woodstore.».
6. **Lista Material_IMOS** numa obra → o «Assistente Lista Material — configuração
   da obra» mostra, em verde, «Woodstore ligado (só leitura): N placas, M
   materiais.» em vez de «Ligação ao armazém/HOMAG ainda não configurada».
   Sem rede, a faixa fica amarela e diz «Woodstore sem ligação neste momento…».
7. Na **Análise da Lista Material**, «Importar custo de ferragens…», «Aplicar
   materiais selecionados» e «Inserir relatório no Excel» já não deixam `#NAME?`
   na LISTAGEM_CUT_RITE.

## F1 + F2 (21-09-2026) — assistente fora do arranque; materiais: referências, decisões e pedido às compras

Obra de teste: **26.1610_01_01_JF_VIVA**. «Matérias usados» desta obra:
`AGL_MLM_LINHO_CANCUN_10/16/19MM`, `MDF_HID_BRANCO_B3002/MA_19MM`, `AGL_MLM_BRANCO_B3768/SC_12/19MM`.

**F1 — o assistente já não abre ao criar a Lista Material**
1. **Produção** → selecionar uma obra com Nome Enc IMOS IX → **Lista Material_IMOS**.
   Aparece logo «Lista Material criada — passo 1 de 4» (ou a pergunta «já existe»),
   sem o «Assistente Lista Material — configuração da obra». As preferências
   guardadas para o cliente continuam a ir para a folha ASSISTENTE do Excel.

**F2 — separador Materiais Woodstore**
2. **Produção** → selecionar `26.1610_01_01_JF_VIVA` → **Funções** → **Analisar/Completar
   Lista Material** (ou o passo 4 de 4). Separador **Materiais Woodstore**.
3. Por cima da tabela: «7 materiais: 6 validados no Woodstore, 1 sem código (0 já
   decididos, 1 por decidir).»
4. Coluna **Verificação da referência**: `Ref B3768 consta nas «Matérias usados».`,
   `CANCUN LINHO consta…`, `Ref B3002 consta…`; no Tampo: `Não aparece nas
   «Matérias usados» da obra — confirmar.` (fundo amarelo).
5. A linha do `Tampo PostForming_30mm` está a rosa. Na coluna **Decisão / referência
   proposta** escolher **Fora do Cut-Rite (comprado / cortado à parte)** →
   **Aplicar materiais selecionados**. O estado passa a «Sem código no Woodstore —
   decidido: Fora do Cut-Rite…» e o resumo a «1 já decididos, 0 por decidir».
6. Fechar → **CUT-RITE** → **Enviar CUT-RITE**: o aviso do Tampo já NÃO aparece; a
   barra de estado diz «1 peça(s) sem material no Woodstore, já decididas na Análise…».
7. Pedido às compras: voltar à Análise, no Tampo escolher **Pedir criação no
   Woodstore** → botão **Pedido de criação no Woodstore (PDF)…**. Abre
   `Pedido_Material_Woodstore_1610_01_26_JF_VIVA.pdf` (pasta da obra) com nome,
   espessura nominal 30, 1 peça 1475 × 620, 0,91 m², orla PVC_1.0_BRANCO.
8. **Nome temporário…**: pede o nome (sugere `TEMP_TAMPO_POSTFORMING_30MM`); ao
   aplicar, a coluna Material do Excel passa a esse nome e fica registado.
9. Troca de referência: numa obra cuja «Matérias usados» diga, p. ex., `M6307` e a
   lista traga `…M6305…`, a verificação fica cor de laranja («referência
   parecida: confirmar…») e o combo oferece o código do Woodstore com M6307.

## F3 (21-09-2026) — separador «Procedimentos da listagem» (obras lowcost)

O analisador dos procedimentos manuais estava sem chamada desde a 1.0.15. Volta
dentro da Análise, decidido por regra. Medido nas obras 1568/1562/1582: na 1568,
das 496 alterações feitas à mão, depois de aplicar as regras sobram 171 células
diferentes — quase todas o texto da nota CNC («RECORTE L» vs «CNC RECORTE L»,
acerta-se na configuração) e notas próprias da obra («MONTADO», «NICHO ABERTO»).

1. **Produção** → selecionar uma obra lowcost com a Lista Material acabada de gerar
   (passos 1 a 3) → passo 4 (ou **Funções** → **Analisar/Completar Lista Material…**)
   → separador **Procedimentos da listagem**.
2. **Configuração da obra…** abre o antigo assistente (puxador, nota CNC_FRESAR,
   exceções, regras ativas, «Guardar como minhas preferências para este cliente»).
   A linha por cima dos botões resume o que ficou escolhido.
3. **Analisar procedimentos**: aparece uma linha por regra, com nº de alterações,
   peças, «Para confirmar» e um exemplo. Regras: CNC_FRESAR; Notas das costas
   (piso/fração do artigo: `RP_13_P1_F` → `PISO 1º - F`, `RP_B_05_RC_ESQ` →
   `RES DO CHAO ESQUERDO`); Notas de lacagem/puxador («LACAR 1 FACE + PUX TIC-TAC»,
   «NÃO LACAR»); Vista Vertical, Remate Teto e Rodapé Frente em barras.
4. **Substituir orla em massa…**: escolher `PVC_0.4_LINHO` → escrever `PVC_1.0_LINHO`,
   desmarcar lados/peças; a janela mostra «N células em M peças». **Propor
   substituição** acrescenta a linha «Substituição de orla: PVC_0.4_LINHO →
   PVC_1.0_LINHO».
5. Desmarcar as regras que não quer → **Aplicar regras marcadas** → confirmar.
   Com centenas de células demora ~1 minuto (cursor de espera). Fica a cópia
   `..._antes_procedimentos_....xlsm` em `Analise_Lista_Material\Copias`.
6. **Rever peça a peça…** abre a revisão antiga só com as regras marcadas (inclui as
   «Para confirmar», que o bloco não aplica).
7. Se o Excel foi mexido depois de analisar, aplicar recusa: «O Excel mudou desde a
   análise. Volte a analisar antes de aplicar.»

## Grelha tipo Excel + F4 (21-09-2026) — editar a listagem; custo V3 → PHC → IMOS

**Grelha «Rever / editar a listagem»** (separador Procedimentos da listagem)
1. Obra `26.1568_01_01_JF_VIVA` (ou outra lowcost) → Análise → **Procedimentos da
   listagem** → **Analisar procedimentos** → **Rever / editar a listagem…**.
2. A listagem inteira aparece com as propostas das regras marcadas já pintadas
   (amarelo); vermelho = confirmar; linhas a remover riscadas a cinzento.
3. Clicar no cabeçalho **Descricao** → desmarcar tudo → marcar `Costa` → **OK**: só
   ficam as costas e o cabeçalho mostra «Descricao ▼». **Limpar filtros** repõe.
4. Selecionar uma linha → **Ctrl+C** → **Ctrl+V** (cola depois) ou **Ctrl+Shift+V**
   (cola antes): aparece uma linha verde «nova». **Ctrl+-** elimina; **Delete** limpa
   as células; **Ctrl+R** repõe a linha como está no Excel; **Ctrl+Z** anula a última operação e **Ctrl+Y** refaz. Botão direito tem o mesmo.
5. Colunas com fórmula (Cliente, Ref_Cliente, Processo, ID, Esp.Mat, Esp.Final,
   Grafico Orlas) não se editam: o Excel calcula-as, também nas linhas coladas.
6. **Aplicar no Excel** → a barra de estado diz quantas células, linhas eliminadas e
   novas. Cópia antes em `Analise_Lista_Material\Copias\..._antes_grelha_...`.
   Ensaio numa cópia da 1568: 278 células, 69 eliminadas, 1 colada em 19 s.

**F4 — custo (separador Custo de produção (parcial))**
7. Obra `26.1610_01_01_JF_VIVA` → Análise → **Custo de produção (parcial)**. No topo
   (amarelo): «Custo PROVISÓRIO…» com ✓/✗: obra Producao ✗; Placas sem plano de
   corte ✗; Orlas 8 de 8 ✓; «Ferragens: V3 9 · PHC 13 · IMOS provisório 2 · sem preço
   2» ✗; Tempos ainda não consultados ✗.
8. Na tabela, a coluna de estado diz a fonte: «2.ª opção PHC (custo): PHC 2.59 € / un»,
   «PHC 1.267 € por 100 → 0.01267 € / un», «Preço IMOS — PROVISÓRIO».
9. A cavilha `FC00304` está ao QUILO no PHC: não entra pelo PHC (fica IMOS 0,01 €).
10. **Mapear ferragens passo a passo…**: «1 de N», dados da ferragem e três botões —
    «1.º Associar à matéria-prima V3…» (fica memorizado), «2.º Usar PHC: … €» (com
    «— CONFIRMAR» quando a unidade não é UN), «3.º Usar IMOS (provisório)». Saltar /
    Anterior / Fechar. Depois **Guardar análise de custos**.
11. Com a obra Finalizada/Arquivada, plano de corte, tudo com preço V3/PHC e os oito
    setores concluídos, o quadro fica verde: «Custo FINAL da obra — tudo apurado.»

## Ferragens a partir dos separadores do Excel (21-09-2026)

A origem das ferragens do custo passa a ser **1_FERRAGENS, 2_PURCH e 3_SPP** (os que
existirem com dados), porque são corrigidos à mão em cada obra. Do
5_Custo_Obra_Ferragens (IMOS) só vêm o preço IMOS de referência e as cavilhas
«Na lista = fora».

1. Obra `26.1610_01_01_JF_VIVA` (o 2_PURCH da máquina de lavar já foi apagado) →
   Análise → **Custo de produção (parcial)**. Nas pendências/avisos: «Ferragens a partir
   de 1_FERRAGENS (21), 3_SPP (10) + 1 fora da lista (cavilhas).»
2. A máquina de lavar já não aparece. O varão aparece em ml (8,927 ml = soma de
   quantidade × comprimento das peças do 3_SPP). O suporte de prateleira FF00043 soma as
   duas linhas (148).
3. O TIC-TAC FF00132 fica com preço V3 (associação antiga reaproveitada pela Ref PHC).
4. **Mapear ferragens passo a passo…**: o nome mostra de onde vem, p. ex.
   «[1_FERRAGENS · RP_A_05(b)]». Para o Calçeiro (sem Ref PHC) ou um acessório só de
   representação / do cliente → **Não contabilizar nesta obra** (custo 0, conta como
   resolvido). O «Canto Rodape» fica com o preço IMOS (1,10 €) achado pela descrição.
5. Editar o Excel (p. ex. mudar a quantidade de uma ferragem em 1_FERRAGENS), gravar,
   fechar → **Reanalisar ficheiros**: a quantidade nova entra e o preço escolhido mantém-se.
6. Numa obra sem nenhum dos três separadores: «Sem separadores 1_FERRAGENS / 2_PURCH /
   3_SPP com dados: ferragens sem custo nesta obra».

### Conciliação com o IMOS e «Não considerar nesta obra» (21-09-2026)

7. Na 1610, por baixo do resumo de custos aparecem três linhas de conciliação:
   «No IMOS mas não nos separadores (retirado à mão, não conta): MAQ_LAVAR_ROUPA»,
   «Fora da lista mas contam (a máquina aplica-as ao furar): CAVILHA_08p1X30_COLA» e,
   quando houver, «Nos separadores mas não no IMOS (acrescentado ou mudado à mão, conta)».
8. Selecionar a linha do Calçeiro (ou várias, com Ctrl) → **Não considerar nesta obra /
   voltar a considerar**: fica cinzenta, «NÃO CONSIDERADA NESTA OBRA», o total desce e o
   quadro diz «não consideradas nesta obra 1». O preço e o mapeamento V3/PHC não mudam.
   **Guardar análise de custos** → fechar e reabrir: continua fora. Carregar outra vez
   no botão volta a pô-la no custo.
9. No passo a passo, **Não considerar nesta obra** faz o mesmo e passa à seguinte.
10. O Canto Rodapé (sem Ref PHC) fica com o preço IMOS de 1,10 € (3.ª opção).
