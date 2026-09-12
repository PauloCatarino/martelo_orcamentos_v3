# 35 — Navegador de chaves nos Modelos ValueSet

Estado: **CICLO FECHADO — Peças 1 a 4 entregues** (12-set-2026). Falta o teste dele.

---

## Objetivo

Remodelar a página **Configurações → Modelos ValueSet → (modelo)**
(`app/ui/pages/def_valueset_modelo_detail_page.py`), hoje uma tabela plana de
~100 linhas × 17 colunas onde é difícil localizar uma chave. Vai crescer para ~200.

---

## O que já foi analisado (não repetir)

- As chaves aparecem misturadas porque `agrupar_linhas_por_chave` ordena por
  `linha.chave` como **string** — `def_valueset_modelo_linha_service.py:315`.
- `def_valueset_chaves` **já tem** `tipo`/`grupo`/`ordem` preenchidos nas 80 chaves,
  0 sem grupo. Agrupar **não precisa de migração**: basta LEFT JOIN por
  `codigo = chave`. No ROUP_STD (id 4, 95 linhas): MATERIAIS 27, FERRAGENS 46,
  SISTEMAS_CORRER 9, ILUMINACAO 7, ORLAS 2, ACABAMENTOS 2.
- O código da chave é **texto solto em 7 tabelas, sem FK nenhuma**:
  `def_valueset_chaves.codigo` (o vocabulário), `def_valueset_modelo_linhas.chave`,
  `orcamento_valueset_linhas.chave`, `orcamento_item_valueset_linhas.chave`,
  `def_pecas.chave_valueset_material` / `_acabamento_sup` / `_acabamento_inf`,
  `def_modulo_linhas.chave_valueset`, `orcamento_item_custeio_linhas.chave_valueset`.
- `editar_chave` (`def_valueset_chave_service.py:108`) muda o `codigo` **sem propagar**.
- **Sintoma silencioso:** `valueset_compat.py:68` — uma linha de custeio do tipo
  FERRAGEM só vê opções com a MESMA chave; `chave_tipos` vem de
  `def_valueset_chaves` (`orcamento_item_custeio_linha_service.py:1268`).
  Chave órfã → tipo `None` → `return []` → dropdown "Mat. default" **vazio**,
  sem erro nem log.
- Limita o estrago: o combo de chave da Nova Linha **não é editável**
  (`def_valueset_modelo_linha_dialog.py:152`) — não se inventam chaves a escrever.
- `CatalogoAuditoriaService` já valida `def_peca.chave_valueset_material`
  (`catalogo_auditoria_service.py:243`) mas **não** valida as chaves dos modelos
  ValueSet nem de `def_modulo_linhas`.

### FERRAGEM_SUPORTE_VARAO — alcance real (medido em 12-set-2026)

`FERRAGEM_SUPORTE_VARAO` já não existe no vocabulário. O vocabulário tem hoje
`FERRAGEM_VARAO` (id 14), `FERRAGEM_SUPORTE_LATERAL_VARAO` (id 15) e
`FERRAGEM_SUPORTE_CENTRAL_VARAO` (id 68).

Na base **real** (`martelo_v3`) sobrevive em **1 sítio só**:

| tabela | ocorrências |
|---|---|
| `def_valueset_modelo_linhas.chave` | **1** (linha 48) |
| `orcamento_valueset_linhas.chave` | 0 |
| `orcamento_item_valueset_linhas.chave` | 0 |
| `def_modulo_linhas.chave_valueset` | 0 |
| `orcamento_item_custeio_linhas.chave_valueset` | 0 |
| `def_pecas.chave_valueset_*` | 0 |

A linha 48: modelo **Roupeiro standard** (id 2, âmbito UTILIZADOR),
`nome_opcao` = "Suporte varão standard", `ref_le` = FER0089,
`descricao_no_orcamento` = "SUPORTE VARAO ROUPEIRO F233",
prioridade 1, ordem 14, ativo.

As 6 + 12 ocorrências em orçamentos que tinham sido contadas antes estão na base
**dev** (`martelo_v3_dev`), não na real. As peças/associados já foram migrados a 11/09.

---

## Decisões do Paulo

