# 30 - Plano de melhoria da tabela de materias-primas (Excel -> Martelo V3)

> **Estado (2026-08-24): F0 e F1 e F2 FEITAS. F3 por fazer. Ver capitulo 8.**
> Documento escrito a partir do ficheiro real
> `\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\Base_Dados_Orcamento\TAB_MATERIAS_PRIMAS.xlsm`
> e do codigo de importacao do V3. Os capitulos 1 a 7 sao o plano tal como foi
> aprovado; o capitulo 8 regista o que ficou mesmo feito e o que falta.

---

## 1. Objetivo

O Excel `TAB_MATERIAS_PRIMAS.xlsm` e, hoje, a **porta de entrada** de todas as
materias-primas do Martelo V3: placas, orlas, ferragens e acabamentos. Tudo o que
esta errado nesse ficheiro entra silenciosamente no custeio dos orcamentos.

Este plano responde a duas perguntas:

1. como reduzir os erros **na origem** (no proprio Excel), e
2. que **tecnologia** aplicar para o V3 deixar de aceitar dados errados sem avisar.

O plano e faseado de proposito: cada fase entrega valor sozinha e pode parar ai.

---

## 2. Como funciona o fluxo hoje

| Peca | Onde esta | O que faz |
| --- | --- | --- |
| Ficheiro Excel | servidor, pasta `Base_Dados_Orcamento` | fonte unica; folha `Tab_Materias_Primas`, cabecalho na linha 5, tabela estruturada, **com macros (VBA)** |
| Pasta configurada | `system_settings.pasta_materias_primas` | diz ao V3 onde procurar o ficheiro |
| Leitura | `scripts/import_materias_primas_excel.py` | le com openpyxl, deteta o cabecalho, mapeia colunas por alias, converte numeros |
| Gravacao | `app/services/def_materia_prima_service.py` | *upsert* por `Ref_LE` (cria ou atualiza) |
| Tabela | `def_materias_primas` | 17 campos importados |
| Ecra | `app/ui/pages/materias_primas_page.py` | lista + pesquisa + botoes "Importar/Atualizar Excel" e "Abrir Excel" (so leitura, nao edita) |

Pontos importantes do funcionamento atual:

- a chave de sincronizacao e a `Ref_LE`; linhas **sem** `Ref_LE` sao ignoradas em silencio;
- `PLIQ` no Excel e uma **formula**: `PRECO_TABELA x (1 - DESC2) x (1 + MRG)`;
- o V3 **nunca** desativa um material que desapareceu do Excel;
- os precos **nunca** se atualizam sozinhos dentro de um orcamento ja feito
  (comportamento intencional, herdado da sincronizacao de precos dos ValueSets);
- so 17 das 29 colunas do Excel sao aproveitadas.

---

## 3. Diagnostico com numeros (24-08-2026)

### 3.1 Estrutura

| Indicador | Valor |
| --- | --- |
| Linhas de dados | **337** (a analise da Fase 6, doc 06, tinha 290) |
| Referencias | PLC 120 - FER 189 - ACB 16 - ORL 7 |
| Colunas | 29 (o V3 le 17) |
| Listas de validacao (dropdowns) | **uma so**: FAMILIA, em `O6:O342` |
| Proteccao da folha | nao |
| Macros | sim, `vbaProject.bin` com 23 KB (conteudo comprimido, **por auditar**) |
| Paineis congelados | na linha **249** (o cabecalho da linha 5 nao fica fixo) |
| Formato da data | `mm-dd-yy` (formato americano) |

### 3.2 Problemas encontrados

