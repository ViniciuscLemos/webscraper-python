# Web Scraper de Livros

![Testes](https://github.com/ViniciuscLemos/webscraper-python/actions/workflows/testes.yml/badge.svg)

Scraper em Python que coleta livros do [books.toscrape.com](https://books.toscrape.com), um site feito justamente pra treinar scraping. Ele pega título, preço, avaliação, disponibilidade e categoria, salva os dados e mostra um resumo no final.

Usei requests e BeautifulSoup. Os dados podem ir pra um PostgreSQL ou só pra um arquivo CSV/JSON.

## Rodando

```bash
python -m venv .venv
.venv\Scripts\activate        # no Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
```

Sem banco de dados, salvando em CSV:

```bash
python main.py --sem-banco
```

Com PostgreSQL:

```bash
psql -U postgres -c "CREATE DATABASE scraper_db;"
cp .env.example .env    # coloca a senha do seu Postgres
python main.py
```

Algumas opções:

```bash
python main.py --sem-banco --categorias 2 --paginas 1
python main.py --sem-banco --json output/livros.json
```

Por padrão ele espera 0.8s entre uma página e outra pra não sobrecarregar o site (dá pra mudar com `--delay`). Se uma requisição falhar, ele tenta de novo algumas vezes antes de desistir.

## Testes

```bash
python -m unittest discover -s tests
```

Os testes usam um HTML salvo no próprio teste, então não acessam a internet.

## Arquivos

```
main.py             fluxo principal e opções de linha de comando
src/scraper.py      requisições e leitura do HTML
src/banco.py        parte do PostgreSQL
src/exportar.py     CSV, JSON e o resumo
```

Se for usar a ideia em outro site, dá uma olhada no `robots.txt` e nos termos de uso dele antes.
