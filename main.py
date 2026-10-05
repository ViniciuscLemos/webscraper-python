"""
Web Scraper de Livros — Python + PostgreSQL
=============================================
Coleta dados de livros do site books.toscrape.com,
salva em um banco PostgreSQL (ou em CSV/JSON) e gera relatório.

Execute: python main.py --help
"""

import argparse
import sys

from src.scraper import raspar_categoria, obter_categorias


def ler_argumentos(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Coleta livros de books.toscrape.com.")
    parser.add_argument("--categorias", type=int, default=4,
                        help="quantas categorias coletar (padrão: 4)")
    parser.add_argument("--paginas", type=int, default=3,
                        help="máximo de páginas por categoria (padrão: 3)")
    parser.add_argument("--delay", type=float, default=0.8,
                        help="segundos de espera entre páginas (padrão: 0.8)")
    parser.add_argument("--sem-banco", action="store_true",
                        help="não usa o PostgreSQL; só exporta os arquivos")
    parser.add_argument("--csv", metavar="ARQUIVO",
                        help="exporta os livros para um arquivo CSV")
    parser.add_argument("--json", metavar="ARQUIVO",
                        help="exporta os livros para um arquivo JSON")
    args = parser.parse_args(argv)

    if args.sem_banco and not (args.csv or args.json):
        args.csv = "output/livros.csv"
    if args.categorias < 1 or args.paginas < 1:
        parser.error("--categorias e --paginas devem ser maiores que zero")
    return args


def main(argv=None) -> int:
    args = ler_argumentos(argv)

    print("=" * 50)
    print("  WEB SCRAPER DE LIVROS")
    print("  Fonte: books.toscrape.com")
    print("=" * 50)

    # Passo 1: Conecta ao banco (opcional)
    conn = None
    if args.sem_banco:
        print("\n[1/4] Modo sem banco: os dados serão salvos só em arquivo.")
    else:
        print("\n[1/4] Conectando ao banco de dados...")
        try:
            # Import aqui dentro: quem usa --sem-banco não precisa do psycopg2
            from src.banco import conectar, criar_tabelas
            conn = conectar()
            criar_tabelas(conn)
            print("      Conectado!")
        except Exception as e:
            print(f"      Erro de conexão: {e}")
            print("\n      Dica: verifique as configurações no arquivo .env")
            print("      Certifique-se que o PostgreSQL está rodando,")
            print("      ou rode sem banco: python main.py --sem-banco")
            return 1

    try:
        # Passo 2: Obtém categorias disponíveis
        print("\n[2/4] Obtendo categorias do site...")
        categorias = obter_categorias(max_categorias=args.categorias)

        if not categorias:
            print("      Erro: não foi possível obter as categorias.")
            print("      Verifique sua conexão com a internet.")
            return 1

        print(f"      {len(categorias)} categorias encontradas:")
        for nome, _ in categorias:
            print(f"        - {nome}")

        # Passo 3: Raspa cada categoria
        print("\n[3/4] Coletando livros...")
        todos_livros = []
        for nome, url in categorias:
            todos_livros.extend(raspar_categoria(
                url_categoria=url,
                nome_categoria=nome,
                max_paginas=args.paginas,
                delay=args.delay,
            ))

        print(f"\n  Total coletado: {len(todos_livros)} livros")

        # Passo 4: Salva e gera relatório
        print("\n[4/4] Salvando os dados...")
        from src.exportar import exportar_csv, exportar_json, imprimir_relatorio, remover_duplicados
        todos_livros = remover_duplicados(todos_livros)

        if args.csv:
            exportar_csv(todos_livros, args.csv)
            print(f"      CSV salvo em: {args.csv}")
        if args.json:
            exportar_json(todos_livros, args.json)
            print(f"      JSON salvo em: {args.json}")

        if conn is not None:
            from src.banco import inserir_livros, gerar_relatorio
            total_salvo = inserir_livros(conn, todos_livros)
            print(f"      {total_salvo} livros salvos/atualizados no banco!")
            gerar_relatorio(conn)
        else:
            imprimir_relatorio(todos_livros)
    finally:
        if conn is not None:
            conn.close()

    print("\nColeta finalizada com sucesso!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
