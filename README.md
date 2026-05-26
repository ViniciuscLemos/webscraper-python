# Web Scraper de Livros — Python + PostgreSQL

Coleta dados de livros do site [books.toscrape.com](http://books.toscrape.com) (site público feito para praticar scraping), salva em PostgreSQL e gera relatórios com estatísticas.

## Tecnologias
- **Python 3.10+** — linguagem principal
- **requests** — requisições HTTP
- **BeautifulSoup4** — parsing de HTML
- **psycopg2** — driver PostgreSQL para Python
- **python-dotenv** — gerenciamento de variáveis de ambiente

## O que você vai aprender com este projeto
- Web scraping com requests + BeautifulSoup
- Navegação no DOM HTML: `find()`, `find_all()`, seletores CSS
- Paginação automática
- Rate limiting (delay entre requisições — boa prática)
- PostgreSQL com psycopg2: conexão, queries, transações
- Upsert: `ON CONFLICT DO UPDATE` — inserir ou atualizar
- `execute_values()`: inserção em lote (muito mais eficiente que loop)
- Dataclasses em Python
- Variáveis de ambiente com python-dotenv

## Pré-requisitos
- Python 3.10+
- PostgreSQL instalado e rodando
- Conexão com a internet (para acessar books.toscrape.com)

## Como rodar

### 1. Instale as dependências
```bash
pip install -r requirements.txt
```

### 2. Configure o banco de dados
```bash
psql -U postgres -c "CREATE DATABASE scraper_db;"
```

### 3. Configure as variáveis de ambiente
```bash
cp .env.example .env
# Edite o .env com suas credenciais do PostgreSQL
```

### 4. Execute
```bash
python main.py
```

O programa vai:
1. Conectar ao banco e criar as tabelas
2. Coletar as categorias disponíveis no site
3. Raspar livros de cada categoria (com delay entre páginas)
4. Salvar tudo no PostgreSQL com upsert
5. Exibir relatório com estatísticas

## O que é coletado por livro
- Título
- Preço (em libras £)
- Avaliação (1 a 5 estrelas)
- Disponibilidade (em estoque ou não)
- Categoria
- URL da página do livro

## Estrutura do projeto
```
main.py                 # Orquestração do fluxo completo
src/
├── __init__.py
├── scraper.py          # Coleta de dados (HTTP + BeautifulSoup)
└── banco.py            # Persistência no PostgreSQL
requirements.txt        # Dependências do projeto
.env.example            # Modelo de configuração
```

## Nota ética sobre web scraping
Este projeto usa books.toscrape.com, um site criado especificamente para praticar scraping. Para raspar outros sites, sempre verifique o arquivo `robots.txt` e os Termos de Serviço do site.
