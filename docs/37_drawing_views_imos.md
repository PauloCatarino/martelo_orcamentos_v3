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
- ~~A configuração no Element Manager é sempre o Paulo que a faz.~~ Revisto a 05-10: o Paulo
  autorizou-me a escrever as `DV_*` na base de testes `imos_LE_TESTES` (ver 6b). A base real
  continua só leitura.

## 6b. Volta 1 na base de testes (05-10, à tarde)

O Paulo aprovou o PDF e deixou-me avançar. Autorizou:

- escrever na **`imos_LE_TESTES`**, só linhas `DV_*`;
- controlar o iX CAD e o iX Organizer;
- gravar na obra de teste **ORC_260881_2604023** (cozinha/lavandaria em U);
- copiar ficheiros `DV_*` novos para `I:\Library\AttDWG`.

Ferramentas e receita em [`scripts/imos_drawing_views`](../scripts/imos_drawing_views/README.md).

**Requisitos dele:**

- tudo em A3 horizontal, sem "Lanca Encanto" nem "LE" nas folhas;
- cores por tipo, com os 5 estilos que já existem: inferiores azul, superiores magenta,
  colunas vermelho, tampos e alturas preto, paredes verde;
- no alçado, nome e medidas do módulo enquadrados e medidas das portas e gavetas, com o
  rodapé sem etiqueta;
- folha única com perspetiva + planta/alçado + corte + tabela;
- mais vale gerar layouts a mais do que a menos.

**O que ficou na base** (pasta `DV_Desenhos` em cada árvore do Element Manager):

| Tipo | Princípios |
|---|---|
| Condições | `DV_Art_Inferiores` (Z≤250, A≤1250), `DV_Art_Colunas` (Z<250, A>1250), `DV_Art_Nichos`, `DV_Art_Superiores` (Z>1280), `DV_Art_Alturas`, `DV_Art_Todos`, `DV_Frentes(_Baixo/_Cima)`, `DV_Tampos`. Os rodapés ficam sempre de fora (nome começa por `RDP`). |
| Cotagem | `DV_Planta`, `DV_Alcado` e a variante `DV_Alcado_Frentes`. |
| Etiquetas | `DV_Alcado_Etiquetas` (módulo + frentes), `DV_Alcado_Etiquetas_Modulos`, `DV_Planta_Etiquetas` (só o nome). |
| Moldura | `DV_A3_Obra`: 400×270, legenda neutra (Cliente, Obra, Data, Desenho, Escala, Folha, Desenhador), uma janela. |
| Output batch | `DV_Desenhos_Obra`: planta + alçados, `DV_A3_Obra`, "Best scale", Layouts & PDF em `C:\IMOS_Output_Batches\DV_Desenhos`. |

**Resultado na ORC_260881_2604023** (vistas refeitas com as DV_* e conferidas com o
`ver_vistas.py`):

- **Planta:** cadeias certas por cor:
  - azul 720 | 920 | 660 | 600;
  - vermelho 720 | 2180;
  - magenta 720 | 1580 | 600;
  - paredes 2900 / 2950;
  - lado direito 1160,4 / 1571,5.

  As 6 etiquetas saem com o nome certo. As colunas da parede da direita aparecem rodadas. Os
  rodapés e as máquinas ficam de fora.
- **Alçado da parede do fundo:** larguras por fiada e **uma** cadeia de alturas
  (880 / 620 / 810, total 2310). As etiquetas enquadradas estão certas (por exemplo ARM_02
  920×880×600) e as portas levam L×A ao centro (por exemplo 446,5 × 801,4).
- **`DV_Alcado_Frentes`:** carregado demais. Junta cadeias com as folgas das frentes
  (1,8 / 3,5 mm) e linhas de chamada a atravessar o alçado. Fica `DV_Alcado` como principal.

**Armadilhas encontradas** (e o que foi feito):

1. **Etiquetas minúsculas.** O iMos insere-as à escala 1 no modelo. A 1.ª versão dos blocos
   (`DV_Artigo_Medidas*`, `DV_Frente_Medidas`) era anotativa e em mm de papel, por isso não
   aparecia. Foi refeita em mm do modelo, para 1:20, e não anotativa: `DV_Etq_*`. Os
   ficheiros da 1.ª versão ficaram em `AttDWG` sem uso; só se apagam se o Paulo quiser.
