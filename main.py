"""Scrapes books from books.toscrape.com and saves them to Postgres or to CSV/JSON."""

import argparse
import sys

from src.scraper import scrape_category, get_categories


def read_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrapes books from books.toscrape.com.")
    parser.add_argument("--categories", type=int, default=4,
                        help="how many categories to scrape (default: 4)")
    parser.add_argument("--category", action="append", metavar="NAME",
                        help="scrapes only this category (can repeat, e.g. --category Mystery --category Poetry)")
    parser.add_argument("--pages", type=int, default=3,
                        help="max pages per category (default: 3)")
    parser.add_argument("--delay", type=float, default=0.8,
                        help="seconds to wait between pages (default: 0.8)")
    parser.add_argument("--no-db", action="store_true",
                        help="doesn't use PostgreSQL; only exports the files")
    parser.add_argument("--csv", metavar="FILE",
                        help="exports the books to a CSV file")
    parser.add_argument("--json", metavar="FILE",
                        help="exports the books to a JSON file")
    args = parser.parse_args(argv)

    if args.no_db and not (args.csv or args.json):
        args.csv = "output/books.csv"
    if args.categories < 1 or args.pages < 1:
        parser.error("--categories and --pages must be greater than zero")
    return args


def main(argv=None) -> int:
    # On Windows, with the output redirected to a file (python main.py > log.txt),
    # Python uses cp1252 and breaks on the ★ and £ in the report
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = read_args(argv)

    print("=" * 50)
    print("  BOOK WEB SCRAPER")
    print("  Source: books.toscrape.com")
    print("=" * 50)

    conn = None
    if args.no_db:
        print("\n[1/4] No database mode: the data will only be saved to files.")
    else:
        print("\n[1/4] Connecting to the database...")
        try:
            # imported here so whoever uses --no-db doesn't need psycopg2
            from src.database import connect, create_tables
            conn = connect()
            create_tables(conn)
            print("      Connected!")
        except Exception as e:
            print(f"      Connection error: {e}")
            print("\n      Tip: check the settings in the .env file")
            print("      Make sure PostgreSQL is running,")
            print("      or run without a database: python main.py --no-db")
            return 1

    try:
        print("\n[2/4] Getting the categories from the site...")
        categories = get_categories(max_categories=args.categories, names=args.category)

        if args.category:
            found = {name.lower() for name, _ in categories}
            missing = [n for n in args.category if n.strip().lower() not in found]
            if missing:
                print(f"      Not found on the site: {', '.join(missing)}")

        if not categories:
            print("      Error: no categories to scrape.")
            print("      Check your internet connection or the category names.")
            return 1

        print(f"      {len(categories)} category(ies):")
        for name, _ in categories:
            print(f"        - {name}")

        print("\n[3/4] Scraping books...")
        all_books = []
        for name, url in categories:
            all_books.extend(scrape_category(
                category_url=url,
                category_name=name,
                max_pages=args.pages,
                delay=args.delay,
            ))

        print(f"\n  Total scraped: {len(all_books)} books")

        print("\n[4/4] Saving the data...")
        from src.export import export_csv, export_json, print_report, remove_duplicates
        all_books = remove_duplicates(all_books)

        if args.csv:
            export_csv(all_books, args.csv)
            print(f"      CSV saved to: {args.csv}")
        if args.json:
            export_json(all_books, args.json)
            print(f"      JSON saved to: {args.json}")

        if conn is not None:
            from src.database import insert_books, generate_report
            total_saved = insert_books(conn, all_books)
            print(f"      {total_saved} books saved/updated in the database!")
            generate_report(conn)
        else:
            print_report(all_books)
    finally:
        if conn is not None:
            conn.close()

    print("\nScraping finished!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
