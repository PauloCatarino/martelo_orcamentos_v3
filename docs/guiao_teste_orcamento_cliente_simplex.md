# Guião de teste — Orçamentos: cliente com nome abreviado obrigatório

Pedido do Paulo (25-09-2026). Ao criar um orçamento novo, ou ao trocar o cliente
de um orçamento, o cliente tem de ter **nome abreviado (Simplex)**, com 19
caracteres no máximo. A regra vale tanto para clientes do PHC como para os
temporários.

É esse nome que dá o nome à pasta do orçamento no servidor (`NNNNNN_ABREVIADO`).
Até aqui, um cliente sem abreviado entrava na mesma, e a pasta ficava com o nome
completo do cliente (ex.: `A48_-_SISTEMAS_DE_SEGURANÇA_LDA`).

**Base real, 25-09:**
- 252 dos 534 clientes PHC não têm nome abreviado, e 4 passam dos 19 caracteres.
- Os 10 temporários têm todos abreviado.
- Nenhum orçamento usa ainda um cliente destes.

**Onde se corrige:**
- **Cliente do PHC:** preencher o nome abreviado (campo NOME2) na ficha do cliente
  no PHC. Depois, no Martelo: **Clientes › Clientes PHC › «Atualizar PHC»**.
- **Cliente temporário:** **Clientes › Clientes Temporários**, escolher o cliente,
  escrever o Simplex e carregar em **«Guardar»**.

---

## 1. A lista de clientes mostra quem está por corrigir

1. **Orçamentos › Novo Orçamento › «Escolher cliente…»**.
2. Por cima da tabela aparece a frase «O cliente tem de ter nome abreviado
   (Simplex)…».
3. Na coluna **Simplex**, com a lista toda (sem pesquisa):
   - cliente do PHC sem abreviado → **«(vazio no PHC)»** a ocre;
   - temporário sem abreviado → **«(vazio)»** a ocre;
   - abreviado com mais de 19 caracteres → o texto a **vermelho**.
4. Passe o rato por cima de uma célula ocre. A dica diz o que falta e **onde se
   corrige**: no PHC mais «Atualizar PHC», ou em Clientes Temporários.

## 2. Novo Orçamento — cliente sem abreviado é recusado

1. **Orçamentos › Novo Orçamento › «Escolher cliente…»**.
2. Faça duplo-clique num cliente com **«(vazio no PHC)»**.
3. **Esperado:**
   - aparece o aviso **«Cliente sem nome abreviado»**, com o nome do cliente e o
     «Como corrigir: No PHC, … NOME2 … Atualizar PHC»;
   - ao fechar o aviso, **continua na lista** e pode escolher outro cliente;
   - a linha de estado diz «… não tem nome abreviado válido — escolha outro ou
     corrija-o primeiro.»
4. Repita com um cliente a vermelho (mais de 19). O aviso diz «tem o nome
   abreviado com N caracteres (máximo 19)».
5. Escolha um cliente com abreviado (ex.: MÓVEIS J.F. VIVA). **Esperado:** a lista
   fecha, e no Novo Orçamento aparece
   **«MÓVEIS J.F. VIVA… (PHC) — abreviado: JF_VIVA»**.
6. Continue como sempre («1.º Criar proposta no PHC…» e depois «Guardar»). Quando
   perguntar pela pasta, a pasta criada é **`NNNNNN_JF_VIVA`**.

A regra vale também para o **«Orçamento antigo (registo manual)»**. Aí a pasta
é escolhida à mão, mas o abreviado volta a fazer falta mais à frente: na pasta
da obra, no plano CUT-RITE e na encomenda iMos.

## 3. Editar Orçamento › «Trocar cliente…»

1. Abra um orçamento existente (**Orçamentos › Editar**).
2. No quadro **Cliente**, a linha **Simplex** mostra o abreviado do cliente atual.
3. Carregue em **«Trocar cliente…»** e escolha um cliente com **«(vazio no PHC)»**.
   **Esperado:** o mesmo aviso do ponto 2, e o cliente do orçamento **não muda**.
4. Escolha um cliente com abreviado. **Esperado:**
   - o quadro Cliente passa a mostrar o novo cliente;
   - depois de **«Guardar»**, o Martelo pergunta se quer **renomear a pasta** para
     `NNNNNN_<novo abreviado>`.

## 4. Corrigir um cliente e voltar a tentar

1. **Cliente do PHC:**
   - no PHC, preencha o nome abreviado de um cliente que estava a ocre;
   - no Martelo: **Clientes › Clientes PHC › «Atualizar PHC»**;
   - volte ao **Novo Orçamento › «Escolher cliente…»**.
   **Esperado:** o cliente já mostra o abreviado e já se pode escolher.
2. **Cliente temporário:**
   - em **Clientes › Clientes Temporários**, escolha o cliente e escreva o
     Simplex (máx. 19);
   - carregue em **«Guardar»**.
   **Esperado:** o cliente passa a poder ser escolhido.

## 5. O que NÃO muda

- **Orçamentos antigos** que já tinham um cliente sem abreviado continuam a
  abrir e a gravar normalmente, desde que o cliente não seja trocado. Não há
  nenhum na base real, mas a regra deixa-os passar.
- **Outras listas de clientes** (as que não servem para escolher o cliente de um
  orçamento) continuam a deixar escolher qualquer cliente.
- **Clientes temporários:** o Simplex continua a ser **sugerido a partir do nome**
  quando fica em branco e o nome tem até 19 caracteres. Com um nome maior, o
  «Guardar» pede para escrever o Simplex à mão.