| # | Problema | Impacto | Quantidade |
| --- | --- | --- | --- |
| P1 | `PLIQ` a zero sem se saber se e de proposito | material entra no custeio a **0,00 EUR** | 43 linhas: 31 sao "LIVRE" (intencional) + **7 esquecimentos** + 5 linhas fantasma |
| P2 | Linhas sem `Ref_LE` ignoradas em silencio | ninguem sabe que ficaram de fora | 5 (linhas 338-342, so com a formula do PLIQ) |
| P3 | `TIPO` sem lista de validacao | 20 valores escritos a mao, impossivel agrupar | 21 linhas com TIPO vazio (7 ORLA + 14 PLACAS) |
| P4 | Espessura da descricao != `ESP_MP` | custeio e plano de corte errados | 2 (PLC0023, PLC0116) |
| P5 | Precos com mais de 12 meses | orcamentos com precos de 2025 | **95** (77 ferragens, 18 placas); mais antigo 23-07-2025 |
| P6 | `DATA_ULTIMO_PRECO` nao e importada | o V3 nao consegue avisar do P5 | 332 linhas preenchidas, todas perdidas |
| P7 | Colunas preenchidas que se perdem | informacao util fica so no Excel | `STOCK` 321, `NOME_FABRICANTE` 261, `COR` 149, `REF_PHC` 72 |
| P8 | Colunas mortas | ruido para quem preenche | `APLICACAO` 0/337, `NOTAS_3` 0/337, `NOTAS_4` 0/337, `COR_REF_MATERIAL` 1/337 |
| P9 | Material apagado do Excel continua ativo no V3 | aparece nas escolhas para sempre | por natureza, nao contavel |
| P10 | Texto sujo nas descricoes | estraga pesquisas e listagens | 151 com espacos duplos, 41 com espacos nas pontas |
| P11 | Ambiguidade fraccao vs percentagem | ver 3.3 | risco latente |

### 3.3 O caso das percentagens (P11) - detalhe tecnico

No Excel, `MRG_(+)`, `DESC2_(-)` e `DESP` estao formatadas como **percentagem**
(`0%`): o valor guardado e `0,2` e o utilizador ve `20%`.

O V3 guarda o numero cru e adivinha depois, em
`app/domain/numeros.py::normalize_percentagem_humana`: "valores entre -1 e 1 sao
fraccoes, o resto ja e percentagem".

A regra funciona para tudo o que la esta hoje, **mas parte** no dia em que
alguem escrever uma margem de `100%` (guardada como `1`), que passaria a ser
lida como **1%**. A correccao certa e deterministica: ler o *formato* da celula
(`cell.number_format`) e converter so quando a coluna esta mesmo formatada como
percentagem, em vez de adivinhar pelo valor.

### 3.4 O que ja esta bem (nao mexer)

- todas as referencias de orla (`CORESP_ORLA_0_4` / `CORESP_ORLA_1_0`) apontam
  para `Ref_LE` que existem - **zero orfas**;
- nao ha `Ref_LE` duplicadas;
- nenhum numero esta guardado como texto;
- a leitura do cabecalho na linha 5 e a conversao de numeros ja sao robustas
  (`detect_header_row`, `to_decimal`, com 22 testes em
  `tests/test_import_materias_primas_excel.py`).

---

## 4. Riscos por ordem de gravidade

1. **Custo zero silencioso (P1/P2)** - ja aconteceu: PLC0009 e PLC0011 aparecem
   a 0,00 EUR no ecra de Materias-Primas. Um orcamento com estes materiais sai
   por baixo do custo e ninguem e avisado.
2. **Precos velhos (P5/P6)** - 95 materiais com preco de ha mais de um ano.
3. **Dados errados que passam a verdade (P4)** - espessura trocada propaga-se ao
   custeio, ao plano de corte e a lista de material do IMOS.
4. **Catalogo que so cresce (P9)** - materiais eliminados continuam a aparecer.
5. **Classificacao inconsistente (P3)** - impede agrupamentos e relatorios fiaveis.

---

## 5. Plano faseado

Regra geral: **F1 e F2 podem ser feitas em paralelo** (uma e no Excel, outra e no
V3). F3 depende de F2. F4 e uma decisao estrategica.

### F0 - Analise (esta fase)

- [x] leitura do ficheiro real do servidor (em copia);
- [x] contagem e listagem completa dos problemas (anexos A a F);
- [x] mapa do codigo tocado por cada fase seguinte;
- [ ] **auditar as macros existentes** - 23 KB de VBA que nao foi possivel ler
      (esta comprimido dentro do ficheiro). E preciso abrir o Excel,
      `Alt+F11`, e ver o que fazem antes de proteger a folha ou mexer em colunas,
      sob pena de partir alguma macro. **Isto tem de acontecer antes de F1.**

### F1 - Endurecer o Excel (sem tocar no V3)

Trabalho feito **no ficheiro**, com copia de seguranca datada antes de comecar
(mesmo criterio ja usado no `Lista_Material_IMOS_MARTELO.xltm`).

