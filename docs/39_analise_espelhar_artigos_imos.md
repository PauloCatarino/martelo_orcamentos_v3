# 39 — Espelhar artigos no iMos (ESQ → DIR): análise de viabilidade

Análise de 23-10-2026, pedida pelo Paulo. **Sem código e sem escrita em lado nenhum**: só leituras
na `imos_LE` (com `ler_imos.ps1`, transação sempre desfeita) e nos ficheiros do iX CAD 2025.

## 1. O pedido

Fazer o espelho de um artigo do iMos como ele faz à mão: o `RP_A_01_DIR` é o `RP_A_01_ESQ` espelhado,
o `RP_A_02_DIR` é o `RP_A_02_ESQ` espelhado (obra de teste `APAGAR_14`, PROADMIN 7443, na `imos_LE`).
O `MIRROR` do AutoCAD não serve: espelha o desenho, mas não o artigo. Uma porta esquerda tem de passar
a direita e levar as dobradiças para o outro lado. As colunas trocam de ordem.

## 2. O que muda de ESQ para DIR (medido na APAGAR_14)

Comparação da lista de peças calculada pelo iMos (`IDBGPL` + `IDBGRPS` + `IDBATT` + `IDBPURCH`).

| | RP_A_01 | RP_A_02 |
|---|---|---|
| Peças | 56 = 56, os mesmos princípios e as mesmas medidas | 45 = 45, iguais |
| Divisão das colunas (`ANGL_ZONE_LINEAR_DIVISION`) | `2:2:1` → `1:2:2` | as 2 colunas trocam de ordem |
| Ordem das colunas | 2PA+varão · 3 gavetas · 4PA → 4PA · 3 gavetas · 2PA+varão | igual, ao contrário |
| Porta simples `1P_O_2222_DB` | direita (RIGHT) → **esquerda (LEFT)** | não tem |
| Dobradiças | as 5 da porta simples seguem a porta, sozinhas | — |
| Dentro de cada coluna (gaveteiro, prateleiras, laterais) | **igual** | igual |

O par que já está na biblioteca, `RP_CANTO_SEGO_ESQ` / `RP_CANTO_SEGO_DIR`, confirma a mesma regra:
`20MM:1:0MM` → `0MM:1:20MM`, `1:1:972.5MM` → `972.5MM:1:1`, `400MM-15.7MM:150MM:1` →
`1:150MM:400MM-15.7MM`. O gaveteiro fica igual.

### Regra do espelho (proposta, por confirmar com o Paulo)

1. **Divisões na largura** (`DIVDIR = H` na biblioteca, direção `1, 0, 0` na obra): inverter a fórmula
   (`a:b:c` → `c:b:a`) e a ordem das zonas filhas. Fazer o mesmo, por recursão, dentro de cada zona.
2. **Portas simples:** trocar a abertura esquerda ↔ direita. As dobradiças vêm atrás pelo Connection Scan.
3. **O que tem lado:** laterais com «Lateral esquerda/direita» e «Informação de produção»
   `LATERAL_ESQ`/`LATERAL_DIR`, remates `ESQ`/`DIR`, molduras (`ANGLELFR` LEFT/RIGHT), cortes de início e
   de fim, peças de canto. Troca-se o lado *e* a posição. Por isso, numa coluna simétrica fica tudo igual
   (é o que se vê nos dados).
4. **Nomes:** `_ESQ` ↔ `_DIR` no artigo e nos grupos.
5. **Não muda:** alturas (divisões `V`), profundidades (`I`), materiais, orlas, gavetas.

## 3. Onde vive cada coisa

- **Artigo dentro da obra:** no `.DWG` e no `.FXF` (formato binário da imos, 12 MB na APAGAR_14).
  As tabelas `IDB*` são só o *resultado* calculado ao gravar. Servem para comparar, não para editar.
