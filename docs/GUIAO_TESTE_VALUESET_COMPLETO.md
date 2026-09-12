# Guião de teste — ValueSet (tudo o que mudou)

12-set-2026. Junta num só sítio os seis guiões das rondas de hoje.
**Vá marcando os `[ ]` à medida que passa.**

Substitui, para efeitos de teste, os ficheiros
`GUIAO_TESTE_NAVEGADOR_CHAVES_VALUESET.md`,
`GUIAO_TESTE_AUDITORIA_CHAVES_VALUESET.md`,
`GUIAO_TESTE_RENOMEAR_CHAVE_VALUESET.md`,
`GUIAO_TESTE_COPIAR_CHAVES_VALUESET.md`,
`GUIAO_TESTE_VALUESET_ORCAMENTO.md` e
`GUIAO_TESTE_VALUESET_ITEM_E_COLUNAS.md`, que ficam como estão.

---

## Antes de começar

**O que mudou, em três linhas.** As três tabelas de ValueSet — a do **modelo**,
a do **orçamento** e a do **item** — tinham ~100 linhas espalhadas por ~70
chaves, em 17 a 23 colunas. Passaram a ter um navegador de chaves à esquerda,
chips de grupo, pesquisa, faixas de grupo e colunas que se arrastam. Além disso,
as **chaves** ganharam ferramentas próprias: auditoria, renomear com propagação,
e copiar entre modelos.

**Nada disto mexe em preços, custeio ou orçamentos já feitos.** As únicas
escritas novas são as que você mandar fazer de propósito (renomear uma chave,
copiar chaves entre modelos).

**O que eu já testei, e onde não vale a pena perder tempo:**

| Já verificado por mim | Como |
|---|---|
| 4946 testes automáticos | passam todos |
| As contagens dos navegadores | com os seus dados reais (1_ROUP_STD, ROUP_BRANCO, 260888_01, item 239) |
| Renomear uma chave e repor | na base de **trabalho**, nunca na real |
| Copiar chaves entre modelos | na base de **trabalho**; previsão bate certo com o escrito |
| A faixa a seguir a coluna arrastada | medido em píxeis |

**O que só você pode confirmar:** se o comportamento faz sentido no seu
trabalho, e se nada do que já usava se portou de outra maneira.

**Se alguma coisa falhar:** anote o ecrã, o que carregou e o que esperava. Não
precisa de desfazer nada — excepto nos pontos marcados com ⚠, que alteram dados
e têm sempre o passo de "repor" a seguir.

---

# Sessão A — o essencial (10 minutos)

Se só tiver tempo para uma coisa, faça esta. É aqui que está o risco de eu ter
partido algo que já funcionava.

## A1. As setas ↑↓ continuam certas
**Configurações → Modelos ValueSet → 1_ROUP_STD**

- [ ] Escolha uma linha do meio de um bloco e repare no número da coluna **Ordem**.
- [ ] Carregue em **↑**. A linha sobe uma posição *na tabela como a está a ver*,
      e a coluna Ordem acompanha. **Não salta para outro sítio.**
- [ ] Selecione duas linhas seguidas (Ctrl ou Shift) e carregue em **↓**:
      descem juntas, mantendo a ordem entre si.
- [ ] Feche o bloco de um grupo e mova uma linha de outro grupo: não troca com
      nenhuma das escondidas.

> As faixas **não reordenam** a tabela — seguem a coluna Ordem. Se reordenassem,
> a seta mandava a linha para um sítio diferente daquele que vê.

## A2. O que já usava, no ValueSet do Orçamento
**Orçamentos → (um orçamento) → ValueSet**

- [ ] **Importar Modelo** (acrescentar e substituir)
- [ ] **Nova Linha**, **Editar Linha**
- [ ] **Copiar / Colar Dados** (Ctrl+C / Ctrl+V) — e a linha colada **fica com a
      marca ✎**, como sempre ficou: foi você que a mexeu
