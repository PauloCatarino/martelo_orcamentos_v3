# Fase 2 — Opção única nos ValueSets

## Regra funcional

O utilizador vê uma única coluna/campo chamado **Opção**. O texto apresentado
é `nome_opcao`, com fallback para `codigo_opcao`. Os dois campos continuam na
base de dados e continuam a ser usados pela unicidade, pesquisa, resolução,
propagação, importação e custeio.

## Identidade técnica

Em novas linhas, o serviço gera `codigo_opcao` internamente:

1. `LE_<Ref LE normalizada>` quando existe Ref LE;
2. `MP_<Ref MP normalizada>` quando só existe Ref MP;
3. `OP_<nome normalizado>` para opção livre;
4. a chave ValueSet como fallback de compatibilidade quando não há nome nem
   referência.

As colisões de códigos gerados recebem o sufixo determinístico `_2`, `_3`, …
no mesmo âmbito e chave. Um código fornecido internamente continua sujeito à
validação de unicidade.

Ao editar, o serviço lê o registo original e preserva sempre o seu
`codigo_opcao`; apenas `nome_opcao` pode mudar através da interface. As cópias
Modelo → orçamento → item continuam a transportar os dois campos sem
alteração.

## Teste manual

1. Abrir um Modelo ValueSet e confirmar que a tabela tem apenas **Opção**, sem
   **Nome opção**.
2. Criar uma opção livre; preencher apenas **Opção**, guardar e confirmar que
   a tabela mostra o nome amigável.
3. Criar outra opção com o mesmo texto na mesma chave; confirmar que é criada
   sem substituir a primeira.
4. Criar uma linha através de **Selecionar Matéria-Prima**; confirmar que o
   campo **Opção** fica preenchido com a descrição e que não aparece qualquer
   campo de código técnico.
5. Editar o nome de uma linha existente; confirmar que resolução e custeio
   continuam a selecionar a mesma opção técnica.
6. Importar o modelo para o ValueSet do orçamento e depois para o ValueSet do
   item; confirmar que o nome amigável aparece nos três níveis.
7. Repetir a criação/edição no orçamento e no item, confirmando a mesma regra.