2. **Escala de anotação (`CANNOSCALE`).** A 1:20 as etiquetas anotativas aparecem, mas as
   cotas ficam 20 vezes maiores. Fica a 1:1.
3. **Profundidades na planta.** A "Depth dim" das linhas Furniture põe a cota por cima do
   desenho. A linha "Furniture depth" põe-na longe, com chamadas a atravessar a planta.
   Ficou sem profundidades: vão na tabela.
4. **Correção ao diagnóstico** (ponto 8 da secção 4):
   - **Camadas:** as `imosSect*` de 14 plantas e 10 alçados também aparecem na
     ORC_260881_2604023, que nunca teve essas vistas. Vêm com a obra (biblioteca/modelo) e
     não são restos de tentativas.
   - **Etiquetas `_Medidas_Artigo`:** estão com FUNCT 1 = "Indexing detail" (legado), e não
     "Standard".
   - **Molduras:** a fonte é a base (`BINDATA`), não os ficheiros de `I:\Library\Bord`.
5. **Batch sem iX CAD.** O Output batch chama o assistente do iX CAD. No 1.º teste o iX CAD
   fechou-se durante o batch e nada foi gerado: não ficou PDF e o DWG não mudou. **Falta
   repetir com o iX CAD aberto.**

**Próximos passos:**

1. Correr o batch com o iX CAD aberto e ver os layouts A3 com a `DV_A3_Obra` e o PDF.
2. Tabela de módulos (princípio Table com SQL sobre `IDBINFO`, `<<IMOSORDERID>>`).
3. Cortes: falta conhecer os códigos dos atributos (a ajuda descreve-os, a base não tem
   exemplos). É preciso configurar uma linha no Element Manager e ler a base, como se fez
   com o batch.
4. Folha única (moldura com várias janelas) e indicadores de alçado legíveis na planta.

## 6c. Objetivo final acordado e ronda R1 dos roupeiros (06-10)

As voltas 2 a 5 (05-10, noite) estão resumidas no README de `scripts/imos_drawing_views` e
nos commits fc81906 a 2703144.

### Objetivo final (acordado com o Paulo a 06-10)

1. **O `IMOS.dwt` e o layout "1" não se mexem.** O Paulo copia o "1" para os seus layouts
   manuais (1(2), 1(3)…). O `IMOS_v2.dwt` fica sem efeito.
2. **Desenhos automáticos só pelo Output batch**, com o iX CAD fechado. Há um batch por
   tipo de obra, cada um com as suas regras e a sua moldura:
   - **`DV_Roupeiros`** agora;
   - **`DV_Cozinhas`** mais tarde (a legenda das cozinhas mantém a Descrição, porque têm
     vários artigos).
3. **Roupeiros:** por cada roupeiro, planta + alçado + **perspetiva** (a perspetiva continua
   a ser importante). O objetivo é que estes layouts cheguem para o cliente, sem layouts
   manuais.
   - **Planta:** medidas das portas, e o nome do artigo ao meio, à frente do artigo.
   - **Alçado:** nome e medidas do artigo em baixo, por fora; portas com 1 casa decimal;
     uma cadeia vertical com rodapé, rodateto, caixotes e a posição do nicho.
   - **Legenda de 2 linhas:** Artigo (número de posição), sem Descrição e sem Cliente, e
     Ref. cliente mais larga.
4. **De fora por agora:** tabelas (não inseriram) e cortes automáticos.
5. **Texto no modelo:** a barra de escala do modelo fica a **1:1**. O `IMOS_Text35` é
   anotativo e o batch muda a escala da obra (na APAGAR_15 ficou 1:16): 35 × 16 = 560 mm.
   - Notas: 50 mm no modelo (2,5 mm a 1:20).
   - Títulos: 70 mm no modelo.
   - Os estilos `DV_*` não entram no `IMOS.dwt` por agora (decisão dele).

**Rondas, uma de cada vez e cada uma com teste:**

- R1 batch + legenda;
- R2 etiqueta do artigo e portas com 1 casa decimal;
- R3 cadeia vertical;
- R4 planta;
- depois a perspetiva e as cozinhas.