- **Artigo da biblioteca:** em tabelas legíveis da base: `articles` (1 linha), `anglprim` (1),
  `anglzone` (árvore de zonas, `TREEID` `0.0.1.1…`, `DIVDIR`, `LINDIV1`), `anglelem` (peças da zona:
  princípio, `RIGHTSIDE`, `DOORHISIDE`, `MANINFO`, cortes), `anglconi` (uniões), `ANGLELFR`, `anglgrtx`.
  Hoje há 748 artigos (TYPE 46), todos com `INORDER = ''`.
- **Campo nativo `articles.MIRRORED_ARTICLE`** («Mirrored article», mensagem 2950 do `imos.msg`):
  existe no iX 2025 e no Element Manager (`ElementManagerControl.dll`), e o `imosr25.arx` usa-o no
  código de inserir/copiar/mover artigos (`ArticleHandling`, ao lado de «Refreshing copied article to
  apply modifications!»). **Está vazio nos 1784 registos.** A tradução portuguesa (`PTG;2950`) está
  vazia: no Element Manager em português o campo pode aparecer sem nome.
  Os 52 PDF de novidades do iX 2025 não falam de espelhar artigos (são do lançamento, não do SR2).

## 3a. Como o iX faz o espelho (ajuda online, lida a 23-10-2026 com o login do Paulo)

Tópicos «Mirror iX Articles and Room Objects» (novidades do **iX 2025 SR2**) e «Mirror – CAD Method».
O iX do Paulo está na versão **17.0.02.95** (ficheiros de 30-09-2026), que já traz o campo na base, no
Element Manager e no `imosr25.arx`. Por isso a função já está instalada.

- Usa o próprio **`_MIRROR`** (Designer › Funções CAD, ou escrever o comando). Exige **Article Mode
  ligado** (barra de estado do CAD) e **3D Editing desligado**.
- Escolhem-se os artigos e os dois pontos do eixo. Uma janela pergunta se apaga os originais (Sim/Não).
- **Artigo simétrico:** espelha-se logo, sem mais nada.
- **Artigo não simétrico** (os roupeiros ESQ/DIR): é preciso ter os **dois** como princípio «Artigo»
  na biblioteca. O espelho tem de ser feito à mão no iX CAD, «uma imagem exata». No Element Manager ›
  Artigo › original › «Mirrored article» escolhe-se o outro e grava-se. Ficam «gémeos»: espelhar
  qualquer um dos dois insere o outro.
- **Limite:** «as alterações específicas do artigo ou da obra não são tidas em conta». O gémeo entra
  tal como está na biblioteca. O que se mexeu na obra tem de se refazer.
- Não serve para peças soltas.

**O que isto quer dizer:** o iX já sabe *trocar* o ESQ pelo DIR, mas não sabe *fazer* o DIR. Fazer o
DIR (o trabalho de hoje à mão) é exatamente a parte que a ferramenta B automatizaria.

## 4. Caminhos possíveis

| Caminho | Possível? | Risco | Nota |
|---|---|---|---|
| A. Função nativa (`_MIRROR` + «Mirrored article») | **Sim, já instalada** (iX 2025 SR2) | nenhum, se testado numa obra de teste | Troca ESQ ↔ DIR na obra. Não *cria* o DIR, e o gémeo entra sem as alterações feitas na obra. |
| B. Ferramenta no Martelo «Espelhar artigo» (biblioteca) | **Sim** | baixo: só cria um artigo novo e nunca mexe nos existentes nem nas obras | Lê o ESQ das tabelas `angl*`, faz o DIR com a regra da secção 2 e grava como artigo **novo**, 1.º na `imos_LE_TESTE02` (R02: com linha na `DATACHANGELOG`; R04). Pode preencher o `MIRRORED_ARTICLE` dos dois. |
| C. Botão/plugin dentro do iX CAD | **Não**, sem a imos | — | O iX CAD é um AutoCAD OEM: sem LISP, sem SCRIPT, COM fechado (já provado). Os 4 módulos .NET que carregam lá dentro têm assinatura `.sig` da imos (`imosRibbon26`, `imosManager.PaletteWrapper26`, `MMF_CommunicationInterface26`, `imosExConnect26`), por isso um plugin nosso não carrega. Um botão da aba «Imos» só chama comandos que já existem, e nenhum edita a estrutura de um artigo. |
| D. Mexer no programa da imos (engenharia reversa para alterar) | **Não** | alto | Partia a assinatura e a licença, desaparecia na próxima atualização e põe em risco a produção. *Ler* o código para perceber uma interface é diferente e já foi feito (Organizer, canal MMF). |

