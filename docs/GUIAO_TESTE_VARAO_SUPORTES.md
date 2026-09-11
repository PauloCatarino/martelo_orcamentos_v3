# Varão SPP e suportes — validação

Código corrigido na pasta principal, branch `main`. Reiniciar a aplicação.

## O que foi corrigido

- A regra constante `VARAO_SPP = 1` não exige dimensões desnecessárias. Num conjunto só de ferragens, o próprio varão com comprimento pode ser a referência.
- O consumo ML volta a ser calculado a partir das dimensões atuais em cada atualização. O resultado anterior não fixa o consumo quando muda LM. Um consumo antigo só é usado como alternativa em linhas sem dimensões nem fórmulas dimensionais.
- Na base real `martelo_v3`, as duas prateleiras passaram a ter suporte central com `SUPORTE_VARAO_CENTRAL` e suporte lateral com `SUPORTE_TERMINAL_VARAO`. As restantes associações e os ValueSets foram preservados.
- Os scripts de criação das duas prateleiras também foram corrigidos para futuras instalações. A função de reparação está em `scripts/corrigir_suportes_prateleiras.py`; a segunda aplicação não altera nada.
- Não foram recalculados nem modificados os itens 1 e 2 de `260887_01`. O item 1 permanece como comparação; os cálculos corrigidos aplicam-se quando o utilizador atualiza o custeio.

## 1. Catálogo

1. Abrir **Configurações → Definições de peças** e abrir `PRAT_AMOV[2111]+SUP_PRAT+VARAO+SUP_VARAO`.
2. No separador **Associados**, clicar em **Atualizar**.
3. Confirmar os associados da prateleira e os três do varão: `VARAO`, `SUPORTE_CENTRAL_VARAO`, `SUPORTE_LATERAL_VARAO`.
4. Confirmar regra do central **SUPORTE_VARAO_CENTRAL** e regra do lateral **SUPORTE_TERMINAL_VARAO**.
5. Repetir em `PRAT_FIXA[2000]+VARAO+SUP_VARAO`.

## 2. Novas inserções no item 2

1. Abrir **Orçamentos → 260887_01 → Items → item 2 → Custeio**. Não atualizar o item 1, para manter a comparação original.
2. Na divisão independente de teste, manter **QT mod = 1** e **Larg = L/3*2** (item com largura 1750 mm, logo LM = 1166,667 mm).
3. A partir da biblioteca, inserir cada uma destas composições e expandir os associados:
   - `VARAO+SUPORTES`;
   - `PRAT_AMOV[2111]+SUP_PRAT+VARAO+SUP_VARAO`;
   - `PRAT_FIXA[2000]+VARAO+SUP_VARAO`.
4. Clicar em **Atualizar**. Em cada composição, esperar **1 varão**, **1 suporte central** e **2 suportes laterais**. Os outros associados das prateleiras devem continuar presentes.
5. Confirmar que desaparece o aviso crítico de dimensões em falta da regra `VARAO_SPP`.
6. Confirmar **Comp real = 1166,667 mm** e **SPP ML und aproximadamente 1,167 m**; na base o consumo é guardado com quatro casas decimais. Os custos usam os preços dos ValueSets atuais.

Os grupos inseridos anteriormente mantêm a configuração guardada no orçamento. **Atualizar** recalcula medidas e custos, mas não acrescenta automaticamente associados novos do catálogo. Para comparar o catálogo corrigido, usar novas inserções; para adaptar grupos antigos, usar o fluxo explícito **Atualizar peça da biblioteca**, revendo a confirmação apresentada pela aplicação.

## 3. Mudança de comprimento e limiar do suporte central

1. Na linha da divisão independente de teste, mudar **Larg** para **1000** e clicar em **Atualizar**: varão com **1000 mm**, **SPP ML und = 1 m**, central com quantidade **0**, laterais com quantidade **2**.
2. Mudar **Larg** para **1100** e atualizar: **1,1 m**, central **0**, laterais **2**.
3. Mudar **Larg** para **1200** e atualizar: **1,2 m**, central **1**, laterais **2**.
4. Voltar a **1000** e atualizar: o consumo deve voltar a **1 m**, não ficar no valor calculado anteriormente.
5. Repor **Larg = L/3*2** quando terminar.

## Cópia anterior do catálogo

Antes da alteração foi guardado um JSON dos associados das duas prateleiras em:
`C:\Users\UTILIZ~1\AppData\Local\Temp\martelo_suportes_antes_20260911_125625_563801.json`.

A verificação automática confirmou que as linhas de custeio dos itens 1 e 2 permaneceram iguais durante a correção do catálogo.
