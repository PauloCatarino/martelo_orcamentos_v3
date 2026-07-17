# Custeio mais legível — peças compostas colapsáveis (mockup)

> Documento **só de proposta visual**. Não altera código. Serve para o Paulo ver
> o resultado possível e escolher a variante antes de implementarmos.
>
> **✅ Decidido (2026-07-17):** **Variante A** (peça composta colapsa peças +
> ferragens), **sempre colapsada por defeito** — o utilizador expande quando
> precisa. Manter: setas `▶/▼`, resumo rico (`2 peças · 7 ferragens · 45,20 €`),
> chip `auto` nas ferragens de regra, e o `✕` para eliminar ferragens. Mockup
> interativo em [`mockups/custeio_pecas_compostas_colapsaveis.html`](mockups/custeio_pecas_compostas_colapsaveis.html).

## 1. O problema

A tabela "Linhas de custeio do item" mistura, em linhas todas com o mesmo peso
visual:

- **Divisões independentes** (cabeçalho de bloco);
- **Peças** simples;
- **Peças compostas** (ex.: `PORTA_DUPLA+DOBRADICA+PUXADOR`, `FUNDO+PES`), que
  se expandem em **muitas** linhas filhas — peças + ferragens;
- **Ferragens** dos componentes compostos, que já vêm **preenchidas por regras
  por defeito** e que o utilizador quase nunca precisa de tocar.

Resultado: um `FUNDO+PES` traz `FUNDO_2000 + SISTEMAS_UNIAO + SISTEMAS_UNIAO +
PES + SISTEMAS_UNIAO + SISTEMAS_UNIAO + FUNDO_0000 + …`. Tudo importante para o
cálculo, mas visualmente vira uma parede de linhas quase iguais onde é difícil
ver o que interessa.

**Todas as linhas continuam a existir e a ser calculadas.** A proposta é apenas
**mostrar menos por defeito**, mantendo tudo acessível a um clique.

## 2. A ideia central: a peça composta é uma linha "dobrável"

A linha **Peça composta** passa a comportar-se como um cabeçalho que se
**expande/colapsa**, com um triângulo `▶ / ▼` e um **resumo** do que está lá
dentro. Por defeito nasce **colapsada**.

Isto encaixa no que já existe: cada linha filha já sabe quem é o seu pai
(`linha_pai_id`) e o seu `nível`, por isso agrupar e esconder é directo — é só
visual (esconder/mostrar linhas), sem mexer em cálculos, quantidades ou preços.

### Antes (tudo aberto, como hoje)

```
Tipo linha       Def. Peça                         QT   Mat. default / Descrição
───────────────────────────────────────────────────────────────────────────────
Peça composta    FUNDO+PES                          1
  Peça           FUNDO_2000                         1   AGL MLM LINHO CANCUN 12G…
  Ferragem       SISTEMAS_UNIAO                     10  CAVILHA MADEIRA 8 X 35
  Ferragem       SISTEMAS_UNIAO                     10  PARAFUSO POZIDRIVE 3.5 X 50
  Ferragem       PES                                6   PE NIVELADOR AXILO H55-75
  Ferragem       SISTEMAS_UNIAO                     10  CAVILHA MADEIRA 8 X 35
  Ferragem       SISTEMAS_UNIAO                     10  PARAFUSO POZIDRIVE 3.5 X 50
  Peça           FUNDO_0000                         1   AGL MLM LINHO CANCUN 12G…
  Ferragem       SISTEMAS_UNIAO                     2   CAVILHA MADEIRA 8 X 35
  Ferragem       SISTEMAS_UNIAO                     2   PARAFUSO POZIDRIVE 3.5 X 50
```

### Depois (colapsada por defeito)

```
Tipo linha       Def. Peça                                    QT   Resumo
───────────────────────────────────────────────────────────────────────────────
▶ Peça composta  FUNDO+PES              · 2 peças · 6 ferragens · 45,20 €
```

Um clique no `▶` (ou duplo-clique na linha) abre:

### Depois (expandida por escolha do utilizador)

```
Tipo linha       Def. Peça                                    QT   Resumo
───────────────────────────────────────────────────────────────────────────────
▼ Peça composta  FUNDO+PES              · 2 peças · 6 ferragens · 45,20 €
    Peça         FUNDO_2000                                   1    AGL MLM LINHO…
    Ferragem     SISTEMAS_UNIAO                               10   CAVILHA MADEIRA…
    Ferragem     SISTEMAS_UNIAO                               10   PARAFUSO POZIDRIVE…
    Peça         FUNDO_0000                                   1    AGL MLM LINHO…
    …
```

