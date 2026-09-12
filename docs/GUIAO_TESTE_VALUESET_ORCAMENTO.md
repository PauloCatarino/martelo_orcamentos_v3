# Guião de teste — ValueSet do Orçamento com navegador de chaves

> **Para testar, use antes o [guião completo](GUIAO_TESTE_VALUESET_COMPLETO.md)**,
> que junta os seis guiões pela ordem por que convém percorrê-los.
> Corresponde a: Sessões A2 e B2.
> Este ficheiro fica como o detalhe da ronda em que foi escrito.

Versão de 12-set-2026. **Nada aqui muda dados nem custeio** — é apresentação e
filtros. As escritas continuam a ser as de sempre (Importar, Nova, Editar,
Colar, Limpar, Ativar/Desativar).

---

## O que mudou, e porquê

Esta tabela tem **~100 linhas em ~70 chaves e 23 colunas**. Era o mesmo problema
da página do modelo, com mais seis colunas. Ficou com o mesmo navegador.

E ganhou uma coisa que a do modelo não tem: como aqui o normal é **importar um
modelo e depois afinar linhas à mão**, essas linhas afinadas são as mais
importantes de encontrar — e estavam escondidas numa coluna ao fundo de 23.

---

## 1. Abrir

1. **Orçamentos → 260888 → versão 01 → separador ValueSet**.

**Esperado:**
- painel **"Navegador de chaves"** à esquerda, com os grupos:
  Materiais (27), Ferragens (51), Sistemas de correr (9), Iluminação (9),
  Orlas (2), Acabamentos (2);
- por cima da tabela, chips com esses mesmos números **mais um**:
  **`✎ Editadas (16)`**;
- a linha de estado diz: *"Linhas encontradas: 100. **16 afinada(s) à mão neste
  orçamento.**"*
- na tabela, faixas escuras a separar cada grupo:
  `▾ ACABAMENTOS — 2 linha(s)`, `▾ FERRAGENS — 50 linha(s)`, e a de
  `▾ MATERIAIS — … · ✎ 16 afinada(s) à mão`.

> **São faixas só de grupo**, não de chave. Aqui há 70 chaves para 100 linhas:
> com faixas de chave o ecrã passava de 107 para ~176 linhas. Assim são 7 faixas.

---

## 2. O filtro que interessa: o que você mexeu

1. Carregue no chip **`✎ Editadas (16)`**.

**Esperado:** ficam **16 linhas**, todas com o ✎ e a opção a ocre. A linha de
estado acrescenta *"· só as editadas localmente"*.

2. Repare no navegador: o grupo **Materiais** mostra **`✎16`** na coluna do meio,
   e as chaves que as contêm mostram o seu próprio número.

> Neste orçamento as 16 estão todas em Materiais — é o que muda de obra para
> obra. Confirme se bate certo com o que se lembra de ter afinado.

3. Carregue outra vez no chip para voltar a ver tudo.

---

## 3. Navegar por chave

1. Abra **Ferragens** no navegador e clique em **Corrediça**.

**Esperado:** só as corrediças; o estado diz o grupo e a chave.

2. Clique outra vez na mesma chave.

**Esperado:** volta tudo — o filtro do grupo sai junto com o da chave.

3. Clique no chip **Materiais**.

**Esperado:** só os 27 materiais, e o navegador passa a mostrar só esse grupo.

---

## 4. Fechar grupos

1. Clique na faixa **`▾ FERRAGENS — 50 linha(s)`**.

**Esperado:** fecha e as 50 linhas desaparecem; a seta passa a `▸`. Clicar outra
vez abre.

2. **Limpar filtros** repõe tudo: pesquisa, grupo, chave, chip das editadas e
   grupos fechados.

---

## 5. Pesquisa

1. Escreva **`blum`** na pesquisa.

**Esperado:** só as linhas da Blum; os chips e o navegador passam a contar só o
que a pesquisa encontrou.

2. Apague. Volta tudo.

---

## 6. O que **não** pode ter mudado (o mais importante)

Faça cada um destes e confirme que se comporta como sempre:

- **Importar Modelo** — importa e a tabela recarrega (experimente em modo
  acrescentar e em modo substituir).
- **Nova Linha**, **Editar Linha** — o diálogo é o mesmo.
- **Copiar / Colar Dados** (Ctrl+C / Ctrl+V) numa linha — e a linha colada
  **fica com a marca ✎**, como sempre ficou: foi você que a mexeu.
- **Limpar Dados** numa ou em várias linhas selecionadas.
- **Ativar/Desativar**, e o **Mostrar inativas**.
- Duplo clique numa linha abre a edição. Duplo clique numa **faixa** não abre
  nada; botão direito sobre uma faixa não abre menu.
- Seleção de **várias linhas** (Ctrl/Shift) continua a funcionar para o
  **Limpar Dados**.
- O aviso de **prioridade repetida** continua a aparecer.

---

## 7. Desligar o que não quiser

- **"Faixas de grupo na tabela"** desligado → tabela corrida, como antes.
- **"Ocultar navegador"** → a tabela ocupa a largura toda; a largura do painel
  que escolher (arrastando a barra) fica guardada.

---

## 8. Velocidade

A página passou a ler as operações de todas as linhas **numa consulta só** em
vez de uma por linha (eram ~100). Deve abrir visivelmente mais depressa,
sobretudo com a base no outro computador.

---

## A seguir

Se isto estiver bom, faço o mesmo no **ValueSet do Item** — é o mesmo widget, e
lá o botão **"Atualizar Custeio"** e o **"Criar a partir do Orçamento"**
mantêm-se onde estão.
