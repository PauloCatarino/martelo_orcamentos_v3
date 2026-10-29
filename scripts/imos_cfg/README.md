# Transferência de dados do iMos (`.cfg` da lista de corte)

O CSV que dá origem à Lista Material (`I:\Cutrite\Work\Cutrite_Import_CSV\<obra>_Lista_Corte.csv`)
sai do iMos por um princípio de **Processar transferência de dados** (Element Manager), que
corre um ficheiro `.cfg`. Esta pasta guarda, com histórico, os `.cfg` que fazemos e um
verificador.

| Ficheiro | Faz |
|---|---|
| `EXPORT_CSV_CUT_RITE_LE_V2.cfg` | Cópia do `EXPORT_CSV_CUT_RITE_LE.cfg` em uso com a coluna nova **Sub_Artigo**, sem CNC/ABD/BHT e com o `ACCUMULATE` corrigido. **Ronda 1 = ENSAIO**: tem 4 colunas `DIAG_*` no fim e escreve na subpasta `TESTE_SUBARTIGOS`. |
| `verificar_csv_subartigos.py` | Lê um CSV exportado e compara-o com a base do iMos (só SELECT): RP, Sub_Artigo e quantidades por peça. Também confere CSV antigos, só pelo RP. |

## Como o iMos guarda e usa o `.cfg` (descoberto a 29-10-2026)

- O `.cfg` que conta é o que está **dentro da base** (`imos_LE`), não o da pasta
  `\\SERVER_LE\Homag_iX\CFG`. O princípio (`PDTLINK`) guarda só o nome do ficheiro
  (`CONFIGFILE`); o conteúdo está em `BINDATA` (`INTERNTYPE='CFG'`, `NAME` = nome do
  princípio). Mudar o ficheiro da pasta não faz nada: é preciso **importá-lo** no princípio
  (botão ↓ em «Default Settings») e Guardar.
- Ao correr, o iX CAD escreve o `.cfg` em `%APPDATA%\imos AG\iX CAD 2025\TEMP\<princípio>_<n>.cfg`
  e o motor é o `IDBCCLG25.dll` (a janela das mensagens chama-se «IDBCCLG25»).
- Com «Configuração do caminho = Standard», o **Output path** do princípio substitui o
  `LOCATION` do `.cfg`, e o `SUBDIRNAME` cria uma subpasta lá dentro.
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
- `ARTNR` → nome do artigo onde a peça está (o mais próximo). `ARTNR_NR_ID` → o seu ID.
- `TOPARTICLE_NAME[ARTNR_NR_ID]` → nome do artigo de topo (dica da imos, KB #00867).
- Funções que o motor aceita (lidas no `IDBCCLG25.dll`): `IFEMPTY`, `IFEQUAL`, `IFNOTBLANK`,
  `IF_GREATER`, `COMPARE`, `REPLACE_EMPTY`, `SPLITLEFT`, `SPLITRIGHT`, `MAKESTRING`, `UPPER`,
  `TEXT[...]`, `TOPARTICLE_NAME`… Sintaxe confirmada só para `IFEMPTY[valor;se_vazio;se_não]`
  (está no `Homag_DF_Productionmanager.cfg`).

## O defeito do `ACCUMULATE` antigo

`ACCUMULATE=CPID;MATID;FLENG;FWIDTH;INFO5;POSSTR;NAME1;AUFTRAG` junta peças iguais com o
mesmo `POSSTR`. Como as peças de sub-artigos têm `POSSTR` vazio, **peças iguais de
sub-artigos de RPs diferentes juntam-se numa só linha com o RP da primeira**. O total corta-se
certo, mas a coluna Artigo fica errada. Visto em CSV mais recentes do que a última alteração
da obra: `CRW_2128_2711_01` (gaveteiro dos RP_01/02/03 todo no RP_01), `0792_01_26_LINHAS_DIREITAS`,
`1172_03_26_INNERE` (ZONA 1P), `DATAMOVEL_1674_1809_01`, `CRW_2046_1411_03`. A V2 junta
`ARTNR_NR_ID` à chave.

## Verificar um CSV

A partir da pasta principal do Martelo (para apanhar o `.env`):

    python scripts/imos_cfg/verificar_csv_subartigos.py APAGAR_14
    python scripts/imos_cfg/verificar_csv_subartigos.py CRW_2128_2711_01

Sem caminho, lê `...\Cutrite_Import_CSV\TESTE_SUBARTIGOS\<obra>_Lista_Corte.csv`. A
comparação só é justa se o CSV for **posterior** à última gravação da obra com a lista de
peças.
