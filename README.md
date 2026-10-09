# Book Web Scraper

![Tests](https://github.com/ViniciuscLemos/webscraper-python/actions/workflows/tests.yml/badge.svg)

A Python scraper that collects books from [books.toscrape.com](https://books.toscrape.com), a site made exactly for practicing scraping. It grabs the title, price, rating, availability and category, saves the data and shows a summary at the end.

I used requests and BeautifulSoup. The data can go to PostgreSQL or just to a CSV/JSON file.

## Running

```bash
python -m venv .venv
.venv\Scripts\activate        # on Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
```

Without a database, saving to CSV:

```bash
python main.py --no-db
```

With PostgreSQL:

```bash
psql -U postgres -c "CREATE DATABASE scraper_db;"
cp .env.example .env    # put your Postgres password in it
python main.py
```

Some options:

```bash
python main.py --no-db --categories 2 --pages 1
python main.py --no-db --category Poetry --category Travel
python main.py --no-db --json output/books.json
```

`--category` uses the name shown in the site's menu (case doesn't matter) and can be repeated. Without it, the scraper takes the first categories in the menu.

The CSV is saved with a BOM, so you can open it straight in Excel without the £ turning into a weird character.

By default it waits 0.8s between pages so it doesn't overload the site (you can change it with `--delay`). If a request fails, it retries a few times before giving up.

## Sample output

Running `python main.py --no-db --category Poetry --category Travel --pages 1`, the report at the end looks like this:

```
==================================================
  REPORT OF THE SCRAPED BOOKS
==================================================
  Total books:     30
  Average price:   £37.38
  Cheapest:        £14.19
  Most expensive:  £57.31

  Category                   Books    Avg Price
  ---------------------------------------------
  Poetry                        19       £35.97
  Travel                        11       £39.79

  Top 5 cheapest with 5 stars:
  1. ★★★★★ £15.42 - The Collected Poems of W.B. Yeats (The C
  2. ★★★★★ £17.49 - Booked
  3. ★★★★★ £26.08 - 1,000 Places to See Before You Die
  4. ★★★★★ £29.04 - Les Fleurs du Mal
  5. ★★★★★ £50.89 - Quarter Life Poetry: Poems for the Young

==================================================
```

## Tests

```bash
python -m unittest discover -s tests
```

The tests use HTML written inside the test itself, so they don't hit the internet.

## Files

```
main.py             main flow and command line options
src/scraper.py      requests and HTML parsing
src/database.py     the PostgreSQL part
src/export.py       CSV, JSON and the summary
```

If you want to use the idea on another site, take a look at its `robots.txt` and terms of use first.
