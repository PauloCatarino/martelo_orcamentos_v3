# Drawing Views do iMos — análise e plano (2026-10-05)

Pedido do Paulo (04-10, à noite): explorar a parte do iMos que gera **automaticamente
layouts, plantas, cortes e alçados, com cotas** ("Drawing views"). Já tinha tentado e
nunca chegou a layouts válidos. Fontes usadas: os 7 vídeos da Online Academy que ele
descarregou, a configuração real do iMos (base `imos_LE`, **só leitura**), as pastas do
`I:\Library` e uma **cópia** da obra de teste `APAGAR_03`. A ajuda oficial
(`help.imos3d.com`) pede login, por isso não foi lida.

Propostas desenhadas: [`imos_drawing_views/Propostas_Layouts_A3.pdf`](imos_drawing_views/Propostas_Layouts_A3.pdf)
(7 folhas A3: índice, diagnóstico, planta, alçado, corte, folha única, variante cliente).

## 1. Em resumo

1. **É possível.** O iX CAD 2025 instalado faz plantas, alçados e cortes cotados e
   etiquetados, e (novidade do iX 2025) pode gerá-los **sozinho dentro de um Output batch**,
   tal como já se geram as listas: saída "Drawing Views" → layouts e/ou **PDF multi-folha**
   por encomenda.
2. **O que falha hoje é configuração, não o programa.** Na APAGAR_03 o desenho das vistas
   está bom; o que estraga são: moldura de artigo numa vista de obra, alturas triplicadas,
   larguras dos superiores em falta, etiquetas desproporcionadas, cortes sem nenhuma regra
   de cotas, escalas "ajustar à folha" e restos de 40+ tentativas na mesma obra.
3. **O caminho** (secção 5): moldura de obra → condições LE → cotagem de alçado → anotação
   → planta → corte → Output batch. Começar pelo alçado, que é o que mais se usa.

## 2. Como funcionam as Drawing Views (o modelo mental)

Confirmado pela análise da APAGAR_03 e pelos vídeos:

- **Uma vista = um bloco no espaço modelo**, com o desenho 2D já calculado pelo iMos
  (linhas visíveis, escondidas, peças cortadas tracejadas, símbolos de abertura):
  - `imosSectGround.N` — **planta** (corte horizontal visto de cima);
  - `imosSectView.N` — **alçado** (vista de frente de uma parede);
  - `imosSect.X` / `imosSectSideView.X` — **cortes** (frente / lado / topo).
- Cada vista tem camadas próprias para **cotas automáticas** (`….AutoDims`), **cotas à mão**
  (`….ManualDims`) e **etiquetas** (`….Label`). Por isso o "Refresh view" refaz as cotas
  automáticas sem estragar as manuais.
- **Cada vista vai para um layout** (folha) com uma viewport e uma **moldura** com legenda.
- **O que decide o resultado são princípios** do Element Manager:

| O quê | Onde (Element Manager) | Tabela na base |
|---|---|---|
| Cotas da planta | Outputs → Dimensioning Principles → Floor plan dimensioning | `DIMPLAN*` |
| Cotas do alçado | … → Elevation dimensioning | `DIMELEV*` |
| Cotas dos cortes | … → Front/Side/Top-view section dimensioning (iX 2025 SR2) | `DIMSECT*` |
| Etiquetas | Outputs → Annotation Principles | `LABELLING*` |
| Moldura / legenda | Outputs → Border | `DOCMANBORDERPRINCIPLE` |
| Automatizar por obra | Outputs → Output batches → saída "Drawing Views" | `CMSOUTPUT*` |
| Que objetos entram em cada linha | General Rules → Conditions | `CONDITIONS*` |

- Cada linha de um princípio de cotagem = **tipo de cota** + **estilo** + **condição**
  (filtro). Ex.: "larguras dos móveis do chão" = tipo *artigo* + condição *inserção Z ≤ 250*.
- **Document Manager ≠ Drawing Views.** Os relatórios `Report_*` que a LE já usa (o PDF de
  conjunto) são do Document Manager e trabalham **por artigo** (uma A3 por módulo, com
  isométrica, explodida, frente, esquerda, cima). As Drawing Views trabalham **por obra**
  (a divisão inteira). São complementares.

### A automação no iX 2025 (vídeo "Drawing Wizards inside Output Batches")

Element Manager → Outputs → Output batches → novo batch (Modo: *Order*) → saída com
"Output function" **Drawing Views**, com estes campos (lidos no vídeo):

- **Generate:** Layouts / Multi-Sheet-PDF / Layouts & PDF; **Output directory**.
- **Plan view settings:** Layout (moldura), Viewport scaling (no exemplo "Zoom extents"),
  Visualization level, Dimensioning principle, Annotation principle, Hidden lines,
  Create: article contours / coloration / display connectors.
- **Elevation settings:** os mesmos + Create: surface symbol / surface name / material
  symbol / material name / hatch / coloration / 2D symbols / display connectors.