### R1: batch `DV_Roupeiros` + legenda de 2 linhas (feito a 06-10, por testar)

Na `imos_LE_TESTES`, pasta `DV_Desenhos`:

- **Output batch `DV_Roupeiros`:** igual ao `DV_Desenhos_Obra`, mas com a moldura
  `DV_A3_Roupeiro` e as regras `DV_Roup_Planta`, `DV_Roup_Alcado`,
  `DV_Roup_Planta_Etiquetas` e `DV_Roup_Alcado_Etiquetas`.
  - Na R1 estas regras são cópias das de obra. As rondas seguintes mudam só as
    `DV_Roup_*`, por isso as cozinhas não são afetadas.
- **Moldura `DV_A3_Roupeiro`** (`criar_moldura_a3.ps1 -Legenda Roupeiro`, legenda
  `DV_A3_Legenda_Roup_v1`):
  - **linha 1:** Artigo (`IMOSARTICLEPOSITION`), Nome enc. iMOS, Enc. PHC, Ref. cliente,
    Obra, Entrega;
  - **linha 2:** Desenho, Escala, Folha, Desenhador, Data.
- **A confirmar no teste:** a ajuda lista o `IMOSARTICLEPOSITION` para molduras, mas não
  diz se as folhas do batch (que são de obra) o preenchem.
- A planta do `DV_Desenhos_Obra` passou a "coloration" 0 no script: foi o Paulo que a
  desligou no Element Manager.

**Resultado da R1** (APAGAR_15): a legenda de 2 linhas saiu certa, mas o **Artigo veio
vazio**. As folhas do batch são de obra e não preenchem o `IMOSARTICLEPOSITION`.

### R2: legenda, etiquetas do alçado e portas na planta (06-10, por testar)

- **Legenda `DV_A3_Legenda_Roup_v2`:**
  - Artigo = `IMOSARTICLEPOSITIONHIERARCHY` (sugestão do Paulo);
  - por cima, uma **faixa de teste provisória** com outros candidatos:
    `IMOSARTICLENAME`, `IMOSELEMENTARTICLE`, `IMOSELEMENTGROUPPOSITION`,
    `IMOSVSDESCRIPT` e `IMOSPLANPOSNAME`;
  - fica o que for preenchido e a faixa sai na versão seguinte.
- **Alçado (`DV_Roup_Alcado` + `DV_Roup_Alcado_Etiquetas`):**
  - a etiqueta do artigo vai para baixo do artigo, por fora (60 mm do modelo);
  - as cotas afastam-se 14 mm de papel (eram 8) para lhe dar lugar;
  - os módulos acima de 1490 mm ficam com a etiqueta por cima, por fora.
- **Portas, alçado:** bloco `DV_Lbl_PortaLxA` com largura × altura (`IMOSPARTWIDTH` ×
  `IMOSPARTHEIGHT`).
  - Os `COND.PART_SIZE_*` saíam em bruto (350.785714286 = o `FWIDTH` da base) e na ordem
    do veio.
  - A base não tem nenhuma medida arredondada (`FWIDTH` 350.7857), e a ajuda não tem
    formato de casas decimais.
  - **Hipótese a testar:** os `IMOS*` saem com as casas da precisão de unidades da obra
    (`LUPREC`, que é 2 nas obras atuais: "446.50"). Com `LUPREC` 1 devem dar "350.8".
- **Planta (`DV_Roup_Planta_Etiquetas`):**
  - a largura de cada porta à frente dela: bloco `DV_Lbl_PortaL`, condição nova
    `DV_Portas`, sem frentes de gaveta;
  - o nome do artigo ao meio, à frente do artigo (150 mm do modelo, lado y = −1).
- **Blocos novos em `I:\Library\AttDWG`:** `DV_Lbl_PortaLxA(_r)` e `DV_Lbl_PortaL(_r)`.

**Cadeia vertical (rodapé, rodateto, caixotes, nicho): não dá com o batch.**

- O batch só gera a planta e os alçados.
- A cotagem de alçado só tem os tipos Móveis, Alturas, Frentes (alturas/larguras),
  Paredes, Tampos, Instalação e Faceframe.
