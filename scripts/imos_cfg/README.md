# Transferência de dados do iMos (`.cfg` da lista de corte)

O CSV que dá origem à Lista Material (`I:\Cutrite\Work\Cutrite_Import_CSV\<obra>_Lista_Corte.csv`)
sai do iMos por um princípio de **Processar transferência de dados** (Element Manager), que
corre um ficheiro `.cfg`. Esta pasta guarda, com histórico, os `.cfg` que fazemos e um
verificador.

| Ficheiro | Faz |
|---|---|
| `EXPORT_CSV_CUT_RITE_LE_V2.cfg` | Cópia do `EXPORT_CSV_CUT_RITE_LE.cfg` em uso com as colunas pedidas pelo Paulo (29-10-2026): `… Enc.; Cliente; Artigo; SubArtigo; Notas; Notas_1; Cliente_Final` — **RP** passa a **Artigo**; **SubArtigo** à direita, só com o nome do sub-artigo quando é diferente do nome do artigo principal (vazio no resto); sem CNC/ABD/BHT — e com o `ACCUMULATE` corrigido. **Ronda 3 (ensaio): 3 colunas `TESTE_*` no fim** para confirmar o `IFEQUAL`. Só para obras de teste até o modelo da Lista Material ser adaptado (ver «Falta no Excel»). |
| `gerar_cfg_v2.py` | Gera o `EXPORT_CSV_CUT_RITE_LE_V2.cfg` a partir do `.cfg` em uso (latin1 + CRLF, só troca as linhas ativas; as antigas ficam comentadas). A fórmula do SubArtigo e as colunas de ensaio (`TESTES`) estão no topo. |
| `verificar_csv_subartigos.py` | Lê um CSV exportado e compara-o com a base do iMos (só SELECT): Artigo, SubArtigo e quantidades por peça. Também confere CSV antigos, só pelo artigo. |

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
- Funções que o motor aceita (lidas no `IDBCCLG25.dll`): `IFEMPTY`, `IFEQUAL`, `IFNOTBLANK`,
  `IF_GREATER`, `COMPARE`, `REPLACE_EMPTY`, `SPLITLEFT`, `SPLITRIGHT`, `MAKESTRING`, `UPPER`,
  `TEXT[...]`, `TOPARTICLE_NAME`…
- `IFEMPTY[x;se_vazio;se_não]`: confirmado pelo XML do Productionmanager (peças sem programa
  CNC → `TEXT[Ignore]`). Mas **`IFEMPTY[POSSTR;ARTNR;TEXT[]]` não funcionou** (devolveu o próprio
  `POSSTR`): o mais provável é o `TEXT[]` vazio. Para «vazio» usa-se um campo que está sempre
  vazio: **`VENEER_ID`** (vazio nas 139 903 peças das obras > 7000; o `FLITCH_ID` também).
- `IFEQUAL[a;b;se_igual;se_diferente]`: sintaxe **por confirmar** na ronda 3 (coluna
  `TESTE_IFEQUAL_TXT` deve dar `IGUAL` nas peças fora de sub-artigos).
- **A coluna Artigo mostra a POSIÇÃO, não o nome:** em 450 artigos principais (102 obras,
  ~9 %) o `POSSTR` é um número (`1`, `001`) e o nome (`GROUPNAME`) é `RP_A_01a`. Por isso o
  SubArtigo compara **nome com nome** (`ARTNR` contra `TOPARTICLE_NAME[ARTNR_NR_ID]`), não com a
  coluna Artigo.
- Sub-artigos nas obras > 7000: 792 sem posição própria (o caso normal: `VARAO_RP_STD`,
  `GUARNICAO…`, `BL_…`), 257 com posição e o mesmo nome do artigo (artigos compostos, ex.
  `RP_D_15_RC_FRENTE`: ficam vazios) e 162 com posição e nome diferente («Peça de pontos»,
  «Grupo Article Designer», `WC_A_01_MOB1_SUITE_B` dentro de `WC_A_01_MOB1_SUIT`: aparecem). A
  regra pelo `POSSTR` vazio esqueceria estes últimos; a do nome não.

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
cabeçalho; na `LISTA_ORDENADA` (linha 3) pôr «SubArtigo» em R, à direita de «Artigo» (Q), com
Notas/Notas_1/Cliente_Final em S/T/U e sem CNC/ABD/BHT; decidir se o SubArtigo segue para a
`LISTAGEM_CUT_RITE`. Nenhuma fórmula do modelo aponta para a `LISTA_ORDENADA`, e a passagem
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
