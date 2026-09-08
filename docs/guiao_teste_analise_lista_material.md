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
