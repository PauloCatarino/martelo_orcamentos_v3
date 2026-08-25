# 31 - Materias-primas dentro do Martelo V3 (F3 + ciclo com os fornecedores)

> **Estado: PLANO. A aguardar validacao do mockup e das 4 decisoes do capitulo 5.**
> Continuacao de `docs/30_plano_melhoria_tabela_materias_primas.md`, onde o Excel
> foi endurecido e o V3 ganhou o "Verificar Excel".
> Mockup: `docs/mockups/mockup_materias_primas_v3.html`.

---

## 1. O que muda de fundo

O Excel deixa de ser a fonte das materias-primas: passa a ser **um destino de
exportacao**. O registo (inserir, alterar, desativar) passa a fazer-se dentro do
V3, com registo de quem mexeu e historico de precos.

A isto junta-se uma ideia do Paulo que resolve o problema real do dia-a-dia:
**nao ser ele a andar atras dos precos**. O V3 junta os materiais com preco
antigo, agrupa-os por fornecedor, prepara um email com uma tabela para o
fornecedor preencher, e quando essa tabela volta o V3 le-a e propoe as
atualizacoes.

---

## 2. O que ja esta a nosso favor (verificado no codigo)

Duas coisas que tornam isto muito menos arriscado do que parece:

1. **Os orcamentos ja guardam a sua propria copia do material.** A linha de
   custeio grava `ref_le`, `descricao_materia_prima`, `descricao_no_orcamento` e
   `preco_liquido` no momento em que o material e escolhido
   (`app/models/orcamento_item_custeio_linha.py`, linhas 157-161), alem do
   `materia_prima_id`. **Mexer no catalogo nao altera orcamentos ja feitos.**
2. **A pesquisa de materiais ja filtra os ativos**
   (`app/repositories/def_materia_prima_repository.py`, `pesquisar()` e
   `list_active()`). Um material desativado ja desaparece das escolhas; falta a
   UI para o desativar e para o voltar a mostrar.

O mesmo padrao de snapshot existe nas linhas de ValueSet (orcamento, item e
modelo), por isso a garantia e a mesma em todo o lado.

---

## 3. Fases

### G1 - Base de dados (migracao 95)

Campos novos em `def_materias_primas`:

| Campo | Porque |
| --- | --- |
| `data_ultimo_preco` | o aviso dos 12 meses passa a viver no V3 |
| `tipo_preco` (`TABELA` / `LIVRE`) | o custeio deixa de tratar os materiais livres como erro |
| `stock`, `cor`, `nome_fabricante`, `ref_phc` | hoje estao preenchidos no Excel e perdem-se |
| `criado_por_id`, `alterado_por_id` | saber quem inseriu e quem alterou |

Tabela nova `def_materias_primas_precos_historico`: material, preco tabela,
preco liquido, desconto, margem, data, origem (`EXCEL` / `MANUAL` /
`FORNECEDOR`) e utilizador.

A importacao do Excel passa a preencher tudo isto e a escrever no historico
sempre que um preco mude.

### G2 - Editar no V3

- botoes **Novo / Editar / Duplicar / Desativar** na pagina de Matearias-Primas;
- **"Mostrar nao ativos"**, com as linhas inativas riscadas e a cinzento
  (equivalente ao `Ctrl+5` do Excel);
- ficha do material com os separadores **Dados**, **Historico de precos** e
  **Onde esta a ser usado**;
- rodape com "N precos a rever" e "N sem preco", a ligar ao pedido aos
  fornecedores;
- a `Ref_LE` continua a ser atribuida automaticamente por familia
  (`PLC`/`FER`/`ACB`/`ORL` + 4 digitos), a mesma regra da macro do Excel, e
  **nunca se repete**.

### G3 - Regressao dos orcamentos (a fase que nao se ve mas e a mais importante)

Testes que provam, com dados, que continua tudo a funcionar:

- um orcamento feito com um material **desativado** depois disso mantem
  descricao, referencia e preco, e continua a custear igual;
- um orcamento feito **antes** de uma alteracao de preco mantem o preco antigo;
- um material desativado **nao aparece** nas escolhas de linhas novas;
- a auditoria de custeio deixa de marcar como erro os materiais de preco livre;
- o "Verificar Excel" continua a funcionar para quem ainda importe do Excel.

### G4 - Exportar para Excel

Botao "Exportar Excel" que gera o ficheiro no formato atual (mesmas colunas,
mesma folha), para consulta, impressao e para quem quiser trabalhar fora.

### G5 - Fornecedores a serio

Hoje o fornecedor e apenas **texto** na linha do material. Para haver email e
preciso uma tabela propria (nome, email, contacto, observacoes) e ligar cada
material ao fornecedor. Aproveita-se para normalizar os nomes que hoje estao
escritos a mao.

### G6 - Pedir precos ao fornecedor

- ecra que junta os materiais com preco acima de N meses, agrupados por
  fornecedor;