- Clique numa chave = **filtra**. Manter os cabeçalhos de grupo na tabela.
- "Agrupar por chave" passa a **grupo → ordem da chave → prioridade**
  (continua a pedir confirmação, porque reescreve a coluna `ordem`).
- Entrega **faseada**: ele testa cada fase antes da seguinte.
- SUPORTE_VARAO: corrigir em modelos ValueSet, peças e módulos.
  **Orçamentos já feitos ficam intactos.**
- Reimportação de modelo com chave renomeada (duplicados): **não tratar agora**.
  Orçamentos antigos morrem como estão, servem para visualização.
- **Não** adicionar FK às 7 tabelas — risco alto, benefício já dado pela auditoria.

---

## Plano

### Peça 1 (agora)
Navegador de chaves à esquerda (`QTreeWidget` + `QSplitter`, padrão de
`biblioteca_modulos_page.py`, com `estado_splitter.py`), chips de grupo,
cabeçalhos de grupo/chave colapsáveis na tabela, novo "Agrupar por chave",
e corrigir o **N+1** em `carregar_linhas`
(`def_valueset_modelo_detail_page.py:301` — faz 1 query por linha para as
operações; trocar por `IN(...)` único).

**Cuidado:** `estilo_tabela_valueset.py` é partilhado com `orcamento_valueset_page`
e `orcamento_item_valueset_page` — alterações só **aditivas**. As setas ↑↓ já
recebem `ids_visiveis` (linha 348), já funcionam filtradas. Manter
`ligar_persistencia_larguras` e `ligar_menu_colunas`. Chaves órfãs → grupo "Sem grupo".

Testes: `test_valueset_modelo_detail_page_setas.py`,
`test_valueset_modelo_linha_ordenacao.py`, `test_estilo_tabela_valueset.py`,
`test_valueset_modelo_pesquisa.py` + suite completa.

### Peça 2 — FEITA (12-set-2026)
Auditoria alargada, em `catalogo_auditoria_service.py`. Cinco testes novos:

| código | severidade | o que apanha |
|---|---|---|
| `VALUESET_MODELO_CHAVE_INEXISTENTE` | ERRO | chave de linha de modelo fora do vocabulário |
| `VALUESET_MODELO_CHAVE_INATIVA` | AVISO | chave existe mas está desativada |
| `MODULO_CHAVE_VALUESET_INEXISTENTE` | ERRO | `def_modulo_linhas.chave_valueset` órfã |
| `MODULO_CHAVE_VALUESET_INATIVA` | AVISO | idem, mas só desativada |
| `VALUESET_MODELO_CHAVES_EM_FALTA` | AVISO | chaves que TODOS os irmãos do mesmo tipo têm |

Decisões de desenho, medidas na base real antes de escrever:
- **Um item por (modelo, chave)**, não um por linha — 6 linhas da mesma chave
  órfã dão 1 ocorrência que diz "6 linha(s)".
- **Chaves em falta comparam-se com os irmãos do mesmo tipo**, não com o
  vocabulário inteiro. Com o vocabulário inteiro dava **121 avisos**; assim dá
  **1**. Um modelo sozinho no seu tipo não é comparado com nada, e uma chave que
  só um irmão tem não conta como falta.
- **Um item por modelo** nas chaves em falta, não um por chave: o
  ROUPEIRO_INOV_POSITIVA sozinho enchia o relatório com 40.

Guião: `docs/GUIAO_TESTE_AUDITORIA_CHAVES_VALUESET.md`.

### FERRAGEM_SUPORTE_VARAO — resolvido (12-set-2026)
A `def_materias_primas` FER0089 passou a chamar-se
"SUPORTE **LATERAL** VARAO ROUPEIRO F233" (o Paulo alinhou os nomes das
matérias-primas). A linha 48 passou de `FERRAGEM_SUPORTE_VARAO` para
`FERRAGEM_SUPORTE_LATERAL_VARAO`. Já não há chaves órfãs em modelos na base real.

Fica por alinhar, se ele quiser: a própria linha 48 ainda tem
`nome_opcao` = "Suporte varão standard" e
`descricao_no_orcamento` = "SUPORTE VARAO ROUPEIRO F233" — sem o "LATERAL". É o
texto que sai no orçamento ao cliente.

