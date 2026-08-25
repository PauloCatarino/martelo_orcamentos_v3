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
