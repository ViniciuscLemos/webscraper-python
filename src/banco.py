"""Parte do PostgreSQL: cria a tabela, salva os livros e mostra o relatório."""

import os
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from src.scraper import Livro

load_dotenv()


def conectar() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "scraper_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )


def criar_tabelas(conn: psycopg2.extensions.connection) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS livros (
                id          SERIAL PRIMARY KEY,
                titulo      TEXT NOT NULL,
                preco       NUMERIC(8, 2) NOT NULL,
                avaliacao   SMALLINT CHECK (avaliacao BETWEEN 1 AND 5),
                disponivel  BOOLEAN DEFAULT TRUE,
                categoria   TEXT,
                url         TEXT UNIQUE,
                coletado_em TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_categoria ON livros(categoria)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_avaliacao ON livros(avaliacao)")

    conn.commit()
    print("Tabelas criadas/verificadas.")


def inserir_livros(conn: psycopg2.extensions.connection, livros: list[Livro]) -> int:
    """Insere os livros; se a URL já existir, só atualiza (upsert)."""
    if not livros:
        return 0

    # o ON CONFLICT dá erro se a mesma URL aparecer duas vezes no mesmo INSERT,
    # então deixo só uma por URL. Avaliação 0 vira NULL por causa do CHECK.
    dados = list({
        l.url: (l.titulo, l.preco, l.avaliacao or None, l.disponivel, l.categoria, l.url)
        for l in livros
    }.values())

    with conn.cursor() as cur:
        execute_values(cur, """
            INSERT INTO livros (titulo, preco, avaliacao, disponivel, categoria, url)
            VALUES %s
            ON CONFLICT (url) DO UPDATE SET
                preco      = EXCLUDED.preco,
                avaliacao  = EXCLUDED.avaliacao,
                disponivel = EXCLUDED.disponivel,
                coletado_em = NOW()
        """, dados)

    conn.commit()
    return len(dados)


def gerar_relatorio(conn: psycopg2.extensions.connection) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*), AVG(preco), MIN(preco), MAX(preco) FROM livros")
        total, media, minimo, maximo = cur.fetchone()
        print(f"\n{'='*50}")
        print("  RELATÓRIO DO ACERVO COLETADO")
        print(f"{'='*50}")

        if total == 0:
            print("  Nenhum livro no banco.")
            print(f"{'='*50}")
            return

        print(f"  Total de livros: {total}")
        print(f"  Preço médio:     £{float(media):.2f}")
        print(f"  Mais barato:     £{float(minimo):.2f}")
        print(f"  Mais caro:       £{float(maximo):.2f}")

        cur.execute("""
            SELECT categoria, COUNT(*) as qtd, AVG(preco)
            FROM livros
            GROUP BY categoria
            ORDER BY qtd DESC
        """)
        print(f"\n  {'Categoria':<23} {'Livros':>8} {'Preço Médio':>12}")
        print(f"  {'-'*45}")
        for row in cur.fetchall():
            print(f"  {row[0]:<23} {row[1]:>8} {f'£{float(row[2]):.2f}':>12}")

        cur.execute("""
            SELECT titulo, avaliacao, preco
            FROM livros
            WHERE avaliacao = 5
            ORDER BY preco ASC
            LIMIT 5
        """)
        print("\n  Top 5 com 5 estrelas e mais baratos:")
        for i, row in enumerate(cur.fetchall(), 1):
            print(f"  {i}. {'★'*row[1]} £{row[2]:.2f} - {row[0][:40]}")

        print(f"\n{'='*50}")
