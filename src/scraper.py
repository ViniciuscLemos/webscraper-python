"""Scrapes books from books.toscrape.com (a site made for practicing scraping)."""

import time
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://books.toscrape.com/"

# the site puts the rating as a word in the CSS class (star-rating Three)
STARS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PortfolioScraper/1.0)"}


def create_session(retries: int = 3) -> requests.Session:
    """Session that retries on 429/5xx errors, waiting 0.5s, 1s, 2s..."""
    session = requests.Session()
    session.headers.update(HEADERS)
    retry = Retry(
        total=retries,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session.mount("http://", HTTPAdapter(max_retries=retry))
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


_session: Optional[requests.Session] = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = create_session()
    return _session


@dataclass
class Book:
    title: str
    price: float
    rating: int  # 1 to 5
    available: bool
    category: str
    url: str


def get_page(url: str) -> Optional[BeautifulSoup]:
    """Downloads the page and returns the parsed HTML, or None if something goes wrong."""
    try:
        response = _get_session().get(url, timeout=10)
        response.raise_for_status()
        response.encoding = "utf-8"  # without this the £ comes out broken
        return BeautifulSoup(response.text, "html.parser")
    except requests.exceptions.ConnectionError:
        print(f"  Connection error while accessing: {url}")
    except requests.exceptions.Timeout:
        print(f"  Timeout while accessing: {url}")
    except requests.exceptions.HTTPError as e:
        print(f"  HTTP error {e.response.status_code}: {url}")
    except requests.exceptions.RequestException as e:
        print(f"  Request failed ({e.__class__.__name__}): {url}")
    return None


def extract_books_from_page(soup: BeautifulSoup, category: str, page_url: str) -> list[Book]:
    books = []

    for article in soup.find_all("article", class_="product_pod"):
        try:
            # the link text gets cut off, the full title is in the title attribute
            title = article.h3.a["title"]
            url = urljoin(page_url, article.h3.a["href"])

            price_text = article.find("p", class_="price_color").text
            price = float(re.sub(r"[^\d.]", "", price_text))

            classes = article.find("p", class_="star-rating")["class"]
            word = next((c for c in classes if c in STARS), None)
            rating = STARS.get(word, 0)

            available = "In stock" in article.find("p", class_="instock").text

            books.append(Book(title, price, rating, available, category, url))
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            print(f"  Warning: couldn't extract a book ({e})")

    return books


def scrape_category(category_url: str, category_name: str,
                    max_pages: int = 5, delay: float = 1.0) -> list[Book]:
    """Goes through the category pages following the "next" button."""
    all_books = []
    current_url = category_url
    page = 1

    print(f"\nScraping category: {category_name}")

    while current_url and page <= max_pages:
        print(f"  Page {page}: {current_url}")

        soup = get_page(current_url)
        if soup is None:
            break

        page_books = extract_books_from_page(soup, category_name, current_url)
        all_books.extend(page_books)
        print(f"    {len(page_books)} books on this page")

        next_link = soup.find("li", class_="next")
        if next_link and next_link.a and page < max_pages:
            current_url = urljoin(current_url, next_link.a["href"])
            page += 1
            time.sleep(delay)  # so we don't overload the site
        else:
            break

    print(f"  Total scraped: {len(all_books)} books")
    return all_books


def get_categories(max_categories: int = 5, names: Optional[list[str]] = None) -> list[tuple[str, str]]:
    soup = get_page(BASE_URL)
    if soup is None:
        return []
    return extract_categories(soup, max_categories, names)


def extract_categories(soup: BeautifulSoup, max_categories: int = 5,
                       names: Optional[list[str]] = None) -> list[tuple[str, str]]:
    """Reads the side menu and returns [(name, url), ...].

    With `names`, returns only those categories (case insensitive), in the order asked.
    Without `names`, returns the first `max_categories`.
    """
    nav = soup.find("ul", class_="nav-list")
    if not nav:
        return []

    # the first link is "Books", which has everything
    everything = [(link.text.strip(), urljoin(BASE_URL, link["href"])) for link in nav.find_all("a")[1:]]
    if not names:
        return everything[:max_categories]

    by_name = {name.lower(): (name, url) for name, url in everything}
    return [by_name[n.strip().lower()] for n in names if n.strip().lower() in by_name]
