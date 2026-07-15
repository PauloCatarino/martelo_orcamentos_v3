# Fase 4 — Perfis de margens

As margens continuam copiadas para cada versão de orçamento e podem ser
alteradas localmente. O novo campo **Perfil** apenas define que conjunto será
usado por **Repor Padrão**:

- **Standard** (predefinido);
- **Cliente Final**, um perfil único partilhado;
- **Por Cliente**, usando a ficha do cliente do orçamento quando exista uma
  margem ativa, com fallback seguro para Standard.

Os antigos registos `UTILIZADOR` são preservados na base de dados para
histórico, mas deixam de ser apresentados ou usados na resolução de novos
perfis. Versões existentes mantêm os seus valores efetivos de margem e ficam
marcadas como Standard para futuros resets, sem alteração silenciosa de preço.

## Roteiro manual

1. Execute `python -m alembic upgrade head` e confirme `20260727_66 (head)`.
2. Em **Configurações > Margens por Defeito**, abra **Cliente Final**, grave um
   conjunto diferente de Standard e confirme que só existe um formulário.
3. Crie um orçamento novo: o seletor de margens inicia em Standard e mostra
   Cliente Final quando este perfil estiver configurado.
4. Num orçamento existente, abra **Items**. Escolha cada opção do seletor
   **Perfil** e confirme que a escolha é mantida ao recarregar a página.
5. Para cada perfil, clique **Repor Padrão** e confirme que as cinco margens e
   os preços são recalculados. Em Por Cliente sem margem específica, confirme
   o fallback para Standard.
6. Edite manualmente uma margem no painel do orçamento, recarregue e confirme
   que a edição local permanece até escolher explicitamente Repor Padrão.
