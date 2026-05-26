"""
Web Scraper de Livros — Python + PostgreSQL
=============================================
Coleta dados de livros do site books.toscrape.com,
salva em um banco PostgreSQL e gera relatório.

Execute: python main.py
"""

from src.scraper import raspar_categoria, obter_categorias
from src.banco import conectar, criar_tabelas, inserir_livros, gerar_relatorio


def main():
    print("=" * 50)
    print("  WEB SCRAPER DE LIVROS")
    print("  Fonte: books.toscrape.com")
    print("=" * 50)

    # Passo 1: Conecta ao banco
    print("\n[1/4] Conectando ao banco de dados...")
    try:
        conn = conectar()
        criar_tabelas(conn)
        print("      Conectado!")
    except Exception as e:
        print(f"      Erro de conexão: {e}")
        print("\n      Dica: verifique as configurações no arquivo .env")
        print("      Certifique-se que o PostgreSQL está rodando.")
        return

    # Passo 2: Obtém categorias disponíveis
    print("\n[2/4] Obtendo categorias do site...")
    categorias = obter_categorias(max_categorias=4)

    if not categorias:
        print("      Erro: não foi possível obter as categorias.")
        print("      Verifique sua conexão com a internet.")
        conn.close()
        return

    print(f"      {len(categorias)} categorias encontradas:")
    for nome, url in categorias:
        print(f"        - {nome}")

    # Passo 3: Raspa cada categoria
    print("\n[3/4] Coletando livros...")
    todos_livros = []

    for nome, url in categorias:
        livros = raspar_categoria(
            url_categoria=url,
            nome_categoria=nome,
            max_paginas=3,   # Máximo de páginas por categoria
            delay=0.8        # 0.8 segundos entre requisições
        )
        todos_livros.extend(livros)

    print(f"\n  Total coletado: {len(todos_livros)} livros")

    # Passo 4: Salva no banco e gera relatório
    print("\n[4/4] Salvando no banco de dados...")
    total_salvo = inserir_livros(conn, todos_livros)
    print(f"      {total_salvo} livros salvos/atualizados!")

    # Relatório final
    gerar_relatorio(conn)

    conn.close()
    print("\nColeta finalizada com sucesso!")


if __name__ == "__main__":
    main()
