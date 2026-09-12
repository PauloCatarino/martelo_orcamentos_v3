# Teste dos perfis de roupeiros de correr e copiar/colar

As calhas superiores/inferiores e puxadores continuam a ser custeados por UND.
O comprimento aplicado é distinto do comprimento comercial da matéria-prima.
As calhas U/H entram na seleção automática: também se compram à barra
(a calha U do catálogo vem em 2350 mm). Ficam de fora os rodízios e o
amortecedor, que se vendem à unidade e não têm comprimento comercial.

## Configuração

1. Confirmar a base indicada no topo da aplicação. A nova coluna
   `def_pecas.selecao_perfil` tem de existir nessa base, não apenas na base de
   desenvolvimento usada pelos testes/scripts. Na base real `martelo_v3`, a
   coluna foi acrescentada pontualmente em 12/09/2026; a revisão Alembic foi
   preservada em `20260908_111`, pois a migração intermédia de catálogos não
   fazia parte desta reparação. A migração `20260912_113` reconhece agora a
   coluna existente quando a cadeia for executada posteriormente.
2. Abrir a definição `CALHA_SUP_SISTEMA_CORRER` → **Regras**.
3. Em **Comp do cabeçalho**, introduzir `LM-40`. Em **Seleção do perfil**, manter
   **Automática para calhas sup/inf e puxadores de correr**. Guardar.
4. Repetir para `CALHA_INF_SISTEMA_CORRER`.
5. Abrir `PUXADOR_PORTA_CORRER` → **Regras**. Usar `HM-50` se essa for a folga
   pretendida para o sistema em teste. Guardar. Esta folga é configurável.
6. **Sem seleção por comprimento** desliga a regra na definição. **Selecionar
   perfil pelo comprimento** permite ativá-la noutra definição explicitamente.
7. Abrir **Orçamento 260912_01 → Itens → item 1 → Custeio → ValueSet**.
   Confirmar que as opções das chaves superior, inferior e puxador têm o
   **Comp MP** comercial preenchido e unidade **UND**, com preço por barra/perfil.

## Copiar a operação editada

1. Em **Orçamento 260912_01 → Itens → item 1 → Custeio**, selecionar a linha de
   montagem manual e abrir **Operações da peça…**.
2. Editar a operação para **17 minutos por unidade**, guardando a máquina
   escolhida e os restantes parâmetros usados no teste.
3. Selecionar a linha → botão direito → **Copiar (Ctrl+C)**.
4. Na linha de destino → botão direito → **Colar abaixo (Ctrl+V)**.
5. Abrir **Operações da peça…** na cópia: deve manter os 17 minutos, máquina,
   método, quantidade, descrição e estado ativo/inativo das operações locais.
6. Carregar em **Atualizar**: a cópia deve manter a operação editada e o custo
   correspondente. Editar a cópia não deve alterar a original.
7. Repetir com uma operação manual autónoma: por exemplo, 17 min × quantidade 2
   deve conservar **34 minutos totais** após copiar e atualizar.

## Verificação após a reparação dos menus vazios

1. **Configurações → Definições de Peças → Atualizar**: a lista deve voltar
   a mostrar as definições, sem «Não foi possível carregar».
2. **Orçamento 260912_01 → Itens → RP_01 → Custeio**: sair e voltar a entrar
   na página. Foram confirmadas por leitura 11 linhas para este item.
3. Abrir **A Minha Biblioteca de Peças**: devem aparecer as peças e as
   preferências já existentes. Não é necessário usar «Repor».
4. Se ainda aparecer um erro de carregamento, fechar e reabrir a aplicação,
   confirmando que o topo indica **BASE REAL · martelo_v3**.

A reparação acrescentou apenas a coluna de configuração. As contagens da
base real ficaram iguais: 139 definições e 11 856 linhas de custeio. As
consultas da aplicação passaram a carregar também as 136 peças ativas e as
108 opções de ValueSet do item RP_01. Não foram recalculados custos nesta
verificação de recuperação.

## Seleção das calhas

1. Nas linhas existentes, verificar **Comp = LM-40**. Se ainda não estiver,
   selecionar a linha e usar **Atualizar peça da biblioteca**, revendo a
   pré-visualização antes de aplicar, ou editar a fórmula localmente.
2. Com LM = **1505 mm**, carregar em **Atualizar**: **Comp real = 1465 mm**.
3. Abrir **Mat. default** na calha superior/inferior: as opções são da mesma
   chave. A menor calha que cobre 1465 mm aparece primeiro, como recomendada.
   Cada opção mostra comprimento comercial, sobra/falta, referência e preço.
4. Com várias opções, selecionar explicitamente uma. Até confirmar, o campo
   identifica o material atual; o seu custo continua a ser o desse material.
5. Com uma única opção adequada e unidade UND, **Atualizar** aplica-a
   automaticamente, desde que a linha não tenha uma escolha manual anterior.
6. Para testar a folga, usar LM = **2000 mm** num item/divisão de teste:
   **Comp real = 1960 mm**, sem um segundo desconto de 40 mm na seleção.
7. Com opções de 1800, 2000 e 2500 mm, esperar a ordem: **2000, 2500, 1800**.
   A de 1800 deve indicar **CURTA: faltam 160 mm**. Se todas forem curtas,
   a maior aparece primeiro, sem aplicação automática.
8. Uma opção sem Comp MP aparece como comprimento desconhecido e não deve ser
   aplicada automaticamente.
9. Escolher uma opção e aumentar LM até essa opção ficar curta: a escolha
   manual deve manter-se; em **Observações** e no tooltip do material deve
   aparecer a falta de comprimento.
10. Confirmar custo UND: uma calha de 18 €/UND, QT total = 1 e desperdício = 0%
    custa **18 €**, mesmo que seja cortada. Não deve ser multiplicada por 1,96 m.

## Puxadores e limites desta fase

- Com HM = **2618 mm** e Comp = `HM-50`, o comprimento necessário é **2568 mm**.
  A lista de puxadores deve seguir a mesma seleção pelo comprimento e custar UND.
- A quantidade de puxadores continua a ser a configurada na peça/associação;
  esta alteração não presume quantos puxadores existem por porta.
- H/U e rodízios mantêm o comportamento anterior. A conversão de H/U para ML,
  incluindo conversão do preço por barra para preço por metro, fica para a fase
  em que forem definidas as regras de aplicação por porta.
- Nenhuma opção curta é bloqueada: o utilizador pode escolhê-la deliberadamente,
  mantendo o aviso dimensional visível.
- A regra consulta o ValueSet do item; não importa automaticamente opções do PHC
  nem altera o catálogo de matérias-primas.
