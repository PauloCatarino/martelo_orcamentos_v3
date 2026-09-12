# Guião de teste — ValueSet do Item + colunas arrastáveis

> **Para testar, use antes o [guião completo](GUIAO_TESTE_VALUESET_COMPLETO.md)**,
> que junta os seis guiões pela ordem por que convém percorrê-los.
> Corresponde a: Sessões A3, B3 e C.
> Este ficheiro fica como o detalhe da ronda em que foi escrito.

Versão de 12-set-2026. **Nada aqui muda dados nem custeio** — é apresentação,
filtros e a ordem das colunas.

---

## Parte A — colunas arrastáveis (as três tabelas de ValueSet)

São 17 a 23 colunas e não cabem no ecrã. Agora pode pô-las pela ordem que
quiser: as importantes à esquerda, as outras no fim.

### A1. Arrastar

1. Abra **Orçamentos → (um orçamento) → ValueSet**.
2. **Arraste o cabeçalho de uma coluna** — por exemplo o **Preço líquido** —
   para logo a seguir à Opção.

**Esperado:** a coluna muda de sítio e leva os valores consigo.

3. Arraste mais duas ou três, até ter à esquerda o que lhe interessa
   (por exemplo: Chave, Opção, Ref LE, Preço líquido, Prioridade).

### A2. Fica guardado

1. Saia da página e volte a entrar.

**Esperado:** a ordem que escolheu é a que lá está.

2. Feche o Martelo e volte a abrir.

**Esperado:** continua igual. (É guardado **por máquina e por utilizador** —
se a Andreia entrar no PC dela, tem a ordem dela.)

### A3. A faixa acompanha

> Isto foi o que me obrigou a mudar a forma como a faixa é desenhada: com o
> método antigo, mover a primeira coluna fazia a faixa deixar de atravessar a
> tabela e começar a meio.

1. Com as **faixas de grupo ligadas**, arraste a coluna **Chave** para o meio.

**Esperado:** o texto da faixa (`▾ FERRAGENS — 50 linha(s)`) salta para a
coluna que ficou mais à esquerda, e a faixa continua a atravessar a tabela toda.

2. Passe o rato por cima de uma faixa: o texto completo aparece no tooltip,
   mesmo que a coluna da esquerda seja estreita e o corte.

### A4. As três tabelas

Repita o arrastar em:
- **Configurações → Modelos ValueSet → (modelo)**
- **Orçamentos → (orçamento) → Items → (item) → ValueSet**

Cada tabela guarda a **sua** ordem, independente das outras.

---

## Parte B — ValueSet do Item

Ficou igual ao do orçamento. Use o item **ROUPEIRO 2+2 PORTAS ABRIR + NICHOS**
do **260911**, que tem 100 linhas e 7 afinadas à mão.

### B1. Abrir

**Esperado:**
- navegador à esquerda com Materiais (27), Ferragens (51), Sistemas de correr
  (9), Iluminação (9), Orlas (2), Acabamentos (2);
- chips com esses números **mais** `✎ Editadas (7)`;
- estado: *"Linhas encontradas: 100. **7 afinada(s) à mão neste item.**"*
- 7 faixas de grupo na tabela (107 linhas no ecrã para 100 de dados).

### B2. O filtro das editadas

1. Carregue no chip **`✎ Editadas (7)`**.

**Esperado:** ficam as 7 que você afinou só para este item, com o ✎ a ocre.
O navegador mostra `✎N` nos grupos e chaves que as contêm.

> É a diferença entre este item e o modelo que lhe deu origem — num clique.

### B3. Navegador, faixas e pesquisa

Igual ao do orçamento: clicar numa chave filtra, clicar outra vez mostra tudo;
clicar numa faixa fecha o grupo; **Limpar filtros** repõe tudo; a pesquisa
reduz os chips e o navegador.

### B4. Os botões próprios do item — o que mais importa confirmar

Estes são só deste ecrã e **não podem ter mudado**:

- **Criar a partir do Orçamento** — com o item vazio e com o item já
  preenchido (acrescentar e substituir).
- **Atualizar Custeio** — com linhas selecionadas e **sem seleção nenhuma**
  (deve propor o quadro todo). Confirme que o aviso de diferenças aparece como
  sempre.
- **Importar Modelo**, **Nova/Editar Linha**, **Copiar/Colar Dados**
  (Ctrl+C / Ctrl+V), **Limpar Dados**, **Ativar/Desativar**.
- **Colar Dados** continua a pôr a marca ✎ — é você que mexe.

### B5. Uma mudança por dentro

O **Mostrar inativas** já não volta à base de dados: as linhas vêm todas de uma
vez e o visto filtra em memória, como nas outras páginas. Confirme que continua
a mostrar e a esconder as desativadas, e que o **Ativar/Desativar** continua a
funcionar.

### B6. Velocidade

Também aqui as operações passaram a ser lidas **numa consulta só** em vez de uma
por linha (eram ~100). Deve abrir mais depressa.

---

## O que não pode ter mudado em lado nenhum

- O custeio e os preços.
- O separador **Custeio** e o botão **Atualizar Custos**.
- Os relatórios e as exportações.
