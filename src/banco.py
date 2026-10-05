"""
Módulo de banco de dados — PostgreSQL com psycopg2
====================================================
Salva os livros coletados em um banco PostgreSQL.

Conceitos que você vai aprender:
- psycopg2: driver Python para PostgreSQL
- ON CONFLICT DO UPDATE: upsert (inserir ou atualizar se já existir)
- Transações: commit/rollback
- Context manager com psycopg2
- Variáveis de ambiente para configurações sensíveis
"""

import os
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from src.scraper import Livro

# Carrega variáveis do arquivo .env
load_dotenv()


def conectar() -> psycopg2.extensions.connection:
    """Cria e retorna uma conexão com o PostgreSQL."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "scraper_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )


def criar_tabelas(conn: psycopg2.extensions.connection) -> None:
    """Cria a tabela de livros se não existir."""
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

        # Index para acelerar buscas por categoria e avaliação
        cur.execute("CREATE INDEX IF NOT EXISTS idx_categoria ON livros(categoria)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_avaliacao ON livros(avaliacao)")

    conn.commit()
    print("Tabelas criadas/verificadas com sucesso.")


def inserir_livros(conn: psycopg2.extensions.connection, livros: list[Livro]) -> int:
    """
    Insere ou atualiza os livros no banco.

    ON CONFLICT (url) DO UPDATE:
    Se um livro com a mesma URL já existir, atualiza os campos
    em vez de lançar erro. Isso se chama "upsert".

    execute_values() insere múltiplas linhas de uma vez (muito mais rápido
    do que um INSERT em loop).
    """
    if not livros:
        return 0

    # Prepara os dados como lista de tuplas.
    # Um mesmo INSERT não pode ter a mesma URL duas vezes (o ON CONFLICT
    # falharia), então usamos um dicionário para manter só uma por URL.
    # avaliacao 0 (desconhecida) vira NULL para respeitar o CHECK da tabela.
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
    """Exibe estatísticas dos livros coletados."""
    with conn.cursor() as cur:

        # Total geral
        cur.execute("SELECT COUNT(*), AVG(preco), MIN(preco), MAX(preco) FROM livros")
        total, media, minimo, maximo = cur.fetchone()
        print(f"\n{'='*50}")
        print("  RELATÓRIO DO ACERVO COLETADO")
        print(f"{'='*50}")

        # Com a tabela vazia, AVG/MIN/MAX retornam NULL (None no Python)
        if total == 0:
            print("  Nenhum livro no banco.")
            print(f"{'='*50}")
            return

        print(f"  Total de livros: {total}")
        print(f"  Preço médio:     £{float(media):.2f}")
        print(f"  Mais barato:     £{float(minimo):.2f}")
        print(f"  Mais caro:       £{float(maximo):.2f}")

        # Por categoria
        cur.execute("""
            SELECT categoria, COUNT(*) as qtd, AVG(preco) as media_preco
            FROM livros
            GROUP BY categoria
            ORDER BY qtd DESC
        """)
        print(f"\n  {'Categoria':<23} {'Livros':>8} {'Preço Médio':>12}")
        print(f"  {'-'*45}")
        for row in cur.fetchall():
            print(f"  {row[0]:<23} {row[1]:>8} {f'£{float(row[2]):.2f}':>12}")

        # Top 5 mais bem avaliados e mais baratos
        cur.execute("""
            SELECT titulo, avaliacao, preco, categoria
            FROM livros
            WHERE avaliacao = 5
            ORDER BY preco ASC
            LIMIT 5
        """)
        print(f"\n  TOP 5 — Melhor avaliados e mais baratos:")
        for i, row in enumerate(cur.fetchall(), 1):
            print(f"  {i}. {'★'*row[1]} £{row[2]:.2f} — {row[0][:40]}")

        print(f"\n{'='*50}")
