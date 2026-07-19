# Guião de teste — CNC e revestimento sandwich

Este guião destina-se ao worktree `claude/cnc-operations-costing-380317` e a
uma base de dados de desenvolvimento. Não usar a base de produção nem integrar
no `main` antes de todos os cenários estarem validados.

## Preparação única da base de desenvolvimento

1. Confirmar que a aplicação está fechada e que o `.env` aponta para a base de
   desenvolvimento.
2. A partir deste worktree, correr `alembic upgrade head`.
3. Correr, por esta ordem:

   ```powershell
   python -m scripts.create_default_operacoes
   python -m scripts.seed_tarifas_maquinas
   python -m scripts.seed_tarifas_producao_reais
   python -m scripts.create_default_pecas_sandwich
   ```

4. Arrancar a aplicação com `python -m app.main`.

> A migração substitui as operações genéricas `CNC_MECANIZACAO` e `CNC_RASGO`,
> e limpa snapshots antigos de operações. Isto é esperado e foi autorizado
> apenas para o ciclo de testes de desenvolvimento.

## Valores de referência

| Máquina | Métodos permitidos | Tarifas usadas nos exemplos |
| --- | --- | --- |
| CNC ABD | Área, Tempo, Furação | 30 €/h; 0,10 €/furo STD; 0,07 € SÉRIE |
| CNC Vertical | Área, Tempo, Furação, Rasgo, Pocket | 60 €/h; 0,12 €/furo STD; 0,40 €/ML de rasgo |
| CNC Sandwich | Área, Tempo, Furação, Rasgo | 60 €/h; 0,10 €/furo STD; 0,40 €/ML de rasgo |
| CNC 5 Eixos | Área, Tempo, Furação, Rasgo, Pocket | 90 €/h; 0,15 €/furo STD; 0,40 €/ML de rasgo |
| Revestimento Sandwich | Revestimento | 3,25 €/m² por face, STD e SÉRIE |

Os escalões CNC de exemplo são: até 0,25 m² = 1,20 € STD / 0,90 € SÉRIE;
até 0,50 m² = 1,80 € / 1,35 €; até 1,00 m² = 2,60 € / 1,95 €; até 2,00 m² =
3,80 € / 2,85 €; sem limite = 5,50 € / 4,10 €.

## Cenário 1 — Configuração das máquinas

1. Abrir `Configurações` → `Operações / Máquinas / Simulador` → separador
   `Máquinas`.
2. Abrir `CNC ABD` e confirmar que Rasgos e Pocket estão desmarcados.
3. Abrir `CNC Sandwich` e confirmar que Pocket está desmarcado, mas Rasgos,
   Furação e Escalões de área estão marcados.
4. Abrir `Revestimento Sandwich` e confirmar que apenas aparecem as duas
   tarifas `€/m² por face`.

Resultado esperado: as capacidades e tarifas coincidem com a tabela de
referência. Todos os campos editáveis têm tooltip.

## Cenário 2 — Simulador: furação + rasgo somados

1. Em `Configurações` → `Operações / Máquinas / Simulador`, abrir o separador
   `Simulador`.
2. Escolher `CNC Vertical`; introduzir Comprimento `800`, Largura `600` e
   Quantidade `2`.
3. Escolher método `Furação`, indicar `8` furos por unidade e premir
   `Adicionar operação`.
4. Escolher método `Rasgo`, indicar `0` rasgos ao comprimento e `1` à largura;
   voltar a adicionar.

Resultado esperado: furação = `8 × 2 × 0,12 = 1,92 €`; rasgo =
`0,600 ML × 2 × 0,40 = 0,48 €`; total STD = **2,40 €**. A tabela mostra as
duas fórmulas abertas e os totais STD/SÉRIE lado a lado.

## Cenário 3 — Simulador: capacidade bloqueada

1. No mesmo separador, escolher `CNC ABD`.
2. Abrir a lista de métodos.

Resultado esperado: aparecem Área, Tempo e Furação. `Rasgo` não aparece.
Isto confirma que a máquina, e não o nome da operação, controla os métodos
disponíveis.

## Cenário 4 — Simulador: revestimento

1. Escolher `Revestimento Sandwich`; introduzir Comprimento `2000`, Largura
   `1000` e Quantidade `1`.
2. Escolher `1 face` e adicionar a operação.
3. Limpar; escolher `2 faces` e adicionar novamente.

Resultado esperado: 1 face = `2,000 m² × 1 × 3,25 = 6,50 €`; 2 faces =
`2,000 m² × 2 × 3,25 = 13,00 €`.

## Cenário 5 — Peça e ValueSet: método na associação

1. Abrir `Configurações` → `Definições de Peças`, pesquisar uma peça de teste
   ou `FACE_SANDWICH` e abrir a aba `Operações`.
