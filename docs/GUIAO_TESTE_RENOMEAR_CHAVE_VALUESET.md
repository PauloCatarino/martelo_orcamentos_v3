# Guião de teste — Peça 3: renomear uma chave ValueSet leva atrás quem a usa

> **Para testar, use antes o [guião completo](GUIAO_TESTE_VALUESET_COMPLETO.md)**,
> que junta os seis guiões pela ordem por que convém percorrê-los.
> Corresponde a: Sessão D2.
> Este ficheiro fica como o detalhe da ronda em que foi escrito.

Versão de 12-set-2026.

---

## Porque é que isto existe

O código de uma chave está guardado **como texto em sete tabelas, sem ligação
entre elas**. Até aqui, mudar o código em *Configurações → Chaves ValueSet*
mudava só ali. Quem ficasse com o nome antigo **não dava erro nenhum**: no
custeio, a lista de materiais dessa chave vinha vazia, o dropdown "Mat. default"
ficava em branco, e não aparecia mensagem nem ficava registo.

Foi assim que o `FERRAGEM_SUPORTE_VARAO` sobreviveu. Isto é o que faz com que
não volte a acontecer.

---

## 1. Renomear uma chave usada

1. **Configurações → Chaves ValueSet**.
2. Escolha uma chave com algum uso — por exemplo **`FERRAGEM_VARAO`** — e
   **Editar Chave**.
3. Mude só o **Código** para `FERRAGEM_VARAO_TESTE`. Grave.

**Esperado:** antes de gravar abre uma janela **"Renomear chave ValueSet"** que
mostra, sítio a sítio, quem usa a chave:

```
Catálogos — muda sempre (N)
    Linhas de modelos ValueSet            …
    Peças — material                      …
    Peças — acabamento superior           …
    Peças — acabamento inferior           …
    Linhas de módulos guardados           …
Orçamentos já feitos — só se pedir (M)
    Orçamentos — ValueSet do orçamento    …
    Orçamentos — ValueSet do item         …
    Orçamentos — linhas de custeio        …
```

Por baixo, uma caixa **desligada**: *"Mudar também nos orçamentos já feitos"*,
e um aviso a dizer quantas linhas vão mudar e quantas ficam como estão.

4. **Sem ligar a caixa**, carregue em **Renomear**.

**Esperado:** a linha de estado da página diz algo como
*"Chave FERRAGEM_VARAO renomeada para FERRAGEM_VARAO_TESTE: N linha(s) de
catálogo atualizadas. Os orçamentos já feitos ficaram como estavam."*

---

## 2. Confirmar que os catálogos acompanharam

1. **Configurações → Modelos ValueSet → 1_ROUP_STD**.

**Esperado:** no navegador de chaves, a chave aparece com o **nome novo**, no
grupo certo (Ferragens) — e **não** em "Sem grupo". Foi exatamente isto que
falhou da última vez.

2. **Configurações → Auditoria ao catálogo → Atualizar**.

**Esperado:** **nenhum** `VALUESET_MODELO_CHAVE_INEXISTENTE`. A renomeação foi
completa.

3. Abra um orçamento antigo que usasse essa chave.

**Esperado:** continua a mostrar o **código antigo** — é o registo do que foi
vendido, e ficou intacto de propósito.

---

## 3. Desfazer

1. Volte às **Chaves ValueSet**, edite a chave e reponha o código
   `FERRAGEM_VARAO`. Grave e confirme na janela.

**Esperado:** volta tudo ao que era. Confirme na auditoria que continua limpa.

---

## 4. Incluir também os orçamentos

Só faça isto se quiser mesmo ver o efeito — **altera orçamentos já entregues**.

1. Renomeie outra vez, mas desta vez **ligue** a caixa dos orçamentos.

**Esperado:** o aviso muda para *"Vão mudar X linha(s), incluindo M de
orçamentos já feitos. Isso altera o registo do que foi vendido."*
No fim, a linha de estado conta as duas coisas em separado.

2. Reponha o nome, outra vez com a caixa ligada, para deixar tudo como estava.

---

## 5. O que a janela não deixa fazer

- **Dar a uma chave o código de outra que já existe** — recusa com
  *"Já existe uma chave com esse código."*, e **não altera nada pelo caminho**.
- **Deixar o código vazio.**
- **Gravar sem passar pela janela**, quando o código mudou.
- Mudar só espaços ou maiúsculas (`ferragem varao` → `FERRAGEM_VARAO`) **não** é
  uma renomeação: a janela não aparece, porque na prática o código é o mesmo.
- Alterar só o **nome**, o **grupo**, a **ordem** ou o **tipo** também não abre
  janela nenhuma — isso continua a ser uma edição normal.
- Uma chave parecida (`FERRAGEM_VARAO_2`) **não** é apanhada pela renomeação de
  `FERRAGEM_VARAO`. A comparação é exata.

---

## 6. Chave sem uso nenhum

1. Crie uma chave nova (**Nova Chave**), grave, e a seguir edite-lhe o código.

**Esperado:** a janela aparece na mesma, com tudo a zeros, e a caixa dos
orçamentos **desligada e cinzenta** — não há orçamentos para incluir.

---

## 7. Se alguma coisa correr mal a meio

A renomeação é **tudo ou nada**: ou muda o vocabulário e todos os sítios
escolhidos, ou não muda nada. Ficar a meio seria pior do que não ter começado —
era exatamente a situação que isto veio resolver.