| Passo | O que muda | Porque |
| --- | --- | --- |
| F1.1 | Folha oculta `LISTAS` com os valores validos de TIPO, FAMILIA, UND, COR e das ORL existentes | fonte unica das listas |
| F1.2 | Validacao de dados em TIPO, UND, COR, `CORESP_ORLA_0_4`, `CORESP_ORLA_1_0` (a de FAMILIA ja existe) | acaba o texto livre (P3) |
| F1.3 | Nova coluna **`TIPO_PRECO`** com `TABELA` / `MANUAL_NA_OBRA` | distingue "preco livre" de "preco esquecido" (P1) |
| F1.4 | Nova coluna **`ATIVO`** com `SIM` / `NAO` | deixa de ser preciso apagar linhas (P9) |
| F1.5 | Formatacao condicional: vermelho quando falta `Ref_LE`, quando `PLIQ`=0 com `TIPO_PRECO`=TABELA, ou quando a espessura da descricao nao bate com `ESP_MP`; amarelo quando o preco tem mais de 12 meses | o erro ve-se enquanto se escreve (P1, P4, P5) |
| F1.6 | Proteger a folha deixando editaveis so as colunas de dados (o `PLIQ` fica bloqueado) | ninguem esmaga a formula |
| F1.7 | Congelar paineis na linha 6 e passar `DATA_ULTIMO_PRECO` para `dd-mm-aaaa` | usabilidade e leitura correcta das datas |
| F1.8 | Apagar as colunas mortas `APLICACAO`, `NOTAS_3`, `NOTAS_4` (e decidir sobre `COR_REF_MATERIAL`) | menos ruido (P8) |
| F1.9 | Limpar os espacos duplos e as pontas nas descricoes | (P10) |

**Risco:** o ficheiro esta num servidor partilhado e tem macros. Mitigacao:
copia de seguranca, trabalhar fora do horario dos colegas, e testar as macros
depois de proteger a folha.

**Nao ha alteracoes de codigo nesta fase**, mas F1.3/F1.4/F1.8 mudam colunas, por
isso o mapeamento do importador tem de aceitar as colunas novas **antes** de F1
ir para o servidor - ou o importador deixa de encontrar o que espera. Ver 5.6.

### F2 - "Verificar Excel": o V3 passa a avisar antes de importar

Novo botao **"Verificar Excel"** ao lado do "Importar/Atualizar Excel", que corre
a leitura em modo simulacao (o `--dry-run` ja existe no script) e mostra um
**relatorio linha a linha**, no mesmo estilo do dialogo
`app/ui/dialogs/atualizar_precos_valueset_dialog.py`, que ja faz exactamente isto
para os precos dos ValueSets (tabela + selecao por caixa de visto).

O relatorio classifica cada aviso com a mesma linguagem do supervisor de custeio
(**CRITICO** / **AVISO**), para nao haver duas maneiras de dizer a mesma coisa:

| Verificacao | Severidade |
| --- | --- |
| linha com dados mas sem `Ref_LE` (vai ser ignorada) | CRITICO |
| `PLIQ` = 0 e `TIPO_PRECO` != `MANUAL_NA_OBRA` | CRITICO |
| orla que aponta para `Ref_LE` inexistente | CRITICO |
| espessura escrita na descricao != `ESP_MP` (so PLACAS) | AVISO |
| `DATA_ULTIMO_PRECO` com mais de 12 meses | AVISO |
| `TIPO`, `UND` ou `FAMILIA` fora da lista de valores | AVISO |
| material que existe no V3 e desapareceu do Excel | AVISO, com proposta de desativar |
| preco que mudou desde a ultima importacao | informativo, com valor antigo -> novo |

Ficheiros tocados (estimativa):

- `scripts/import_materias_primas_excel.py` - separar "ler e validar" de "gravar";
  as validacoes ficam em funcoes puras, testaveis sem Excel e sem base de dados
  (o ficheiro ja esta escrito com esse cuidado);
- `app/domain/materias_primas_validacao.py` **(novo)** - regras puras;
- `app/ui/dialogs/verificar_excel_materias_primas_dialog.py` **(novo)**;
- `app/ui/pages/materias_primas_page.py` - botao novo + ligacao;
- `tests/test_materias_primas_validacao.py` **(novo)** e reforco de
  `tests/test_import_materias_primas_excel.py`.

**Sem migracao de base de dados.** Nesta fase o V3 so le e avisa.

### F3 - Aproveitar o que hoje se perde + historico de precos

