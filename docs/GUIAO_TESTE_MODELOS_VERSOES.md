# Validação — Os Meus Orçamentos e Modelo/Versão

Alterações na pasta principal, branch `main`. Reiniciar a aplicação a partir dessa pasta.

## 1. Orçamentos

1. Entrar com o utilizador habitual e abrir **Orçamentos**.
2. Marcar **👤 Os Meus Orçamentos**.
3. Confirmar que **Utilizador** passa para o utilizador atual e a tabela mostra os seus orçamentos.
4. Desmarcar: **Utilizador** deve voltar a **Todos**.
5. Marcar novamente e clicar em **Limpar filtros**: a seleção deve desaparecer e a lista voltar ao conjunto completo.
6. Selecionar manualmente outro utilizador: o atalho não deve continuar marcado.

## 2. Nomes e sugestões na Produção

1. Abrir **Produção**, selecionar uma obra e confirmar os campos e colunas **Modelo** e **Versão**.
2. Clicar em **Novo Modelo/Versão**.
3. Confirmar os campos **MODELO no IMOX IX** e **Versão CUT-RITE**. Os botões devem aparecer por esta ordem: **Sugestão Modelo | Sugestão Versão**.
4. **Sugestão Versão** mantém o modelo da obra selecionada e sugere uma versão livre.
5. **Sugestão Modelo** sugere um modelo livre, com versão **01**.
6. A árvore mantém as pastas existentes e inclui **Registos no Streamlit (com ou sem pasta)** quando houver registos externos.

As sugestões consideram ano + encomenda no Martelo, nas pastas e no Caderno de Encargos do Streamlit. As encomendas especiais `_NNN` consultam a tabela externa correspondente.

## 3. Duplicados sem pasta

1. Escolher uma encomenda que tenha no Streamlit um modelo/versão guardado, mas sem pasta criada.
2. No Martelo, abrir **Produção → selecionar a obra → Novo Modelo/Versão**.
3. Introduzir exatamente esse **Modelo** e essa **Versão**.
4. Deve aparecer um aviso a mencionar o **Streamlit** e o botão **Criar** deve ficar desativado.
5. Confirmar que a combinação aparece na árvore dos registos externos, apesar de não existir na árvore das pastas.
6. Clicar em **Cancelar**.

A aplicação volta a consultar os registos ao clicar em Criar. Se a consulta ao Streamlit falhar, bloqueia a criação e apresenta um aviso; não assume que uma falha significa ausência de registos.

## 4. Datas herdadas

Usar uma obra de teste, pois o último passo cria efetivamente um processo e a respetiva pasta.

1. Em **Produção**, selecionar a obra de teste.
2. Preencher **Data Início = 10-09-2026** e **Data Entrega = 18-09-2026** e clicar em **Salvar**.
3. Abrir **Novo Modelo/Versão**, clicar em **Sugestão Modelo** e confirmar que não há conflito.
4. Clicar em **Criar**.
5. No processo criado, confirmar **Data Início = 10-09-2026** e **Data Entrega = 18-09-2026**.
6. Repetir com **Sugestão Versão** para verificar a herança dentro do mesmo modelo.

As datas vazias na origem continuam vazias: não se inventa uma data de entrega.

## 5. Descrição no Ponto Situação

1. Em **Produção**, selecionar uma obra com **Descrição produção** preenchida e tomar nota do texto.
2. Abrir **Produção → Ponto Situação → Estado de Produção** e clicar em **Atualizar estado**.
3. Localizar o mesmo processo: imediatamente à direita de **Ref Cliente** deve aparecer **Descrição da Produção**, com o texto dessa obra.
4. Passar o rato sobre a célula para consultar o texto completo na dica. Obras sem descrição devem apresentar a célula vazia.
5. Confirmar que **Responsável**, **Estado**, **Preço**, **% Global** e os setores continuam alinhados com os respetivos cabeçalhos.

## 6. Total no email do orçamento

1. Abrir **Orçamentos**, selecionar um orçamento com total superior a mil euros e abrir o fluxo habitual de envio por email ao cliente.
2. Na pré-visualização do corpo do email, confirmar a separação dos milhares: **24254,60 €** deve aparecer como **24 254,60 €**; **1234,50 €** como **1 234,50 €**.
3. Confirmar que a indicação do IVA continua presente e que o número do orçamento não foi alterado.
4. Cancelar a janela: não é necessário enviar um email para validar esta formatação. A alteração aplica-se ao corpo dos novos emails gerados, não ao histórico já enviado.

## 7. As minhas obras no Ponto Situação

1. Entrar com o utilizador habitual e abrir **Produção → Ponto Situação → Resumo**.
2. Marcar **👤 As minhas obras**, junto ao filtro **Utilizador**. Este deve passar para o responsável correspondente ao utilizador atual; os totais, gráficos e obras atrasadas devem refletir esse filtro.
3. Abrir **Estado de Produção**: o atalho deve continuar marcado e a tabela deve mostrar as obras do mesmo responsável.
4. Desmarcar o atalho nesse separador: **Utilizador** deve voltar a **Todos** e a tabela deve ser atualizada. Regressar ao **Resumo** e confirmar os totais sem esse filtro.
5. Selecionar manualmente o próprio responsável e depois outro: o atalho deve acompanhar a seleção, marcando e desmarcando respetivamente.
6. Marcar novamente e clicar em **Limpar filtros**: o atalho deve ficar desmarcado nos dois separadores.
7. Caso o utilizador não corresponda a nenhum responsável da lista, o atalho deve ficar desmarcado e apresentar um aviso na linha de estado.

## Verificação e limites

- Os testes automatizados cobrem sugestões com registos externos sem pasta, conflito surgido depois de abrir a janela, indisponibilidade do Streamlit, herança das datas e pasta criada entretanto.
- Foi executado SELECT na ligação Streamlit configurada: **1550/2026** devolveu **01/01**. Para **1551**, foi encontrado **01/01 em 2025**, mas nenhum registo em 2026 nessa ligação. Uma ficha visível no Streamlit pode ainda não estar guardada; também convém confirmar que ambos usam a mesma base configurada.
- Não foram criados processos nem pastas na produção durante a verificação do agente. A validação visual completa na aplicação fica a cargo deste guião.
- A nomenclatura visível foi alterada. Os identificadores internos, nomes de pastas existentes e formato do código Processo mantêm compatibilidade. O nome do plano continua a representar encomenda/modelo/versão/ano/cliente.
- A verificação externa é só de leitura e não reserva números no Streamlit. A revalidação deteta registos criados desde a abertura da janela, mas não é uma transação conjunta entre as duas aplicações.