### Peça 3 — FEITA (12-set-2026)
`app/services/def_valueset_chave_renomeacao_service.py` +
`app/ui/dialogs/renomear_chave_valueset_dialog.py`, ligados ao "Editar Chave"
de `def_valueset_chaves_page.py`.

Mudar o **código** deixa de ser uma edição e passa a ser uma **renomeação**:
abre uma janela que conta, tabela a tabela, quem usa a chave, e pergunta o
alcance antes de gravar. Alterar nome/grupo/ordem/tipo continua a ser edição
normal, e mudar só espaços ou caixa não conta como renomeação.

**O alcance, e porquê.** Medido na base real:

| chave | catálogos | orçamentos |
|---|---:|---:|
| `FERRAGEM_VARAO` | 24 | 849 |
| `FERRAGEM_SUPORTE_LATERAL_VARAO` | 17 | 576 |
| `MATERIAL_COSTAS` | 30 | 539 |

Os catálogos são a configuração viva — é aí que renomear resolve o problema.
Os orçamentos são o registo do que foi vendido, com preços e descrições
congelados, e são ~20× mais linhas. Por isso ficam **de fora por omissão**, com
uma caixa que tem de ser ligada de propósito.

A operação é **tudo ou nada** (uma transação): ficar a meio seria exatamente a
situação que isto veio resolver.

Guião: `docs/GUIAO_TESTE_RENOMEAR_CHAVE_VALUESET.md`.

### Peça 4 — FEITA (12-set-2026)
`app/services/def_valueset_chave_copia_service.py` +
`app/ui/dialogs/copiar_chaves_valueset_dialog.py`, com o botão
**"Copiar Chaves…"** na página de detalhe do modelo.

Leva chaves inteiras de um modelo para outros, com pré-visualização por modelo
antes de escrever seja o que for. As operações viajam com a linha.

**Duas regras que não se negoceiam:**

1. **Nunca apaga nem desativa nada no destino.** Uma opção que só exista lá pode
   ter sido posta de propósito por quem é dono do modelo, e não cabe a uma cópia
   em massa decidir que ela sobra. Ela aparece na coluna "Só no destino" e fica.
2. **Respeita o dono** — mesma regra da propagação de operações: o modelo
   próprio é sempre seu; global ou de outra pessoa exige
   `acao.propagar_operacoes_valueset_outros`. Hoje têm-na: admin, paulo,
   Andreia, Catia.

Dois modos, com o menos destrutivo por omissão:
- `SO_ACRESCENTAR` — cria o que falta, não toca no que já lá está;
- `ACRESCENTAR_E_ATUALIZAR` — além disso, põe as opções comuns iguais às da
  origem (material, preços, prioridade e operações).

A identidade de uma linha é `(modelo, chave, código da opção)` — é por ela que
se decide o que é criar e o que é atualizar, e é o que torna a operação
idempotente: correr duas vezes não duplica nada.

**A marca ✎ é do utilizador, não da cópia** (decidido com ele a 12-set-2026,
depois de ver o resultado no ecrã). O `aplicar_snapshot_linha` passou a aceitar
`marcar_editado=False`, e a cópia usa-o: nem as linhas criadas nem as
atualizadas ficam com `editado_localmente`, e uma marca anterior **sai** quando
a linha é reposta pelo modelo de origem. O `origem_dados` viaja com o conteúdo
em vez de virar "EDITADO_LOCALMENTE". O **Colar Dados** (Ctrl+V) à mão continua
a marcar — é esse o propósito da bandeira.

Guião: `docs/GUIAO_TESTE_COPIAR_CHAVES_VALUESET.md`.

**Contexto do INOV_POSITIVA:** era um modelo de teste do utilizador `admin`, do
início do desenvolvimento, já não usado por ninguém. O Paulo desativou-o a
12-set-2026, e com isso o aviso `VALUESET_MODELO_CHAVES_EM_FALTA` deixou de
aparecer (a auditoria ignora modelos inativos). A Peça 4 fica na mesma útil para
o caso normal: chave nova que tem de ir para todos os modelos.

---

O mockup validado está em `tmp/mockup_valueset/mockup_valueset.html`.