| Passo | O que muda |
| --- | --- |
| F3.1 | Importar tambem `DATA_ULTIMO_PRECO`, `STOCK`, `COR`, `NOME_FABRICANTE`, `REF_PHC` (colunas novas em `def_materias_primas`) |
| F3.2 | Importar `TIPO_PRECO` e `ATIVO` (criados em F1) - o `ATIVO` do Excel passa a mandar no `ativo` do V3, e o que desaparece do Excel e desativado em vez de ficar |
| F3.3 | Tabela nova `def_materias_primas_precos_historico` (ref, preco tabela, preco liquido, data, origem) escrita a cada importacao que mude o preco |
| F3.4 | Ler as percentagens pelo **formato da celula** em vez de adivinhar (P11) |
| F3.5 | Colunas "Ultimo preco" e "Stock" no ecra Materias-Primas, com o amarelo dos precos velhos |

Precisa de **migracao** (proximo numero livre: 95, a seguir a
`20260824_94_add_predefinido_lm_pdf_presets.py`) e de correr tambem na **beta**.

O historico e o que abre a porta a perguntas do genero "quanto subiu o
aglomerado este ano" e a ligacao futura as tabelas dos fornecedores que ja estao
na pasta `TABELAS_MAT_EGGER_SONAE`.

### F4 - Inverter a direccao (decisao estrategica, nao para agora)

O registo passa a fazer-se **dentro do V3** (a pagina ja existe, so esta em modo
leitura) e o Excel fica como **exportacao** para consulta e impressao. Ganha-se
validacao a serio, registo de quem alterou o que, e acaba a dependencia de um
ficheiro que qualquer pessoa pode abrir e estragar. A importacao de Excel
mantem-se, mas so para **carregamentos em massa** (por exemplo tabelas novas da
Egger/Sonae).

Fica aqui registado como destino; **nao faz parte desta ronda**.

### 5.6 Ordem correcta de execucao

```
F0 (auditar macros)
   -> F2 no V3 (ler e aceitar as colunas novas, ainda opcionais)
      -> F1 no Excel (criar TIPO_PRECO, ATIVO, listas, semaforos)
         -> correr "Verificar Excel" e limpar os erros dos anexos A a D
            -> F3 (migracao + historico)
```

O importador tem de saber lidar com as colunas novas **antes** de elas
existirem no servidor. As colunas novas entram como opcionais no mapeamento
(`COLUMN_ALIASES`), por isso o ficheiro antigo continua a funcionar durante a
transicao.

---

## 6. Guiao de teste (para quando F2 estiver feita)

1. Abrir o Martelo V3 (base **martelo_v3_dev**), entrar como `paulo`.
2. Menu lateral: **Orcamentos > Materias-Primas**.
3. Clicar em **"Verificar Excel"**.
   - Esperado: abre um dialogo "Verificar Excel de materias-primas" com uma
     tabela de avisos, sem gravar nada na base de dados.
4. Confirmar que aparecem, no minimo:
   - 5 avisos CRITICOS de "linha sem Ref LE" (linhas 338 a 342);
   - 7 avisos CRITICOS de "preco a zero": PLC0009, PLC0011, FER0157, FER0137,
     FER0138, FER0139, FER0140;
   - 2 avisos de espessura: PLC0023 e PLC0116;
   - 95 avisos de "preco com mais de 12 meses".
5. Fechar o dialogo e clicar em **"Atualizar Pagina"**.
   - Esperado: a lista fica igual ao que estava - a verificacao **nao** grava.
6. Clicar em **"Importar/Atualizar Excel"** e confirmar a mensagem de resumo
   (criadas / atualizadas / erros) por baixo dos botoes.
7. Pesquisar `PLC0009`.
   - Esperado: continua a aparecer com 0,00 EUR (a correccao e no Excel, F1), mas
     agora ja foi avisado antes de importar.

---

## 7. Decisoes que precisam de resposta antes de avancar

1. **F1 avanca?** Mexer no ficheiro do servidor (colunas novas, proteccao da
   folha) obriga a avisar os colegas e a auditar as macros primeiro.
2. **Os 7 precos em falta** (anexo A) sao esquecimento ou sao materiais
   descontinuados? Se forem descontinuados, o caminho e `ATIVO = NAO`.
3. **PLC0023 e PLC0116**: qual e a espessura correcta, a da descricao ou a de
   `ESP_MP`?
