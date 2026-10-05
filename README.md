# Web Scraper de Livros — Python + PostgreSQL

![Testes](https://github.com/ViniciuscLemos/webscraper-python/actions/workflows/testes.yml/badge.svg)

Coleta dados de livros do site [books.toscrape.com](https://books.toscrape.com) (site público feito para praticar scraping), salva em PostgreSQL — ou em CSV/JSON, sem precisar de banco — e gera relatórios com estatísticas.

## Tecnologias
- **Python 3.10+** — linguagem principal
- **requests** — requisições HTTP (com sessão e retry automático)
- **BeautifulSoup4** — parsing de HTML
- **psycopg2** — driver PostgreSQL para Python
- **python-dotenv** — gerenciamento de variáveis de ambiente
- **unittest** + **unittest.mock** — testes sem acessar a internet

## O que você vai aprender com este projeto
- Web scraping com requests + BeautifulSoup
- Navegação no DOM HTML: `find()`, `find_all()`, classes CSS
- Paginação automática e resolução de links relativos com `urljoin`
- Rate limiting (delay entre requisições — boa prática)
- Retry com backoff exponencial para falhas temporárias (429/5xx)
- PostgreSQL com psycopg2: conexão, queries, transações
- Upsert: `ON CONFLICT DO UPDATE` — inserir ou atualizar
- `execute_values()`: inserção em lote (muito mais eficiente que loop)
- Dataclasses em Python, exportação para CSV/JSON
- Testes com HTML de exemplo e `mock.patch`

## Pré-requisitos
- Python 3.10+
- Conexão com a internet (para acessar books.toscrape.com)
- PostgreSQL instalado e rodando — **opcional**, veja o modo `--sem-banco`

## Como rodar

### 1. Instale as dependências
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

### 2a. Rodar sem banco (mais rápido para testar)
```bash
python main.py --sem-banco                       # salva em output/livros.csv
python main.py --sem-banco --json output/livros.json
```

### 2b. Rodar com PostgreSQL
```bash
psql -U postgres -c "CREATE DATABASE scraper_db;"
cp .env.example .env      # edite com suas credenciais
python main.py
```

O programa vai:
1. Conectar ao banco e criar as tabelas (ou pular, no modo sem banco)
2. Coletar as categorias disponíveis no site
3. Raspar livros de cada categoria (com delay entre páginas)
4. Salvar no PostgreSQL com upsert e/ou exportar para CSV/JSON
5. Exibir relatório com estatísticas

### Opções

| Opção | Padrão | O que faz |
|-------|--------|-----------|
| `--categorias N` | 4 | Quantas categorias coletar |
| `--paginas N` | 3 | Máximo de páginas por categoria |
| `--delay S` | 0.8 | Segundos entre uma página e outra |
| `--sem-banco` | — | Não usa PostgreSQL |
| `--csv ARQUIVO` | — | Exporta os livros para CSV |
| `--json ARQUIVO` | — | Exporta os livros para JSON |

## O que é coletado por livro
- Título
- Preço (em libras £)
- Avaliação (1 a 5 estrelas)
- Disponibilidade (em estoque ou não)
- Categoria
- URL da página do livro

## Testes
```bash
python -m unittest discover -s tests -v
```
Os testes usam HTML de exemplo com a mesma estrutura do site, então rodam offline e em milissegundos. Rodam também no GitHub Actions a cada push.

## Estrutura do projeto
```
main.py                 # Orquestração do fluxo e argumentos de linha de comando
src/
├── scraper.py          # Coleta de dados (HTTP + BeautifulSoup)
├── banco.py            # Persistência no PostgreSQL
└── exportar.py         # Exportação CSV/JSON e relatório sem banco
tests/
└── test_scraper.py     # Testes offline do parser, paginação e exportação
requirements.txt        # Dependências do projeto
.env.example            # Modelo de configuração
```

## Nota ética sobre web scraping
Este projeto usa books.toscrape.com, um site criado especificamente para praticar scraping. Para raspar outros sites, sempre verifique o arquivo `robots.txt` e os Termos de Serviço do site.
