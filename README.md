# Martelo Orçamentos V3

Fundação técnica inicial do Martelo Orçamentos V3.

Este projeto é novo e independente do Martelo V2. Nesta etapa existem apenas a estrutura base, configuração, ligação SQLAlchemy a MySQL, Alembic, logging, janela PySide6 mínima e testes de importação.

## Stack

- Python
- PySide6
- SQLAlchemy
- Alembic
- MySQL
- pytest
- python-dotenv

## Configuração

1. Copiar `.env.example` para `.env`.
2. Ajustar as variáveis `DB_*` para o MySQL local.
3. Em alternativa, definir `DATABASE_URL` diretamente.

## Ambiente virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## Instalar dependências

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Testes

```powershell
python -m pytest
```

## Executar aplicação

```powershell
python -m app.main
```

## Alembic

A configuração inicial do Alembic está em `alembic.ini` e `alembic/env.py`. O URL da base de dados é lido através das mesmas variáveis de ambiente da aplicação.

Ainda não existem tabelas de negócio, modelos de orçamentos, modelos de clientes, motor de custeio, migração do V2 ou interface final.