4. **`TIPO` das 7 orlas e das 14 "PLACAS LIVRES"**: fica vazio de proposito ou
   passam a ter valor proprio (`ORLA`, `PLACA_LIVRE`)?
5. **Colunas mortas**: pode-se apagar `APLICACAO`, `NOTAS_3`, `NOTAS_4`? E
   `COR_REF_MATERIAL` (1 preenchimento em 337)?
6. **Precos velhos**: 12 meses e o limite certo para o aviso amarelo?
7. **F4** entra no horizonte ou o Excel fica mesmo como dono dos dados?

---

## Anexo A - Precos em falta (PLIQ a zero sem ser "LIVRE")

| Linha | Ref LE | Descricao | Familia |
| --- | --- | --- | --- |
| 14 | PLC0009 | AGL FOL ALD. FAIA BRANCA FIG. 19MM | PLACAS |
| 16 | PLC0011 | AGL FOL ALD. FREIXO FIG. 19MM | PLACAS |
| 139 | FER0157 | CESTO COZ 002G MOD 200 | FERRAGENS |
| 266 | FER0137 | GUARNICAO CONTRAPLACADO REVESTIDA CPL (3050 X 70 X 12/25) | FERRAGENS |
| 267 | FER0138 | GUARNICAO CONTRAPLACADO REVESTIDA CPL (2500 X 70 X 15/25) | FERRAGENS |
| 268 | FER0139 | GUARNICAO CONTRAPLACADO REVESTIDA CPL (2500 X 70 X 12/25) | FERRAGENS |
| 269 | FER0140 | GUARNICAO CONTRAPLACADO REVESTIDA CPL (2200 X 70 X 12/25) | FERRAGENS |

