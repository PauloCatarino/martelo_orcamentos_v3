# Fase 6 - Analise do Excel de materias-primas

## Origem

- ficheiro analisado: `C:\Users\Utilizador\Documents\Martelo_Orcamentos_V3\TAB_MATERIAS_PRIMAS.xlsm`
- nota: o nome de referencia da fase e `TAB_MATERIAS_PRIMAS(3).xlsm`; o `(3)` indica apenas uma copia descarregada. A estrutura analisada e a mesma tabela de materias-primas.
- este relatorio foi gerado automaticamente pelo script `scripts/analyze_materias_primas_excel.py` e e apenas analise.

## Resumo das folhas encontradas

| Folha | Linhas | Colunas | Linhas de dados |
| --- | --- | --- | --- |
| `Tab_Materias_Primas` | 295 | 29 | 290 |

## Estrutura da folha principal

- folha: `Tab_Materias_Primas`
- linha de cabecalho detetada: linha 5
- colunas: 29
- linhas de dados: 290

### Lista de colunas

1. `ID_MP`
2. `REF_PHC`
3. `REF_FORNECEDOR`
4. `Ref_LE`
5. `DESCRICAO_do_PHC`
6. `DESCRICAO_no_ORCAMENTO`
7. `PRECO_TABELA`
8. `MRG_(+)`
9. `DESC2_(-)`
10. `PLIQ`
11. `UND`
12. `DESP`
13. `ESP_MP`
14. `TIPO`
15. `FAMILIA`
16. `COR`
17. `CORESP_ORLA_0_4`
18. `CORESP_ORLA_1_0`
19. `COR_REF_MATERIAL`
20. `COMP_MP`
21. `LARG_MP`
22. `NOME_FORNECEDOR`
23. `NOME_FABRICANTE`
24. `DATA_ULTIMO_PRECO`
25. `APLICACAO`
26. `STOCK`
27. `NOTAS_2`
28. `NOTAS_3`
29. `NOTAS_4`

### Primeiras linhas de exemplo

| ID_MP | REF_PHC | REF_FORNECEDOR | Ref_LE | DESCRICAO_do_PHC | DESCRICAO_no_ORCAMENTO | PRECO_TABELA | MRG_(+) | DESC2_(-) | PLIQ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 |  | FOLHEADO_ALDECOR | PLC0001 |  | AGL FOL ALD. BÉTULA D… | 24.87 |  | 0.2 | 19.896 |
| 2 |  | FOLHEADO_ALDECOR | PLC0002 |  | AGL FOL ALD. CARV. BR… | 31.51 |  | 0.2 | 25.208000000000002 |
| 3 |  | FOLHEADO_ALDECOR | PLC0003 |  | AGL FOL ALD. CARV. BR… | 36.87 |  | 0.2 | 29.496 |
| 4 |  | FOLHEADO_ALDECOR | PLC0004 |  | AGL FOL ALD. CARV. EU… | 32.49 |  | 0.2 | 25.992000000000004 |
| 5 |  | FOLHEADO_ALDECOR | PLC0005 |  | AGL FOL ALD. CARV. EU… | 33.58 |  | 0.2 | 26.864 |

(mostradas as primeiras 10 de 29 colunas, para evitar excesso de dados)

## Tipos e familias encontradas

### Coluna `UND`

- 3 valores unicos:

| Valor | Ocorrencias |
| --- | --- |
| `M2` | 147 |
| `UND` | 119 |
| `ML` | 19 |

### Coluna `TIPO`

- 17 valores unicos:

| Valor | Ocorrencias |
| --- | --- |
| `AGLOMERADO` | 99 |
| `ROUPEIROS CORRER` | 22 |
| `FERRAGENS` | 20 |
| `CORREDICAS` | 19 |
| `ILUMINACAO` | 19 |
| `VERNIZ` | 15 |
| `ACESSORIOS` | 14 |
| `DOBRADICAS` | 11 |
| `VIDRO` | 11 |
| `PES` | 7 |
| `PUXADOR` | 7 |
| `MDF` | 6 |
| `SUPORTE VARAO` | 6 |
| `RODAPE` | 3 |
| `SPP` | 3 |
| `SUPORTE PRATELEIRA` | 2 |
| `LACAR` | 1 |

