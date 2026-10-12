"""Saves the books to CSV/JSON/HTML and shows the summary when there's no database."""

import csv
import json
import os
from collections import defaultdict
from dataclasses import asdict, fields
from html import escape
from statistics import mean

from src.scraper import Book


def shorten(text: str, size: int = 40) -> str:
    """Cuts long titles for the report, with … so it's clear something was cut."""
    return text if len(text) <= size else text[:size - 1].rstrip() + "…"


def remove_duplicates(books: list[Book]) -> list[Book]:
    seen = set()
    unique = []
    for book in books:
        if book.url not in seen:
            seen.add(book.url)
            unique.append(book)
    return unique


def export_csv(books: list[Book], path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    # utf-8-sig adds the BOM, otherwise Excel shows the £ broken
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=[c.name for c in fields(Book)])
        writer.writeheader()
        for book in books:
            writer.writerow(asdict(book))


def export_json(books: list[Book], path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(b) for b in books], f, ensure_ascii=False, indent=2)


def print_report(books: list[Book]) -> None:
    print(f"\n{'='*50}")
    print("  REPORT OF THE SCRAPED BOOKS")
    print(f"{'='*50}")

    if not books:
        print("  No books scraped.")
        print(f"{'='*50}")
        return

    prices = [b.price for b in books]
    print(f"  Total books:     {len(books)}")
    print(f"  Average price:   £{mean(prices):.2f}")
    print(f"  Cheapest:        £{min(prices):.2f}")
    print(f"  Most expensive:  £{max(prices):.2f}")

    by_category = defaultdict(list)
    for book in books:
        by_category[book.category].append(book.price)

    print(f"\n  {'Category':<23} {'Books':>8} {'Avg Price':>12}")
    print(f"  {'-'*45}")
    for category, items in sorted(by_category.items(), key=lambda kv: -len(kv[1])):
        print(f"  {category:<23} {len(items):>8} {f'£{mean(items):.2f}':>12}")

    best = sorted((b for b in books if b.rating == 5), key=lambda b: b.price)[:5]
    if best:
        print("\n  Top 5 cheapest with 5 stars:")
        for i, b in enumerate(best, 1):
            print(f"  {i}. {'★'*b.rating} £{b.price:.2f} - {shorten(b.title)}")

    print(f"\n{'='*50}")


def export_html(books: list[Book], path: str) -> None:
    """A single page with every book as a card (cover, price, stars), grouped by category.

    The covers are linked straight from books.toscrape.com instead of downloaded, so the
    file stays small; it needs internet to show them.
    """
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    by_category = defaultdict(list)
    for book in books:
        by_category[book.category].append(book)

    sections = []
    for category, items in sorted(by_category.items()):
        cards = "".join(_card(b) for b in sorted(items, key=lambda b: (-b.rating, b.price)))
        sections.append(
            f'<section><h2>{escape(category)} <small>{len(items)} books · '
            f'avg £{mean(b.price for b in items):.2f}</small></h2>'
            f'<div class="grid">{cards}</div></section>'
        )

    summary = (f"{len(books)} books · {len(by_category)} categories · "
               f"£{min(b.price for b in books):.2f} to £{max(b.price for b in books):.2f}") if books else "No books scraped."
    with open(path, "w", encoding="utf-8") as f:
        f.write(HTML_PAGE.format(summary=escape(summary), sections="".join(sections)))


def _card(book: Book) -> str:
    stars = "★" * book.rating + "☆" * (5 - book.rating)
    cover = (f'<img src="{escape(book.cover)}" alt="" loading="lazy">' if book.cover
             else '<div class="no-cover">no cover</div>')
    stock = "in stock" if book.available else "out of stock"
    return (
        f'<a class="card{"" if book.available else " out"}" href="{escape(book.url)}">{cover}'
        f'<span class="title">{escape(book.title)}</span>'
        f'<span class="meta"><b>£{book.price:.2f}</b>'
        f'<span class="stars" aria-label="{book.rating} of 5 stars">{stars}</span></span>'
        f'<span class="stock">{stock}</span></a>'
    )


# kept here instead of a template file so the scraper is still a single pip install
HTML_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Scraped books</title>
<style>
  :root {{ --bg: #f6f4ef; --card: #fff; --text: #222; --muted: #5f5b53; --accent: #8a5a00; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg: #1b1a18; --card: #26241f; --text: #eee; --muted: #b5afa3; --accent: #f0b85a; }}
  }}
  body {{ margin: 0; padding: 24px 16px; font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); }}
  main {{ max-width: 1100px; margin: 0 auto; }}
  h1 {{ margin: 0 0 4px; }}
  .summary, small, .stock {{ color: var(--muted); }}
  small {{ font-size: .6em; font-weight: normal; margin-left: 8px; }}
  h2 {{ margin: 32px 0 12px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 14px; }}
  .card {{ display: flex; flex-direction: column; gap: 6px; padding: 10px; border-radius: 8px;
          background: var(--card); color: inherit; text-decoration: none; box-shadow: 0 1px 3px #0002; }}
  .card:hover, .card:focus-visible {{ outline: 2px solid var(--accent); }}
  .card.out {{ opacity: .6; }}
  img, .no-cover {{ width: 100%; aspect-ratio: 2 / 3; object-fit: cover; border-radius: 4px; background: #0001; }}
  .no-cover {{ display: grid; place-items: center; color: var(--muted); font-size: .8em; }}
  .title {{ font-size: .9em; line-height: 1.25; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
  .meta {{ display: flex; justify-content: space-between; align-items: baseline; }}
  .stars {{ color: var(--accent); letter-spacing: 1px; }}
  .stock {{ font-size: .75em; }}
</style>
</head>
<body>
<main>
<h1>Scraped books</h1>
<p class="summary">{summary} · from <a href="https://books.toscrape.com">books.toscrape.com</a></p>
{sections}
</main>
</body>
</html>
"""