- gera **um anexo por fornecedor** so com: codigo (nossa referencia, bloqueado),
  ref. do fornecedor, designacao, unidade e as colunas a preencher (preco novo,
  nova referencia, nova designacao, observacoes);
- **nao vao** desconto, margem, preco liquido, desperdicio, stock, orlas nem
  obras;
- prepara o email no Outlook (mesmo caminho ja usado nos orcamentos e no aviso
  de producao), com o texto de apresentacao ja escrito.

### G7 - Importar a resposta

- le o ficheiro devolvido e mostra um **ecra de revisao**: preco atual, preco
  novo, variacao e observacoes do fornecedor, com visto por linha;
- assinala variacoes fora do normal e as referencias marcadas como
  descontinuadas (propondo desativa-las);
- ao aplicar, escreve no historico com origem `FORNECEDOR`.

### G8 - Assistente (a parte de IA)

Onde a IA acrescenta mesmo alguma coisa:

1. **encontrar as colunas** quando o fornecedor mexe no ficheiro ou responde com
   a lista dele;
2. **ler uma tabela de precos em PDF** enviada em vez do anexo;
3. **assinalar valores estranhos** antes de entrarem na base de dados.

O que **nao** faz: decidir sozinha o que fica gravado. A ultima palavra e sempre
um visto do utilizador.

---

## 4. Ordem e risco

```
G1 (migracao)  ->  G2 (editar no V3)  ->  G3 (regressao)   <- fecha o essencial
                              G4 (exportar Excel)
G5 (fornecedores) -> G6 (pedir precos) -> G7 (importar resposta) -> G8 (IA)
```

G1+G2+G3 e o bloco que tem de andar junto: sem G3 nao se mexe no catalogo com
confianca. G4 e pequeno e pode entrar a qualquer momento. G5 a G8 sao o ciclo
com os fornecedores e podem esperar.

Riscos a vigiar:

- **a beta** precisa da migracao 95 quando la chegar;
- **nomes de fornecedor escritos a mao** (277 preenchidos, com variacoes) vao
  precisar de uma limpeza manual em G5;
- **os emails dos fornecedores** nao existem em lado nenhum ainda.

---

## 5. Decisoes pendentes (estao no fim do mockup)

1. O anexo mostra ao fornecedor o preco que temos, ou so pede o novo?
2. A resposta do fornecedor aplica-se automaticamente ou passa sempre por
   revisao? (proposta: revisao, com "aceitar tudo" a mao)
3. Criamos tabela de fornecedores a serio (nome, email, contacto)?
4. O Excel antigo continua a poder ser importado, ou passa a ser so exportacao?

---

## 6. O que ficou feito (2026-08-25) - G1, G2 e G3

### 6.1 Decisoes do Paulo que fecharam o desenho

1. **O anexo mostra o preco atual.** O fornecedor preenche o **preco de tabela**
   e a **percentagem de desconto** - as duas colunas que o Excel ja tinha. O
   preco liquido e calculado por nos e nunca sai daqui.
2. **A importacao da resposta e automatica, a validacao e sempre humana.** Mesmo
   com o ficheiro bem preenchido, os valores passam por confirmacao antes de
   entrarem no catalogo.
3. **Vai existir tabela de fornecedores.** Os fornecedores tem varios emails por
   departamento, por isso no envio o V3 **sugere** o destinatario e o utilizador
   pode altera-lo e acrescentar CC.
4. **O Excel deixa de ser fonte.** A partir do momento em que os dados sao
   editados no V3, o ficheiro fica desatualizado e nao pode voltar a importar.

### 6.2 G1 - Base de dados (migracao `20260825_95`)

Campos novos em `def_materias_primas`: `tipo_preco` (TABELA/LIVRE),
`data_ultimo_preco`, `stock`, `cor`, `nome_fabricante`, `ref_phc`,
`criado_por_id` e `alterado_por_id`. Tabela nova
`def_materias_primas_precos_historico` (so acrescenta, nunca reescreve) e os
*grants* do MySQL aplicados como nas outras tabelas.

A migracao **converte as percentagens** de fraccao (0,2) para percentagem humana
(20). Era o P11 do documento 30: a leitura dependia de adivinhar pelo valor e
enganava-se numa margem de 100%. E seguro correr duas vezes e nao toca em
orcamentos - as linhas de custeio tem a sua propria copia.

Vocabulario partilhado em `app/domain/materia_prima_types.py` (tipos de preco,
familias, unidades, prefixos das referencias, `preco_em_falta`,
`preco_desatualizado`), para o modelo, a validacao e os ecras falarem todos a
mesma lingua.

### 6.3 G2 - Editar dentro do V3

- **Nova materia-prima / Editar / Duplicar / Desativar** e **"Mostrar nao
  ativos"** na pagina de Materias-Primas; duplo-clique abre a ficha;
