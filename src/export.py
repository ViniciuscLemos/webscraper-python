"""Saves the books to CSV/JSON and shows the summary when there's no database."""

import csv
import json
import os
from collections import defaultdict
from dataclasses import asdict, fields
from statistics import mean

from src.scraper import Book


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
            print(f"  {i}. {'★'*b.rating} £{b.price:.2f} - {b.title[:40]}")

    print(f"\n{'='*50}")