- O RP_A_01 é um só artigo: o rodapé (H75), os interiores (H2352), os remates e o nicho são
  grupos dentro dele, e as "Alturas" só veem artigos.
- Quem tem nichos, sub-artigos e peças horizontais da carcaça é a cotagem de **corte de
  frente** (tabela `DIMSECTFRONT`, tipos 1966 a 1971). Esse corte faz-se à mão ("Create
  Section", vista de frente).
- Decisão pendente do Paulo: princípio `DV_Roup_Corte_Frente` para usar à mão, ou perguntar
  à Enersale se o batch faz cortes.

**Resultado da R2** (APAGAR_15, 06-10):

- **Planta:** saem as larguras das portas. Ele aprovou e pediu "Porta" por cima da medida.
- **Artigo na legenda:** vazio, e os 5 campos de teste também. **Não há campo de moldura
  com o artigo nas folhas de obra.**
- **Portas:**
  - saem com 2 casas ("350.79 x 2344.40"), mesmo com `LUPREC` 1 na obra;
  - os `IMOSPART*` têm sempre 2 casas e os `COND.PART_SIZE_*` vêm em bruto;
  - o imos.msg não tem nenhum campo da peça arredondado (18037/18038 "Part size X/Y");
  - na 260881 parecia resolvido porque as medidas eram "redondas" (513.67).

### R3: "Porta", " X ", artigo com Alt/Cmp/Prof, paredes em cima (06-10, por testar)

- **Blocos novos em `AttDWG`** (todos com `_r`). Têm nomes novos porque a obra guarda a
  definição antiga:
  - `DV_Lbl_Porta_Alcado` e `DV_Lbl_Gaveta_Alcado`: "Porta"/"Gaveta" + L X A;
  - `DV_Lbl_Porta_Planta`: "Porta" + largura;
  - `DV_Lbl_Artigo_Azul/Verm`: "5000 X 2500 X 600";
  - `DV_Lbl_Artigo_Planta`: nome a preto + "Alt:/Cmp:/Prof:" a azul (exemplo do Paulo).
- **Condição nova `DV_Gavetas`** (frentes de gaveta).
- **`DV_Roup_Alcado`:** a cota das paredes (verde) passa para cima (1958 = 0).
- **Planta:** a cota azul (móveis) **não pode ir para a frente**. A cotagem de planta não
  tem posição para as larguras, só "dentro/fora" para a profundidade (ajuda
  "Dimensioning Principle – Floor Plan").
- **Legenda `DV_A3_Legenda_Roup_v3`:**
  - sem a faixa de teste e sem a célula Artigo;
  - linha 1: Nome enc. iMOS, Enc. PHC, Ref. cliente (larga), Obra, Entrega.

**Resultado da R3** (APAGAR_15, agora em L, 3 folhas):

- a planta ficou boa;
- nos alçados do L, as medidas das portas ao centro confundem-se com as linhas e com as
  vizinhas;
- na planta não aparecem a etiqueta "Planta 1" nem os indicadores "1 Vista 1" / "2 Vista 2"
  (no modelo existem);
- a etiqueta da Vista 1 fica longe, e o desenho não enche a folha.

**Diagnóstico** (cópia da APAGAR_15 em DXF):

- **Etiquetas e indicadores escondidos.** Os blocos `imosLabel*` e `imosFlag*` são
  anotativos e só têm a escala de anotação da obra (1:16). Nas folhas a 1:20 (planta) e a
  1:25 (Vista 2) ficam escondidos, porque as folhas têm `ANNOALLVISIBLE` = 0. A Vista 1 está
  a 1:16, por isso mostra a etiqueta. As etiquetas `DV_*` aparecem sempre porque o iMos lhes
  dá a escala da folha.
- **Etiqueta longe.**
  - O iMos insere-a 5 mm à esquerda e 6 mm abaixo do canto inferior esquerdo do limite da
    vista (−80, −96 a 1:16).
  - O desenho do bloco está todo à esquerda desse ponto: o círculo fica em −58, −15 mm de
    papel, cerca de 930 mm do modelo.
  - Na Vista 1 o limite inclui o corte da asa A do L, por isso a etiqueta fica ainda mais
    longe.
- **Batch:** as únicas chaves da saída "Drawing views" são generate, outputpath, layout,
  scaling, visugrad, dimensioning, annotation, hiddenlines, contour, coloration, connector,
  surfacesymbol, surfacename, materialsymbol, materialname, hatch e drawingsymbol
  (`imosr25.arx`). Não há opção para as etiquetas nem para o valor da escala.
- **Cadeia vertical:** o **corte de frente** só cota as medidas do artigo e as interiores
  (ajuda "Front-View Section Dimensioning"). Peças horizontais e nichos só existem no
  **corte lateral**.

### R4 (06-10, por testar)

- **Portas no alçado:**
  - bloco `DV_Lbl_Porta_3L`: "Porta" / "L 359.83" / "A 2481.40", estreito;
  - vai **por cima da porta, por fora** (110 mm do modelo);
  - `DV_Roup_Alcado` com as cotas a 16 mm;
  - as gavetas ficam ao centro, com `DV_Lbl_Gaveta_3L`.
- **Moldura `DV_A3_Roupeiro` com `ANNOALLVISIBLE` = 1** no layout, para as etiquetas e os
  indicadores da obra aparecerem em qualquer escala. Falta ver se o iMos copia este valor
  para os layouts que cria.
- **Batch de comparação `DV_Roupeiros_Zoom`:** igual, mas com "Zoom extents" (o desenho
  enche a janela). O PDF vai para `C:\IMOS_Output_Batches\Zoom`.
- **Etiqueta simples da vista:** `criar_etiqueta_vista.ps1 -Simples`.
  - Fica só o nome ("Vista 1"), com 3 mm, encostado ao desenho: no alçado à esquerda, na
    linha do chão; na planta, por baixo do canto.
  - Está em `C:\Pasta_Transferencia_Ourem_Calvaria\DrawingFlags_simples`. O Paulo instala
    no `config\DrawingFlags` (guardar antes os atuais).
  - Só vale para obras que ainda não tenham o bloco: a obra guarda a definição antiga.
- **`DV_Roup_Corte_Lateral`** (à mão, um corte lateral por coluna):
  - artigo: altura e profundidade (preto);
  - **peças horizontais** (1971, magenta): rodapé, rodateto, tampos e fundos dos caixotes,
    prateleiras fixas, "entre peças" e com a distância ao topo/fundo;
  - **nichos** (1969, vermelho).
  - A CONFIRMAR no Element Manager: os valores de "Height dim. – Reference" (1995 = 1,
    "Between parts"?) e "Offset of shelf to article" (1999 = 1).
  - Nota: o iMos só conta como peça horizontal as que usam os princípios Top shelf, Bottom
    shelf ou Fixed shelf. O rodapé pode não entrar se for uma peça vertical.

**Resultado da R4** (06-10):

- O `ANNOALLVISIBLE` = 1 da moldura **resultou**: as etiquetas e os indicadores das vistas
  aparecem em todas as folhas.
- O **Zoom extents ganhou**. As escalas ficam fora da lista (1:19.9, 1:16.8, 1:23), mas as
  cotas e as etiquetas saem todas.
- O corte lateral à mão ficou como está ("para não perder mais tempo").
- O Paulo afinou no Element Manager:
  - `DV_Roup_Alcado` 9 / 4 mm e `DV_Roup_Planta` 4 / 5 mm;
  - etiqueta do artigo no alçado a −40 e portas a +30;
  - artigo do chão na planta em (1, −1) / (−1, 0) com desvio (−700, −350).

### R5 (06-10, por testar)

- **O script passou a escrever os valores do Paulo** (a base ficou igual antes e depois do
  `--aplicar`).
- **`DV_Roupeiros` com Zoom extents** (scaling 0). O `DV_Roupeiros_Zoom` saiu da base
  (`BATCHES_RETIRADOS`).
- **Estilos `DV_AZUL`, `DV_MAGENTA`, `DV_PRETO` e `DV_VERDE`** (`estilos_cota_dv.py`,
  `CENTRADO`):
  - texto ao meio da linha (DIMTAD 0, DIMJUST 0), sem fundo (DIMTFILL 0);
  - quando não cabe, o texto vai para o lado e a linha prolonga-se (DIMTMOVE 0, DIMATFIT 2,
    DIMSOXD 0);
  - o `DV_VERMELHO` não foi pedido e ficou como estava;
  - o `imosBlocks.dwg` novo e o texto `comandos_estilos_APAGAR_15.txt` (para as obras que
    já têm os estilos) estão em `Pasta_Transferencia\Estilos_cota_R5`;
  - impresso numa cópia da APAGAR_15: "—5000—" com o texto ao meio e os "50" ao lado.
  - Cuidado: o texto de comandos só serve se a obra tiver os 4 estilos. Se faltar um, o
    `-DIMSTYLE` descarrila.
### R6: perspetiva pelo Document Manager e DV_VERMELHO centrado (06-10, por testar)

- **Resultado da R5:** o Zoom, o texto centrado (azul/verde) e as posições ficaram bem. O
  DV_PRETO só ficou certo depois de o Paulo o mudar à mão na obra (o PDF era anterior); as
  cotas não têm overrides próprios.
- **DV_VERMELHO** igual aos outros 4 (`CENTRADOS`). Ficheiros em
  `Pasta_Transferencia\Estilos_cota_R6`: `imosBlocks.dwg` e o texto de comandos (5 estilos).
- **Perspetiva:** o batch "Drawing views" só tem planta e alçados. A perspetiva vem do
  **Document Manager 2.0** (saída "Create Document Manager 2.0 data" do batch, ou à mão em
  DESIGN → Output).
  - Princípio `DV_Roup_Perspetiva`: um layout `DV_A3_Roup_Persp`, com uma janela
    "Perspetiva"; nível 9999 "show object order" (a obra inteira) e VisuLevel 4.
  - Saída: DWG + impressora com a página `PDF_LS_A3`, para
    `I:\Factory\Imorder\<obra>\DOC\DV_Perspetiva_3D`.
  - **Moldura `DV_A3_Roup_Persp`** (`criar_moldura_a3.ps1 -Legenda Roupeiro -LayoutNome
    DV_A3_Roup_Persp -JanelaDocMan Perspetiva`):
    - a mesma legenda;
    - a janela com XDATA `IMOS / DocMan / UserName:Perspetiva` (é assim que a LE dá nome
      às janelas: `A3_JF_VIVA_FrtEsqCimaPresp_V1`);
    - vista −1,−1,0.7 (frente-esquerda, de cima) e estilo Realistic.
    - A consola não tem `-VPOINT`: a direção (16/26/36) e o estilo (348) mudam-se no DXF.
  - Tabelas escritas: DOCMANPRINCIPLES, LAYOUTS, VIEWPORTS, FUNCATTR, LAYOUTPLOTS,
    FILENAMEATTR, POSSIBLEVIEWS, PLOTSETTINGS (linha da moldura DV) e pasta (tipo 350).
  - **Falta:** o número de tipo da saída "Document Manager 2.0" no `CMSOUTPUTITEM`. Nenhum
    batch da LE a usa. O Paulo junta-a no Element Manager e eu leio-a da base.
  - **Resultado (06-10):** a folha saiu em `APAGAR_15\DOC\DV_Perspetiva_3D` (PDF e DWG),
    mas o Paulo prefere os Document Managers que já tem. O `DV_Roup_Perspetiva` e a moldura
    `DV_A3_Roup_Persp` saíram da base (`DOCMAN_RETIRADOS`, `MOLDURAS_RETIRADAS`), e o
    `DmLayout_DV_A3_Roup_Persp.dwt` saiu da pasta TEMP do iX CAD, a pedido dele. O
    `-JanelaDocMan` do `criar_moldura_a3.ps1` fica, para quando for preciso dar nome a
    janelas.

- **Cotas verticais longe do alçado:** ficam à direita do **limite** da vista, que o iMos põe
  300 mm depois do último artigo, mais a distância da 1.ª cota (9 mm, a mesma das cotas de
  cima e de baixo). Na Vista 2 a 1:25 eram ~1280 mm do modelo. Só a distância é nossa, e
  baixá-la encosta a cota verde de cima às etiquetas das portas.

### R7: textos e cotas feitos à mão no Model (06-10, por testar)

- **Pedido:** reta final. Os PDFs servem. Falta escrever e cotar à mão no Model (1:1) com texto
  normal (preto) e títulos (azul), legíveis nos layouts `1` / `1 (2)` e no PDF.
- **Porque é que as cotas e os textos crescem quando a escala muda** (lido nos DXF da APAGAR_15,
  da 1556_01_26_JF_VIVA e numa cópia do `config\IMOS.dwt`):
  - o IMOS.dwt abre as obras com o estilo de texto **`IMOS_Text35`** e a cota
    **`IMOS_VIEW_RED`**. São anotativos com **35 mm de papel** (`IMOS_Text25`: 25 mm);
  - a escala de anotação do Model vem a 1:1 e o `ANNOAUTOSCALE` é 4. Quando a escala muda (o
    batch põe 1:16, 1:25…), cada objeto anotativo ganha essa escala. Um texto de "50" passa
    a 50 mm **no papel**, ou seja 800 mm no Model a 1:16;
  - o IMOS.dwt (gravado pelo Paulo a 06-10, 09:49) já traz no Model o título
    `_01_26_JF_VIVA_()` (135, azul por formatação `\C5`) e a lista de materiais (50), ambos em
    `IMOS_Text35`: todas as obras novas nascem com eles.
- **Solução:** estilos anotativos em mm de papel a sério, e o Model a 1:20.
  - `DV_Texto`: 2,5 mm de papel, camada `DV_Texto` (cor 7, preto na folha).
  - `DV_Titulo`: 5 mm de papel, camada `DV_Titulo` (cor 5, azul).
  - Os dois com letra simplex e largura 0,8, a do IMOS_Text35.
  - Cotas: os `DV_*` (2,5 mm); a atual passa a ser o `DV_VERMELHO`.
  - Escala de anotação do Model: **1:20**. O texto de 2,5 mm vê-se com 50 mm no Model, como
    o "50" a que o Paulo está habituado.
  - Numa janela a 1:16 o texto sai com 2,5 mm e numa a 1:25 também. Numa janela com escala
    fora da lista (o `1 (2)` estava a 1:25,6), o `ANNOALLVISIBLE 1` mostra-o com a escala
    mais próxima que o objeto tenha (~2 mm).
- **Ficheiros** (`estilos_cota_dv.py --manual` / `--dwt`) em `Pasta_Transferencia\Estilos_R7`:
  - **`comandos_R7_APAGAR_15.txt`**, para colar no Model da APAGAR_15. Faz o mesmo que os da
    R6 (cotas centradas; na APAGAR_15 o DV_VERMELHO ainda tinha `DIMTMOVE 1`, a cota com
    chamada) e cria as camadas, os estilos de texto e a escala de anotação 1:20.
    - Simulado na consola numa cópia: tudo certo.
    - O `-STYLE` fica no fim. A consola não o tem (lá é `STYLE`), mas o iX CAD normal deve
      ter: é a única linha não testada.
  - **`IMOS.dwt`** candidato:
    - feito na consola a partir de uma cópia do `config\IMOS.dwt`;
    - comparado o DXF objeto a objeto: só ganhou 5 dimstyles, 2 camadas e 2 estilos de texto;
    - os 2 textos do Model ganharam a escala 1:20 e ficam ENORMES até o Paulo lhes mudar o
      estilo para `DV_Titulo` / `DV_Texto`. A consola não muda estilos de MTEXT, por isso
      esse passo é dele;
    - o layout `1` fica igual.
- **imosBlocks.dwg:** o Paulo copiou o da **R5** para `config\DrawingFlags\`. O iMos procura-o
  em `config\` (onde continua o de 05-10). Falta copiar o da R6 para `config\`. O de
  `DrawingFlags` não é usado.
- **Resultado (06-10):**
  - o `imosBlocks.dwg` da R6 está no `config\`;
  - o Paulo instalou o IMOS.dwt da R7 (o original ficou em `IMOS - Cópia (2).dwt`);
  - na APAGAR_15 o **`-STYLE` não existe no iX CAD**: as linhas a seguir abriram um ARC, que
    ficou `*Invalid*`, sem nada desenhado. Os estilos de texto só podem vir pelo IMOS.dwt.

### R8: IMOS_Text35 à escala dos DV_* e IMOS.dwt pronto para uma obra nova (06-10, por testar)

- **Pedido:** o Paulo cota no Model com o **`IMOS_Text35`** e quer continuar com ele, mas à
  escala dos `DV_*`. O texto livre faz com MTEXT e `DV_Texto` / `DV_Titulo`. Vai fazer o ciclo
  completo numa obra nova.
- **Cota `IMOS_Text35`:**
  - fica vermelha, com setas e 1 casa decimal, e anotativa;
  - medidas dos DV_*: texto 2,5, setas 1,5, chamadas 1/1, afastamento 0,6, linhas
    paralelas a 7;
  - o texto passa ao estilo **ISO**, porque o estilo de texto `IMOS_Text35` tem altura fixa
    35 e mandava sobre o DIMTXT;
  - comportamento centrado dos DV_*: sem a chamada do `DIMTMOVE 1`;
  - volta a ser a cota atual;
  - os `IMOS_VIEW_*` ficam como estavam: são da LE e ninguém os pediu.
- **Os 2 MTEXT do Model do IMOS.dwt:**
  - passam a 5 mm (título) e 2,5 mm (lista) de papel, com o `SCALE`, porque a consola não
    muda o estilo de um MTEXT;
  - a escala 1:20 acompanha (a mesma posição; no Model a 1:20 ficam com 100 e 50 mm);
  - a letra é a mesma do `DV_Texto`.
- **Ficheiros** (`estilos_cota_dv.py --dwt-r8` sobre o IMOS.dwt da R7; o `--dwt` faz tudo a
  partir do original e dá o mesmo resultado, objeto a objeto) em `Pasta_Transferencia\Estilos_R8`:
  - `IMOS.dwt`;
  - `comandos_R8_obra_aberta.txt`: para as obras que já existem; já não tem o `-STYLE`.

### R9: PDF vazio na APAGAR_16 = etiqueta da vista sem geometria (06-10, por testar)

- **Sintoma:**
  - na APAGAR_16 (obra nova, IMOS.dwt R8) o batch `DV_Roupeiros` deu o PDF em branco;
  - nas folhas `Planta 1`, `Vista 1` e `Vista 2` a escala era `1:447154471544715520`;
  - a 1556_01_26_JF_VIVA (real, 06-10) tinha o mesmo.
- **Causa** (DXF das APAGAR_14, 15 e 16):
  - as janelas `BRef_of_View` tinham o centro em 5E19 e a altura em 1,1E20;
  - os blocos `imosLabelPlanview` / `imosLabelElevation` estavam inseridos em **(1E20, 1E20)**,
    e o Zoom extents foi até lá;
  - nas obras novas entra o bloco da pasta `DrawingFlags`, que era a **versão simples da R4:
    só o atributo, sem geometria**. Um bloco sem extensão faz o iMos pô-lo em 1E20;
  - a APAGAR_14 e a 15 tinham o bloco com o círculo (extensão −69,25,−26,25 a −20,−3,75) e o
    iMos punha-o a −80,−96,25 do canto da vista, a 1:16 e a 1:20.
  - A R4 nunca foi testada numa obra nova: a APAGAR_15 já tinha o bloco antigo definido.
- **Correção** (`criar_etiqueta_vista.ps1 -Simples`): os blocos simples levam 2 pontos na
  camada **Defpoints** (não imprime) nesses mesmos cantos. A extensão volta a ser a do símbolo
  e a etiqueta fica onde a R4 a desenhou.
- **Escala da legenda:** o `IMOSVSSCALE` é preenchido pelo iMos já com 1 casa decimal
  (`1:19.6`, `1:22.5`, `1:16`); o número enorme era só o da janela partida.
- **Ficheiros:** `Pasta_Transferencia\DrawingFlags_simples_v2`.
  - Os 2 DWG vão para `config\DrawingFlags`, para as obras novas.
  - `1_redefinir_alcado.txt` e `2_redefinir_planta.txt` redefinem o bloco numa obra aberta
    (`-INSERT nome=ficheiro`, depois Esc), porque o bloco que já está no desenho manda sobre o
    da pasta.

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
