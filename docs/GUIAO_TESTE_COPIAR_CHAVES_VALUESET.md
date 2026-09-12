# Guião de teste — Peça 4: copiar chaves entre modelos ValueSet

Versão de 12-set-2026.

---

## O que isto resolve

Quando nasce uma chave nova, ou quando um modelo ficou para trás, pô-la nos
outros modelos era opção a opção, à mão. Num modelo de 100 linhas isso é meio
dia de trabalho — e basta esquecer um modelo para o custeio desse modelo ficar
sem material nessa chave, **em silêncio**.

**Duas regras que o botão respeita sempre:**

1. **Nunca apaga nada no destino.** Uma opção que só exista lá fica onde está —
   pode ter sido posta de propósito por quem é dono do modelo.
2. **Respeita o dono.** Um modelo de outra pessoa, ou global, só se toca com a
   permissão *"Propagar operações ValueSet para modelos globais ou de outros
   utilizadores"* — a mesma que já governa a propagação de operações.

---

## 1. Abrir

1. **Configurações → Modelos ValueSet → 1_ROUP_STD**.
2. Na barra de cima, no grupo de copiar, carregue em **"Copiar Chaves…"**.

**Esperado:** abre a janela **"Copiar chaves para outros modelos"**, com:
- em cima, a lista das **70 chaves** do modelo, com grupo, nome, código e
  quantas opções cada uma tem;
- ao meio, a escolha *"Se o destino já tiver a opção:"* com
  **"Só acrescentar o que falta"** já marcado;
- em baixo, os **modelos de destino** com a conta de cada um.

> **Atalho:** se antes de abrir tiver uma chave a filtrar a tabela (clicada no
> navegador da esquerda), ela já vem marcada na janela.

---

## 2. A conta antes de escrever

1. Marque a chave **Corrediça** (`FERRAGEM_CORREDICA`).

**Esperado:** a lista de baixo enche-se. Para cada modelo vê **A criar**,
**A atualizar**, **Já iguais** e **Só no destino**. Como os seus modelos já
estão sincronizados, é natural que dê tudo a zeros e diga *"sem efeito"*.

2. Repare que:
   - os modelos do **mesmo tipo** da origem (ROUPEIRO) aparecem primeiro;
   - os que **não têm nada a fazer** não se conseguem marcar;
   - o **ROUP_BRANCO** (da Andreia) e o **ROUPEIRO_STANDARD** (global) aparecem
     como *Outro utilizador* e *Global*;
   - modelos **desativados** não aparecem de todo.

3. Troque para **"Acrescentar e atualizar as que já existem"**.

**Esperado:** a conta refaz-se sozinha. As opções que existam nos dois lados mas
com preço, prioridade ou material diferentes passam a contar em **A atualizar**.

> Enquanto esta janela estiver aberta **nada é escrito**. A conta é refeita a
> cada mudança.

---

## 3. Copiar mesmo (com um destino de propósito)

Para ver a coisa a funcionar precisa de um destino a quem falte alguma chave.

1. **Novo Modelo** — crie um modelo vazio, tipo **ROUPEIRO**, por exemplo
   `TESTE_COPIA`.
2. Volte ao **1_ROUP_STD → Copiar Chaves…**.
3. Marque **duas ou três chaves** (por exemplo Corrediça, Dobradiça e Varão).

**Esperado:** o `TESTE_COPIA` aparece com **A criar** igual à soma das opções
dessas chaves, e o resumo em baixo diz, a verde, quantas linhas vão ser criadas
e que **nada é apagado**.

4. Marque o `TESTE_COPIA` e carregue em **Copiar**.

**Esperado:** a linha de estado do modelo diz
*"N linha(s) criadas e 0 atualizadas em 1 modelo(s), com M operação(ões)."*

5. Abra o `TESTE_COPIA`.

**Esperado:** as chaves lá estão, com todas as opções, **e com as operações** —
confirme na última coluna (Operações). Sem elas a opção copiada custeava
diferente da original sem ninguém dar por isso.

6. Carregue em **"Agrupar por chave"** no modelo novo: as linhas arrumam-se pela
   ordem do navegador.

---

## 4. Correr outra vez não duplica

1. Repita o **Copiar Chaves…** com as mesmas chaves para o `TESTE_COPIA`.

**Esperado:** o destino aparece como **sem efeito** e não se consegue marcar.
Não há linhas duplicadas.

---

## 5. Não apagar é mesmo não apagar

1. No `TESTE_COPIA`, edite uma das opções copiadas: mude-lhe o preço.
2. Acrescente ao `TESTE_COPIA` uma **opção nova** numa dessas chaves, que a
   origem não tenha.
3. Corra o **Copiar Chaves…** outra vez, agora em
   **"Acrescentar e atualizar as que já existem"**.

**Esperado:**
- a opção a que mudou o preço volta ao preço da origem (conta em *A atualizar*);
- a opção que **só** existe no `TESTE_COPIA` **continua lá, intacta** — aparece
  na coluna *Só no destino* e não é tocada.

---

## 6. Permissões

Se entrar com uma conta **sem** a permissão de propagar para outros (por
exemplo a Ana, o Bruno ou o Pedro):

**Esperado:** os modelos de **outras pessoas** e os **globais** aparecem na
lista mas **não se conseguem marcar**, e ao passar o rato por cima a explicação
diz que permissão falta. Os modelos **próprios** continuam a funcionar.

Com a permissão (hoje: admin, paulo, Andreia, Catia) é possível marcá-los.

---

## 7. Limpar o teste

Apague ou desative o `TESTE_COPIA` quando acabar.

---

## 8. O que não pode ter mudado

- Todos os outros botões da página do modelo fazem o mesmo de sempre.
- O botão **"Propagar Operações…"**, que é parecido mas faz outra coisa
  (leva as operações de **uma linha** para linhas com a mesma chave e a mesma
  Ref LE), não foi tocado.
- Cancelar a janela não escreve nada.

---

## 9. A marca ✎ continua a ser só sua

A marca de *"editado localmente"* (✎) serve para assinalar o que **você** mexeu
à mão numa linha. Uma linha que veio inteira de outro modelo não foi mexida à
mão por ninguém.

**Confirme:** depois de copiar (em qualquer dos dois modos), nenhuma linha do
destino fica com ✎ — nem as criadas nem as atualizadas. E se uma linha do
destino **já tinha** a marca e foi reposta pela cópia, a marca **sai**: ela
deixou de ter edição local nenhuma.

O que **não** pode ter mudado: **Colar Dados** (Ctrl+V) numa linha, à mão,
continua a pôr a marca. É esse o seu propósito.
