# Transferência de dados do iMos (`.cfg` da lista de corte)

O CSV que dá origem à Lista Material (`I:\Cutrite\Work\Cutrite_Import_CSV\<obra>_Lista_Corte.csv`)
sai do iMos por um princípio de **Processar transferência de dados** (Element Manager), que
corre um ficheiro `.cfg`. Esta pasta guarda, com histórico, os `.cfg` que fazemos e um
verificador.

| Ficheiro | Faz |
|---|---|
| `EXPORT_CSV_CUT_RITE_LE_V2.cfg` | Cópia do `EXPORT_CSV_CUT_RITE_LE.cfg` em uso com as colunas pedidas pelo Paulo (29-10-2026): `… Enc.; Cliente; Artigo; SubArtigo; Notas; Notas_1; Cliente_Final` — **RP** passa a **Artigo**; **SubArtigo** (`ARTNR`, o artigo mais próximo da peça) à direita; sem CNC/ABD/BHT; no fim a coluna técnica **ArtigoNome** (nome do artigo principal), que o Excel usa para deixar o SubArtigo vazio quando é igual, e a coluna **ISPEC** (forma da peça) — e com o `ACCUMULATE` corrigido. Testada na APAGAR_14 (29-10, 15h05); fica como **cópia de referência**. Só para obras de teste até o modelo da Lista Material ser adaptado (ver «Falta no Excel»). |
| `EXPORT_CSV_CUT_RITE_LE_V1.cfg` | **Ensaio (29-10-2026):** a V2 com as colunas 16-18 com os nomes que o Paulo deu no `imos.msg`: `… Cliente; Posicao; Artigo/SubArtigo; Piso; Notas; …; ArtigoNome; ISPEC`. **Piso** = `CP90NAME`, o campo «Name» do artigo (o 1.º ensaio, com `ART_CPID`, saiu vazio). O `V1.cfg` antigo (ensaio do cabeçalho da obra, 07-10) ficou no servidor como `EXPORT_CSV_CUT_RITE_LE_V1.cfg.copia_2026-10-29_173746`. |
| `gerar_cfg_v2.py` | Gera o `EXPORT_CSV_CUT_RITE_LE_V2.cfg` a partir do `.cfg` em uso (latin1 + CRLF, só troca as linhas ativas; as antigas ficam comentadas). A fórmula do SubArtigo e as colunas do fim (`COLUNAS_FIM`) estão no topo. |
| `gerar_cfg_v1_piso.py` | Gera o `EXPORT_CSV_CUT_RITE_LE_V1.cfg` a partir da V2 desta pasta (muda só o cabeçalho, as colunas 16-18 e a linha das peças; as da V2 ficam comentadas). |
| `verificar_csv_subartigos.py` | Lê um CSV exportado e compara-o com a base do iMos (só SELECT): Artigo, SubArtigo e quantidades por peça, ISPEC e, no CSV da V1, o Piso. Também confere CSV antigos, só pelo artigo. |

## Como o iMos guarda e usa o `.cfg` (descoberto a 29-10-2026)

- O `.cfg` que conta é o que está **dentro da base** (`imos_LE`), não o da pasta
  `\\SERVER_LE\Homag_iX\CFG`. O princípio (`PDTLINK`) guarda só o nome do ficheiro
  (`CONFIGFILE`); o conteúdo está em `BINDATA` (`INTERNTYPE='CFG'`, `NAME` = nome do
  princípio). Mudar o ficheiro da pasta não faz nada: é preciso **importá-lo** no princípio
  (botão ↓ em «Default Settings») e Guardar.
- Ao correr, o iX CAD escreve o `.cfg` em `%APPDATA%\imos AG\iX CAD 2025\TEMP\<princípio>_<n>.cfg`
  e o motor é o `IDBCCLG25.dll` (a janela das mensagens chama-se «IDBCCLG25»).