Corre-se no Order Manager como os outros batches; o resultado do exemplo é um layout
"Plan view 1" + um layout por alçado ("Elevation 1…5"), cada um com moldura e legenda.

## 3. O que a configuração do iMos tem hoje

| Área | Estado |
|---|---|
| Document Manager (por artigo) | 40 princípios; os da casa em `_LANCA_ENCANTO/GENERICO` (`Report_Art_Princ`, `Report_STD_CLIENTE_*`, `Report_JF_VIVA_*`, `Report_Portas_*`). Em uso nos batches `JF_VIVA_*`. **Funciona.** |
| Cotagem de planta | 10 princípios, quase todos do kit de exemplo iFurn (`STANDARD`, `FloorPlan_Kitchen…`). |
| Cotagem de alçado | 13; três da casa: `Elevation_kitchen_LE`, `LE_Elevation_kitchen`, `Elevation_kitchen_V1`. |
| Cotagem de cortes | `Side/Front/Top-view section dimensioning` só com `STANDARD` — **sem nenhuma linha**. |
| Anotação | 20 princípios; da casa: `Elevation_ArtiName_Dim`, `Planta_ArtiName_Dim`, `Plan_View_LE_V1`, `Section_V1`, `STANDARD_V1`. Blocos em `I:\Library\AttDWG` (`_Medidas_Artigo.DWG` é da casa). |
| Molduras | 107 em `I:\Library\Bord` (`DmLayout_*.dwt`). Quase todas de **artigo**. De **obra** só as do kit: `DinA0..4_order`, `DinA4_LS_order`. |
| Output batches | 6; nenhum usa "Drawing Views". |
| Condições usadas pelas cotas | as do kit iFurn: classificam por **cota de inserção Z** (chão ≤ 250 mm, nicho 790–1200, superior > 1280) e por **tipo de peça** (porta, frente de gaveta, tampo…). |

## 4. Diagnóstico da APAGAR_03 (ver folha 0 do PDF)

As vistas foram extraídas de uma cópia da obra e redesenhadas tal e qual:

1. **Três cadeias de alturas.** Três linhas diferentes de `Elevation_kitchen_LE` fazem cada
   uma a sua cadeia (880/620/860/90; 120/1380/860/90 com o rodapé; 1500/860/90). Deve
   haver só uma linha com a cota de altura ligada.
2. **Faltam as larguras dos superiores** (600 | 600) no alçado. A planta tem-nas; no alçado
   a linha de "wall units" não as produziu — rever a condição/tipo dessa linha.
3. **Etiquetas enormes e por cima do desenho.** O bloco `_Medidas_Artigo` tem textos de
   60–80 mm no modelo; o tamanho no papel depende da escala da viewport.
4. **O rodapé `RDP_PVC_Frente_Dir` é tratado como módulo** (está no chão, passa na condição
   de "inferiores") → leva etiqueta e cotas.
5. **Planta:** cotas certas (2640,3; 600/600/1440,3; 606,4/2033,9), etiquetas ilegíveis.
   Escalas 1:5,4 e 1:40,6 — viewports "ajustadas à folha" em vez de escala normalizada.
6. **Corte A-A:** o desenho é bom (peças cortadas tracejadas, prateleiras, tulha), mas
   **zero cotas**: o princípio de corte lateral `STANDARD` não tem regras.
7. **Legenda com nomes de campos** ("IMOSARTICLEINFO1", "IMOSARTICLEPOSITIONHIERARCHY" a
   vermelho): a moldura `STANDARD` (`DmLayout_STANDARD.dwt`, bloco
   `iX_A3_Layout_Template_Article`) é de **artigo**, e o valor por defeito de cada campo é o
   próprio nome. Numa vista de obra não há artigo → fica o nome.
8. **Restos de tentativas:** camadas de 14 plantas, 10 alçados e 19 cortes na mesma obra.

## 5. Plano por fases (o que configurar, por ordem)

Tudo no iX Organizer → Element Manager. Fazer **cópias** dos princípios existentes e dar
nomes `LE_…`, nunca mexer nos do kit. Testar sempre numa obra **limpa** (ver F0).

**F0 — Obra de teste limpa.** Nova encomenda de teste com uma parede de cozinha
(inferiores, superiores, uma coluna, bancada) e um roupeiro. Não reutilizar a APAGAR_03
(tem 40+ vistas antigas). Confirmar que o separador *Drawing views* mostra
"Section Dimensioning" (iX 2025 SR2) — já mostra.

**F1 — Moldura de obra `LE_A3_Obra`** (Outputs → Border). Partir de `DinA3_order`
(`I:\Library\Bord\DmLayout_DinA3_order.dwt`) com o aspeto da `STANDARD` da casa. Campos
(estão a verde em todas as folhas do PDF):
`IMOSORDERCUSTOMER`, `IMOSORDERID`, `IMOSORDERDATE`, `IMOSORDERREVDATE`,
`IMOSORDEREMPLOYEE`, `IMOSVSLAYOUTNAME`, `IMOSVSSCALE`, `IMOSVSLAYOUTPAGE`.
**Valor por defeito de cada atributo vazio** (senão volta a aparecer o nome do campo).
Nada de `IMOSARTICLE*`.