As restantes 31 linhas a zero sao intencionais ("FERRAGEM LIVRE", "LACAGEM
LIVRE", "PLACAS LIVRES", "ORLA LIVRE") e sao exactamente o motivo para criar a
coluna `TIPO_PRECO`.

## Anexo B - Linhas sem Ref_LE

Linhas **338, 339, 340, 341 e 342**: estao vazias, so tem a formula do `PLIQ`
arrastada para baixo. A tabela do Excel vai ate a linha 342 mas os dados acabam
na 337.

## Anexo C - Linhas com TIPO vazio (21)

- ORLA (7): ORL0001, ORL0002, ORL0003, ORL0004, ORL0005, ORL0006, ORL0007
- PLACAS (14): PLC0095 a PLC0107 (as "PLACAS LIVRES") e PLC0120 (SUPLEMENTO)

## Anexo D - Espessura da descricao != ESP_MP

| Linha | Ref LE | Descricao | ESP_MP |
| --- | --- | --- | --- |
| 93 | PLC0023 | AGL MR MLM BRANCO B3768/SC 16MM | 12 |
| 335 | PLC0116 | AGL MLM SONAE PROMO 2 10MM | 19 |

## Anexo E - Precos com mais de 12 meses

95 materiais (77 ferragens, 18 placas). O mais antigo e de **23-07-2025**.
Distribuicao das datas de todo o ficheiro:

| Mes | Linhas |
| --- | --- |
| 2025-07 | 89 |
| 2025-08 | 6 |
| 2026-01 | 6 |
| 2026-03 | 30 |
| 2026-04 | 133 |
| 2026-05 | 10 |
| 2026-07 | 4 |
| 2026-08 | 54 |
| (vazio) | 5 |

## Anexo F - Colunas do Excel: preenchimento e destino

| Coluna | Preenchida | Importada hoje | Proposta |
| --- | --- | --- | --- |
| ID_MP | 337/337 | nao | manter so no Excel |
| REF_PHC | 72/337 | nao | importar (F3.1) |
| REF_FORNECEDOR | 166/337 | sim | - |
| Ref_LE | 332/337 | sim (chave) | - |
| DESCRICAO_do_PHC | 5/337 | sim (alternativa) | - |
| DESCRICAO_no_ORCAMENTO | 332/337 | sim | limpar espacos (F1.9) |
| PRECO_TABELA | 298/337 | sim | - |
| MRG_(+) | 153/337 | sim | ler pelo formato (F3.4) |
| DESC2_(-) | 139/337 | sim | ler pelo formato (F3.4) |
| PLIQ | 337/337 | sim | bloquear a formula (F1.6) |
| UND | 332/337 | sim | validacao (F1.2) |
| DESP | 332/337 | sim | ler pelo formato (F3.4) |
| ESP_MP | 302/337 | sim | semaforo vs descricao (F1.5) |
| TIPO | 311/337 | sim | validacao (F1.2) |
| FAMILIA | 332/337 | sim | ja tem validacao |
| COR | 149/337 | nao | importar (F3.1) |
| CORESP_ORLA_0_4 | 125/337 | sim | validacao por lista (F1.2) |
| CORESP_ORLA_1_0 | 125/337 | sim | validacao por lista (F1.2) |
| COR_REF_MATERIAL | 1/337 | nao | **apagar?** (decisao 5) |
| COMP_MP | 235/337 | sim | - |
| LARG_MP | 193/337 | sim | - |
| NOME_FORNECEDOR | 277/337 | sim | - |
| NOME_FABRICANTE | 261/337 | nao | importar (F3.1) |
| DATA_ULTIMO_PRECO | 332/337 | nao | importar (F3.1) + formato dd-mm-aaaa |
| APLICACAO | 0/337 | nao | **apagar** (F1.8) |
| STOCK | 321/337 | nao | importar (F3.1) |
| NOTAS_2 | 5/337 | nao | manter |
| NOTAS_3 | 0/337 | nao | **apagar** (F1.8) |
| NOTAS_4 | 0/337 | nao | **apagar** (F1.8) |
| **TIPO_PRECO** (nova) | - | - | criar (F1.3) + importar (F3.2) |
| **ATIVO** (nova) | - | - | criar (F1.4) + importar (F3.2) |

---

## 8. O que foi feito (2026-08-24)

Decisoes do Paulo que mudaram o plano original:

- a `Ref_LE` **nunca** pode repetir-se (e usada para identificar o material em
  todo o lado nos orcamentos) -> passou a haver uma verificacao dedicada;
- as linhas a zero ("PLACAS LIVRES", "FERRAGEM LIVRE", "LACAGEM LIVRE", "ORLA
  LIVRE") **nao sao erro**: sao materiais de preco e descricao editaveis dentro
  de cada orcamento, para quando e' preciso uma ferragem que nao vale a pena
  acrescentar ao catalogo. Foi por isso que nasceu a coluna `TIPO_PRECO`;
- as colunas mortas (`APLICACAO`, `NOTAS_3`, `NOTAS_4`, `COR_REF_MATERIAL`)
  **ficam** por agora;
- as espessuras de PLC0023 e PLC0116 ja foram corrigidas pelo Paulo no Excel;
- o V3 ainda nao esta instalado em nenhum posto, por isso foi possivel mexer no
  Excel do servidor sem janela de manutencao.

### 8.1 F1 - Excel (feito, ja no servidor)

Salvaguarda criada antes de tudo:
`TAB_MATERIAS_PRIMAS_backup_20260824_230418.xlsm`, na mesma pasta.

| Passo | Estado | Resultado |
| --- | --- | --- |
| F1.1 folha `LISTAS` oculta | feito | 19 tipos, 26 cores, 7 orlas, unidades, familias, tipos de preco e ativo |
| F1.2 validacoes | feito | TIPO, COR, UND, FAMILIA, TIPO_PRECO, ATIVO, `CORESP_ORLA_0_4`, `CORESP_ORLA_1_0` |
| F1.3 coluna `TIPO_PRECO` | feito | 301 `TABELA` + 31 `LIVRE`, a seguir ao PLIQ |
| F1.4 coluna `ATIVO` | feito | `SIM` em todas as 332 linhas |
| F1.5 semaforos | feito | 7 celulas de PLIQ a vermelho e 70 datas a ambar (confirmado no proprio Excel) |
| F1.6 proteger a folha | **NAO feito** | ver 8.4 |
| F1.7 paineis e formato de data | feito | congelado na linha 5; `DATA_ULTIMO_PRECO` em `dd-mm-aaaa` |
| F1.8 apagar colunas mortas | **nao feito** | decisao do Paulo: ficam |
| F1.9 limpar espacos | **nao feito** | passa para F3, junto com a limpeza de texto na importacao |

Tambem foram apagadas as 5 linhas fantasma (338-342): a tabela era `A5:AC342` e
passou a `A5:AE337`, com 332 linhas de dados e 31 colunas.

Duas armadilhas encontradas pelo caminho, registadas para nao se repetirem:

1. **As formulas passadas por COM vao na lingua do Excel instalado.** Este Excel
   e portugues: as regras tem de ir com `;` e com os nomes PT (`E`, `HOJE`). Com
   `AND(...)` e virgulas, o Excel aceita mas grava `_xludf.AND(...)` — uma
   "funcao desconhecida" — e a regra **nunca pinta nada**, sem dar erro nenhum.
   Dentro do ficheiro fica na forma inglesa, por isso funciona em qualquer PC.
2. **O openpyxl nao le validacoes que apontem para outra folha** (sao guardadas
   numa extensao que ele nao suporta) e **apaga-as se gravar o ficheiro**. O V3
   so le o Excel, nunca o grava, por isso nao ha problema — mas nenhum script
   pode passar a gravar este ficheiro com openpyxl.

### 8.2 F2 - Verificacao no V3 (feito)

- `app/domain/materias_primas_validacao.py` (novo): regras puras, sem Excel, sem
  base de dados e sem Qt;
- `scripts/import_materias_primas_excel.py`: colunas novas **opcionais**
  (`TIPO_PRECO`, `ATIVO`, `DATA_ULTIMO_PRECO`), leitura de datas e de SIM/NAO,
  numeracao das linhas do Excel e `analisar_materias_primas()`;
- o `ATIVO` do Excel passa a mandar no `ativo` do V3; sem essa coluna, fica tudo
  como estava (nenhuma copia antiga do ficheiro reativa o que foi desativado);
- `app/ui/dialogs/verificar_excel_materias_primas_dialog.py` (novo): relatorio
  com filtros por gravidade, cores da app e botao "Copiar lista";
- `app/ui/pages/materias_primas_page.py`: botao **"Verificar Excel"**; alem
  disso, o **"Importar/Atualizar Excel" passa a avisar** quando ha criticos,
  dando a escolher entre ver a lista, importar mesmo assim ou cancelar;
- testes: 31 novos (2 ficheiros novos + reforco do teste da pagina); suite
  completa a **3691 testes**, todos a passar.

### 8.3 Resultado medido

| | Antes | Depois |
| --- | --- | --- |
| Linhas | 337 (5 fantasma) | 332 |
| Criticos | **38** | **7** |
| Avisos | 75 | 70 |

Os 7 criticos que restam sao exactamente os precos que o Paulo ainda nao sabe
(PLC0009, PLC0011, FER0157, FER0137, FER0138, FER0139, FER0140) e desaparecem
sozinhos assim que o preco for preenchido. Os 70 avisos sao os precos com mais
de 12 meses.

### 8.4 O que ficou pendente

1. **Proteger a folha (F1.6).** A macro `Atualizar_ID_e_Ref` escreve nas
   celulas e tem as duas linhas de proteccao **comentadas**:

   ```vb
   'ws.Unprotect "1234"
   ...
   'ws.Protect "1234"
   ```

   Enquanto estiverem comentadas, proteger a folha faz a macro rebentar. Assim
   que o Paulo tirar as plicas (`Alt+F11`, apagar o `'` das duas linhas), a folha
   pode ser protegida com a password `1234` e a formula do `PLIQ` fica a salvo.

2. **A macro nao foi executada** por nenhum automatismo (mostra um `MsgBox` no
   fim, que travaria a automacao). As colunas de que ela precisa — `ID_MP`,
   `Ref_LE`, `FAMILIA` — nao foram tocadas e as colunas novas entraram no fim do
   bloco de precos, mas convem correr a macro uma vez para confirmar.

3. **Sugestao para a macro:** as linhas novas ficam com `TIPO_PRECO` e `ATIVO`
   vazios. Dentro do `Select Case familia`, a seguir a atribuir a `Ref_LE`, pode
   acrescentar-se:

   ```vb
   linha.Range.Cells(1, tbl.ListColumns("TIPO_PRECO").Index).Value = "TABELA"
   linha.Range.Cells(1, tbl.ListColumns("ATIVO").Index).Value = "SIM"
   ```

4. **F3 continua por fazer**: importar `DATA_ULTIMO_PRECO`, `STOCK`, `COR`,
   `NOME_FABRICANTE` e `REF_PHC` para a base de dados (migracao 95), guardar
   `TIPO_PRECO` (para o custeio deixar de assinalar como erro os materiais de
   preco livre), historico de precos, desactivar o que desaparece do Excel, ler
   as percentagens pelo formato da celula (P11) e limpar os espacos das
   descricoes (F1.9).

5. **F4** continua em aberto — o Paulo quer perceber melhor as duas hipoteses
   antes de decidir.

### 8.5 Guiao de teste (a fazer na app)

1. Abrir o Martelo V3 (base **martelo_v3_dev**) e entrar como `paulo`.
2. Menu lateral: **Orcamentos > Materias-Primas**.
3. Clicar em **"Verificar Excel"**.
   - Esperado: dialogo "Verificar Excel de matérias-primas" com o resumo
     "332 linhas — 7 críticos, 70 avisos" (mais os informativos de precos
     alterados, que so aparecem se ligar o terceiro filtro).
   - Esperado: os 7 criticos sao PLC0009, PLC0011, FER0157 e FER0137 a FER0140.
4. Ligar e desligar os filtros **Críticos / Avisos / Informativos** e confirmar
   que a lista muda.
5. Clicar em **"Copiar lista"** e colar no Excel ou no Bloco de Notas.
6. Fechar e clicar em **"Atualizar Pagina"** — a lista de materias-primas tem de
   ficar exactamente na mesma (a verificacao nao grava nada).
7. Clicar em **"Importar/Atualizar Excel"**.
   - Esperado: aviso "O Excel tem 7 problemas críticos… Quer ver a lista antes de
     importar?" com **Sim / Nao / Cancelar**.
   - "Sim" abre o relatorio e nao importa; "Cancelar" nao faz nada;
     "Nao" segue para a confirmacao habitual e importa.
8. Depois de importar, pesquisar `PLC0097` (uma "PLACAS LIVRES") e confirmar que
   continua la, activa e a 0,00 EUR — e assim que tem de ser.
9. Abrir o Excel no servidor e confirmar: cabecalho fixo ao rolar, listas nas
   colunas TIPO/COR/UND/FAMILIA/TIPO_PRECO/ATIVO e nas duas orlas, PLIQ a
   vermelho nas 7 linhas sem preco e datas antigas a ambar.
10. Correr a macro **Atualizar_ID_e_Ref** uma vez e confirmar que termina com
    "Actualização concluída." sem erro.

### 8.6 Correcao do formato da data (2026-08-25)

A coluna `DATA_ULTIMO_PRECO` ficou a mostrar **`23-04-yyyy`**: o formato foi
aplicado como `dd-mm-yyyy` e o Excel portugues tratou cada `y` como uma letra
literal (`dd\-mm\-\y\y\y\y`), porque em PT o codigo do ano e `aaaa`.

E a mesma armadilha das formulas (ver 8.1): **o que se passa ao Excel por COM vai
na lingua do Excel instalado**. Corrigido com `NumberFormatLocal = "dd-mm-aaaa"`,
que e a propriedade explicitamente localizada e nao obriga a adivinhar. Dentro do
ficheiro fica guardado na forma canonica `dd-mm-yyyy`, por isso funciona em
qualquer instalacao.

Salvaguarda antes desta correccao: `TAB_MATERIAS_PRIMAS_backup_20260825_110147.xlsm`.

Verificado depois de o Paulo correr a macro `Atualizar_ID_e_Ref`: 332 linhas,
`ID_MP` renumerado de 1 a 332, `TIPO_PRECO` (301 TABELA / 31 LIVRE), `ATIVO`
(332 SIM), semaforos, folha `LISTAS` e macros — tudo intacto. **A macro convive
bem com as colunas novas.**

As duas linhas da proteccao continuam comentadas na macro:

```vb
' ws.Unprotect 1234
'ws.Protect 1234
```

Enquanto tiverem a plica, o VBA ignora-as e a folha nao pode ser protegida. Ao
descomentar, a password deve ir entre aspas (`"1234"`), senao esta a passar-se um
numero em vez de texto.

### 8.7 Decisao sobre o F4 (2026-08-25)

O Paulo decidiu: **nao se aplica agora, mas fica para ser pensado e feito.** O
raciocinio dele e que, tendo o Martelo V3 "todo o universo" la dentro, faz
sentido que **inserir e alterar materias-primas passe a ser feito no proprio
V3**. Fica como direccao assumida para uma ronda futura, nao como duvida em
aberto.
