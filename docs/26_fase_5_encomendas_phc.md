# Fase 5 — Várias encomendas PHC por versão

Uma versão de orçamento pode agora ter **várias encomendas PHC**, guardadas na
nova tabela filha `orcamento_versao_encomendas_phc` (migração `20260728_67`,
aditiva). Regras:

- Cada versão marca **uma encomenda como principal** (★). O campo antigo
  `orcamento_versoes.enc_phc` é mantido por compatibilidade e passa a ser um
  **espelho da principal** — as listas (Orçamentos, Início) continuam a
  mostrá-la sem alterações; quando existem mais encomendas aparece o sufixo
  `(+N)`.
- A migração importa o `enc_phc` existente como primeira encomenda
  (principal). Versões antigas sem registo filho continuam a funcionar por
  fallback de leitura.
- No **Editar Orçamento**, o campo único "Enc. PHC" deu lugar ao grupo
  **Encomendas PHC**: adicionar, remover e **Principal**. Números repetidos na
  mesma versão são recusados.
- Na **conversão para produção**, o diálogo mostra todas as encomendas da
  versão e permite escolher qual dá origem ao processo PHC (a principal vem
  pré-selecionada). Cada encomenda pode ser convertida no seu próprio
  processo; converter duas vezes a mesma encomenda é recusado; o orçamento
  continua único.

## Roteiro manual

1. Execute `python -m alembic upgrade head` e confirme `20260728_67 (head)`.
2. Abra **Orçamentos** e escolha um orçamento existente com Nº Enc PHC
   preenchido. Clique **Editar** e confirme que o número antigo aparece no
   grupo **Encomendas PHC** com a estrela de principal.
3. Adicione mais duas encomendas (por exemplo `901` e `902`) e grave.
   Confirme que a lista de orçamentos mostra a principal com `(+2)`.
4. Volte a **Editar**, selecione `901` e clique **Principal**. Grave e
   confirme que a lista passa a mostrar `901 (+2)`.
5. Tente adicionar uma encomenda com um número já existente na versão e
   confirme a mensagem de erro.
6. Com o orçamento **Adjudicado** e um cliente PHC definitivo, abra
   **Produção > Converter Orçamento**. Confirme a coluna `Nº Enc PHC` com
   `(+2)` e o seletor **Encomenda PHC a converter** com as três encomendas.
7. Converta com a encomenda principal e depois converta novamente escolhendo
   outra encomenda: cada uma cria o seu processo (`26.0901_01_01…`, etc.).
8. Tente converter uma encomenda já convertida e confirme o aviso
   "Já existe o processo…". Confirme que o orçamento continua único na
   página Orçamentos.
