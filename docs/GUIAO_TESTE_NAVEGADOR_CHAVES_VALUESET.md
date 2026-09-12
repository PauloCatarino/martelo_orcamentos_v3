# Guião de teste — Navegador de chaves nos Modelos ValueSet (Peça 1)

Versão: branch `claude/valueset-modelo-page-redesign-7c7291`, 12-set-2026.
Nada nesta peça altera dados de orçamentos. As únicas escritas na base são as
que já existiam: o botão "Agrupar por chave" (que reescreve a coluna `Ordem`) e
as setas ↑↓.

---

## 1. A página abre com o navegador à esquerda

1. **Configurações → Modelos ValueSet**
2. Duplo clique no modelo **ROUP_BRANCO** (109 linhas).

**Esperado:**
- À esquerda, um painel **"Navegador de chaves"** com os grupos:
  Materiais (38), Ferragens (49), Sistemas de correr (9), Iluminação (7),
  Orlas (2), Acabamentos (2).
- Por cima da tabela, uma fila de botões (chips): `Todos (107)`, `Materiais (38)`,
  `Ferragens (49)`, … — 107 e não 109 porque há 2 linhas inativas escondidas.
- Na tabela, faixas escuras a separar cada grupo e cada chave, por exemplo:
  `▾ ACABAMENTOS — 2 linha(s)` e, por baixo,
  `▾ Acabamento face inferior · ACABAMENTO_FACE_INF · 1 opção(ões)`.
- A barra entre a pesquisa e a tabela tem **"Cabeçalhos de grupo na tabela"**
  (ligado) e **"Limpar filtros"**.
- Na barra dos botões, ao pé de "Verificar preços…", há **"Ocultar navegador"**.

---

## 2. Clicar numa chave filtra a tabela

1. No navegador, abra **Ferragens** e clique em **Corrediça**.

**Esperado:** a tabela passa a mostrar só as 6 corrediças. A linha de estado
diz `Linhas encontradas: 6.  ·  grupo: Ferragens  ·  chave: FERRAGEM_CORREDICA`.

2. Clique **outra vez** em Corrediça.

**Esperado:** volta a aparecer tudo (107 linhas). O filtro do grupo sai junto
com o da chave — não fica meio filtro para trás.

---

## 3. Chips de grupo

1. Clique no chip **Ferragens**.

**Esperado:** só as 49 ferragens; o chip fica marcado; o navegador passa a
mostrar só o grupo Ferragens.

2. Clique no chip **Todos**.

**Esperado:** volta tudo.

---

## 4. Fechar e abrir blocos na tabela

1. Sem filtros, clique na faixa **`▾ Corrediça · FERRAGEM_CORREDICA · 6 opção(ões)`**.

**Esperado:** a seta passa a `▸` e as 6 linhas desaparecem; as outras chaves
ficam. Clicar outra vez volta a abrir.

2. Clique na faixa **`▾ FERRAGENS — 48 linha(s)`**.

**Esperado:** fecha o grupo inteiro.

3. Clique em **"Limpar filtros"**.

**Esperado:** tudo aberto outra vez, pesquisa vazia, sem grupo nem chave.

---

## 5. A pesquisa e o navegador trabalham juntos

1. Escreva **`corred`** na pesquisa.

**Esperado:** a tabela mostra só as corrediças; o navegador e os chips passam a
contar só o que a pesquisa encontrou (o chip Todos deixa de dizer 107).

2. Apague a pesquisa.

**Esperado:** volta tudo.

---

## 6. As setas continuam a bater certo (o mais importante)

As faixas **não reordenam nada** — seguem a coluna `Ordem`. Confirme:

1. Sem filtros, escolha uma linha do meio de um bloco (por exemplo a 3.ª
   corrediça) e repare no número da coluna **Ordem**.
2. Carregue em **↑**.

**Esperado:** a linha sobe uma posição *dentro da tabela como a está a ver*, e a
coluna Ordem acompanha. A linha não salta para outro sítio.

3. Selecione duas linhas seguidas (Ctrl ou Shift) e carregue em **↓**.

**Esperado:** as duas descem juntas, mantendo a ordem entre si.

4. Feche o bloco de uma chave, e mova uma linha de outra chave.

**Esperado:** a linha não troca com nenhuma das que estão escondidas.

---

## 7. "Agrupar por chave" passou a seguir o navegador

1. Repare que, hoje, o modelo ROUP_BRANCO começa por **ACABAMENTOS** — porque a
   ordenação antiga era alfabética pelo código da chave.
2. Carregue em **"Agrupar por chave"** e confirme.

**Esperado:**
- A pergunta diz: *"Voltar a arrumar todas as linhas pela ordem do navegador
  (grupo, chave, prioridade)?"*
- Depois de confirmar, a tabela passa a começar por **MATERIAIS**, seguido de
  FERRAGENS, SISTEMAS DE CORRER, ILUMINAÇÃO, ORLAS e ACABAMENTOS — a mesma
  ordem que se lê no navegador à esquerda.
- Dentro de cada chave, a prioridade 1 fica em primeiro.
- A linha de estado diz `109 linhas arrumadas por grupo e por chave.`
- Cada chave passa a ter **uma só faixa** (antes podia ter mais do que uma, se
  as linhas estivessem espalhadas).

---

## 8. Desligar as faixas

1. Desligue **"Cabeçalhos de grupo na tabela"**.

**Esperado:** a tabela volta ao aspeto antigo, corrida, sem faixas. O navegador
e os chips continuam a funcionar e a filtrar.

---

## 9. Ocultar o navegador

1. Carregue em **"Ocultar navegador"**.

**Esperado:** o painel esquerdo desaparece e a tabela ocupa a largura toda; o
botão passa a dizer "Mostrar navegador". O filtro que estivesse escolhido
mantém-se (a linha de estado continua a dizê-lo).
2. Arraste a barra entre o navegador e a tabela para mudar a largura, saia da
   página e volte a entrar.

**Esperado:** a largura que escolheu é a que lá está.

---

## 10. O que não pode ter mudado

- **Editar Linha**, **Copiar/Colar Dados** (Ctrl+C / Ctrl+V), **Propagar
  Operações…**, **Ativar/Desativar**, **Verificar preços…** e **Gravar como…**
  fazem exatamente o mesmo que faziam.
- Duplo clique numa linha abre a edição. Duplo clique numa **faixa** não abre
  nada.
- O botão direito sobre uma **faixa** não abre menu nenhum; sobre uma linha
  abre o menu de sempre.
- As páginas **Orçamentos → ValueSet** e **Item → ValueSet** ficam na mesma —
  o ficheiro de estilo é partilhado e só levou acrescentos.

---

## 11. Uma nota que vai aparecer

Se algum modelo tiver uma chave que já não existe no vocabulário
(`Configurações → Chaves ValueSet`), ela aparece no navegador dentro de um grupo
chamado **"Sem grupo"**, no fim. Não é um erro do ecrã: é uma chave partida, e é
exatamente essa que deixa o dropdown "Mat. default" vazio no custeio. A Peça 2
(auditoria) passa a apanhá-las sozinha.

Hoje, na base real, há **uma**: `FERRAGEM_SUPORTE_VARAO`, no modelo
**Roupeiro standard** (linha 48, "Suporte varão standard", FER0089).
