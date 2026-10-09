"""
Scraper tests that don't hit the internet: they use sample HTML
with the same structure as books.toscrape.com.
"""

import csv
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest import mock

from bs4 import BeautifulSoup

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src import scraper  # noqa: E402
from src.export import export_csv, export_json, print_report, remove_duplicates, shorten  # noqa: E402
from src.scraper import Book  # noqa: E402


def article(title, href, price, stars, stock="In stock"):
    return f"""
    <article class="product_pod">
      <p class="star-rating {stars}"></p>
      <h3><a href="{href}" title="{title}">{title[:10]}...</a></h3>
      <div class="product_price">
        <p class="price_color">£{price}</p>
        <p class="instock availability">{stock}</p>
      </div>
    </article>"""


def page(articles, next_page=None):
    nav = f'<li class="next"><a href="{next_page}">next</a></li>' if next_page else ""
    return BeautifulSoup(f"<html><body>{''.join(articles)}<ul class='pager'>{nav}</ul></body></html>",
                         "html.parser")


CATEGORY_URL = "https://books.toscrape.com/catalogue/category/books/travel_2/index.html"


class TestExtraction(unittest.TestCase):
    def test_extracts_fields(self):
        soup = page([article("A Light in the Attic", "../../../a-light-in-the-attic_1000/index.html",
                             "51.77", "Three")])
        books = scraper.extract_books_from_page(soup, "Poetry", CATEGORY_URL)
        self.assertEqual(len(books), 1)
        book = books[0]
        self.assertEqual(book.title, "A Light in the Attic")
        self.assertEqual(book.price, 51.77)
        self.assertEqual(book.rating, 3)
        self.assertTrue(book.available)
        self.assertEqual(book.category, "Poetry")
        # urljoin resolves the "../" from the current page
        self.assertEqual(book.url, "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html")

    def test_out_of_stock_and_unknown_rating(self):
        soup = page([article("X", "x/index.html", "10.00", "Zero", stock="Out of stock")])
        book = scraper.extract_books_from_page(soup, "C", CATEGORY_URL)[0]
        self.assertFalse(book.available)
        self.assertEqual(book.rating, 0)

    def test_skips_malformed_book(self):
        broken = '<article class="product_pod"><h3></h3></article>'
        soup = page([broken, article("Ok", "ok/index.html", "1.00", "One")])
        with redirect_stdout(StringIO()):
            books = scraper.extract_books_from_page(soup, "C", CATEGORY_URL)
        self.assertEqual([b.title for b in books], ["Ok"])

    def test_extracts_categories(self):
        soup = BeautifulSoup("""
            <ul class="nav nav-list"><li><a href="catalogue/category/books_1/index.html">Books</a>
              <ul>
                <li><a href="catalogue/category/books/travel_2/index.html"> Travel </a></li>
                <li><a href="catalogue/category/books/mystery_3/index.html"> Mystery </a></li>
              </ul></li></ul>""", "html.parser")
        categories = scraper.extract_categories(soup, max_categories=5)
        self.assertEqual(categories, [
            ("Travel", "https://books.toscrape.com/catalogue/category/books/travel_2/index.html"),
            ("Mystery", "https://books.toscrape.com/catalogue/category/books/mystery_3/index.html"),
        ])


    def test_picks_categories_by_name(self):
        soup = BeautifulSoup("""
            <ul class="nav nav-list"><li><a href="catalogue/category/books_1/index.html">Books</a>
              <ul>
                <li><a href="catalogue/category/books/travel_2/index.html"> Travel </a></li>
                <li><a href="catalogue/category/books/mystery_3/index.html"> Mystery </a></li>
                <li><a href="catalogue/category/books/poetry_23/index.html"> Poetry </a></li>
              </ul></li></ul>""", "html.parser")
        categories = scraper.extract_categories(soup, names=["poetry", "Does Not Exist", "MYSTERY"])
        self.assertEqual([name for name, _ in categories], ["Poetry", "Mystery"])


class TestPagination(unittest.TestCase):
    def setUp(self):
        self.pages = {
            CATEGORY_URL: page([article("A", "a/index.html", "1.00", "One")], next_page="page-2.html"),
            CATEGORY_URL.replace("index.html", "page-2.html"):
                page([article("B", "b/index.html", "2.00", "Two")], next_page="page-3.html"),
            CATEGORY_URL.replace("index.html", "page-3.html"):
                page([article("C", "c/index.html", "3.00", "Five")]),
        }

    def scrape(self, max_pages):
        with mock.patch.object(scraper, "get_page", side_effect=self.pages.get), \
             mock.patch.object(scraper.time, "sleep") as sleep, \
             redirect_stdout(StringIO()):
            books = scraper.scrape_category(CATEGORY_URL, "Travel", max_pages=max_pages, delay=1)
        return books, sleep

    def test_follows_all_pages(self):
        books, sleep = self.scrape(max_pages=10)
        self.assertEqual([b.title for b in books], ["A", "B", "C"])
        self.assertEqual(sleep.call_count, 2)  # waits between pages, not after the last one

    def test_respects_page_limit(self):
        books, sleep = self.scrape(max_pages=2)
        self.assertEqual([b.title for b in books], ["A", "B"])
        self.assertEqual(sleep.call_count, 1)

    def test_stops_when_page_fails(self):
        with mock.patch.object(scraper, "get_page", return_value=None), redirect_stdout(StringIO()):
            self.assertEqual(scraper.scrape_category(CATEGORY_URL, "Travel"), [])


class TestExport(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.books = [
            Book("A", 10.0, 5, True, "Travel", "https://x/a"),
            Book("B", 20.0, 3, False, "Poetry", "https://x/b"),
            Book("A again", 10.0, 5, True, "Travel", "https://x/a"),
        ]

    def tearDown(self):
        self.folder.cleanup()

    def test_removes_duplicates_by_url(self):
        self.assertEqual([b.title for b in remove_duplicates(self.books)], ["A", "B"])

    def test_csv(self):
        path = os.path.join(self.folder.name, "sub", "books.csv")
        export_csv(self.books[:2], path)
        with open(path, "rb") as f:
            self.assertTrue(f.read().startswith(b"\xef\xbb\xbf"))  # BOM for Excel
        with open(path, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(rows[1]["title"], "B")
        self.assertEqual(rows[1]["available"], "False")

    def test_json(self):
        path = os.path.join(self.folder.name, "books.json")
        export_json(self.books[:2], path)
        with open(path, encoding="utf-8") as f:
            self.assertEqual(json.load(f)[0]["price"], 10.0)

    def test_report(self):
        output = StringIO()
        with redirect_stdout(output):
            print_report(self.books[:2])
            print_report([])
        text = output.getvalue()
        self.assertIn("Total books:     2", text)
        self.assertIn("Average price:   £15.00", text)
        self.assertIn("No books scraped", text)

    def test_shorten(self):
        self.assertEqual(shorten("Booked"), "Booked")
        long_title = "The Collected Poems of W.B. Yeats (The Collected Works)"
        self.assertLessEqual(len(shorten(long_title)), 40)
        self.assertTrue(shorten(long_title).endswith("…"))


if __name__ == "__main__":
    unittest.main()