- [ ] **Limpar Dados**, com uma e com várias linhas selecionadas
- [ ] **Ativar/Desativar** e o **Mostrar inativas**
- [ ] O aviso de **prioridade repetida** continua a aparecer
- [ ] Duplo clique numa **faixa** não abre nada; botão direito sobre uma faixa
      não abre menu

## A3. Os botões próprios do Item
**Orçamentos → (orçamento) → Items → (item) → ValueSet**

- [ ] **Criar a partir do Orçamento** — com o item vazio e com o item já
      preenchido
- [ ] **Atualizar Custeio** — com linhas selecionadas **e sem seleção nenhuma**
      (deve propor o quadro todo); o aviso de diferenças aparece como sempre
- [ ] **Mostrar inativas** continua a mostrar e a esconder as desativadas

> Por dentro, o *Mostrar inativas* já não volta à base de dados: as linhas vêm
> todas de uma vez e o visto filtra em memória. Por fora deve ser igual.

---

# Sessão B — os ecrãs novos

## B1. Modelos ValueSet
**Configurações → Modelos ValueSet → ROUP_BRANCO** (109 linhas)

- [ ] Navegador à esquerda com Materiais, Ferragens, Sistemas de correr,
      Iluminação, Orlas, Acabamentos
- [ ] Clicar numa chave **filtra**; clicar outra vez mostra tudo (e o filtro do
      grupo sai junto — não fica meio filtro para trás)
- [ ] Chips de grupo, e **Todos** volta a mostrar tudo
- [ ] Clicar numa faixa fecha/abre o bloco
- [ ] Pesquisar `corred`: os chips e o navegador passam a contar só o que a
      pesquisa encontrou
- [ ] **Limpar filtros** repõe tudo
- [ ] **Ocultar navegador** dá a largura toda à tabela
- [ ] Desligar **Cabeçalhos de grupo na tabela**: volta ao aspeto corrido

### O "Agrupar por chave" mudou de ordem
- [ ] Repare que hoje o ROUP_BRANCO começa por **ACABAMENTOS** (era alfabético)
- [ ] Carregue em **Agrupar por chave** e confirme
- [ ] ⚠ *Escreve na coluna Ordem.* Agora deve começar por **MATERIAIS**, seguido
      de FERRAGENS, SISTEMAS DE CORRER, ILUMINAÇÃO, ORLAS, ACABAMENTOS — a mesma
      ordem do navegador. Dentro de cada chave, a prioridade 1 em primeiro.
- [ ] Cada chave passa a ter **uma só faixa**

## B2. ValueSet do Orçamento
**Orçamentos → 260888 → versão 01 → ValueSet** (100 linhas, 16 afinadas à mão)

- [ ] Estado diz: *"Linhas encontradas: 100. **16 afinada(s) à mão neste
      orçamento.**"*
- [ ] Chip **`✎ Editadas (16)`** — um clique mostra só essas, a ocre
- [ ] No navegador, o grupo **Materiais** mostra **`✎16`**
- [ ] 7 faixas de grupo (107 linhas no ecrã para 100 de dados)

> São faixas **só de grupo**. Com faixas de chave seriam ~176 linhas no ecrã,
> porque há 70 chaves para 100 linhas. Foi o que escolheu no mockup.

## B3. ValueSet do Item
**Orçamentos → 260911 → Items → ROUPEIRO 2+2 PORTAS ABRIR + NICHOS → ValueSet**

- [ ] Chip **`✎ Editadas (7)`** mostra as 7 que afinou só para este item —
      é a diferença face ao modelo que lhe deu origem, num clique
- [ ] Navegador, faixas, pesquisa e Limpar filtros como nos outros

---

# Sessão C — colunas arrastáveis

São 17 a 23 colunas e não cabem no ecrã. Agora põe-nas pela ordem que quiser.

- [ ] Arraste o cabeçalho de uma coluna (por exemplo **Preço líquido**) para
      logo a seguir à Opção. A coluna muda de sítio com os valores.
