# Fase 6 — Categorias e gestão da Biblioteca de Módulos

As categorias dos módulos deixaram de ser fixas: passam a viver na nova tabela
`def_modulo_categorias` (migração `20260729_68`, aditiva), com um nível único —
o nome de um cliente é uma categoria válida. Regras:

- A migração faz seed de **Roupeiros, Cozinhas, Móveis WC e Outros** e importa
  qualquer código de categoria já usado por módulos existentes; os módulos
  antigos são preservados sem alteração (continuam ligados por código).
- **Gerir Categorias…** (Configurações → Biblioteca de Módulos): criar,
  renomear (o código mantém-se estável), **arquivar/reativar** (sai das
  escolhas, módulos antigos mantêm-na) e **eliminar segura** — recusada quando
  a categoria está em uso; **Outros** é a categoria de recurso e está
  protegida contra arquivar/eliminar.
- Todos os seletores de categoria (Biblioteca, Guardar como Módulo, Importar
  Módulo, Editar Módulo) passam a mostrar as categorias geridas.
- **Permissões** (editar, eliminar, converter): módulos **Global** são geridos
  apenas pelo administrador; módulos **Utilizador** pelo próprio dono ou pelo
  administrador.
- **Converter Âmbito** (novo botão na Biblioteca): converte um módulo entre
  Utilizador e Global, de forma **reversível** — voltar a Utilizador atribui o
  módulo a quem converte.

## Roteiro manual

1. Execute `python -m alembic upgrade head` e confirme `20260729_68 (head)`.
2. Abra **Configurações → Biblioteca de Módulos** e clique **Gerir
   Categorias…**. Confirme as 4 categorias iniciais ativas.
3. Crie uma categoria com o nome de um cliente (ex.: `Cliente Silva`).
   Confirme o código `CLIENTE_SILVA` na tabela.
4. No custeio de um item, selecione linhas e use **Guardar como Módulo**;
   escolha a categoria `Cliente Silva` e grave.
5. Na Biblioteca, filtre por `Cliente Silva` e confirme que só esse módulo
   aparece. Use **Importar Módulo** noutro item e confirme o mesmo filtro.
6. Em **Gerir Categorias…**, tente **Eliminar** `Cliente Silva` → deve ser
   recusado por estar em uso. Use **Arquivar**: a categoria sai das escolhas,
   mas o módulo mantém-na na lista. **Reativar** volta a mostrá-la.
7. Edite o módulo e confirme que a categoria arquivada continua selecionável
   nesse módulo.
8. Com o seu utilizador (admin), selecione o módulo e use **Converter
   Âmbito** para Global; confirme que muda de separador. Converta de volta
   para Utilizador e confirme que volta a ser seu.
9. Com um utilizador NÃO administrador: no separador Global, tente Editar /
   Eliminar / Converter um módulo → aviso "Sem permissão…". No separador
   Utilizador, o próprio consegue gerir os seus módulos.
10. Tente arquivar ou eliminar a categoria **Outros** → deve ser recusado.