O resumo na linha da peça composta (`2 peças · 6 ferragens · 45,20 €`) dá ao
utilizador o essencial **sem** abrir: o que é, quantos componentes tem e quanto
custa.

## 3. Variantes possíveis (escolher uma)

Do mais discreto ao mais agressivo. Podem também combinar-se.

| Variante | O que colapsa por defeito | Vantagem | A pensar |
|---|---|---|---|
| **A — Colapsar tudo** | Toda a peça composta (peças + ferragens filhas) | Máxima limpeza; a lista fica curtíssima | Esconde também as peças filhas (que às vezes interessam) |
| **B — Só ferragens** | Só as **ferragens** filhas auto-preenchidas; as **peças** filhas ficam visíveis | Mantém à vista o que é "material/peça", esconde o "parafuso/cavilha" | Colapso parcial é menos óbvio de perceber |
| **C — Modo simplificado (global)** | Um botão liga/desliga "esconder ferragens automáticas" para a tabela inteira | Um só interruptor controla tudo | Menos granular por peça |

**Recomendação:** começar pela **Variante A** (peça composta colapsada por
defeito, com resumo rico), porque é a que resolve melhor a "parede de linhas" e
é a mais simples de perceber — o triângulo `▶/▼` é uma convenção universal. As
peças filhas continuam a um clique.

## 4. Como fica a interação

- **Expandir/colapsar uma peça composta:** clicar no `▶ / ▼`, ou duplo-clique na
  linha da peça composta.
- **Expandir/colapsar tudo:** dois botões na barra ("Expandir tudo" /
  "Colapsar tudo"), à semelhança do que já existe noutras árvores da app.
- **Estado inicial:** peças compostas **colapsadas**. (Opcional: lembrar por
  utilizador/por item o que ficou aberto, como já se guardam larguras de coluna.)
- **Eliminar uma linha de ferragem** (o teu caso "pode haver necessidade de
  eliminar"): expandir a peça composta → selecionar a ferragem → **Eliminar
  linha** (menu de contexto/botão que já existe). Continua tudo lá, só deixa de
  estar sempre à vista.
- **Realce visual:** a linha da peça composta ganha destaque de cabeçalho (fundo
  bege/castanho, negrito) e o triângulo; as filhas ficam ligeiramente indentadas
  quando abertas.

## 5. Detalhe do "resumo" da peça composta

Sugestão do texto na coluna principal quando colapsada:

```
FUNDO+PES · 2 peças · 6 ferragens · 45,20 €
```

- **nome** da peça composta;
- **contagem** de filhos por tipo (peças / ferragens) — dá noção do tamanho sem abrir;
- **total** da peça composta (soma dos filhos), para o utilizador validar o valor
  sem precisar de expandir.

Se preferires mais sóbrio: `FUNDO+PES  (8 linhas)  45,20 €`.

## 6. Notas técnicas (porque é seguro e barato)

- É **100% visual**: usa o esconder/mostrar linhas do próprio `QTableWidget`.
  Nenhuma linha é apagada, nenhum cálculo, quantidade, preço, plano de corte ou
  export muda.
- A hierarquia **já existe nos dados** (`linha_pai_id` + `nível`), por isso
  agrupar filhas sob a sua peça composta não exige mudar o modelo nem a base de
  dados.
- Não afeta exports (PDF/Excel/plano de corte): esses leem as linhas todas, não o
  que está visível no ecrã.
- Divisões independentes e separadores mantêm-se como estão.

## 7. Pontos a decidires

1. **Variante A, B ou C?** (recomendo A).
2. **Resumo rico** (`2 peças · 6 ferragens · 45,20 €`) **ou sóbrio** (`8 linhas ·
   45,20 €`)?
3. **Lembrar** o estado expandido/colapsado por utilizador, ou começar sempre
   colapsado?
4. Queres que eu faça também um **mockup HTML interativo** (clicável, para
   sentires o expandir/colapsar a sério) antes de tocarmos no código?

> Assim que escolheres, implemento — é uma alteração contida na página de custeio
> (`orcamento_item_custeio_page.py`), sem migração nem risco de dados.
