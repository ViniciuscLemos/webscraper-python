"""PostgreSQL part: creates the table, saves the books and shows the report."""

import os
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from src.export import shorten
from src.scraper import Book

load_dotenv()


def connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "scraper_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )


def create_tables(conn: psycopg2.extensions.connection) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id          SERIAL PRIMARY KEY,
                title       TEXT NOT NULL,
                price       NUMERIC(8, 2) NOT NULL,
                rating      SMALLINT CHECK (rating BETWEEN 1 AND 5),
                available   BOOLEAN DEFAULT TRUE,
                category    TEXT,
                url         TEXT UNIQUE,
                scraped_at  TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_category ON books(category)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_rating ON books(rating)")

    conn.commit()
    print("Tables created/checked.")


def insert_books(conn: psycopg2.extensions.connection, books: list[Book]) -> int:
    """Inserts the books; if the URL already exists, just updates it (upsert)."""
    if not books:
        return 0

    # ON CONFLICT errors out if the same URL shows up twice in the same INSERT,
    # so I keep only one per URL. Rating 0 becomes NULL because of the CHECK.
    rows = list({
        b.url: (b.title, b.price, b.rating or None, b.available, b.category, b.url)
        for b in books
    }.values())

    with conn.cursor() as cur:
        execute_values(cur, """
            INSERT INTO books (title, price, rating, available, category, url)
            VALUES %s
            ON CONFLICT (url) DO UPDATE SET
                price      = EXCLUDED.price,
                rating     = EXCLUDED.rating,
                available  = EXCLUDED.available,
                scraped_at = NOW()
        """, rows)

    conn.commit()
    return len(rows)


def generate_report(conn: psycopg2.extensions.connection) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*), AVG(price), MIN(price), MAX(price) FROM books")
        total, average, lowest, highest = cur.fetchone()
        print(f"\n{'='*50}")
        print("  REPORT OF THE SCRAPED BOOKS")
        print(f"{'='*50}")

        if total == 0:
            print("  No books in the database.")
            print(f"{'='*50}")
            return

        print(f"  Total books:     {total}")
        print(f"  Average price:   £{float(average):.2f}")
        print(f"  Cheapest:        £{float(lowest):.2f}")
        print(f"  Most expensive:  £{float(highest):.2f}")

        cur.execute("""
            SELECT category, COUNT(*) as qty, AVG(price)
            FROM books
            GROUP BY category
            ORDER BY qty DESC
        """)
        print(f"\n  {'Category':<23} {'Books':>8} {'Avg Price':>12}")
        print(f"  {'-'*45}")
        for row in cur.fetchall():
            print(f"  {row[0]:<23} {row[1]:>8} {f'£{float(row[2]):.2f}':>12}")

        cur.execute("""
            SELECT title, rating, price
            FROM books
            WHERE rating = 5
            ORDER BY price ASC
            LIMIT 5
        """)
        print("\n  Top 5 cheapest with 5 stars:")
        for i, row in enumerate(cur.fetchall(), 1):
            print(f"  {i}. {'★'*row[1]} £{row[2]:.2f} - {shorten(row[0])}")

        print(f"\n{'='*50}")