- [ ] Arrume as que lhe interessam à esquerda
- [ ] Saia da página e volte: a ordem mantém-se
- [ ] Feche o Martelo e volte a abrir: continua igual

> Guardado **por máquina e por utilizador** — a Andreia tem a ordem dela.

### A faixa acompanha
- [ ] Com as faixas ligadas, arraste a coluna **Chave** para o meio
- [ ] O texto da faixa (`▾ FERRAGENS — 50 linha(s)`) salta para a coluna que
      ficou mais à esquerda, e a faixa continua a atravessar a tabela toda
- [ ] Passe o rato por cima de uma faixa: o texto completo está no tooltip

### Nas três tabelas
- [ ] Modelos ValueSet
- [ ] ValueSet do Orçamento
- [ ] ValueSet do Item

Cada tabela guarda a **sua** ordem, independente das outras.

---

# Sessão D — as ferramentas das chaves

## D1. Auditoria
**Configurações → Auditoria ao catálogo → Atualizar**

- [ ] **43 ocorrências** (1 erro, 15 avisos, 27 informações), medidas hoje
- [ ] **Não** deve haver `VALUESET_MODELO_CHAVE_INEXISTENTE` — a base está limpa
- [ ] O aviso `VALUESET_MODELO_CHAVES_EM_FALTA` já não aparece, porque desativou
      o ROUPEIRO_INOV_POSITIVA

> Eram 48 antes de o desativar. Desativar esse modelo tirou o aviso das chaves
> em falta **e mais quatro** ocorrências que eram dele — a auditoria ignora
> modelos inativos.

### Provar que a rede apanha (⚠ altera dados — desfaz-se no fim)
- [ ] **Configurações → Chaves ValueSet**: anote o código de uma chave pouco
      usada (ex.: `FERRAGEM_PE_NIVELADOR`)
- [ ] Mude o código para `FERRAGEM_PE_NIVELADOR_X` e grave
      *(vai aparecer a janela de renomear — é o ponto D2; por agora confirme)*
- [ ] **Auditoria → Atualizar**: se tiver escolhido **não** propagar, aparecem
      erros vermelhos `VALUESET_MODELO_CHAVE_INEXISTENTE`, um por modelo, a
      dizer quantas linhas
- [ ] **Abrir configuração** leva ao modelo certo
- [ ] No modelo, a chave aparece no navegador dentro de **"Sem grupo"**, no fim
- [ ] ⚠ **Reponha o código** `FERRAGEM_PE_NIVELADOR`. Corra a auditoria: limpa.

> É esse o silêncio que isto veio resolver: uma chave órfã não dá erro nenhum —
> no custeio, a lista de materiais dessa chave vem simplesmente **vazia**.

## D2. Renomear uma chave
**Configurações → Chaves ValueSet → Editar Chave**

- [ ] Mudar **só o Código** abre a janela **"Renomear chave ValueSet"**
- [ ] A janela mostra, sítio a sítio, quem usa a chave: catálogos em cima,
      orçamentos em baixo
- [ ] A caixa *"Mudar também nos orçamentos já feitos"* vem **desligada**
- [ ] O aviso diz quantas linhas mudam e quantas ficam com o nome antigo
- [ ] ⚠ Renomeando **sem** ligar a caixa: os catálogos acompanham, e um
      orçamento antigo continua a mostrar o **código antigo** — é o registo do
      que foi vendido
- [ ] ⚠ **Reponha o nome.**

E o que a janela **não** deixa fazer:
- [ ] Dar a uma chave o código de outra que já existe (recusa, e não altera nada)
- [ ] Deixar o código vazio
- [ ] Mudar só espaços ou maiúsculas **não** é renomeação: a janela não aparece
- [ ] Alterar só o nome, grupo, ordem ou tipo também não abre janela nenhuma

## D3. Copiar chaves entre modelos
**Configurações → Modelos ValueSet → 1_ROUP_STD → Copiar Chaves…**