**Fluxo com o caminho B** numa obra real:

1. No Article Designer, gravar o artigo da obra na biblioteca (disquete). *Falta confirmar* que grava
   nas tabelas `angl*`.
2. No Martelo, «Espelhar»: escolhe-se o artigo e vê-se a árvore ESQ e DIR lado a lado, com a lista
   do que muda. Grava como `_DIR`.
3. No iX CAD, inserir o `_DIR` do catálogo, ou espelhar com o `MIRRORED_ARTICLE`, se o caminho A
   funcionar.

## 5. Plano de teste proposto (por fases, cada uma com o OK do Paulo)

- **M0 — FEITO (23-10-2026).** Ajuda lida (secção 3a): a troca ESQ ↔ DIR é nativa, mas o DIR tem de
  existir na biblioteca.
- **T1 — testar a função nativa, sem código (o Paulo, no iX CAD).** Usar o par que ele já fez à mão
  na APAGAR_14:
  1. gravar o `RP_A_01_ESQ` e o `RP_A_01_DIR` como princípios «Artigo». Ele escolhe o nome e a pasta,
     e a base (TESTE02, se a usar no iX CAD; senão numa pasta de testes da `imos_LE`);
  2. no Element Manager › Artigo › ESQ › Details › «Mirrored article» (pode estar sem nome em
     português: é a linha depois do princípio de cálculo), escolher o DIR e gravar;
  3. numa obra de teste, inserir o ESQ, ligar o Article Mode, desligar o 3D Editing e fazer `_MIRROR`
     com um eixo vertical. Responder «Não» para manter o original;
  4. esperado: aparece o DIR espelhado ao lado, com a porta simples à esquerda. Depois de gravar a
     obra, o Claude compara as duas listas de peças, como na secção 2.
  Ver também o que acontece a um artigo **simétrico** sem gémeo (uma coluna só com porta simples):
  a porta troca de lado sozinha?
- **M1 — só leitura, depois do T1.** Ferramenta que lê um artigo da biblioteca e mostra o gémeo, sem
  gravar nada. O objetivo é fazer automaticamente o DIR que o iX pede (secção 3a).
  Prova: espelhar o `RP_A_01_ESQ` (gravado na biblioteca pelo Paulo) e comparar com o `RP_A_01_DIR`
  que ele fez à mão. Têm de bater: as mesmas peças e medidas, e a porta e as dobradiças do lado certo.
- **M2 — escrita na TESTE02.** Grava o `_DIR` como artigo novo. O Paulo abre-o no Article Designer,
  insere-o numa obra de teste e grava. A comparação da secção 2 corre outra vez sobre as `IDB*`.
- **M3 — `imos_LE`.** Só depois de M2 OK, com o método das migrações do CAM (cópia de segurança,
  ensaio, comparação = 0).

O que pode falhar: campos com «lado» que ainda não conhecemos (uniões de canto, cortes início/fim,
`LEFTHINGE`/`RIGHTHINGE`, que nalgumas zonas têm valores sem sentido), artigos com DWG de compras
assimétricos (puxadores, perfis). A M1 serve para os apanhar antes de gravar o que quer que seja.

## 6. Ficheiros desta análise

Scripts e resultados no scratchpad da sessão (não ficam no repositório): `comparar.py`, `arvore.py`
(árvore por artigo a partir das `IDB*`), `zonas.py` (árvore da biblioteca). As consultas são todas
`SELECT` sobre `IDBGPL`/`IDBGRPS`/`IDBINFO`/`IDBATT`/`IDBPURCH` (`ORDERID = 'APAGAR_14'`) e sobre
`anglzone`/`anglelem` (`NAME IN ('RP_CANTO_SEGO_ESQ','RP_CANTO_SEGO_DIR')`).
