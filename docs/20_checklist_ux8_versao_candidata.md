# UX-8 — Estabilização e preparação de versão

Data da revisão: 12 de julho de 2026

## Objetivo

Preparar o Martelo Orçamentos V3 para uma versão candidata controlada, sem alterar dados funcionais nem introduzir novas funcionalidades nesta fase.

## Estado funcional

As fases UX-1 a UX-7 estão implementadas. Durante a validação funcional foram aprovados, entre outros:

- painel inicial e dashboard;
- listagens visuais de orçamentos;
- auditoria avançada de custeio e indicador de saúde;
- consulta apenas de leitura ao arquivo V2;
- introdução de arranque;
- atualização de várias peças selecionadas a partir da biblioteca, incluindo linhas importadas de módulos.

## Checklist automática

- [x] Compilação de `app`, `scripts` e `tests` sem erros.
- [x] Bateria completa: **2061 testes aprovados em 11,27 segundos**.
- [x] Migração ativa coincide com a cabeça Alembic: `20260721_60`.
- [x] `git diff --check` sem erros de espaços ou conflitos.
- [x] `.env` local ignorado pelo Git.
- [x] `.env.example` sem credenciais reais.

Validação automática executada com sucesso em 12 de julho de 2026.

## Checklist manual da versão candidata

- [ ] Iniciar com `python -m app.main` e confirmar a introdução de aproximadamente 3 segundos.
- [ ] Autenticar e terminar sessão.
- [ ] Abrir o painel inicial e testar pesquisa e filtros.
- [ ] Criar, editar, duplicar para versão e abrir um orçamento.
- [ ] Abrir um item, recalcular o custeio e guardar.
- [ ] Atualizar várias peças selecionadas a partir da biblioteca.
- [ ] Confirmar a saúde do orçamento, incluindo observações de produção incompletas.
- [ ] Abrir a Auditoria de Custeio e testar severidade, categoria e utilizador.
- [ ] Abrir o Arquivo V2, pesquisar e filtrar sem qualquer alteração na base V2.
- [ ] Abrir as páginas de produção e confirmar o comportamento quando uma fonte externa está indisponível.
- [ ] Redimensionar colunas, reiniciar a aplicação e confirmar a persistência das larguras.
- [ ] Desativar um registo e confirmar que fica oculto; testar a opção para mostrar ocultos.

## Segurança e dados

- O `.env` não deve ser enviado, anexado nem incluído num commit.
- A conta de acesso ao arquivo V2 deve ter apenas permissões `SELECT`.
- A proteção de leitura da aplicação é uma segunda camada e não substitui permissões restritas no servidor MySQL.
- Não executar testes manuais destrutivos numa base de produção sem uma cópia de segurança confirmada.

## Cópia de segurança

Antes de instalar a versão candidata:

1. criar um dump completo da base V3;
2. confirmar que o ficheiro gerado tem conteúdo;
3. guardar uma cópia fora do computador de desenvolvimento;
4. registar a data, a versão da aplicação e a revisão Git associada;
5. validar periodicamente que a cópia pode ser restaurada num ambiente de teste.

## Riscos conhecidos antes da versão candidata

1. A conta atualmente configurada para consulta ao V2 pode ter permissões de escrita no servidor. Deve ser substituída por uma conta dedicada apenas de leitura.
2. Existe um conjunto alargado de alterações locais ainda não consolidado num commit de marco. Deve ser revisto antes da distribuição.
3. As integrações de produção dependem de fontes externas; deve ser validado o comportamento online e indisponível no ambiente real.
4. A cópia de segurança da base V3 deve ser confirmada pelo responsável antes da instalação.

## Critério de aprovação

A versão candidata fica pronta quando:

- todos os testes automáticos passam;
- a migração da base de dados está atualizada;
- o checklist manual crítico está validado;
- existe uma cópia de segurança confirmada;
- a conta V2 está limitada a leitura;
- as alterações são revistas e consolidadas num commit identificado.

Não é criado automaticamente qualquer commit, tag ou pacote de distribuição durante esta fase.
