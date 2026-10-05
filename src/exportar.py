"""Salva os livros em CSV/JSON e mostra o resumo quando não tem banco."""

import csv
import json
import os
from collections import defaultdict
from dataclasses import asdict, fields
from statistics import mean

from src.scraper import Livro


def remover_duplicados(livros: list[Livro]) -> list[Livro]:
    vistos = set()
    unicos = []
    for livro in livros:
        if livro.url not in vistos:
            vistos.add(livro.url)
            unicos.append(livro)
    return unicos


def exportar_csv(livros: list[Livro], caminho: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(caminho)), exist_ok=True)
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=[c.name for c in fields(Livro)])
        escritor.writeheader()
        for livro in livros:
            escritor.writerow(asdict(livro))


def exportar_json(livros: list[Livro], caminho: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(caminho)), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump([asdict(l) for l in livros], f, ensure_ascii=False, indent=2)


def imprimir_relatorio(livros: list[Livro]) -> None:
    print(f"\n{'='*50}")
    print("  RELATÓRIO DO ACERVO COLETADO")
    print(f"{'='*50}")

    if not livros:
        print("  Nenhum livro coletado.")
        print(f"{'='*50}")
        return

    precos = [l.preco for l in livros]
    print(f"  Total de livros: {len(livros)}")
    print(f"  Preço médio:     £{mean(precos):.2f}")
    print(f"  Mais barato:     £{min(precos):.2f}")
    print(f"  Mais caro:       £{max(precos):.2f}")

    por_categoria = defaultdict(list)
    for livro in livros:
        por_categoria[livro.categoria].append(livro.preco)

    print(f"\n  {'Categoria':<23} {'Livros':>8} {'Preço Médio':>12}")
    print(f"  {'-'*45}")
    for categoria, lista in sorted(por_categoria.items(), key=lambda kv: -len(kv[1])):
        print(f"  {categoria:<23} {len(lista):>8} {f'£{mean(lista):.2f}':>12}")

    melhores = sorted((l for l in livros if l.avaliacao == 5), key=lambda l: l.preco)[:5]
    if melhores:
        print("\n  Top 5 com 5 estrelas e mais baratos:")
        for i, l in enumerate(melhores, 1):
            print(f"  {i}. {'★'*l.avaliacao} £{l.preco:.2f} - {l.titulo[:40]}")

    print(f"\n{'='*50}")
