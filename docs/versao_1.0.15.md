# Martelo V3 — 1.0.15

- Análise da Lista Material com validação Woodstore, sem bloquear Cut-Rite.
- Custos de placas, orlas, ferragens e produção com preços guardados por análise.
- Associações de matérias-primas reutilizáveis e pesquisa por categoria.
- Consulta de tempos reais Streamlit por encomenda/modelo e oito setores.
- Relatório de custos no Excel, com duas casas decimais e pendências explícitas.
- Janela maior, divisão das tabelas ajustável e larguras guardadas por utilizador.
- Atalho «👤 As minhas obras» na Produção.

## Instalação

Fechar o Martelo antes de instalar. O instalador preserva a configuração local
existente e cada pessoa entra com a sua conta. O perfil lean não inclui a
pesquisa semântica por IA.

A base partilhada necessita da migração `20260908_111`. As permissões da nova
tabela de mapeamentos são preparadas pelo administrador com
`deploy/mysql_custo_mapeamentos.sql`, uma única vez na base, não em cada PC.
O administrador atribui o acesso à Análise da Lista Material nas permissões
dos utilizadores.

## Verificação

Confirmar a versão 1.0.15 ao abrir, testar o atalho de responsável na Produção
e seguir `docs/guiao_teste_analise_lista_material.md` para a análise e relatório.
O custo continua parcial enquanto faltarem preços, horas ou associações.