- [ ] A janela mostra as 70 chaves em cima e os modelos de destino em baixo
- [ ] Para cada modelo: **A criar**, **A atualizar**, **Já iguais**,
      **Só no destino**
- [ ] Os modelos do mesmo tipo aparecem primeiro; os que não têm nada a fazer
      não se marcam; modelos desativados não aparecem
- [ ] Trocar entre *"só acrescentar"* e *"acrescentar e atualizar"* refaz a conta
- [ ] **Enquanto a janela está aberta, nada é escrito**

### Ver a funcionar (⚠ cria um modelo de teste)
- [ ] **Novo Modelo** vazio, tipo ROUPEIRO, chamado `TESTE_COPIA`
- [ ] Do 1_ROUP_STD, copie 2 ou 3 chaves para ele
- [ ] As chaves lá estão, **com as operações** (última coluna)
- [ ] Correr outra vez: o destino fica **sem efeito** — não duplica
- [ ] Mude o preço de uma opção copiada e acrescente uma opção nova ao
      `TESTE_COPIA`. Copie outra vez em *"acrescentar e atualizar"*:
      - a que mudou volta ao preço da origem
      - **a que só existe no TESTE_COPIA fica intacta**
- [ ] **Nenhuma linha copiada fica com a marca ✎** — essa é só sua
- [ ] ⚠ Apague ou desative o `TESTE_COPIA` no fim

### Permissões
- [ ] Com uma conta **sem** a permissão de propagar (Ana, Bruno, Pedro…), os
      modelos de **outras pessoas** e os **globais** aparecem mas **não se
      marcam**, e o tooltip diz que permissão falta
- [ ] Os modelos próprios continuam a funcionar
- [ ] Com a permissão (admin, paulo, Andreia, Catia) já se marcam

---

# Sessão E — no dia-a-dia, ao fazer orçamentos novos

Esta é a que conta a sério, e faz-se com o trabalho normal. Ao longo dos
próximos orçamentos, repare nisto:

- [ ] O **`✎ Editadas`** mostra mesmo tudo o que afinou à mão? Bate certo com o
      que se lembra de ter mexido?
- [ ] A ordem das colunas que escolheu continua a servir depois de uns dias?
- [ ] As **faixas só de grupo** chegam, ou dá por si a querer também as de
      chave? (Dá para ligar — diga.)
- [ ] O navegador ajuda ou atrapalha em orçamentos pequenos, com poucas linhas?
- [ ] Alguma chave aparece em **"Sem grupo"** num orçamento novo? Se sim,
      diga-me qual — é uma chave partida.
- [ ] As páginas abrem mais depressa? (As operações passaram a ser lidas numa
      consulta só em vez de ~100.)

---

# O que não pode ter mudado em lado nenhum

- [ ] O custeio e os preços
- [ ] O separador **Custeio** e o **Atualizar Custos**
- [ ] Os relatórios e as exportações
- [ ] As páginas **Orçamentos → ValueSet** e **Item → ValueSet** dos orçamentos
      antigos abrem e mostram o que sempre mostraram

---

## Resumo do que ficou decidido pelo caminho

| Decisão | Porquê |
|---|---|
| As faixas **não reordenam** a tabela | Senão a seta ↑ mandava a linha para um sítio diferente do que se vê |
| Faixas **só de grupo** no orçamento e no item | 70 chaves para 100 linhas: com faixas de chave o ecrã quase duplicava |
| A marca ✎ é **só do utilizador** | Nenhuma operação automática a põe; o Ctrl+V à mão põe |
| Orçamentos **de fora** ao renomear, por omissão | São ~20× mais linhas que os catálogos, e são o registo do que foi vendido |
| Copiar chaves **nunca apaga** no destino | Uma opção que só exista lá pode ter sido posta de propósito |
| A faixa não usa `setSpan` | Com colunas arrastáveis, o span parte-se e a faixa deixa de atravessar a tabela |