- Com «Configuração do caminho = Standard», o **Output path** do princípio substitui o
  `LOCATION` do `.cfg`. O `SUBDIRNAME` cria a subpasta, mas **o ficheiro só lá entra se o
  `PARTFILENAME` começar por `\`** (o Productionmanager usa `\Project`). Com
  `PARTFILENAME=AUFTRAG` o nome fica colado e o ficheiro vai para a pasta de cima: no ensaio
  de 29-10 saiu `...\Cutrite_Import_CSV\TESTE_SUBARTIGOSAPAGAR_14_Lista_Corte.csv` (e a
  subpasta `TESTE_SUBARTIGOS` ficou vazia). A documentação da imos não diz isto.
- O princípio `EXPORT_CSV_CUT_RITE_LE` é o **por defeito** (corre ao gravar a obra). O
  `EXPORT_CSV_CUT_RITE_LE_V1` é de ensaio; em 29-10-2026 tinha lá dentro o
  `Homag_DF_Productionmanager.cfg` (por isso saiu um XML, em
  `...\Cutrite_Import_CSV\Productionmanager\Project.xml`).
- **«Erro no ficheiro!» + nome do CSV** (mensagem 15017 do `imos.msg`, «File error!») = o
  iMos não conseguiu abrir o CSV para escrever. A 29-10-2026 foi porque o
  `APAGAR_14_Lista_Corte.csv` estava aberto noutro programa (Windows: 0x80070020, «está a ser
  utilizado por outro processo»; deixava ler mas não escrever, como faz o Excel). O `.cfg`
  não tinha culpa. Para ver o CSV sem o prender, usar o Notepad++ / Bloco de Notas, não o
  Excel — e o Excel, ao gravar, ainda muda o ficheiro (`494.0` → `494`, tira o `;` final).
- **Um campo que não existe no `STRING_MAT`** dá a caixa «Erro no ficheiro de configuração.
  Chave:STRING_MAT / <campo> / O campo não existe na base de dados!» **uma vez por peça e por
  campo**. Quem a mostra é o `idbcclg.exe` (`...\iX CAD 2025\BIN\`), um processo à parte do
  iX CAD, que fica preso nela. A 29-10-2026 o OK enviado de fora não a fechava. A solução foi
  terminar o processo (Gestor de Tarefas → `idbcclg` → Terminar tarefa), o que não mexe na
  obra. A linha sai **sem** essas colunas (as seguintes andam para a esquerda) e o CSV pode
  ficar cortado a meio: não serve, exporta-se outra vez.
- A macro `Import_CSV_Imos_1` do modelo da Lista Material lê o **primeiro** `*.csv` da pasta
  `Cutrite_Import_CSV` (só a de cima) cujo nome tenha a obra, e copia as colunas **por
  posição** (1–22 → `LISTA_ORDENADA` B–W). A passagem para a `LISTAGEM_CUT_RITE` é por
  **nome** de cabeçalho (CNC/ABD/BHT nunca passavam).

## Os campos que interessam aos artigos

- `SPLITLEFT[PARTPOSSTR;.]` → artigo principal (coluna RP). `PARTPOSSTR` é uma coluna da
  `IDBGPL`: `<posição do artigo principal>.<número da peça>`, **diferente em cada peça** —
  nunca a pôr no `ACCUMULATE`.
- `POSSTR` → posição do artigo onde a peça está. Num sub-artigo (artigo dentro de outro,
  sem «posição própria») vem **vazio**.
- `ARTNR` → nome do artigo onde a peça está (o mais próximo): `BL_3GVT_RP_01` nas peças do
  gaveteiro, `RP_A_01_ESQ` nas outras (confirmado no ensaio da `APAGAR_14`, 29-10).
  `ARTNR_NR_ID` → o seu ID (49187 para o BL; o `%s` imprime IDs numéricos sem problema).
- `TOPARTICLE_NAME[ARTNR_NR_ID]` → nome do artigo de topo (dica da imos, KB #00867; confirmado).
  Não há outras funções `TOPARTICLE_*` no motor.
- **Os campos do artigo no iX CAD e na base** (o Paulo traduziu-os no `imos.msg` a 29-10-2026;
  o `imos.msg` é UTF-8, linhas `PTG;<n>\t;<texto>`):

  | Mensagem | Original (ENG) | Paulo (PTG) | Na base | No `.cfg` |
  |---|---|---|---|---|
  | 10410 | Pos. Number | Posicao | `IDBINFO.POSSTR` | `POSSTR` (vazio nos sub-artigos); a do principal: `SPLITLEFT[PARTPOSSTR;.]` |
  | 6700 | Hierarchy | Hierarquia de Artigo | (calculado; cinzento no iX CAD) | — |
  | 41 | Name of Element Group | Artigo/SubArtigo | `IDBINFO.GROUPNAME` (= `IDBGRPS.NAME`) | `ARTNR` (artigo mais próximo) |
  | 1219 | Name | Piso | `IDBINFO.CPID` do artigo | `CP90NAME` (ou `IDBINFO_CPID`); **não** `ART_CPID` |

  O «Name» vem com `.` por defeito; num sub-artigo traz o ID dele (ex. `49187` no
  `BL_3GVT_RP_01`). Na `APAGAR_14` o `RP_04_DIR` tem Posicao `Fração_A` e Piso `Piso 1º`.
- **Como o motor lê os campos do artigo** (código do `IDBCCLG25.dll` desmontado a
  29-10-2026; a imos não documenta isto). Os campos que contêm `HEIGHT`, `WIDTH`, `DEPTH`,
  `CP90NAME`, `CPID`, `INFO1`–`INFO10` (exceto `IDENT_`/`IDBWG_`/`IDBGPL_INFO*`), `ARTCALC1-3`,
  `POSSTR`, `PARTPOSSTR`, `SERIALNO`, `ATTVALUEGROUP` ou `PLANPOSDATA[`, e os que começam por
  `IDBINFO_`, leem a `IDBINFO` do **artigo da peça** (`ARTNR_NR_ID`; com `PLANPOS_POSSTR`,
  `POSNR_NR_ID`). A coluna lida é:
  - `CP90NAME` → `CPID`;
  - `PLANPOS_POSSTR` → `POSSTR`;
  - `IDBINFO_<coluna>` → `<coluna>` (é como faz o Productionmanager da imos: `IDBINFO_BOMFACTOR`,
    `IDBINFO_ID`).

  Por isso o `POSSTR` vem vazio nos sub-artigos.
- **`ART_<campo>` não é a `IDBINFO`:** lê o `CPID` do artigo da peça e procura o `<campo>` no
  artigo do **catálogo** com esse nome. No ensaio de 29-10 (18h26) o `ART_CPID` saiu vazio em
  todas as linhas. Outros prefixos no motor: `PROADMIN_`, `IMORDER`, `IDBVERSO_`, `DRAWREF_`,
  `CMSINCIDENTTEXT_`.
- **Funções, não campos:** `EDGECOUNT` é uma função (`EDGECOUNT[...]`); sem `[...]` dá «O campo
  não existe». A tabela de funções do motor tem também `VALUE_FROM_TABLE`, `ASSEMBLY`
  (`ASSEMBLY[ID;ID;#]`), `ASSEMBLY_DATA`, `PARENTASSEMBLY`, `PARTS_IN_ARTICLE` e
  `ARTICLE_VARIABLE`, sem documentação. Talvez sirvam para ler o artigo **principal** num
  sub-artigo.
- **O «Name» (CPID) nos artigos** (300 obras recentes):
  - 2571 vezes `.`;
  - 1272 igual ao nome do grupo;
  - 1076 o próprio ID;
  - poucas o nome de um artigo do catálogo (`TULHA_600`, `CESTO_SIGE_…`, `TANQUE_COZINHA`).

  Nestes últimos, o `ART_` e o que o iMos faz pelo catálogo dependem do «Name»: escrever lá o
  piso pode estragá-los.
- Funções que o motor aceita (lidas no `IDBCCLG25.dll`): `IFEMPTY`, `IFEQUAL`, `IFNOTBLANK`,
  `IF_GREATER`, `COMPARE`, `REPLACE_EMPTY`, `SPLITLEFT`, `SPLITRIGHT`, `MAKESTRING`, `UPPER`,
  `TEXT[...]`, `TOPARTICLE_NAME`…
- **Condições (`IFEMPTY`, `IFEQUAL`) não servem com um campo simples à cabeça.** O
  `IFEMPTY[x;se_vazio;se_não]` funciona no Productionmanager porque à cabeça está uma função
  (`PXM_PROGRAM_INFO[...]`; peças sem programa → `TEXT[Ignore]`). Na ronda 3 (29-10-2026,
  `APAGAR_14`) `IFEQUAL[ARTNR;TOPARTICLE_NAME[ARTNR_NR_ID];…]`, `IFEMPTY[POSSTR;ARTNR;VENEER_ID]`
  e até `IFEMPTY[POSSTR;TEXT[VAZIO];TEXT[CHEIO]]` devolveram **sempre o valor do primeiro
  campo**. Regras do tipo «se igual, vazio» fazem-se no Excel.
- `VENEER_ID` e `FLITCH_ID` estão vazios nas 139 903 peças das obras > 7000 (serviriam de
  «vazio»; o `TEXT[]` vazio também não funciona).
- **A coluna Artigo mostra a POSIÇÃO, não o nome:** em 450 artigos principais (102 obras,
  ~9 %; quase todas as cozinhas, ex. `1431_02_26_CRW`: posição `001`, nome `MB_01_GVT_PL`) o
  `POSSTR` é um número e o nome (`GROUPNAME`) está noutro sítio. Por isso o CSV leva a coluna
  técnica **ArtigoNome** (`TOPARTICLE_NAME[ARTNR_NR_ID]`) e o Excel compara o SubArtigo com
  ela, não com a coluna Artigo (decisão do Paulo, 29-10-2026).
- Sub-artigos nas obras > 7000: 792 sem posição própria (o caso normal: `VARAO_RP_STD`,
  `GUARNICAO…`, `BL_…`), 257 com posição e o mesmo nome do artigo (artigos compostos, ex.
  `RP_D_15_RC_FRENTE`: ficam vazios) e 162 com posição e nome diferente («Peça de pontos»,
  «Grupo Article Designer», `WC_A_01_MOB1_SUITE_B` dentro de `WC_A_01_MOB1_SUIT`: aparecem,
  porque o nome é diferente).

## Forma da peça: `ISPEC` e recortes interiores (29-10-2026)

Pedido do Paulo: saber no CSV se a peça não é retangular de 4 lados, para o Excel pôr um
aviso nas Notas («forma especial, pode ter CAM»). O campo `ISPEC` (coluna da `IDBGPL`)
vale 0 = retangular de 4 lados, 1 = 4 lados com pelo menos um contorno, 2 = mais de 4 lados,
3 = não é painel; também aparece **4** (30 peças, ex. «Frente da base»), sem descrição da imos.

Nas 160 obras mais recentes (peças cortadas): 30 676 com ISPEC 0, 84 com 1, 348 com 2,
108 com 3, 30 com 4. **Mas o ISPEC não vê os recortes interiores:** uma peça retangular com
um contorno interior (perfil `PTYPE='I'` na `IDBPRF`, ex. `REC_CNT_L_RODAPE_FRENTE`,
`REC_CNT_L_CIMA_TRAS`, `CAVIDADE_POCKET`, `FRESAR_RECORTES_VARADO`) continua com ISPEC 0 —
**382 peças em 48 obras**. Na `APAGAR_14` o Paulo criou as duas variantes: `PECA_L` (L
desenhado com 6 orlas → ISPEC 2) e `RECORTE_L` (retangular com o recorte
`REC_CNT_L_CIMA_TRAS` → ISPEC 0). A V2 leva a coluna **ISPEC**, confirmada no ensaio de
29-10-2026: «Topo» (`PECA_L`) saiu com 2 e «Teto» (`RECORTE_L`) com 0.

No mesmo ensaio foram 3 colunas `TESTE_*` à procura de um campo do motor que apanhasse o
recorte, e nenhum serviu:
- `EDGECOUNT` e `PRFCNT` **não existem** (caixa de erro por peça; ver «Erro no ficheiro de
  configuração» acima);
- `IDBPRF_PRFID` sai vazio.

Para avisar também dos recortes interiores fica o plano B: um princípio «Views» (SQL próprio
sobre a `IDBGPL`/`IDBPRF`, Element Manager) ou o Martelo ler a `IDBPRF` diretamente.

O `ACCUMULATE` não junta peças de formas diferentes numa só linha: nas obras recentes não há
nenhum caso (uma peça com forma especial tem outro princípio de construção, `CPID`).

## O defeito do `ACCUMULATE` antigo

`ACCUMULATE=CPID;MATID;FLENG;FWIDTH;INFO5;POSSTR;NAME1;AUFTRAG` junta peças iguais com o
mesmo `POSSTR`. Como as peças de sub-artigos têm `POSSTR` vazio, **peças iguais de
sub-artigos de RPs diferentes juntam-se numa só linha com o RP da primeira**. O total corta-se
certo, mas a coluna Artigo fica errada. Visto em CSV mais recentes do que a última alteração
da obra: `CRW_2128_2711_01` (gaveteiro dos RP_01/02/03 todo no RP_01), `0792_01_26_LINHAS_DIREITAS`,
`1172_03_26_INNERE` (ZONA 1P), `DATAMOVEL_1674_1809_01`, `CRW_2046_1411_03`. A V2 junta
`ARTNR_NR_ID` à chave.

A correção só pode ser provada numa obra com o mesmo sub-artigo em **dois RPs**; a
`APAGAR_14` tem só um (no `RP_A_01_ESQ`). No ensaio confirmou-se que a chave nova não estraga a
junção normal (110 linhas, iguais ao CSV antigo).

## Falta no Excel (modelo `Lista_Material_IMOS_MARTELO.xltm`)

O CSV da V2 **não pode** ir para o princípio por defeito antes disto, porque a macro
`Import_CSV_Imos_1` (módulo `modImportCSVImos_1`, ainda só dentro do `.xltm`: versioná-lo em
`scripts/vba` antes de lhe mexer) faria isto:

1. `CorrigirColunaRP` e `VerificarECorrigir_Rasgo_Em_Notas` procuram o cabeçalho **«RP»**:
   com «Artigo» aparecem duas mensagens e a correção do Rasgo dos fundos de gaveta não corre.
2. `CopiarLinha_Mapeada` copia **por posição** (coluna n do CSV → coluna n+1 da
   `LISTA_ORDENADA`): o SubArtigo cairia em **Notas**, as Notas em Notas_1 e o Notas_1 em
   Cliente_Final — e as Notas passam para a `LISTAGEM_CUT_RITE` (por nome) e para o Cut-Rite.

O que mudar: procurar «Artigo» (aceitando «RP» nos CSV antigos); copiar por **nome** de
cabeçalho; **deixar o SubArtigo vazio quando é igual ao ArtigoNome** (regra do Paulo); o
ArtigoNome é técnico e não passa para a `LISTA_ORDENADA`; o ISPEC também é técnico: com o ISPEC ≠ 0 (e, com o plano B, com recorte interior) escrever um aviso nas Notas (texto a decidir com o Paulo); na `LISTA_ORDENADA` (linha 3) pôr
«SubArtigo» em R, à direita de «Artigo» (Q), com Notas/Notas_1/Cliente_Final em S/T/U e sem
CNC/ABD/BHT; decidir se o SubArtigo segue para a `LISTAGEM_CUT_RITE`.

Com o `.cfg` V1, os nomes passam a Posicao / Artigo/SubArtigo / Piso, e o Piso traz mais uma
regra. Nas linhas de sub-artigos vem o «Name» do sub-artigo e não o piso: o Excel põe lá o
Piso do artigo principal, procurando-o nas linhas em que Artigo/SubArtigo = ArtigoNome. O `.`
(sem piso) fica vazio.

Nenhuma fórmula do modelo aponta para a `LISTA_ORDENADA`, e a passagem
para a `LISTAGEM_CUT_RITE` já é por nome (`ARTIGO`, `NOTAS`…). Mudar o modelo só afeta as
Listas Material criadas depois.

## Verificar um CSV

A partir da pasta principal do Martelo (para apanhar o `.env`):

    python scripts/imos_cfg/verificar_csv_subartigos.py APAGAR_14

Sem caminho, lê `...\Cutrite_Import_CSV\<obra>_Lista_Corte.csv`. A comparação só é justa se
o CSV for **posterior** à última gravação da obra com a lista de peças.

## XML (pergunta do Paulo, 29-10-2026)

- **Exportar em XML** (como o `Homag_DF_Productionmanager.cfg`): é o mesmo motor e os mesmos
  campos do CSV, só noutro formato (árvore em vez de tabela). Não traz dados novos — o que o
  XML tem pode ir para uma coluna do CSV, como se fez com o SubArtigo. Para a Lista Material
  não compensa trocar.
- **Importar encomendas em XML** («Order XML» / Sales Import Manager, SIM): cria a encomenda
  no iMos e constrói sozinho cada linha a partir de artigos que **já existem** no Element
  Manager, com as variáveis (medidas, materiais). É módulo à parte (não vem na instalação
  base); a `imos_LE` não tem tabelas do SIM em uso. O Paulo vai pedir explicações e preço à
  Enersale (29-10-2026): pode interessar para alguns projetos.

## Alternativa em ensaio: a lista lida pelo Martelo da base (29-10-2026)

O `.cfg` não consegue dar o Piso do artigo principal às peças dos sub-artigos. Além disso, o
`ACCUMULATE` dele junta peças com notas diferentes. Por isso, a pedido do Paulo, o Martelo
passou a fazer a mesma lista **em paralelo**, a ler a base: `app/services/lista_corte_imos_base_service.py`
(regras no cabeçalho). Na Produção é a opção **Funções** → «Lista Material da base iMos
(ensaio)…». Escreve o CSV e um relatório da comparação com o CSV do `.cfg` na subpasta
`Ensaio_Lista_Base_iMos` da obra e, se o Paulo quiser, cria lá um Excel de ensaio
`Lista_Material_<obra>_BASE.xlsm`. A importação para esse Excel é feita pela macro
`Import_Base_Imos_1` (`scripts/vba/modImportCSVImos_1.bas`). Guião de teste no doc 17,
«Lista Material: lista de peças lida da base do iMos».