2. Criar/editar a operação `REVESTIMENTO_SANDWICH`.
3. Confirmar que o formulário mostra `Método de cálculo = Revestimento` e
   `N.º de faces (1 ou 2)`, sem campos de tempo nem de rasgo.
4. Numa linha ValueSet de uma dobradiça, associar `CNC ABD` e escolher o
   método `Furação`; indicar `3` furos por unidade.

Resultado esperado: cada associação guarda o método. Na furação não são
mostrados os campos de tempo; no revestimento o número de faces é configurado
pela quantidade base. Em ambos os ecrãs a tabela passa a ter a coluna
`Método`.

## Cenário 6 — Custeio de uma operação local

1. Abrir `Orçamentos` → orçamento de teste → `Itens` → selecionar um item →
   `Custeio do Item`.
2. Numa linha de peça, abrir `Operações` e adicionar uma operação local
   `CNC Vertical` com método `Rasgo`, uma vez ao comprimento.
3. Definir Comp `1200`, Larg `80`, QT `1` e recalcular o item.

Resultado esperado: `custo_cnc = 1,200 ML × 0,40 = 0,48 €`; a operação aparece
no detalhe/auditoria da linha com o método Rasgo. Não deve surgir uma operação
de catálogo chamada `CNC_RASGO`.

## Cenário 7 — Painel sandwich composto

1. No mesmo custeio, abrir a biblioteca de peças e inserir
   `PAINEL_SANDWICH_2F`.
2. Definir Comp `2000`, Larg `1000`, Esp `19` e QT `1`; recalcular.
3. Expandir a peça composta.

Resultado esperado:

- existe um cabeçalho composto sem custo próprio;
- existem duas linhas `FACE_SANDWICH` com espessura `0,8` e uma linha
  `NUCLEO_SANDWICH` com espessura `17,4`;
- cada face mostra `Custo revestimento = 6,50 €`;
- o custo de revestimento das duas faces soma **13,00 €** no custo de produção;
- o núcleo mantém o seu material ValueSet separado.

Repetir com `PAINEL_SANDWICH_1F`: devem existir uma face `0,8` e núcleo `18,2`;
o revestimento total é **6,50 €**.

## Cenário 8 — STD versus SÉRIE e regressão

1. No simulador, escolher `CNC Sandwich`, Comp `600`, Larg `400`, QT `20` e
   modo `SÉRIE`.
2. Adicionar Escalões de área e Furação com `6` furos por unidade.
3. Confirmar que ambos os totais continuam visíveis e que o destaque está em
   SÉRIE.
4. Criar ou abrir uma peça simples em `Custeio Simplificado`, com corte e
   orlagem, e recalcular.

Resultado esperado: para a CNC Sandwich, escalão SÉRIE = `0,90 × 20 = 18,00 €`
e furação SÉRIE = `0,06 × 6 × 20 = 7,20 €`, total SÉRIE = **25,20 €**. O
custeio simplificado continua a calcular apenas corte/orlagem como antes.

## Validação adicional — correções de teste

1. No separador `Simulador`, escolher `CNC Vertical` e depois `CNC 5 Eixos`.
   Em ambos, confirmar que a lista de métodos inclui `Pocket (minutos ×
   custo/hora da máquina)`. Introduzir `4` em `Min/unidade`, `1` pocket e QT
   `1`: na CNC Vertical o custo deve ser **4,00 €**; na CNC 5 Eixos deve ser
   **6,00 €**. CNC ABD e CNC Sandwich não devem mostrar Pocket.
2. Confirmar a zona `Peça em análise`: os campos estão compactos à esquerda.
   Escrever valores e usar Enter: Comprimento → Largura → Quantidade → Modo.
3. Em `Configurações` → `Definições de Peças`, abrir uma peça composta e a aba
   `Regras`. Selecionar uma linha em `Transformações dimensionais dos
   associados`: o fundo passa a bege e o texto mantém-se escuro e legível.
4. No `Custeio do Item`, selecionar uma peça com `Comp MP`/`Larg MP` preenchidos.
   Introduzir, por exemplo, Comp `2800` para uma placa Comp MP `2750`.
   Confirmar que surge o aviso; ao escolher `Registar mesmo assim`, a medida é
   guardada e o custeio continua a funcionar. Ao escolher `Cancelar`, a medida
   anterior mantém-se. Repetir para Larg. O aviso informa que a peça não entra
   no plano de corte, mas não altera os cálculos.

## Registo da validação

Para cada cenário, anotar `OK`, `NOK` ou `a decidir`, incluindo captura de
ecrã e valor obtido. Só depois dos oito cenários estarem `OK` se deve decidir
a integração deste worktree no `main`; o push para GitHub continua a ser uma
decisão separada.
