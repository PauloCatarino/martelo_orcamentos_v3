# Martelo Orçamentos V3

Aplicação desktop para criação, custeio, validação e acompanhamento de orçamentos de mobiliário, com apoio à produção e consulta histórica do Martelo V2.

## Estado atual

O projeto encontra-se em fase de estabilização e preparação de uma versão candidata. As áreas principais disponíveis incluem:

- gestão de orçamentos, versões, itens e clientes;
- custeio por materiais, ferragens, operações e acabamentos;
- biblioteca de peças, módulos e ValueSets;
- dashboards de orçamentos e produção;
- auditoria avançada da saúde do custeio;
- consulta direta e apenas de leitura ao arquivo de orçamentos V2;
- gestão de produção e integração com dados PHC;
- persistência das preferências visuais das tabelas, incluindo larguras de colunas.

## Tecnologia

- Python 3.11 ou superior
- PySide6
- SQLAlchemy e Alembic
- MySQL/MariaDB
- pytest

## Instalação

Na raiz do projeto, criar e ativar o ambiente virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Copiar o ficheiro de exemplo e preencher apenas o `.env` local:

```powershell
Copy-Item .env.example .env
```

O `.env` contém credenciais locais e está excluído do Git. Nunca colocar palavras-passe reais no `.env.example`, README, código ou histórico Git.

## Base de dados V3

Configurar no `.env` a ligação principal indicada em `.env.example` e aplicar as migrações:

```powershell
python -m alembic upgrade head
```

Antes de uma atualização importante, criar uma cópia de segurança da base de dados:

```powershell
mysqldump -h <servidor> -u <utilizador> -p martelo_orcamentos_v3 > backup_martelo_v3_YYYYMMDD.sql
```

Guardar a cópia fora da pasta do repositório e confirmar que o ficheiro não está vazio.

## Consulta ao arquivo V2

O arquivo V2 é consultado diretamente e os seus dados não são importados para a base V3. Configurar no `.env` uma das opções documentadas no `.env.example`.

Recomendação de segurança: usar no V2 uma conta MySQL dedicada, com permissão `SELECT` apenas nas tabelas necessárias. A aplicação também bloqueia instruções de escrita e abre a sessão V2 em modo de leitura, mas as permissões da própria base de dados são a proteção principal.

## Iniciar a aplicação

```powershell
python -m app.main
```

Para criar um atalho sem terminal no menu Iniciar (e opcionalmente no Ambiente de Trabalho):

```powershell
.\scripts\instalar_atalho_martelo_v3.ps1
.\scripts\instalar_atalho_martelo_v3.ps1 -Desktop
```

O atalho usa o `pythonw.exe` do ambiente virtual e abre sempre o código desta pasta.

## Validação técnica

Executar a compilação e os testes antes de criar uma versão candidata:

```powershell
python -m compileall -q app scripts tests
python -m pytest -q
python -m alembic current
python -m alembic heads
git diff --check
```

Executar também a validação manual descrita em [docs/20_checklist_ux8_versao_candidata.md](docs/20_checklist_ux8_versao_candidata.md).

## Documentação

- [Índice da documentação](docs/00_indice.md)
- [Arranque rápido](docs/01_quick_start.md)
- [Arquitetura](docs/02_arquitetura.md)
- [Base de dados e migrações](docs/03_base_dados_migracoes.md)
- [Testes e qualidade](docs/06_testes_qualidade.md)
- [Checklist UX-8 e versão candidata](docs/20_checklist_ux8_versao_candidata.md)

## Preparação de uma versão

1. Confirmar a cópia de segurança da base V3.
2. Confirmar que `.env` e outros ficheiros sensíveis não estão no Git.
3. Aplicar e verificar as migrações.
4. Executar toda a bateria de testes.
5. Realizar o teste manual dos fluxos críticos.
6. Rever alterações pendentes e criar um commit de marco identificado.
7. Só depois gerar ou distribuir a versão candidata.