- linhas descontinuadas **riscadas e a cinzento**, como o `Ctrl+5` do Excel, com
  a coluna "Ativo" legivel;
- colunas novas: **Ultimo preco**, **Stock** e **Fornecedor**; preco em falta a
  vermelho e preco com mais de 12 meses a ambar - as mesmas cores do Excel;
- rodape com o que esta a vista, quantos precos ha a rever e quantos estao sem
  preco;
- ficha (`app/ui/dialogs/materia_prima_dialog.py`) com **Dados** e **Historico de
  precos**, o preco liquido **calculado** e nao escrito, a referencia atribuida
  automaticamente pela familia, e a linha de quem criou / quem alterou;
- desativar pede confirmacao e diz em quantas linhas de orcamento o material
  esta a ser usado;
- materiais de **preco livre** nao tem campos de preco: o valor escreve-se dentro
  do orcamento.

Uma consequencia assumida: **sem origem indicada, um material passa a nascer com
`origem_dados = "V3"`** (era `EXCEL`). A importacao continua a marcar `EXCEL`
expressamente.

### 6.4 G3 - Regressao (a rede de seguranca)

`tests/test_materias_primas_no_v3_regressao.py` - 19 testes com base de dados a
serio, que provam:

- desativar um material **nao muda** a referencia, a descricao nem o preco das
  linhas de orcamento onde ja foi usado;
- alterar o preco ou a descricao **nao muda** os orcamentos ja calculados;
- um material desativado sai das escolhas (`pesquisar`, `list_active`) mas
  continua no catalogo e pode ser reposto;
- as referencias nunca se repetem nem se reaproveitam, mesmo depois de
  desativar;
- o historico so ganha linha quando o preco muda mesmo;
- "preco em falta" e "preco a rever" ignoram os materiais de preco livre.

Mais `tests/test_migracao_materias_primas_no_v3.py` (4 testes: colunas,
conversao das percentagens, idempotencia e downgrade). Suite completa: **3723
testes**.

### 6.5 Guiao de teste

1. Na pasta principal, correr a migracao com `python -m alembic upgrade head`.
   Esperado: a base fica em `20260825_95`.
2. Abrir o Martelo V3 (base **martelo_v3_dev**) e entrar como `paulo`.
3. **Orcamentos > Materias-Primas** e clicar em **"Importar/Atualizar Excel"**
   **uma ultima vez**: e o que traz do Excel o `TIPO_PRECO`, a
   `DATA_ULTIMO_PRECO`, o stock, a cor, o fabricante e a referencia PHC.
   **Depois desta importacao o Excel deixa de ser usado.**
4. Confirmar na lista: coluna **Ultimo preco** preenchida, com ambar nos precos
   de 2025; **Preco Liquido** a vermelho nos 7 sem preco; as "PLACAS LIVRES" a
   dizer *preco livre*.
5. **"+ Nova materia-prima"**: escolher familia PLACAS e confirmar que o campo
   Ref LE sugere a proxima referencia livre. Preencher preco de tabela 30 e
   desconto 20 e confirmar que o **preco liquido da 24,00 EUR** sozinho. Gravar.
6. Selecionar essa materia-prima nova e **Desativar**. Confirmar que desaparece
   da lista e que o rodape passa a dizer "1 descontinuada escondida".
7. Ligar **"Mostrar nao ativos"**: aparece **riscada e a cinzento**.
8. Com ela selecionada, o botao passa a **"Repor ativo"** - clicar e confirmar
   que volta ao normal.
9. Escolher uma materia-prima **ja usada num orcamento** (por exemplo uma placa
   comum), abrir com duplo-clique e confirmar o separador **Historico de precos**
   e a frase "Usado em N linhas de orcamento".
10. Alterar-lhe o preco de tabela e gravar. Abrir um **orcamento antigo** que use
    essa materia-prima e confirmar que **os valores nao mudaram**.
11. Voltar a ficha e confirmar que o **Historico** ganhou uma linha nova, com a
    variacao em percentagem e o seu nome.

### 6.6 O que falta

- **G4** a **G8 estao FEITOS**: exportar para Excel, tabela de fornecedores,
  pedido de precos, importar a resposta e o assistente. O G8 tem documento
  proprio: `docs/32_assistente_resposta_fornecedor_g8.md`.
- **Os botoes do Excel sairam da barra** (commit 6468756) e o script de
  importacao recusa-se a correr por cima do que ja foi editado no V3. Falta
  virar as regras de validacao escritas para o ficheiro para validar o
  **catalogo do V3** (precos em falta, orlas que nao existem, espessuras que
  nao batem certo).
- A auditoria de custeio continua a assinalar como erro uma linha de material de
  preco livre ainda sem preco. Esta **correto** (o orcamento sairia a zero), mas
  a mensagem pode passar a dizer "material de preco livre: escreva o preco nesta
  linha" em vez do aviso generico.
- A **beta** precisa das migracoes 95 e 96 quando la chegar.