### Coluna `FAMILIA`

- 4 valores unicos:

| Valor | Ocorrencias |
| --- | --- |
| `FERRAGENS` | 144 |
| `PLACAS` | 118 |
| `ACABAMENTOS` | 16 |
| `ORLA` | 7 |

### Coluna `COR`

- 28 valores unicos:

| Valor | Ocorrencias |
| --- | --- |
| `BRANCO` | 29 |
| `CARVALHO` | 13 |
| `PRETO` | 9 |
| `ALUMINIO` | 7 |
| `ANODIZ/BRANCO` | 5 |
| `ANODIZADO` | 5 |
| `ABS` | 4 |
| `ANTRACITE` | 4 |
| `CINZA` | 4 |
| `LINHO` | 4 |
| `NOGUEIRA` | 4 |
| `ALUM/PRETO/BRANCO` | 3 |
| `CROMADO` | 3 |
| `NUDE` | 3 |
| `BEGE` | 2 |
| `CASTANHO` | 2 |
| `FAIA` | 2 |
| `BRANCO/PRETO` | 1 |
| `BÉTULA` | 1 |
| `CEREJEIRA` | 1 |
| `EUCALIPTO` | 1 |
| `FREIXO` | 1 |
| `KAMBALA` | 1 |
| `MAPLE/ERABLE` | 1 |
| `MONGNO` | 1 |
| `PINHO` | 1 |
| `PLASTICO` | 1 |
| `ZAMAK` | 1 |

## Proposta inicial de mapeamento para o Martelo V3

Proposta automatica e provisoria, agrupando os valores de `TIPO` e `FAMILIA` por palavra-chave. Precisa de revisao humana.

- **Materias-primas de painel**: `AGLOMERADO`, `MDF`, `PLACAS`
- **Orlas**: `ORLA`
- **Ferragens**: `CORREDICAS`, `DOBRADICAS`, `FERRAGENS`
- **Acessorios**: `ACESSORIOS`, `PES`, `PUXADOR`, `RODAPE`, `SUPORTE PRATELEIRA`, `SUPORTE VARAO`
- **SPP / barras / ML**: `SPP`
- **Iluminacao / LEDs**: `ILUMINACAO`
- **Outros (a rever)**: `ACABAMENTOS`, `LACAR`, `ROUPEIROS CORRER`, `VERNIZ`, `VIDRO`

> Nem todos os tipos do Excel devem virar categorias finais do Martelo V3. Esta proposta serve apenas como ponto de partida; alguns tipos podem ser fundidos, renomeados ou descartados apos revisao tecnica.

## Observacoes sobre dados uteis

- existem colunas de identificacao (por exemplo `ID_MP`, `REF_*`) que podem servir de codigo estavel no catalogo do V3;
- existem colunas de preco, margem e desconto que alimentam o custeio futuro;
- existem colunas de dimensao (comprimento, largura, espessura) compativeis com a logica de peca horizontal Comp / Larg / Esp do V3;
- existem colunas de classificacao (`TIPO`, `FAMILIA`, `COR`) uteis para montar os grupos de material/ferragem.

## Observacoes sobre dados que precisam de limpeza

- o cabecalho nao esta na primeira linha (esta na linha 5); a importacao deve saltar as linhas iniciais;
- alguns valores de texto (descricoes, cores) podem ter problemas de codificacao de caracteres acentuados e precisam de revisao;
- os valores de `TIPO` e `FAMILIA` devem ser normalizados (maiusculas, sem acentos, sem duplicados quase iguais) antes de virarem grupos finais;
- podem existir linhas vazias, colunas auxiliares ou registos antigos que nao devem ser importados diretamente.

## Proximos passos e decisoes pendentes

- que valores de `TIPO`/`FAMILIA` se tornam grupos finais do Martelo V3?
- ferragens e acessorios ficam na mesma tabela ou em tabelas separadas?
- SPP pertence a materiais ou a acessorios?
- como mapear cada `TIPO` antigo para os grupos novos sem duplicar?
- que colunas do Excel sao realmente necessarias no catalogo do V3?
- como tratar a codificacao de caracteres ao importar?

Esta fase e apenas analise. Nao foram criadas tabelas, models, migrations nem importacao real de dados.