**F2 — Condições LE** (General Rules → Conditions), copiando as `D_*` do kit:
- `LE_Art_Inferiores` = `D_Articles_base_tall_units` **e** nome não começa por `RDP_`
  (rodapés) nem pelos prefixos de remates/acessórios que a casa usa;
- `LE_Art_Superiores` = `D_Articles_wall_tall_units` (inserção Z > 1280) — confirmar com
  as obras reais que os `MS_*` passam;
- `LE_Art_Colunas` (altura > 1250 e Z < 250);
- `LE_Art_Alturas` = artigos de topo, sem decorativos/comprados/instalações/rodapés.
Os limites de Z (250 / 790–1200 / 1280) são os do kit: confirmar que servem às alturas da
LE (superiores a 1500 na APAGAR_03 → passam).

**F3 — Cotagem de alçado `LE_Alcado`** (cópia de `Elevation_kitchen_LE`), com 4 linhas:
larguras dos inferiores (por baixo), larguras dos superiores (por cima), **uma** linha de
alturas (`LE_Art_Alturas`) e paredes. Distâncias "em altura no papel" (ex. 8 mm à
primeira linha, 6 mm entre linhas) para ficar igual em qualquer escala. Alvo: folha 2.

**F4 — Anotação de alçado `LE_Alcado_Pos`.** Um bloco novo e pequeno em
`I:\Library\AttDWG` (círculo + nº de posição) em vez do `_Medidas_Artigo`; condições
`LE_Art_Inferiores/Superiores/Colunas` (o rodapé fica de fora). As medidas e nomes vão
para uma **tabela** ("Inserir tabela") com Pos / Artigo / Descrição / L×A×P.

**F5 — Planta `LE_Planta` + `LE_Planta_Pos`.** Cotas em 3 linhas (superiores, inferiores,
parede) + bancadas; móveis suspensos a tracejado; nº de posição. Alvo: folha 1.

**F6 — Corte lateral `LE_Corte_Lateral`** (Side-view section dimensioning), receita do
vídeo da SR2:
- *Article dimension* — Height dim **Yes**, zero point **Bottom**, position **Front**,
  dim type **Chain**, insertion height dim **Yes**, distance between articles **Yes**,
  depth dim **Yes** (zero **Back**, baseline);
- *Horizontal carcass parts* — posições das prateleiras/fundos (reference *between parts*);
- *Article front* (opcional) — folgas das frentes.
Alvo: folha 3.

**F7 — Output batch `LE_Desenhos_Obra`** (Mode: Order) com a saída "Drawing Views":
Generate **Layouts & PDF**, pasta `DOC\Desenhos` da obra, planta com `LE_A3_Obra` +
`LE_Planta` + `LE_Planta_Pos`, alçados com `LE_A3_Obra` + `LE_Alcado` + `LE_Alcado_Pos`.
Ver se "Viewport scaling" tem escala fixa; se só houver "Zoom extents", usar molduras A3
e A4 conforme o tamanho da parede. Depois de validado, juntar aos batches `JF_VIVA_*`.

**F8 — Validar com 3 obras reais** (cozinha, roupeiro, WC) contra o PDF de propostas.

## 6. O que eu posso fazer a seguir (com autorização)

- Criar os ficheiros de apoio sem tocar no existente: o `.dwt` da moldura `LE_A3_Obra` e o
  bloco de posição, como **ficheiros novos** em `I:\Library\Bord` / `AttDWG`.
- Um **verificador**: lê uma cópia da obra, extrai as vistas e desenha-as (como na folha 0)
  para conferir o resultado sem abrir o iX CAD.
- A configuração no Element Manager é sempre o Paulo que a faz (é escrita na base do iMos).

## 7. Anexo — o que mostra cada vídeo

| Vídeo | Conteúdo útil |
|---|---|
| iX 2021 — Drawing output | primeira versão das vistas (planta/alçado/corte) |
| iX 2023 — Drawing assistant | assistente para criar planta + alçados de uma vez |
| iX 2023 — Creation of border drawings | como fazer molduras com atributos |
| iX 2023 — Dimensioning principles | linhas de cotagem com condições (planta/alçado) |
| iX 2025 — Drawing wizards inside output batches | a saída "Drawing Views" nos batches (secção 2) |
| iX 2025 SR2 — Section dimensioning | cotagem de cortes frente/lado/topo (receita F6) |
| Annotation principles (2026) | etiquetas por condição e bloco |

Técnica usada (para repetir): imagens extraídas com o QtMultimedia do PySide6 (os vídeos
não têm legendas e o PC não tem reconhecimento de voz); configuração lida da `imos_LE` com
`app.services.imos_sql` (só `SELECT`); vistas da obra extraídas de uma cópia com a consola
do iX CAD (`-WBLOCK` dos blocos `imosSect*` → DXF) e redesenhadas em Python.
